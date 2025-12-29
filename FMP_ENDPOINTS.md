# FMP Stable Endpoints Used

## Migration Summary

The FMP provider has been updated to use **stable v4 endpoints** instead of legacy v3 endpoints.

## Endpoints Defined

### Base URL
**Location**: `src/hf_memo/providers/fmp_provider.py`, line 19

```python
BASE_URL = "https://financialmodelingprep.com/api/v4"
```

### Income Statement Endpoint
**Location**: `src/hf_memo/providers/fmp_provider.py`, line 137

**Endpoint Path**: `/income-statement/{ticker}`

**Full URL**: `https://financialmodelingprep.com/api/v4/income-statement/{ticker}?apikey={key}&period=annual&limit=5`

**Method**: `get_income_statement(ticker: str) -> pd.DataFrame`

**Code Reference**:
```python
def get_income_statement(self, ticker: str) -> pd.DataFrame:
    endpoint = f"/income-statement/{ticker.upper()}"
    data = self._fetch_endpoint(endpoint)
    # ...
```

### Balance Sheet Endpoint
**Location**: `src/hf_memo/providers/fmp_provider.py`, line 157

**Endpoint Path**: `/balance-sheet-statement/{ticker}`

**Full URL**: `https://financialmodelingprep.com/api/v4/balance-sheet-statement/{ticker}?apikey={key}&period=annual&limit=5`

**Method**: `get_balance_sheet(ticker: str) -> pd.DataFrame`

**Code Reference**:
```python
def get_balance_sheet(self, ticker: str) -> pd.DataFrame:
    endpoint = f"/balance-sheet-statement/{ticker.upper()}"
    data = self._fetch_endpoint(endpoint)
    # ...
```

### Cash Flow Statement Endpoint
**Location**: `src/hf_memo/providers/fmp_provider.py`, line 177

**Endpoint Path**: `/cash-flow-statement/{ticker}`

**Full URL**: `https://financialmodelingprep.com/api/v4/cash-flow-statement/{ticker}?apikey={key}&period=annual&limit=5`

**Method**: `get_cash_flow(ticker: str) -> pd.DataFrame`

**Code Reference**:
```python
def get_cash_flow(self, ticker: str) -> pd.DataFrame:
    endpoint = f"/cash-flow-statement/{ticker.upper()}"
    data = self._fetch_endpoint(endpoint)
    # ...
```

## URL Construction

**Location**: `src/hf_memo/providers/fmp_provider.py`, line 36-42

The `_build_url()` method constructs the full URL:

```python
def _build_url(self, endpoint: str) -> str:
    """Build the full URL for an FMP API endpoint."""
    return f"{self.BASE_URL}{endpoint}"
```

## Query Parameters

All endpoints use the same query parameters (defined in `_fetch_endpoint()`, line 51):

- `apikey`: FMP API key (from environment variable or constructor)
- `period`: `"annual"` (annual statements only)
- `limit`: `5` (last 5 years of data)

## Error Handling

**Location**: `src/hf_memo/providers/fmp_provider.py`, lines 55-95

The provider now includes enhanced error handling:

1. **Legacy Endpoint Detection**: If a 403 response contains "Legacy Endpoint" in the error message, raises `LegacyEndpointError` with a clear message
2. **Generic 403 Handling**: If 403 occurs without legacy message, still provides helpful guidance
3. **Response Body Checking**: Also checks response body (not just status code) for legacy endpoint messages

**Exception Class**: `LegacyEndpointError` (defined at line 15)

## Testing

**Location**: `tests/test_fmp_provider.py`

Tests verify:
- URL construction uses v4 endpoints (`test_build_url`)
- Stable endpoints are documented (`test_stable_endpoints_used`)
- Legacy endpoint errors are detected (`test_legacy_endpoint_error_detection`)
- Endpoint paths are correct (`test_endpoint_paths`)

## Migration Checklist

✅ Updated `BASE_URL` from `/api/v3` to `/api/v4`
✅ Updated all three endpoint methods to use stable paths
✅ Added `_build_url()` method for testable URL construction
✅ Enhanced error handling for legacy endpoint detection
✅ Added `LegacyEndpointError` exception class
✅ Updated docstrings to document stable endpoints
✅ Added unit tests for URL construction and error handling

## Example Usage

```python
from hf_memo.providers.fmp_provider import FMPProvider

provider = FMPProvider()  # Uses FMP_API_KEY env var

# These now call stable v4 endpoints:
income = provider.get_income_statement("AAPL")
balance = provider.get_balance_sheet("AAPL")
cashflow = provider.get_cash_flow("AAPL")
```

## Verification

To verify the endpoints being used, check:

1. **BASE_URL constant**: Line 19 in `fmp_provider.py` should be `api/v4`
2. **URL construction**: Run `test_build_url()` test to verify URLs
3. **Actual API calls**: Check network logs or FMP API dashboard to confirm v4 endpoints are being called

