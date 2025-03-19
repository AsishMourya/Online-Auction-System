from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0002_remove_wallet_user_delete_accountbalance_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Disable the payment notification trigger that's causing duplicates
            DROP TRIGGER IF EXISTS payment_notification_trigger ON transactions_transaction;
            """,
            """
            -- Re-enable the payment notification trigger if needed
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
            """,
        ),
    ]
