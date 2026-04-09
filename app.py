"""
app.py — Golf Performance Analysis App

Entry point for the Streamlit app. Handles:
  - File upload
  - Data pipeline (ingest → clean → metrics → insights → recommendations)
  - Page rendering via tabs
"""

import streamlit as st
import pandas as pd

from src.data_ingestion.loader import load_csv
from src.data_cleaning.cleaner import clean, build_rounds
from src.metrics.calculator import compute_metrics, compute_hole_type_metrics
from src.recommendations.engine import generate_recommendations
from src.insights.analyzer import (
    rolling_avg_score,
    score_consistency,
    front_back_nine,
    biggest_weakness,
    trend_narrative,
)
from src.ui.components import (
    metric_card,
    no_data_notice,
    section_header,
    score_trend_chart,
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

# Light custom CSS
st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  [data-testid="stMetricValue"] { font-size: 1.6rem; }
  [data-testid="stMetricDelta"] { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

for key in ["df", "rounds", "metrics", "hole_metrics", "recommendations",
            "insights", "load_report"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── Header ────────────────────────────────────────────────────────────────────

st.title("⛳ Golf Performance Analysis")
st.caption("Upload your Golfshot export to get personalised insights and recommendations.")

st.divider()


# ── File upload ───────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Upload your Golfshot CSV export",
    type=["csv"],
    help="Export your scorecard data from the Golfshot app as a CSV file, then upload it here.",
)

if uploaded_file is not None:
    try:
        with st.spinner("Reading your data..."):
            raw_df, load_report = load_csv(uploaded_file)

        if load_report["missing_required"]:
            st.error(
                f"Your file is missing required columns: "
                f"**{', '.join(load_report['missing_required'])}**. "
                f"Please check that your CSV includes hole number, par, score, and date."
            )
            st.stop()

        with st.spinner("Cleaning data..."):
            df, skipped = clean(raw_df)
            rounds = build_rounds(df)

        if df.empty or rounds.empty:
            st.error("No valid rounds could be found in your file. Please check your CSV and try again.")
            st.stop()

        # Run the full pipeline
        rounds = rolling_avg_score(rounds, window=5)
        metrics = compute_metrics(rounds)
        hole_metrics = compute_hole_type_metrics(df)
        recommendations = generate_recommendations(metrics, hole_metrics)

        insights = {
            "consistency": score_consistency(rounds),
            "front_back": front_back_nine(df),
            "weakness": biggest_weakness(metrics, hole_metrics),
            "narrative": trend_narrative(rounds, metrics),
        }

        # Store in session state
        st.session_state.update({
            "df": df,
            "rounds": rounds,
            "metrics": metrics,
            "hole_metrics": hole_metrics,
            "recommendations": recommendations,
            "insights": insights,
            "load_report": load_report,
        })

        # Upload summary banner
        n_rounds = metrics.get("rounds_played", 0)
        n_holes = len(df)
        missing_opt = load_report.get("missing_optional", [])

        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(
                f"✅ Loaded **{n_rounds} round{'s' if n_rounds != 1 else ''}** "
                f"({n_holes} holes total)"
                + (f" — {skipped} rows skipped due to missing data" if skipped > 0 else "")
            )
        with col2:
            if missing_opt:
                with st.expander("ℹ️ Some metrics unavailable"):
                    st.write(
                        "These columns weren't found in your file, so some metrics won't show:\n"
                        + "\n".join(f"- {c.replace('_', ' ').title()}" for c in missing_opt)
                    )

    except ValueError as e:
        st.error(f"Could not read your file: {e}")
        st.stop()


# ── Main content (only when data is loaded) ───────────────────────────────────

if st.session_state.rounds is None:
    st.markdown("""
---
### How to export from Golfshot
1. Open the Golfshot app on your phone
2. Go to **Rounds** → select the rounds you want to analyse
3. Tap **Export** → choose **CSV**
4. Upload the file above

**What you'll get:**
- 📊 Score trends and key metrics
- 🎯 Personalised practice recommendations
- 📈 Insights on your strengths and weaknesses
""")
    st.stop()


rounds = st.session_state.rounds
metrics = st.session_state.metrics
hole_metrics = st.session_state.hole_metrics
recommendations = st.session_state.recommendations
insights = st.session_state.insights
n_rounds = metrics.get("rounds_played", 0)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_overview, tab_metrics, tab_insights, tab_recommendations = st.tabs([
    "📊 Overview",
    "📈 Metrics",
    "🔍 Insights",
    "🎯 Recommendations",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    section_header("Your Performance at a Glance")

    # Key metric tiles
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            "Average Score",
            metrics.get("avg_score"),
            help_text="Your mean gross score per round.",
        )
    with c2:
        metric_card(
            "Avg Score vs Par",
            f"+{metrics['avg_score_vs_par']:.1f}" if metrics.get("avg_score_vs_par", 0) >= 0
            else f"{metrics['avg_score_vs_par']:.1f}",
            help_text="How many strokes over (or under) par you average per round.",
        )
    with c3:
        metric_card(
            "Rounds Played",
            n_rounds,
            help_text="Total rounds included in this analysis.",
        )
    with c4:
        best = metrics.get("best_score")
        metric_card(
            "Best Round",
            best,
            help_text="Your lowest gross score across all uploaded rounds.",
        )

    st.markdown("")

    # Trend narrative
    narrative = insights.get("narrative", "")
    if narrative:
        st.info(f"📝 {narrative}")

    st.markdown("")

    # Score trend chart
    section_header("Score Trend", "Your gross score for each round over time")
    score_trend_chart(rounds)

    # Biggest weakness callout
    weakness = insights.get("weakness")
    if weakness:
        st.markdown("")
        st.warning(f"⚠️ **Biggest opportunity to improve:** {weakness}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — METRICS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_metrics:
    section_header("Detailed Performance Metrics")
    st.caption("All metrics are calculated from your uploaded rounds data.")

    # Core metrics row
    c1, c2, c3 = st.columns(3)
    with c1:
        gir = metrics.get("avg_gir_pct")
        metric_card(
            "Greens in Regulation %",
            f"{gir:.0f}" if gir is not None else None,
            suffix="%" if gir is not None else "",
            help_text=(
                "How often you reached the green in the expected number of shots. "
                "For a par 4, that means reaching the green in 2 shots or fewer."
            ),
        )
    with c2:
        fw = metrics.get("avg_fairway_pct")
        metric_card(
            "Fairways Hit %",
            f"{fw:.0f}" if fw is not None else None,
            suffix="%" if fw is not None else "",
            help_text="How often your tee shot lands in the fairway on par 4 and par 5 holes.",
        )
    with c3:
        putts = metrics.get("avg_putts_per_round")
        metric_card(
            "Putts per Round",
            putts,
            help_text="Average number of putts per round. Tour average is ~29; typical amateur is 32–36.",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        pen = metrics.get("avg_penalties_per_round")
        metric_card(
            "Penalties per Round",
            pen,
            help_text="Average penalty strokes per round (out of bounds, water hazards, etc.).",
        )
    with c5:
        consistency = insights.get("consistency", {})
        label = consistency.get("consistency_label")
        std = consistency.get("std_dev")
        if label and std is not None:
            st.metric(
                label="Score Consistency",
                value=label,
                help=f"Standard deviation of your round scores: {std}. Lower = more consistent.",
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
            help_text="Your average score over the last 5 rounds, compared to your overall average.",
        )

    st.divider()

    # Hole-type breakdown
    section_header("Performance by Hole Type", "How you score on par 3s, 4s, and 5s")
    hole_type_bar_chart(hole_metrics)

    # Rounds table
    st.divider()
    section_header("All Rounds", "Full breakdown of every round in your file")

    display_cols = {
        "round_id": "Round",
        "date": "Date",
        "course": "Course",
        "holes_played": "Holes",
        "total_score": "Score",
        "score_vs_par": "vs Par",
        "gir_pct": "GIR %",
        "fairway_pct": "Fairway %",
        "putts_per_round": "Putts",
        "total_penalties": "Penalties",
    }
    available = {k: v for k, v in display_cols.items() if k in rounds.columns}
    display_df = rounds[list(available.keys())].rename(columns=available).copy()

    if "Date" in display_df.columns:
        display_df["Date"] = display_df["Date"].dt.strftime("%b %d, %Y")
    if "vs Par" in display_df.columns:
        display_df["vs Par"] = display_df["vs Par"].apply(
            lambda x: f"+{int(x)}" if x > 0 else str(int(x)) if pd.notna(x) else ""
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_insights:
    section_header("Deep Dive Insights")

    # Front / back nine
    section_header("Front Nine vs Back Nine", "Do you play better on the first or second half?")
    fb = insights.get("front_back", {})
    if fb:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Front Nine Avg vs Par", f"+{fb['front_nine_avg_vs_par']:.2f}")
        with c2:
            st.metric("Back Nine Avg vs Par", f"+{fb['back_nine_avg_vs_par']:.2f}")
        with c3:
            gap = fb["back_vs_front_gap"]
            worse = fb["worse_half"]
            st.metric(
                "Gap",
                f"{gap:+.2f} strokes",
                help=f"Your {worse} is harder for you on average per hole.",
            )
        front_back_chart(fb)
    else:
        no_data_notice("Not enough hole data to compare front and back nine.")

    st.divider()

    # Consistency
    section_header("Score Consistency", "How much do your scores vary round to round?")
    consistency = insights.get("consistency", {})
    if consistency:
        label = consistency["consistency_label"]
        std = consistency["std_dev"]
        label_colors = {
            "Very Consistent": "success",
            "Consistent": "success",
            "Variable": "warning",
            "Highly Variable": "error",
        }
        msg = (
            f"Your scores vary by about ±{std} strokes round to round — "
            f"that's classified as **{label}**."
        )
        if label in ["Very Consistent", "Consistent"]:
            st.success(msg)
        elif label == "Variable":
            st.warning(msg)
        else:
            st.error(msg)
    else:
        no_data_notice("Upload at least 3 rounds to see consistency data.")

    st.divider()

    # Score trend chart with rolling avg
    section_header("Score Trend with Rolling Average", "5-round moving average smooths out one-off rounds")
    score_trend_chart(rounds)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_recommendations:
    section_header(
        "Practice Recommendations",
        "Based on your data — these are the areas that will lower your score the most",
    )

    min_rounds = metrics.get("min_rounds_for_recommendations", 5)
    if n_rounds < min_rounds:
        no_data_notice(
            f"Upload at least {min_rounds} rounds to unlock personalised recommendations. "
            f"You currently have {n_rounds}."
        )
    elif not recommendations:
        st.success(
            "Great job — no major weaknesses detected in your current data. "
            "Keep playing and check back as more rounds are added."
        )
    else:
        st.caption(
            f"Showing the top {len(recommendations)} area{'s' if len(recommendations) != 1 else ''} "
            f"to focus on, ranked by impact on your score."
        )
        for rec in recommendations:
            recommendation_card(rec)
