"""Discounted Cash Flow (DCF) valuation calculations."""

import pandas as pd


def calculate_fcff(forecast_df: pd.DataFrame) -> pd.Series:
    """Calculate Free Cash Flow to Firm (FCFF) from forecast.

    FCFF = CFO - Capex

    Args:
        forecast_df: DataFrame with forecasted financials including 'cfo' and 'capex'.

    Returns:
        Series of FCFF values indexed by period_end.
    """
    fcff = forecast_df["cfo"] + forecast_df["capex"]  # capex is negative, so addition works
    return pd.Series(fcff.values, index=forecast_df["period_end"])


def calculate_dcf(
    fcff_series: pd.Series,
    discount_rate: float,
    terminal_growth: float,
    terminal_fcff: float | None = None,
) -> dict[str, float]:
    """Calculate DCF valuation.

    Args:
        fcff_series: Series of FCFF values indexed by period_end.
        discount_rate: WACC (discount rate) as decimal (e.g., 0.10 for 10%).
        terminal_growth: Terminal growth rate as decimal (e.g., 0.025 for 2.5%).
        terminal_fcff: Terminal FCFF value. If None, uses last FCFF value.

    Returns:
        Dictionary containing:
        - pv_explicit: Present value of explicit forecast period
        - terminal_value: Terminal value
        - pv_terminal: Present value of terminal value
        - enterprise_value: Total enterprise value
    """
    if terminal_fcff is None:
        terminal_fcff = fcff_series.iloc[-1]

    # Discount explicit forecast period
    periods = len(fcff_series)
    pv_explicit = 0.0

    for i, (period, fcff) in enumerate(fcff_series.items()):
        years_from_now = i + 1
        pv = fcff / ((1 + discount_rate) ** years_from_now)
        pv_explicit += pv

    # Terminal value (perpetuity growth model)
    terminal_value = terminal_fcff * (1 + terminal_growth) / (discount_rate - terminal_growth)

    # Present value of terminal value
    pv_terminal = terminal_value / ((1 + discount_rate) ** periods)

    # Enterprise value
    enterprise_value = pv_explicit + pv_terminal

    return {
        "pv_explicit": pv_explicit,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
    }


def calculate_equity_value(
    enterprise_value: float,
    cash: float,
    debt: float,
    shares_outstanding: float | None = None,
) -> dict[str, float]:
    """Calculate equity value from enterprise value.

    Equity Value = Enterprise Value - Debt + Cash

    Args:
        enterprise_value: Enterprise value from DCF.
        cash: Cash and cash equivalents.
        debt: Total debt.
        shares_outstanding: Number of shares outstanding (optional, for per-share calculation).

    Returns:
        Dictionary containing:
        - equity_value: Total equity value
        - price_per_share: Price per share (if shares_outstanding provided)
    """
    equity_value = enterprise_value - debt + cash

    result = {"equity_value": equity_value}

    if shares_outstanding is not None and shares_outstanding > 0:
        result["price_per_share"] = equity_value / shares_outstanding

    return result

