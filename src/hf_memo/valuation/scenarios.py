"""Scenario-based valuation (Base/Bull/Bear)."""

from typing import Any

import pandas as pd

from hf_memo.config import ForecastConfig
from hf_memo.model.forecast import build_forecast
from hf_memo.valuation.dcf import calculate_dcf, calculate_equity_value, calculate_fcff


def run_scenarios(
    historical_drivers: dict[str, pd.Series],
    config: ForecastConfig,
    cash: float,
    debt: float,
    shares_outstanding: float | None = None,
) -> dict[str, Any]:
    """Run Base/Bull/Bear scenario valuations.

    Args:
        historical_drivers: Dictionary from extract_drivers() containing historical metrics.
        config: Forecast configuration with Base/Bull/Bear scenarios.
        cash: Current cash and cash equivalents.
        debt: Current total debt.
        shares_outstanding: Number of shares outstanding (optional).

    Returns:
        Dictionary containing:
        - base: Base scenario results
        - bull: Bull scenario results
        - bear: Bear scenario results
        Each scenario contains: forecast_df, fcff_series, dcf_results, equity_results
    """
    results = {}

    for scenario_name in ["base", "bull", "bear"]:
        scenario_config = getattr(config, scenario_name)

        # Build forecast
        forecast_df = build_forecast(historical_drivers, scenario_config, config.horizon_years)

        # Calculate FCFF
        fcff_series = calculate_fcff(forecast_df)

        # Calculate DCF
        dcf_results = calculate_dcf(
            fcff_series,
            scenario_config.discount_rate,
            scenario_config.terminal_growth,
        )

        # Calculate equity value
        equity_results = calculate_equity_value(
            dcf_results["enterprise_value"],
            cash,
            debt,
            shares_outstanding,
        )

        results[scenario_name] = {
            "forecast_df": forecast_df,
            "fcff_series": fcff_series,
            "dcf_results": dcf_results,
            "equity_results": equity_results,
        }

    return results

