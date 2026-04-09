"""
data_cleaning/cleaner.py

Takes the raw DataFrame from loader.py and produces a clean, typed DataFrame
ready for metric calculation. Handles missing values, type coercion, and
boolean normalisation for fairway_hit / gir columns.
"""

import pandas as pd
import numpy as np
from typing import Tuple


BOOL_TRUE_VALUES = {"yes", "true", "1", "y", "hit", "gir", "fairway"}
BOOL_FALSE_VALUES = {"no", "false", "0", "n", "miss", "missed"}


def _parse_bool(series: pd.Series) -> pd.Series:
    """Convert string boolean-like values to True/False/NaN."""
    def convert(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip().lower()
        if s in BOOL_TRUE_VALUES:
            return True
        if s in BOOL_FALSE_VALUES:
            return False
        # Try numeric: 1 = True, 0 = False
        try:
            return bool(int(float(s)))
        except (ValueError, TypeError):
            return np.nan
    return series.apply(convert)


def clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Clean and type-cast the raw DataFrame.

    Returns
    -------
    clean_df : pd.DataFrame
        Fully typed, cleaned DataFrame.
    skipped : int
        Number of rows dropped due to missing required fields.
    """
    df = df.copy()
    initial_len = len(df)

    # --- Date ---
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # --- Numeric columns ---
    for col in ["hole", "par", "score", "putts", "penalties", "distance"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Boolean columns ---
    for col in ["fairway_hit", "gir"]:
        if col in df.columns:
            df[col] = _parse_bool(df[col])

    # --- String columns ---
    for col in ["course", "club"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": np.nan, "": np.nan})

    # --- Drop rows missing any required field ---
    required_present = [c for c in ["date", "course", "hole", "par", "score"] if c in df.columns]
    before = len(df)
    df = df.dropna(subset=required_present)
    skipped = before - len(df)

    # --- Sanity filters ---
    if "score" in df.columns:
        df = df[df["score"] > 0]
    if "par" in df.columns:
        df = df[df["par"].isin([3, 4, 5])]
    if "hole" in df.columns:
        df = df[(df["hole"] >= 1) & (df["hole"] <= 18)]
    if "putts" in df.columns:
        df = df[(df["putts"].isna()) | (df["putts"] >= 0)]

    df = df.reset_index(drop=True)
    skipped = initial_len - len(df)

    return df, skipped


def build_rounds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate hole-level data into a per-round summary DataFrame.

    Columns produced (when source data is available):
        round_id, date, course, holes_played,
        total_score, total_par, score_vs_par,
        total_putts, putts_per_round,
        gir_count, gir_pct,
        fairway_count, fairway_opportunities, fairway_pct,
        total_penalties
    """
    if df.empty:
        return pd.DataFrame()

    group_cols = ["date", "course"]
    # Use only columns that exist
    group_cols = [c for c in group_cols if c in df.columns]
    if not group_cols:
        return pd.DataFrame()

    agg: dict = {}

    if "hole" in df.columns:
        agg["holes_played"] = ("hole", "count")
    if "score" in df.columns:
        agg["total_score"] = ("score", "sum")
    if "par" in df.columns:
        agg["total_par"] = ("par", "sum")
    if "putts" in df.columns:
        agg["total_putts"] = ("putts", "sum")
    if "penalties" in df.columns:
        agg["total_penalties"] = ("penalties", "sum")
    if "gir" in df.columns:
        agg["gir_count"] = ("gir", lambda x: x.eq(True).sum())
        agg["gir_holes"] = ("gir", "count")
    if "fairway_hit" in df.columns:
        agg["fairway_count"] = ("fairway_hit", lambda x: x.eq(True).sum())

    rounds = df.groupby(group_cols, as_index=False).agg(**agg)

    # Derived columns
    if "total_score" in rounds.columns and "total_par" in rounds.columns:
        rounds["score_vs_par"] = rounds["total_score"] - rounds["total_par"]

    if "total_putts" in rounds.columns and "holes_played" in rounds.columns:
        rounds["putts_per_round"] = rounds["total_putts"]

    if "gir_count" in rounds.columns and "gir_holes" in rounds.columns:
        rounds["gir_pct"] = (rounds["gir_count"] / rounds["gir_holes"] * 100).round(1)
        rounds.drop(columns=["gir_holes"], inplace=True)

    if "fairway_count" in rounds.columns:
        # Fairway opportunities = par 4 + par 5 holes
        fw_opps = (
            df[df["par"].isin([4, 5])].groupby(group_cols)["fairway_hit"].count().reset_index()
        )
        fw_opps.columns = group_cols + ["fairway_opportunities"]
        rounds = rounds.merge(fw_opps, on=group_cols, how="left")
        rounds["fairway_pct"] = (
            rounds["fairway_count"] / rounds["fairway_opportunities"] * 100
        ).round(1)

    # Add a simple round index sorted by date
    if "date" in rounds.columns:
        rounds = rounds.sort_values("date").reset_index(drop=True)
        rounds.insert(0, "round_id", range(1, len(rounds) + 1))

    return rounds
