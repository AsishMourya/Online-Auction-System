-- =========================================================================
-- Online Auction System - PostgreSQL Implementation
-- Compatible with Django ORM
-- =========================================================================
-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- -------------------------------------------------------------------------
-- Enum Types
-- -------------------------------------------------------------------------
-- Item condition options
CREATE TYPE item_condition AS ENUM ('New', 'Used', 'Refurbished');
-- Item status options
CREATE TYPE item_status AS ENUM ('Pending', 'Approved', 'Rejected', 'Sold');
-- Auction status options
CREATE TYPE auction_status AS ENUM ('Upcoming', 'Active', 'Ended', 'Cancelled');
-- Auction history action types
CREATE TYPE auction_action AS ENUM (
    'Created',
    'Started',
    'Extended',
    'Ended',
    'Cancelled'
);
-- Bid status options
CREATE TYPE bid_status AS ENUM ('Active', 'Outbid', 'Won');
-- Payment status options
CREATE TYPE payment_status AS ENUM ('Pending', 'Completed', 'Failed', 'Refunded');
-- Shipping status options
CREATE TYPE shipping_status AS ENUM ('Not Shipped', 'Shipped', 'Delivered');
-- Payment type options
CREATE TYPE payment_type AS ENUM (
    'Credit Card',
    'PayPal',
    'Bank Transfer',
    'Cryptocurrency'
);
-- Notification type options
CREATE TYPE notification_type AS ENUM (
    'Outbid',
    'AuctionEnded',
    'ItemSold',
    'BidWon',
    'ItemApproved',
    'ItemRejected',
    'PaymentReceived',
    'PaymentFailed',
    'ItemShipped'
);
-- -------------------------------------------------------------------------
-- Tables
-- -------------------------------------------------------------------------
-- Users table
CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT user_username_key UNIQUE (username),
    CONSTRAINT user_email_key UNIQUE (email),
    CONSTRAINT user_email_valid CHECK (
        email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$'
    )
);
COMMENT ON TABLE "user" IS 'Stores all user information for the auction system';
-- Roles table
CREATE TABLE role (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    description TEXT,
    CONSTRAINT role_name_key UNIQUE (role_name)
);
COMMENT ON TABLE role IS 'Defines roles for role-based access control';
-- Insert default roles
INSERT INTO role (role_name, description)
VALUES (
        'Admin',
        'System administrators with full control'
    ),
    ('Seller', 'Users who can list items for auction'),
    ('Buyer', 'Users who can bid on auctions'),
    (
        'Moderator',
        'Users who can review and approve items'
    );
