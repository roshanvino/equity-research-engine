"""Tests for schema validation."""

import pandas as pd
import pytest

from hf_memo.standardize.schema import (
    STANDARD_COLUMNS,
    StatementType,
    create_empty_standard_df,
    validate_standard_df,
)


def test_create_empty_standard_df() -> None:
    """Test creation of empty standard dataframe."""
    df = create_empty_standard_df()

    assert list(df.columns) == STANDARD_COLUMNS
    assert len(df) == 0


def test_validate_standard_df_valid() -> None:
    """Test validation of valid standard dataframe."""
    df = pd.DataFrame({
        "ticker": ["AAPL"],
        "period_end": [pd.Timestamp("2023-12-31")],
        "statement": ["income"],
        "line_item": ["revenue"],
        "value": [1000000.0],
        "currency": ["USD"],
        "source": ["fmp"],
    })

    # Should not raise
    validate_standard_df(df)


def test_validate_standard_df_missing_column() -> None:
    """Test validation fails with missing column."""
    df = pd.DataFrame({
        "ticker": ["AAPL"],
        "period_end": [pd.Timestamp("2023-12-31")],
        "statement": ["income"],
        "line_item": ["revenue"],
        "value": [1000000.0],
        "currency": ["USD"],
        # Missing "source"
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_standard_df(df)


def test_validate_standard_df_wrong_type() -> None:
    """Test validation fails with wrong data type."""
    df = pd.DataFrame({
        "ticker": ["AAPL"],
        "period_end": ["2023-12-31"],  # Should be datetime
        "statement": ["income"],
        "line_item": ["revenue"],
        "value": [1000000.0],
        "currency": ["USD"],
        "source": ["fmp"],
    })

    with pytest.raises(ValueError, match="must be datetime"):
        validate_standard_df(df)

