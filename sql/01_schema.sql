--Master Products Table (One row per gadget/product)
CREATE TABLE IF NOT EXISTS products(
     product_id SERIAL PRIMARY KEY,
	 product_code VARCHAR(50) UNIQUE NOT NULL,
	 product_name VARCHAR(255) NOT NULL,
	 category VARCHAR(100) NOT NULL,
	 mrp NUMERIC(10,2) NOT NULL CHECK (mrp>0)
);
--Store Listings Table (Maps 1 Product -> Multiple E-Commerce Websites)"
CREATE TABLE IF NOT EXISTS store_listings(
     listing_id SERIAL PRIMARY KEY,
	 product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
	 store_name VARCHAR(50) NOT NULL,
	 product_url TEXT NOT NULL,
	 UNIQUE (product_id,store_name)
);
-- Daily Price History Table (Time-Series Logs per Store)"
CREATE TABLE IF NOT EXISTS price_history (
    history_id BIGSERIAL PRIMARY KEY,
    listing_id INT REFERENCES store_listings(listing_id) ON DELETE CASCADE,
    scraped_date DATE NOT NULL DEFAULT CURRENT_DATE,
    selling_price NUMERIC(10, 2) NOT NULL CHECK (selling_price > 0),
    in_stock BOOLEAN DEFAULT TRUE,
    UNIQUE (listing_id, scraped_date)
);
-- Fast B-Tree Index for historical lookups
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(listing_id, scraped_date DESC);


-- 4. SQL Analytical View: Automatically calculates All-Time Low, 30-Day Avg, and Best Store Rank
CREATE OR REPLACE VIEW vw_product_price_analytics AS
SELECT 
    p.product_id,
    p.product_code,
    p.product_name,
    p.mrp,
    sl.listing_id,
    sl.store_name,
    sl.product_url,
    ph.scraped_date,
    ph.selling_price,
    ph.in_stock,
    -- Rank stores from cheapest (#1) to most expensive on each day
    RANK() OVER (PARTITION BY p.product_id, ph.scraped_date ORDER BY ph.selling_price ASC) AS daily_store_rank,
    -- All-Time Lowest Price across ALL stores for this product
    MIN(ph.selling_price) OVER (PARTITION BY p.product_id) AS all_time_low_price,
    -- All-Time Highest Price across ALL stores for this product
    MAX(ph.selling_price) OVER (PARTITION BY p.product_id) AS all_time_high_price,
    -- 30-Day Rolling Average Price for this product
    ROUND(AVG(ph.selling_price) OVER (
        PARTITION BY p.product_id ORDER BY ph.scraped_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_30d_avg_price
FROM price_history ph
JOIN store_listings sl ON ph.listing_id = sl.listing_id
JOIN products p ON sl.product_id = p.product_id;

