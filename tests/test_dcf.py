"""Tests for DCF valuation calculations."""

import pandas as pd
import pytest

from hf_memo.valuation.dcf import calculate_dcf, calculate_equity_value, calculate_fcff


def test_calculate_fcff() -> None:
    """Test FCFF calculation from forecast."""
    forecast_df = pd.DataFrame({
        "period_end": pd.date_range("2024-01-01", periods=5, freq="YS"),
        "cfo": [100.0, 110.0, 120.0, 130.0, 140.0],
        "capex": [-20.0, -22.0, -24.0, -26.0, -28.0],
    })

    fcff = calculate_fcff(forecast_df)

    assert len(fcff) == 5
    assert fcff.iloc[0] == 80.0  # 100 - 20
    assert fcff.iloc[-1] == 112.0  # 140 - 28


def test_calculate_dcf() -> None:
    """Test DCF calculation with toy series."""
    fcff_series = pd.Series(
        [80.0, 88.0, 96.0, 104.0, 112.0],
        index=pd.date_range("2024-01-01", periods=5, freq="YS"),
    )

    discount_rate = 0.10
    terminal_growth = 0.025

    results = calculate_dcf(fcff_series, discount_rate, terminal_growth)

    assert "pv_explicit" in results
    assert "terminal_value" in results
    assert "pv_terminal" in results
    assert "enterprise_value" in results

    # PV explicit should be sum of discounted cash flows
    assert results["pv_explicit"] > 0
    assert results["pv_explicit"] < sum(fcff_series)  # Discounted should be less

    # Terminal value should be positive
    assert results["terminal_value"] > 0

    # Enterprise value should be sum of PV explicit and PV terminal
    assert abs(results["enterprise_value"] - (results["pv_explicit"] + results["pv_terminal"])) < 0.01


def test_calculate_equity_value() -> None:
    """Test equity value calculation."""
    enterprise_value = 1000.0
    cash = 100.0
    debt = 200.0

    results = calculate_equity_value(enterprise_value, cash, debt)

    assert results["equity_value"] == 900.0  # 1000 - 200 + 100

    # Test with shares outstanding
    results_with_shares = calculate_equity_value(enterprise_value, cash, debt, shares_outstanding=100.0)
    assert "price_per_share" in results_with_shares
    assert results_with_shares["price_per_share"] == 9.0  # 900 / 100

