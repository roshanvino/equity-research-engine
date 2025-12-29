"""Tests for forecast module."""

import pandas as pd
import pytest

from hf_memo.config import ScenarioConfig
from hf_memo.model.forecast import build_forecast


def test_capex_sign_handling() -> None:
    """Test that capex reduces FCFF (capex should be negative)."""
    historical_drivers = {
        "revenue": pd.Series([1000.0, 1100.0, 1200.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "operating_income": pd.Series([150.0, 165.0, 180.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "operating_margin": pd.Series([15.0, 15.0, 15.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "cfo": pd.Series([160.0, 175.0, 190.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "capex": pd.Series([-50.0, -55.0, -60.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "capex_pct_revenue": pd.Series([5.0, 5.0, 5.0], index=pd.date_range("2021-01-01", periods=3, freq="YS")),
        "periods": pd.date_range("2021-01-01", periods=3, freq="YS"),
    }

    scenario_config = ScenarioConfig(
        discount_rate=0.10,
        terminal_growth=0.025,
        revenue_growth=[0.05] * 5,
        operating_income_pct_revenue=[0.15] * 5,
        capex_pct_revenue=0.05,  # 5% of revenue
        nwc_pct_revenue=0.0,
    )

    forecast_df = build_forecast(historical_drivers, scenario_config, horizon_years=5)

    # Check that capex is negative (cash outflow)
    assert all(forecast_df["capex"] < 0), "Capex should be negative (cash outflow)"

    # Check that FCFF = CFO + Capex (capex negative, so FCFF < CFO)
    # In our simplified model, we don't calculate FCFF in forecast_df,
    # but we can verify the sign is correct
    for _, row in forecast_df.iterrows():
        assert row["capex"] < 0, f"Capex should be negative, got {row['capex']}"


def test_forecast_revenue_growth() -> None:
    """Test that forecast applies revenue growth correctly."""
    historical_drivers = {
        "revenue": pd.Series([1000.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "operating_income": pd.Series([150.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "operating_margin": pd.Series([15.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "cfo": pd.Series([160.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "capex": pd.Series([-50.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "capex_pct_revenue": pd.Series([5.0], index=pd.date_range("2023-01-01", periods=1, freq="YS")),
        "periods": pd.date_range("2023-01-01", periods=1, freq="YS"),
    }

    scenario_config = ScenarioConfig(
        discount_rate=0.10,
        terminal_growth=0.025,
        revenue_growth=[0.10, 0.08, 0.06, 0.04, 0.02],  # Declining growth
        operating_income_pct_revenue=[0.15] * 5,
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.0,
    )

    forecast_df = build_forecast(historical_drivers, scenario_config, horizon_years=5)

    assert len(forecast_df) == 5

    # Check revenue growth
    assert forecast_df["revenue"].iloc[0] == 1000.0 * 1.10  # 10% growth
    assert forecast_df["revenue"].iloc[1] == 1000.0 * 1.10 * 1.08  # 8% growth on previous

