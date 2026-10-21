import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from src.config import engine

app = FastAPI(
    title="Smart Price Tracker & Buy Recommendation API",
    description="Backend API for multi-platform e-commerce price intelligence and AI-driven buy/wait recommendations.",
    version="1.1.0"
)

# Gorgeous Tailwind CSS Dashboard served at the root URL (http://127.0.0.1:8000/)
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Price Intelligence & Buy/Wait Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen">
    <div class="max-w-6xl mx-auto px-4 py-10">
        <!-- Header -->
        <header class="mb-10 text-center">
            <h1 class="text-4xl font-extrabold tracking-tight text-white mb-2">🛍️ Smart Price Intelligence</h1>
            <p class="text-slate-400">Multi-Platform Competitor Tracker & Automated "Buy Now vs. Wait" Decision Engine</p>
        </header>

        <!-- Product Cards Container -->
        <div id="loading" class="text-center text-slate-400 py-20 text-lg">Loading market intelligence...</div>
        <div id="dashboard-grid" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
    </div>

    <script>
        async function fetchRecommendations() {
            try {
                const response = await fetch('/api/v1/recommendations');
                const result = await response.json();
                const grid = document.getElementById('dashboard-grid');
                const loading = document.getElementById('loading');

                loading.style.display = 'none';

                if (!result.data || result.data.length === 0) {
                    grid.innerHTML = '<p class="col-span-2 text-center text-slate-400">No data found. Run your seeder or live scraper!</p>';
                    return;
                }

                grid.innerHTML = result.data.map(item => {
                    let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
                    if (item.recommendation.includes('STRONG BUY')) badgeColor = 'bg-emerald-950 text-emerald-300 border-emerald-800';
                    else if (item.recommendation.includes('BUY NOW')) badgeColor = 'bg-green-950 text-green-300 border-green-800';
                    else if (item.recommendation.includes('WAIT')) badgeColor = 'bg-rose-950 text-rose-300 border-rose-800';

                    return `
                        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between hover:border-slate-600 transition">
                            <div>
                                <div class="flex justify-between items-start mb-3">
                                    <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">${item.product_code}</span>
                                    <span class="text-xs font-bold px-3 py-1 rounded-full border ${badgeColor}">${item.recommendation}</span>
                                </div>
                                <h2 class="text-xl font-bold text-white mb-4">${item.product_name}</h2>
                                
                                <div class="grid grid-cols-2 gap-4 bg-slate-900/50 p-4 rounded-xl mb-4 border border-slate-700/50">
                                    <div>
                                        <p class="text-xs text-slate-400 uppercase tracking-wider">Best Store Today</p>
                                        <p class="text-lg font-bold text-indigo-400">${item.best_store}</p>
                                    </div>
                                    <div>
                                        <p class="text-xs text-slate-400 uppercase tracking-wider">Best Price</p>
                                        <p class="text-lg font-bold text-emerald-400">₹${item.best_price.toLocaleString('en-IN')}</p>
                                    </div>
                                    <div>
                                        <p class="text-xs text-slate-400">MRP / List Price</p>
                                        <p class="text-sm font-semibold text-slate-300">₹${item.mrp.toLocaleString('en-IN')} (${item.discount_percentage})</p>
                                    </div>
                                    <div>
                                        <p class="text-xs text-slate-400">30-Day Rolling Avg</p>
                                        <p class="text-sm font-semibold text-slate-300">₹${item.rolling_30d_avg.toLocaleString('en-IN')}</p>
                                    </div>
                                </div>
                            </div>

                            <div class="flex justify-between items-center mt-2 pt-4 border-t border-slate-700">
                                <span class="text-xs text-slate-400">All-Time Low: <strong class="text-white">₹${item.all_time_low.toLocaleString('en-IN')}</strong></span>
                                <a href="${item.product_url}" target="_blank" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-xl text-sm transition shadow-lg shadow-indigo-600/20">
                                    View on Store &rarr;
                                </a>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (err) {
                document.getElementById('loading').innerText = 'Error loading dashboard data.';
            }
        }
        fetchRecommendations();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def render_dashboard():
    """Serves the gorgeous Tailwind CSS Executive Dashboard."""
    return HTML_DASHBOARD

@app.get("/api/v1/recommendations")
def get_buying_recommendations():
    """Calculates and returns today's best store prices and automated buy/wait advice per product."""
    query = """
        SELECT 
            product_code, product_name, store_name, product_url,
            selling_price, mrp, all_time_low_price, rolling_30d_avg_price
        FROM vw_product_price_analytics
        WHERE scraped_date = CURRENT_DATE AND in_stock = TRUE
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, engine)
        
    if df.empty:
        return {"data": []}

    recommendations = []
    for code, group in df.groupby("product_code"):
        prod_name = group["product_name"].iloc[0]
        mrp = group["mrp"].iloc[0]
        atl = group["all_time_low_price"].iloc[0]
        avg_30d = group["rolling_30d_avg_price"].iloc[0]

        cheapest_row = group.loc[group["selling_price"].idxmin()]
        best_store = cheapest_row["store_name"]
        best_price = float(cheapest_row["selling_price"])
        best_url = cheapest_row["product_url"]

        discount_pct = round(((mrp - best_price) / mrp) * 100, 1)
        price_diff_vs_30d = best_price - avg_30d

        if best_price <= atl * 1.01:
            advice = "🟢 STRONG BUY (All-Time Low)"
        elif price_diff_vs_30d < -500:
            advice = f"🟢 BUY NOW (₹{abs(price_diff_vs_30d):,.0f} below avg)"
        elif best_price > avg_30d * 1.05:
            advice = "🔴 WAIT / FAKE SALE ALERT"
        else:
            advice = "🟡 FAIR PRICE (Hold)"

        recommendations.append({
            "product_code": code,
            "product_name": prod_name,
            "best_store": best_store,
            "best_price": best_price,
            "mrp": float(mrp),
            "all_time_low": float(atl),
            "rolling_30d_avg": float(avg_30d),
            "discount_percentage": f"{discount_pct}% OFF",
            "recommendation": advice,
            "product_url": best_url
        })

    return {"count": len(recommendations), "data": recommendations}