from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0003_alter_auction_status"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Update the autobid processing trigger to reference accounts_wallet instead of transactions_wallet
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
            $$ LANGUAGE plpgsql;
            
            -- Update the bid processing trigger to reference accounts_wallet
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
                    UPDATE accounts_wallet
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
                        UPDATE accounts_wallet
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
                            UPDATE accounts_wallet
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
            """,
            reverse_sql="""
            CREATE OR REPLACE FUNCTION process_autobids()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Original function restored in reverse migration
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            CREATE OR REPLACE FUNCTION create_bid_transactions()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Original function restored in reverse migration
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
        ),
        migrations.RunSQL(
            sql="""
            -- Update the auction status update trigger to reference accounts_wallet
            CREATE OR REPLACE FUNCTION update_auction_status() 
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;
            
            -- Update the autobid process trigger to reference accounts_wallet
            CREATE OR REPLACE FUNCTION process_autobid() 
            RETURNS TRIGGER AS $$
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
            """,
            reverse_sql="""
            -- Restore original function definitions as needed
            """,
        ),
    ]
