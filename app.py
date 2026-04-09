"""
app.py — Golf Performance Analysis App
Entry point for the Streamlit app.
"""

import streamlit as st
import pandas as pd

from src.data_ingestion.loader import load_csv
from src.data_cleaning.cleaner import clean, build_rounds
from src.metrics.calculator import compute_metrics, compute_hole_type_metrics
from src.metrics.segmentation import (
    classify_player,
    compute_strokes_lost,
    compute_area_performance,
    generate_profile_label,
)
from src.recommendations.engine import generate_recommendations
from src.insights.analyzer import (
    rolling_avg_score,
    score_consistency,
    front_back_nine,
    last5_vs_prev5,
    biggest_weakness,
    trend_narrative,
)
from src.ui.map_view import render_course_map
from src.ui.components import (
    metric_card,
    no_data_notice,
    section_header,
    coaching_summary_card,
    strokes_lost_chart,
    score_trend_chart,
    trend_comparison_chart,
    hole_type_bar_chart,
    front_back_chart,
    recommendation_card,
)


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Golf Performance Analysis",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
  [data-testid="stMetricDelta"] { font-size: 0.85rem; }
  [data-testid="stMetricLabel"] { font-size: 0.85rem; font-weight: 600; color: #374151; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

for key in ["df", "rounds", "metrics", "hole_metrics", "recommendations",
            "insights", "segment", "coaching", "load_report"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── Header ────────────────────────────────────────────────────────────────────

st.title("⛳ Golf Performance Analysis")
st.caption("Upload your Golfshot export to get personalised coaching insights.")
st.divider()


# ── File upload & pipeline ────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Upload your Golfshot CSV export",
    type=["csv"],
    help="Export scorecard data from Golfshot as CSV, then upload it here.",
)

if uploaded_file is not None:
    try:
        with st.spinner("Reading your data..."):
            raw_df, load_report = load_csv(uploaded_file)

        if load_report["missing_required"]:
            st.error(
                f"Your file is missing required columns: "
                f"**{', '.join(load_report['missing_required'])}**. "
                f"Please check your CSV includes date, hole, par, and score."
            )
            st.stop()

        with st.spinner("Analysing your game..."):
            df, skipped     = clean(raw_df)
            rounds          = build_rounds(df)

            if df.empty or rounds.empty:
                st.error("No valid rounds found. Please check your CSV and try again.")
                st.stop()

            rounds          = rolling_avg_score(rounds, window=5)
            metrics         = compute_metrics(rounds)
            hole_metrics    = compute_hole_type_metrics(df)
            consistency     = score_consistency(rounds)

            # Segmentation & coaching layer
            avg_score = metrics.get("avg_score", 100)
            segment   = classify_player(avg_score)
            recommendations = generate_recommendations(metrics, hole_metrics, segment)
            strokes_lost    = compute_strokes_lost(metrics, segment)
            area_perf       = compute_area_performance(metrics, segment)
            profile_label   = generate_profile_label(
                metrics, segment, std_dev=consistency.get("std_dev")
            )
            trend_5v5 = last5_vs_prev5(rounds)

            insights = {
                "consistency": consistency,
                "front_back":  front_back_nine(df),
                "weakness":    biggest_weakness(metrics, hole_metrics),
                "narrative":   trend_narrative(rounds, metrics),
                "trend_5v5":   trend_5v5,
            }
            coaching = {
                "segment":       segment,
                "strokes_lost":  strokes_lost,
                "area_perf":     area_perf,
                "profile_label": profile_label,
                "trend_5v5":     trend_5v5,
            }

        st.session_state.update({
            "df": df, "rounds": rounds, "metrics": metrics,
            "hole_metrics": hole_metrics, "recommendations": recommendations,
            "insights": insights, "coaching": coaching,
            "load_report": load_report,
        })

        n_rounds    = metrics.get("rounds_played", 0)
        missing_opt = load_report.get("missing_optional", [])
        col1, col2  = st.columns([3, 1])
        with col1:
            st.success(
                f"✅ Loaded **{n_rounds} round{'s' if n_rounds != 1 else ''}** "
                f"({len(df)} holes)"
                + (f" — {skipped} rows skipped" if skipped > 0 else "")
            )
        with col2:
            if missing_opt:
                with st.expander("ℹ️ Some metrics unavailable"):
                    st.write("\n".join(
                        f"- {c.replace('_', ' ').title()}" for c in missing_opt
                    ))

    except ValueError as e:
        st.error(f"Could not read your file: {e}")
        st.stop()


# ── Guard: no data yet ────────────────────────────────────────────────────────

if st.session_state.rounds is None:
    st.markdown("""
---
### How to export from Golfshot
1. Open Golfshot on your phone
2. Go to **Rounds** → select rounds → **Export** → **CSV**
3. Upload the file above

**What you'll get:**
- 🏌️ Player profile & skill level classification
- 📊 Strokes-gained style analysis
- 🎯 Top 3 prioritised recommendations with practice drills
- 📈 Score trends and recent form comparison
- 🗺️ Interactive course map
""")
    st.stop()


# ── Pull from session state ───────────────────────────────────────────────────

rounds          = st.session_state.rounds
metrics         = st.session_state.metrics
hole_metrics    = st.session_state.hole_metrics
recommendations = st.session_state.recommendations
insights        = st.session_state.insights
coaching        = st.session_state.coaching
n_rounds        = metrics.get("rounds_played", 0)

segment       = coaching["segment"]
strokes_lost  = coaching["strokes_lost"]
area_perf     = coaching["area_perf"]
profile_label = coaching["profile_label"]
trend_5v5     = coaching["trend_5v5"]


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_overview, tab_coaching, tab_metrics, tab_insights, tab_map = st.tabs([
    "📊 Overview",
    "🎯 Coaching",
    "📈 Metrics",
    "🔍 Insights",
    "🗺️ Course Map",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    # Coaching summary card (player profile + fix first / strength / form)
    coaching_summary_card(segment, profile_label, area_perf, trend_5v5, metrics)

    st.divider()

    # Key metric tiles
    section_header("Performance Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Average Score", metrics.get("avg_score"),
                    help_text="Your mean gross score per round.")
    with c2:
        svp = metrics.get("avg_score_vs_par")
        metric_card(
            "Avg vs Par",
            f"+{svp:.1f}" if svp is not None and svp >= 0 else f"{svp:.1f}" if svp is not None else None,
            help_text="How many strokes over or under par you average per round.",
        )
    with c3:
        metric_card("Rounds Played", n_rounds,
                    help_text="Total rounds included in this analysis.")
    with c4:
        metric_card("Best Round", metrics.get("best_score"),
                    help_text="Your lowest gross score across all uploaded rounds.")

    st.markdown("")

    narrative = insights.get("narrative", "")
    if narrative:
        st.info(f"📝 {narrative}")

    st.markdown("")
    section_header("Score Trend", "Your gross score for each round over time")
    score_trend_chart(rounds, key="score_trend_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COACHING (new)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_coaching:
    section_header(
        "Personalised Coaching Plan",
        f"Based on your data — calibrated for {segment['level']} level players",
    )

    # Player level description
    st.markdown(
        f"""
<div style="background:{segment['color']}12; border-left:4px solid {segment['color']};
            padding:12px 16px; border-radius:0 8px 8px 0; margin-bottom:20px;">
  <strong>{segment['emoji']} {segment['level']} Golfer</strong><br>
  <span style="color:#374151;">{segment['description']}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    # Strokes-lost breakdown
    section_header(
        "Where You're Losing Strokes",
        f"Estimated strokes lost per round vs {segment['target_label']} benchmarks",
    )
    strokes_lost_chart(strokes_lost, segment)

    st.caption(
        "ℹ️ These estimates use standard golf analytics factors: each missed green costs ~0.7 strokes, "
        "each missed fairway ~0.35, putts and penalties are counted directly."
    )

    st.divider()

    # Top 3 recommendations with drills
    section_header(
        "Top 3 Priorities — Ranked by Stroke Impact",
        "Fix these in order for the fastest improvement to your score",
    )

    min_rounds = 5
    if n_rounds < min_rounds:
        no_data_notice(
            f"Upload at least {min_rounds} rounds to unlock personalised recommendations. "
            f"You have {n_rounds} so far."
        )
    elif not recommendations:
        st.success(
            "No major weaknesses detected. You're performing at or above your level benchmarks. "
            "Keep playing and upload more rounds to refine this analysis."
        )
    else:
        for i, rec in enumerate(recommendations, 1):
            recommendation_card(rec, rank=i)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — METRICS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_metrics:
    section_header("Detailed Performance Metrics")
    st.caption(
        f"All metrics compared against **{segment['level']}** level benchmarks "
        f"(target: {segment['target_label']})"
    )

    benchmarks = segment["benchmarks"]
    targets    = segment["targets"]

    c1, c2, c3 = st.columns(3)
    with c1:
        gir = metrics.get("avg_gir_pct")
        metric_card(
            "Greens in Regulation %",
            f"{gir:.0f}" if gir is not None else None,
            suffix="%" if gir is not None else "",
            help_text=(
                f"How often you reach the green in the expected number of shots. "
                f"Your level benchmark: {benchmarks['gir_pct']}% | Target: {targets['gir_pct']}%"
            ),
        )
    with c2:
        fw = metrics.get("avg_fairway_pct")
        metric_card(
            "Fairways Hit %",
            f"{fw:.0f}" if fw is not None else None,
            suffix="%" if fw is not None else "",
            help_text=(
                f"Tee shots landing in the fairway on par 4 and par 5 holes. "
                f"Benchmark: {benchmarks['fairway_pct']}% | Target: {targets['fairway_pct']}%"
            ),
        )
    with c3:
        putts = metrics.get("avg_putts_per_round")
        metric_card(
            "Putts per Round",
            putts,
            help_text=(
                f"Average putts per round. "
                f"Benchmark: {benchmarks['putts_per_round']} | Target: {targets['putts_per_round']}"
            ),
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        pen = metrics.get("avg_penalties_per_round")
        metric_card(
            "Penalties per Round",
            pen,
            help_text=(
                f"Average penalty strokes (OB, water, etc.). "
                f"Benchmark: {benchmarks['penalties_per_round']} | Target: {targets['penalties_per_round']}"
            ),
        )
    with c5:
        consistency = insights.get("consistency", {})
        label = consistency.get("consistency_label")
        std   = consistency.get("std_dev")
        if label and std is not None:
            st.metric(
                label="Score Consistency",
                value=label,
                help=f"Standard deviation of round scores: ±{std} strokes. Lower = more consistent.",
            )
        else:
            metric_card("Score Consistency", None)
    with c6:
        last5 = metrics.get("last5_avg_score")
        trend = metrics.get("trend_vs_overall")
        metric_card(
            "Last 5 Rounds Avg",
            last5,
            delta=trend,
            delta_label="vs overall avg",
            help_text="Your average score over the last 5 rounds vs your overall average.",
        )

    st.divider()
    section_header("Performance by Hole Type", "How you score on par 3s, 4s, and 5s")
    hole_type_bar_chart(hole_metrics)

    st.divider()
    section_header("All Rounds")
    display_cols = {
        "round_id": "Round", "date": "Date", "course": "Course",
        "holes_played": "Holes", "total_score": "Score", "score_vs_par": "vs Par",
        "gir_pct": "GIR %", "fairway_pct": "Fairway %",
        "putts_per_round": "Putts", "total_penalties": "Penalties",
    }
    available  = {k: v for k, v in display_cols.items() if k in rounds.columns}
    display_df = rounds[list(available.keys())].rename(columns=available).copy()
    if "Date" in display_df.columns:
        display_df["Date"] = display_df["Date"].dt.strftime("%b %d, %Y")
    if "vs Par" in display_df.columns:
        display_df["vs Par"] = display_df["vs Par"].apply(
            lambda x: f"+{int(x)}" if pd.notna(x) and x > 0 else str(int(x)) if pd.notna(x) else ""
        )
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_insights:
    section_header("Deep Dive Insights")

    # Last 5 vs previous 5
    section_header(
        "Recent Form vs Previous Form",
        "Last 5 rounds compared against the 5 rounds before that",
    )
    if trend_5v5:
        direction  = trend_5v5.get("score_direction", "stable")
        score_cmp  = trend_5v5.get("score", {})
        dir_map    = {"improving": ("↓ Improving", "#059669"), "declining": ("↑ Declining", "#dc2626"), "stable": ("→ Stable", "#64748b")}
        dir_label, dir_color = dir_map.get(direction, ("—", "#64748b"))

        c1, c2, c3 = st.columns(3)
        with c1:
            if score_cmp:
                st.metric("Last 5 Avg Score", score_cmp.get("last5", "—"))
        with c2:
            if score_cmp:
                st.metric("Previous 5 Avg Score", score_cmp.get("prev", "—"))
        with c3:
            if score_cmp:
                delta = score_cmp.get("delta", 0)
                st.metric(
                    "Trend",
                    dir_label,
                    help=f"Score change: {'+' if delta >= 0 else ''}{delta:.1f} strokes vs previous 5 rounds",
                )
        trend_comparison_chart(trend_5v5)
    else:
        no_data_notice("Upload at least 6 rounds to compare recent vs previous form.")

    st.divider()

    # Front / back nine
    section_header("Front Nine vs Back Nine")
    fb = insights.get("front_back", {})
    if fb:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Front Nine Avg vs Par", f"+{fb['front_nine_avg_vs_par']:.2f}")
        with c2:
            st.metric("Back Nine Avg vs Par", f"+{fb['back_nine_avg_vs_par']:.2f}")
        with c3:
            gap   = fb["back_vs_front_gap"]
            worse = fb["worse_half"]
            st.metric("Gap", f"{gap:+.2f} strokes/hole",
                      help=f"Your {worse} is harder on average.")
        front_back_chart(fb)
    else:
        no_data_notice("Not enough hole data to compare front and back nine.")

    st.divider()

    # Consistency
    section_header("Score Consistency", "How much your scores vary round to round")
    consistency = insights.get("consistency", {})
    if consistency:
        label = consistency["consistency_label"]
        std   = consistency["std_dev"]
        msg   = f"Your scores vary by about ±{std} strokes round to round — classified as **{label}**."
        if label in ["Very Consistent", "Consistent"]:
            st.success(msg)
        elif label == "Variable":
            st.warning(msg)
        else:
            st.error(msg)
    else:
        no_data_notice("Upload at least 3 rounds to see consistency data.")

    st.divider()
    section_header("Score Trend with Rolling Average")
    score_trend_chart(rounds, key="score_trend_insights")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — COURSE MAP
# ═══════════════════════════════════════════════════════════════════════════════

with tab_map:
    section_header(
        "Courses Played",
        "Hover over a pin to see your scores at that course",
    )
    render_course_map(rounds)
