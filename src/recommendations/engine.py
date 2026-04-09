"""
recommendations/engine.py

Rule-based recommendation engine. Evaluates metric thresholds and returns
a prioritised list of actionable recommendations for the player.

Each recommendation includes:
  - issue: short label
  - headline: one-line plain-English summary
  - supporting_data: what the numbers show
  - recommendation: concrete action
  - practice_focus: drill / focus area
  - expected_impact: score improvement estimate
  - priority: "high" | "medium" | "low"
"""

from pathlib import Path
from typing import List, Dict
import yaml


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


def _load_thresholds() -> dict:
    with open(_find_config(), "r") as f:
        config = yaml.safe_load(f)
    return config.get("thresholds", {})


def generate_recommendations(metrics: dict, hole_metrics: dict) -> List[Dict]:
    """
    Evaluate all rules and return a list of triggered recommendations,
    sorted by priority (high → medium → low). Returns top 5 maximum.

    Parameters
    ----------
    metrics : dict  — output of calculator.compute_metrics()
    hole_metrics : dict — output of calculator.compute_hole_type_metrics()
    """
    t = _load_thresholds()
    recs: List[Dict] = []

    # --- GIR ---
    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        if gir < t.get("gir_poor", 40):
            recs.append({
                "issue": "Weak Approach Play",
                "headline": "You're missing most greens — this is costing you strokes every round",
                "supporting_data": f"You hit {gir:.0f}% of greens in regulation (benchmark: 50–60% for amateur golfers)",
                "recommendation": "Focus on accuracy with mid and short irons from 100–150 yards",
                "practice_focus": "7-iron to 9-iron drills: target accuracy, not distance. Aim for 70% of shots within 20 ft of pin",
                "expected_impact": "Potential savings of 2–4 strokes per round",
                "priority": "high",
            })
        elif gir < t.get("gir_moderate", 55):
            recs.append({
                "issue": "Inconsistent Approach Play",
                "headline": "Your iron play is inconsistent — improving it will lower your scores",
                "supporting_data": f"You hit {gir:.0f}% of greens in regulation (benchmark: 50–60%)",
                "recommendation": "Work on controlled tempo and consistent ball-striking with mid irons",
                "practice_focus": "Half-swing drills; focus on contact quality over distance",
                "expected_impact": "Potential savings of 1–2 strokes per round",
                "priority": "medium",
            })

    # --- Putts ---
    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        if putts > t.get("putts_high", 36):
            recs.append({
                "issue": "Putting Inefficiency",
                "headline": "Too many putts per round — this is one of the easiest areas to improve",
                "supporting_data": f"You average {putts:.1f} putts per round (benchmark: 30–32 for amateur golfers)",
                "recommendation": "Prioritise lag putting to eliminate 3-putts, then work on 3–6 ft conversion",
                "practice_focus": "Lag putting from 20–40 ft: focus on leaving the ball within 2 ft. Gate drill for short putts",
                "expected_impact": "Potential savings of 2–4 strokes per round",
                "priority": "high",
            })
        elif putts > t.get("putts_moderate", 32):
            recs.append({
                "issue": "Moderate Putting Weakness",
                "headline": "Your putting is slightly above average — small improvements add up",
                "supporting_data": f"You average {putts:.1f} putts per round (benchmark: 30–32)",
                "recommendation": "Work on short putt reliability and green-reading",
                "practice_focus": "3–6 ft putt conversion drills; consistent pre-putt routine",
                "expected_impact": "Potential savings of 1–2 strokes per round",
                "priority": "medium",
            })

    # --- Fairway ---
    fairway = metrics.get("avg_fairway_pct")
    if fairway is not None:
        if fairway < t.get("fairway_poor", 40):
            recs.append({
                "issue": "Inaccurate Driving",
                "headline": "You're missing most fairways — it's making the rest of each hole harder",
                "supporting_data": f"You hit {fairway:.0f}% of fairways (benchmark: 50–60% for amateurs)",
                "recommendation": "Club down off the tee for control; prioritise fairway over distance",
                "practice_focus": "3-wood or hybrid off the tee on tight holes. Focus on alignment and tempo — swing at 80%",
                "expected_impact": "Potential savings of 1–3 strokes per round",
                "priority": "high",
            })
        elif fairway < t.get("fairway_moderate", 55):
            recs.append({
                "issue": "Below-Average Driving Accuracy",
                "headline": "Your driving could be more consistent",
                "supporting_data": f"You hit {fairway:.0f}% of fairways (benchmark: 50–60%)",
                "recommendation": "Check alignment and commit to a pre-shot routine",
                "practice_focus": "Alignment rods on the range; controlled driver swing (no overswing)",
                "expected_impact": "Potential savings of 0.5–1.5 strokes per round",
                "priority": "medium",
            })

    # --- Penalties ---
    penalties = metrics.get("avg_penalties_per_round")
    if penalties is not None:
        if penalties > t.get("penalties_high", 2):
            recs.append({
                "issue": "Poor Course Management",
                "headline": "Too many penalty strokes — this is directly adding to your score",
                "supporting_data": f"You average {penalties:.1f} penalty strokes per round (target: under 1)",
                "recommendation": "Play conservatively near hazards; take the safe route even if longer",
                "practice_focus": "Pre-shot checklist: identify safe landing zones. When in doubt, lay up",
                "expected_impact": "Potential savings of 2–4 strokes per round",
                "priority": "high",
            })
        elif penalties > t.get("penalties_moderate", 1):
            recs.append({
                "issue": "Occasional Poor Decisions",
                "headline": "A few penalty strokes per round are costing you",
                "supporting_data": f"You average {penalties:.1f} penalty strokes per round (target: under 1)",
                "recommendation": "Be more conservative on high-risk shots",
                "practice_focus": "On-course decision-making: always identify the 'safe' option before the risky one",
                "expected_impact": "Potential savings of 0.5–1.5 strokes per round",
                "priority": "low",
            })

    # --- Par 3 weakness ---
    par3 = hole_metrics.get("par3_avg_vs_par")
    if par3 is not None and par3 > t.get("par3_avg_poor", 1.5):
        recs.append({
            "issue": "Struggling on Par 3s",
            "headline": "Par 3s are hurting your score — short iron accuracy needs work",
            "supporting_data": f"You average +{par3:.1f} on par 3 holes (target: +0.5 to +1.0 for amateurs)",
            "recommendation": "Focus on short iron distance control and tee-shot accuracy",
            "practice_focus": "8-iron to wedge distance control; full shots at 80% effort for accuracy",
            "expected_impact": "Potential savings of 0.5–1.5 strokes per round",
            "priority": "medium",
        })

    # --- Par 5 underperformance ---
    par5 = hole_metrics.get("par5_avg_vs_par")
    if par5 is not None and par5 > t.get("par5_avg_poor", 0.5):
        recs.append({
            "issue": "Not Scoring on Par 5s",
            "headline": "You're leaving shots on the table on par 5s — scoring holes you should capitalise on",
            "supporting_data": f"You average +{par5:.1f} on par 5 holes (target: close to even par or better)",
            "recommendation": "Improve layup strategy: don't go for the green in 2 unless the percentage is high",
            "practice_focus": "3rd shot wedge accuracy from 80–100 yards; treat par 5s as 3-shot holes",
            "expected_impact": "Potential savings of 0.5–1.5 strokes per round",
            "priority": "medium",
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: priority_order.get(r["priority"], 3))

    return recs[:5]
