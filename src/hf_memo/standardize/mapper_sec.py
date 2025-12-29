"""Mapper to convert SEC provider data to canonical schema."""

import pandas as pd

from hf_memo.standardize.schema import (
    STANDARD_COLUMNS,
    StatementType,
    validate_standard_df,
)


def standardize_sec(
    raw_income_df: pd.DataFrame,
    raw_balance_df: pd.DataFrame,
    raw_cash_df: pd.DataFrame,
    ticker: str,
    source: str = "sec",
) -> pd.DataFrame:
    """Convert SEC provider dataframes to canonical long-format schema.

    Args:
        raw_income_df: SEC income statement DataFrame.
        raw_balance_df: SEC balance sheet DataFrame.
        raw_cash_df: SEC cash flow statement DataFrame.
        ticker: Stock ticker symbol.
        source: Source identifier (default: "sec").

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
    """Map SEC income statement to canonical schema.

    Args:
        df: SEC income statement DataFrame.
        ticker: Stock ticker symbol.
        currency: Currency code.
        source: Source identifier.

    Returns:
        List of dictionaries representing standardized income statement rows.
    """
    rows = []

    for _, row in df.iterrows():
        period_end = pd.to_datetime(row["period_end"])

        # Map revenue
        revenue = _get_field_value(row, ["revenue"])
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

        # Map operating income
        operating_income = _get_field_value(row, ["operating_income"])
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
        net_income = _get_field_value(row, ["net_income"])
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
    """Map SEC balance sheet to canonical schema.

    Args:
        df: SEC balance sheet DataFrame.
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
        cash = _get_field_value(row, ["cash_and_equivalents"])
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

        # Map total debt
        total_debt = _get_field_value(row, ["total_debt"])
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
    """Map SEC cash flow statement to canonical schema.

    Args:
        df: SEC cash flow statement DataFrame.
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
        cfo = _get_field_value(row, ["operating_cash_flow"])
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

        # Map capital expenditures (capex) - note: capex should be negative (cash outflow)
        capex = _get_field_value(row, ["capital_expenditure"])
        if capex is not None:
            # Ensure capex is negative (cash outflow)
            capex_val = float(capex)
            if capex_val > 0:
                capex_val = -capex_val
            rows.append(
                {
                    "ticker": ticker,
                    "period_end": period_end,
                    "statement": StatementType.CASHFLOW.value,
                    "line_item": "capex",
                    "value": capex_val,
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

    missing_fields = []

    # Check for revenue
    if income_df[income_df["line_item"] == "revenue"].empty:
        missing_fields.append("revenue")

    # Check for operating income or net income (at least one)
    has_operating_income = not income_df[income_df["line_item"] == "operating_income"].empty
    has_net_income = not income_df[income_df["line_item"] == "net_income"].empty
    if not has_operating_income and not has_net_income:
        missing_fields.append("operating_income or net_income")

    # Check for CFO
    if cash_df[cash_df["line_item"] == "cfo"].empty:
        missing_fields.append("cfo (operating cash flow)")

    # Check for capex
    if cash_df[cash_df["line_item"] == "capex"].empty:
        missing_fields.append("capex (capital expenditures)")

    if missing_fields:
        raise ValueError(
            f"Missing required fields for ticker {ticker}: {', '.join(missing_fields)}\n"
            f"Please verify the company has filed annual reports with SEC containing these line items."
        )