-- User-Role mapping table
CREATE TABLE user_role (
    user_role_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_role_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT user_role_role_fk FOREIGN KEY (role_id) REFERENCES role (role_id) ON DELETE CASCADE,
    CONSTRAINT user_role_unique UNIQUE (user_id, role_id)
);
COMMENT ON TABLE user_role IS 'Maps users to their assigned roles';
-- Categories table
CREATE TABLE category (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_category_id INTEGER,
    description TEXT,
    CONSTRAINT category_name_key UNIQUE (name),
    CONSTRAINT category_parent_fk FOREIGN KEY (parent_category_id) REFERENCES category (category_id) ON DELETE
    SET NULL
);
COMMENT ON TABLE category IS 'Hierarchical categories for organizing items';
-- Items table
CREATE TABLE item (
    item_id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL,
    condition item_condition NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status item_status NOT NULL DEFAULT 'Pending',
    admin_id INTEGER,
    reject_reason TEXT,
    CONSTRAINT item_seller_fk FOREIGN KEY (seller_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT item_category_fk FOREIGN KEY (category_id) REFERENCES category (category_id) ON DELETE RESTRICT,
    CONSTRAINT item_admin_fk FOREIGN KEY (admin_id) REFERENCES "user" (user_id) ON DELETE
    SET NULL
);
COMMENT ON TABLE item IS 'Stores information about items listed for auction';
-- Item Images table
CREATE TABLE item_image (
    image_id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    image_url VARCHAR(1000) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT item_image_item_fk FOREIGN KEY (item_id) REFERENCES item (item_id) ON DELETE CASCADE
);
-- Add constraint to ensure only one primary image per item
CREATE UNIQUE INDEX item_image_primary_idx ON item_image (item_id)
WHERE is_primary = TRUE;
COMMENT ON TABLE item_image IS 'Stores images associated with auction items';
-- Auctions table
CREATE TABLE auction (
    auction_id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    starting_bid DECIMAL(15, 2) NOT NULL,
    reserve_price DECIMAL(15, 2),
    bid_increment DECIMAL(15, 2) NOT NULL,
    status auction_status NOT NULL DEFAULT 'Upcoming',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extended_count INTEGER NOT NULL DEFAULT 0,
    last_extended_at TIMESTAMP,
    CONSTRAINT auction_item_fk FOREIGN KEY (item_id) REFERENCES item (item_id) ON DELETE CASCADE,
    CONSTRAINT auction_item_unique UNIQUE (item_id),
    CONSTRAINT auction_end_after_start CHECK (end_time > start_time),
    CONSTRAINT auction_positive_bid CHECK (starting_bid > 0),
    CONSTRAINT auction_positive_increment CHECK (bid_increment > 0)
);
COMMENT ON TABLE auction IS 'Manages auction details including timing and bid parameters';
-- Auction History table
CREATE TABLE auction_history (
    history_id SERIAL PRIMARY KEY,
    auction_id INTEGER NOT NULL,
    action auction_action NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    admin_id INTEGER,
    reason TEXT,
    CONSTRAINT auction_history_auction_fk FOREIGN KEY (auction_id) REFERENCES auction (auction_id) ON DELETE CASCADE,
    CONSTRAINT auction_history_admin_fk FOREIGN KEY (admin_id) REFERENCES "user" (user_id) ON DELETE
    SET NULL
);
COMMENT ON TABLE auction_history IS 'Logs all changes to auctions for auditing and dispute resolution';
-- Bids table
CREATE TABLE bid (
    bid_id SERIAL PRIMARY KEY,
    auction_id INTEGER NOT NULL,
    bidder_id INTEGER NOT NULL,
    bid_amount DECIMAL(15, 2) NOT NULL,
    bid_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_auto_bid BOOLEAN NOT NULL DEFAULT FALSE,
    max_auto_bid_amount DECIMAL(15, 2),
    bid_status bid_status NOT NULL DEFAULT 'Active',
    CONSTRAINT bid_auction_fk FOREIGN KEY (auction_id) REFERENCES auction (auction_id) ON DELETE CASCADE,
    CONSTRAINT bid_bidder_fk FOREIGN KEY (bidder_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT bid_positive_amount CHECK (bid_amount > 0)
);
COMMENT ON TABLE bid IS 'Records all bids placed on auctions';
-- Payment Methods table
CREATE TABLE payment_method (
    payment_method_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    payment_type payment_type NOT NULL,
    account_number VARCHAR(255) NOT NULL,
    -- Should be encrypted in application code
    expiry_date DATE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT payment_method_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE
);
-- Add constraint to ensure only one default payment method per user
CREATE UNIQUE INDEX payment_method_default_idx ON payment_method (user_id)
WHERE is_default = TRUE;
COMMENT ON TABLE payment_method IS 'Stores user payment methods';
-- Shipping Addresses table
CREATE TABLE shipping_address (
    address_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT shipping_address_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE
);
-- Add constraint to ensure only one default address per user
CREATE UNIQUE INDEX shipping_address_default_idx ON shipping_address (user_id)
WHERE is_default = TRUE;
COMMENT ON TABLE shipping_address IS 'Stores user shipping addresses';
-- Transactions table
CREATE TABLE transaction (
    transaction_id SERIAL PRIMARY KEY,
    auction_id INTEGER NOT NULL,
    seller_id INTEGER NOT NULL,
    buyer_id INTEGER NOT NULL,
    final_amount DECIMAL(15, 2) NOT NULL,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_status payment_status NOT NULL DEFAULT 'Pending',
    shipping_status shipping_status NOT NULL DEFAULT 'Not Shipped',
    tracking_number VARCHAR(100),
    payment_method_id INTEGER,
    shipping_address_id INTEGER,
    CONSTRAINT transaction_auction_fk FOREIGN KEY (auction_id) REFERENCES auction (auction_id) ON DELETE RESTRICT,
    CONSTRAINT transaction_seller_fk FOREIGN KEY (seller_id) REFERENCES "user" (user_id) ON DELETE RESTRICT,
    CONSTRAINT transaction_buyer_fk FOREIGN KEY (buyer_id) REFERENCES "user" (user_id) ON DELETE RESTRICT,
    CONSTRAINT transaction_payment_method_fk FOREIGN KEY (payment_method_id) REFERENCES payment_method (payment_method_id) ON DELETE
    SET NULL,
        CONSTRAINT transaction_shipping_address_fk FOREIGN KEY (shipping_address_id) REFERENCES shipping_address (address_id) ON DELETE
    SET NULL,
        CONSTRAINT transaction_auction_unique UNIQUE (auction_id),
        CONSTRAINT transaction_positive_amount CHECK (final_amount > 0)
);
COMMENT ON TABLE transaction IS 'Records all completed auction transactions';
-- Feedback table
CREATE TABLE feedback (
    feedback_id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    reviewee_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT feedback_transaction_fk FOREIGN KEY (transaction_id) REFERENCES transaction (transaction_id) ON DELETE CASCADE,
    CONSTRAINT feedback_reviewer_fk FOREIGN KEY (reviewer_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT feedback_reviewee_fk FOREIGN KEY (reviewee_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT feedback_unique_review UNIQUE (transaction_id, reviewer_id),
    CONSTRAINT feedback_rating_range CHECK (
        rating BETWEEN 1 AND 5
    )
);
COMMENT ON TABLE feedback IS 'User feedback after transactions';
-- Notifications table
CREATE TABLE notification (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    type notification_type NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    related_auction_id INTEGER,
    related_item_id INTEGER,
    related_bid_id INTEGER,
    CONSTRAINT notification_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT notification_auction_fk FOREIGN KEY (related_auction_id) REFERENCES auction (auction_id) ON DELETE
    SET NULL,
        CONSTRAINT notification_item_fk FOREIGN KEY (related_item_id) REFERENCES item (item_id) ON DELETE
    SET NULL,
        CONSTRAINT notification_bid_fk FOREIGN KEY (related_bid_id) REFERENCES bid (bid_id) ON DELETE
    SET NULL
);
COMMENT ON TABLE notification IS 'System notifications for users';
-- Watchlist table
CREATE TABLE watchlist (
    watchlist_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    auction_id INTEGER NOT NULL,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT watchlist_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE,
    CONSTRAINT watchlist_auction_fk FOREIGN KEY (auction_id) REFERENCES auction (auction_id) ON DELETE CASCADE,
    CONSTRAINT watchlist_unique UNIQUE (user_id, auction_id)
);
COMMENT ON TABLE watchlist IS 'Tracks auctions users are watching';
-- Audit Log table
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    user_id INTEGER,
    table_affected VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    old_values JSONB,
    new_values JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    CONSTRAINT audit_log_user_fk FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE
    SET NULL
);
COMMENT ON TABLE audit_log IS 'System-wide audit log for tracking all changes';
-- -------------------------------------------------------------------------
-- Indexes
-- -------------------------------------------------------------------------
-- User indexes
CREATE INDEX user_firstname_idx ON "user" (first_name);
CREATE INDEX user_lastname_idx ON "user" (last_name);
CREATE INDEX user_active_idx ON "user" (is_active);
-- User Role indexes
CREATE INDEX user_role_user_idx ON user_role (user_id);
CREATE INDEX user_role_role_idx ON user_role (role_id);
-- Item indexes
CREATE INDEX item_seller_idx ON item (seller_id);
CREATE INDEX item_category_idx ON item (category_id);
CREATE INDEX item_title_idx ON item (title);
CREATE INDEX item_status_idx ON item (status);
CREATE INDEX item_created_idx ON item (created_at);
-- Item Image indexes
CREATE INDEX item_image_item_idx ON item_image (item_id);
CREATE INDEX item_image_primary_flag_idx ON item_image (is_primary);
-- Category indexes
CREATE INDEX category_parent_idx ON category (parent_category_id);
-- Auction indexes
CREATE INDEX auction_item_idx ON auction (item_id);
CREATE INDEX auction_status_idx ON auction (status);
CREATE INDEX auction_start_idx ON auction (start_time);
CREATE INDEX auction_end_idx ON auction (end_time);
-- Auction History indexes
CREATE INDEX auction_history_auction_idx ON auction_history (auction_id);
CREATE INDEX auction_history_timestamp_idx ON auction_history (timestamp);
-- Bid indexes
CREATE INDEX bid_auction_idx ON bid (auction_id);
CREATE INDEX bid_bidder_idx ON bid (bidder_id);
CREATE INDEX bid_amount_idx ON bid (bid_amount);
CREATE INDEX bid_time_idx ON bid (bid_time);
CREATE INDEX bid_status_idx ON bid (bid_status);
-- Transaction indexes
CREATE INDEX transaction_auction_idx ON transaction (auction_id);
CREATE INDEX transaction_seller_idx ON transaction (seller_id);
CREATE INDEX transaction_buyer_idx ON transaction (buyer_id);
CREATE INDEX transaction_date_idx ON transaction (transaction_date);
CREATE INDEX transaction_payment_status_idx ON transaction (payment_status);
CREATE INDEX transaction_shipping_status_idx ON transaction (shipping_status);
-- Payment Method indexes
CREATE INDEX payment_method_user_idx ON payment_method (user_id);
CREATE INDEX payment_method_default_flag_idx ON payment_method (is_default);
-- Shipping Address indexes
CREATE INDEX shipping_address_user_idx ON shipping_address (user_id);
CREATE INDEX shipping_address_country_idx ON shipping_address (country);
CREATE INDEX shipping_address_default_flag_idx ON shipping_address (is_default);
-- Feedback indexes
CREATE INDEX feedback_transaction_idx ON feedback (transaction_id);
CREATE INDEX feedback_reviewer_idx ON feedback (reviewer_id);
CREATE INDEX feedback_reviewee_idx ON feedback (reviewee_id);
CREATE INDEX feedback_created_idx ON feedback (created_at);
-- Notification indexes
CREATE INDEX notification_user_idx ON notification (user_id);
CREATE INDEX notification_type_idx ON notification (type);
CREATE INDEX notification_created_idx ON notification (created_at);
CREATE INDEX notification_read_flag_idx ON notification (is_read);
-- Watchlist indexes
CREATE INDEX watchlist_user_idx ON watchlist (user_id);
CREATE INDEX watchlist_auction_idx ON watchlist (auction_id);
-- Audit Log indexes
CREATE INDEX audit_log_user_idx ON audit_log (user_id);
CREATE INDEX audit_log_action_idx ON audit_log (action);
CREATE INDEX audit_log_table_idx ON audit_log (table_affected);
CREATE INDEX audit_log_record_idx ON audit_log (record_id);
CREATE INDEX audit_log_timestamp_idx ON audit_log (timestamp);
-- -------------------------------------------------------------------------
-- Functions and Triggers
-- -------------------------------------------------------------------------
-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Trigger to update timestamp on user table
CREATE TRIGGER update_user_timestamp BEFORE
UPDATE ON "user" FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- Trigger to update timestamp on item table
CREATE TRIGGER update_item_timestamp BEFORE
UPDATE ON item FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- Trigger to update timestamp on auction table
CREATE TRIGGER update_auction_timestamp BEFORE
UPDATE ON auction FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- Trigger to update timestamp on payment_method table
CREATE TRIGGER update_payment_method_timestamp BEFORE
UPDATE ON payment_method FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- Trigger to update timestamp on shipping_address table
CREATE TRIGGER update_shipping_address_timestamp BEFORE
UPDATE ON shipping_address FOR EACH ROW EXECUTE FUNCTION update_timestamp();
-- Function to automatically log auction status changes
CREATE OR REPLACE FUNCTION log_auction_changes() RETURNS TRIGGER AS $$ BEGIN IF (OLD.status <> NEW.status) THEN
INSERT INTO auction_history (auction_id, action, timestamp)
VALUES (
        NEW.auction_id,
        CASE
            NEW.status
            WHEN 'Upcoming' THEN 'Created'
            WHEN 'Active' THEN 'Started'
            WHEN 'Ended' THEN 'Ended'
            WHEN 'Cancelled' THEN 'Cancelled'
        END,
        CURRENT_TIMESTAMP
    );
END IF;
IF (NEW.extended_count > OLD.extended_count) THEN
INSERT INTO auction_history (auction_id, action, timestamp)
VALUES (NEW.auction_id, 'Extended', CURRENT_TIMESTAMP);
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Trigger to log auction changes
CREATE TRIGGER log_auction_status_changes
AFTER
UPDATE ON auction FOR EACH ROW
    WHEN (
        OLD.status IS DISTINCT
        FROM NEW.status
            OR OLD.extended_count IS DISTINCT
        FROM NEW.extended_count
    ) EXECUTE FUNCTION log_auction_changes();
-- Function to handle new bid placement
CREATE OR REPLACE FUNCTION process_bid() RETURNS TRIGGER AS $$
DECLARE current_highest_bid DECIMAL(15, 2);
current_highest_bidder INTEGER;
min_bid DECIMAL(15, 2);
auc_status auction_status;
BEGIN -- Get auction status
SELECT status INTO auc_status
FROM auction
WHERE auction_id = NEW.auction_id;
-- Check if auction is active
IF auc_status <> 'Active' THEN RAISE EXCEPTION 'Cannot place bid on non-active auction';
END IF;
-- Get current highest bid
SELECT COALESCE(MAX(bid_amount), 0) INTO current_highest_bid
FROM bid
WHERE auction_id = NEW.auction_id
    AND bid_status = 'Active';
-- Get auction's starting bid
SELECT starting_bid,
    bid_increment INTO min_bid,
    min_bid
FROM auction
WHERE auction_id = NEW.auction_id;
-- Calculate minimum required bid
IF current_highest_bid > 0 THEN min_bid := current_highest_bid + (
    SELECT bid_increment
    FROM auction
    WHERE auction_id = NEW.auction_id
);
END IF;
-- Check if bid amount is sufficient
IF NEW.bid_amount < min_bid THEN RAISE EXCEPTION 'Bid amount must be at least %',
min_bid;
END IF;
-- Get current highest bidder
IF current_highest_bid > 0 THEN
SELECT bidder_id INTO current_highest_bidder
FROM bid
WHERE auction_id = NEW.auction_id
    AND bid_status = 'Active'
ORDER BY bid_amount DESC
LIMIT 1;
-- Mark previous highest bid as outbid
UPDATE bid
SET bid_status = 'Outbid'
WHERE auction_id = NEW.auction_id
    AND bid_status = 'Active';
-- Create notification for outbid user
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_bid_id
    )
VALUES (
        current_highest_bidder,
        'You have been outbid on auction #' || NEW.auction_id,
        'Outbid',
        NEW.auction_id,
        (
            SELECT bid_id
            FROM bid
            WHERE bidder_id = current_highest_bidder
                AND auction_id = NEW.auction_id
                AND bid_status = 'Outbid'
            ORDER BY bid_amount DESC
            LIMIT 1
        )
    );
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Trigger to process bids before insertion
CREATE TRIGGER process_new_bid BEFORE
INSERT ON bid FOR EACH ROW EXECUTE FUNCTION process_bid();
-- Function to handle auto-bidding
CREATE OR REPLACE FUNCTION handle_auto_bidding() RETURNS TRIGGER AS $$
DECLARE auto_bid_record RECORD;
current_highest_bid DECIMAL(15, 2);
new_bid_amount DECIMAL(15, 2);
bid_increment DECIMAL(15, 2);
BEGIN -- Only proceed if this is not an auto-generated bid
IF NEW.is_auto_bid = FALSE THEN -- Get bid increment for this auction
SELECT bid_increment INTO bid_increment
FROM auction
WHERE auction_id = NEW.auction_id;
-- Find all active auto-bids for this auction except the one just placed
FOR auto_bid_record IN
SELECT b.bidder_id,
    b.max_auto_bid_amount
FROM bid b
WHERE b.auction_id = NEW.auction_id
    AND b.is_auto_bid = TRUE
    AND b.bidder_id <> NEW.bidder_id
    AND b.max_auto_bid_amount > NEW.bid_amount
ORDER BY b.max_auto_bid_amount DESC,
    b.bid_time ASC
LIMIT 1 LOOP -- Calculate new bid amount (just enough to outbid the current highest)
    new_bid_amount := LEAST(
        auto_bid_record.max_auto_bid_amount, NEW.bid_amount + bid_increment
    );
-- Place auto bid
INSERT INTO bid (
        auction_id,
        bidder_id,
        bid_amount,
        is_auto_bid,
        max_auto_bid_amount,
        bid_status
    )
VALUES (
        NEW.auction_id,
        auto_bid_record.bidder_id,
        new_bid_amount,
        TRUE,
        auto_bid_record.max_auto_bid_amount,
        'Active'
    );
-- Mark the current bid as outbid
UPDATE bid
SET bid_status = 'Outbid'
WHERE bid_id = NEW.bid_id;
-- Create notification for manually outbid user
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_bid_id
    )
VALUES (
        NEW.bidder_id,
        'You have been outbid by an automatic bid on auction #' || NEW.auction_id,
        'Outbid',
        NEW.auction_id,
        NEW.bid_id
    );
EXIT;
-- Only process the highest auto-bid
END LOOP;
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Trigger to handle auto-bidding after a manual bid
CREATE TRIGGER handle_auto_bidding_trigger
AFTER
INSERT ON bid FOR EACH ROW
    WHEN (NEW.bid_status = 'Active') EXECUTE FUNCTION handle_auto_bidding();
-- Function to close auctions automatically
CREATE OR REPLACE FUNCTION close_ended_auctions() RETURNS void AS $$
DECLARE ended_auction RECORD;
highest_bid RECORD;
seller_id INTEGER;
BEGIN FOR ended_auction IN
SELECT auction_id,
    item_id
FROM auction
WHERE status = 'Active'
    AND end_time <= CURRENT_TIMESTAMP LOOP -- Update auction status
UPDATE auction
SET status = 'Ended'
WHERE auction_id = ended_auction.auction_id;
-- Get highest bid
SELECT b.bid_id,
    b.bidder_id,
    b.bid_amount,
    i.seller_id INTO highest_bid
FROM bid b
    JOIN item i ON i.item_id = ended_auction.item_id
WHERE b.auction_id = ended_auction.auction_id
    AND b.bid_status = 'Active'
ORDER BY b.bid_amount DESC
LIMIT 1;
-- If there's a winning bid
IF FOUND THEN -- Update bid status to 'Won'
UPDATE bid
SET bid_status = 'Won'
WHERE bid_id = highest_bid.bid_id;
-- Update item status to 'Sold'
UPDATE item
SET status = 'Sold'
WHERE item_id = ended_auction.item_id;
-- Create transaction record
INSERT INTO transaction (
        auction_id,
        seller_id,
        buyer_id,
        final_amount,
        payment_status,
        shipping_status
    )
VALUES (
        ended_auction.auction_id,
        highest_bid.seller_id,
        highest_bid.bidder_id,
        highest_bid.bid_amount,
        'Pending',
        'Not Shipped'
    );
-- Notify winner
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_bid_id
    )
