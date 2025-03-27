from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0001_initial"),
        ("notifications", "0001_initial"),
        ("transactions", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- =============================================
            -- 1. OUTBID NOTIFICATION TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION notify_outbid_users()
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER outbid_notification_trigger
            AFTER INSERT ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION notify_outbid_users();

            -- =============================================
            -- 2. AUCTION STATUS CHANGE TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION handle_auction_status_change()
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER auction_status_trigger
            AFTER UPDATE OF status ON auctions_auction
            FOR EACH ROW
            EXECUTE FUNCTION handle_auction_status_change();

            -- =============================================
            -- 3. AUTOBID PROCESSING TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION process_autobids()
            RETURNS TRIGGER AS $$
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
                    JOIN transactions_wallet w ON w.user_id = ab.user_id
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
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER autobid_processing_trigger
            AFTER INSERT ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION process_autobids();

            -- =============================================
            -- 4. BID HOLD TRANSACTION TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION create_bid_transactions()
            RETURNS TRIGGER AS $$
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
                    
                    -- Update wallet/account balance
                    UPDATE transactions_wallet
                    SET balance = balance - NEW.amount
                    WHERE user_id = NEW.bidder_id;
                    
                    -- Also update account balance if it exists
                    UPDATE transactions_accountbalance
                    SET available_balance = available_balance - NEW.amount,
                        held_balance = held_balance + NEW.amount,
                        last_updated = NOW()
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
                        UPDATE transactions_wallet
                        SET balance = balance + NEW.amount
                        WHERE user_id = NEW.bidder_id;
                        
                        -- Update account balance if it exists
                        UPDATE transactions_accountbalance
                        SET available_balance = available_balance + NEW.amount,
                            held_balance = held_balance - NEW.amount,
                            last_updated = NOW()
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
                        
                        -- Update held_balance
                        UPDATE transactions_accountbalance
                        SET held_balance = held_balance - NEW.amount,
                            last_updated = NOW()
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
                            UPDATE transactions_wallet
                            SET balance = balance + net_seller_amount
                            WHERE user_id = seller_id;
                            
                            -- Update seller account balance
                            UPDATE transactions_accountbalance
                            SET available_balance = available_balance + net_seller_amount,
                                last_updated = NOW()
                            WHERE user_id = seller_id;
                        END;
                    END IF;
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER bid_transaction_trigger
            AFTER INSERT OR UPDATE ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION create_bid_transactions();

            -- =============================================
            -- 5. TRANSACTION PAYMENT NOTIFICATION TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION send_payment_notification()
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER payment_notification_trigger
            AFTER INSERT OR UPDATE ON transactions_transaction
            FOR EACH ROW
            EXECUTE FUNCTION send_payment_notification();

            -- =============================================
            -- 6. BUY NOW TRIGGER
            -- =============================================
            CREATE OR REPLACE FUNCTION process_buy_now()
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER buy_now_trigger
            BEFORE INSERT ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION process_buy_now();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS outbid_notification_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS notify_outbid_users();
            
            DROP TRIGGER IF EXISTS auction_status_trigger ON auctions_auction;
            DROP FUNCTION IF EXISTS handle_auction_status_change();
            
            DROP TRIGGER IF EXISTS autobid_processing_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS process_autobids();
            
            DROP TRIGGER IF EXISTS bid_transaction_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS create_bid_transactions();
            
            DROP TRIGGER IF EXISTS payment_notification_trigger ON transactions_transaction;
            DROP FUNCTION IF EXISTS send_payment_notification();
            
            DROP TRIGGER IF EXISTS buy_now_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS process_buy_now();
            """,
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_auction_status() RETURNS TRIGGER AS $$
            DECLARE
                now_time TIMESTAMP;
                highest_bid_record RECORD;
                notification_id UUID;
                lost_bid RECORD;  -- Add declaration for lost_bid variable
                bid RECORD;       -- Add declaration for bid variable
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
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS auction_status_update_trigger ON auctions_auction;
            CREATE TRIGGER auction_status_update_trigger
            BEFORE UPDATE ON auctions_auction
            FOR EACH ROW
            EXECUTE FUNCTION update_auction_status();
            """,
            """
            DROP TRIGGER IF EXISTS auction_status_update_trigger ON auctions_auction;
            DROP FUNCTION IF EXISTS update_auction_status();
            """,
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION process_autobid() RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS autobid_trigger ON auctions_bid;
            CREATE TRIGGER autobid_trigger
            AFTER INSERT OR UPDATE ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION process_autobid();
            """,
            """
            DROP TRIGGER IF EXISTS autobid_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS process_autobid();
            """,
        ),
        migrations.RunSQL(
            """
            -- Function to extend auction time when bid is placed near end
            CREATE OR REPLACE FUNCTION extend_auction_time() RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS auction_extend_time_trigger ON auctions_bid;
            CREATE TRIGGER auction_extend_time_trigger
            AFTER INSERT ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION extend_auction_time();
            """,
            """
            DROP TRIGGER IF EXISTS auction_extend_time_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS extend_auction_time();
            """,
        ),
        migrations.RunSQL(
            """
            -- Function to handle bid release when outbid
            CREATE OR REPLACE FUNCTION handle_outbid_wallet_refund() RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.status = 'outbid' AND OLD.status = 'active' THEN
                    -- Refund the outbid user's wallet
                    UPDATE accounts_wallet
                    SET balance = balance + OLD.amount
                    WHERE user_id = OLD.bidder_id;
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS outbid_refund_trigger ON auctions_bid;
            CREATE TRIGGER outbid_refund_trigger
            AFTER UPDATE ON auctions_bid
            FOR EACH ROW
            WHEN (NEW.status = 'outbid' AND OLD.status = 'active')
            EXECUTE FUNCTION handle_outbid_wallet_refund();
            """,
            """
            DROP TRIGGER IF EXISTS outbid_refund_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS handle_outbid_wallet_refund();
            """,
        ),
    ]
