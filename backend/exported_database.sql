--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4 (Debian 17.4-1.pgdg120+2)
-- Dumped by pg_dump version 17.4 (Debian 17.4-1.pgdg120+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: create_bid_transactions(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.create_bid_transactions() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                auction_title TEXT;
                tx_id UUID;
            BEGIN
                -- Get the auction title for transaction reference
                SELECT title INTO auction_title FROM auctions_auction WHERE id = NEW.auction_id;
                
                -- For new bids, create BID_HOLD transaction
                IF TG_OP = 'INSERT' THEN
                    -- Generate UUID for new transaction
                    tx_id := uuid_generate_v4();
                    
                    -- Create a BID_HOLD transaction
                    INSERT INTO transactions_transaction (
                        id, user_id, transaction_type, amount, status,
                        reference, reference_id, created_at, updated_at
                    ) VALUES (
                        tx_id,
                        NEW.bidder_id,
                        'bid_hold',
                        NEW.amount,
                        'completed',
                        'Hold for bid on ' || auction_title,
                        NEW.id,
                        NOW(),
                        NOW()
                    );
                    
                    -- Update wallet balance
                    UPDATE accounts_wallet
                    SET balance = balance - NEW.amount,
                        held_balance = held_balance + NEW.amount
                    WHERE user_id = NEW.bidder_id;
                    
                -- For status changes, handle different transaction types
                ELSIF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
                    -- Handle status changes
                    
                    -- Outbid or cancelled - release held funds
                    IF NEW.status IN ('outbid', 'cancelled') THEN
                        tx_id := uuid_generate_v4();
                        
                        -- Create BID_RELEASE transaction
                        INSERT INTO transactions_transaction (
                            id, user_id, transaction_type, amount, status,
                            reference, reference_id, created_at, updated_at
                        ) VALUES (
                            tx_id,
                            NEW.bidder_id,
                            'bid_release',
                            NEW.amount,
                            'completed',
                            'Release funds for outbid on ' || auction_title,
                            NEW.id,
                            NOW(),
                            NOW()
                        );
                        
                        -- Update wallet
                        UPDATE accounts_wallet
                        SET balance = balance + NEW.amount,
                            held_balance = held_balance - NEW.amount
                        WHERE user_id = NEW.bidder_id;
                        
                    -- Won - process purchase
                    ELSIF NEW.status = 'won' THEN
                        -- Purchase transaction
                        tx_id := uuid_generate_v4();
                        INSERT INTO transactions_transaction (
                            id, user_id, transaction_type, amount, status,
                            reference, reference_id, created_at, updated_at
                        ) VALUES (
                            tx_id,
                            NEW.bidder_id,
                            'purchase',
                            NEW.amount,
                            'completed',
                            'Purchase of ' || auction_title,
                            NEW.auction_id,
                            NOW(),
                            NOW()
                        );
                        
                        -- Update held_balance in wallet
                        UPDATE accounts_wallet
                        SET held_balance = held_balance - NEW.amount
                        WHERE user_id = NEW.bidder_id;
                        
                        -- Calculate platform fee (5%)
                        DECLARE
                            platform_fee DECIMAL(12,2);
                            net_seller_amount DECIMAL(12,2);
                            seller_id UUID;
                        BEGIN
                            -- Get the seller ID
                            SELECT seller_id INTO seller_id FROM auctions_auction WHERE id = NEW.auction_id;
                            
                            -- Calculate fee and seller amount
                            platform_fee := NEW.amount * 0.05;
                            net_seller_amount := NEW.amount - platform_fee;
                            
                            -- Create FEE transaction
                            tx_id := uuid_generate_v4();
                            INSERT INTO transactions_transaction (
                                id, user_id, transaction_type, amount, status,
                                reference, reference_id, created_at, updated_at
                            ) VALUES (
                                tx_id,
                                seller_id,
                                'fee',
                                platform_fee,
                                'completed',
                                'Fee for auction ' || auction_title,
                                NEW.auction_id,
                                NOW(),
                                NOW()
                            );
                            
                            -- Create SALE transaction for seller
                            tx_id := uuid_generate_v4();
                            INSERT INTO transactions_transaction (
                                id, user_id, transaction_type, amount, status,
                                reference, reference_id, created_at, updated_at
                            ) VALUES (
                                tx_id,
                                seller_id,
                                'sale',
                                net_seller_amount,
                                'completed',
                                'Sale of ' || auction_title,
                                NEW.auction_id,
                                NOW(),
                                NOW()
                            );
                            
                            -- Update seller wallet balance
                            UPDATE accounts_wallet
                            SET balance = balance + net_seller_amount
                            WHERE user_id = seller_id;
                        END;
                    END IF;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.create_bid_transactions() OWNER TO django_user;

--
-- Name: extend_auction_time(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.extend_auction_time() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                time_remaining INTERVAL;
                auction_record RECORD;
            BEGIN
                -- Find the auction this bid belongs to
                SELECT * INTO auction_record FROM auctions_auction WHERE id = NEW.auction_id;
                
                -- Calculate time remaining
                time_remaining := auction_record.end_time - NOW();
                
                -- If less than 5 minutes remaining, extend by 5 minutes
                IF time_remaining < INTERVAL '5 minutes' AND auction_record.status = 'active' THEN
                    UPDATE auctions_auction
                    SET end_time = end_time + INTERVAL '5 minutes'
                    WHERE id = NEW.auction_id;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.extend_auction_time() OWNER TO django_user;

--
-- Name: handle_auction_status_change(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.handle_auction_status_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                highest_bid_record RECORD;
                bidder_record RECORD;
                notification_id UUID;
                auction_title TEXT;
            BEGIN
                -- Only run when status changes
                IF NEW.status = OLD.status THEN
                    RETURN NEW;
                END IF;
                
                -- Get the auction title for notifications
                auction_title := NEW.title;
                
                -- Handle auction ended
                IF NEW.status = 'ended' THEN
                    -- Get highest active bid
                    SELECT * INTO highest_bid_record 
                    FROM auctions_bid 
                    WHERE auction_id = NEW.id 
                    AND status = 'active' 
                    ORDER BY amount DESC LIMIT 1;
                    
                    -- If there is a highest bid and it meets reserve price
                    IF FOUND AND (NEW.reserve_price IS NULL OR highest_bid_record.amount >= NEW.reserve_price) THEN
                        -- Update highest bid to won status
                        UPDATE auctions_bid SET status = 'won' 
                        WHERE id = highest_bid_record.id;
                        
                        -- Update all other bids to lost status
                        UPDATE auctions_bid SET status = 'lost' 
                        WHERE auction_id = NEW.id AND id != highest_bid_record.id;
                        
                        -- Update auction to sold status
                        UPDATE auctions_auction SET status = 'sold' 
                        WHERE id = NEW.id;
                        
                        -- Create notification for winner
                        notification_id := uuid_generate_v4();
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            highest_bid_record.bidder_id,
                            'auction_won',
                            'You won the auction for ' || auction_title,
                            'Congratulations! You won the auction for ''' || auction_title || ''' with a bid of ' || highest_bid_record.amount || '. Please proceed to checkout to complete your purchase.',
                            NEW.id,
                            'auction',
                            false,
                            'high',
                            NOW()
                        );
                    ELSE
                        -- Mark all bids as lost if no highest bid or reserve not met
                        UPDATE auctions_bid SET status = 'lost' 
                        WHERE auction_id = NEW.id AND status = 'active';
                    END IF;
                    
                    -- Notify seller about auction end
                    notification_id := uuid_generate_v4();
                    
                    -- Craft appropriate message based on outcome
                    IF FOUND AND (NEW.reserve_price IS NULL OR highest_bid_record.amount >= NEW.reserve_price) THEN
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            NEW.seller_id,
                            'auction_ended',
                            'Your auction for ' || auction_title || ' has ended',
                            'Your auction for ''' || auction_title || ''' has ended with a winning bid of ' || highest_bid_record.amount || '. The buyer will be notified to complete the payment.',
                            NEW.id,
                            'auction',
                            false,
                            'high',
                            NOW()
                        );
                    ELSIF FOUND THEN
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            NEW.seller_id,
                            'auction_ended',
                            'Your auction for ' || auction_title || ' has ended',
                            'Your auction for ''' || auction_title || ''' has ended but the reserve price was not met. The highest bid was ' || highest_bid_record.amount || '.',
                            NEW.id,
                            'auction',
                            false,
                            'high',
                            NOW()
                        );
                    ELSE
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            NEW.seller_id,
                            'auction_ended',
                            'Your auction for ' || auction_title || ' has ended',
                            'Your auction for ''' || auction_title || ''' has ended with no bids.',
                            NEW.id,
                            'auction',
                            false,
                            'high',
                            NOW()
                        );
                    END IF;
                    
                    -- Notify all watchers that auction has ended
                    FOR bidder_record IN
                        SELECT DISTINCT user_id FROM auctions_auctionwatch WHERE auction_id = NEW.id
                    LOOP
                        notification_id := uuid_generate_v4();
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            bidder_record.user_id,
                            'auction_ended',
                            'Auction has ended: ' || auction_title,
                            'The auction ''' || auction_title || ''' you''re watching has ended.',
                            NEW.id,
                            'auction',
                            false,
                            'medium',
                            NOW()
                        );
                    END LOOP;
                    
                -- Handle auction cancelled
                ELSIF NEW.status = 'cancelled' THEN
                    -- Mark all bids as cancelled
                    UPDATE auctions_bid SET status = 'cancelled' 
                    WHERE auction_id = NEW.id AND status = 'active';
                    
                    -- Notify all bidders
                    FOR bidder_record IN
                        SELECT DISTINCT bidder_id FROM auctions_bid WHERE auction_id = NEW.id
                    LOOP
                        notification_id := uuid_generate_v4();
                        INSERT INTO notifications_notification (
                            id, recipient_id, notification_type, title, message,
                            related_object_id, related_object_type, is_read, priority, created_at
                        ) VALUES (
                            notification_id,
                            bidder_record.bidder_id,
                            'auction_cancelled',
                            'Auction cancelled: ' || auction_title,
                            'The auction ''' || auction_title || ''' you bid on has been cancelled by the seller or admin. No charges have been applied.',
                            NEW.id,
                            'auction',
                            false,
                            'high',
                            NOW()
                        );
                    END LOOP;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.handle_auction_status_change() OWNER TO django_user;

--
-- Name: handle_new_bid(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.handle_new_bid() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                -- Only run on new bids that are active
                IF TG_OP = 'INSERT' AND NEW.status = 'active' THEN
                    -- Mark all other active bids for this auction as outbid
                    UPDATE auctions_bid 
                    SET status = 'outbid'
                    WHERE auction_id = NEW.auction_id
                    AND status = 'active'
                    AND id != NEW.id;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.handle_new_bid() OWNER TO django_user;

--
-- Name: handle_outbid_wallet_refund(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.handle_outbid_wallet_refund() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF NEW.status = 'outbid' AND OLD.status = 'active' THEN
                    -- Refund the outbid user's wallet
                    UPDATE accounts_wallet
                    SET balance = balance + OLD.amount
                    WHERE user_id = OLD.bidder_id;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.handle_outbid_wallet_refund() OWNER TO django_user;

--
-- Name: notify_outbid_users(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.notify_outbid_users() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                auction_title TEXT;
                auction_end_time TIMESTAMP;
                outbid_bid_record RECORD;
                outbid_user_id UUID;
                notification_id UUID;
            BEGIN
                -- Get auction details
                SELECT title, end_time INTO auction_title, auction_end_time
                FROM auctions_auction WHERE id = NEW.auction_id;
                
                -- Find users who were outbid (those whose bids were just marked as outbid)
                FOR outbid_bid_record IN 
                    SELECT DISTINCT bidder_id 
                    FROM auctions_bid 
                    WHERE auction_id = NEW.auction_id 
                    AND status = 'outbid' 
                    AND bidder_id != NEW.bidder_id
                    AND timestamp < NEW.timestamp
                LOOP
                    outbid_user_id := outbid_bid_record.bidder_id;
                    
                    -- Generate a UUID for the notification
                    notification_id := uuid_generate_v4();
                    
                    -- Create notification for outbid user
                    INSERT INTO notifications_notification (
                        id, recipient_id, notification_type, title, message,
                        related_object_id, related_object_type, is_read, priority, created_at
                    ) VALUES (
                        notification_id,
                        outbid_user_id,
                        'outbid',
                        'You''ve been outbid on ' || auction_title,
                        'Someone placed a higher bid of ' || NEW.amount || ' on ''' || auction_title || '''. The auction ends on ' || auction_end_time || '.',
                        NEW.auction_id,
                        'auction',
                        false,
                        'high',
                        NOW()
                    );
                END LOOP;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.notify_outbid_users() OWNER TO django_user;

--
-- Name: process_autobid(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.process_autobid() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                autobid_record RECORD;
                current_highest_bid DECIMAL(12,2);
                new_bid_amount DECIMAL(12,2);
                wallet_balance DECIMAL(12,2);
            BEGIN
                -- Only process if a new bid is placed and outbids someone
                IF NEW.status = 'active' THEN
                    -- Find all active autobids for this auction excluding the bidder who just bid
                    FOR autobid_record IN 
                        SELECT ab.*, w.balance as wallet_balance
                        FROM transactions_autobid ab
                        JOIN accounts_wallet w ON w.user_id = ab.user_id
                        WHERE ab.auction_id = NEW.auction_id
                          AND ab.is_active = TRUE
                          AND ab.user_id != NEW.bidder_id
                        ORDER BY ab.max_amount DESC
                    LOOP
                        -- Get current highest bid amount
                        SELECT COALESCE(MAX(amount), 0) INTO current_highest_bid
                        FROM auctions_bid
                        WHERE auction_id = NEW.auction_id AND status = 'active';
                        
                        -- Calculate new bid amount (current highest + increment)
                        new_bid_amount := current_highest_bid + autobid_record.bid_increment;
                        
                        -- Check if this autobid can outbid the current highest bid
                        IF new_bid_amount <= autobid_record.max_amount AND new_bid_amount <= autobid_record.wallet_balance THEN
                            -- Create a new bid for the autobidder
                            INSERT INTO auctions_bid (
                                id, auction_id, bidder_id, amount, timestamp, status
                            ) VALUES (
                                uuid_generate_v4(), NEW.auction_id, autobid_record.user_id, 
                                new_bid_amount, NOW(), 'active'
                            );
                            
                            -- Update the current bid to outbid
                            UPDATE auctions_bid SET status = 'outbid' WHERE id = NEW.id;
                            
                            -- Update wallet balance for the autobidder
                            UPDATE accounts_wallet 
                            SET balance = balance - new_bid_amount
                            WHERE user_id = autobid_record.user_id;
                            
                            -- Return here as we've processed one autobid
                            -- The trigger will fire again for the new bid
                            RETURN NEW;
                        END IF;
                    END LOOP;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.process_autobid() OWNER TO django_user;

--
-- Name: process_autobids(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.process_autobids() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                auto_bid RECORD;
                next_bid_amount DECIMAL(12,2);
                new_bid_id UUID;
            BEGIN
                -- Only run on new bids
                IF TG_OP != 'INSERT' THEN
                    RETURN NEW;
                END IF;
                
                -- Loop through active autobids for this auction, ordered by max amount desc
                FOR auto_bid IN 
                    SELECT ab.*, w.balance 
                    FROM transactions_autobid ab
                    JOIN accounts_wallet w ON w.user_id = ab.user_id
                    WHERE ab.auction_id = NEW.auction_id
                    AND ab.is_active = true
                    AND ab.user_id != NEW.bidder_id
                    ORDER BY ab.max_amount DESC
                LOOP
                    -- Calculate next minimum bid amount
                    next_bid_amount := NEW.amount + auto_bid.bid_increment;
                    
                    -- Check if autobid's max amount is sufficient and wallet has funds
                    IF auto_bid.max_amount >= next_bid_amount AND auto_bid.balance >= next_bid_amount THEN
                        -- Generate UUID for new bid
                        new_bid_id := uuid_generate_v4();
                        
                        -- Create the autobid
                        INSERT INTO auctions_bid (
                            id, auction_id, bidder_id, amount, status, timestamp
                        ) VALUES (
                            new_bid_id,
                            NEW.auction_id,
                            auto_bid.user_id,
                            next_bid_amount,
                            'active',
                            NOW()
                        );
                        
                        -- Update prior bids to outbid status
                        UPDATE auctions_bid
                        SET status = 'outbid'
                        WHERE auction_id = NEW.auction_id
                        AND id != new_bid_id
                        AND status = 'active';
                        
                        -- No need to process more autobids, this one succeeded
                        EXIT;
                    END IF;
                END LOOP;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.process_autobids() OWNER TO django_user;

--
-- Name: process_buy_now(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.process_buy_now() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                -- Check if this bid meets the buy now price
                IF TG_OP = 'INSERT' THEN
                    DECLARE
                        auction_buy_now_price DECIMAL(12,2);
                    BEGIN
                        -- Get buy now price for the auction
                        SELECT auctions_auction.buy_now_price INTO auction_buy_now_price 
                        FROM auctions_auction 
                        WHERE id = NEW.auction_id;
                        
                        -- If buy now price exists and bid meets/exceeds it
                        IF auction_buy_now_price IS NOT NULL AND NEW.amount >= auction_buy_now_price THEN
                            -- Mark this bid as won
                            NEW.status := 'won';
                            
                            -- Update auction status to sold
                            UPDATE auctions_auction 
                            SET status = 'sold' 
                            WHERE id = NEW.auction_id;
                            
                            -- Mark all other bids as lost
                            UPDATE auctions_bid 
                            SET status = 'lost' 
                            WHERE auction_id = NEW.auction_id 
                            AND id != NEW.id;
                        END IF;
                        
                        RETURN NEW;
                    END;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.process_buy_now() OWNER TO django_user;

--
-- Name: send_payment_notification(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.send_payment_notification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                notification_id UUID;
                title_text TEXT;
                message_text TEXT;
                is_deposit BOOLEAN;
            BEGIN
                -- Only run if status becomes 'completed'
                IF NEW.status = 'completed' AND (OLD.status != 'completed' OR TG_OP = 'INSERT') THEN
                    -- Determine if this is a deposit-type transaction
                    is_deposit := NEW.transaction_type IN ('deposit', 'sale', 'refund');
                    
                    -- Set up notification text
                    IF is_deposit THEN
                        title_text := 'Payment Received';
                        message_text := 'Received ' || NEW.amount || ' for ' || NEW.reference || '.';
                    ELSE
                        title_text := 'Payment Sent';
                        message_text := 'Sent ' || NEW.amount || ' for ' || NEW.reference || '.';
                    END IF;
                    
                    -- Create notification
                    notification_id := uuid_generate_v4();
                    INSERT INTO notifications_notification (
                        id, recipient_id, notification_type, title, message,
                        related_object_id, related_object_type, is_read, priority, created_at
                    ) VALUES (
                        notification_id,
                        NEW.user_id,
                        'payment',
                        title_text,
                        message_text,
                        NEW.id,
                        'transaction',
                        false,
                        'high',
                        NOW()
                    );
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.send_payment_notification() OWNER TO django_user;

--
-- Name: update_auction_status(); Type: FUNCTION; Schema: public; Owner: django_user
--

CREATE FUNCTION public.update_auction_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                now_time TIMESTAMP;
                highest_bid_record RECORD;
                notification_id UUID;
                lost_bid RECORD;
                bid RECORD;
            BEGIN
                now_time := NOW();
                
                -- Check if auction should be activated
                IF OLD.status = 'pending' AND now_time >= OLD.start_time THEN
                    NEW.status := 'active';
                    
                    -- Notify seller that auction has started
                    notification_id := uuid_generate_v4();
                    INSERT INTO notifications_notification (
                        id, recipient_id, notification_type, title, message,
                        related_object_id, related_object_type, is_read, priority, created_at
                    ) VALUES (
                        notification_id,
                        NEW.seller_id,
                        'auction_started',
                        'Your auction has started: ' || NEW.title,
                        'Your auction for ''' || NEW.title || ''' is now active and accepting bids.',
                        NEW.id,
                        'auction',
                        false,
                        'medium',
                        NOW()
                    );
                END IF;
                
                -- Check if auction should be ended
                IF OLD.status = 'active' AND now_time >= OLD.end_time THEN
                    NEW.status := 'ended';
                    
                    -- Find highest bid
                    SELECT * INTO highest_bid_record 
                    FROM auctions_bid 
                    WHERE auction_id = NEW.id 
                    AND status = 'active' 
                    ORDER BY amount DESC LIMIT 1;
                    
                    -- If there is a highest bid and it meets reserve price
                    IF FOUND AND (NEW.reserve_price IS NULL OR highest_bid_record.amount >= NEW.reserve_price) THEN
                        -- Update highest bid to won status
                        UPDATE auctions_bid SET status = 'won' 
                        WHERE id = highest_bid_record.id;
                        
                        -- Update all other bids to lost status
                        UPDATE auctions_bid SET status = 'lost' 
                        WHERE auction_id = NEW.id AND id != highest_bid_record.id;
                        
                        -- Release funds for all lost bids
                        FOR lost_bid IN 
                            SELECT * FROM auctions_bid 
                            WHERE auction_id = NEW.id 
                            AND status = 'lost' 
                            AND bidder_id != highest_bid_record.bidder_id
                        LOOP
                            -- Release funds for lost bidders
                            UPDATE accounts_wallet
                            SET balance = balance + lost_bid.amount,
                                held_balance = GREATEST(0, held_balance - lost_bid.amount)
                            WHERE user_id = lost_bid.bidder_id;
                            
                            -- Create a transaction record for the release
                            INSERT INTO transactions_transaction (
                                id, user_id, transaction_type, amount, status,
                                reference, reference_id, created_at, updated_at, completed_at
                            ) VALUES (
                                uuid_generate_v4(),
                                lost_bid.bidder_id,
                                'bid_release',
                                lost_bid.amount,
                                'completed',
                                'Release funds for lost bid on ' || NEW.title,
                                lost_bid.id,
                                NOW(),
                                NOW(),
                                NOW()
                            );
                        END LOOP;
                        
                        -- Update auction to sold status
                        NEW.status := 'sold';
                    ELSE
                        -- Release all bids if no winner
                        FOR bid IN 
                            SELECT * FROM auctions_bid 
                            WHERE auction_id = NEW.id
                        LOOP
                            -- Release funds back to all bidders
                            UPDATE accounts_wallet
                            SET balance = balance + bid.amount,
                                held_balance = GREATEST(0, held_balance - bid.amount)
                            WHERE user_id = bid.bidder_id;
                            
                            -- Create a transaction record for each release
                            INSERT INTO transactions_transaction (
                                id, user_id, transaction_type, amount, status,
                                reference, reference_id, created_at, updated_at, completed_at
                            ) VALUES (
                                uuid_generate_v4(),
                                bid.bidder_id,
                                'bid_release',
                                bid.amount,
                                'completed',
                                'Release funds for auction ended without sale: ' || NEW.title,
                                bid.id,
                                NOW(),
                                NOW(),
                                NOW()
                            );
                            
                            -- Mark bid as lost
                            UPDATE auctions_bid SET status = 'lost' 
                            WHERE id = bid.id;
                        END LOOP;
                    END IF;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.update_auction_status() OWNER TO django_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accounts_address; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_address (
    id uuid NOT NULL,
    address_line1 character varying(255) NOT NULL,
    address_line2 character varying(255),
    city character varying(100) NOT NULL,
    state character varying(100) NOT NULL,
    postal_code character varying(20) NOT NULL,
    country character varying(100) NOT NULL,
    is_default boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.accounts_address OWNER TO django_user;

--
-- Name: accounts_paymentmethod; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_paymentmethod (
    id uuid NOT NULL,
    payment_type character varying(20) NOT NULL,
    provider character varying(100) NOT NULL,
    account_identifier character varying(100) NOT NULL,
    is_default boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.accounts_paymentmethod OWNER TO django_user;

--
-- Name: accounts_user; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_user (
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    is_staff boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    email character varying(254) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    phone_number character varying(20),
    role character varying(10) NOT NULL,
    is_active boolean NOT NULL,
    signup_datetime timestamp with time zone NOT NULL,
    last_login_datetime timestamp with time zone
);


ALTER TABLE public.accounts_user OWNER TO django_user;

--
-- Name: accounts_user_groups; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_user_groups (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.accounts_user_groups OWNER TO django_user;

--
-- Name: accounts_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.accounts_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounts_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounts_user_user_permissions; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_user_user_permissions (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.accounts_user_user_permissions OWNER TO django_user;

--
-- Name: accounts_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.accounts_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounts_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounts_wallet; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.accounts_wallet (
    id uuid NOT NULL,
    balance numeric(12,2) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    user_id uuid NOT NULL,
    held_balance numeric(12,2) NOT NULL,
    pending_balance numeric(12,2) NOT NULL
);


ALTER TABLE public.accounts_wallet OWNER TO django_user;

--
-- Name: auctions_auction; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auctions_auction (
    id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text NOT NULL,
    starting_price numeric(12,2) NOT NULL,
    reserve_price numeric(12,2),
    buy_now_price numeric(12,2),
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    auction_type character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    seller_id uuid NOT NULL,
    item_id uuid NOT NULL
);


ALTER TABLE public.auctions_auction OWNER TO django_user;

--
-- Name: auctions_auctionwatch; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auctions_auctionwatch (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    auction_id uuid NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.auctions_auctionwatch OWNER TO django_user;

--
-- Name: auctions_auctionwatch_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.auctions_auctionwatch ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auctions_auctionwatch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auctions_bid; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auctions_bid (
    id uuid NOT NULL,
    amount numeric(12,2) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    auction_id uuid NOT NULL,
    bidder_id uuid NOT NULL
);


ALTER TABLE public.auctions_bid OWNER TO django_user;

--
-- Name: auctions_category; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auctions_category (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    parent_id uuid
);


ALTER TABLE public.auctions_category OWNER TO django_user;

--
-- Name: auctions_item; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auctions_item (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text NOT NULL,
    image_urls character varying(200)[] NOT NULL,
    weight numeric(10,2),
    dimensions character varying(100),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    category_id uuid NOT NULL,
    owner_id uuid NOT NULL
);


ALTER TABLE public.auctions_item OWNER TO django_user;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO django_user;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO django_user;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO django_user;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id uuid NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO django_user;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO django_user;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO django_user;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO django_user;

--
-- Name: notifications_notification; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.notifications_notification (
    id uuid NOT NULL,
    notification_type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    message text NOT NULL,
    related_object_id uuid,
    related_object_type character varying(50),
    is_read boolean NOT NULL,
    priority character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    recipient_id uuid NOT NULL
);


ALTER TABLE public.notifications_notification OWNER TO django_user;

--
-- Name: notifications_notificationpreference; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.notifications_notificationpreference (
    id uuid NOT NULL,
    bid_notifications boolean NOT NULL,
    outbid_notifications boolean NOT NULL,
    auction_won_notifications boolean NOT NULL,
    auction_ended_notifications boolean NOT NULL,
    payment_notifications boolean NOT NULL,
    admin_notifications boolean NOT NULL,
    preferred_channels jsonb NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.notifications_notificationpreference OWNER TO django_user;

--
-- Name: token_blacklist_blacklistedtoken; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.token_blacklist_blacklistedtoken (
    id bigint NOT NULL,
    blacklisted_at timestamp with time zone NOT NULL,
    token_id bigint NOT NULL
);


ALTER TABLE public.token_blacklist_blacklistedtoken OWNER TO django_user;

--
-- Name: token_blacklist_blacklistedtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.token_blacklist_blacklistedtoken ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.token_blacklist_blacklistedtoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: token_blacklist_outstandingtoken; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.token_blacklist_outstandingtoken (
    id bigint NOT NULL,
    token text NOT NULL,
    created_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    user_id uuid,
    jti character varying(255) NOT NULL
);


ALTER TABLE public.token_blacklist_outstandingtoken OWNER TO django_user;

--
-- Name: token_blacklist_outstandingtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: django_user
--

ALTER TABLE public.token_blacklist_outstandingtoken ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.token_blacklist_outstandingtoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: transactions_autobid; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.transactions_autobid (
    id uuid NOT NULL,
    max_amount numeric(12,2) NOT NULL,
    bid_increment numeric(8,2) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    auction_id uuid NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.transactions_autobid OWNER TO django_user;

--
-- Name: transactions_transaction; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.transactions_transaction (
    id uuid NOT NULL,
    transaction_type character varying(20) NOT NULL,
    amount numeric(12,2) NOT NULL,
    status character varying(20) NOT NULL,
    reference character varying(255),
    reference_id uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    payment_method_id uuid,
    user_id uuid NOT NULL
);


ALTER TABLE public.transactions_transaction OWNER TO django_user;

--
-- Name: transactions_transactionlog; Type: TABLE; Schema: public; Owner: django_user
--

CREATE TABLE public.transactions_transactionlog (
    id uuid NOT NULL,
    action character varying(100) NOT NULL,
    status_before character varying(20),
    status_after character varying(20),
    "timestamp" timestamp with time zone NOT NULL,
    details jsonb NOT NULL,
    transaction_id uuid NOT NULL
);


ALTER TABLE public.transactions_transactionlog OWNER TO django_user;

--
-- Data for Name: accounts_address; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_address (id, address_line1, address_line2, city, state, postal_code, country, is_default, created_at, updated_at, user_id) FROM stdin;
\.


--
-- Data for Name: accounts_paymentmethod; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_paymentmethod (id, payment_type, provider, account_identifier, is_default, created_at, user_id) FROM stdin;
\.


--
-- Data for Name: accounts_user; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_user (password, last_login, is_superuser, is_staff, date_joined, id, email, first_name, last_name, phone_number, role, is_active, signup_datetime, last_login_datetime) FROM stdin;
\.


--
-- Data for Name: accounts_user_groups; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: accounts_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: accounts_wallet; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.accounts_wallet (id, balance, created_at, updated_at, user_id, held_balance, pending_balance) FROM stdin;
\.


--
-- Data for Name: auctions_auction; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auctions_auction (id, title, description, starting_price, reserve_price, buy_now_price, start_time, end_time, status, auction_type, created_at, updated_at, seller_id, item_id) FROM stdin;
\.


--
-- Data for Name: auctions_auctionwatch; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auctions_auctionwatch (id, created_at, auction_id, user_id) FROM stdin;
\.


--
-- Data for Name: auctions_bid; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auctions_bid (id, amount, "timestamp", status, auction_id, bidder_id) FROM stdin;
\.


--
-- Data for Name: auctions_category; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auctions_category (id, name, description, parent_id) FROM stdin;
\.


--
-- Data for Name: auctions_item; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auctions_item (id, name, description, image_urls, weight, dimensions, created_at, updated_at, category_id, owner_id) FROM stdin;
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add content type	4	add_contenttype
14	Can change content type	4	change_contenttype
15	Can delete content type	4	delete_contenttype
16	Can view content type	4	view_contenttype
17	Can add session	5	add_session
18	Can change session	5	change_session
19	Can delete session	5	delete_session
20	Can view session	5	view_session
21	Can add blacklisted token	6	add_blacklistedtoken
22	Can change blacklisted token	6	change_blacklistedtoken
23	Can delete blacklisted token	6	delete_blacklistedtoken
24	Can view blacklisted token	6	view_blacklistedtoken
25	Can add outstanding token	7	add_outstandingtoken
26	Can change outstanding token	7	change_outstandingtoken
27	Can delete outstanding token	7	delete_outstandingtoken
28	Can view outstanding token	7	view_outstandingtoken
29	Can add user	8	add_user
30	Can change user	8	change_user
31	Can delete user	8	delete_user
32	Can view user	8	view_user
33	Can add address	9	add_address
34	Can change address	9	change_address
35	Can delete address	9	delete_address
36	Can view address	9	view_address
37	Can add payment method	10	add_paymentmethod
38	Can change payment method	10	change_paymentmethod
39	Can delete payment method	10	delete_paymentmethod
40	Can view payment method	10	view_paymentmethod
41	Can add wallet	11	add_wallet
42	Can change wallet	11	change_wallet
43	Can delete wallet	11	delete_wallet
44	Can view wallet	11	view_wallet
45	Can add auction	12	add_auction
46	Can change auction	12	change_auction
47	Can delete auction	12	delete_auction
48	Can view auction	12	view_auction
49	Can add bid	13	add_bid
50	Can change bid	13	change_bid
51	Can delete bid	13	delete_bid
52	Can view bid	13	view_bid
53	Can add category	14	add_category
54	Can change category	14	change_category
55	Can delete category	14	delete_category
56	Can view category	14	view_category
57	Can add item	15	add_item
58	Can change item	15	change_item
59	Can delete item	15	delete_item
60	Can view item	15	view_item
61	Can add auction watch	16	add_auctionwatch
62	Can change auction watch	16	change_auctionwatch
63	Can delete auction watch	16	delete_auctionwatch
64	Can view auction watch	16	view_auctionwatch
65	Can add notification preference	17	add_notificationpreference
66	Can change notification preference	17	change_notificationpreference
67	Can delete notification preference	17	delete_notificationpreference
68	Can view notification preference	17	view_notificationpreference
69	Can add notification	18	add_notification
70	Can change notification	18	change_notification
71	Can delete notification	18	delete_notification
72	Can view notification	18	view_notification
73	Can add transaction	19	add_transaction
74	Can change transaction	19	change_transaction
75	Can delete transaction	19	delete_transaction
76	Can view transaction	19	view_transaction
77	Can add transaction log	20	add_transactionlog
78	Can change transaction log	20	change_transactionlog
79	Can delete transaction log	20	delete_transactionlog
80	Can view transaction log	20	view_transactionlog
81	Can add auto bid	21	add_autobid
82	Can change auto bid	21	change_autobid
83	Can delete auto bid	21	delete_autobid
84	Can view auto bid	21	view_autobid
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	contenttypes	contenttype
5	sessions	session
6	token_blacklist	blacklistedtoken
7	token_blacklist	outstandingtoken
8	accounts	user
9	accounts	address
10	accounts	paymentmethod
11	accounts	wallet
12	auctions	auction
13	auctions	bid
14	auctions	category
15	auctions	item
16	auctions	auctionwatch
17	notifications	notificationpreference
18	notifications	notification
19	transactions	transaction
20	transactions	transactionlog
21	transactions	autobid
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-03-26 19:16:45.955056+00
2	contenttypes	0002_remove_content_type_name	2025-03-26 19:16:45.96662+00
3	auth	0001_initial	2025-03-26 19:16:46.006977+00
4	auth	0002_alter_permission_name_max_length	2025-03-26 19:16:46.017569+00
5	auth	0003_alter_user_email_max_length	2025-03-26 19:16:46.026204+00
6	auth	0004_alter_user_username_opts	2025-03-26 19:16:46.035166+00
7	auth	0005_alter_user_last_login_null	2025-03-26 19:16:46.04712+00
8	auth	0006_require_contenttypes_0002	2025-03-26 19:16:46.052171+00
9	auth	0007_alter_validators_add_error_messages	2025-03-26 19:16:46.063098+00
10	auth	0008_alter_user_username_max_length	2025-03-26 19:16:46.073875+00
11	auth	0009_alter_user_last_name_max_length	2025-03-26 19:16:46.082685+00
12	auth	0010_alter_group_name_max_length	2025-03-26 19:16:46.094604+00
13	auth	0011_update_proxy_permissions	2025-03-26 19:16:46.102608+00
14	auth	0012_alter_user_first_name_max_length	2025-03-26 19:16:46.112085+00
15	accounts	0001_initial	2025-03-26 19:16:46.179044+00
16	accounts	0002_add_uuid_extension	2025-03-26 19:16:46.188438+00
17	accounts	0003_wallet	2025-03-26 19:16:46.205757+00
18	accounts	0004_wallet_held_balance_wallet_pending_balance	2025-03-26 19:16:46.226689+00
19	admin	0001_initial	2025-03-26 19:16:46.249182+00
20	admin	0002_logentry_remove_auto_add	2025-03-26 19:16:46.259242+00
21	admin	0003_logentry_add_action_flag_choices	2025-03-26 19:16:46.270065+00
22	auctions	0001_initial	2025-03-26 19:16:46.375721+00
23	transactions	0001_initial	2025-03-26 19:16:46.518688+00
24	notifications	0001_initial	2025-03-26 19:16:46.575658+00
25	auctions	0002_add_database_triggers	2025-03-26 19:16:46.591991+00
26	auctions	0003_alter_auction_status	2025-03-26 19:16:46.614496+00
27	auctions	0004_fix_wallet_table_references	2025-03-26 19:16:46.624438+00
28	auctions	0005_fix_accountbalance_references	2025-03-26 19:16:46.630691+00
29	auctions	0006_fix_bid_status_trigger	2025-03-26 19:16:46.636311+00
30	notifications	0002_notification_notificatio_related_e0a5d0_idx	2025-03-26 19:16:46.660115+00
31	sessions	0001_initial	2025-03-26 19:16:46.67411+00
32	token_blacklist	0001_initial	2025-03-26 19:16:46.746889+00
33	token_blacklist	0002_outstandingtoken_jti_hex	2025-03-26 19:16:46.771093+00
34	token_blacklist	0003_auto_20171017_2007	2025-03-26 19:16:46.797465+00
35	token_blacklist	0004_auto_20171017_2013	2025-03-26 19:16:46.822876+00
36	token_blacklist	0005_remove_outstandingtoken_jti	2025-03-26 19:16:46.847182+00
37	token_blacklist	0006_auto_20171017_2113	2025-03-26 19:16:46.86987+00
38	token_blacklist	0007_auto_20171017_2214	2025-03-26 19:16:46.924425+00
39	token_blacklist	0008_migrate_to_bigautofield	2025-03-26 19:16:46.984873+00
40	token_blacklist	0010_fix_migrate_to_bigautofield	2025-03-26 19:16:47.024652+00
41	token_blacklist	0011_linearizes_history	2025-03-26 19:16:47.028887+00
42	token_blacklist	0012_alter_outstandingtoken_user	2025-03-26 19:16:47.053074+00
43	transactions	0002_remove_wallet_user_delete_accountbalance_and_more	2025-03-26 19:16:47.089356+00
44	transactions	0003_disable_payment_notification_trigger	2025-03-26 19:16:47.094447+00
45	transactions	0004_alter_autobid_options_alter_transactionlog_options_and_more	2025-03-26 19:16:47.407129+00
46	transactions	0002_disable_payment_notification_trigger	2025-03-26 19:16:47.422191+00
47	transactions	0005_merge_20250318_1610	2025-03-26 19:16:47.425073+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
\.


--
-- Data for Name: notifications_notification; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.notifications_notification (id, notification_type, title, message, related_object_id, related_object_type, is_read, priority, created_at, recipient_id) FROM stdin;
\.


--
-- Data for Name: notifications_notificationpreference; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.notifications_notificationpreference (id, bid_notifications, outbid_notifications, auction_won_notifications, auction_ended_notifications, payment_notifications, admin_notifications, preferred_channels, user_id) FROM stdin;
\.


--
-- Data for Name: token_blacklist_blacklistedtoken; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.token_blacklist_blacklistedtoken (id, blacklisted_at, token_id) FROM stdin;
\.


--
-- Data for Name: token_blacklist_outstandingtoken; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.token_blacklist_outstandingtoken (id, token, created_at, expires_at, user_id, jti) FROM stdin;
\.


--
-- Data for Name: transactions_autobid; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.transactions_autobid (id, max_amount, bid_increment, is_active, created_at, updated_at, auction_id, user_id) FROM stdin;
\.


--
-- Data for Name: transactions_transaction; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.transactions_transaction (id, transaction_type, amount, status, reference, reference_id, created_at, updated_at, completed_at, payment_method_id, user_id) FROM stdin;
\.


--
-- Data for Name: transactions_transactionlog; Type: TABLE DATA; Schema: public; Owner: django_user
--

COPY public.transactions_transactionlog (id, action, status_before, status_after, "timestamp", details, transaction_id) FROM stdin;
\.


--
-- Name: accounts_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.accounts_user_groups_id_seq', 1, false);


--
-- Name: accounts_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.accounts_user_user_permissions_id_seq', 1, false);


--
-- Name: auctions_auctionwatch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.auctions_auctionwatch_id_seq', 1, false);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 84, true);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 21, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 47, true);


--
-- Name: token_blacklist_blacklistedtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.token_blacklist_blacklistedtoken_id_seq', 1, false);


--
-- Name: token_blacklist_outstandingtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: django_user
--

SELECT pg_catalog.setval('public.token_blacklist_outstandingtoken_id_seq', 2, true);


--
-- Name: accounts_address accounts_address_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_address
    ADD CONSTRAINT accounts_address_pkey PRIMARY KEY (id);


--
-- Name: accounts_paymentmethod accounts_paymentmethod_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_paymentmethod
    ADD CONSTRAINT accounts_paymentmethod_pkey PRIMARY KEY (id);


--
-- Name: accounts_user accounts_user_email_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user
    ADD CONSTRAINT accounts_user_email_key UNIQUE (email);


--
-- Name: accounts_user_groups accounts_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_pkey PRIMARY KEY (id);


--
-- Name: accounts_user_groups accounts_user_groups_user_id_group_id_59c0b32f_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_user_id_group_id_59c0b32f_uniq UNIQUE (user_id, group_id);


--
-- Name: accounts_user accounts_user_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user
    ADD CONSTRAINT accounts_user_pkey PRIMARY KEY (id);


--
-- Name: accounts_user_user_permissions accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq UNIQUE (user_id, permission_id);


--
-- Name: accounts_user_user_permissions accounts_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: accounts_wallet accounts_wallet_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_wallet
    ADD CONSTRAINT accounts_wallet_pkey PRIMARY KEY (id);


--
-- Name: accounts_wallet accounts_wallet_user_id_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_wallet
    ADD CONSTRAINT accounts_wallet_user_id_key UNIQUE (user_id);


--
-- Name: auctions_auction auctions_auction_item_id_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auction
    ADD CONSTRAINT auctions_auction_item_id_key UNIQUE (item_id);


--
-- Name: auctions_auction auctions_auction_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auction
    ADD CONSTRAINT auctions_auction_pkey PRIMARY KEY (id);


--
-- Name: auctions_auctionwatch auctions_auctionwatch_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auctionwatch
    ADD CONSTRAINT auctions_auctionwatch_pkey PRIMARY KEY (id);


--
-- Name: auctions_auctionwatch auctions_auctionwatch_user_id_auction_id_ceec04eb_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auctionwatch
    ADD CONSTRAINT auctions_auctionwatch_user_id_auction_id_ceec04eb_uniq UNIQUE (user_id, auction_id);


--
-- Name: auctions_bid auctions_bid_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_bid
    ADD CONSTRAINT auctions_bid_pkey PRIMARY KEY (id);


--
-- Name: auctions_category auctions_category_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_category
    ADD CONSTRAINT auctions_category_pkey PRIMARY KEY (id);


--
-- Name: auctions_item auctions_item_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_item
    ADD CONSTRAINT auctions_item_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: notifications_notification notifications_notification_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.notifications_notification
    ADD CONSTRAINT notifications_notification_pkey PRIMARY KEY (id);


--
-- Name: notifications_notificationpreference notifications_notificationpreference_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.notifications_notificationpreference
    ADD CONSTRAINT notifications_notificationpreference_pkey PRIMARY KEY (id);


--
-- Name: notifications_notificationpreference notifications_notificationpreference_user_id_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.notifications_notificationpreference
    ADD CONSTRAINT notifications_notificationpreference_user_id_key UNIQUE (user_id);


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_blacklistedtoken
    ADD CONSTRAINT token_blacklist_blacklistedtoken_pkey PRIMARY KEY (id);


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_token_id_key; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_blacklistedtoken
    ADD CONSTRAINT token_blacklist_blacklistedtoken_token_id_key UNIQUE (token_id);


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_outstandingtoken
    ADD CONSTRAINT token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq UNIQUE (jti);


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outstandingtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_outstandingtoken
    ADD CONSTRAINT token_blacklist_outstandingtoken_pkey PRIMARY KEY (id);


--
-- Name: transactions_autobid transactions_autobid_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_autobid
    ADD CONSTRAINT transactions_autobid_pkey PRIMARY KEY (id);


--
-- Name: transactions_autobid transactions_autobid_user_id_auction_id_211ce9e1_uniq; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_autobid
    ADD CONSTRAINT transactions_autobid_user_id_auction_id_211ce9e1_uniq UNIQUE (user_id, auction_id);


--
-- Name: transactions_transaction transactions_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_transaction
    ADD CONSTRAINT transactions_transaction_pkey PRIMARY KEY (id);


--
-- Name: transactions_transactionlog transactions_transactionlog_pkey; Type: CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_transactionlog
    ADD CONSTRAINT transactions_transactionlog_pkey PRIMARY KEY (id);


--
-- Name: accounts_address_user_id_c8c74ddf; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_address_user_id_c8c74ddf ON public.accounts_address USING btree (user_id);


--
-- Name: accounts_paymentmethod_user_id_d6721175; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_paymentmethod_user_id_d6721175 ON public.accounts_paymentmethod USING btree (user_id);


--
-- Name: accounts_user_email_b2644a56_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_user_email_b2644a56_like ON public.accounts_user USING btree (email varchar_pattern_ops);


--
-- Name: accounts_user_groups_group_id_bd11a704; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_user_groups_group_id_bd11a704 ON public.accounts_user_groups USING btree (group_id);


--
-- Name: accounts_user_groups_user_id_52b62117; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_user_groups_user_id_52b62117 ON public.accounts_user_groups USING btree (user_id);


--
-- Name: accounts_user_user_permissions_permission_id_113bb443; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_user_user_permissions_permission_id_113bb443 ON public.accounts_user_user_permissions USING btree (permission_id);


--
-- Name: accounts_user_user_permissions_user_id_e4f0a161; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX accounts_user_user_permissions_user_id_e4f0a161 ON public.accounts_user_user_permissions USING btree (user_id);


--
-- Name: auctions_auction_seller_id_e503b3cb; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_auction_seller_id_e503b3cb ON public.auctions_auction USING btree (seller_id);


--
-- Name: auctions_auctionwatch_auction_id_5e8a6978; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_auctionwatch_auction_id_5e8a6978 ON public.auctions_auctionwatch USING btree (auction_id);


--
-- Name: auctions_auctionwatch_user_id_bf9e4dbd; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_auctionwatch_user_id_bf9e4dbd ON public.auctions_auctionwatch USING btree (user_id);


--
-- Name: auctions_bid_auction_id_e2ac2714; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_bid_auction_id_e2ac2714 ON public.auctions_bid USING btree (auction_id);


--
-- Name: auctions_bid_bidder_id_caac8a93; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_bid_bidder_id_caac8a93 ON public.auctions_bid USING btree (bidder_id);


--
-- Name: auctions_category_parent_id_f15b4ad5; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_category_parent_id_f15b4ad5 ON public.auctions_category USING btree (parent_id);


--
-- Name: auctions_item_category_id_a9424adf; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_item_category_id_a9424adf ON public.auctions_item USING btree (category_id);


--
-- Name: auctions_item_owner_id_e5c9566a; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auctions_item_owner_id_e5c9566a ON public.auctions_item USING btree (owner_id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: notificatio_notific_f2898f_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX notificatio_notific_f2898f_idx ON public.notifications_notification USING btree (notification_type);


--
-- Name: notificatio_recipie_4e3567_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX notificatio_recipie_4e3567_idx ON public.notifications_notification USING btree (recipient_id, is_read);


--
-- Name: notificatio_related_e0a5d0_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX notificatio_related_e0a5d0_idx ON public.notifications_notification USING btree (related_object_id, related_object_type);


--
-- Name: notifications_notification_recipient_id_d055f3f0; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX notifications_notification_recipient_id_d055f3f0 ON public.notifications_notification USING btree (recipient_id);


--
-- Name: token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like ON public.token_blacklist_outstandingtoken USING btree (jti varchar_pattern_ops);


--
-- Name: token_blacklist_outstandingtoken_user_id_83bc629a; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX token_blacklist_outstandingtoken_user_id_83bc629a ON public.token_blacklist_outstandingtoken USING btree (user_id);


--
-- Name: transaction_referen_1bb812_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transaction_referen_1bb812_idx ON public.transactions_transaction USING btree (reference_id);


--
-- Name: transaction_status_d2f80b_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transaction_status_d2f80b_idx ON public.transactions_transaction USING btree (status, created_at);


--
-- Name: transaction_user_id_98a6b3_idx; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transaction_user_id_98a6b3_idx ON public.transactions_transaction USING btree (user_id, transaction_type);


--
-- Name: transactions_autobid_auction_id_aaf8d097; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_autobid_auction_id_aaf8d097 ON public.transactions_autobid USING btree (auction_id);


--
-- Name: transactions_autobid_user_id_5bce86df; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_autobid_user_id_5bce86df ON public.transactions_autobid USING btree (user_id);


--
-- Name: transactions_transaction_payment_method_id_6d18e334; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_payment_method_id_6d18e334 ON public.transactions_transaction USING btree (payment_method_id);


--
-- Name: transactions_transaction_status_e57b788b; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_status_e57b788b ON public.transactions_transaction USING btree (status);


--
-- Name: transactions_transaction_status_e57b788b_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_status_e57b788b_like ON public.transactions_transaction USING btree (status varchar_pattern_ops);


--
-- Name: transactions_transaction_transaction_type_22ae98e2; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_transaction_type_22ae98e2 ON public.transactions_transaction USING btree (transaction_type);


--
-- Name: transactions_transaction_transaction_type_22ae98e2_like; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_transaction_type_22ae98e2_like ON public.transactions_transaction USING btree (transaction_type varchar_pattern_ops);


--
-- Name: transactions_transaction_user_id_b9ecc248; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transaction_user_id_b9ecc248 ON public.transactions_transaction USING btree (user_id);


--
-- Name: transactions_transactionlog_transaction_id_951d1ff5; Type: INDEX; Schema: public; Owner: django_user
--

CREATE INDEX transactions_transactionlog_transaction_id_951d1ff5 ON public.transactions_transactionlog USING btree (transaction_id);


--
-- Name: auctions_bid auction_extend_time_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER auction_extend_time_trigger AFTER INSERT ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.extend_auction_time();


--
-- Name: auctions_auction auction_status_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER auction_status_trigger AFTER UPDATE OF status ON public.auctions_auction FOR EACH ROW EXECUTE FUNCTION public.handle_auction_status_change();


--
-- Name: auctions_auction auction_status_update_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER auction_status_update_trigger BEFORE UPDATE ON public.auctions_auction FOR EACH ROW EXECUTE FUNCTION public.update_auction_status();


--
-- Name: auctions_bid autobid_processing_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER autobid_processing_trigger AFTER INSERT ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.process_autobids();


--
-- Name: auctions_bid autobid_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER autobid_trigger AFTER INSERT OR UPDATE ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.process_autobid();


--
-- Name: auctions_bid bid_status_update_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER bid_status_update_trigger AFTER INSERT ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.handle_new_bid();


--
-- Name: auctions_bid bid_transaction_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER bid_transaction_trigger AFTER INSERT OR UPDATE ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.create_bid_transactions();


--
-- Name: auctions_bid buy_now_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER buy_now_trigger BEFORE INSERT ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.process_buy_now();


--
-- Name: auctions_bid outbid_notification_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER outbid_notification_trigger AFTER INSERT ON public.auctions_bid FOR EACH ROW EXECUTE FUNCTION public.notify_outbid_users();


--
-- Name: auctions_bid outbid_refund_trigger; Type: TRIGGER; Schema: public; Owner: django_user
--

CREATE TRIGGER outbid_refund_trigger AFTER UPDATE ON public.auctions_bid FOR EACH ROW WHEN ((((new.status)::text = 'outbid'::text) AND ((old.status)::text = 'active'::text))) EXECUTE FUNCTION public.handle_outbid_wallet_refund();


--
-- Name: accounts_address accounts_address_user_id_c8c74ddf_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_address
    ADD CONSTRAINT accounts_address_user_id_c8c74ddf_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_paymentmethod accounts_paymentmethod_user_id_d6721175_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_paymentmethod
    ADD CONSTRAINT accounts_paymentmethod_user_id_d6721175_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_groups accounts_user_groups_group_id_bd11a704_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_group_id_bd11a704_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_groups accounts_user_groups_user_id_52b62117_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_user_id_52b62117_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_user_permissions accounts_user_user_p_permission_id_113bb443_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_p_permission_id_113bb443_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_user_permissions accounts_user_user_p_user_id_e4f0a161_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_p_user_id_e4f0a161_fk_accounts_ FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_wallet accounts_wallet_user_id_e646a316_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.accounts_wallet
    ADD CONSTRAINT accounts_wallet_user_id_e646a316_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_auction auctions_auction_item_id_4c12d10c_fk_auctions_item_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auction
    ADD CONSTRAINT auctions_auction_item_id_4c12d10c_fk_auctions_item_id FOREIGN KEY (item_id) REFERENCES public.auctions_item(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_auction auctions_auction_seller_id_e503b3cb_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auction
    ADD CONSTRAINT auctions_auction_seller_id_e503b3cb_fk_accounts_user_id FOREIGN KEY (seller_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_auctionwatch auctions_auctionwatc_auction_id_5e8a6978_fk_auctions_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auctionwatch
    ADD CONSTRAINT auctions_auctionwatc_auction_id_5e8a6978_fk_auctions_ FOREIGN KEY (auction_id) REFERENCES public.auctions_auction(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_auctionwatch auctions_auctionwatch_user_id_bf9e4dbd_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_auctionwatch
    ADD CONSTRAINT auctions_auctionwatch_user_id_bf9e4dbd_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_bid auctions_bid_auction_id_e2ac2714_fk_auctions_auction_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_bid
    ADD CONSTRAINT auctions_bid_auction_id_e2ac2714_fk_auctions_auction_id FOREIGN KEY (auction_id) REFERENCES public.auctions_auction(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_bid auctions_bid_bidder_id_caac8a93_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_bid
    ADD CONSTRAINT auctions_bid_bidder_id_caac8a93_fk_accounts_user_id FOREIGN KEY (bidder_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_category auctions_category_parent_id_f15b4ad5_fk_auctions_category_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_category
    ADD CONSTRAINT auctions_category_parent_id_f15b4ad5_fk_auctions_category_id FOREIGN KEY (parent_id) REFERENCES public.auctions_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_item auctions_item_category_id_a9424adf_fk_auctions_category_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_item
    ADD CONSTRAINT auctions_item_category_id_a9424adf_fk_auctions_category_id FOREIGN KEY (category_id) REFERENCES public.auctions_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auctions_item auctions_item_owner_id_e5c9566a_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auctions_item
    ADD CONSTRAINT auctions_item_owner_id_e5c9566a_fk_accounts_user_id FOREIGN KEY (owner_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: notifications_notification notifications_notifi_recipient_id_d055f3f0_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.notifications_notification
    ADD CONSTRAINT notifications_notifi_recipient_id_d055f3f0_fk_accounts_ FOREIGN KEY (recipient_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: notifications_notificationpreference notifications_notifi_user_id_7cfb3d3a_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.notifications_notificationpreference
    ADD CONSTRAINT notifications_notifi_user_id_7cfb3d3a_fk_accounts_ FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_blacklistedtoken
    ADD CONSTRAINT token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk FOREIGN KEY (token_id) REFERENCES public.token_blacklist_outstandingtoken(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outs_user_id_83bc629a_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.token_blacklist_outstandingtoken
    ADD CONSTRAINT token_blacklist_outs_user_id_83bc629a_fk_accounts_ FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transactions_autobid transactions_autobid_auction_id_aaf8d097_fk_auctions_auction_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_autobid
    ADD CONSTRAINT transactions_autobid_auction_id_aaf8d097_fk_auctions_auction_id FOREIGN KEY (auction_id) REFERENCES public.auctions_auction(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transactions_autobid transactions_autobid_user_id_5bce86df_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_autobid
    ADD CONSTRAINT transactions_autobid_user_id_5bce86df_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transactions_transaction transactions_transac_payment_method_id_6d18e334_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_transaction
    ADD CONSTRAINT transactions_transac_payment_method_id_6d18e334_fk_accounts_ FOREIGN KEY (payment_method_id) REFERENCES public.accounts_paymentmethod(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transactions_transactionlog transactions_transac_transaction_id_951d1ff5_fk_transacti; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_transactionlog
    ADD CONSTRAINT transactions_transac_transaction_id_951d1ff5_fk_transacti FOREIGN KEY (transaction_id) REFERENCES public.transactions_transaction(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: transactions_transaction transactions_transaction_user_id_b9ecc248_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django_user
--

ALTER TABLE ONLY public.transactions_transaction
    ADD CONSTRAINT transactions_transaction_user_id_b9ecc248_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

