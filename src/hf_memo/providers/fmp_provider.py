"""Financial Modeling Prep (FMP) API provider for financial statements."""

import os
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from hf_memo.providers.base import FinancialsProvider


class FMPProvider(FinancialsProvider):
    """Provider for fetching financial data from Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize FMP provider.

        Args:
            api_key: FMP API key. If None, reads from FMP_API_KEY environment variable.

        Raises:
            ValueError: If API key is not provided and not found in environment.
        """
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FMP_API_KEY not found. Please set it as an environment variable:\n"
                "  export FMP_API_KEY='your-api-key'\n"
                "Or pass it directly to FMPProvider(api_key='your-api-key')"
            )
        self.client = httpx.Client(timeout=30.0)

    def _fetch_endpoint(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch data from FMP API endpoint.

        Args:
            endpoint: API endpoint path (e.g., '/income-statement/AAPL').
            params: Optional query parameters.

        Returns:
            List of dictionaries containing JSON response data.

        Raises:
            RuntimeError: If API call fails or returns error.
            ValueError: If response is invalid.
        """
        url = f"{self.BASE_URL}{endpoint}"
        query_params = {"apikey": self.api_key, "period": "annual", "limit": 5}
        if params:
            query_params.update(params)

        try:
            response = self.client.get(url, params=query_params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "Error Message" in data:
                raise RuntimeError(f"FMP API error: {data['Error Message']}")

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format from FMP API: {type(data)}")

            return data
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"FMP API HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"FMP API request failed: {str(e)}")

    def _normalize_dataframe(self, data: list[dict[str, Any]], ticker: str) -> pd.DataFrame:
        """Convert FMP JSON response to normalized DataFrame.

        Args:
            data: List of dictionaries from FMP API.
            ticker: Ticker symbol for the data.

        Returns:
            DataFrame with normalized column names and period_end as datetime.
        """
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Normalize column names: convert camelCase to snake_case
        df.columns = [self._camel_to_snake(col) for col in df.columns]

        # Ensure period_end column exists and is datetime
        if "date" in df.columns:
            df["period_end"] = pd.to_datetime(df["date"])
            df = df.drop(columns=["date"])
        elif "period_end" not in df.columns:
            raise ValueError("FMP response missing 'date' or 'period_end' column")

        # Add ticker if not present
        if "symbol" not in df.columns:
            df["symbol"] = ticker

        # Extract currency if present
        if "currency" in df.columns:
            df["currency"] = df["currency"].fillna("USD")
        else:
            df["currency"] = "USD"

        return df

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case.

        Args:
            name: CamelCase string.

        Returns:
            snake_case string.
        """
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def get_income_statement(self, ticker: str) -> pd.DataFrame:
        """Fetch income statement data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with income statement data, including 'period_end' as datetime.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        endpoint = f"/income-statement/{ticker.upper()}"
        data = self._fetch_endpoint(endpoint)
        if not data:
            raise ValueError(f"No income statement data found for ticker: {ticker}")

        return self._normalize_dataframe(data, ticker.upper())

    def get_balance_sheet(self, ticker: str) -> pd.DataFrame:
        """Fetch balance sheet data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with balance sheet data, including 'period_end' as datetime.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        endpoint = f"/balance-sheet-statement/{ticker.upper()}"
        data = self._fetch_endpoint(endpoint)
        if not data:
            raise ValueError(f"No balance sheet data found for ticker: {ticker}")

        return self._normalize_dataframe(data, ticker.upper())

    def get_cash_flow(self, ticker: str) -> pd.DataFrame:
        """Fetch cash flow statement data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with cash flow statement data, including 'period_end' as datetime.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        endpoint = f"/cash-flow-statement/{ticker.upper()}"
        data = self._fetch_endpoint(endpoint)
        if not data:
            raise ValueError(f"No cash flow statement data found for ticker: {ticker}")

        return self._normalize_dataframe(data, ticker.upper())

    def __enter__(self) -> "FMPProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close HTTP client."""
        self.client.close()

