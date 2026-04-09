"""
metrics/segmentation.py

Player segmentation: classifies the player into a skill level based on
average score, then computes level-relative benchmarks, strokes-lost
estimates, and a descriptive player profile label.
"""

from typing import List, Dict, Optional

# ── Level definitions ─────────────────────────────────────────────────────────

LEVELS: Dict[str, dict] = {
    "Beginner": {
        "score_min": 100,
        "score_max": 999,
        "emoji": "🌱",
        "color": "#6b7280",
        "description": "You're building your foundations. Every round is a learning opportunity.",
        "benchmarks": {
            "gir_pct": 15,
            "fairway_pct": 35,
            "putts_per_round": 40,
            "penalties_per_round": 3.0,
        },
        "targets": {
            "gir_pct": 30,
            "fairway_pct": 50,
            "putts_per_round": 36,
            "penalties_per_round": 2.0,
        },
        "target_label": "Intermediate",
    },
    "Intermediate": {
        "score_min": 85,
        "score_max": 100,
        "emoji": "🏌️",
        "color": "#2563eb",
        "description": "Your game has real strengths. Consistency is the key to breaking 85.",
        "benchmarks": {
            "gir_pct": 30,
            "fairway_pct": 50,
            "putts_per_round": 36,
            "penalties_per_round": 2.0,
        },
        "targets": {
            "gir_pct": 50,
            "fairway_pct": 65,
            "putts_per_round": 32,
            "penalties_per_round": 1.0,
        },
        "target_label": "Advanced",
    },
    "Advanced": {
        "score_min": 70,
        "score_max": 85,
        "emoji": "⚡",
        "color": "#7c3aed",
        "description": "You're a competitive player. Small, focused improvements compound into lower scores.",
        "benchmarks": {
            "gir_pct": 50,
            "fairway_pct": 65,
            "putts_per_round": 32,
            "penalties_per_round": 1.0,
        },
        "targets": {
            "gir_pct": 65,
            "fairway_pct": 75,
            "putts_per_round": 29,
            "penalties_per_round": 0.3,
        },
        "target_label": "Elite",
    },
    "Elite": {
        "score_min": 0,
        "score_max": 70,
        "emoji": "🏆",
        "color": "#059669",
        "description": "Tour-level performance. Marginal gains are where lower scores are found.",
        "benchmarks": {
            "gir_pct": 65,
            "fairway_pct": 75,
            "putts_per_round": 29,
            "penalties_per_round": 0.3,
        },
        "targets": {
            "gir_pct": 70,
            "fairway_pct": 80,
            "putts_per_round": 28,
            "penalties_per_round": 0.1,
        },
        "target_label": "Tour Average",
    },
}


def classify_player(avg_score: float) -> dict:
    """
    Return the level dict for a given average score.
    Includes level name + all benchmark / target data.
    """
    for level_name, level in LEVELS.items():
        if level["score_min"] <= avg_score < level["score_max"]:
            return {"level": level_name, **level}
    return {"level": "Beginner", **LEVELS["Beginner"]}


# ── Strokes-lost analysis ─────────────────────────────────────────────────────

# Penalty factors: how many strokes each unit of gap costs
_PENALTIES = {
    "putts":    1.0,   # 1 extra putt = 1 stroke (direct)
    "gir":      0.70,  # each missed green (vs target) costs ~0.7 strokes
    "fairway":  0.35,  # each missed fairway costs ~0.35 strokes
    "penalties": 1.0,  # 1 extra penalty = 1 stroke (direct)
}


def compute_strokes_lost(metrics: dict, segment: dict) -> List[Dict]:
    """
    Estimate strokes lost per round vs the target level in each area.

    Returns a list sorted by strokes_lost descending (biggest leak first).
    Each entry:
        area, strokes_lost, your_value, target_value, note
    """
    targets = segment["targets"]
    results = []

    # ── Putting ──
    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        gap = max(0.0, putts - targets["putts_per_round"])
        results.append({
            "area": "Putting",
            "strokes_lost": round(gap * _PENALTIES["putts"], 2),
            "your_value": f"{putts:.1f} putts/round",
            "target_value": f"{targets['putts_per_round']} putts/round",
            "note": "Each extra putt is a direct stroke added to your score.",
        })

    # ── Approach play (GIR) ──
    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        extra_missed = max(0.0, (targets["gir_pct"] - gir) / 100.0 * 18)
        results.append({
            "area": "Approach Play",
            "strokes_lost": round(extra_missed * _PENALTIES["gir"], 2),
            "your_value": f"{gir:.0f}% greens hit",
            "target_value": f"{targets['gir_pct']}% greens hit",
            "note": "Each missed green costs ~0.7 strokes on average (accounting for up-and-downs).",
        })

    # ── Driving accuracy (Fairway %) ──
    fw = metrics.get("avg_fairway_pct")
    if fw is not None:
        extra_missed = max(0.0, (targets["fairway_pct"] - fw) / 100.0 * 14)
        results.append({
            "area": "Driving Accuracy",
            "strokes_lost": round(extra_missed * _PENALTIES["fairway"], 2),
            "your_value": f"{fw:.0f}% fairways hit",
            "target_value": f"{targets['fairway_pct']}% fairways hit",
            "note": "Each missed fairway costs ~0.35 strokes on average.",
        })

    # ── Course management (Penalties) ──
    pen = metrics.get("avg_penalties_per_round")
    if pen is not None:
        gap = max(0.0, pen - targets["penalties_per_round"])
        results.append({
            "area": "Course Management",
            "strokes_lost": round(gap * _PENALTIES["penalties"], 2),
            "your_value": f"{pen:.1f} penalties/round",
            "target_value": f"{targets['penalties_per_round']} penalties/round",
            "note": "Each penalty stroke is added directly to your score.",
        })

    results.sort(key=lambda x: x["strokes_lost"], reverse=True)
    return results


