Set-Content -Path README.md -Encoding utf8 -Value @"
# 🛍️ Smart Price Tracker & "Buy vs. Wait" Engine

Have you ever noticed how e-commerce sites artificially inflate a product's price right before a major festive sale, just so the "discount" looks massive? I noticed it too. 

I built this full-stack application to catch exactly that. It's an automated price tracker that monitors gadgets across Amazon, Flipkart, Croma, and Reliance Digital. Instead of just showing you a price, it uses historical data and statistical moving averages to tell you if a sale is genuine, or if you're falling for a "fake sale" trap.

## 🚀 What This App Actually Does

* **Catches Fake Sales:** Calculates a rolling 30-day average for every product. If today's "discounted" price is actually higher than the recent average, it flags it as a `🔴 WAIT / FAKE SALE ALERT`.
* **Spots Real Deals:** If a product hits its All-Time Low (ATL) or drops significantly below the 30-day baseline, the app throws a `🟢 STRONG BUY` signal.
* **Scrapes Concurrently:** Uses `aiohttp` and `asyncio` to pull live prices from multiple websites simultaneously without blocking the main thread.
* **Serves Data Fast:** Exposes everything through a fast REST API built with FastAPI, hooked up to a responsive Tailwind CSS dashboard.

---

## 🏛️ System Architecture

I designed this to be a robust, end-to-end data pipeline rather than just a simple script.

[ Live E-Commerce Sites ]
           │ (Async Scraper using aiohttp & bs4)
           ▼
[ Data Ingestion & Validation ]
           │ (Idempotent Batch Upserts)
           ▼
[ PostgreSQL Database (3NF) ] ──► [ SQL Window Functions ]
           │                        Calculates Rolling Averages,
           │                        All-Time Lows, and Rankings directly on disk.
           ▼
[ Python Decision Engine ]
           │ (Pandas / NumPy for threshold calculations)
           ▼
[ FastAPI Backend ]
           │
           ▼
[ Tailwind CSS Dashboard ]

---

## 🧠 The "Buy vs. Wait" Algorithm

The app doesn't just guess if a deal is good; it does the math. Here is the logic it runs every time you refresh the dashboard:

1. **All-Time Low Alert (`🟢 STRONG BUY`):** 
   If the current price (P) is within 1% of the historical All-Time Low (P_ATL): P <= P_ATL * 1.01
2. **Solid Discount (`🟢 BUY NOW`):** 
   If the price is significantly cheaper (e.g., ₹500+) than the 30-day moving average.
3. **Deceptive Sale (`🔴 WAIT / FAKE SALE ALERT`):** 
   If the current price is more than 5% *higher* than the 30-day average. Retailers often do this right before a major sale event.

---

## 🗄️ Database & Schema Design

I built the PostgreSQL database in **Third Normal Form (3NF)**. Instead of creating one massive, repetitive table, I split it into `products` (master data), `store_listings` (URLs and vendor info), and `price_history` (the daily time-series logs). 

### Pushing Compute to the Database
Instead of loading millions of raw rows into Pandas to calculate averages (which would eat up RAM), I wrote a PostgreSQL View using **SQL Window Functions**. 

This view calculates the All-Time Lows (`MIN() OVER`) and the 30-Day Moving Averages (`AVG() OVER ... ROWS BETWEEN 29 PRECEDING AND CURRENT ROW`) directly on the database level, returning only the final clean data to the API.

---

## 💻 Tech Stack

* **Language:** Python 3.10+
* **Web Framework:** FastAPI, Uvicorn (ASGI)
* **Database & ORM:** PostgreSQL 16, SQLAlchemy, psycopg2
* **Data Processing:** Pandas, NumPy
* **Web Scraping:** AsyncIO, aiohttp, BeautifulSoup4
* **Frontend UI:** HTML5, Tailwind CSS
* **Testing:** Pytest

---

## 🛠️ How to Run It Locally

### 1. Set up the environment
git clone https://github.com/BitByBit-utkarsh/smart-price-tracker.git
cd smart-price-tracker

python -m venv venv
.\venv\Scripts\Activate

pip install -r requirements.txt

### 2. Set up the Database
1. Create a PostgreSQL database named `smart_price_db`.
2. Update your credentials inside `src/config.py`.
3. Run the SQL script located in `sql/01_schema.sql` to generate the tables and views.

### 3. Seed Data & Launch
# Seed 1 year of historical price data so the charts have something to show
python -m src.scraper.seed_1year_history

# Start the FastAPI server
uvicorn src.api.main:app --reload

Once the server is running, open your browser and go to http://127.0.0.1:8000/ to see the UI, or /docs to test the API directly via Swagger.

---

## 💡 Technical Decisions 

If you're looking at my code, here are a few deliberate engineering choices I made:

* **AsyncIO over Threading:** Web scraping is heavily I/O-bound. Instead of spinning up OS threads (which carry context-switching overhead and GIL limitations), I used `aiohttp` so the single-threaded event loop can process concurrent network requests incredibly fast.
* **Idempotent Database Writes:** What happens if the scraper runs twice in one day by accident? To prevent duplicate rows and database crashes, I used composite unique constraints combined with PostgreSQL's `ON CONFLICT DO UPDATE` (upsert). It safely overwrites the day's price without throwing errors.
* **Connection Pooling:** I used SQLAlchemy's connection pooling to maintain a set of open database connections. This eliminates the TCP handshake latency that would otherwise happen every time a user hits the FastAPI endpoints.
"@