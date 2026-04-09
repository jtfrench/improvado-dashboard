import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Cross-Channel Ad Performance Dashboard", layout="wide")
st.title("Cross-Channel Ad Performance Dashboard")


@st.cache_data
def load_data():
    # Load each platform's raw CSV
    fb = pd.read_csv("01_facebook_ads.csv")
    goog = pd.read_csv("02_google_ads.csv")
    tt = pd.read_csv("03_tiktok_ads.csv")

    # Normalise column names to uppercase to match unified schema
    fb.columns = fb.columns.str.upper()
    goog.columns = goog.columns.str.upper()
    tt.columns = tt.columns.str.upper()

    # ── Facebook ──────────────────────────────────────────────
    fb = fb.rename(columns={"AD_SET_ID": "AD_GROUP_ID", "AD_SET_NAME": "AD_GROUP_NAME"})
    fb["SOURCE_PLATFORM"] = "Facebook"
    fb["SPEND"] = fb["SPEND"]  # already named SPEND

    # ── Google Ads ────────────────────────────────────────────
    goog = goog.rename(columns={"COST": "SPEND"})
    goog["SOURCE_PLATFORM"] = "Google Ads"

    # ── TikTok ────────────────────────────────────────────────
    tt = tt.rename(columns={
        "ADGROUP_ID": "AD_GROUP_ID",
        "ADGROUP_NAME": "AD_GROUP_NAME",
        "COST": "SPEND",
    })
    tt["SOURCE_PLATFORM"] = "TikTok"

    # ── Common columns for unified view ───────────────────────
    common = ["DATE", "SOURCE_PLATFORM", "CAMPAIGN_ID", "CAMPAIGN_NAME",
              "AD_GROUP_ID", "AD_GROUP_NAME", "IMPRESSIONS", "CLICKS",
              "SPEND", "CONVERSIONS"]

    unified = pd.concat(
        [fb[common], goog[common], tt[common]],
        ignore_index=True
    )

    unified["DATE"] = pd.to_datetime(unified["DATE"])
    for c in ["IMPRESSIONS", "CLICKS", "SPEND", "CONVERSIONS"]:
        unified[c] = pd.to_numeric(unified[c], errors="coerce").fillna(0)

    return unified


df = load_data()

PLATFORM_COLORS = {"Facebook": "#1877F2", "Google Ads": "#34A853", "TikTok": "#010101"}

# ── Sidebar Filters ──────────────────────────────────────────
st.sidebar.header("Filters")
min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
date_range = st.sidebar.slider(
    "Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date)
)

platforms = sorted(df["SOURCE_PLATFORM"].unique())
selected_platforms = st.sidebar.multiselect("Platform", platforms, default=platforms)

available_campaigns = sorted(
    df[df["SOURCE_PLATFORM"].isin(selected_platforms)]["CAMPAIGN_NAME"].unique()
)
selected_campaigns = st.sidebar.multiselect(
    "Campaign", available_campaigns, default=available_campaigns
)

filtered = df[
    (df["DATE"].dt.date >= date_range[0])
    & (df["DATE"].dt.date <= date_range[1])
    & (df["SOURCE_PLATFORM"].isin(selected_platforms))
    & (df["CAMPAIGN_NAME"].isin(selected_campaigns))
]

# ── KPI Cards ────────────────────────────────────────────────
total_spend = filtered["SPEND"].sum()
total_impressions = filtered["IMPRESSIONS"].sum()
total_clicks = filtered["CLICKS"].sum()
total_conversions = filtered["CONVERSIONS"].sum()
blended_ctr = total_clicks / total_impressions if total_impressions else 0
blended_cpc = total_spend / total_clicks if total_clicks else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Spend", f"${total_spend:,.2f}")
k2.metric("Total Impressions", f"{total_impressions:,.0f}")
k3.metric("Total Clicks", f"{total_clicks:,.0f}")
k4.metric("Total Conversions", f"{total_conversions:,.0f}")
k5.metric("Blended CTR", f"{blended_ctr:.2%}")
k6.metric("Blended CPC", f"${blended_cpc:,.2f}")

st.divider()

# ── Spend & Conversions by Platform ──────────────────────────
platform_agg = filtered.groupby("SOURCE_PLATFORM", as_index=False).agg(
    total_spend=("SPEND", "sum"), total_conversions=("CONVERSIONS", "sum")
)
color_scale = alt.Scale(
    domain=list(PLATFORM_COLORS.keys()), range=list(PLATFORM_COLORS.values())
)

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Spend by Platform")
    st.altair_chart(
        alt.Chart(platform_agg)
        .mark_bar()
        .encode(
            y=alt.Y("SOURCE_PLATFORM:N", title=None, sort="-x"),
            x=alt.X("total_spend:Q", title="Total Spend ($)"),
            color=alt.Color("SOURCE_PLATFORM:N", scale=color_scale, legend=None),
        )
        .properties(height=200),
        use_container_width=True,
    )

with col_right:
    st.subheader("Conversions by Platform")
    st.altair_chart(
        alt.Chart(platform_agg)
        .mark_bar()
        .encode(
            y=alt.Y("SOURCE_PLATFORM:N", title=None, sort="-x"),
            x=alt.X("total_conversions:Q", title="Total Conversions"),
            color=alt.Color("SOURCE_PLATFORM:N", scale=color_scale, legend=None),
        )
        .properties(height=200),
        use_container_width=True,
    )

st.divider()

# ── Daily Spend Trend + Anomaly Detection ────────────────────
st.subheader("Daily Spend Trend")

daily = filtered.groupby(["DATE", "SOURCE_PLATFORM"], as_index=False).agg(
    daily_spend=("SPEND", "sum")
)