VALUES (
        highest_bid.bidder_id,
        'Congratulations! You won the auction #' || ended_auction.auction_id,
        'BidWon',
        ended_auction.auction_id,
        highest_bid.bid_id
    );
-- Notify seller
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_item_id
    )
VALUES (
        highest_bid.seller_id,
        'Your item has been sold in auction #' || ended_auction.auction_id,
        'ItemSold',
        ended_auction.auction_id,
        ended_auction.item_id
    );
ELSE -- No bids were placed, notify seller
SELECT seller_id INTO seller_id
FROM item
WHERE item_id = ended_auction.item_id;
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_item_id
    )
VALUES (
        seller_id,
        'Your auction #' || ended_auction.auction_id || ' ended without any bids',
        'AuctionEnded',
        ended_auction.auction_id,
        ended_auction.item_id
    );
END IF;
END LOOP;
END;
$$ LANGUAGE plpgsql;
-- Function to start upcoming auctions
CREATE OR REPLACE FUNCTION start_upcoming_auctions() RETURNS void AS $$ BEGIN
UPDATE auction
SET status = 'Active'
WHERE status = 'Upcoming'
    AND start_time <= CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;
-- Function to generate audit logs
CREATE OR REPLACE FUNCTION audit_trigger_function() RETURNS TRIGGER AS $$
DECLARE v_old_data JSONB;
v_new_data JSONB;
BEGIN IF (TG_OP = 'UPDATE') THEN v_old_data = to_jsonb(OLD);
v_new_data = to_jsonb(NEW);
INSERT INTO audit_log (
        action,
        table_affected,
        record_id,
        old_values,
        new_values
    )
