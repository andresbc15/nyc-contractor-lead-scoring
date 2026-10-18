# DASHBOARD part of the project!! (ROLE E)
# Pulling the 5 processed tables from the API's GET endpoints
# showing a ranked list for a B2B payments sales team
# market overview of NYC permit activity by trade, company size and borough

import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API_SERVICE_URL = os.getenv("API_SERVICE_URL",
                            "http://localhost:8000").rstrip("/")
TABLES = ["contractors", "by_trade", "by_trade_size", "monthly", "by_borough"]
SIZE_LABELS = ["Small", "Mid", "Large", "Very large"]


def retrieve_data_from_api(api_url: str, table: str) -> pd.DataFrame:
    """Calling the API's GET endpoint and return the table."""
    response = requests.get(f"{api_url}/data/{table}", timeout=120)
    response.raise_for_status()
    return pd.DataFrame(response.json()["data"])


@st.cache_data(ttl=600)
def load_tables(api_url: str) -> dict:
    """Loading every processed table. Cached for 10 minutes so new data from
    the scheduled pipeline shows up without restarting the app."""
    return {table: retrieve_data_from_api(api_url, table) for table in TABLES}


def prepare_contractors(contractors: pd.DataFrame) -> pd.DataFrame:
    """Converting date columns and adding a clickable email column."""
    contractors = contractors.copy()
    for col in ["first_permit", "last_permit"]:
        contractors[col] = pd.to_datetime(contractors[col])
    emails = contractors["business_email"].str.lower()
    contractors["email_link"] = "mailto:" + emails
    return contractors


def filter_leads(contractors: pd.DataFrame, current_only: bool,
                 sizes: list, trades: list, search: str,
                 website: str) -> pd.DataFrame:
    """Applying the sidebar filters and sorting by lead score."""
    leads = contractors[contractors["size_tier"].isin(sizes)]
    if current_only:
        leads = leads[leads["is_current_lead"]]
    if trades:
        leads = leads[leads["main_work_type"].isin(trades)]
    if search:
        names = leads["business_name"].fillna("")
        leads = leads[names.str.contains(search, case=False, regex=False)]
    # AI-generated (Claude, claude-opus-5-5). Prompt: "Add a sidebar filter
    # for has website / payment signal instead of a column."
    if website == "Has a website":
        leads = leads[leads["has_website"].fillna(False)]
    elif website == "Payment signal found":
        leads = leads[leads["payment_signal"].fillna(False)]
    return leads.sort_values("lead_score", ascending=False)

def show_sidebar(contractors: pd.DataFrame) -> tuple:
    """Sidebar filters."""
    with st.sidebar:
        st.header("Filter leads")
        current_only = st.toggle(
            "Current leads only", value=True,
            help="Had an active license and a permit in the last 6 months")

        st.write("Filter by Company Size")
        sizes = []
        for size in SIZE_LABELS:
            if st.checkbox(size, value=True, key=f"checkbox_{size}"):
                sizes.append(size)

        work_types = sorted(contractors["main_work_type"].dropna().unique())
        trades = st.multiselect("Main work type", work_types)
        search = st.text_input("Search business name")

        # AI-generated (Claude, claude-opus-5-5). Prompt: "Add a sidebar
        # filter for has website / payment signal instead of a column."
        website_options = ["All contractors"]
        if "has_website" in contractors.columns:
            website_options.append("Has a website")
        if "payment_signal" in contractors.columns:
            website_options.append("Payment signal found")
        website = st.radio("Website signal", website_options)
    return current_only, sizes, trades, search, website

def main():
    st.set_page_config(page_title="NYC Contractor Leads", layout="wide")
    apply_page_style()

    try:
        tables = load_tables(API_SERVICE_URL)
    except requests.RequestException as error:
        st.error(f"Couldn't load data from the API at "
                 f"{API_SERVICE_URL}: {error}")
        st.stop()

    contractors = prepare_contractors(tables["contractors"])
    show_header(contractors)
    filters = show_sidebar(contractors)
    show_lead_list(filter_leads(contractors, *filters))
    st.divider()
    show_market_overview(tables, contractors)

# NOTE on AI use: I used claude for the design of the dashboard
# and here is the prompt I used: "this is my code for
# app.py(copy pasted my code), dont change anything about the code,
# if you see a mistake in the code, notify me instead of adding changes
# and make the design of the dashboard pretty - styled metric cards,
# a leads table that's formatted and has a score bar emails you can click.
# also have good consistent charts for the market overview tabs"
# model: claude-opus-5-5