# ── Player profile label ──────────────────────────────────────────────────────

def generate_profile_label(metrics: dict, segment: dict, std_dev: Optional[float] = None) -> str:
    """
    Generate a short descriptive label summarising the player's profile.
    Example: "Strong putter, weak approach player, consistent scorer"
    Comparisons are made relative to the player's own level benchmarks.
    """
    benchmarks = segment["benchmarks"]
    descriptors = []

    # Putting
    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        if putts < benchmarks["putts_per_round"] - 1.5:
            descriptors.append(("strength", "strong putter"))
        elif putts > benchmarks["putts_per_round"] + 2.5:
            descriptors.append(("weakness", "weak putter"))

    # Approach play (GIR)
    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        if gir > benchmarks["gir_pct"] + 8:
            descriptors.append(("strength", "strong approach player"))
        elif gir < benchmarks["gir_pct"] - 8:
            descriptors.append(("weakness", "weak approach player"))

    # Driving accuracy
    fw = metrics.get("avg_fairway_pct")
    if fw is not None:
        if fw > benchmarks["fairway_pct"] + 10:
            descriptors.append(("strength", "accurate driver"))
        elif fw < benchmarks["fairway_pct"] - 10:
            descriptors.append(("weakness", "inconsistent driver"))

    # Course management
    pen = metrics.get("avg_penalties_per_round")
    if pen is not None:
        if pen < benchmarks["penalties_per_round"] * 0.5:
            descriptors.append(("strength", "smart course manager"))
        elif pen > benchmarks["penalties_per_round"] * 1.5:
            descriptors.append(("weakness", "takes too many risks"))

    # Consistency (std dev)
    if std_dev is not None:
        if std_dev < 3.0:
            descriptors.append(("strength", "very consistent scorer"))
        elif std_dev > 7.0:
            descriptors.append(("weakness", "high-variance scorer"))

    # Build label: up to 1 strength + 1 weakness + 1 consistency tag
    parts = []
    strengths = [d[1] for d in descriptors if d[0] == "strength"]
    weaknesses = [d[1] for d in descriptors if d[0] == "weakness"]

    if strengths:
        parts.append(strengths[0].capitalize())
    if weaknesses:
        parts.append(weaknesses[0])
    if len(parts) < 2 and len(descriptors) > len(parts):
        remaining = [d[1] for d in descriptors if d[1] not in parts]
        if remaining:
            parts.append(remaining[0])

    return ", ".join(parts) if parts else "Balanced player"


# ── Strength / weakness summary ───────────────────────────────────────────────

def compute_area_performance(metrics: dict, segment: dict) -> List[Dict]:
    """
    For each area, return strokes gained (positive = better than benchmark).
    Used to identify biggest strength and biggest weakness.
    """
    benchmarks = segment["benchmarks"]
    results = []

    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        results.append({
            "area": "Putting",
            "strokes_gained": round((benchmarks["putts_per_round"] - putts) * 1.0, 2),
        })

    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        diff_pct = (gir - benchmarks["gir_pct"]) / 100.0 * 18
        results.append({
            "area": "Approach Play",
            "strokes_gained": round(diff_pct * 0.7, 2),
        })

    fw = metrics.get("avg_fairway_pct")
    if fw is not None:
        diff_pct = (fw - benchmarks["fairway_pct"]) / 100.0 * 14
        results.append({
            "area": "Driving Accuracy",
            "strokes_gained": round(diff_pct * 0.35, 2),
        })

    pen = metrics.get("avg_penalties_per_round")
    if pen is not None:
        results.append({
            "area": "Course Management",
            "strokes_gained": round((benchmarks["penalties_per_round"] - pen) * 1.0, 2),
        })

    results.sort(key=lambda x: x["strokes_gained"], reverse=True)
    return results
