"""Configuration management for forecast assumptions and scenario parameters.

This module handles loading and validation of configuration from YAML/JSON files
with sensible defaults for Base/Bull/Bear scenarios.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


@dataclass
class ScenarioConfig:
    """Configuration for a single scenario (Base/Bull/Bear)."""

    discount_rate: float
    terminal_growth: float
    revenue_growth: list[float] | Callable[[int], float]
    operating_margin: list[float] | Callable[[int], float] | None = None
    operating_income_pct_revenue: list[float] | Callable[[int], float] | None = None
    capex_pct_revenue: float | list[float] | Callable[[int], float] = 0.0
    nwc_pct_revenue: float = 0.0

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not 0.0 <= self.discount_rate <= 1.0:
            raise ValueError(f"discount_rate must be between 0 and 1, got {self.discount_rate}")
        if not 0.0 <= self.terminal_growth <= 0.1:
            raise ValueError(
                f"terminal_growth must be between 0 and 0.1, got {self.terminal_growth}"
            )

        # Validate that either operating_margin or operating_income_pct_revenue is provided
        if self.operating_margin is None and self.operating_income_pct_revenue is None:
            raise ValueError(
                "Either operating_margin or operating_income_pct_revenue must be provided"
            )


@dataclass
class ForecastConfig:
    """Main configuration for forecast assumptions."""

    horizon_years: int = 5
    base: ScenarioConfig = field(default_factory=lambda: ScenarioConfig(
        discount_rate=0.10,
        terminal_growth=0.025,
        revenue_growth=[0.05] * 5,  # 5% growth for 5 years
        operating_income_pct_revenue=[0.15] * 5,  # 15% operating margin
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.0,
    ))
    bull: ScenarioConfig = field(default_factory=lambda: ScenarioConfig(
        discount_rate=0.09,
        terminal_growth=0.03,
        revenue_growth=[0.08] * 5,  # 8% growth for 5 years
        operating_income_pct_revenue=[0.18] * 5,  # 18% operating margin
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.0,
    ))
    bear: ScenarioConfig = field(default_factory=lambda: ScenarioConfig(
        discount_rate=0.11,
        terminal_growth=0.02,
        revenue_growth=[0.02] * 5,  # 2% growth for 5 years
        operating_income_pct_revenue=[0.12] * 5,  # 12% operating margin
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.0,
    ))

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.horizon_years < 1 or self.horizon_years > 10:
            raise ValueError(f"horizon_years must be between 1 and 10, got {self.horizon_years}")


def _parse_revenue_growth(value: Any, horizon_years: int) -> list[float] | Callable[[int], float]:
    """Parse revenue growth from config value.

    Args:
        value: Can be a list, single float, or function string.
        horizon_years: Number of years in forecast horizon.

    Returns:
        List of growth rates or a callable function.
    """
    if isinstance(value, list):
        if len(value) != horizon_years:
            raise ValueError(
                f"revenue_growth list length ({len(value)}) must match horizon_years ({horizon_years})"
            )
        return [float(x) for x in value]
    elif isinstance(value, (int, float)):
        return [float(value)] * horizon_years
    else:
        raise ValueError(f"revenue_growth must be list or number, got {type(value)}")


def _parse_margin_or_pct(
    value: Any, horizon_years: int
) -> list[float] | Callable[[int], float] | None:
    """Parse operating margin or operating income pct from config value.

    Args:
        value: Can be a list, single float, or None.
        horizon_years: Number of years in forecast horizon.

    Returns:
        List of margin rates, None, or a callable function.
    """
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) != horizon_years:
            raise ValueError(
                f"margin list length ({len(value)}) must match horizon_years ({horizon_years})"
            )
        return [float(x) for x in value]
    elif isinstance(value, (int, float)):
        return [float(value)] * horizon_years
    else:
        raise ValueError(f"margin must be list, number, or None, got {type(value)}")


def _parse_capex(value: Any, horizon_years: int) -> float | list[float] | Callable[[int], float]:
    """Parse capex percentage from config value.

    Args:
        value: Can be a list, single float, or function string.
        horizon_years: Number of years in forecast horizon.

    Returns:
        Float, list of floats, or a callable function.
    """
    if isinstance(value, list):
        if len(value) != horizon_years:
            raise ValueError(
                f"capex_pct_revenue list length ({len(value)}) must match horizon_years ({horizon_years})"
            )
        return [float(x) for x in value]
    elif isinstance(value, (int, float)):
        return float(value)
    else:
        raise ValueError(f"capex_pct_revenue must be list or number, got {type(value)}")


def _load_scenario_from_dict(data: dict[str, Any], horizon_years: int) -> ScenarioConfig:
    """Load a scenario configuration from a dictionary.

    Args:
        data: Dictionary containing scenario configuration.
        horizon_years: Number of years in forecast horizon.

    Returns:
        ScenarioConfig instance.
    """
    revenue_growth = _parse_revenue_growth(data.get("revenue_growth", [0.05] * horizon_years), horizon_years)

    operating_margin = _parse_margin_or_pct(data.get("operating_margin"), horizon_years)
    operating_income_pct = _parse_margin_or_pct(
        data.get("operating_income_pct_revenue"), horizon_years
    )

    capex_pct = _parse_capex(data.get("capex_pct_revenue", 0.05), horizon_years)

    return ScenarioConfig(
        discount_rate=float(data.get("discount_rate", 0.10)),
        terminal_growth=float(data.get("terminal_growth", 0.025)),
        revenue_growth=revenue_growth,
        operating_margin=operating_margin,
        operating_income_pct_revenue=operating_income_pct,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=float(data.get("nwc_pct_revenue", 0.0)),
    )


def load_config(config_path: Optional[str | Path] = None) -> ForecastConfig:
    """Load forecast configuration from YAML or JSON file, or use defaults.

    Args:
        config_path: Path to YAML or JSON config file. If None, uses defaults.

    Returns:
        ForecastConfig instance with loaded or default values.

    Raises:
        FileNotFoundError: If config_path is provided but file doesn't exist.
        ValueError: If config file format is invalid or contains invalid values.
    """
    if config_path is None:
        return ForecastConfig()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        elif path.suffix.lower() == ".json":
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a dictionary/object")

    horizon_years = int(data.get("horizon_years", 5))

    base_data = data.get("base", {})
    bull_data = data.get("bull", {})
    bear_data = data.get("bear", {})

    return ForecastConfig(
        horizon_years=horizon_years,
        base=_load_scenario_from_dict(base_data, horizon_years),
        bull=_load_scenario_from_dict(bull_data, horizon_years),
        bear=_load_scenario_from_dict(bear_data, horizon_years),
    )