VALUES (
        TG_OP,
        TG_TABLE_NAME::VARCHAR,
        OLD.id,
        v_old_data,
        v_new_data
    );
RETURN NEW;
ELSIF (TG_OP = 'DELETE') THEN v_old_data = to_jsonb(OLD);
INSERT INTO audit_log (
        action,
        table_affected,
        record_id,
        old_values
    )
VALUES (
        TG_OP,
        TG_TABLE_NAME::VARCHAR,
        OLD.id,
        v_old_data
    );
RETURN OLD;
ELSIF (TG_OP = 'INSERT') THEN v_new_data = to_jsonb(NEW);
INSERT INTO audit_log (
        action,
        table_affected,
        record_id,
        new_values
    )
VALUES (
        TG_OP,
        TG_TABLE_NAME::VARCHAR,
        NEW.id,
        v_new_data
    );
RETURN NEW;
ELSE RAISE WARNING '[AUDIT.%] - Other operation detected: %, at %',
TG_TABLE_NAME,
TG_OP,
now();
RETURN NULL;
END IF;
END;
$$ LANGUAGE plpgsql;
-- -------------------------------------------------------------------------
-- Stored Procedures
-- -------------------------------------------------------------------------
-- Procedure to place a bid
CREATE OR REPLACE PROCEDURE place_bid(
        p_auction_id INTEGER,
        p_bidder_id INTEGER,
        p_bid_amount DECIMAL,
        p_is_auto_bid BOOLEAN DEFAULT FALSE,
        p_max_auto_bid_amount DECIMAL DEFAULT NULL
    ) LANGUAGE plpgsql AS $$
