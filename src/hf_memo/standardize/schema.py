"""Canonical schema definitions for financial statements.

This module defines the standardized line items we care about for the MVP
and the long-format dataframe structure for storing financial data.
"""

from enum import Enum
from typing import Literal

import pandas as pd


class StatementType(str, Enum):
    """Types of financial statements."""

    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


# Canonical line items for MVP
CANONICAL_LINE_ITEMS = {
    StatementType.INCOME: {
        "revenue": "Total revenue",
        "operating_income": "Operating income (EBIT)",
        "net_income": "Net income",
    },
    StatementType.CASHFLOW: {
        "cfo": "Cash from operations",
        "capex": "Capital expenditures",
    },
    StatementType.BALANCE: {
        "cash_and_equivalents": "Cash and cash equivalents",
        "total_debt": "Total debt",
    },
}


# Long-format standard dataframe columns
STANDARD_COLUMNS = [
    "ticker",
    "period_end",
    "statement",
    "line_item",
    "value",
    "currency",
    "source",
]


def create_empty_standard_df() -> pd.DataFrame:
    """Create an empty dataframe with the standard column structure.

    Returns:
        Empty DataFrame with columns: ticker, period_end, statement, line_item, value, currency, source.
    """
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def validate_standard_df(df: pd.DataFrame) -> bool:
    """Validate that a dataframe conforms to the standard schema.

    Args:
        df: DataFrame to validate.

    Returns:
        True if valid, raises ValueError otherwise.

    Raises:
        ValueError: If dataframe doesn't have required columns or has invalid data types.
    """
    missing_cols = set(STANDARD_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Validate data types
    if not pd.api.types.is_string_dtype(df["ticker"]):
        raise ValueError("Column 'ticker' must be string type")
    if not pd.api.types.is_datetime64_any_dtype(df["period_end"]):
        raise ValueError("Column 'period_end' must be datetime type")
    if not pd.api.types.is_string_dtype(df["statement"]):
        raise ValueError("Column 'statement' must be string type")
    if not pd.api.types.is_string_dtype(df["line_item"]):
        raise ValueError("Column 'line_item' must be string type")
    if not pd.api.types.is_numeric_dtype(df["value"]):
        raise ValueError("Column 'value' must be numeric type")
    if not pd.api.types.is_string_dtype(df["currency"]):
        raise ValueError("Column 'currency' must be string type")
    if not pd.api.types.is_string_dtype(df["source"]):
        raise ValueError("Column 'source' must be string type")

    return True

