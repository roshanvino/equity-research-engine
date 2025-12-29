"""Extract historical drivers from standardized financial data."""

from typing import Any

import pandas as pd


def extract_drivers(standardized_df: pd.DataFrame) -> dict[str, Any]:
    """Extract historical drivers from standardized financial data.

    Args:
        standardized_df: Long-format DataFrame with standardized financials.

    Returns:
        Dictionary containing historical driver metrics:
        - revenue: Series of revenue values
        - operating_income: Series of operating income values
        - operating_margin: Series of operating margin percentages
        - cfo: Series of cash from operations
        - capex: Series of capital expenditures
        - capex_pct_revenue: Series of capex as % of revenue
        - periods: Series of period_end dates
    """
    income_df = standardized_df[standardized_df["statement"] == "income"]
    cash_df = standardized_df[standardized_df["statement"] == "cashflow"]

    # Get revenue
    revenue_data = income_df[income_df["line_item"] == "revenue"].sort_values("period_end")
    revenue = revenue_data.set_index("period_end")["value"]

    # Get operating income
    operating_income_data = income_df[income_df["line_item"] == "operating_income"].sort_values(
        "period_end"
    )
    operating_income = operating_income_data.set_index("period_end")["value"]

    # Calculate operating margin
    operating_margin = (operating_income / revenue * 100).fillna(0)

    # Get CFO
    cfo_data = cash_df[cash_df["line_item"] == "cfo"].sort_values("period_end")
    cfo = cfo_data.set_index("period_end")["value"]

    # Get capex
    capex_data = cash_df[cash_df["line_item"] == "capex"].sort_values("period_end")
    capex = capex_data.set_index("period_end")["value"]

    # Calculate capex as % of revenue
    capex_pct_revenue = (capex.abs() / revenue * 100).fillna(0)

    return {
        "revenue": revenue,
        "operating_income": operating_income,
        "operating_margin": operating_margin,
        "cfo": cfo,
        "capex": capex,
        "capex_pct_revenue": capex_pct_revenue,
        "periods": revenue.index,
    }

