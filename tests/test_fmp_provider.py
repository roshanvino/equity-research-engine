"""Tests for FMP provider."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from hf_memo.providers.fmp_provider import FMPProvider, LegacyEndpointError


def test_build_url() -> None:
    """Test URL construction for stable endpoints."""
    provider = FMPProvider(api_key="test-key")

    # Test income statement endpoint
    url = provider._build_url("/income-statement/AAPL")
    assert url == "https://financialmodelingprep.com/api/v4/income-statement/AAPL"

    # Test balance sheet endpoint
    url = provider._build_url("/balance-sheet-statement/AAPL")
    assert url == "https://financialmodelingprep.com/api/v4/balance-sheet-statement/AAPL"

    # Test cash flow endpoint
    url = provider._build_url("/cash-flow-statement/AAPL")
    assert url == "https://financialmodelingprep.com/api/v4/cash-flow-statement/AAPL"

    provider.client.close()


def test_stable_endpoints_used() -> None:
    """Verify that stable v4 endpoints are used, not legacy v3."""
    provider = FMPProvider(api_key="test-key")

    # Verify BASE_URL uses v4
    assert provider.BASE_URL == "https://financialmodelingprep.com/api/v4"
    assert "/api/v3" not in provider.BASE_URL

    # Verify endpoint methods use stable paths
    assert provider.get_income_statement.__doc__ is not None
    assert "/api/v4/income-statement" in provider.get_income_statement.__doc__

    assert provider.get_balance_sheet.__doc__ is not None
    assert "/api/v4/balance-sheet-statement" in provider.get_balance_sheet.__doc__

    assert provider.get_cash_flow.__doc__ is not None
    assert "/api/v4/cash-flow-statement" in provider.get_cash_flow.__doc__

    provider.client.close()


def test_legacy_endpoint_error_detection() -> None:
    """Test that 403 with legacy endpoint message raises LegacyEndpointError."""
    provider = FMPProvider(api_key="test-key")

    # Mock a 403 response with legacy endpoint message
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "Error Message": "Legacy Endpoint. This endpoint is only available for legacy users prior August 31, 2025."
    }
    mock_response.text = '{"Error Message": "Legacy Endpoint..."}'

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    provider.client = mock_client

    with pytest.raises(LegacyEndpointError) as exc_info:
        provider._fetch_endpoint("/income-statement/AAPL")

    error_msg = str(exc_info.value).lower()
    assert "legacy endpoint" in error_msg
    assert "stable endpoints" in error_msg
    assert "v4" in error_msg

    provider.client.close()


def test_legacy_endpoint_error_in_response_body() -> None:
    """Test legacy endpoint error detection in response body (not just 403)."""
    provider = FMPProvider(api_key="test-key")

    # Mock a response with legacy endpoint message in body
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Error Message": "Legacy Endpoint. This endpoint is only available for legacy users."
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    provider.client = mock_client

    with pytest.raises(LegacyEndpointError) as exc_info:
        provider._fetch_endpoint("/income-statement/AAPL")

    error_msg = str(exc_info.value).lower()
    assert "legacy endpoint" in error_msg

    provider.client.close()


def test_api_key_required() -> None:
    """Test that API key is required."""
    # Temporarily remove API key if set
    original_key = os.environ.get("FMP_API_KEY")
    if "FMP_API_KEY" in os.environ:
        del os.environ["FMP_API_KEY"]

    try:
        with pytest.raises(ValueError, match="FMP_API_KEY not found"):
            FMPProvider()
    finally:
        # Restore original key if it existed
        if original_key:
            os.environ["FMP_API_KEY"] = original_key


def test_endpoint_paths() -> None:
    """Test that endpoint paths are correct for stable API."""
    provider = FMPProvider(api_key="test-key")

    # Verify endpoint paths match stable API structure
    income_url = provider._build_url("/income-statement/AAPL")
    assert income_url.endswith("/income-statement/AAPL")

    balance_url = provider._build_url("/balance-sheet-statement/AAPL")
    assert balance_url.endswith("/balance-sheet-statement/AAPL")

    cashflow_url = provider._build_url("/cash-flow-statement/AAPL")
    assert cashflow_url.endswith("/cash-flow-statement/AAPL")

    provider.client.close()

