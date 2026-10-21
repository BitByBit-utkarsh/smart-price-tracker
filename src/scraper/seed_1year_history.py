import random
from datetime import date, timedelta
from sqlalchemy import text
from src.config import engine

PRODUCTS = [
    {"code": "MOB-SAM-S24P", "name": "Samsung Galaxy S24 Plus 5G (256GB)", "category": "Smartphones", "mrp": 99999.00, "base_price": 76999.00, "today_scenario": "STRONG_BUY"},
    {"code": "MOB-MOT-E70F", "name": "Motorola Edge 70 Fusion 5G (256GB)", "category": "Smartphones", "mrp": 27999.00, "base_price": 23999.00, "today_scenario": "WAIT_FAKE_SALE"},
    {"code": "MOB-APL-IP17P", "name": "Apple iPhone 17 Pro (128GB)", "category": "Smartphones", "mrp": 119900.00, "base_price": 114900.00, "today_scenario": "FAIR_HOLD"},
    {"code": "AUD-SNY-XM5", "name": "Sony WH-1000XM5 Wireless Headphones", "category": "Audio", "mrp": 34990.00, "base_price": 28990.00, "today_scenario": "STRONG_BUY"},
    {"code": "LAP-APL-MBA3", "name": "Apple MacBook Air M3 (512GB)", "category": "Laptops", "mrp": 134900.00, "base_price": 118900.00, "today_scenario": "WAIT_HIGH"}
]

STORES = [
    {"name": "Amazon", "url_prefix": "https://www.amazon.in/dp/", "price_bias": 0.995},
    {"name": "Flipkart", "url_prefix": "https://www.flipkart.com/p/", "price_bias": 0.990},
    {"name": "Croma", "url_prefix": "https://www.croma.com/p/", "price_bias": 1.005},
    {"name": "Reliance Digital", "url_prefix": "https://www.reliancedigital.in/p/", "price_bias": 1.002}
]

def get_seasonal_multiplier(target_date: date) -> float:
    m, d = target_date.month, target_date.day
    if m == 1 and 18 <= d <= 26: return 0.88      # Republic Day
    if m == 7 and 12 <= d <= 18: return 0.89      # Prime Day
    if m == 10 and 1 <= d <= 12: return 0.85     # Big Billion Days
    return random.uniform(0.97, 1.02)

def seed_one_year_data(days: int = 365):
    random.seed(42)
    start_date = date.today() - timedelta(days=days - 1)
    total_rows = 0

    with engine.begin() as conn:
        for prod in PRODUCTS:
            conn.execute(text("""
                INSERT INTO products (product_code, product_name, category, mrp)
                VALUES (:code, :name, :cat, :mrp)
                ON CONFLICT (product_code) DO UPDATE SET mrp = EXCLUDED.mrp
            """), {"code": prod["code"], "name": prod["name"], "cat": prod["category"], "mrp": prod["mrp"]})

            prod_id = conn.execute(text("SELECT product_id FROM products WHERE product_code = :code"), {"code": prod["code"]}).scalar()

            listing_map = {}
            for store in STORES:
                conn.execute(text("""
                    INSERT INTO store_listings (product_id, store_name, product_url)
                    VALUES (:pid, :sname, :url)
                    ON CONFLICT (product_id, store_name) DO NOTHING
                """), {"pid": prod_id, "sname": store["name"], "url": f"{store['url_prefix']}{prod['code'].lower()}"})

                lid = conn.execute(text("SELECT listing_id FROM store_listings WHERE product_id = :pid AND store_name = :sname"), {"pid": prod_id, "sname": store["name"]}).scalar()
                listing_map[store["name"]] = (lid, store["price_bias"])

            batch_rows = []
            for day_offset in range(days):
                curr_date = start_date + timedelta(days=day_offset)
                is_today = (curr_date == date.today())
                seasonal_mult = get_seasonal_multiplier(curr_date)

                for store_name, (lid, bias) in listing_map.items():
                    raw_price = prod["base_price"] * seasonal_mult * bias * random.uniform(0.99, 1.015)
                    if is_today:
                        if prod["today_scenario"] == "STRONG_BUY" and store_name in ("Flipkart", "Amazon"):
                            raw_price = prod["base_price"] * 0.84
                        elif prod["today_scenario"] == "WAIT_FAKE_SALE":
                            raw_price = prod["base_price"] * 1.09

                    final_price = min(prod["mrp"], round(raw_price / 10) * 10 - 1)
                    batch_rows.append({"lid": lid, "sdate": curr_date, "price": final_price, "stock": True})

            conn.execute(text("""
                INSERT INTO price_history (listing_id, scraped_date, selling_price, in_stock)
                VALUES (:lid, :sdate, :price, :stock)
                ON CONFLICT (listing_id, scraped_date) DO UPDATE 
                SET selling_price = EXCLUDED.selling_price, in_stock = EXCLUDED.in_stock
            """), batch_rows)
            total_rows += len(batch_rows)

    print(f"Successfully seeded {total_rows:,} historical price records!")

if __name__ == "__main__":
    seed_one_year_data(365)