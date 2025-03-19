from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0005_fix_accountbalance_references"),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Update the trigger that handles new bids to properly mark previous bids as outbid
            CREATE OR REPLACE FUNCTION handle_new_bid()
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;

            -- Create a trigger for the function if it doesn't exist yet
            DROP TRIGGER IF EXISTS bid_status_update_trigger ON auctions_bid;
            CREATE TRIGGER bid_status_update_trigger
            AFTER INSERT ON auctions_bid
            FOR EACH ROW
            EXECUTE FUNCTION handle_new_bid();
            """,
            """
            -- Reverse SQL to clean up
            DROP TRIGGER IF EXISTS bid_status_update_trigger ON auctions_bid;
            DROP FUNCTION IF EXISTS handle_new_bid();
            """,
        ),
    ]
