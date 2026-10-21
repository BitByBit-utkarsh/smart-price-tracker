import pandas as pd
from sqlalchemy import text
from src.config import engine

def generate_buying_advice():
    """Queries the PostgreSQL analytical view and evaluates today's best buying options."""
    query = """
        SELECT 
            product_code,
            product_name,
            store_name,
            product_url,
            selling_price,
            mrp,
            all_time_low_price,
            rolling_30d_avg_price,
            daily_store_rank
        FROM vw_product_price_analytics
        WHERE scraped_date = CURRENT_DATE AND in_stock = TRUE
    """
    
    print("Fetching today's market intelligence from PostgreSQL...")
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("No price records found for today. Make sure your live scraper or seeder ran for today's date!")
        return

    recommendations = []

    # Group by product to compare across stores and history
    for code, group in df.groupby("product_code"):
        prod_name = group["product_name"].iloc[0]
        mrp = group["mrp"].iloc[0]
        atl = group["all_time_low_price"].iloc[0]
        avg_30d = group["rolling_30d_avg_price"].iloc[0]

        # Find the absolute cheapest store today
        cheapest_row = group.loc[group["selling_price"].idxmin()]
        best_store = cheapest_row["store_name"]
        best_price = cheapest_row["selling_price"]
        best_url = cheapest_row["product_url"]

        # Calculate discount from MRP and deviation from 30-day average
        discount_pct = round(((mrp - best_price) / mrp) * 100, 1)
        price_diff_vs_30d = best_price - avg_30d

        # Decision Engine Logic (Catching fake sales & finding strong buys)
        if best_price <= atl * 1.01:
            advice = "🟢 STRONG BUY (All-Time Low Price!)"
        elif price_diff_vs_30d < -500:
            advice = f"🟢 BUY NOW (₹{abs(price_diff_vs_30d):,.0f} below 30-day average)"
        elif best_price > avg_30d * 1.05:
            advice = "🔴 WAIT / FAKE SALE ALERT (Price is higher than normal rolling average)"
        else:
            advice = "🟡 FAIR PRICE (Hold unless urgent)"

        recommendations.append({
            "Product": prod_name,
            "Best Store": best_store,
            "Best Price (₹)": f"₹{best_price:,.2f}",
            "30-Day Avg (₹)": f"₹{avg_30d:,.2f}",
            "All-Time Low (₹)": f"₹{atl:,.2f}",
            "Discount": f"{discount_pct}% OFF",
            "Recommendation": advice,
            "URL": best_url
        })

    result_df = pd.DataFrame(recommendations)
    print("\n" + "="*80)
    print(" SMART PRICE TRACKER: TODAY'S BUYING RECOMMENDATIONS ")
    print("="*80)
    print(result_df[["Product", "Best Store", "Best Price (₹)", "Discount", "Recommendation"]].to_string(index=False))
    print("="*80)

if __name__ == "__main__":
    generate_buying_advice()