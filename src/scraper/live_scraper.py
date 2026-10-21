import asyncio
import aiohttp
import logging
import re
from datetime import date
from bs4 import BeautifulSoup
from sqlalchemy import text
from src.config import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

async def fetch_live_price(session: aiohttp.ClientSession, url: str, store_name: str) -> float:
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status != 200: return None
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            price_text = None
            if store_name == "Amazon":
                elem = soup.find("span", {"class": "a-price-whole"})
                if elem: price_text = elem.get_text()
            elif store_name == "Flipkart":
                elem = soup.find("div", {"class": "_30jeq3"})
                if elem: price_text = elem.get_text()

            if price_text:
                return float(re.sub(r"[^\d.]", "", price_text))
    except Exception as e:
        logging.error(f"Error scraping {store_name}: {e}")
    return None

async def run_daily_live_scrape():
    today = date.today()
    with engine.connect() as conn:
        listings = conn.execute(text("""
            SELECT sl.listing_id, sl.store_name, sl.product_url, p.product_name
            FROM store_listings sl JOIN products p ON sl.product_id = p.product_id
        """)).mappings().all()

    async with aiohttp.ClientSession() as session:
        for item in listings:
            price = await fetch_live_price(session, item["product_url"], item["store_name"])
            if price:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO price_history (listing_id, scraped_date, selling_price, in_stock)
                        VALUES (:lid, :sdate, :price, TRUE)
                        ON CONFLICT (listing_id, scraped_date) DO UPDATE 
                        SET selling_price = EXCLUDED.selling_price, in_stock = TRUE
                    """), {"lid": item["listing_id"], "sdate": today, "price": price})
                logging.info(f"SAVED LIVE: {item['product_name']} on {item['store_name']} -> ₹{price}")

if __name__ == "__main__":
    asyncio.run(run_daily_live_scrape())