"""
ui/map_view.py

Interactive map of golf courses played.
Geocodes course names via OpenStreetMap Nominatim (free, no API key).
Results are cached in session state to avoid repeated lookups.
"""

import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


GEOCODER = Nominatim(user_agent="golf_performance_app_v1")


def _geocode_course(name: str) -> tuple:
    """
    Try to find lat/lon for a golf course name.
    Appends 'golf course' to improve Nominatim accuracy.
    Returns (lat, lon) or (None, None) if not found.
    """
    queries = [
        f"{name} golf course",
        f"{name} golf club",
        name,
    ]
    for query in queries:
        try:
            location = GEOCODER.geocode(query, timeout=5)
            if location:
                return (location.latitude, location.longitude)
            time.sleep(1.1)  # Nominatim rate limit: 1 req/sec
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(1.1)
    return (None, None)


def build_course_map_data(rounds: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate rounds by course, geocode each unique course,
    and return a DataFrame ready for plotting.
    """
    if rounds.empty or "course" not in rounds.columns:
        return pd.DataFrame()

    # Cache geocoding results across reruns
    if "geocode_cache" not in st.session_state:
        st.session_state.geocode_cache = {}

    cache = st.session_state.geocode_cache
    unique_courses = rounds["course"].dropna().unique()

    # Geocode only courses not yet in cache
    new_courses = [c for c in unique_courses if c not in cache]
    if new_courses:
        progress = st.progress(0, text="Finding course locations on the map...")
        for i, course in enumerate(new_courses):
            cache[course] = _geocode_course(course)
            progress.progress((i + 1) / len(new_courses), text=f"Locating: {course}")
            time.sleep(0.1)
        progress.empty()

    # Build one row per course
    rows = []
    for course, group in rounds.groupby("course"):
        lat, lon = cache.get(course, (None, None))

        dates = sorted(group["date"].dropna().dt.strftime("%b %d, %Y").tolist())
        scores = group["total_score"].dropna().astype(int).tolist()
        vs_par = group["score_vs_par"].dropna().astype(int).tolist()

        score_lines = [
            f"{d}: {s} ({'+' if v >= 0 else ''}{v})"
            for d, s, v in zip(dates, scores, vs_par)
        ]

        rows.append({
            "course": course,
            "lat": lat,
            "lon": lon,
            "rounds_played": len(group),
            "best_score": int(group["total_score"].min()) if "total_score" in group else None,
            "avg_score": round(group["total_score"].mean(), 1) if "total_score" in group else None,
            "dates_played": ", ".join(dates),
            "score_detail": "<br>".join(score_lines),
            "found": lat is not None,
        })

    return pd.DataFrame(rows)


def render_course_map(rounds: pd.DataFrame):
    """Main entry point — renders the full course map section."""
    from src.ui.components import no_data_notice

    if rounds.empty or "course" not in rounds.columns:
        no_data_notice("No course data available.")
        return

    with st.spinner("Loading map..."):
        df = build_course_map_data(rounds)

    if df.empty:
        no_data_notice("Could not build map data.")
        return

    located = df[df["found"]].copy()
    not_found = df[~df["found"]]["course"].tolist()

    if located.empty:
        st.warning(
            "Could not find map locations for any of your courses. "
            "This can happen with private clubs or unusual course names."
        )
    else:
        # Build hover text
        located["hover"] = located.apply(
            lambda r: (
                f"<b>{r['course']}</b><br>"
                f"Rounds played: {r['rounds_played']}<br>"
                f"Best score: {r['best_score']}<br>"
                f"Avg score: {r['avg_score']}<br>"
                f"<br><b>Rounds:</b><br>{r['score_detail']}"
            ),
            axis=1,
        )

        fig = go.Figure()

        fig.add_trace(go.Scattermap(
            lat=located["lat"],
            lon=located["lon"],
            mode="markers+text",
            marker=dict(
                size=located["rounds_played"].clip(upper=10) * 5 + 10,
                color="#2563eb",
                opacity=0.85,
            ),
            text=located["course"],
            textposition="top center",
            textfont=dict(size=11, color="#1e3a5f"),
            hovertemplate=located["hover"] + "<extra></extra>",
            name="",
        ))

        # Centre map on the mean of all points
        centre_lat = located["lat"].mean()
        centre_lon = located["lon"].mean()

        fig.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=centre_lat, lon=centre_lon),
                zoom=5,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=520,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True, key="course_map")

        # Legend: marker size explanation
        st.caption("Marker size reflects number of rounds played at each course.")

    # Show table of all courses
    st.divider()
    st.markdown("#### All Courses")

    display = df[["course", "rounds_played", "avg_score", "best_score", "dates_played"]].copy()
    display.columns = ["Course", "Rounds", "Avg Score", "Best Score", "Dates Played"]
    display = display.sort_values("Rounds", ascending=False).reset_index(drop=True)
    st.dataframe(display, use_container_width=True, hide_index=True)

    if not_found:
        st.caption(
            f"Could not locate on map: {', '.join(not_found)}. "
            "Private clubs or abbreviated names may not appear in OpenStreetMap."
        )
