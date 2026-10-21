from sqlalchemy import create_engine
from urllib.parse import quote_plus

DB_USER = "postgres"
DB_PASSWORD = quote_plus("root123")  # Put your PostgreSQL password here
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "smart_price_db"

DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URI, pool_size=5, max_overflow=10)