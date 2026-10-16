"""
NYC contractor lead dashboard (Role E) (what we got from all this data in a clean dashboard!!)
what it does: reads the processed tables from the API's GET endpoints
"""
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("API_SERVICE_URL", "http://localhost:8000").rstrip("/")
BLUE, ORANGE = "#2a78d6", "#eb6834"
SIZE_ORDER = ["Small", "Mid", "Large", "Very large"]

st.set_page_config(page_title="NYC Contractor Leads", layout="wide")


@st.cache_data(ttl=600)
def load(table):
    """Fetch one processed table from the API. Cached for 10 minutes so new data shows up."""
    resp = requests.get(f"{API_URL}/data/{table}", timeout=120)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["data"])

try:
    contractors = load("contractors")
    by_trade = load("by_trade")
    by_trade_size = load("by_trade_size")
    monthly = load("monthly")
    by_borough = load("by_borough")
except requests.RequestException as e:
    st.error(f"Could not load data from the API at {API_URL}: {e}")
    st.stop()

# since dates arrive as text in the JSON, we will convert them back
for col in ["first_permit", "last_permit"]:
    contractors[col] = pd.to_datetime(contractors[col])
monthly["month"] = pd.to_datetime(monthly["month"])

st.title("NYC Contractor Leads")
st.caption(f"Permits issued {contractors['first_permit'].min():%b %Y} to "
    f"{contractors['last_permit'].max():%b %d, %Y}. NYC DOB permits joined to the DOB license registry.")

# filters for the sidebar
st.sidebar.header("Filter leads")
current_only = st.sidebar.checkbox("Current leads only", value=True, help="Active license and a permit in the last 6 months")
sizes = st.sidebar.multiselect("Company size", SIZE_ORDER, default=SIZE_ORDER)
trades = st.sidebar.multiselect("Main work type", sorted(contractors["main_work_type"].dropna().unique()))
search = st.sidebar.text_input("Search business name")

leads = contractors[contractors["size_tier"].isin(sizes)]
if current_only:
    leads = leads[leads["is_current_lead"]]
if trades:
    leads = leads[leads["main_work_type"].isin(trades)]
if search:
    leads = leads[leads["business_name"].fillna("").str.contains(search, case=False)]
leads = leads.sort_values("lead_score", ascending=False)

# list for the leads...
st.header("Ranked lead list")
# giving a one line summary about how we got the lead score
st.caption("Lead score = 100 × (50% frequency percentile + 50% median job value percentile) × size factor "
           "(Small/Mid 1.0, Large 0.7, Very large 0.4). Higher the score, better the lead.")
c1, c2, c3 = st.columns(3)
c1.metric("Leads shown", f"{len(leads):,}")
c2.metric("Median score", f"{leads['lead_score'].median():.1f}" if len(leads) else "-")
c3.metric("Have an email", f"{leads['business_email'].notna().mean():.0%}" if len(leads) else "-")

columns = ["lead_score", "business_name", "license_type", "size_tier", "main_work_type",
           "permits_per_month", "median_job_cost", "last_permit", "business_email", "business_phone"]
st.dataframe(
    leads[columns],
    hide_index=True,
    use_container_width=True,
    column_config={
        "lead_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        "business_name": "Business",
        "license_type": "License",
        "size_tier": "Size",
        "main_work_type": "Main work type",
        "permits_per_month": st.column_config.NumberColumn("Permits / month", format="%.2f"),
        "median_job_cost": st.column_config.NumberColumn("Median job cost", format="dollar"),
        "last_permit": st.column_config.DateColumn("Last permit"),
        "business_email": "Email",
        "business_phone": "Phone",
    },
)
st.download_button("Download leads as CSV", leads[columns].to_csv(index=False), file_name="contractor_leads.csv")

with st.expander("How the score works"):
    st.markdown(
        "- **Frequency:** permits per month, as a percentile among all contractors (50%)\n"
        "- **Job value:** median job cost, as a percentile (50%). Contractors with no usable cost rank lowest.\n"
        "- **Size factor:** Small and Mid × 1.0, Large × 0.7, Very large × 0.4. "
        "Smaller firms are less likely to already have a payments system.\n"
        "- Score = 100 × (weighted percentiles) × size factor, from 0 to 100."
    )

# overview of the market
st.header("Market overview")
tab_trade, tab_size, tab_mix, tab_trend, tab_borough = st.tabs(
    ["By trade", "By company size", "Trade × size", "Monthly trend", "By borough"])

with tab_trade:
    left, right = st.columns(2)
    t = by_trade.sort_values("n_permits")
    left.plotly_chart(px.bar(t, x="n_permits", y="work_type", orientation="h",
                             color_discrete_sequence=[BLUE], height=600, title="Permits",
                             labels={"n_permits": "Permits", "work_type": ""}),
                      use_container_width=True)
    t = by_trade.sort_values("median_job_cost")
    right.plotly_chart(px.bar(t, x="median_job_cost", y="work_type", orientation="h",
                              color_discrete_sequence=[BLUE], height=600, title="Median job cost ($)",
                              labels={"median_job_cost": "Median job cost ($)", "work_type": ""}),
                       use_container_width=True)

with tab_size:
    s = contractors.groupby("size_tier").agg(
        contractors=("contractor_id", "size"), permits=("n_permits", "sum")).reindex(SIZE_ORDER)
    s = (s / s.sum()).reset_index()
    s = s.melt(id_vars="size_tier", var_name="share_of", value_name="share")
    fig = px.bar(s, x="size_tier", y="share", color="share_of", barmode="group",
                 color_discrete_sequence=[BLUE, ORANGE], text_auto=".0%",
                 labels={"size_tier": "Company size", "share": "Share", "share_of": "Share of"})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A small number of large contractors account for a large share of permits.")

with tab_mix:
    mix = by_trade_size.pivot_table(index="work_type", columns="size_tier", values="n_permits",
                                    aggfunc="sum").reindex(columns=SIZE_ORDER).fillna(0)
    mix = mix.div(mix.sum(axis=1), axis=0)  # share of each trade's permits by company size
    fig = px.imshow(mix, text_auto=".0%", aspect="auto", height=650,
                    color_continuous_scale=["#cde2fb", "#0d366b"],
                    labels={"x": "Company size", "y": "", "color": "Share of trade's permits"})
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Each row adds to 100%: how a trade's permits split across company sizes.")

with tab_trend:
    trade = st.selectbox("Work type", ["All"] + sorted(monthly["work_type"].dropna().unique()))
    m = monthly if trade == "All" else monthly[monthly["work_type"] == trade]
    m = m.groupby("month", as_index=False)["n_permits"].sum()
    fig = px.line(m, x="month", y="n_permits", markers=True, color_discrete_sequence=[BLUE],
                  labels={"month": "", "n_permits": "Permits"})
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The most recent month may be incomplete.")

with tab_borough:
    left, right = st.columns(2)
    b = by_borough.sort_values("n_permits", ascending=False)
    left.plotly_chart(px.bar(b, x="borough", y="n_permits", color_discrete_sequence=[BLUE],
                             title="Permits", labels={"n_permits": "Permits", "borough": ""}),
                      use_container_width=True)
    right.plotly_chart(px.bar(b, x="borough", y="median_job_cost", color_discrete_sequence=[BLUE],
                              title="Median job cost ($)",
                              labels={"median_job_cost": "Median job cost ($)", "borough": ""}),
                       use_container_width=True)