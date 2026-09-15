"""
Configuration management for NFL MCP.

Stores config at ~/.nfl-mcp/config.json.
DuckDB database lives at ~/.nfl-mcp/nflread.duckdb by default.
"""

import datetime
import json
import os
import warnings
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".nfl-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_DUCKDB_PATH = CONFIG_DIR / "nflread.duckdb"

# ── Season bounds ──────────────────────────────────────────────────────────────
# 2013 is the first season where every default nflverse source is complete.
FIRST_SEASON = 2013


def current_season(today: datetime.date | None = None) -> int:
    """Return the NFL season year that is current or most recently started.

    nflverse labels a season by its starting calendar year, so the 2026 season
    spans Sep 2026 – Feb 2027.  The league year rolls over in March, which is
    also roughly when nflverse begins publishing rows for the upcoming season,
    so any date from March onward belongs to that calendar year's season.

    Erring a season ahead is safe: the ingest loops wrap every loader call in
    try/except and skip seasons that have no upstream data yet.
    """
    today = today or datetime.date.today()
    return today.year if today.month >= 3 else today.year - 1

_DEFAULT_CONFIG = {
    "duckdb_path": str(DEFAULT_DUCKDB_PATH),
}


def ensure_config_dir() -> Path:
    """Create ~/.nfl-mcp/ if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict[str, Any]:
    """Load config from disk, falling back to defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                stored = json.load(f)
            return {**_DEFAULT_CONFIG, **stored}
        except json.JSONDecodeError:
            ensure_config_dir()
            backup = CONFIG_FILE.with_suffix(".json.broken")
            try:
                CONFIG_FILE.replace(backup)
                backup_note = f" Backed up to {backup}."
            except OSError:
                backup_note = ""
            warnings.warn(
                f"Malformed config at {CONFIG_FILE}.{backup_note} "
                "Falling back to defaults; run 'nfl-mcp init' to regenerate config."
            )
            return {**_DEFAULT_CONFIG}
    return {**_DEFAULT_CONFIG}


def save_config(config: dict[str, Any]) -> Path:
    """Write config to ~/.nfl-mcp/config.json."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    return CONFIG_FILE


def get_duckdb_path() -> Path:
    """Return resolved path to the DuckDB database file."""
    # Env var override for CI / containers
    override = os.getenv("NFL_MCP_DB_PATH")
    if override:
        return Path(override).expanduser()
    return Path(load_config()["duckdb_path"]).expanduser()


def config_exists() -> bool:
    """Check whether a config file has been created (i.e., init has been run)."""
    return CONFIG_FILE.exists()