BLUE = "#2a78d6"
ORANGE = "#eb6834"
SEQUENTIAL = ["#cde2fb", "#0d366b"]

LEAD_COLUMNS = ["lead_score", "business_name", "license_type", "size_tier",
                "main_work_type", "permits_per_month", "median_job_cost",
                "last_permit", "email_link", "business_phone"]

SCORE_FORMULA = (
    "**Lead score** = 100 × (50% frequency percentile + 50% median job "
    "value percentile) × size factor (Small/Mid 1.0, Large 0.7, "
    "Very large 0.4). Higher is a better lead."
)

CSS = """
<style>
div[data-testid="stMetric"] {
    background: rgba(42, 120, 214, 0.06);
    border: 1px solid rgba(42, 120, 214, 0.25);
    border-radius: 12px;
    padding: 14px 18px;
}
div[data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
"""


def apply_page_style():
    """Card styling for the metric tiles."""
    st.markdown(CSS, unsafe_allow_html=True)


def style_figure(fig, height=420):
    """Shared chart styling: transparent background, faint grid."""
    fig.update_layout(height=height,
                      margin=dict(l=10, r=10, t=50, b=10),
                      plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      legend_title_text="")
    fig.update_xaxes(gridcolor="rgba(128,128,128,0.15)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)")
    return fig


def bar_chart(df, x, y, title, labels, horizontal=False, height=420):
    """Single-measure bar chart in one color (no legend needed)."""
    fig = px.bar(df, x=x, y=y, title=title, labels=labels,
                 orientation="h" if horizontal else "v",
                 color_discrete_sequence=[BLUE])
    fig.update_traces(marker_cornerradius=4)
    return style_figure(fig, height)


def show_header(contractors):
    """Title and the date range the data covers."""
    st.title("NYC Contractor Lead Scoring")
    start = contractors["first_permit"].min()
    end = contractors["last_permit"].max()
    st.caption(f"Ranked leads for a B2B payments platform, built from NYC "
               f"DOB permits issued {start:%b %Y} to {end:%b %d, %Y} "
               f"joined to the DOB license registry.")