DECLARE v_auction_status auction_status;
v_starting_bid DECIMAL;
v_bid_increment DECIMAL;
v_current_highest_bid DECIMAL;
v_seller_id INTEGER;
v_reserve_price DECIMAL;
BEGIN -- Check if auction exists and is active
SELECT a.status,
    a.starting_bid,
    a.bid_increment,
    a.reserve_price,
    i.seller_id INTO v_auction_status,
    v_starting_bid,
    v_bid_increment,
    v_reserve_price,
    v_seller_id
FROM auction a
    JOIN item i ON a.item_id = i.item_id
WHERE a.auction_id = p_auction_id;
IF NOT FOUND THEN RAISE EXCEPTION 'Auction does not exist';
END IF;
IF v_auction_status <> 'Active' THEN RAISE EXCEPTION 'Auction is not active';
END IF;
-- Check if bidder is the seller
IF p_bidder_id = v_seller_id THEN RAISE EXCEPTION 'Seller cannot bid on their own item';
END IF;
-- Get current highest bid
SELECT COALESCE(MAX(bid_amount), 0) INTO v_current_highest_bid
FROM bid
WHERE auction_id = p_auction_id
    AND bid_status = 'Active';
-- Calculate minimum allowed bid
IF v_current_highest_bid > 0 THEN IF p_bid_amount < (v_current_highest_bid + v_bid_increment) THEN RAISE EXCEPTION 'Bid must be at least % higher than current bid',
v_bid_increment;
END IF;
ELSE IF p_bid_amount < v_starting_bid THEN RAISE EXCEPTION 'Bid must be at least the starting bid of %',
v_starting_bid;
END IF;
END IF;
-- Check auto-bid parameters
IF p_is_auto_bid
AND p_max_auto_bid_amount IS NULL THEN RAISE EXCEPTION 'Maximum auto-bid amount must be specified for auto-bidding';
END IF;
IF p_is_auto_bid
AND p_max_auto_bid_amount < p_bid_amount THEN RAISE EXCEPTION 'Maximum auto-bid amount must be greater than or equal to bid amount';
END IF;
-- Insert the bid (triggers will handle the rest)
INSERT INTO bid (
        auction_id,
        bidder_id,
        bid_amount,
        is_auto_bid,
        max_auto_bid_amount
    )
