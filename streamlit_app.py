"""
Phase 5: Predictive Maintenance Dashboard
Run: uv run streamlit run streamlit_app.py
Requires: streamlit, plotly, snowflake-snowpark-python
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from snowpark_session import create_snowpark_session

st.set_page_config(page_title="Predictive Maintenance", page_icon="🔧", layout="wide")

@st.cache_resource
def get_session():
    return create_snowpark_session("PT09219")

@st.cache_data(ttl=300)
def load_health_summary():
    session = get_session()
    return session.table("PREDICT_MAINT_DB.ANALYTICS.ASSET_HEALTH_SUMMARY").to_pandas()

@st.cache_data(ttl=300)
def load_oee():
    session = get_session()
    return session.table("PREDICT_MAINT_DB.ANALYTICS.PRODUCTION_OEE").to_pandas()

@st.cache_data(ttl=300)
def load_maintenance_cost():
    session = get_session()
    return session.table("PREDICT_MAINT_DB.ANALYTICS.MAINTENANCE_COST_SUMMARY").to_pandas()

@st.cache_data(ttl=300)
def load_sensor_data(asset_id: str):
    session = get_session()
    df = (session.table("PREDICT_MAINT_DB.ANALYTICS.ASSET_SENSOR_STATS")
          .filter(f"ASSET_ID = '{asset_id}'")
          .to_pandas())
    df["READING_TS"] = pd.to_datetime(df["READING_TS"])
    return df

@st.cache_data(ttl=300)
def load_assets():
    session = get_session()
    return session.table("PREDICT_MAINT_DB.RAW.ASSETS").to_pandas()

STATUS_COLOR = {"NORMAL": "#2ecc71", "ALERT": "#f39c12", "ALARM": "#e74c3c"}

# ---- Sidebar ----
st.sidebar.title("Predictive Maintenance")
st.sidebar.caption("PREDICT_MAINT_DB | 3 Plants | 30 Assets")
page = st.sidebar.radio("Navigation", ["Asset Health", "OEE Dashboard", "Maintenance Costs", "Sensor Deep Dive"])


# ==================================================
# PAGE 1: Asset Health Overview
# ==================================================
if page == "Asset Health":
    st.title("Asset Health Overview")
    df = load_health_summary()

    col_plant, col_type = st.columns(2)
    plants = ["All"] + sorted(df["PLANT"].unique().tolist())
    types = ["All"] + sorted(df["ASSET_TYPE"].unique().tolist())
    sel_plant = col_plant.selectbox("Plant", plants, key="health_plant")
    sel_type = col_type.selectbox("Asset Type", types, key="health_type")
    if sel_plant != "All":
        df = df[df["PLANT"] == sel_plant]
    if sel_type != "All":
        df = df[df["ASSET_TYPE"] == sel_type]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Assets", len(df))
    alert_count = len(df[df["OVERALL_STATUS"].isin(["ALERT", "ALARM"])])
    k2.metric("Alert / Alarm", alert_count)
    k3.metric("Avg Hrs Since Maint", f"{df['HOURS_SINCE_LAST_MAINT'].mean():.0f}")
    k4.metric("Corrective WOs (30d)", int(df["CORRECTIVE_WO_30D"].sum()))

    # Health table
    st.subheader("Asset Status")
    display_cols = ["ASSET_ID", "ASSET_TYPE", "PLANT", "CRITICALITY", "OVERALL_STATUS",
                    "VIB_BASELINE_DEV_PCT", "TEMP_BASELINE_DEV_PCT", "VIB_BREACH_COUNT_24H",
                    "HOURS_SINCE_LAST_MAINT", "CORRECTIVE_WO_30D"]
    st.dataframe(
        df[display_cols].sort_values("OVERALL_STATUS", ascending=False)
        .style.applymap(
            lambda v: f"background-color: {STATUS_COLOR.get(v, '')}" if v in STATUS_COLOR else "",
            subset=["OVERALL_STATUS"]
        ),
        use_container_width=True, hide_index=True
    )

    # Baseline deviation chart
    st.subheader("Baseline Deviation (%)")
    chart_df = df[["ASSET_ID", "VIB_BASELINE_DEV_PCT", "TEMP_BASELINE_DEV_PCT", "CURR_BASELINE_DEV_PCT"]].melt(
        id_vars="ASSET_ID", var_name="Metric", value_name="Deviation"
    )
    chart_df["Metric"] = chart_df["Metric"].str.replace("_BASELINE_DEV_PCT", "")
    fig = px.bar(chart_df, x="ASSET_ID", y="Deviation", color="Metric", barmode="group",
                 color_discrete_sequence=["#3498db", "#e74c3c", "#f39c12"])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


# ==================================================
# PAGE 2: OEE Dashboard
# ==================================================
elif page == "OEE Dashboard":
    st.title("OEE Dashboard")
    df = load_oee()
    df["SHIFT_DATE"] = pd.to_datetime(df["SHIFT_DATE"].astype(str).str.strip('"'))

    col_plant, col_type, col_dates = st.columns(3)
    plants = ["All"] + sorted(df["PLANT"].unique().tolist())
    types = ["All"] + sorted(df["ASSET_TYPE"].unique().tolist())
    sel_plant = col_plant.selectbox("Plant", plants, key="oee_plant")
    sel_type = col_type.selectbox("Asset Type", types, key="oee_type")
    date_range = col_dates.date_input("Date Range",
        value=(df["SHIFT_DATE"].min(), df["SHIFT_DATE"].max()),
        min_value=df["SHIFT_DATE"].min(), max_value=df["SHIFT_DATE"].max(), key="oee_dates")
    if sel_plant != "All":
        df = df[df["PLANT"] == sel_plant]
    if sel_type != "All":
        df = df[df["ASSET_TYPE"] == sel_type]
    if len(date_range) == 2:
        df = df[(df["SHIFT_DATE"] >= pd.Timestamp(date_range[0])) &
                (df["SHIFT_DATE"] <= pd.Timestamp(date_range[1]))]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avg OEE", f"{df['OEE'].mean():.1%}")
    k2.metric("Avg Availability", f"{df['AVAILABILITY'].mean():.1%}")
    k3.metric("Avg Performance", f"{df['PERFORMANCE'].mean():.1%}")
    k4.metric("Avg Quality", f"{df['QUALITY'].mean():.1%}")

    # Daily OEE trend
    st.subheader("Daily OEE Trend")
    daily = df.groupby("SHIFT_DATE").agg(OEE=("OEE", "mean"), AVAILABILITY=("AVAILABILITY", "mean"),
                                          PERFORMANCE=("PERFORMANCE", "mean"), QUALITY=("QUALITY", "mean")).reset_index()
    fig = px.line(daily, x="SHIFT_DATE", y=["OEE", "AVAILABILITY", "PERFORMANCE", "QUALITY"],
                  color_discrete_sequence=["#2c3e50", "#3498db", "#e67e22", "#2ecc71"])
    fig.update_layout(height=400, yaxis_title="Score", xaxis_title="Date", legend_title="Metric")
    st.plotly_chart(fig, use_container_width=True)

    # OEE by plant
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("OEE by Plant")
        plant_oee = df.groupby("PLANT")["OEE"].mean().reset_index()
        fig2 = px.bar(plant_oee, x="PLANT", y="OEE", color="PLANT",
                      color_discrete_sequence=["#3498db", "#e74c3c", "#2ecc71"])
        fig2.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    with c2:
        st.subheader("OEE by Asset Type")
        type_oee = df.groupby("ASSET_TYPE")["OEE"].mean().reset_index()
        fig3 = px.bar(type_oee, x="ASSET_TYPE", y="OEE", color="ASSET_TYPE",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig3.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)


# ==================================================
# PAGE 3: Maintenance Costs
# ==================================================
elif page == "Maintenance Costs":
    st.title("Maintenance Costs")
    df = load_maintenance_cost()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Cost (INR)", f"₹{df['TOTAL_MAINT_COST_INR'].sum():,.0f}")
    k2.metric("Corrective Cost", f"₹{df['CORRECTIVE_COST_INR'].sum():,.0f}")
    k3.metric("Preventive Cost", f"₹{df['PREVENTIVE_COST_INR'].sum():,.0f}")
    k4.metric("Avg MTBF (hours)", f"{df['MTBF_HOURS'].mean():.0f}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Cost by Plant")
        plant_cost = df.groupby("PLANT").agg(
            Corrective=("CORRECTIVE_COST_INR", "sum"),
            Preventive=("PREVENTIVE_COST_INR", "sum")
        ).reset_index().melt(id_vars="PLANT", var_name="Type", value_name="Cost_INR")
        fig = px.bar(plant_cost, x="PLANT", y="Cost_INR", color="Type", barmode="stack",
                     color_discrete_sequence=["#e74c3c", "#3498db"])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Top 10 Costliest Assets")
        top10 = df.nlargest(10, "TOTAL_MAINT_COST_INR")
        fig2 = px.bar(top10, x="ASSET_ID", y="TOTAL_MAINT_COST_INR", color="CRITICALITY",
                      color_discrete_map={"A": "#e74c3c", "B": "#f39c12", "C": "#2ecc71"})
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Asset Maintenance Details")
    st.dataframe(
        df[["ASSET_ID", "ASSET_NAME", "PLANT", "CRITICALITY", "CORRECTIVE_COUNT", "PREVENTIVE_COUNT",
            "TOTAL_MAINT_COST_INR", "AVG_REPAIR_HOURS", "AVG_PARTS_WAIT_HOURS", "MTBF_HOURS"]]
        .sort_values("TOTAL_MAINT_COST_INR", ascending=False),
        use_container_width=True, hide_index=True
    )


# ==================================================
# PAGE 4: Sensor Deep Dive
# ==================================================
elif page == "Sensor Deep Dive":
    st.title("Sensor Deep Dive")
    assets_df = load_assets()
    asset_ids = sorted(assets_df["ASSET_ID"].tolist())
    sel_asset = st.selectbox("Select Asset", asset_ids)

    asset_info = assets_df[assets_df["ASSET_ID"] == sel_asset].iloc[0]
    st.caption(f"{asset_info['ASSET_NAME']} | {asset_info['ASSET_TYPE']} | {asset_info['PLANT']} | Criticality: {asset_info['CRITICALITY']}")

    with st.spinner("Loading sensor data..."):
        sdf = load_sensor_data(sel_asset)

    if sdf.empty:
        st.warning("No sensor data found for this asset.")
    else:
        last_7d = sdf[sdf["READING_TS"] >= sdf["READING_TS"].max() - pd.Timedelta(days=7)]

        # Vibration
        st.subheader("Vibration (mm/s)")
        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["VIBRATION_MM_S"],
                                    mode="lines", name="Vibration", line=dict(color="#3498db", width=1)))
        fig_v.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["VIB_AVG_6H"],
                                    mode="lines", name="6h Avg", line=dict(color="#2c3e50", width=2)))
        fig_v.add_hline(y=float(asset_info["VIB_ALERT_MM_S"]), line_dash="dash", line_color="orange",
                        annotation_text="ALERT")
        fig_v.add_hline(y=float(asset_info["VIB_ALARM_MM_S"]), line_dash="dash", line_color="red",
                        annotation_text="ALARM")
        fig_v.update_layout(height=300, margin=dict(t=30, b=30))
        st.plotly_chart(fig_v, use_container_width=True)

        # Temperature
        st.subheader("Temperature (°C)")
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["TEMPERATURE_C"],
                                    mode="lines", name="Temperature", line=dict(color="#e74c3c", width=1)))
        fig_t.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["TEMP_AVG_6H"],
                                    mode="lines", name="6h Avg", line=dict(color="#2c3e50", width=2)))
        fig_t.add_hline(y=float(asset_info["TEMP_ALERT_C"]), line_dash="dash", line_color="orange",
                        annotation_text="ALERT")
        fig_t.add_hline(y=float(asset_info["TEMP_ALARM_C"]), line_dash="dash", line_color="red",
                        annotation_text="ALARM")
        fig_t.update_layout(height=300, margin=dict(t=30, b=30))
        st.plotly_chart(fig_t, use_container_width=True)

        # Motor Current
        st.subheader("Motor Current (A)")
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["MOTOR_CURRENT_A"],
                                    mode="lines", name="Current", line=dict(color="#f39c12", width=1)))
        fig_c.add_trace(go.Scatter(x=last_7d["READING_TS"], y=last_7d["CURR_AVG_6H"],
                                    mode="lines", name="6h Avg", line=dict(color="#2c3e50", width=2)))
        fig_c.update_layout(height=300, margin=dict(t=30, b=30))
        st.plotly_chart(fig_c, use_container_width=True)
