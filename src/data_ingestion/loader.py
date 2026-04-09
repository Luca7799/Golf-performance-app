"""
data_ingestion/loader.py

Loads a Golfshot CSV export and maps its columns to internal standard names
using config/column_mapping.yaml. Returns a raw DataFrame with standardised
column names and a report of which columns were found / missing.
"""

import os
import yaml
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict


CONFIG_PATH = Path(__file__).parents[2] / "config" / "column_mapping.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _find_column(df_columns: list, candidates: list) -> Optional[str]:
    """Return the first candidate that exists in df_columns (case-insensitive)."""
    lower_map = {c.lower(): c for c in df_columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def load_csv(file) -> tuple:
    """
    Load a Golfshot CSV from a file path or file-like object.

    Returns
    -------
    df : pd.DataFrame
        Raw DataFrame with internal column names.
    report : dict
        {
          "found": [list of internal names successfully mapped],
          "missing_required": [list of required internal names not found],
          "missing_optional": [list of optional internal names not found],
          "skipped_rows": int,
          "total_rows": int,
        }
    """
    try:
        raw_df = pd.read_csv(file, dtype=str)
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {e}")

    config = load_config()
    df_columns = list(raw_df.columns)

    rename_map: Dict[str, str] = {}
    found: List[str] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []

    for internal_name, candidates in config["required"].items():
        matched = _find_column(df_columns, candidates)
        if matched:
            rename_map[matched] = internal_name
            found.append(internal_name)
        else:
            missing_required.append(internal_name)

    for internal_name, candidates in config["optional"].items():
        matched = _find_column(df_columns, candidates)
        if matched:
            rename_map[matched] = internal_name
            found.append(internal_name)
        else:
            missing_optional.append(internal_name)

    df = raw_df.rename(columns=rename_map)

    # Keep only internal-named columns (drop unmapped columns silently)
    all_internal = list(config["required"].keys()) + list(config["optional"].keys())
    keep_cols = [c for c in all_internal if c in df.columns]
    df = df[keep_cols].copy()

    total_rows = len(df)
    report = {
        "found": found,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "skipped_rows": 0,
        "total_rows": total_rows,
    }

    return df, report
