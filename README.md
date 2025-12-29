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

## Status
🚧 Early development (MVP).  
Initial implementation focuses on a single ticker, annual data, and a clean end-to-end research flow.

## Intended Extensions
- Additional data providers (e.g. filings, alternative APIs)
- Batch analysis across a universe of stocks
- Sensitivity analysis and assumption stress testing
- Optional news and catalyst tagging

---

*This project is for research and educational purposes only. It does not constitute investment advice.*
