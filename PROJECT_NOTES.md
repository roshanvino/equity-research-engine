# Project Notes

## Implementation Progress

### ✅ Prompt 1: Canonical Schema + Configuration (Completed)

**Files Created:**
- `src/hf_memo/standardize/schema.py` - Defines canonical line items and standard dataframe schema
- `src/hf_memo/config.py` - Configuration management with Base/Bull/Bear scenario defaults

**Key Features:**
- Canonical line items for MVP: revenue, operating_income, net_income, cfo, capex, cash_and_equivalents, total_debt
- Long-format standard dataframe with columns: ticker, period_end, statement, line_item, value, currency, source
- Configuration system with defaults and YAML/JSON override support
- Type-safe dataclasses with validation
- Support for time-varying assumptions (lists or functions)

**Testing:**
- Test schema validation functions
- Test config loading with defaults
- Test config loading from YAML/JSON files
- Test scenario validation (discount rates, growth rates, etc.)

## Architecture Decisions

### Schema Design
- Using long-format (tidy) dataframes for flexibility and easier aggregation
- Enum-based statement types for type safety
- Separate canonical line items dictionary for easy extension

### Configuration Design
- Dataclasses for type safety and validation
- Support for both static values and time-varying assumptions (lists/functions)
- Sensible defaults that can be overridden via config files
- Validation at initialization to catch errors early

## Next Steps

1. Implement data fetching layer (OpenBB integration)
2. Implement standardization layer (convert to canonical schema)
3. Implement forecast builder
4. Implement DCF valuation
5. Implement scenario generation
6. Implement report generator
7. Implement CLI entry point

## Important Notes

- All financial values should be in consistent currency units
- Annual data only - no quarterly data for MVP
- Use last 3-5 years of historical data if available
- Defensive error handling at all boundaries
- Type hints required throughout