VALUES (
        p_auction_id,
        p_bidder_id,
        p_bid_amount,
        p_is_auto_bid,
        p_max_auto_bid_amount
    );
-- Extend auction if bid is placed in last 5 minutes
PERFORM extend_auction_if_needed(p_auction_id);
COMMIT;
END;
$$;
-- Function to extend auction if bid is placed near end time
CREATE OR REPLACE FUNCTION extend_auction_if_needed(p_auction_id INTEGER) RETURNS void AS $$
DECLARE v_end_time TIMESTAMP;
v_extend_minutes INTEGER := 5;
-- Default extension time in minutes
BEGIN -- Get auction end time
SELECT end_time INTO v_end_time
FROM auction
WHERE auction_id = p_auction_id;
-- If bid is placed within 5 minutes of end time, extend by 5 minutes
IF v_end_time - CURRENT_TIMESTAMP < INTERVAL '5 minutes' THEN
UPDATE auction
SET end_time = end_time + (v_extend_minutes * INTERVAL '1 minute'),
    extended_count = extended_count + 1,
    last_extended_at = CURRENT_TIMESTAMP
WHERE auction_id = p_auction_id;
-- Log the extension
INSERT INTO auction_history (auction_id, action, reason)
VALUES (
        p_auction_id,
        'Extended',
        'Auto-extended due to last-minute bidding'
    );
