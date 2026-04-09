"""
insights/analyzer.py

Derives deeper insights from rounds data:
  - Rolling averages (score trend over last N rounds)
  - Consistency (standard deviation of scores)
  - Front nine vs back nine comparison
  - Identifying the biggest scoring weakness
  - Plain-English trend narrative
"""

import pandas as pd
import numpy as np
from typing import List, Tuple


def rolling_avg_score(rounds: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Add a rolling average score column to the rounds DataFrame.
    Returns rounds with an added 'rolling_avg_score' column.
    Requires at least `window` rounds; NaN otherwise.
    """
    if "total_score" not in rounds.columns or rounds.empty:
        return rounds
    df = rounds.copy()
    df["rolling_avg_score"] = df["total_score"].rolling(window=window, min_periods=window).mean().round(1)
    return df


def score_consistency(rounds: pd.DataFrame) -> dict:
    """
    Returns consistency metrics:
      - std_dev: standard deviation of round scores
      - consistency_label: "Very Consistent" | "Consistent" | "Variable" | "Highly Variable"
    """
    if "total_score" not in rounds.columns or len(rounds) < 3:
        return {}

    std = rounds["total_score"].std()
    if std < 3:
        label = "Very Consistent"
    elif std < 5:
        label = "Consistent"
    elif std < 8:
        label = "Variable"
    else:
        label = "Highly Variable"

    return {
        "std_dev": round(std, 1),
        "consistency_label": label,
    }


def front_back_nine(df: pd.DataFrame) -> dict:
    """
    Compare front nine (holes 1–9) vs back nine (holes 10–18) scoring.
    Requires hole-level DataFrame with 'hole', 'score', 'par' columns.
    Returns average score vs par for each half, and the gap.
    """
    if df.empty or not all(c in df.columns for c in ["hole", "score", "par"]):
        return {}

    df = df.copy()
    df["score_vs_par"] = df["score"] - df["par"]

    front = df[df["hole"] <= 9]["score_vs_par"].mean()
    back = df[df["hole"] >= 10]["score_vs_par"].mean()

    if pd.isna(front) or pd.isna(back):
        return {}

    gap = round(back - front, 2)
    return {
        "front_nine_avg_vs_par": round(front, 2),
        "back_nine_avg_vs_par": round(back, 2),
        "back_vs_front_gap": gap,
        "worse_half": "Back Nine" if gap > 0 else "Front Nine" if gap < 0 else "Equal",
    }


def biggest_weakness(metrics: dict, hole_metrics: dict) -> str:
    """
    Identifies the single biggest scoring weakness based on available metrics.
    Returns a plain-English string.
    """
    candidates: List[Tuple[float, str]] = []

    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        # Normalise: lower GIR % = bigger problem. Map to a penalty score.
        candidates.append((max(0, 60 - gir) * 0.05, f"Approach play (GIR: {gir:.0f}%)"))

    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        candidates.append((max(0, putts - 30) * 0.2, f"Putting ({putts:.1f} putts/round)"))

    fairway = metrics.get("avg_fairway_pct")
    if fairway is not None:
        candidates.append((max(0, 60 - fairway) * 0.03, f"Driving accuracy (Fairway: {fairway:.0f}%)"))

    penalties = metrics.get("avg_penalties_per_round")
    if penalties is not None:
        candidates.append((max(0, penalties - 0.5) * 0.8, f"Course management ({penalties:.1f} penalties/round)"))

    if not candidates:
        return "Not enough data to determine your biggest weakness yet."

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def trend_narrative(rounds: pd.DataFrame, metrics: dict) -> str:
    """
    Generate a plain-English summary of the player's recent trend.
    Based on the last 5 rounds vs overall average.
    """
    n = len(rounds)
    if n < 5:
        return f"Upload more rounds (you have {n} — aim for at least 5) to see a trend summary."

    overall = metrics.get("avg_score")
    last5 = metrics.get("last5_avg_score")
    trend = metrics.get("trend_vs_overall")

    if overall is None or last5 is None or trend is None:
        return "Not enough scoring data to generate a trend summary."

    direction = "improving" if trend < -0.5 else "declining" if trend > 0.5 else "stable"

    if direction == "improving":
        return (
            f"Your game is trending in the right direction. "
            f"Your last 5 rounds average {last5:.1f} — that's {abs(trend):.1f} strokes better "
            f"than your overall average of {overall:.1f}. Keep it up."
        )
    elif direction == "declining":
        return (
            f"Your recent rounds are slightly higher than your average. "
            f"Your last 5 rounds average {last5:.1f} vs your overall average of {overall:.1f} "
            f"(+{trend:.1f}). Check the recommendations below to identify what to focus on."
        )
    else:
        return (
            f"Your scoring has been consistent recently. "
            f"Your last 5 rounds average {last5:.1f}, "
            f"close to your overall average of {overall:.1f}."
        )