# Z-score anomaly detection per platform (flag |z| > 2)
daily["z_score"] = daily.groupby("SOURCE_PLATFORM")["daily_spend"].transform(
    lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
)
anomalies = daily[daily["z_score"].abs() > 2].copy()
anomalies["anomaly_label"] = anomalies.apply(
    lambda r: f"{r['SOURCE_PLATFORM']}: ${r['daily_spend']:,.0f} (z={r['z_score']:.1f})", axis=1
)

line = (
    alt.Chart(daily)
    .mark_line(point=True)
    .encode(
        x=alt.X("DATE:T", title="Date"),
        y=alt.Y("daily_spend:Q", title="Spend ($)"),
        color=alt.Color("SOURCE_PLATFORM:N", scale=color_scale, title="Platform"),
    )
)

anomaly_markers = (
    alt.Chart(anomalies)
    .mark_circle(size=120, color="red", opacity=0.85)
    .encode(
        x=alt.X("DATE:T"),
        y=alt.Y("daily_spend:Q"),
        tooltip=[
            alt.Tooltip("DATE:T", title="Date"),
            alt.Tooltip("SOURCE_PLATFORM:N", title="Platform"),
            alt.Tooltip("daily_spend:Q", title="Spend ($)", format="$,.2f"),
            alt.Tooltip("z_score:Q", title="Z-Score", format=".2f"),
        ],
    )
)

st.altair_chart(
    (line + anomaly_markers).properties(height=350),
    use_container_width=True,
)

# Anomaly callout
if not anomalies.empty:
    with st.expander(f"⚠️ {len(anomalies)} spend anomal{'y' if len(anomalies)==1 else 'ies'} detected"):
        st.caption("Days where daily spend deviated more than 2 standard deviations from that platform's average.")
        for _, row in anomalies.sort_values("DATE").iterrows():
            direction = "spike" if row["z_score"] > 0 else "drop"
            st.markdown(
                f"**{row['DATE'].strftime('%b %d')}** — {row['SOURCE_PLATFORM']} "
                f"spend {direction}: **${row['daily_spend']:,.0f}** "
                f"(z = {row['z_score']:.1f})"
            )
else:
    st.caption("No significant spend anomalies detected in the selected date range.")

st.divider()

# ── Campaign Performance Table ───────────────────────────────
st.subheader("Campaign Performance")
camp = filtered.groupby(["SOURCE_PLATFORM", "CAMPAIGN_NAME"], as_index=False).agg(
    total_spend=("SPEND", "sum"),
    total_impressions=("IMPRESSIONS", "sum"),
    total_clicks=("CLICKS", "sum"),
    total_conversions=("CONVERSIONS", "sum"),
)
camp["ctr"] = camp.apply(
    lambda r: 100 * r["total_clicks"] / r["total_impressions"]
    if r["total_impressions"] else 0, axis=1,
)
camp["cpc"] = camp.apply(
    lambda r: r["total_spend"] / r["total_clicks"] if r["total_clicks"] else 0, axis=1
)
camp["conversion_rate"] = camp.apply(
    lambda r: 100 * r["total_conversions"] / r["total_clicks"]
    if r["total_clicks"] else 0, axis=1,
)
camp = camp.sort_values("total_spend", ascending=False).reset_index(drop=True)

display_camp = camp.rename(columns={
    "SOURCE_PLATFORM": "Platform", "CAMPAIGN_NAME": "Campaign",
    "total_spend": "Total Spend", "total_impressions": "Impressions",
    "total_clicks": "Clicks", "total_conversions": "Conversions",
    "ctr": "CTR (%)", "cpc": "CPC ($)", "conversion_rate": "Conv. Rate (%)",
})
display_camp["Total Spend"] = display_camp["Total Spend"].apply(lambda x: f"${x:,.2f}")
display_camp["Impressions"] = display_camp["Impressions"].apply(lambda x: f"{x:,.0f}")
display_camp["Clicks"] = display_camp["Clicks"].apply(lambda x: f"{x:,.0f}")
display_camp["Conversions"] = display_camp["Conversions"].apply(lambda x: f"{x:,.0f}")
display_camp["CTR (%)"] = display_camp["CTR (%)"].apply(lambda x: f"{x:.2f}%")
display_camp["CPC ($)"] = display_camp["CPC ($)"].apply(lambda x: f"${x:.2f}")
display_camp["Conv. Rate (%)"] = display_camp["Conv. Rate (%)"].apply(lambda x: f"{x:.2f}%")
st.dataframe(display_camp, use_container_width=True)

st.divider()

# ── Efficiency Scatter Plot ──────────────────────────────────
st.subheader("Campaign Efficiency: CPC vs Conversion Rate")
scatter_data = camp[camp["total_clicks"] > 0].copy()
st.altair_chart(
    alt.Chart(scatter_data)
    .mark_circle()
    .encode(
        x=alt.X("cpc:Q", title="Cost per Click ($)"),
        y=alt.Y("conversion_rate:Q", title="Conversion Rate (%)"),
        color=alt.Color("SOURCE_PLATFORM:N", scale=color_scale, title="Platform"),
        size=alt.Size("total_spend:Q", title="Total Spend", scale=alt.Scale(range=[50, 500])),
        tooltip=[
            alt.Tooltip("CAMPAIGN_NAME:N", title="Campaign"),
            alt.Tooltip("SOURCE_PLATFORM:N", title="Platform"),
            alt.Tooltip("cpc:Q", title="CPC", format="$.2f"),
            alt.Tooltip("conversion_rate:Q", title="Conv Rate", format=".2f"),
            alt.Tooltip("total_spend:Q", title="Spend", format="$,.0f"),
        ],
    )
    .properties(height=400),
    use_container_width=True,
)