END IF;
END;
$$ LANGUAGE plpgsql;
-- Procedure to approve an item
CREATE OR REPLACE PROCEDURE approve_item(p_item_id INTEGER, p_admin_id INTEGER) LANGUAGE plpgsql AS $$ BEGIN -- Update item status
UPDATE item
SET status = 'Approved',
    admin_id = p_admin_id,
    updated_at = CURRENT_TIMESTAMP
WHERE item_id = p_item_id
    AND status = 'Pending';
IF NOT FOUND THEN RAISE EXCEPTION 'Item not found or not in pending status';
END IF;
-- Get seller ID
DECLARE v_seller_id INTEGER;
BEGIN
SELECT seller_id INTO v_seller_id
FROM item
WHERE item_id = p_item_id;
-- Notify seller
INSERT INTO notification (user_id, message, type, related_item_id)
VALUES (
        v_seller_id,
        'Your item has been approved and is now listed for auction',
        'ItemApproved',
        p_item_id
    );
END;
COMMIT;
END;
$$;
-- Procedure to reject an item
CREATE OR REPLACE PROCEDURE reject_item(
        p_item_id INTEGER,
        p_admin_id INTEGER,
        p_reject_reason TEXT
    ) LANGUAGE plpgsql AS $$ BEGIN -- Update item status
