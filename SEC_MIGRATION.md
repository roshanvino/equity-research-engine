# SEC Provider Migration Summary

## Overview

The project has been migrated from FMP (which requires a paid API plan) to **SEC EDGAR public APIs** as the default provider. The SEC provider is completely free, requires no API key, and uses publicly available XBRL financial data.

## Implementation Details

### 1. SEC Provider (`src/hf_memo/providers/sec_provider.py`)

**Key Features:**
- Uses SEC EDGAR Company Facts API (`https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit}.json`)
- Ticker-to-CIK mapping with local caching (`.cache/ticker_cik_map.json`)
- XBRL tag mapping for canonical line items
- Rate limiting (10 requests/second as per SEC guidelines)
- Descriptive User-Agent header (required by SEC)

**XBRL Tag Mappings:**
- Revenue: `Revenues`, `SalesRevenueNet`
- Operating Income: `OperatingIncomeLoss`
- Net Income: `NetIncomeLoss`
- CFO: `NetCashProvidedByUsedInOperatingActivities`
- Capex: `PaymentsToAcquirePropertyPlantAndEquipment` (sign-corrected to negative)
- Cash: `CashAndCashEquivalentsAtCarryingValue`
- Debt: `Debt` or sum of `LongTermDebt` + `DebtCurrent`

### 2. SEC Mapper (`src/hf_memo/standardize/mapper_sec.py`)

**Features:**
- Converts SEC provider DataFrames to canonical long-format schema
- Validates required core fields (revenue, operating_income, cfo, capex)
- Ensures capex is negative (cash outflow)
- Validates minimum 2 years of data

### 3. CLI Updates (`src/hf_memo/cli.py`)

**Changes:**
- Default provider changed from `fmp` to `sec`
- Supports both `--provider sec` (default) and `--provider fmp` (optional)
- Automatically uses correct mapper based on provider

### 4. Tests

**New Test Files:**
- `tests/test_sec_provider.py` - Tests for SEC provider
  - URL construction
  - User-Agent header
  - Ticker-to-CIK mapping
  - XBRL fact extraction
  - Capex sign handling
  - Rate limiting

- `tests/test_mapper_sec.py` - Tests for SEC mapper
  - Basic standardization
  - Capex sign handling
  - Missing field validation
  - Insufficient periods validation

### 5. Documentation Updates

**README.md:**
- Updated installation section (no API key required)
- Updated usage examples (SEC as default)
- Updated architecture section (SEC provider details)
- Noted FMP requires paid plan

## Usage

### Default (SEC - No API Key Required)

```bash
poetry run hf-memo run AAPL
```

### Optional FMP Provider (Requires Paid API Key)

```bash
export FMP_API_KEY='your-key'
poetry run hf-memo run AAPL --provider fmp
```

## Technical Details

### Ticker-to-CIK Mapping

- Downloads from: `https://www.sec.gov/files/company_tickers.json`
- Cached locally in: `.cache/ticker_cik_map.json`
- Refreshed daily (24-hour cache TTL)
- Falls back to stale cache if download fails

### Rate Limiting

- Minimum interval: 0.1 seconds (10 requests/second max)
- Enforced via `_rate_limit()` method
- Respects SEC API guidelines

### XBRL Data Extraction

- Filters for annual data only (`fp == "FY"`)
- Prefers USD units
- Falls back to first available unit if USD not found
- Handles multiple tag name variations (fallback chain)

### Error Handling

- Clear error messages for missing tickers
- Validates minimum required fields
- Helpful messages for insufficient data
- Graceful fallback to cached ticker mapping

## File Structure

```
src/hf_memo/
├── providers/
│   ├── base.py              # Abstract interface
│   ├── sec_provider.py      # NEW: SEC EDGAR provider
│   └── fmp_provider.py      # Optional: FMP provider
├── standardize/
│   ├── mapper_sec.py        # NEW: SEC to canonical mapper
│   └── mapper_fmp.py        # FMP to canonical mapper
└── cli.py                   # Updated: Default to SEC

tests/
├── test_sec_provider.py     # NEW: SEC provider tests
└── test_mapper_sec.py       # NEW: SEC mapper tests

.cache/                      # NEW: Ticker-CIK mapping cache
```

## Benefits

1. **Free**: No API key or paid subscription required
2. **Public Data**: Uses official SEC EDGAR filings
3. **Reliable**: SEC data is authoritative and comprehensive
4. **Reproducible**: Anyone can run without external dependencies
5. **Extensible**: Provider pattern allows easy addition of other sources

## Migration Notes

- FMP provider remains available as optional (`--provider fmp`)
- All existing functionality preserved
- Same canonical schema and pipeline
- No breaking changes to config or output format

## Testing

Run tests to verify implementation:

```bash
# Test SEC provider
poetry run pytest tests/test_sec_provider.py -v

# Test SEC mapper
poetry run pytest tests/test_mapper_sec.py -v

# Test full pipeline with SEC
poetry run hf-memo run AAPL
```

## Known Limitations

1. **Annual Data Only**: SEC provider extracts annual (FY) data only
2. **XBRL Tag Variations**: Some companies may use different XBRL tags (fallback chain handles most cases)
3. **Rate Limiting**: SEC enforces rate limits (handled automatically)
4. **Cache Dependency**: First run requires internet to download ticker mapping

## Future Enhancements

- Add quarterly data support
- Expand XBRL tag fallback chains
- Add more robust error recovery
- Support for international companies (non-US GAAP)

