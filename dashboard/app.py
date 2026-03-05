"""Program 4: Streamlit dashboard for baseball history data.
This app reads data from SQLite and shows interactive charts.
"""
import re
import sqlite3
import sys
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

# Allow imports from project root when running this file directly.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DB_PATH

COLOR_BG = "#F8F9FA"
COLOR_CHART = "#0B3D91"
COLOR_ACCENT = "#D62828"
COLOR_GRAY = "#6C757D"

@st.cache_data
def load_events() -> pd.DataFrame:
    """Load events table from SQLite."""
    with sqlite3.connect(DB_PATH) as connection:
        df = pd.read_sql_query(
            "SELECT year, event_text, source_url FROM events ORDER BY year",
            connection,
        )
    return df

def tokenize_events(series: pd.Series) -> pd.Series:
    """Create basic keyword frequency from event text."""
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "was", "are", "his", "her", "their",
        "year", "game", "team", "league", "baseball", "into", "after", "over", "than", "also", "had",
        "has", "have", "its", "who", "all", "but", "not", "out", "one", "two", "three", "first",
    }

    words = []
    for text in series.astype(str):
        for token in re.findall(r"[a-zA-Z']+", text.lower()):
            if len(token) >= 4 and token not in stop_words:
                words.append(token)

    return pd.Series(words).value_counts()


