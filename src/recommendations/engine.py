"""
recommendations/engine.py

Rule-based recommendation engine.
- Level-aware: thresholds adapt to the player's segment
- Each recommendation includes concrete drills and a stroke impact estimate
- Returns top 3 ranked by stroke impact
"""

from pathlib import Path
from typing import List, Dict, Optional
import yaml


def _find_config() -> Path:
    candidates = [
        Path(__file__).parents[2] / "config" / "column_mapping.yaml",
        Path.cwd() / "config" / "column_mapping.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"column_mapping.yaml not found. Tried: {candidates}")


def _load_thresholds() -> dict:
    with open(_find_config(), "r") as f:
        config = yaml.safe_load(f)
    return config.get("thresholds", {})


# ── Drills library ────────────────────────────────────────────────────────────

_DRILLS = {
    "lag_putting": {
        "name": "Lag Putting Ladder",
        "reps": "15 min per session",
        "description": (
            "Place balls at 20, 30, and 40 feet from the hole. "
            "Goal: leave every putt within 2 feet. "
            "Eliminates 3-putts, which are the fastest way to drop strokes."
        ),
    },
    "gate_drill": {
        "name": "Gate Drill (Short Putts)",
        "reps": "50 putts per session",
        "description": (
            "Place two tees 4 inches apart, 5 feet from the hole. "
            "Every putt must pass through the gate. "
            "Target: 45/50 success rate. Builds stroke consistency and confidence."
        ),
    },
    "circle_drill": {
        "name": "6-Foot Circle Drill",
        "reps": "8 putts per set, 3 sets",
        "description": (
            "Place 8 balls in a circle, 6 feet from the hole. "
            "Hole out each ball without moving to the next until it drops. "
            "Simulates pressure putts you face every round."
        ),
    },
    "iron_accuracy": {
        "name": "Iron Accuracy Target Practice",
        "reps": "20 balls per club, 3 clubs",
        "description": (
            "Pick a specific target (flag or cone) at 100, 130, and 150 yards. "
            "Hit 20 balls at each distance. Track how many land within 20 feet. "
            "Focus on consistent contact — tempo over power."
        ),
    },
    "half_swing": {
        "name": "Half-Swing Contact Drill",
        "reps": "30 balls per session",
        "description": (
            "Using a 7 or 8 iron, make controlled half swings at 70% effort. "
            "Focus on ball-first contact and a divot after the ball. "
            "This builds the muscle memory for crisp iron strikes."
        ),
    },
    "alignment_rod": {
        "name": "Alignment Rod Driving Drill",
        "reps": "20 drives per session",
        "description": (
            "Place two alignment rods on the range forming a 20-yard-wide corridor. "
            "Hit drives aiming to land between them. Swing at 80% effort. "
            "Accuracy beats distance — a fairway at 230 is better than rough at 270."
        ),
    },
    "club_down": {
        "name": "Club-Down Tee Challenge",
        "reps": "Full round drill",
        "description": (
            "For one round, tee off with 3-wood or hybrid on every hole under 400 yards. "
            "Track fairways hit. Most golfers add 0–5 yards distance per round "
            "but gain 20–30% more fairways — a clear stroke saver."
        ),
    },
    "risk_reward": {
        "name": "Risk-Reward Decision Checklist",
        "reps": "Every round",
        "description": (
            "Before any shot near a hazard, ask: 'Would I attempt this shot successfully "
            "7 out of 10 times on the range?' If no — take the safe option. "
            "Write down each decision. Review after the round."
        ),
    },
    "layup_rule": {
        "name": "The Layup Rule",
        "reps": "Every par 5",
        "description": (
            "On every par 5, plan a 3-shot hole from the tee. "
            "Identify your ideal layup distance (80–100 yards) and aim there on shot 2. "
            "Players who stop going for par 5s in 2 typically score half a stroke better per hole."
        ),
    },
    "par3_distance": {
        "name": "Par 3 Distance Control",
        "reps": "30 balls per session",
        "description": (
            "On the range, identify your carry distances for 8-iron, 9-iron, PW, and GW. "
            "Hit 5 balls with each club at 80% effort and note the carry. "
            "On the course, always choose the club that reaches the middle of the green — not the pin."
        ),
    },
    "wedge_accuracy": {
        "name": "Wedge Shot Accuracy Drill",
        "reps": "20 balls per distance",
        "description": (
            "From 80 and 100 yards, hit 20 balls at a target. "
            "Track how many finish within 20 feet of the flag. "
            "Par 5 scoring is won or lost with the 3rd shot — this is your birdie putt set-up."
        ),
    },
}


# ── Recommendation rules ──────────────────────────────────────────────────────

def generate_recommendations(
    metrics: dict,
    hole_metrics: dict,
    segment: Optional[dict] = None,
) -> List[Dict]:
    """
    Evaluate all rules and return top 3 recommendations ranked by stroke impact.

    Parameters
    ----------
    metrics : dict   — output of calculator.compute_metrics()
    hole_metrics : dict — output of calculator.compute_hole_type_metrics()
    segment : dict   — output of segmentation.classify_player() (optional)
                       when provided, thresholds adapt to the player's level
    """
    t = _load_thresholds()

    # If segment provided, override thresholds with level-appropriate targets
    if segment is not None:
        targets = segment.get("targets", {})
        benchmarks = segment.get("benchmarks", {})
        gir_poor     = benchmarks.get("gir_pct", t.get("gir_poor", 40))
        gir_moderate = (benchmarks.get("gir_pct", 40) + targets.get("gir_pct", 55)) / 2
        putts_high   = benchmarks.get("putts_per_round", t.get("putts_high", 36))
        putts_moderate = (benchmarks.get("putts_per_round", 36) + targets.get("putts_per_round", 32)) / 2
        fw_poor      = benchmarks.get("fairway_pct", t.get("fairway_poor", 40))
        fw_moderate  = (benchmarks.get("fairway_pct", 40) + targets.get("fairway_pct", 55)) / 2
        pen_high     = benchmarks.get("penalties_per_round", t.get("penalties_high", 2))
        pen_moderate = (benchmarks.get("penalties_per_round", 2) + targets.get("penalties_per_round", 1)) / 2
    else:
        gir_poor     = t.get("gir_poor", 40)
        gir_moderate = t.get("gir_moderate", 55)
        putts_high   = t.get("putts_high", 36)
        putts_moderate = t.get("putts_moderate", 32)
        fw_poor      = t.get("fairway_poor", 40)
        fw_moderate  = t.get("fairway_moderate", 55)
        pen_high     = t.get("penalties_high", 2)
        pen_moderate = t.get("penalties_moderate", 1)

    recs: List[Dict] = []

    # ── Approach play (GIR) ──────────────────────────────────────────────────
    gir = metrics.get("avg_gir_pct")
    if gir is not None:
        if gir < gir_poor:
            recs.append({
                "issue": "Weak Approach Play",
                "headline": "You're missing most greens — this is costing you strokes every round",
                "supporting_data": f"You hit {gir:.0f}% of greens in regulation (your level target: {int(gir_poor)}%+)",
                "recommendation": "Focus on accuracy with mid and short irons from 100–150 yards",
                "practice_focus": "Hit to targets — not distance. Aim for 70% of shots within 20 ft of pin.",
                "stroke_impact": round(max(0, (gir_poor - gir) / 100 * 18 * 0.7), 1),
                "priority": "high",
                "drills": [_DRILLS["iron_accuracy"], _DRILLS["half_swing"]],
            })
        elif gir < gir_moderate:
            recs.append({
                "issue": "Inconsistent Approach Play",
                "headline": "Your iron play is inconsistent — improving it will lower your scores",
                "supporting_data": f"You hit {gir:.0f}% of greens in regulation (target: {int(gir_moderate)}%+)",
                "recommendation": "Work on controlled tempo and consistent ball-striking with mid irons",
                "practice_focus": "Prioritise contact quality over distance — smooth and solid beats hard and mis-hit.",
                "stroke_impact": round(max(0, (gir_moderate - gir) / 100 * 18 * 0.7), 1),
                "priority": "medium",
                "drills": [_DRILLS["half_swing"], _DRILLS["iron_accuracy"]],
            })

    # ── Putting ──────────────────────────────────────────────────────────────
    putts = metrics.get("avg_putts_per_round")
    if putts is not None:
        if putts > putts_high:
            recs.append({
                "issue": "Too Many Putts",
                "headline": "Too many putts per round — one of the fastest areas to improve",
                "supporting_data": f"You average {putts:.1f} putts/round (your level target: under {int(putts_high)})",
                "recommendation": "Eliminate 3-putts with lag putting, then build short putt confidence",
                "practice_focus": "Lag putting first — distance control from 20–40 ft. Then gate drill for 5–6 footers.",
                "stroke_impact": round(max(0, putts - putts_high), 1),
                "priority": "high",
                "drills": [_DRILLS["lag_putting"], _DRILLS["gate_drill"]],
            })
        elif putts > putts_moderate:
            recs.append({
                "issue": "Putting Leaking Strokes",
                "headline": "Your putting is close — but small improvements here compound quickly",
                "supporting_data": f"You average {putts:.1f} putts/round (target: under {int(putts_moderate)})",
                "recommendation": "Focus on 5–8 ft conversion and consistent pre-putt routine",
                "practice_focus": "Circle drill for short putts under pressure. Build routine before every putt.",
                "stroke_impact": round(max(0, putts - putts_moderate), 1),
                "priority": "medium",
                "drills": [_DRILLS["circle_drill"], _DRILLS["gate_drill"]],
            })

    # ── Driving accuracy (Fairway %) ─────────────────────────────────────────
    fw = metrics.get("avg_fairway_pct")
    if fw is not None:
        if fw < fw_poor:
            recs.append({
                "issue": "Inaccurate Driving",
                "headline": "You're missing most fairways — everything gets harder from the rough",
                "supporting_data": f"You hit {fw:.0f}% of fairways (your level target: {int(fw_poor)}%+)",
                "recommendation": "Prioritise fairway over distance — club down when in doubt",
                "practice_focus": "Swing at 80% off the tee. A fairway at 230 beats rough at 270 every time.",
                "stroke_impact": round(max(0, (fw_poor - fw) / 100 * 14 * 0.35), 1),
                "priority": "high",
                "drills": [_DRILLS["alignment_rod"], _DRILLS["club_down"]],
            })
        elif fw < fw_moderate:
            recs.append({
                "issue": "Below-Average Driving Accuracy",
                "headline": "Your driving could be more consistent off the tee",
                "supporting_data": f"You hit {fw:.0f}% of fairways (target: {int(fw_moderate)}%+)",
                "recommendation": "Check alignment and commit to a consistent pre-shot routine",
                "practice_focus": "Alignment rods on the range — practise hitting a 20-yard corridor consistently.",
                "stroke_impact": round(max(0, (fw_moderate - fw) / 100 * 14 * 0.35), 1),
                "priority": "medium",
                "drills": [_DRILLS["alignment_rod"], _DRILLS["club_down"]],
            })

    # ── Course management (Penalties) ────────────────────────────────────────
    pen = metrics.get("avg_penalties_per_round")
    if pen is not None:
        if pen > pen_high:
            recs.append({
                "issue": "Poor Course Management",
                "headline": "Penalty strokes are directly inflating your score every round",
                "supporting_data": f"You take {pen:.1f} penalties/round (target: under {pen_high:.0f})",
                "recommendation": "Play conservatively near hazards — the safe route is nearly always the right call",
                "practice_focus": "Apply the 7/10 rule: only attempt a risky shot if you'd make it 7 times out of 10.",
                "stroke_impact": round(max(0, pen - pen_high), 1),
                "priority": "high",
                "drills": [_DRILLS["risk_reward"], _DRILLS["layup_rule"]],
            })
        elif pen > pen_moderate:
            recs.append({
                "issue": "Occasional Poor Decisions",
                "headline": "A few penalty strokes per round are adding up",
                "supporting_data": f"You take {pen:.1f} penalties/round (target: under {pen_moderate:.0f})",
                "recommendation": "Be more conservative on high-risk shots",
                "practice_focus": "Before each risky shot, identify the safe option first — then decide deliberately.",
                "stroke_impact": round(max(0, pen - pen_moderate), 1),
                "priority": "low",
                "drills": [_DRILLS["risk_reward"]],
            })

    # ── Par 3 holes ───────────────────────────────────────────────────────────
    par3 = hole_metrics.get("par3_avg_vs_par")
    par3_poor = t.get("par3_avg_poor", 1.5)
    if par3 is not None and par3 > par3_poor:
        recs.append({
            "issue": "Struggling on Par 3s",
            "headline": "Par 3 tee shots are hurting you — short iron accuracy is the fix",
            "supporting_data": f"You average +{par3:.2f} on par 3s (target: under +1.0)",
            "recommendation": "Commit to a specific club and target on every par 3 tee shot",
            "practice_focus": "Know your exact carry distances for each short iron. Never guess on a par 3.",
            "stroke_impact": round(max(0, par3 - 1.0) * 4, 1),  # 4 par 3s per round
            "priority": "medium",
            "drills": [_DRILLS["par3_distance"], _DRILLS["iron_accuracy"]],
        })

    # ── Par 5 holes ───────────────────────────────────────────────────────────
    par5 = hole_metrics.get("par5_avg_vs_par")
    par5_poor = t.get("par5_avg_poor", 0.5)
    if par5 is not None and par5 > par5_poor:
        recs.append({
            "issue": "Not Scoring on Par 5s",
            "headline": "You're leaving shots on the table on the easiest scoring holes",
            "supporting_data": f"You average +{par5:.2f} on par 5s (target: close to even par)",
            "recommendation": "Treat every par 5 as a 3-shot hole — plan your layup on shot 2",
            "practice_focus": "Master your 80–100 yard wedge shot. That's the par 5 birdie set-up shot.",
            "stroke_impact": round(max(0, par5 - 0.3) * 4, 1),  # 4 par 5s per round
            "priority": "medium",
            "drills": [_DRILLS["wedge_accuracy"], _DRILLS["layup_rule"]],
        })

    # Sort by stroke impact descending, return top 3
    recs.sort(key=lambda r: r.get("stroke_impact", 0), reverse=True)
    return recs[:3]
