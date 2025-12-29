import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import textwrap

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv")
    df["month"] = pd.to_datetime(df["month"])
    df["remaining_lease_years"] = df["remaining_lease"].str.extract(r'(\d+)').astype(int)
    df["storey_floor"] = df["storey_range"].str.extract(r'(\d+)').astype(int)
    df["price_per_sqm"] = df["resale_price"] / df["floor_area_sqm"]
    return df

df = load_data()

# -----------------------------
# Price Formatting
# -----------------------------
def format_price(value):
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    else:
        return f"${value/1000:.0f}k"

# -----------------------------
# Dashboard Title
# -----------------------------
st.title("🏠 JiajiaLiangTeh")

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")
default_town = "BUKIT MERAH"
default_flat_type = "4 ROOM"
default_flat_models = ["Improved","DBSS","Standard","S1","S2","Model A","Model A2","Simplified"]

# Town
town = st.sidebar.selectbox(
    "Town",
    sorted(df["town"].dropna().unique()),
    index=sorted(df["town"].dropna().unique()).index(default_town)
)

# Flat Type
flat_type = st.sidebar.selectbox(
    "Flat Type",
    sorted(df["flat_type"].dropna().unique()),
    index=sorted(df["flat_type"].dropna().unique()).index(default_flat_type)
)

# Flat Model Tiles
st.sidebar.markdown("**Flat Model**")
flat_model_options = sorted(df["flat_model"].dropna().unique())
col1, col2 = st.sidebar.columns(2)
select_all = col1.button("Select All")
deselect_all = col2.button("Deselect All")

if "selected_flat_models" not in st.session_state:
    st.session_state.selected_flat_models = [m for m in flat_model_options if m in default_flat_models]

if select_all: st.session_state.selected_flat_models = flat_model_options.copy()
if deselect_all: st.session_state.selected_flat_models = []

num_cols = 2
cols = st.sidebar.columns(num_cols)
selected_flat_models = []
for i, model in enumerate(flat_model_options):
    col = cols[i % num_cols]
    checked = model in st.session_state.selected_flat_models
    if col.checkbox(model, value=checked):
        selected_flat_models.append(model)
st.session_state.selected_flat_models = selected_flat_models

# Storey, Floor Area, Remaining Lease, Month Sold sliders
storey_range = st.sidebar.slider("Storey Range", int(df["storey_floor"].min()), int(df["storey_floor"].max()), (int(df["storey_floor"].min()), int(df["storey_floor"].max())))
floor_area_range = st.sidebar.slider("Floor Area (sqm)", int(df["floor_area_sqm"].min()), int(df["floor_area_sqm"].max()), (int(df["floor_area_sqm"].min()), int(df["floor_area_sqm"].max())))
lease_range = st.sidebar.slider("Remaining Lease (Years)", int(df["remaining_lease_years"].min()), int(df["remaining_lease_years"].max()), (int(df["remaining_lease_years"].min()), int(df["remaining_lease_years"].max())))
latest_month = df["month"].max()
month_range = st.sidebar.date_input("Month Sold Range",[latest_month - pd.DateOffset(months=12), latest_month])

# -----------------------------
# Filter Data
# -----------------------------
filtered = df[
    (df["town"].str.upper()==town.upper()) &
    (df["flat_type"].str.upper()==flat_type.upper()) &
    (df["flat_model"].isin(selected_flat_models)) &
    (df["storey_floor"].between(storey_range[0],storey_range[1])) &
    (df["floor_area_sqm"].between(floor_area_range[0],floor_area_range[1])) &
    (df["remaining_lease_years"].between(lease_range[0],lease_range[1])) &
    (df["month"].between(pd.to_datetime(month_range[0]),pd.to_datetime(month_range[1])))
].copy()

# -----------------------------
# Floor Category & Lease Bucket
# -----------------------------
filtered["floor_category"]=pd.cut(filtered["storey_floor"],bins=[-1,9,20,100],labels=["Low (<10)","Mid (10-20)","High (>20)"])
def lease_bucket(x):
    if x>=81: return "81-99 yrs"
    elif x>=61: return "61-80 yrs"
    else: return "0-60 yrs"
filtered["lease_bucket"]=filtered["remaining_lease_years"].apply(lease_bucket)

# -----------------------------
# Price Trend Charts by Floor Category & Lease Bucket
# -----------------------------
st.subheader("📈 Resale Price Trend by Floor Category and Lease Bucket")
color_palette = {"0-60 yrs": "#FFA600", "61-80 yrs": "#4ECDC4", "81-99 yrs": "#FF6B6B"}

