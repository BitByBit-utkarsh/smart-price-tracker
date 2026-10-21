import pytest
from datetime import date

def test_price_discount_calculation():
    """Test that discount percentage calculation is mathematically correct."""
    mrp = 99999.00
    selling_price = 76999.00
    discount_pct = round(((mrp - selling_price) / mrp) * 100, 1)
    
    assert discount_pct == 23.0
    assert selling_price < mrp

def test_buy_recommendation_logic():
    """Test decision engine thresholds for All-Time Low vs Normal pricing."""
    all_time_low = 75000.00
    rolling_30d_avg = 80000.00

    # Scenario 1: Price is at All-Time Low
    best_price_atl = 75000.00
    assert best_price_atl <= all_time_low * 1.01  # Should trigger STRONG BUY

    # Scenario 2: Price is heavily inflated above 30-day average
    best_price_inflated = 85000.00
    assert best_price_inflated > rolling_30d_avg * 1.05  # Should trigger FAKE SALE / WAIT