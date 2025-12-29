"""Mapper to convert FMP provider data to canonical schema."""

from datetime import datetime

import pandas as pd

from hf_memo.standardize.schema import (
    CANONICAL_LINE_ITEMS,
    STANDARD_COLUMNS,
    StatementType,
    create_empty_standard_df,
    validate_standard_df,
)


def standardize_fmp(
    raw_income_df: pd.DataFrame,
    raw_balance_df: pd.DataFrame,
    raw_cash_df: pd.DataFrame,
    ticker: str,
    source: str = "fmp",
) -> pd.DataFrame:
    """Convert FMP provider dataframes to canonical long-format schema.

    Args:
        raw_income_df: FMP income statement DataFrame.
        raw_balance_df: FMP balance sheet DataFrame.
        raw_cash_df: FMP cash flow statement DataFrame.
        ticker: Stock ticker symbol.
        source: Source identifier (default: "fmp").

    Returns:
        Long-format DataFrame with columns: ticker, period_end, statement, line_item, value, currency, source.

    Raises:
        ValueError: If required fields are missing or insufficient data exists.
    """
    if raw_income_df.empty or raw_balance_df.empty or raw_cash_df.empty:
        raise ValueError("One or more financial statements are empty")

    # Check for required period_end column
    for df_name, df in [
        ("income", raw_income_df),
        ("balance", raw_balance_df),
        ("cash", raw_cash_df),
    ]:
        if "period_end" not in df.columns:
            raise ValueError(f"{df_name} statement missing 'period_end' column")

    # Get currency (assume same across all statements)
    currency = raw_income_df.get("currency", "USD").iloc[0] if not raw_income_df.empty else "USD"

    # Extract currency from other statements if available
    if "currency" in raw_balance_df.columns and not raw_balance_df.empty:
        currency = raw_balance_df["currency"].iloc[0]
    elif "currency" in raw_cash_df.columns and not raw_cash_df.empty:
        currency = raw_cash_df["currency"].iloc[0]

    # Validate minimum data requirements
    min_periods = 2
    income_periods = raw_income_df["period_end"].nunique()
    if income_periods < min_periods:
        raise ValueError(
            f"Insufficient income statement data: found {income_periods} periods, need at least {min_periods}"
        )

    # Map income statement
    income_rows = _map_income_statement(raw_income_df, ticker, currency, source)

    # Map balance sheet
    balance_rows = _map_balance_sheet(raw_balance_df, ticker, currency, source)

    # Map cash flow
    cash_rows = _map_cash_flow(raw_cash_df, ticker, currency, source)

    # Combine all rows
    all_rows = income_rows + balance_rows + cash_rows

    if not all_rows:
        raise ValueError("No data could be mapped to canonical schema")

    # Create DataFrame
    df = pd.DataFrame(all_rows)

    # Validate required core fields exist
    _validate_core_fields(df, ticker)

    # Validate schema
    validate_standard_df(df)

    return df.sort_values(["period_end", "statement", "line_item"]).reset_index(drop=True)


def _map_income_statement(
    df: pd.DataFrame, ticker: str, currency: str, source: str
) -> list[dict[str, any]]:
    """Map FMP income statement to canonical schema.

    Args:
        df: FMP income statement DataFrame.
        ticker: Stock ticker symbol.
        currency: Currency code.
        source: Source identifier.

    Returns:
        List of dictionaries representing standardized income statement rows.
    """
    rows = []

    # Field mappings: FMP field name -> canonical line item
    field_mappings = {
        "revenue": "revenue",
        "total_revenue": "revenue",
        "operating_income": "operating_income",
        "ebit": "operating_income",
        "net_income": "net_income",
    }

    for _, row in df.iterrows():
        period_end = pd.to_datetime(row["period_end"])

        # Map revenue
        revenue = _get_field_value(row, ["revenue", "total_revenue"])
        if revenue is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.INCOME.value,
                    "line_item": "revenue",
                    "value": float(revenue),
                    "currency": currency,
                    "source": source,
                }
            )

        # Map operating income (EBIT)
        operating_income = _get_field_value(row, ["operating_income", "ebit"])
        if operating_income is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.INCOME.value,
                    "line_item": "operating_income",
                    "value": float(operating_income),
                    "currency": currency,
                    "source": source,
                }
            )

        # Map net income
        net_income = _get_field_value(row, ["net_income", "net_income_loss"])
        if net_income is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.INCOME.value,
                    "line_item": "net_income",
                    "value": float(net_income),
                    "currency": currency,
                    "source": source,
                }
            )

    return rows


