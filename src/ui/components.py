"""
ui/components.py

Reusable Streamlit UI building blocks.
Color palette is high-contrast and consistent across all charts.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Color palette ─────────────────────────────────────────────────────────────
C_BLUE   = "#1d4ed8"   # Primary (round scores, main line)
C_AMBER  = "#b45309"   # Rolling average / secondary line
C_GREEN  = "#059669"   # Positive / strength
C_RED    = "#dc2626"   # Negative / weakness
C_PURPLE = "#6d28d9"   # Back nine / tertiary
C_SLATE  = "#1e293b"   # Dark text / axis labels
C_GRAY   = "#64748b"   # Captions
C_BG     = "#f8fafc"   # Card background


# ── Basic helpers ─────────────────────────────────────────────────────────────

def metric_card(label: str, value, suffix: str = "", delta=None,
                delta_label: str = "", help_text: str = ""):
    if value is None:
        st.metric(label=label, value="No data",
                  help=help_text or "Not enough data in your file for this metric.")
    else:
        st.metric(
            label=label,
            value=f"{value}{suffix}",
            delta=f"{delta:+.1f} {delta_label}" if delta is not None else None,
            delta_color="inverse",
            help=help_text,
        )


def no_data_notice(message: str = "Not enough data available for this section."):
    st.info(f"ℹ️ {message}")


def section_header(title: str, subtitle: str = ""):
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


# ── Coaching summary card (Overview tab top section) ─────────────────────────

def coaching_summary_card(segment: dict, profile_label: str, area_perf: list,
                           trend_5v5: dict, metrics: dict):
    """
    Full-width coaching overview showing player level, profile label,
    biggest weakness, biggest strength, and form trend.
    """
    level      = segment.get("level", "")
    emoji      = segment.get("emoji", "🏌️")
    color      = segment.get("color", C_BLUE)
    avg_score  = metrics.get("avg_score")
    n_rounds   = metrics.get("rounds_played", 0)

    # Biggest strength / weakness from area_perf (sorted best → worst)
    strength = next((a for a in area_perf if a["strokes_gained"] > 0), None)
    weakness = next((a for a in reversed(area_perf) if a["strokes_gained"] < 0), None)

    # Trend label from last5 vs prev5
    direction = trend_5v5.get("score_direction", "")
    score_cmp = trend_5v5.get("score", {})
    trend_label = {"improving": "Improving", "declining": "Declining", "stable": "Stable"}.get(direction, "—")
    trend_color = {"improving": C_GREEN, "declining": C_RED, "stable": C_GRAY}.get(direction, C_GRAY)
    trend_arrow = {"improving": "↓", "declining": "↑", "stable": "→"}.get(direction, "")

    # Header band
    st.markdown(
        f"""
