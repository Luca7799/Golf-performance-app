"""
insights/analyzer.py

Derives deeper insights from rounds data:
  - Rolling averages (score trend over last N rounds)
  - Consistency (standard deviation of scores)
  - Front nine vs back nine comparison
  - Last 5 vs previous 5 rounds comparison
  - Identifying the biggest scoring weakness
  - Plain-English trend narrative
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


def rolling_avg_score(rounds: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    if "total_score" not in rounds.columns or rounds.empty:
        return rounds
    df = rounds.copy()
    df["rolling_avg_score"] = (
        df["total_score"].rolling(window=window, min_periods=window).mean().round(1)
    )
    return df


def score_consistency(rounds: pd.DataFrame) -> dict:
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
        "std_dev": round(float(std), 1),
        "consistency_label": label,
    }


def front_back_nine(df: pd.DataFrame) -> dict:
    if df.empty or not all(c in df.columns for c in ["hole", "score", "par"]):
        return {}

    df = df.copy()
    df["score_vs_par"] = df["score"] - df["par"]

    front = df[df["hole"] <= 9]["score_vs_par"].mean()
    back = df[df["hole"] >= 10]["score_vs_par"].mean()

    if pd.isna(front) or pd.isna(back):
        return {}

    gap = round(float(back - front), 2)
    return {
        "front_nine_avg_vs_par": round(float(front), 2),
        "back_nine_avg_vs_par": round(float(back), 2),
        "back_vs_front_gap": gap,
        "worse_half": "Back Nine" if gap > 0 else "Front Nine" if gap < 0 else "Equal",
    }


def last5_vs_prev5(rounds: pd.DataFrame) -> dict:
    """
    Compare the last 5 rounds against the 5 rounds before that.
    Requires at least 6 rounds. With 6–9 rounds uses all preceding rounds as baseline.

    Returns direction per area (score, GIR, putts, fairway) and magnitude.
    """
    n = len(rounds)
    if n < 6:
        return {}

    last5 = rounds.tail(5)
    prev = rounds.iloc[-(min(n, 10)):-5] if n >= 10 else rounds.head(n - 5)

    result: dict = {"rounds_compared": min(n - 5, 5)}

    def _compare(col: str) -> Optional[dict]:
        if col not in rounds.columns:
            return None
        l = last5[col].dropna().mean()
        p = prev[col].dropna().mean()
        if pd.isna(l) or pd.isna(p):
            return None
        delta = round(float(l - p), 2)
        return {"last5": round(float(l), 1), "prev": round(float(p), 1), "delta": delta}

    score_cmp = _compare("total_score")
    if score_cmp:
        result["score"] = score_cmp
        # For score: negative delta = improving
        result["score_direction"] = (
            "improving" if score_cmp["delta"] < -0.5
            else "declining" if score_cmp["delta"] > 0.5
            else "stable"
        )

    gir_cmp = _compare("gir_pct")
    if gir_cmp:
        result["gir"] = gir_cmp

    putts_cmp = _compare("putts_per_round")
    if putts_cmp:
        result["putts"] = putts_cmp

    fw_cmp = _compare("fairway_pct")
    if fw_cmp:
        result["fairway"] = fw_cmp

    return result


def biggest_weakness(metrics: dict, hole_metrics: dict) -> str:
    candidates: List[Tuple[float, str]] = []

    gir = metrics.get("avg_gir_pct")
    if gir is not None:
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
            f"Last 5 rounds: {last5:.1f} vs overall average of {overall:.1f} "
            f"(+{trend:.1f}). Check the recommendations below to focus your practice."
        )
    else:
        return (
            f"Your scoring has been consistent recently. "
            f"Last 5 rounds average {last5:.1f}, close to your overall average of {overall:.1f}."
        )