def _map_balance_sheet(
    df: pd.DataFrame, ticker: str, currency: str, source: str
) -> list[dict[str, any]]:
    """Map FMP balance sheet to canonical schema.

    Args:
        df: FMP balance sheet DataFrame.
        ticker: Stock ticker symbol.
        currency: Currency code.
        source: Source identifier.

    Returns:
        List of dictionaries representing standardized balance sheet rows.
    """
    rows = []

    for _, row in df.iterrows():
        period_end = pd.to_datetime(row["period_end"])

        # Map cash and equivalents
        cash = _get_field_value(
            row, ["cash_and_cash_equivalents", "cash_and_short_term_investments", "cash"]
        )
        if cash is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.BALANCE.value,
                    "line_item": "cash_and_equivalents",
                    "value": float(cash),
                    "currency": currency,
                    "source": source,
                }
            )

        # Map total debt (try total_debt first, then sum of short + long)
        total_debt = _get_field_value(row, ["total_debt"])
        if total_debt is None:
            short_debt = _get_field_value(row, ["short_term_debt", "short_term_debt_and_capital_lease_obligation"])
            long_debt = _get_field_value(row, ["long_term_debt", "long_term_debt_and_capital_lease_obligation"])
            if short_debt is not None and long_debt is not None:
                total_debt = short_debt + long_debt
            elif short_debt is not None:
                total_debt = short_debt
            elif long_debt is not None:
                total_debt = long_debt

        if total_debt is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.BALANCE.value,
                    "line_item": "total_debt",
                    "value": float(total_debt),
                    "currency": currency,
                    "source": source,
                }
            )

    return rows


def _map_cash_flow(df: pd.DataFrame, ticker: str, currency: str, source: str) -> list[dict[str, any]]:
    """Map FMP cash flow statement to canonical schema.

    Args:
        df: FMP cash flow statement DataFrame.
        ticker: Stock ticker symbol.
        currency: Currency code.
        source: Source identifier.

    Returns:
        List of dictionaries representing standardized cash flow rows.
    """
    rows = []

    for _, row in df.iterrows():
        period_end = pd.to_datetime(row["period_end"])

        # Map cash from operations (CFO)
        cfo = _get_field_value(
            row,
            [
                "operating_cash_flow",
                "cash_flow_from_operating_activities",
                "net_cash_flow_from_operating_activities",
            ],
        )
        if cfo is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.CASHFLOW.value,
                    "line_item": "cfo",
                    "value": float(cfo),
                    "currency": currency,
                    "source": source,
                }
            )

        # Map capital expenditures (capex) - note: capex is typically negative
        capex = _get_field_value(
            row,
            [
                "capital_expenditure",
                "capital_expenditures",
                "purchases_of_property_plant_and_equipment",
            ],
        )
        if capex is not None:
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.CASHFLOW.value,
                    "line_item": "capex",
                    "value": float(capex),  # Keep sign as-is (typically negative)
                    "currency": currency,
                    "source": source,
                }
            )

    return rows


def _get_field_value(row: pd.Series, field_names: list[str]) -> float | None:
    """Get value from row using multiple possible field names.

    Args:
        row: DataFrame row (Series).
        field_names: List of possible field names to try.

    Returns:
        Field value if found, None otherwise.
    """
    for field_name in field_names:
        if field_name in row.index:
            value = row[field_name]
            if pd.notna(value) and value != 0:
                return float(value)
    return None


def _validate_core_fields(df: pd.DataFrame, ticker: str) -> None:
    """Validate that required core fields exist in the standardized data.

    Args:
        df: Standardized DataFrame.
        ticker: Stock ticker symbol (for error messages).

    Raises:
        ValueError: If required core fields are missing.
    """
    income_df = df[df["statement"] == StatementType.INCOME.value]
    cash_df = df[df["statement"] == StatementType.CASHFLOW.value]

    # Check for revenue
    if income_df[income_df["line_item"] == "revenue"].empty:
        raise ValueError(f"Missing required field 'revenue' for ticker {ticker}")

    # Check for operating income or EBIT
    if income_df[income_df["line_item"] == "operating_income"].empty:
        raise ValueError(f"Missing required field 'operating_income' (or EBIT) for ticker {ticker}")

    # Check for CFO
    if cash_df[cash_df["line_item"] == "cfo"].empty:
        raise ValueError(f"Missing required field 'cfo' (operating cash flow) for ticker {ticker}")

    # Check for capex
    if cash_df[cash_df["line_item"] == "capex"].empty:
        raise ValueError(f"Missing required field 'capex' (capital expenditures) for ticker {ticker}")

