"""CLI entry point for hf-memo."""

import os
from pathlib import Path
from typing import Optional

import click

from hf_memo.config import ForecastConfig, load_config
from hf_memo.model.drivers import extract_drivers
from hf_memo.providers.fmp_provider import FMPProvider
from hf_memo.providers.sec_provider import SECProvider
from hf_memo.report.memo import generate_memo
from hf_memo.standardize.mapper_fmp import standardize_fmp
from hf_memo.standardize.mapper_sec import standardize_sec
from hf_memo.valuation.scenarios import run_scenarios


@click.group()
def main() -> None:
    """hf-memo: Driver-based financial forecast and DCF valuation memo generator."""
    pass


@main.command()
@click.argument("ticker", type=str)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to YAML/JSON config file (default: use built-in defaults)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["sec", "fmp"], case_sensitive=False),
    default="sec",
    help="Data provider to use: 'sec' (default, free, no API key) or 'fmp' (requires paid API key)",
)
def run(ticker: str, config: Optional[Path], provider: str) -> None:
    """Generate investment memo for a ticker.

    TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
    """
    click.echo(f"Generating memo for {ticker} using {provider} provider...")

    # Load configuration
    try:
        forecast_config = load_config(str(config) if config else None)
        click.echo(f"✓ Loaded configuration (horizon: {forecast_config.horizon_years} years)")
    except Exception as e:
        click.echo(f"✗ Error loading config: {e}", err=True)
        raise click.Abort()

    # Initialize provider
    provider_instance = None
    provider_name = provider.lower()

    try:
        if provider_name == "sec":
            provider_instance = SECProvider()
            click.echo("✓ Initialized SEC provider (public API, no key required)")
        elif provider_name == "fmp":
            provider_instance = FMPProvider()
            click.echo("✓ Initialized FMP provider")
        else:
            click.echo(f"✗ Unsupported provider: {provider}", err=True)
            raise click.Abort()
    except ValueError as e:
        click.echo(f"✗ {e}", err=True)
        raise click.Abort()

    # Fetch financial statements
    try:
        click.echo(f"Fetching financial statements for {ticker}...")
        income_df = provider_instance.get_income_statement(ticker)
        balance_df = provider_instance.get_balance_sheet(ticker)
        cash_df = provider_instance.get_cash_flow(ticker)
        click.echo(
            f"✓ Fetched {len(income_df)} income statements, {len(balance_df)} balance sheets, {len(cash_df)} cash flow statements"
        )
    except Exception as e:
        click.echo(f"✗ Error fetching data: {e}", err=True)
        raise click.Abort()
    finally:
        if provider_instance:
            provider_instance.client.close()

    # Standardize to canonical schema
    try:
        click.echo("Standardizing financial data...")
        if provider_name == "sec":
            standardized_df = standardize_sec(income_df, balance_df, cash_df, ticker, source="sec")
        elif provider_name == "fmp":
            standardized_df = standardize_fmp(income_df, balance_df, cash_df, ticker, source="fmp")
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
        click.echo(f"✓ Standardized {len(standardized_df)} data points")
    except Exception as e:
        click.echo(f"✗ Error standardizing data: {e}", err=True)
        raise click.Abort()

    # Extract historical drivers
    try:
        click.echo("Extracting historical drivers...")
        historical_drivers = extract_drivers(standardized_df)
        click.echo(f"✓ Extracted drivers for {len(historical_drivers['periods'])} periods")
    except Exception as e:
        click.echo(f"✗ Error extracting drivers: {e}", err=True)
        raise click.Abort()

    # Get current cash and debt for valuation
    balance_standardized = standardized_df[standardized_df["statement"] == "balance"]
    cash_data = balance_standardized[balance_standardized["line_item"] == "cash_and_equivalents"]
    debt_data = balance_standardized[balance_standardized["line_item"] == "total_debt"]

    if cash_data.empty:
        click.echo("⚠ Warning: No cash data found, using 0", err=True)
        cash = 0.0
    else:
        cash = cash_data["value"].iloc[-1]  # Most recent

    if debt_data.empty:
        click.echo("⚠ Warning: No debt data found, using 0", err=True)
        debt = 0.0
    else:
        debt = debt_data["value"].iloc[-1]  # Most recent

    # Run scenarios
    try:
        click.echo("Running Base/Bull/Bear scenarios...")
        scenario_results = run_scenarios(
            historical_drivers,
            forecast_config,
            cash,
            debt,
            shares_outstanding=None,  # Could fetch from provider if needed
        )
        click.echo("✓ Completed scenario analysis")
    except Exception as e:
        click.echo(f"✗ Error running scenarios: {e}", err=True)
        raise click.Abort()

    # Generate memo
    try:
        click.echo("Generating investment memo...")
        memo_content = generate_memo(
            ticker,
            historical_drivers,
            scenario_results,
            forecast_config,
            cash,
            debt,
            shares_outstanding=None,
        )
        click.echo("✓ Generated memo content")
    except Exception as e:
        click.echo(f"✗ Error generating memo: {e}", err=True)
        raise click.Abort()

    # Write memo to file
    from datetime import date

    today = date.today()
    output_dir = Path("reports") / ticker.upper() / today.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "memo.md"

    try:
        output_path.write_text(memo_content)
        click.echo(f"✓ Wrote memo to {output_path}")
    except Exception as e:
        click.echo(f"✗ Error writing memo: {e}", err=True)
        raise click.Abort()

    # Print summary
    base_equity = scenario_results["base"]["equity_results"]["equity_value"]
    bull_equity = scenario_results["bull"]["equity_results"]["equity_value"]
    bear_equity = scenario_results["bear"]["equity_results"]["equity_value"]

    click.echo("")
    click.echo("=" * 60)
    click.echo("VALUATION SUMMARY")
    click.echo("=" * 60)
    click.echo(f"Base Case:  ${base_equity/1e9:.2f}B")
    click.echo(f"Bull Case:  ${bull_equity/1e9:.2f}B")
    click.echo(f"Bear Case:  ${bear_equity/1e9:.2f}B")
    click.echo("")
    click.echo(f"Memo written to: {output_path}")
    click.echo("=" * 60)


if __name__ == "__main__":
    main()

