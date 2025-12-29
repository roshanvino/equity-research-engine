"""Abstract base class for financial data providers."""

from abc import ABC, abstractmethod

import pandas as pd


class FinancialsProvider(ABC):
    """Abstract interface for fetching financial statements.

    All providers must implement methods to fetch income statement,
    balance sheet, and cash flow statement data.
    """

    @abstractmethod
    def get_income_statement(self, ticker: str) -> pd.DataFrame:
        """Fetch income statement data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with income statement data. Must include a 'period_end'
            column as datetime type. Other columns are provider-specific.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        pass

    @abstractmethod
    def get_balance_sheet(self, ticker: str) -> pd.DataFrame:
        """Fetch balance sheet data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with balance sheet data. Must include a 'period_end'
            column as datetime type. Other columns are provider-specific.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        pass

    @abstractmethod
    def get_cash_flow(self, ticker: str) -> pd.DataFrame:
        """Fetch cash flow statement data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with cash flow statement data. Must include a 'period_end'
            column as datetime type. Other columns are provider-specific.

        Raises:
            ValueError: If ticker is invalid or data unavailable.
            RuntimeError: If API call fails.
        """
        pass

