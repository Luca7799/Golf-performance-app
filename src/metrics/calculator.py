"""
metrics/calculator.py

Computes global summary metrics from the cleaned rounds DataFrame.
Only calculates a metric when the required columns are present and
there is sufficient data; otherwise returns None so the UI can show
"Not enough data" gracefully.
"""

import pandas as pd
import numpy as np
from typing import Optional


def _has(rounds: pd.DataFrame, *cols: str) -> bool:
    return all(c in rounds.columns for c in cols)


def compute_metrics(rounds: pd.DataFrame) -> dict:
    """
    Compute global performance metrics from a per-round summary DataFrame.

    Returns a flat dict. Each metric is either a value or None (insufficient data).
    """
    m: dict = {}
    n = len(rounds)

    m["rounds_played"] = n
    m["min_rounds_for_recommendations"] = 5

    if n == 0:
        return m

    # --- Core scoring ---
    if _has(rounds, "total_score"):
        m["avg_score"] = round(rounds["total_score"].mean(), 1)
        m["best_score"] = int(rounds["total_score"].min())
        m["worst_score"] = int(rounds["total_score"].max())

    if _has(rounds, "score_vs_par"):
        m["avg_score_vs_par"] = round(rounds["score_vs_par"].mean(), 1)
        m["best_score_vs_par"] = int(rounds["score_vs_par"].min())

    # --- GIR ---
    if _has(rounds, "gir_pct"):
        m["avg_gir_pct"] = round(rounds["gir_pct"].mean(), 1)
    else:
        m["avg_gir_pct"] = None

    # --- Fairway ---
    if _has(rounds, "fairway_pct"):
        m["avg_fairway_pct"] = round(rounds["fairway_pct"].mean(), 1)
    else:
        m["avg_fairway_pct"] = None

    # --- Putts ---
    if _has(rounds, "putts_per_round"):
        valid = rounds["putts_per_round"].dropna()
        m["avg_putts_per_round"] = round(valid.mean(), 1) if len(valid) > 0 else None
    else:
        m["avg_putts_per_round"] = None

    # --- Penalties ---
    if _has(rounds, "total_penalties"):
        valid = rounds["total_penalties"].dropna()
        m["avg_penalties_per_round"] = round(valid.mean(), 2) if len(valid) > 0 else None
    else:
        m["avg_penalties_per_round"] = None

    # --- Trend (last 5 rounds vs overall) ---
    if n >= 5 and _has(rounds, "total_score"):
        last5 = rounds.tail(5)["total_score"].mean()
        m["last5_avg_score"] = round(last5, 1)
        m["trend_vs_overall"] = round(last5 - m["avg_score"], 1)  # negative = improving

    return m


def compute_hole_type_metrics(df: pd.DataFrame) -> dict:
    """
    Compute average score vs par broken down by hole par type (3, 4, 5).
    Requires hole-level DataFrame (not rounds).
    """
    if df.empty or not all(c in df.columns for c in ["par", "score"]):
        return {}

    df = df.copy()
    df["score_vs_par"] = df["score"] - df["par"]

    result = {}
    for par_val in [3, 4, 5]:
        subset = df[df["par"] == par_val]["score_vs_par"].dropna()
        if len(subset) > 0:
            result[f"par{par_val}_avg_vs_par"] = round(subset.mean(), 2)
            result[f"par{par_val}_hole_count"] = len(subset)
        else:
            result[f"par{par_val}_avg_vs_par"] = None
            result[f"par{par_val}_hole_count"] = 0

    return result
