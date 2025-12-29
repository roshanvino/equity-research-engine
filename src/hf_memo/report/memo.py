"""Generate investment memo in Markdown format."""

from datetime import date
from typing import Any

import pandas as pd

from hf_memo.config import ForecastConfig


def generate_memo(
    ticker: str,
    historical_drivers: dict[str, pd.Series],
    scenario_results: dict[str, Any],
    config: ForecastConfig,
    cash: float,
    debt: float,
    shares_outstanding: float | None = None,
) -> str:
    """Generate investment memo in Markdown format.

    Args:
        ticker: Stock ticker symbol.
        historical_drivers: Dictionary from extract_drivers() containing historical metrics.
        scenario_results: Dictionary from run_scenarios() with Base/Bull/Bear results.
        config: Forecast configuration.
        cash: Current cash and cash equivalents.
        debt: Current total debt.
        shares_outstanding: Number of shares outstanding (optional).

    Returns:
        Markdown string containing the investment memo.
    """
    today = date.today()
    base_results = scenario_results["base"]
    bull_results = scenario_results["bull"]
    bear_results = scenario_results["bear"]

    # Extract key metrics
    base_ev = base_results["dcf_results"]["enterprise_value"]
    base_equity = base_results["equity_results"]["equity_value"]
    bull_equity = bull_results["equity_results"]["equity_value"]
    bear_equity = bear_results["equity_results"]["equity_value"]

    base_price = base_results["equity_results"].get("price_per_share")
    bull_price = bull_results["equity_results"].get("price_per_share")
    bear_price = bear_results["equity_results"].get("price_per_share")

    # Build memo
    lines = [
        f"# Investment Memo: {ticker}",
        f"",
        f"**Date:** {today.strftime('%Y-%m-%d')}",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"**Valuation Range (DCF):**",
        f"- Base Case: ${base_equity/1e9:.2f}B (${base_price:.2f}/share)" if base_price else f"- Base Case: ${base_equity/1e9:.2f}B",
        f"- Bull Case: ${bull_equity/1e9:.2f}B (${bull_price:.2f}/share)" if bull_price else f"- Bull Case: ${bull_equity/1e9:.2f}B",
        f"- Bear Case: ${bear_equity/1e9:.2f}B (${bear_price:.2f}/share)" if bear_price else f"- Bear Case: ${bear_equity/1e9:.2f}B",
        f"",
        f"**Key Assumptions:**",
        f"- Forecast Horizon: {config.horizon_years} years",
        f"- Base Case WACC: {config.base.discount_rate*100:.1f}%",
        f"- Base Case Terminal Growth: {config.base.terminal_growth*100:.1f}%",
        f"",
        f"---",
        f"",
        f"## Historical Analysis",
        f"",
    ]

    # Historical revenue and margins
    revenue = historical_drivers["revenue"]
    operating_margin = historical_drivers["operating_margin"]

    lines.extend([
        f"### Revenue Trend",
        f"",
        f"| Period | Revenue | YoY Growth |",
        f"|--------|---------|------------|",
    ])

    for i, (period, rev) in enumerate(revenue.items()):
        if i > 0:
            prev_rev = revenue.iloc[i - 1]
            growth = (rev / prev_rev - 1) * 100
            lines.append(f"| {period.strftime('%Y-%m-%d')} | ${rev/1e6:.1f}M | {growth:+.1f}% |")
        else:
            lines.append(f"| {period.strftime('%Y-%m-%d')} | ${rev/1e6:.1f}M | - |")

    lines.extend([
        f"",
        f"### Operating Margin Trend",
        f"",
        f"| Period | Operating Margin |",
        f"|--------|------------------|",
    ])

    for period, margin in operating_margin.items():
        lines.append(f"| {period.strftime('%Y-%m-%d')} | {margin:.1f}% |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Forecast Assumptions",
        f"",
        f"### Base Case",
        f"",
        f"| Assumption | Value |",
        f"|------------|-------|",
        f"| Discount Rate (WACC) | {config.base.discount_rate*100:.1f}% |",
        f"| Terminal Growth | {config.base.terminal_growth*100:.1f}% |",
        f"| Revenue Growth (Year 1-5) | {', '.join([f'{x*100:.1f}%' for x in (config.base.revenue_growth if isinstance(config.base.revenue_growth, list) else [config.base.revenue_growth]*config.horizon_years)])} |",
    ])

    if config.base.operating_income_pct_revenue:
        margin_vals = config.base.operating_income_pct_revenue if isinstance(config.base.operating_income_pct_revenue, list) else [config.base.operating_income_pct_revenue]*config.horizon_years
        lines.append(f"| Operating Margin (Year 1-5) | {', '.join([f'{x:.1f}%' for x in margin_vals])} |")

    lines.extend([
        f"| Capex % Revenue | {config.base.capex_pct_revenue*100 if isinstance(config.base.capex_pct_revenue, (int, float)) else 'Variable'}% |",
        f"",
        f"### Bull Case",
        f"",
        f"| Assumption | Value |",
        f"|------------|-------|",
        f"| Discount Rate (WACC) | {config.bull.discount_rate*100:.1f}% |",
        f"| Terminal Growth | {config.bull.terminal_growth*100:.1f}% |",
        f"| Revenue Growth (Year 1-5) | {', '.join([f'{x*100:.1f}%' for x in (config.bull.revenue_growth if isinstance(config.bull.revenue_growth, list) else [config.bull.revenue_growth]*config.horizon_years)])} |",
    ])

    if config.bull.operating_income_pct_revenue:
        margin_vals = config.bull.operating_income_pct_revenue if isinstance(config.bull.operating_income_pct_revenue, list) else [config.bull.operating_income_pct_revenue]*config.horizon_years
        lines.append(f"| Operating Margin (Year 1-5) | {', '.join([f'{x:.1f}%' for x in margin_vals])} |")

    lines.extend([
        f"",
        f"### Bear Case",
        f"",
        f"| Assumption | Value |",
        f"|------------|-------|",
        f"| Discount Rate (WACC) | {config.bear.discount_rate*100:.1f}% |",
        f"| Terminal Growth | {config.bear.terminal_growth*100:.1f}% |",
        f"| Revenue Growth (Year 1-5) | {', '.join([f'{x*100:.1f}%' for x in (config.bear.revenue_growth if isinstance(config.bear.revenue_growth, list) else [config.bear.revenue_growth]*config.horizon_years)])} |",
    ])

    if config.bear.operating_income_pct_revenue:
        margin_vals = config.bear.operating_income_pct_revenue if isinstance(config.bear.operating_income_pct_revenue, list) else [config.bear.operating_income_pct_revenue]*config.horizon_years
        lines.append(f"| Operating Margin (Year 1-5) | {', '.join([f'{x:.1f}%' for x in margin_vals])} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Forecast Summary",
        f"",
        f"### Base Case Forecast",
        f"",
        f"| Period | Revenue | Operating Income | CFO | Capex | FCFF |",
        f"|--------|---------|------------------|-----|-------|------|",
    ])

    base_forecast = base_results["forecast_df"]
    base_fcff = base_results["fcff_series"]

    for _, row in base_forecast.iterrows():
        period = row["period_end"]
        fcff = base_fcff[period]
        lines.append(
            f"| {period.strftime('%Y-%m-%d')} | ${row['revenue']/1e6:.1f}M | ${row['operating_income']/1e6:.1f}M | "
            f"${row['cfo']/1e6:.1f}M | ${row['capex']/1e6:.1f}M | ${fcff/1e6:.1f}M |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Valuation Summary",
        f"",
        f"### Base Case DCF",
        f"",
        f"| Component | Value |",
        f"|-----------|-------|",
        f"| PV of Explicit Forecast | ${base_results['dcf_results']['pv_explicit']/1e9:.2f}B |",
        f"| Terminal Value | ${base_results['dcf_results']['terminal_value']/1e9:.2f}B |",
        f"| PV of Terminal Value | ${base_results['dcf_results']['pv_terminal']/1e9:.2f}B |",
        f"| Enterprise Value | ${base_results['dcf_results']['enterprise_value']/1e9:.2f}B |",
        f"| Less: Debt | ${debt/1e9:.2f}B |",
        f"| Plus: Cash | ${cash/1e9:.2f}B |",
        f"| **Equity Value** | **${base_equity/1e9:.2f}B** |",
    ])

    if base_price:
        lines.append(f"| **Price per Share** | **${base_price:.2f}** |")

    lines.extend([
        f"",
        f"### Valuation Range",
        f"",
        f"| Scenario | Enterprise Value | Equity Value |",
        f"|---------|------------------|--------------|",
        f"| Bull | ${bull_results['dcf_results']['enterprise_value']/1e9:.2f}B | ${bull_equity/1e9:.2f}B |",
        f"| Base | ${base_ev/1e9:.2f}B | ${base_equity/1e9:.2f}B |",
        f"| Bear | ${bear_results['dcf_results']['enterprise_value']/1e9:.2f}B | ${bear_equity/1e9:.2f}B |",
        f"",
        f"---",
        f"",
        f"## Sensitivity Analysis",
        f"",
        f"*Sensitivity grid to be populated with WACC and terminal growth variations.*",
        f"",
        f"---",
        f"",
        f"## Investment Thesis",
        f"",
        f"*[To be completed]*",
        f"",
        f"---",
        f"",
        f"## Key Risks",
        f"",
        f"*[To be completed]*",
        f"",
        f"---",
        f"",
        f"## Catalysts",
        f"",
        f"*[To be completed]*",
        f"",
        f"---",
        f"",
        f"*This memo is for research and educational purposes only. It does not constitute investment advice.*",
    ])

    return "\n".join(lines)

