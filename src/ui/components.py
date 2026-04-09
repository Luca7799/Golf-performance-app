"""
ui/components.py

Reusable Streamlit UI building blocks used across pages.
All labels are written in plain English — no technical jargon.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# ── Metric cards ──────────────────────────────────────────────────────────────

def metric_card(label: str, value, suffix: str = "", delta=None, delta_label: str = "", help_text: str = ""):
    """Render a styled metric tile."""
    if value is None:
        st.metric(label=label, value="No data", help=help_text or "Not enough data in your file for this metric.")
    else:
        formatted = f"{value}{suffix}"
        st.metric(
            label=label,
            value=formatted,
            delta=f"{delta:+.1f} {delta_label}" if delta is not None else None,
            delta_color="inverse",  # lower score = green (good)
            help=help_text,
        )


def no_data_notice(message: str = "Not enough data available for this section."):
    st.info(f"ℹ️ {message}")


def section_header(title: str, subtitle: str = ""):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


# ── Charts ────────────────────────────────────────────────────────────────────

def score_trend_chart(rounds: pd.DataFrame, key: str = "score_trend"):
    """Line chart of round scores with optional rolling average overlay."""
    if rounds.empty or "total_score" not in rounds.columns:
        no_data_notice("Upload at least 3 rounds to see your score trend.")
        return

    fig = go.Figure()

    # Round scores
    def _round_label(r):
        date_str = r['date'].strftime('%b %d') if pd.notna(r.get('date')) else "Round " + str(r.get('round_id', ''))
        return date_str + " — " + str(r.get('course', ''))

    x_labels = rounds.apply(_round_label, axis=1)

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=rounds["total_score"],
        mode="lines+markers",
        name="Round Score",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=7),
        hovertemplate="<b>%{x}</b><br>Score: %{y}<extra></extra>",
    ))

    # Rolling average
    if "rolling_avg_score" in rounds.columns:
        valid = rounds["rolling_avg_score"].notna()
        if valid.any():
            fig.add_trace(go.Scatter(
                x=x_labels[valid],
                y=rounds.loc[valid, "rolling_avg_score"],
                mode="lines",
                name="5-Round Average",
                line=dict(color="#f59e0b", width=2, dash="dot"),
                hovertemplate="5-round avg: %{y:.1f}<extra></extra>",
            ))

    fig.update_layout(
        title="Score Over Time",
        xaxis_title="",
        yaxis_title="Total Score",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True, key=key)


def hole_type_bar_chart(hole_metrics: dict):
    """Bar chart of average score vs par for par 3, 4, 5 holes."""
    data = []
    for par_val in [3, 4, 5]:
        val = hole_metrics.get(f"par{par_val}_avg_vs_par")
        count = hole_metrics.get(f"par{par_val}_hole_count", 0)
        if val is not None and count > 0:
            data.append({"Hole Type": f"Par {par_val}", "Avg vs Par": val, "Holes Played": count})

    if not data:
        no_data_notice("Not enough hole data to break down by par type.")
        return

    df = pd.DataFrame(data)
    fig = px.bar(
        df,
        x="Hole Type",
        y="Avg vs Par",
        color="Avg vs Par",
        color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
        range_color=[-0.5, 3],
        text=df["Avg vs Par"].apply(lambda v: f"+{v:.2f}" if v >= 0 else f"{v:.2f}"),
        title="Average Score vs Par — by Hole Type",
        labels={"Avg vs Par": "Avg strokes over/under par"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(zeroline=True, zerolinecolor="#6b7280", zerolinewidth=1.5),
    )
    st.plotly_chart(fig, use_container_width=True)


def front_back_chart(fb: dict):
    """Horizontal bar chart comparing front vs back nine."""
    if not fb or "front_nine_avg_vs_par" not in fb:
        no_data_notice("Not enough data to compare front and back nine.")
        return

    fig = go.Figure(go.Bar(
        x=[fb["front_nine_avg_vs_par"], fb["back_nine_avg_vs_par"]],
        y=["Front Nine (1–9)", "Back Nine (10–18)"],
        orientation="h",
        marker_color=["#2563eb", "#7c3aed"],
        text=[f"+{fb['front_nine_avg_vs_par']:.2f}", f"+{fb['back_nine_avg_vs_par']:.2f}"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Front vs Back Nine — Avg Score vs Par per Hole",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(zeroline=True, zerolinecolor="#6b7280"),
        margin=dict(l=0, r=60, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Recommendations ───────────────────────────────────────────────────────────

PRIORITY_COLORS = {"high": "#ef4444", "medium": "#f59e0b", "low": "#3b82f6"}
PRIORITY_LABELS = {"high": "High Priority", "medium": "Medium Priority", "low": "Low Priority"}


def recommendation_card(rec: dict):
    priority = rec.get("priority", "medium")
    color = PRIORITY_COLORS.get(priority, "#6b7280")
    badge = PRIORITY_LABELS.get(priority, "")

    st.markdown(
        f"""
<div style="border-left: 4px solid {color}; padding: 12px 16px; background: #f9fafb;
            border-radius: 0 8px 8px 0; margin-bottom: 12px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <strong style="font-size:1rem;">{rec['issue']}</strong>
    <span style="background:{color}; color:white; padding:2px 8px;
                 border-radius:12px; font-size:0.75rem;">{badge}</span>
  </div>
  <p style="margin:6px 0 4px; color:#374151;">{rec['headline']}</p>
  <p style="margin:0; font-size:0.875rem; color:#6b7280;">📊 {rec['supporting_data']}</p>
  <hr style="border:none; border-top:1px solid #e5e7eb; margin:8px 0;">
  <p style="margin:0 0 4px; font-size:0.875rem;"><strong>What to do:</strong> {rec['recommendation']}</p>
  <p style="margin:0 0 4px; font-size:0.875rem;"><strong>Practice focus:</strong> {rec['practice_focus']}</p>
  <p style="margin:0; font-size:0.875rem; color:#059669;"><strong>Expected impact:</strong> {rec['expected_impact']}</p>
</div>
""",
        unsafe_allow_html=True,
    )
