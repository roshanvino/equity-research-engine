"""SEC EDGAR API provider for financial statements using public XBRL data."""

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from hf_memo.providers.base import FinancialsProvider


class SECProvider(FinancialsProvider):
    """Provider for fetching financial data from SEC EDGAR public APIs.

    Uses SEC's Company Facts API to extract XBRL financial data.
    No API key required - uses public SEC EDGAR endpoints.
    """

    BASE_URL = "https://data.sec.gov"
    TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
    USER_AGENT = "hf-memo research tool (contact@example.com)"  # SEC requires descriptive User-Agent

    # XBRL tag mappings: canonical line item -> possible XBRL tag names
    XBRL_TAG_MAPPINGS = {
        "revenue": [
            "Revenues",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ],
        "operating_income": [
            "OperatingIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
        "net_income": [
            "NetIncomeLoss",
            "ProfitLoss",
            "IncomeLossFromContinuingOperations",
        ],
        "cfo": [
            "NetCashProvidedByUsedInOperatingActivities",
            "CashFlowFromOperatingActivities",
        ],
        "capex": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "CapitalExpenditures",
            "PaymentsToAcquireProductiveAssets",
        ],
        "cash_and_equivalents": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsAndShortTermInvestments",
        ],
        "total_debt": [
            "Debt",
            "LongTermDebtAndCapitalLeaseObligations",
        ],
        "long_term_debt": [
            "LongTermDebt",
            "LongTermDebtAndCapitalLeaseObligations",
        ],
        "short_term_debt": [
            "DebtCurrent",
            "ShortTermBorrowings",
        ],
    }

    def __init__(self, cache_dir: Path | str | None = None, user_agent: str | None = None) -> None:
        """Initialize SEC provider.

        Args:
            cache_dir: Directory to cache ticker-to-CIK mapping. Defaults to .cache/ in project root.
            user_agent: User-Agent string for SEC API requests. Defaults to descriptive string.
        """
        self.user_agent = user_agent or self.USER_AGENT
        self.client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
        )

        # Set up cache directory
        if cache_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            cache_dir = project_root / ".cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ticker_cik_cache = self.cache_dir / "ticker_cik_map.json"
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # SEC recommends 10 requests/second max

    def _rate_limit(self) -> None:
        """Enforce rate limiting for SEC API requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()

    def _get_ticker_to_cik_map(self) -> dict[str, str]:
        """Get ticker to CIK mapping, with local caching.

        Returns:
            Dictionary mapping ticker -> CIK (as 10-digit zero-padded string).
        """
        # Check cache first
        if self.ticker_cik_cache.exists():
            try:
                with open(self.ticker_cik_cache, "r") as f:
                    cached_data = json.load(f)
                    # Check if cache is recent (refresh daily)
                    if "last_updated" in cached_data:
                        cache_age = time.time() - cached_data.get("last_updated", 0)
                        if cache_age < 86400:  # 24 hours
                            return cached_data.get("map", {})
            except (json.JSONDecodeError, KeyError):
                pass  # Cache invalid, re-download

        # Download from SEC
        self._rate_limit()
        try:
            response = self.client.get(self.TICKER_CIK_URL)
            response.raise_for_status()
            data = response.json()

            # SEC returns a list of dicts with keys: cik_str, ticker, title
            ticker_cik_map = {}
            for entry in data.values() if isinstance(data, dict) else data:
                if isinstance(entry, dict):
                    ticker = entry.get("ticker", "").upper()
                    cik_str = str(entry.get("cik_str", ""))
                    if ticker and cik_str:
                        # Pad CIK to 10 digits
                        cik_padded = cik_str.zfill(10)
                        ticker_cik_map[ticker] = cik_padded

            # Save to cache
            cache_data = {
                "map": ticker_cik_map,
                "last_updated": time.time(),
            }
            with open(self.ticker_cik_cache, "w") as f:
                json.dump(cache_data, f)

            return ticker_cik_map
        except Exception as e:
            # If download fails and cache exists, use stale cache
            if self.ticker_cik_cache.exists():
                try:
                    with open(self.ticker_cik_cache, "r") as f:
                        cached_data = json.load(f)
                        return cached_data.get("map", {})
                except (json.JSONDecodeError, KeyError):
                    pass
            raise RuntimeError(f"Failed to fetch ticker-to-CIK mapping: {e}") from e

    def _ticker_to_cik(self, ticker: str) -> str:
        """Convert ticker symbol to CIK.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            10-digit zero-padded CIK string.

        Raises:
            ValueError: If ticker not found in SEC database.
        """
        ticker_map = self._get_ticker_to_cik_map()
        ticker_upper = ticker.upper()
        if ticker_upper not in ticker_map:
            raise ValueError(
                f"Ticker '{ticker}' not found in SEC database. "
                f"Please verify the ticker symbol is correct."
            )
        return ticker_map[ticker_upper]

    def _get_company_facts(self, cik: str) -> dict[str, Any]:
        """Fetch company facts (XBRL data) from SEC.

        Args:
            cik: 10-digit zero-padded CIK.

        Returns:
            Dictionary containing company facts JSON data.

        Raises:
            RuntimeError: If API call fails.
        """
        self._rate_limit()
        url = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"

        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Company with CIK {cik} not found in SEC database") from e
            raise RuntimeError(f"SEC API HTTP error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"SEC API request failed: {str(e)}") from e

    def _extract_xbrl_facts(
        self, company_facts: dict[str, Any], tag_names: list[str], units_preference: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Extract XBRL facts for given tag names.

        Args:
            company_facts: Company facts JSON from SEC API.
            tag_names: List of XBRL tag names to search for.
            units_preference: Preferred units (e.g., ['USD', 'usd']). Defaults to USD.

        Returns:
            List of fact dictionaries with keys: tag, value, end_date, units.
        """
        if units_preference is None:
            units_preference = ["USD", "usd"]

        facts = company_facts.get("facts", {})
        us_gaap = facts.get("us-gaap", {})
        dei = facts.get("dei", {})  # Document and Entity Information

        extracted = []
        for tag_name in tag_names:
            # Try us-gaap first
            if tag_name in us_gaap:
                tag_data = us_gaap[tag_name]
                units = tag_data.get("units", {})
                # Prefer USD units
                for unit_pref in units_preference:
                    if unit_pref in units:
                        for fact in units[unit_pref]:
                            if fact.get("fp") == "FY":  # Annual (FY = Fiscal Year)
                                extracted.append(
                                    {
                                        "tag": tag_name,
                                        "value": fact.get("val"),
                                        "end_date": fact.get("end"),
                                        "units": unit_pref,
                                    }
                                )
                                break
                        if extracted and extracted[-1]["tag"] == tag_name:
                            break
                # If no preferred unit found, use first available
                if not any(e["tag"] == tag_name for e in extracted) and units:
                    first_unit = list(units.keys())[0]
                    for fact in units[first_unit]:
                        if fact.get("fp") == "FY":
                            extracted.append(
                                {
                                    "tag": tag_name,
                                    "value": fact.get("val"),
                                    "end_date": fact.get("end"),
                                    "units": first_unit,
                                }
                            )
                            break

        return extracted

    def _find_xbrl_tag(self, company_facts: dict[str, Any], canonical_item: str) -> list[dict[str, Any]]:
        """Find XBRL facts for a canonical line item.

        Args:
            company_facts: Company facts JSON from SEC API.
            canonical_item: Canonical line item name (e.g., 'revenue').

        Returns:
            List of fact dictionaries, or empty list if not found.
        """
        tag_candidates = self.XBRL_TAG_MAPPINGS.get(canonical_item, [])
        for tag_name in tag_candidates:
            facts = self._extract_xbrl_facts(company_facts, [tag_name])
            if facts:
                return facts
        return []

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
        cik = self._ticker_to_cik(ticker)
        company_facts = self._get_company_facts(cik)

        # Extract revenue, operating income, net income
        revenue_facts = self._find_xbrl_tag(company_facts, "revenue")
        operating_income_facts = self._find_xbrl_tag(company_facts, "operating_income")
        net_income_facts = self._find_xbrl_tag(company_facts, "net_income")

        # Build DataFrame
        rows = []
        all_dates = set()
        for facts in [revenue_facts, operating_income_facts, net_income_facts]:
            for fact in facts:
                all_dates.add(fact["end_date"])

        for date in sorted(all_dates, reverse=True)[:5]:  # Last 5 years
            row = {"period_end": pd.to_datetime(date), "symbol": ticker.upper()}

            # Find values for this date
            for fact in revenue_facts:
                if fact["end_date"] == date:
                    row["revenue"] = float(fact["value"])
                    break

            for fact in operating_income_facts:
                if fact["end_date"] == date:
                    row["operating_income"] = float(fact["value"])
                    break

            for fact in net_income_facts:
                if fact["end_date"] == date:
                    row["net_income"] = float(fact["value"])
                    break

            if any(k in row for k in ["revenue", "operating_income", "net_income"]):
                rows.append(row)

        if not rows:
            raise ValueError(f"No income statement data found for ticker: {ticker}")

        df = pd.DataFrame(rows)
        df["currency"] = "USD"  # SEC data is typically USD
        return df

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
        cik = self._ticker_to_cik(ticker)
        company_facts = self._get_company_facts(cik)

        # Extract cash and debt
        cash_facts = self._find_xbrl_tag(company_facts, "cash_and_equivalents")
        total_debt_facts = self._find_xbrl_tag(company_facts, "total_debt")
        long_term_debt_facts = self._find_xbrl_tag(company_facts, "long_term_debt")
        short_term_debt_facts = self._find_xbrl_tag(company_facts, "short_term_debt")

        # If total_debt not found, try to sum long + short
        if not total_debt_facts and (long_term_debt_facts or short_term_debt_facts):
            # Group by date and sum
            debt_by_date: dict[str, float] = {}
            for fact in long_term_debt_facts + short_term_debt_facts:
                date = fact["end_date"]
                debt_by_date[date] = debt_by_date.get(date, 0.0) + float(fact["value"])

            total_debt_facts = [
                {"tag": "Debt", "value": val, "end_date": date, "units": "USD"}
                for date, val in debt_by_date.items()
            ]

        # Build DataFrame
        rows = []
        all_dates = set()
        for facts in [cash_facts, total_debt_facts]:
            for fact in facts:
                all_dates.add(fact["end_date"])

        for date in sorted(all_dates, reverse=True)[:5]:  # Last 5 years
            row = {"period_end": pd.to_datetime(date), "symbol": ticker.upper()}

            for fact in cash_facts:
                if fact["end_date"] == date:
                    row["cash_and_equivalents"] = float(fact["value"])
                    break

            for fact in total_debt_facts:
                if fact["end_date"] == date:
                    row["total_debt"] = float(fact["value"])
                    break

            if any(k in row for k in ["cash_and_equivalents", "total_debt"]):
                rows.append(row)

        if not rows:
            raise ValueError(f"No balance sheet data found for ticker: {ticker}")

        df = pd.DataFrame(rows)
        df["currency"] = "USD"
        return df

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
        cik = self._ticker_to_cik(ticker)
        company_facts = self._get_company_facts(cik)

        # Extract CFO and capex
        cfo_facts = self._find_xbrl_tag(company_facts, "cfo")
        capex_facts = self._find_xbrl_tag(company_facts, "capex")

        # Build DataFrame
        rows = []
        all_dates = set()
        for facts in [cfo_facts, capex_facts]:
            for fact in facts:
                all_dates.add(fact["end_date"])

        for date in sorted(all_dates, reverse=True)[:5]:  # Last 5 years
            row = {"period_end": pd.to_datetime(date), "symbol": ticker.upper()}

            for fact in cfo_facts:
                if fact["end_date"] == date:
                    row["operating_cash_flow"] = float(fact["value"])
                    break

            for fact in capex_facts:
                if fact["end_date"] == date:
                    # Capex is typically negative (cash outflow), ensure sign is correct
                    capex_val = float(fact["value"])
                    # If positive, make negative (cash outflow)
                    if capex_val > 0:
                        capex_val = -capex_val
                    row["capital_expenditure"] = capex_val
                    break

            if any(k in row for k in ["operating_cash_flow", "capital_expenditure"]):
                rows.append(row)

        if not rows:
            raise ValueError(f"No cash flow statement data found for ticker: {ticker}")

        df = pd.DataFrame(rows)
        df["currency"] = "USD"
        return df

    def __enter__(self) -> "SECProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close HTTP client."""
        self.client.close()

