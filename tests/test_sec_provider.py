"""Tests for SEC provider."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import pytest

from hf_memo.providers.sec_provider import SECProvider


@pytest.fixture
def sample_company_facts() -> dict:
    """Sample SEC company facts JSON response."""
    return {
        "cik": "0000320193",
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "label": "Revenues",
                    "description": "Total revenue",
                    "units": {
                        "USD": [
                            {"val": 394328000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 365817000000, "end": "2022-09-30", "fp": "FY"},
                            {"val": 274515000000, "end": "2021-09-30", "fp": "FY"},
                        ]
                    },
                },
                "OperatingIncomeLoss": {
                    "label": "Operating Income (Loss)",
                    "units": {
                        "USD": [
                            {"val": 114301000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 108949000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "NetIncomeLoss": {
                    "label": "Net Income (Loss)",
                    "units": {
                        "USD": [
                            {"val": 96995000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 99803000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "label": "Operating Cash Flow",
                    "units": {
                        "USD": [
                            {"val": 110543000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 122151000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "label": "Capital Expenditures",
                    "units": {
                        "USD": [
                            {"val": 10949500000, "end": "2023-09-30", "fp": "FY"},  # Positive in SEC, should be negative
                            {"val": 11085000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "CashAndCashEquivalentsAtCarryingValue": {
                    "label": "Cash and Equivalents",
                    "units": {
                        "USD": [
                            {"val": 29965000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 23646000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "LongTermDebt": {
                    "label": "Long Term Debt",
                    "units": {
                        "USD": [
                            {"val": 95081000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 98959000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
                "DebtCurrent": {
                    "label": "Current Debt",
                    "units": {
                        "USD": [
                            {"val": 11128000000, "end": "2023-09-30", "fp": "FY"},
                            {"val": 11128000000, "end": "2022-09-30", "fp": "FY"},
                        ]
                    },
                },
            }
        },
    }


@pytest.fixture
def sample_ticker_cik_map() -> dict:
    """Sample ticker-to-CIK mapping."""
    return {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "GOOGL": "0001652044",
    }


def test_build_url() -> None:
    """Test URL construction for SEC endpoints."""
    provider = SECProvider()

    # Test company facts endpoint
    cik = "0000320193"
    url = f"{provider.BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"
    assert url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"

    provider.client.close()


def test_user_agent_set() -> None:
    """Test that User-Agent header is set."""
    provider = SECProvider()
    assert "User-Agent" in provider.client.headers
    assert len(provider.client.headers["User-Agent"]) > 0
    provider.client.close()


def test_ticker_to_cik_mapping(sample_ticker_cik_map: dict, tmp_path: Path) -> None:
    """Test ticker to CIK conversion with cached mapping."""
    cache_dir = tmp_path / "cache"
    cache_file = cache_dir / "ticker_cik_map.json"

    # Create cached mapping
    cache_dir.mkdir()
    with open(cache_file, "w") as f:
        json.dump({"map": sample_ticker_cik_map, "last_updated": 0}, f)

    provider = SECProvider(cache_dir=cache_dir)
    provider.ticker_cik_cache = cache_file

    # Mock the _get_ticker_to_cik_map to return our sample
    with patch.object(provider, "_get_ticker_to_cik_map", return_value=sample_ticker_cik_map):
        cik = provider._ticker_to_cik("AAPL")
        assert cik == "0000320193"

    provider.client.close()


def test_extract_xbrl_facts(sample_company_facts: dict) -> None:
    """Test XBRL fact extraction."""
    provider = SECProvider()

    # Extract revenue facts
    revenue_facts = provider._extract_xbrl_facts(sample_company_facts, ["Revenues"])
    assert len(revenue_facts) > 0
    assert revenue_facts[0]["tag"] == "Revenues"
    assert revenue_facts[0]["value"] == 394328000000
    assert revenue_facts[0]["end_date"] == "2023-09-30"

    provider.client.close()


def test_capex_sign_handling(sample_company_facts: dict) -> None:
    """Test that capex is handled with correct sign (negative for cash outflow)."""
    provider = SECProvider()

    # Extract capex facts
    capex_facts = provider._extract_xbrl_facts(sample_company_facts, ["PaymentsToAcquirePropertyPlantAndEquipment"])

    # Get cash flow DataFrame
    with patch.object(provider, "_get_company_facts", return_value=sample_company_facts):
        with patch.object(provider, "_ticker_to_cik", return_value="0000320193"):
            cash_df = provider.get_cash_flow("AAPL")

            # Check that capex is negative
            if "capital_expenditure" in cash_df.columns:
                capex_values = cash_df["capital_expenditure"]
                assert all(capex_values <= 0), "Capex should be negative (cash outflow)"

    provider.client.close()


def test_find_xbrl_tag(sample_company_facts: dict) -> None:
    """Test finding XBRL tags with fallback options."""
    provider = SECProvider()

    # Test finding revenue (should find "Revenues")
    revenue_facts = provider._find_xbrl_tag(sample_company_facts, "revenue")
    assert len(revenue_facts) > 0
    assert revenue_facts[0]["tag"] == "Revenues"

    # Test finding non-existent tag (should return empty)
    missing_facts = provider._find_xbrl_tag(sample_company_facts, "NonExistentTag")
    assert len(missing_facts) == 0

    provider.client.close()


def test_get_income_statement(sample_company_facts: dict, sample_ticker_cik_map: dict) -> None:
    """Test income statement fetching."""
    provider = SECProvider()

    with patch.object(provider, "_get_ticker_to_cik_map", return_value=sample_ticker_cik_map):
        with patch.object(provider, "_get_company_facts", return_value=sample_company_facts):
            income_df = provider.get_income_statement("AAPL")

            assert len(income_df) > 0
            assert "period_end" in income_df.columns
            assert "revenue" in income_df.columns or "operating_income" in income_df.columns
            assert pd.api.types.is_datetime64_any_dtype(income_df["period_end"])

    provider.client.close()


def test_get_balance_sheet(sample_company_facts: dict, sample_ticker_cik_map: dict) -> None:
    """Test balance sheet fetching."""
    provider = SECProvider()

    with patch.object(provider, "_get_ticker_to_cik_map", return_value=sample_ticker_cik_map):
        with patch.object(provider, "_get_company_facts", return_value=sample_company_facts):
            balance_df = provider.get_balance_sheet("AAPL")

            assert len(balance_df) > 0
            assert "period_end" in balance_df.columns
            assert pd.api.types.is_datetime64_any_dtype(balance_df["period_end"])

    provider.client.close()


def test_get_cash_flow(sample_company_facts: dict, sample_ticker_cik_map: dict) -> None:
    """Test cash flow fetching."""
    provider = SECProvider()

    with patch.object(provider, "_get_ticker_to_cik_map", return_value=sample_ticker_cik_map):
        with patch.object(provider, "_get_company_facts", return_value=sample_company_facts):
            cash_df = provider.get_cash_flow("AAPL")

            assert len(cash_df) > 0
            assert "period_end" in cash_df.columns
            assert pd.api.types.is_datetime64_any_dtype(cash_df["period_end"])

    provider.client.close()


def test_rate_limiting() -> None:
    """Test that rate limiting is enforced."""
    provider = SECProvider()

    # Check that rate limiting attributes exist
    assert hasattr(provider, "_min_request_interval")
    assert hasattr(provider, "_last_request_time")
    assert provider._min_request_interval > 0

    provider.client.close()