UPDATE item
SET status = 'Rejected',
    admin_id = p_admin_id,
    reject_reason = p_reject_reason,
    updated_at = CURRENT_TIMESTAMP
WHERE item_id = p_item_id
    AND status = 'Pending';
IF NOT FOUND THEN RAISE EXCEPTION 'Item not found or not in pending status';
END IF;
-- Get seller ID
DECLARE v_seller_id INTEGER;
BEGIN
SELECT seller_id INTO v_seller_id
FROM item
WHERE item_id = p_item_id;
-- Notify seller
INSERT INTO notification (user_id, message, type, related_item_id)
VALUES (
        v_seller_id,
        'Your item has been rejected: ' || p_reject_reason,
        'ItemRejected',
        p_item_id
    );
END;
COMMIT;
END;
$$;
-- Procedure to cancel an auction
CREATE OR REPLACE PROCEDURE cancel_auction(
        p_auction_id INTEGER,
        p_admin_id INTEGER,
        p_reason TEXT
    ) LANGUAGE plpgsql AS $$
DECLARE v_item_id INTEGER;
v_seller_id INTEGER;
BEGIN -- Get auction details
SELECT a.item_id,
    i.seller_id INTO v_item_id,
    v_seller_id
FROM auction a
    JOIN item i ON a.item_id = i.item_id
WHERE a.auction_id = p_auction_id
    AND a.status IN ('Upcoming', 'Active');
IF NOT FOUND THEN RAISE EXCEPTION 'Auction not found or already ended/cancelled';
END IF;
-- Update auction status
UPDATE auction
SET status = 'Cancelled',
    updated_at = CURRENT_TIMESTAMP
WHERE auction_id = p_auction_id;
-- Log the cancellation
INSERT INTO auction_history (auction_id, action, admin_id, reason)
VALUES (
        p_auction_id,
        'Cancelled',
        p_admin_id,
        p_reason
    );
-- Update all active bids to be outbid
UPDATE bid
SET bid_status = 'Outbid'
WHERE auction_id = p_auction_id
    AND bid_status = 'Active';
-- Notify seller
INSERT INTO notification (
        user_id,
        message,
        type,
        related_auction_id,
        related_item_id
    )
VALUES (
        v_seller_id,
        'Your auction has been cancelled: ' || p_reason,
        'AuctionEnded',
        p_auction_id,
        v_item_id
    );
-- Notify all bidders
INSERT INTO notification (user_id, message, type, related_auction_id)
SELECT DISTINCT bidder_id,
    'Auction #' || p_auction_id || ' has been cancelled: ' || p_reason,
    'AuctionEnded',
    p_auction_id
FROM bid
WHERE auction_id = p_auction_id;
COMMIT;
END;
$$;
-- Function to list an item for auction
CREATE OR REPLACE PROCEDURE list_item_for_auction(
        p_seller_id INTEGER,
        p_title VARCHAR(255),
        p_description TEXT,
        p_category_id INTEGER,
        p_condition item_condition,
        p_starting_bid DECIMAL,
        p_reserve_price DECIMAL,
        p_bid_increment DECIMAL,
        p_start_time TIMESTAMP,
        p_end_time TIMESTAMP,
        OUT p_item_id INTEGER,
        OUT p_auction_id INTEGER
    ) LANGUAGE plpgsql AS $$ BEGIN -- Insert item
INSERT INTO item (
        seller_id,
        title,
        description,
        category_id,
        condition,
        status
    )
VALUES (
        p_seller_id,
        p_title,
        p_description,
        p_category_id,
        p_condition,
        'Pending'
    )
RETURNING item_id INTO p_item_id;
-- Create auction
INSERT INTO auction (
        item_id,
        start_time,
        end_time,
        starting_bid,
        reserve_price,
        bid_increment,
        status
    )
VALUES (
        p_item_id,
        p_start_time,
        p_end_time,
        p_starting_bid,
        p_reserve_price,
        p_bid_increment,
        'Upcoming'
    )
RETURNING auction_id INTO p_auction_id;
-- Log auction creation
INSERT INTO auction_history (auction_id, action)
VALUES (p_auction_id, 'Created');
COMMIT;
END;
$$;