for cat in ["High (>20)","Mid (10-20)","Low (<10)"]:
    st.markdown(f"### {cat} Floors")
    df_cat = filtered[filtered["floor_category"]==cat]
    if not df_cat.empty:
        fig = px.scatter(
            df_cat,
            x="month",
            y=df_cat["resale_price"]/1000,
            color="lease_bucket",
            trendline="ols",
            color_discrete_map=color_palette,
            labels={"month":"Month Sold","resale_price":"Price ($k)","lease_bucket":"Lease Bucket"},
            hover_data={
                "resale_price":True,
                "block":True,
                "street_name":True,
                "storey_floor":True,
                "remaining_lease_years":True,
                "floor_area_sqm":True,
                "month":True
            }
        )
        fig.update_layout(yaxis_title="Resale Price ($k)", xaxis_title="Month Sold")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for this floor category.")

# -----------------------------
# Box & Violin Plots (Floor Area vs Price)
# -----------------------------
st.subheader("📦 Resale Price Distribution by Floor Area")
floor_bins = range(int(filtered["floor_area_sqm"].min()), int(filtered["floor_area_sqm"].max()) + 10, 10)
filtered["floor_bin"] = pd.cut(filtered["floor_area_sqm"], bins=floor_bins)
filtered["floor_bin_str"] = filtered["floor_bin"].astype(str)  # Fix for Interval serialization

# Box Plot
fig_box = px.box(
    filtered,
    x="floor_bin_str",
    y="resale_price",
    color="lease_bucket",
    labels={"floor_bin_str":"Floor Area (sqm)","resale_price":"Resale Price ($k)","lease_bucket":"Lease Bucket"},
    color_discrete_map=color_palette
)
fig_box.update_yaxes(title="Resale Price ($k)")
st.plotly_chart(fig_box, use_container_width=True)

# Violin Plot
fig_violin = px.violin(
    filtered,
    x="floor_bin_str",
    y="resale_price",
    color="lease_bucket",
    box=True,
    points="all",
    labels={"floor_bin_str":"Floor Area (sqm)","resale_price":"Resale Price ($k)","lease_bucket":"Lease Bucket"},
    color_discrete_map=color_palette
)
fig_violin.update_yaxes(title="Resale Price ($k)")
st.plotly_chart(fig_violin, use_container_width=True)

# -----------------------------
# Average Resale Price by Street Name
# -----------------------------
st.subheader("🌡️ Average Resale Price by Street Name")
street_stats = filtered.groupby("street_name").agg(avg_price=("resale_price","mean"),count=("resale_price","count")).reset_index()
street_stats["avg_price_k"]=street_stats["avg_price"]/1000
fig_street = px.bar(
    street_stats,
    x="street_name",
    y="avg_price_k",
    text="avg_price_k",
    color="avg_price_k",
    color_continuous_scale=px.colors.sequential.Tealgrn,
    labels={"avg_price_k":"Avg Price ($k)","street_name":"Street"}
)
fig_street.update_layout(yaxis_title="Avg Resale Price ($k)", xaxis_title="Street Name")
st.plotly_chart(fig_street, use_container_width=True)

# -----------------------------
# Potential Purchase Scoring (Top 20)
# -----------------------------
median_psqm = filtered['price_per_sqm'].median()
def calculate_value_score(row):
    score = 50
    if row["storey_floor"]>20: score+=5
    elif row["storey_floor"]>=10: score+=3
    if row["floor_area_sqm"]>filtered['floor_area_sqm'].median(): score+=5
    if row['price_per_sqm']<median_psqm: score+=15
    else: score-=15*((row['price_per_sqm']-median_psqm)/median_psqm)
    if row["remaining_lease_years"]<60: score-=25
    elif row["remaining_lease_years"]<80: score-=10
    return max(min(score,100),0)

def explain_score(row):
    reasons=[]
    if row["storey_floor"]>20: reasons.append("High floor")
    elif row["storey_floor"]>=10: reasons.append("Mid floor")
    if row["floor_area_sqm"]>filtered['floor_area_sqm'].median(): reasons.append("Spacious")
    if row["remaining_lease_years"]<60: reasons.append("Low remaining lease")
    if row['price_per_sqm']<median_psqm: reasons.append("Good value $/sqm")
    return ", ".join(reasons)

filtered["Potential Score"] = filtered.apply(calculate_value_score, axis=1)
filtered["Why Recommended"] = filtered.apply(explain_score, axis=1)

# Top 20 only
top20 = filtered.sort_values("Potential Score",ascending=False).head(20).copy()
top20['resale_price'] = top20['resale_price'].apply(lambda x: format_price(x))

# Add Score Bar column
def score_color(val):
    if val>=75: return 'background-color: #2ECC71'
    elif val>=50: return 'background-color: #F1C40F'
    else: return 'background-color: #E74C3C'

top20_display = top20[[
    "month","town","flat_type","block","street_name","storey_range","floor_area_sqm",
    "flat_model","lease_commence_date","remaining_lease","resale_price","Potential Score","Why Recommended"
]].copy()
top20_display["Potential Score"] = top20_display["Potential Score"].astype(int)

st.subheader("💡 Top 20 Potential Purchase Flats (Interactive Table)")
st.dataframe(
    top20_display.style.bar(subset=["Potential Score"], color=['#E74C3C','#2ECC71']),
    height=600
)
