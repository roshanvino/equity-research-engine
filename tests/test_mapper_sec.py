"""Tests for SEC mapper."""

import pandas as pd
import pytest

from hf_memo.standardize.mapper_sec import standardize_sec
from hf_memo.standardize.schema import StatementType, validate_standard_df


def test_standardize_sec_basic() -> None:
    """Test basic SEC standardization."""
    income_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30", "2022-09-30"]),
        "revenue": [394328000000, 365817000000],
        "operating_income": [114301000000, 108949000000],
        "net_income": [96995000000, 99803000000],
        "currency": ["USD", "USD"],
    })

    balance_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30", "2022-09-30"]),
        "cash_and_equivalents": [29965000000, 23646000000],
        "total_debt": [106209000000, 110087000000],
        "currency": ["USD", "USD"],
    })

    cash_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30", "2022-09-30"]),
        "operating_cash_flow": [110543000000, 122151000000],
        "capital_expenditure": [-10949500000, -11085000000],
        "currency": ["USD", "USD"],
    })

    standardized = standardize_sec(income_df, balance_df, cash_df, "AAPL", source="sec")

    # Validate schema
    validate_standard_df(standardized)

    # Check required columns
    assert "ticker" in standardized.columns
    assert "period_end" in standardized.columns
    assert "statement" in standardized.columns
    assert "line_item" in standardized.columns
    assert "value" in standardized.columns
    assert "currency" in standardized.columns
    assert "source" in standardized.columns

    # Check required line items exist
    income_data = standardized[standardized["statement"] == StatementType.INCOME.value]
    assert not income_data[income_data["line_item"] == "revenue"].empty
    assert not income_data[income_data["line_item"] == "operating_income"].empty

    cash_data = standardized[standardized["statement"] == StatementType.CASHFLOW.value]
    assert not cash_data[cash_data["line_item"] == "cfo"].empty
    assert not cash_data[cash_data["line_item"] == "capex"].empty


def test_capex_sign_handling() -> None:
    """Test that capex sign is handled correctly (negative for cash outflow)."""
    income_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "revenue": [394328000000],
        "operating_income": [114301000000],
        "net_income": [96995000000],
        "currency": ["USD"],
    })

    balance_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "cash_and_equivalents": [29965000000],
        "total_debt": [106209000000],
        "currency": ["USD"],
    })

    # Test with positive capex (should be converted to negative)
    cash_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "operating_cash_flow": [110543000000],
        "capital_expenditure": [10949500000],  # Positive value
        "currency": ["USD"],
    })

    standardized = standardize_sec(income_df, balance_df, cash_df, "AAPL", source="sec")

    capex_values = standardized[
        (standardized["statement"] == StatementType.CASHFLOW.value)
        & (standardized["line_item"] == "capex")
    ]["value"]

    # Capex should be negative (cash outflow)
    assert all(capex_values <= 0), "Capex should be negative (cash outflow)"


def test_missing_required_fields() -> None:
    """Test that missing required fields raise appropriate errors."""
    # Missing revenue
    income_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "operating_income": [114301000000],
        "net_income": [96995000000],
        "currency": ["USD"],
    })

    balance_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "cash_and_equivalents": [29965000000],
        "total_debt": [106209000000],
        "currency": ["USD"],
    })

    cash_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "operating_cash_flow": [110543000000],
        "capital_expenditure": [-10949500000],
        "currency": ["USD"],
    })

    with pytest.raises(ValueError, match="Missing required fields"):
        standardize_sec(income_df, balance_df, cash_df, "AAPL", source="sec")


def test_insufficient_periods() -> None:
    """Test that insufficient periods raise appropriate errors."""
    # Only one period (need at least 2)
    income_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "revenue": [394328000000],
        "operating_income": [114301000000],
        "net_income": [96995000000],
        "currency": ["USD"],
    })

    balance_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "cash_and_equivalents": [29965000000],
        "total_debt": [106209000000],
        "currency": ["USD"],
    })

    cash_df = pd.DataFrame({
        "period_end": pd.to_datetime(["2023-09-30"]),
        "operating_cash_flow": [110543000000],
        "capital_expenditure": [-10949500000],
        "currency": ["USD"],
    })

    with pytest.raises(ValueError, match="Insufficient.*periods"):
        standardize_sec(income_df, balance_df, cash_df, "AAPL", source="sec")