<div style="background:{color}15; border:1.5px solid {color}40;
            border-radius:12px; padding:20px 24px 16px; margin-bottom:16px;">
  <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
    <span style="background:{color}; color:white; font-size:0.85rem; font-weight:700;
                 padding:4px 14px; border-radius:20px; letter-spacing:0.05em;">
      {emoji} {level.upper()}
    </span>
    <span style="font-size:1.05rem; font-weight:600; color:{C_SLATE};">
      Avg {avg_score} · {n_rounds} rounds
    </span>
  </div>
  <p style="margin:10px 0 0; font-size:0.95rem; color:{C_SLATE}; font-style:italic;">
    "{profile_label}"
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # Three-column summary
    c1, c2, c3 = st.columns(3)

    with c1:
        if weakness:
            saved = abs(weakness["strokes_gained"])
            st.markdown(
                f"""
<div style="background:#fef2f2; border:1.5px solid #fca5a5;
            border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_RED};
              text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">
    ⚠️ Fix This First
  </div>
  <div style="font-size:1.05rem; font-weight:700; color:{C_SLATE};">
    {weakness['area']}
  </div>
  <div style="font-size:0.85rem; color:{C_RED}; margin-top:4px;">
    −{saved:.1f} strokes vs benchmark
  </div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style="background:{C_BG}; border:1.5px solid #e2e8f0;
                    border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_GRAY};
              text-transform:uppercase; letter-spacing:0.06em;">⚠️ Fix This First</div>
  <div style="font-size:0.95rem; color:{C_GRAY}; margin-top:4px;">No clear weakness</div>
</div>""",
                unsafe_allow_html=True,
            )

    with c2:
        if strength:
            gained = strength["strokes_gained"]
            st.markdown(
                f"""
<div style="background:#f0fdf4; border:1.5px solid #86efac;
            border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_GREEN};
              text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">
    💪 Biggest Strength
  </div>
  <div style="font-size:1.05rem; font-weight:700; color:{C_SLATE};">
    {strength['area']}
  </div>
  <div style="font-size:0.85rem; color:{C_GREEN}; margin-top:4px;">
    +{gained:.1f} strokes vs benchmark
  </div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style="background:{C_BG}; border:1.5px solid #e2e8f0;
                    border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_GRAY};
              text-transform:uppercase; letter-spacing:0.06em;">💪 Biggest Strength</div>
  <div style="font-size:0.95rem; color:{C_GRAY}; margin-top:4px;">Meets benchmark</div>
</div>""",
                unsafe_allow_html=True,
            )

    with c3:
        if score_cmp and direction:
            delta_val = score_cmp.get("delta", 0)
            st.markdown(
                f"""
<div style="background:{C_BG}; border:1.5px solid #e2e8f0;
            border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_GRAY};
              text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">
    📈 Recent Form
  </div>
  <div style="font-size:1.05rem; font-weight:700; color:{trend_color};">
    {trend_arrow} {trend_label}
  </div>
  <div style="font-size:0.85rem; color:{C_GRAY}; margin-top:4px;">
    Last 5 avg: {score_cmp.get('last5', '—')}
    ({'+' if delta_val >= 0 else ''}{delta_val:.1f} vs prev 5)
  </div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style="background:{C_BG}; border:1.5px solid #e2e8f0;
                    border-radius:10px; padding:14px 16px;">
  <div style="font-size:0.75rem; font-weight:700; color:{C_GRAY};
              text-transform:uppercase; letter-spacing:0.06em;">📈 Recent Form</div>
  <div style="font-size:0.95rem; color:{C_GRAY}; margin-top:4px;">
    Upload 6+ rounds to see trend
  </div>
</div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


# ── Strokes-lost chart ────────────────────────────────────────────────────────

def strokes_lost_chart(strokes_lost: list, segment: dict):
    """Horizontal bar chart of estimated strokes lost per area vs target level."""
    if not strokes_lost:
        no_data_notice("Not enough data to calculate strokes lost.")
        return

    areas   = [s["area"] for s in strokes_lost]
    values  = [s["strokes_lost"] for s in strokes_lost]
    yours   = [s["your_value"] for s in strokes_lost]
    targets = [s["target_value"] for s in strokes_lost]

    max_val = max(values) if values else 1
    colors  = [
        C_RED if v >= max_val * 0.66
        else "#f97316" if v >= max_val * 0.33
        else "#fbbf24"
        for v in values
    ]

    hover = [
        f"<b>{a}</b><br>Strokes lost: {v:.2f}<br>Your stat: {y}<br>Target: {tg}"
        for a, v, y, tg in zip(areas, values, yours, targets)
    ]

    fig = go.Figure(go.Bar(
        x=values,
        y=areas,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color=C_SLATE),
        hovertemplate=hover,
        hoverinfo="text",
        name="",
    ))

    target_label = segment.get("target_label", "next level")
    fig.update_layout(
        title=dict(
            text=f"Estimated Strokes Lost vs {target_label} Target — per Round",
            font=dict(size=15, color=C_SLATE),
        ),
        xaxis=dict(
            title="Strokes lost per round",
            title_font=dict(size=13, color=C_SLATE),
            tickfont=dict(size=12, color=C_SLATE),
            zeroline=True,
            zerolinecolor=C_SLATE,
            zerolinewidth=1.5,
            gridcolor="#e2e8f0",
        ),
        yaxis=dict(
            tickfont=dict(size=13, color=C_SLATE),
            automargin=True,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=60, t=50, b=10),
        height=260,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="strokes_lost_chart")


# ── Score trend chart ─────────────────────────────────────────────────────────

def score_trend_chart(rounds: pd.DataFrame, key: str = "score_trend"):
    if rounds.empty or "total_score" not in rounds.columns:
        no_data_notice("Upload at least 3 rounds to see your score trend.")
        return

    def _label(r):
        date_str = r["date"].strftime("%b %d") if pd.notna(r.get("date")) else "Round " + str(r.get("round_id", ""))
        return date_str + " — " + str(r.get("course", ""))

    x = rounds.apply(_label, axis=1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=rounds["total_score"],
        mode="lines+markers",
        name="Round Score",
        line=dict(color=C_BLUE, width=3),
        marker=dict(size=9, color=C_BLUE, line=dict(color="white", width=2)),
        hovertemplate="<b>%{x}</b><br>Score: %{y}<extra></extra>",
    ))

    if "rolling_avg_score" in rounds.columns:
        valid = rounds["rolling_avg_score"].notna()
        if valid.any():
            fig.add_trace(go.Scatter(
                x=x[valid],
                y=rounds.loc[valid, "rolling_avg_score"],
                mode="lines",
                name="5-Round Avg",
                line=dict(color=C_AMBER, width=2.5, dash="dot"),
                hovertemplate="5-round avg: %{y:.1f}<extra></extra>",
            ))

    fig.update_layout(
        title=dict(text="Score Over Time", font=dict(size=15, color=C_SLATE)),
        xaxis=dict(
            tickangle=-30,
            tickfont=dict(size=11, color=C_SLATE),
            gridcolor="#e2e8f0",
        ),
        yaxis=dict(
            title="Total Score",
            title_font=dict(size=13, color=C_SLATE),
            tickfont=dict(size=12, color=C_SLATE),
            gridcolor="#e2e8f0",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=12, color=C_SLATE),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── Last-5 vs prev-5 trend chart ─────────────────────────────────────────────

def trend_comparison_chart(trend_5v5: dict):
    """Bar chart comparing last 5 rounds vs previous 5 across key metrics."""
    if not trend_5v5:
        no_data_notice("Upload at least 6 rounds to compare recent vs previous form.")
        return

    rows = []
    labels = {
        "score":   ("Avg Score", True),   # lower is better
        "putts":   ("Putts/Round", True),
        "gir":     ("GIR %", False),       # higher is better
        "fairway": ("Fairway %", False),
    }

    for key, (label, lower_better) in labels.items():
        cmp = trend_5v5.get(key)
        if cmp:
            rows.append({
                "Metric": label,
                "Last 5": cmp["last5"],
                "Previous 5": cmp["prev"],
                "lower_better": lower_better,
            })

    if not rows:
        no_data_notice("Not enough metric data for comparison.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Last 5 Rounds",
        x=[r["Metric"] for r in rows],
        y=[r["Last 5"] for r in rows],
        marker_color=C_BLUE,
        text=[str(r["Last 5"]) for r in rows],
        textposition="outside",
        textfont=dict(size=12, color=C_SLATE),
    ))
    fig.add_trace(go.Bar(
        name="Previous 5 Rounds",
        x=[r["Metric"] for r in rows],
        y=[r["Previous 5"] for r in rows],
        marker_color=C_GRAY,
        text=[str(r["Previous 5"]) for r in rows],
        textposition="outside",
        textfont=dict(size=12, color=C_SLATE),
    ))
    fig.update_layout(
        barmode="group",
        title=dict(text="Last 5 Rounds vs Previous 5 Rounds", font=dict(size=15, color=C_SLATE)),
        xaxis=dict(tickfont=dict(size=13, color=C_SLATE)),
        yaxis=dict(tickfont=dict(size=12, color=C_SLATE), gridcolor="#e2e8f0"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(font=dict(size=12, color=C_SLATE)),
        margin=dict(l=0, r=0, t=50, b=0),
    )
    st.plotly_chart(fig, use_container_width=True, key="trend_5v5_chart")


# ── Hole type bar chart ───────────────────────────────────────────────────────

def hole_type_bar_chart(hole_metrics: dict):
    data = []
    for par_val in [3, 4, 5]:
        val   = hole_metrics.get(f"par{par_val}_avg_vs_par")
        count = hole_metrics.get(f"par{par_val}_hole_count", 0)
        if val is not None and count > 0:
            data.append({"Hole Type": f"Par {par_val}", "Avg vs Par": val})

    if not data:
        no_data_notice("Not enough hole data to break down by par type.")
        return

    df = pd.DataFrame(data)
    bar_colors = [
        C_RED if v > 1.5 else "#f97316" if v > 0.8 else C_GREEN
        for v in df["Avg vs Par"]
    ]

    fig = go.Figure(go.Bar(
        x=df["Hole Type"],
        y=df["Avg vs Par"],
        marker_color=bar_colors,
        text=[f"+{v:.2f}" if v >= 0 else f"{v:.2f}" for v in df["Avg vs Par"]],
        textposition="outside",
        textfont=dict(size=14, color=C_SLATE),
    ))
    fig.update_layout(
        title=dict(text="Avg Score vs Par — by Hole Type", font=dict(size=15, color=C_SLATE)),
        xaxis=dict(tickfont=dict(size=14, color=C_SLATE)),
        yaxis=dict(
            title="Avg strokes over/under par",
            title_font=dict(size=13, color=C_SLATE),
            tickfont=dict(size=12, color=C_SLATE),
            zeroline=True,
            zerolinecolor=C_SLATE,
            zerolinewidth=1.5,
            gridcolor="#e2e8f0",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    st.plotly_chart(fig, use_container_width=True, key="hole_type_chart")


# ── Front / back nine chart ───────────────────────────────────────────────────

def front_back_chart(fb: dict):
    if not fb or "front_nine_avg_vs_par" not in fb:
        no_data_notice("Not enough data to compare front and back nine.")
        return

    vals = [fb["front_nine_avg_vs_par"], fb["back_nine_avg_vs_par"]]
    colors = [C_BLUE, C_PURPLE]

    fig = go.Figure(go.Bar(
        x=vals,
        y=["Front Nine (1–9)", "Back Nine (10–18)"],
        orientation="h",
        marker_color=colors,
        text=[f"+{v:.2f}" if v >= 0 else f"{v:.2f}" for v in vals],
        textposition="outside",
        textfont=dict(size=13, color=C_SLATE),
    ))
    fig.update_layout(
        title=dict(text="Front vs Back Nine — Avg Score vs Par per Hole",
                   font=dict(size=15, color=C_SLATE)),
        xaxis=dict(
            zeroline=True, zerolinecolor=C_SLATE, zerolinewidth=1.5,
            gridcolor="#e2e8f0",
            tickfont=dict(size=12, color=C_SLATE),
        ),
        yaxis=dict(tickfont=dict(size=13, color=C_SLATE)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=70, t=50, b=0),
    )
    st.plotly_chart(fig, use_container_width=True, key="front_back_chart")


# ── Recommendation card ───────────────────────────────────────────────────────

PRIORITY_COLORS = {"high": C_RED, "medium": "#f97316", "low": C_BLUE}
PRIORITY_LABELS = {"high": "High Impact", "medium": "Medium Impact", "low": "Lower Impact"}


def recommendation_card(rec: dict, rank: int = 0):
    priority = rec.get("priority", "medium")
    color    = PRIORITY_COLORS.get(priority, C_GRAY)
    badge    = PRIORITY_LABELS.get(priority, "")
    impact   = rec.get("stroke_impact")
    drills   = rec.get("drills", [])

    impact_str = f"Est. −{impact:.1f} strokes/round" if impact else rec.get("expected_impact", "")
    rank_str   = f"#{rank} " if rank else ""

    # Main card
    st.markdown(
        f"""
<div style="border-left:5px solid {color}; padding:14px 18px 10px;
            background:{C_BG}; border-radius:0 10px 10px 0; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
    <strong style="font-size:1.05rem; color:{C_SLATE};">{rank_str}{rec['issue']}</strong>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <span style="background:{color}; color:white; padding:3px 10px;
                   border-radius:12px; font-size:0.75rem; font-weight:600;">{badge}</span>
      <span style="background:#ecfdf5; color:{C_GREEN}; padding:3px 10px;
                   border-radius:12px; font-size:0.75rem; font-weight:600;
                   border:1px solid #6ee7b7;">{impact_str}</span>
    </div>
  </div>
  <p style="margin:8px 0 4px; color:{C_SLATE}; font-size:0.95rem;">{rec['headline']}</p>
  <p style="margin:0; font-size:0.85rem; color:{C_GRAY};">📊 {rec['supporting_data']}</p>
  <hr style="border:none; border-top:1px solid #e2e8f0; margin:10px 0;">
  <p style="margin:0 0 4px; font-size:0.875rem; color:{C_SLATE};">
    <strong>What to do:</strong> {rec['recommendation']}
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # Drills as expandable section
    if drills:
        with st.expander(f"🏋️ Practice drills for this area ({len(drills)} drill{'s' if len(drills) > 1 else ''})"):
            for drill in drills:
                st.markdown(
                    f"""
<div style="background:white; border:1px solid #e2e8f0; border-radius:8px;
            padding:12px 16px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
    <strong style="color:{C_SLATE};">{drill['name']}</strong>
    <span style="font-size:0.8rem; color:{C_GRAY}; background:#f1f5f9;
                 padding:2px 8px; border-radius:10px;">{drill['reps']}</span>
  </div>
  <p style="margin:6px 0 0; font-size:0.875rem; color:{C_GRAY};">{drill['description']}</p>
</div>""",
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)
