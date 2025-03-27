-- Insert 200 users
INSERT INTO accounts_user (id, email, first_name, last_name, phone_number, role, is_active, signup_datetime, password)
SELECT
    gen_random_uuid(),
    CONCAT('user', i, '@example.com'),
    CONCAT('FirstName', i),
    CONCAT('LastName', i),
    CONCAT('+91', LPAD(i::text, 10, '0')),
    CASE WHEN i % 10 = 0 THEN 'admin' ELSE 'user' END,
    TRUE,
    NOW() - (i || ' days')::interval,
    'default_password'
FROM generate_series(1, 200) AS s(i);

-- Insert 300 auctions
INSERT INTO auctions_auction (id, seller_id, title, description, starting_price, reserve_price, buy_now_price, start_time, end_time, status, created_at, updated_at)
SELECT
    gen_random_uuid(),
    (SELECT id FROM accounts_user OFFSET floor(random() * 200) LIMIT 1),
    CONCAT('Auction Title ', i),
    CONCAT('Description for auction ', i),
    round((random() * 1000 + 10)::numeric, 2),
    round((random() * 2000 + 1000)::numeric, 2),
    round((random() * 5000 + 3000)::numeric, 2),
    NOW() - (i || ' days')::interval,
    NOW() + ((i + 10) || ' days')::interval,
    CASE WHEN i % 3 = 0 THEN 'active' ELSE 'draft' END,
    NOW(),
    NOW()
FROM generate_series(1, 300) AS s(i);

-- Insert 500 bids
INSERT INTO auctions_bid (id, auction_id, bidder_id, amount, status, timestamp)
SELECT
    gen_random_uuid(),
    (SELECT id FROM auctions_auction OFFSET floor(random() * 300) LIMIT 1),
    (SELECT id FROM accounts_user OFFSET floor(random() * 200) LIMIT 1),
    round((random() * 1000 + 10)::numeric, 2),
    CASE WHEN i % 5 = 0 THEN 'won' ELSE 'active' END,
    NOW() - (i || ' hours')::interval
FROM generate_series(1, 500) AS s(i);