def filter_events_by_keyword(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """Filter events by keyword in event_text."""
    if not keyword.strip():
        return df.head(0)
    return df[df["event_text"].str.contains(keyword, case=False, na=False)]

def main() -> None:
    """Main dashboard flow."""
    st.set_page_config(page_title="Baseball History Dashboard", layout="wide")

    st.markdown(
        f"""
        <style>
            :root {{ --primary-color: {COLOR_ACCENT}; }}

            .stApp {{ background-color: {COLOR_BG}; }}
            .stSidebar {{ background-color: {COLOR_BG}; }}
            h1, h2, h3 {{ color: {COLOR_CHART}; }}
            .note-text {{ color: {COLOR_GRAY}; }}
            .accent-text {{ color: {COLOR_ACCENT}; font-weight: 600; }}

            /* Sidebar filter styling */
            .stSidebar h2,
            .stSidebar h3,
            .stSidebar label,
            .stSidebar p {{ color: {COLOR_CHART}; }}

            .stSlider [role="slider"] {{
                background-color: {COLOR_ACCENT} !important;
                border-color: {COLOR_ACCENT} !important;
            }}

            .stSlider [role="presentation"] {{
                accent-color: {COLOR_ACCENT};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Evolution of Baseball Through Time")
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}. Run database/import_to_sqlite.py first.")
        return
    events = load_events()
    if events.empty:
        st.warning("No events found in database.")
        return

    # Exclude the current year because it is still in progress and can skew trends.
    current_year = pd.Timestamp.now().year
    events = events[events["year"] < current_year].copy()
    if events.empty:
        st.warning("No completed years available after filtering out the current year.")
        return

    min_year = int(events["year"].min())
    max_year = int(events["year"].max())

    # Interactive filters.
    st.sidebar.header("Filters")
    year_range = st.sidebar.slider("Year range", min_year, max_year, (min_year, max_year))
    selected_year = st.sidebar.selectbox("Single year (optional)", ["All"] + list(range(min_year, max_year + 1)))
    top_words_count = st.sidebar.slider("Top keywords", 1, 10, 10)

    filtered = events[(events["year"] >= year_range[0]) & (events["year"] <= year_range[1])].copy()
    if selected_year != "All":
        filtered = filtered[filtered["year"] == int(selected_year)]

    st.subheader("Summary")
    st.markdown(
        "<div class='note-text'>This dashboard gives a quick historical view of baseball through key moments, "
        "trends, and searchable event records. You can explore how event volume changes over time, identify the "
        "most dramatic years, and scan the most frequent themes in historical text. In total, this project includes "
        "<b>2,766 events</b> across the last <b>151 years</b> of baseball history.</div>",
        unsafe_allow_html=True,
    )

    if filtered.empty:
        st.info("No data for selected filters.")
        return

    keyword = st.text_input(
        "",
        placeholder="🔎",
        label_visibility="collapsed",
        key="top_search_input",
    )
    keyword_matches = filter_events_by_keyword(filtered, keyword)
    if keyword.strip():
        st.markdown(
            f"<div class='accent-text'>Found {len(keyword_matches)} matching events.</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            keyword_matches[["year", "event_text", "source_url"]]
            .rename(columns={"year": "Year", "event_text": "Event", "source_url": "Source URL"})
            .head(10),
            column_config={
                "Year": st.column_config.NumberColumn("Year", width="small", format="%d"),
            },
            use_container_width=True,
        )

    # Visualization 1: line chart by year.
    st.subheader("1) Evolution of Baseball: Events by Year")
    by_year = filtered.groupby("year", as_index=False).size().rename(columns={"size": "events_count"})
    chart_line = (
        alt.Chart(by_year)
        .mark_line(
            color=COLOR_CHART,
            point=alt.OverlayMarkDef(color=COLOR_ACCENT, filled=True, size=55),
        )
        .encode(
            x=alt.X("year:Q", title="Year", axis=alt.Axis(format="d")),
            y=alt.Y("events_count:Q", title="Events"),
            tooltip=["year", "events_count"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_line, use_container_width=True)
    st.markdown(
        "<div class='note-text'>The number of recorded events generally rises in the modern era, "
        "likely reflecting both increased media coverage and league expansion.</div>",
        unsafe_allow_html=True,
    )
    if not by_year.empty:
        line_max = int(by_year["events_count"].max())
        line_min = int(by_year["events_count"].min())
        line_avg = float(by_year["events_count"].mean())
        st.markdown(
            f"<div class='note-text'>Events by year stats — max: <b>{line_max}</b>, "
            f"min: <b>{line_min}</b>, average: <b>{line_avg:.2f}</b>.</div>",
            unsafe_allow_html=True,
        )

    # Visualization 2: top years bar chart.
    st.subheader("2) Most Dramatic Years in Baseball History")
    top_years_count = st.radio(
        "",
        [5, 10, 15],
        horizontal=True,
        index=0,
        label_visibility="collapsed",
        key="dramatic_years_top_n",
    )
    top_years = by_year.sort_values("events_count", ascending=False).head(top_years_count)
    chart_bar = (
        alt.Chart(top_years)
        .mark_bar(color=COLOR_CHART, size=48)
        .encode(
            x=alt.X("year:O", sort="-y", title="Year", axis=alt.Axis(labelAngle=45)),
            y=alt.Y("events_count:Q", title="Events"),
            tooltip=["year", "events_count"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_bar, use_container_width=True)
    st.markdown(
        "<div class='note-text'>These years appear to represent periods of major change in baseball "
        "history: new leagues, records, controversies, and expansion moments.</div>",
        unsafe_allow_html=True,
    )
    if not top_years.empty:
        top_max = int(top_years["events_count"].max())
        top_min = int(top_years["events_count"].min())
        top_avg = float(top_years["events_count"].mean())
        st.markdown(
            f"<div class='note-text'>Top {top_years_count} years stats — max: <b>{top_max}</b>, "
            f"min: <b>{top_min}</b>, average: <b>{top_avg:.2f}</b>.</div>",
            unsafe_allow_html=True,
        )

    # Visualization 3: keyword frequency from event text.
    st.subheader("3) Top Keywords in Event Text")
    keywords = tokenize_events(filtered["event_text"]).head(top_words_count).reset_index()
    keywords.columns = ["keyword", "count"]
    chart_words = (
        alt.Chart(keywords)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("keyword:N", sort="-x", title="Keyword"),
            color=alt.Color(
                "count:Q",
                scale=alt.Scale(range=["#BFD3F2", COLOR_CHART]),
                legend=None,
            ),
            tooltip=["keyword", "count"],
        )
        .properties(height=350)
    )
    st.altair_chart(chart_words, use_container_width=True)
    st.markdown(
        "<div class='note-text'>This chart shows which words appear most often in the selected event "
        "texts. Darker bars represent higher frequency.</div>",
        unsafe_allow_html=True,
    )

    if not keywords.empty:
        max_count = int(keywords["count"].max())
        min_count = int(keywords["count"].min())
        avg_count = float(keywords["count"].mean())
        st.markdown(
            f"<div class='note-text'>Top keywords stats — max: <b>{max_count}</b>, "
            f"min: <b>{min_count}</b>, average: <b>{avg_count:.2f}</b>.</div>",
            unsafe_allow_html=True,
        )

    st.subheader("Records and Milestones")
    records_df = filtered[
        filtered["event_text"].str.contains("record|milestone|career", case=False, na=False)
    ]
    st.markdown(
        f"<div class='accent-text'>Record/milestone events: {len(records_df)}</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        records_df[["year", "event_text", "source_url"]]
        .rename(columns={"year": "Year", "event_text": "Event", "source_url": "Source URL"})
        .head(5),
        use_container_width=True,
    )

    st.subheader("Sample Events")
    st.dataframe(
        filtered[["year", "event_text", "source_url"]]
        .rename(columns={"year": "Year", "event_text": "Event", "source_url": "Source URL"})
        .head(5),
        use_container_width=True,
    )

if __name__ == "__main__":
    main()
