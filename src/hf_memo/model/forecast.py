"""Driver-based forecasting for financial statements."""

from typing import Callable

import pandas as pd

from hf_memo.config import ScenarioConfig


def build_forecast(
    historical_drivers: dict[str, pd.Series],
    scenario_config: ScenarioConfig,
    horizon_years: int,
) -> pd.DataFrame:
    """Build 5-year forecast using driver-based assumptions.

    Args:
        historical_drivers: Dictionary from extract_drivers() containing historical metrics.
        scenario_config: Scenario configuration with assumptions.
        horizon_years: Number of years to forecast.

    Returns:
        DataFrame with forecasted financials in long-format:
        - period_end: Forecast period dates
        - revenue: Forecasted revenue
        - operating_income: Forecasted operating income
        - cfo: Forecasted cash from operations
        - capex: Forecasted capital expenditures
    """
    # Get last historical period
    last_period = historical_drivers["periods"][-1]
    last_revenue = historical_drivers["revenue"].iloc[-1]

    # Generate forecast periods (start from next year)
    # Get the year of the last period and start from next year
    last_year = last_period.year if hasattr(last_period, 'year') else pd.Timestamp(last_period).year
    next_year_start = pd.Timestamp(year=last_year + 1, month=1, day=1)
    forecast_periods = pd.date_range(
        start=next_year_start,
        periods=horizon_years,
        freq="YS",  # Year start
    )

    # Get revenue growth assumptions
    if isinstance(scenario_config.revenue_growth, list):
        revenue_growth_rates = scenario_config.revenue_growth
    elif callable(scenario_config.revenue_growth):
        revenue_growth_rates = [scenario_config.revenue_growth(i) for i in range(horizon_years)]
    else:
        revenue_growth_rates = [0.05] * horizon_years

    # Get operating margin assumptions
    if scenario_config.operating_income_pct_revenue is not None:
        if isinstance(scenario_config.operating_income_pct_revenue, list):
            operating_margin_pct = scenario_config.operating_income_pct_revenue
        elif callable(scenario_config.operating_income_pct_revenue):
            operating_margin_pct = [
                scenario_config.operating_income_pct_revenue(i) for i in range(horizon_years)
            ]
        else:
            operating_margin_pct = [0.15] * horizon_years
    elif scenario_config.operating_margin is not None:
        if isinstance(scenario_config.operating_margin, list):
            operating_margin_pct = scenario_config.operating_margin
        elif callable(scenario_config.operating_margin):
            operating_margin_pct = [scenario_config.operating_margin(i) for i in range(horizon_years)]
        else:
            operating_margin_pct = [0.15] * horizon_years
    else:
        # Fallback: use historical average
        hist_margin = historical_drivers["operating_margin"].iloc[-3:].mean()
        operating_margin_pct = [hist_margin] * horizon_years

    # Get capex assumptions
    if isinstance(scenario_config.capex_pct_revenue, list):
        capex_pct = scenario_config.capex_pct_revenue
    elif callable(scenario_config.capex_pct_revenue):
        capex_pct = [scenario_config.capex_pct_revenue(i) for i in range(horizon_years)]
    else:
        capex_pct = [scenario_config.capex_pct_revenue] * horizon_years

    # Build forecast
    forecast_rows = []
    current_revenue = last_revenue

    for i, period in enumerate(forecast_periods):
        # Revenue growth
        growth_rate = revenue_growth_rates[i] if i < len(revenue_growth_rates) else 0.05
        current_revenue = current_revenue * (1 + growth_rate)

        # Operating income (from margin)
        margin_pct = operating_margin_pct[i] if i < len(operating_margin_pct) else 15.0
        operating_income = current_revenue * (margin_pct / 100.0)

        # Capex
        capex_pct_val = capex_pct[i] if i < len(capex_pct) else 5.0
        capex = -current_revenue * (capex_pct_val / 100.0)  # Negative (cash outflow)

        # CFO approximation: operating income + D&A - change in NWC
        # Simplified: assume CFO = operating income * 1.1 (rough approximation)
        # In practice, you'd model D&A and NWC changes separately
        cfo = operating_income * 1.1

        forecast_rows.append(
            {
                "period_end": period,
                "revenue": current_revenue,
                "operating_income": operating_income,
                "cfo": cfo,
                "capex": capex,
            }
        )

    return pd.DataFrame(forecast_rows)

