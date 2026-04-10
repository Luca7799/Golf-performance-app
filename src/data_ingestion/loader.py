"""
data_ingestion/loader.py

Loads a CSV export (Golfshot hole-level OR ShotZoom/round-level) and maps its
columns to internal standard names using config/column_mapping.yaml.

Format detection is automatic:
  - "hole_level"  : Golfshot-style — one row per hole, requires hole + par columns
  - "round_level" : ShotZoom-style — one row per round with pre-computed percentages

Returns a raw DataFrame with standardised column names and a report dict.
"""

import os
import yaml
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict


def _find_config() -> Path:
    candidates = [
        Path(__file__).parents[2] / "config" / "column_mapping.yaml",
        Path.cwd() / "config" / "column_mapping.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"column_mapping.yaml not found. Tried: {candidates}"
    )


def load_config() -> dict:
    with open(_find_config(), "r") as f:
        return yaml.safe_load(f)


def _find_column(df_columns: list, candidates: list) -> Optional[str]:
    """Return the first candidate that exists in df_columns (case-insensitive)."""
    lower_map = {c.lower(): c for c in df_columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def _detect_format(columns: list) -> str:
    """
    Auto-detect whether the CSV is hole-level (Golfshot) or round-level (ShotZoom).

    Round-level indicators: percentage columns (Fairway_Pct, GIR_Pct, etc.)
    without hole-number / par columns.
    """
    lower = [c.lower() for c in columns]

    has_hole = any(c in lower for c in ["hole", "hole number", "hole_number", "hole #"])
    has_par  = any(c in lower for c in ["par", "hole par", "holepar"])

    # ShotZoom-style percentage columns
    round_pct_indicators = [
        "fairway_pct", "gir_pct", "fairway %", "gir %",
        "fairway pct", "gir pct", "fairways pct", "greens pct",
    ]
    has_round_pct = any(c in lower for c in round_pct_indicators)

    if has_hole and has_par:
        return "hole_level"
    if has_round_pct and not has_hole:
        return "round_level"
    # Default: assume hole-level (will report missing required columns if wrong)
    return "hole_level"


def load_csv(file) -> tuple:
    """
    Load a golf CSV from a file path or file-like object.

    Auto-detects format (hole_level vs round_level) and applies the
    appropriate column mapping from column_mapping.yaml.

    Returns
    -------
    df : pd.DataFrame
        Raw DataFrame with internal column names.
    report : dict
        {
          "format_type":       "hole_level" | "round_level",
          "found":             [list of internal names successfully mapped],
          "missing_required":  [list of required internal names not found],
          "missing_optional":  [list of optional internal names not found],
          "skipped_rows":      int,
          "total_rows":        int,
        }
    """
    try:
        raw_df = pd.read_csv(file, dtype=str)
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {e}")

    config = load_config()
    df_columns = list(raw_df.columns)

    format_type = _detect_format(df_columns)

    if format_type == "round_level":
        required_map = config.get("round_level_required", {})
        optional_map = config.get("round_level_optional", {})
    else:
        required_map = config.get("required", {})
        optional_map = config.get("optional", {})

    rename_map: Dict[str, str] = {}
    found: List[str] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []

    for internal_name, candidates in required_map.items():
        matched = _find_column(df_columns, candidates)
        if matched:
            rename_map[matched] = internal_name
            found.append(internal_name)
        else:
            missing_required.append(internal_name)

    for internal_name, candidates in optional_map.items():
        matched = _find_column(df_columns, candidates)
        if matched:
            rename_map[matched] = internal_name
            found.append(internal_name)
        else:
            missing_optional.append(internal_name)

    df = raw_df.rename(columns=rename_map)

    # Keep only internal-named columns (drop unmapped columns silently)
    all_internal = list(required_map.keys()) + list(optional_map.keys())
    keep_cols = [c for c in all_internal if c in df.columns]
    df = df[keep_cols].copy()

    total_rows = len(df)
    report = {
        "format_type":      format_type,
        "found":            found,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "skipped_rows":     0,
        "total_rows":       total_rows,
    }

    return df, report
