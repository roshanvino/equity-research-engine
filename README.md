# Equity Research Engine

## Overview
This project is a Python-based pipeline for **fundamental equity research**.  
It ingests public company financial statements, standardises them into a canonical schema, builds **lightweight three-statement forecasts**, runs **scenario-based valuation**, and auto-generates concise investment memos.

The goal is to demonstrate **driver-based analysis**, **probabilistic thinking**, and a **reproducible buy-side research workflow**.

## Project Goals (Current MVP)
- Fetch and standardise **income statement, balance sheet, and cash flow** data  
- Build **3–5 year driver-based forecasts** (revenue, margins, capex)  
- Run **Base / Bull / Bear** scenario valuations using a simple DCF framework  
- Output a **Markdown investment memo** summarising assumptions, forecasts, valuation range, and key risks  
- Keep the pipeline **provider-agnostic** and easily extensible

## Design Principles
- Focus on **clarity over complexity**
- Model **economic drivers**, not line-item noise
- Favour **reproducibility** over one-off analysis
- Avoid over-engineering or sell-side style reports

## Installation

### Prerequisites
- Python 3.11+
- Poetry (install via `curl -sSL https://install.python-poetry.org | python3 -`)
- Financial Modeling Prep (FMP) API key ([Get one here](https://site.financialmodelingprep.com/developer/docs/))

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd equity-research-engine

# Install dependencies
poetry install

# Set FMP API key as environment variable
export FMP_API_KEY='your-api-key-here'

# Or add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export FMP_API_KEY="your-api-key-here"' >> ~/.zshrc
```

## Usage

### Basic Usage

```bash
# Generate investment memo for a ticker
poetry run hf-memo run AAPL

# Or if in poetry shell
poetry shell
hf-memo run AAPL
```

### With Custom Configuration

```bash
# Use a custom config file
poetry run hf-memo run AAPL --config config/config.yaml
```

### Output

The memo will be written to:
```
reports/{TICKER}/{YYYY-MM-DD}/memo.md
```

For example: `reports/AAPL/2024-01-15/memo.md`

The memo includes:
- Executive summary with valuation range
- Historical analysis (revenue trends, margins)
- Forecast assumptions (Base/Bull/Bear scenarios)
- 5-year forecast summary
- DCF valuation breakdown
- Sensitivity analysis placeholders
- Sections for investment thesis, risks, and catalysts

## Configuration

Edit `config/config.yaml` (or create from `config/config.example.yaml`) to customize:
- Forecast horizon (default: 5 years)
- Base/Bull/Bear scenario assumptions:
  - Discount rate (WACC)
  - Terminal growth rate
  - Revenue growth path
  - Operating margin assumptions
  - Capex as % of revenue
  - Working capital assumptions

Example config structure:
```yaml
horizon_years: 5

base:
  discount_rate: 0.10
  terminal_growth: 0.025
  revenue_growth: [0.05, 0.05, 0.04, 0.04, 0.03]
  operating_income_pct_revenue: [0.15, 0.16, 0.17, 0.17, 0.18]
  capex_pct_revenue: 0.05
  nwc_pct_revenue: 0.0
```

## Development

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src/hf_memo

# Format code
poetry run black src/ tests/

# Lint
poetry run ruff check src/ tests/

# Type check
poetry run mypy src/
```

## Architecture

The pipeline follows this workflow:
1. **Fetch** → FMP API provider fetches annual financial statements
2. **Standardize** → Convert to canonical long-format schema
3. **Extract Drivers** → Calculate historical revenue growth, margins, capex ratios
4. **Forecast** → Build 5-year driver-based forecast for Base/Bull/Bear scenarios
5. **Value** → Calculate DCF (FCFF, terminal value, enterprise value, equity value)
6. **Generate** → Create Markdown investment memo

### Provider Abstraction

The project uses a provider adapter pattern. Currently implemented:
- **FMP Provider** (`hf_memo/providers/fmp_provider.py`) - Financial Modeling Prep API

Additional providers can be added by implementing the `FinancialsProvider` interface.

## Status
✅ MVP Complete - End-to-end pipeline functional  
Uses Financial Modeling Prep (FMP) API for data fetching. Supports Base/Bull/Bear scenario analysis with configurable assumptions.

## Intended Extensions
- Additional data providers (e.g. OpenBB as optional, SEC filings)
- Batch analysis across a universe of stocks
- Sensitivity analysis and assumption stress testing
- Optional news and catalyst tagging
- Per-share valuation (requires shares outstanding data)

---

*This project is for research and educational purposes only. It does not constitute investment advice.*