def show_lead_metrics(leads):
    """Headline numbers for the filtered lead list."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Leads shown", f"{len(leads):,}")
    if leads.empty:
        for col in (col2, col3, col4):
            col.metric("-", "-")
        return
    col2.metric("Median score", f"{leads['lead_score'].median():.1f}")
    col3.metric("Median permits / month",
                f"{leads['permits_per_month'].median():.2f}")
    col4.metric("Have an email",
                f"{leads['business_email'].notna().mean():.0%}")


def show_lead_list(leads):
    """The ranked lead table, with contact details and a CSV download."""
    st.header("Ranked lead list")
    st.markdown(SCORE_FORMULA)
    show_lead_metrics(leads)

    st.dataframe(
        leads[LEAD_COLUMNS],
        hide_index=True,
        width="stretch",
        height=460,
        column_config={
            "lead_score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.1f"),
            "business_name": "Business",
            "license_type": "License",
            "size_tier": "Size",
            "main_work_type": "Main work type",
            "permits_per_month": st.column_config.NumberColumn(
                "Permits / month", format="%.2f"),
            "median_job_cost": st.column_config.NumberColumn(
                "Median job cost", format="dollar"),
            "last_permit": st.column_config.DateColumn("Last permit"),
            "email_link": st.column_config.LinkColumn(
                "Email", display_text=r"mailto:(.*)"),
            "business_phone": "Phone",
        },
    )

    export = leads[LEAD_COLUMNS + ["business_email"]].drop(
        columns="email_link")
    st.download_button("Download leads as CSV",
                       export.to_csv(index=False),
                       file_name="contractor_leads.csv",
                       mime="text/csv")

    with st.expander("How the score works"):
        st.markdown(
            "- **Frequency:** permits per month, as a percentile among "
            "all contractors (50% of the score).\n"
            "- **Job value:** median job cost, as a percentile (50%). "
            "Contractors with no usable cost rank lowest.\n"
            "- **Size factor:** Small and Mid × 1.0, Large × 0.7, "
            "Very large × 0.4. Smaller firms are less likely to "
            "already have a payments system in place.\n"
            "- **Current lead:** active license and a permit in the "
            "last 6 months."
        )


def show_by_trade(by_trade):
    """Permits and median job cost per work type."""
    labels = {"n_permits": "Permits", "work_type": "",
              "median_job_cost": "Median job cost ($)"}
    left, right = st.columns(2)
    left.plotly_chart(
        bar_chart(by_trade.sort_values("n_permits"), "n_permits",
                  "work_type", "Permits by work type", labels,
                  horizontal=True, height=620),
        width="stretch")
    right.plotly_chart(
        bar_chart(by_trade.sort_values("median_job_cost"),
                  "median_job_cost", "work_type",
                  "Median job cost by work type", labels,
                  horizontal=True, height=620),
        width="stretch")


def show_by_size(contractors):
    """Share of contractors vs share of permits in each size tier."""
    sizes = contractors.groupby("size_tier").agg(
        contractors=("contractor_id", "size"),
        permits=("n_permits", "sum")).reindex(SIZE_LABELS)
    shares = (sizes / sizes.sum()).reset_index().melt(
        id_vars="size_tier", var_name="share_of", value_name="share")
    shares["share_of"] = shares["share_of"].map(
        {"contractors": "Share of contractors",
         "permits": "Share of permits"})

    fig = px.bar(shares, x="size_tier", y="share", color="share_of",
                 barmode="group", text_auto=".0%",
                 title="A few large contractors hold most permits",
                 color_discrete_sequence=[BLUE, ORANGE],
                 labels={"size_tier": "Company size", "share": ""})
    fig.update_traces(marker_cornerradius=4)
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(style_figure(fig), width="stretch")
    st.caption("Size = permits per contractor: Small 1-5, Mid 6-39, "
               "Large 40-249, Very large 250+.")


def show_trade_mix(by_trade_size):
    """How each trade's permits split across company sizes."""
    mix = by_trade_size.pivot_table(
        index="work_type", columns="size_tier", values="n_permits",
        aggfunc="sum").reindex(columns=SIZE_LABELS).fillna(0)
    mix = mix.div(mix.sum(axis=1), axis=0)
    fig = px.imshow(mix, text_auto=".0%", aspect="auto",
                    color_continuous_scale=SEQUENTIAL,
                    title="Share of each trade's permits by company size",
                    labels={"x": "Company size", "y": "",
                            "color": "Share"})
    st.plotly_chart(style_figure(fig, height=680), width="stretch")
    st.caption("Each row adds up to 100%.")


def show_trend(monthly):
    """Permits per month, overall or for one work type."""
    work_types = ["All"] + sorted(monthly["work_type"].dropna().unique())
    trade = st.selectbox("Work type", work_types)
    data = monthly if trade == "All" else monthly[
        monthly["work_type"] == trade]
    data = data.groupby("month", as_index=False)["n_permits"].sum()
    fig = px.line(data, x="month", y="n_permits", markers=True,
                  title=f"Permits per month: {trade}",
                  color_discrete_sequence=[BLUE],
                  labels={"month": "", "n_permits": "Permits"})
    fig.update_traces(line_width=2, marker_size=8)
    st.plotly_chart(style_figure(fig), width="stretch")
    st.caption("The most recent month may be incomplete.")


def show_by_borough(by_borough):
    """Permits and median job cost per borough."""
    data = by_borough.sort_values("n_permits", ascending=False)
    labels = {"borough": "", "n_permits": "Permits",
              "median_job_cost": "Median job cost ($)"}
    left, right = st.columns(2)
    left.plotly_chart(
        bar_chart(data, "borough", "n_permits", "Permits by borough",
                  labels),
        width="stretch")
    right.plotly_chart(
        bar_chart(data, "borough", "median_job_cost",
                  "Median job cost by borough", labels),
        width="stretch")


def show_market_overview(tables, contractors):
    """Context charts below the lead list, one per tab."""
    st.header("Market overview")
    tabs = st.tabs(["By trade", "By company size", "Trade × size",
                    "Monthly trend", "By borough"])
    with tabs[0]:
        show_by_trade(tables["by_trade"])
    with tabs[1]:
        show_by_size(contractors)
    with tabs[2]:
        show_trade_mix(tables["by_trade_size"])
    with tabs[3]:
        monthly = tables["monthly"].copy()
        monthly["month"] = pd.to_datetime(monthly["month"])
        show_trend(monthly)
    with tabs[4]:
        show_by_borough(tables["by_borough"])


if __name__ == "__main__":
    main()
