from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0004_fix_wallet_table_references"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Update the bid transaction trigger to remove references to transactions_accountbalance
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
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="""
            -- This is a placeholder for reverse migration. 
            -- In case of rollback, the original function would be restored through earlier migrations
            """,
        ),
    ]
