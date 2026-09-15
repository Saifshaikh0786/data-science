"""
Mandi-to-Market Supply Chain Optimizer — Streamlit Dashboard
HACKATHON-WINNING VERSION: 10-page premium dashboard with AI Agent,
Sankey flow visualization, Farmer Advisory System, and Price Volatility Heatmap.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
import sys, os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent / "src"))

DB_PATH = Path(__file__).parent / "warehouse.duckdb"

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mandi-to-Market Supply Chain Optimizer",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Premium CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main .block-container { padding-top: 1.2rem; max-width: 1440px; }

/* Sidebar — deep dark gradient */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #080d14 0%, #111827 40%, #0c1222 100%);
}
section[data-testid="stSidebar"] .stMarkdown { color: #cbd5e1; }
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem !important;
    transition: all 0.2s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #60a5fa !important;
    padding-left: 4px;
}

/* KPI Cards — glassmorphism */
.kpi-card {
    background: linear-gradient(135deg, rgba(30,42,58,0.85) 0%, rgba(45,55,72,0.7) 100%);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(99,179,237,0.12);
    border-radius: 18px;
    padding: 1.4rem 1.2rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.05);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #63b3ed, #4fd1c5, #68d391);
    border-radius: 18px 18px 0 0;
}
.kpi-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 16px 48px rgba(99,179,237,0.15), inset 0 1px 0 rgba(255,255,255,0.08);
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #63b3ed, #4fd1c5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0.2rem 0;
    letter-spacing: -0.5px;
}
.kpi-label {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
}
.kpi-sublabel {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 0.2rem;
}

/* Warning KPI variant */
.kpi-card.warning .kpi-value {
    background: linear-gradient(135deg, #f6ad55, #fc8181);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.kpi-card.warning::before {
    background: linear-gradient(90deg, #f6ad55, #fc8181, #f56565);
}

/* Success KPI variant */
.kpi-card.success .kpi-value {
    background: linear-gradient(135deg, #68d391, #4fd1c5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.kpi-card.success::before {
    background: linear-gradient(90deg, #68d391, #4fd1c5, #38b2ac);
}

.section-header {
    font-size: 1.3rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 1.8rem 0 0.7rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid rgba(99,179,237,0.2);
}

/* Info box */
.info-box {
    background: linear-gradient(135deg, rgba(26,54,93,0.6) 0%, rgba(43,76,126,0.4) 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin: 0.5rem 0 1rem;
    backdrop-filter: blur(8px);
}
.info-box.alert {
    background: linear-gradient(135deg, rgba(116,42,42,0.6) 0%, rgba(155,44,44,0.4) 100%);
    border-color: rgba(252,129,129,0.2);
}
.info-box.success {
    background: linear-gradient(135deg, rgba(22,101,52,0.6) 0%, rgba(34,120,65,0.4) 100%);
    border-color: rgba(104,211,145,0.2);
}

/* Recommendation card */
.rec-card {
    background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(30,41,59,0.8));
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 14px;
    padding: 1.2rem;
    margin: 0.6rem 0;
    transition: all 0.25s ease;
}
.rec-card:hover {
    border-color: rgba(99,179,237,0.4);
    box-shadow: 0 4px 20px rgba(99,179,237,0.1);
}
.rec-rank {
    display: inline-block;
    background: linear-gradient(135deg, #63b3ed, #4fd1c5);
    color: #0f172a;
    font-weight: 800;
    width: 32px; height: 32px;
    border-radius: 50%;
    text-align: center;
    line-height: 32px;
    font-size: 0.85rem;
    margin-right: 10px;
}
.rec-mandi {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
}
.rec-price {
    font-size: 1.4rem;
    font-weight: 800;
    color: #4fd1c5;
}
.rec-detail {
    font-size: 0.8rem;
    color: #94a3b8;
}

/* Badge */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-green { background: rgba(104,211,145,0.15); color: #68d391; }
.badge-red { background: rgba(252,129,129,0.15); color: #fc8181; }
.badge-blue { background: rgba(99,179,237,0.15); color: #63b3ed; }
.badge-yellow { background: rgba(246,173,85,0.15); color: #f6ad55; }

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1a1f2e; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }
</style>
""", unsafe_allow_html=True)


# ─── DB Connection ────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)

def run_query(sql):
    con = get_connection()
    return con.execute(sql).fetchdf()

# ─── Plotly Theme ─────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#e2e8f0", size=12),
    margin=dict(l=40, r=30, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
)
COLORS = ["#63b3ed", "#4fd1c5", "#f6ad55", "#fc8181", "#b794f4", "#68d391",
          "#f687b3", "#fbd38d", "#81e6d9", "#a3bffa"]

def kpi_card(label, value, sublabel="", variant=""):
    cls = f"kpi-card {variant}" if variant else "kpi-card"
    st.markdown(f"""
    <div class="{cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sublabel">{sublabel}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 0.5rem 0 0.8rem;'>
        <span style='font-size: 2.2rem;'>🌾</span><br/>
        <span style='font-size: 1.1rem; font-weight: 800;
              background: linear-gradient(135deg, #63b3ed, #4fd1c5);
              -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            Mandi Optimizer
        </span><br/>
        <span style='font-size: 0.65rem; color: #64748b; letter-spacing: 2px; text-transform: uppercase;'>
            Supply Chain Intelligence
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    page = st.radio(
        "Navigate", [
            "📊 Executive Overview",
            "💰 Price & MSP Watch",
            "📈 Arbitrage Explorer",
            "📡 Farmer Advisory",
            "🌐 Supply Chain Flow",
            "🔥 Price Volatility",
            "🚛 Transport & Logistics",
            "🌧️ Weather Impact",
            "🔍 Data Quality",
            "🤖 AI Agent",
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 0.5rem;'>
        <span class="badge badge-blue">TransOrg AgentIQ Datathon</span><br/><br/>
        <span style='color: #475569; font-size: 0.65rem;'>
            DuckDB · Streamlit · Plotly · Groq LLM<br/>
            Agriculture & FoodTech Track
        </span>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: Executive Overview
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Executive Overview":
    st.markdown("# 📊 Executive Overview")
    st.markdown("*National agricultural supply chain intelligence dashboard*")

    # KPIs
    total_qtl = run_query("SELECT ROUND(SUM(arrival_qtl)) FROM fact_arrivals").iloc[0, 0]
    avg_gap = run_query("""
        SELECT ROUND(AVG(modal_price) - AVG(msp), 2)
        FROM fact_prices WHERE modal_price IS NOT NULL AND msp IS NOT NULL
    """).iloc[0, 0]
    crash_count = run_query("SELECT COUNT(*) FROM fact_prices WHERE below_msp").iloc[0, 0]
    delay_rate = run_query("""
        SELECT ROUND(AVG(CASE WHEN is_delayed THEN 1.0 ELSE 0.0 END) * 100, 1)
        FROM fact_transport
    """).iloc[0, 0]
    total_mandis = run_query("SELECT COUNT(*) FROM dim_mandi").iloc[0, 0]
    total_crops = run_query("SELECT COUNT(DISTINCT crop) FROM fact_arrivals WHERE crop IS NOT NULL").iloc[0, 0]

    cols = st.columns(6)
    with cols[0]:
        kpi_card("Total Arrivals", f"{total_qtl:,.0f}", "Quintals", "success")
    with cols[1]:
        sign = "+" if avg_gap and avg_gap > 0 else ""
        kpi_card("Price vs MSP", f"{sign}₹{avg_gap:,.2f}" if avg_gap else "N/A", "Modal − MSP gap")
    with cols[2]:
        kpi_card("Crash Alerts", f"{crash_count:,}", "Below MSP", "warning")
    with cols[3]:
        kpi_card("Delay Rate", f"{delay_rate}%", ">1.5× expected", "warning" if delay_rate > 5 else "")
    with cols[4]:
        kpi_card("Active Mandis", f"{total_mandis}", "Across 3 states")
    with cols[5]:
        kpi_card("Crops Tracked", f"{total_crops}", "Canonical categories")

    st.markdown("")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="section-header">📈 Daily National Arrivals Trend</div>', unsafe_allow_html=True)
        daily = run_query("""
            SELECT date, SUM(arrival_qtl) AS total_qtl FROM fact_arrivals
            WHERE date IS NOT NULL GROUP BY date ORDER BY date
        """)
        if not daily.empty:
            fig = px.area(daily, x="date", y="total_qtl",
                         labels={"date": "Date", "total_qtl": "Total Arrivals (Qtl)"},
                         color_discrete_sequence=["#63b3ed"])
            fig.update_layout(**PLOTLY_LAYOUT, height=370)
            fig.update_traces(fill='tozeroy', fillcolor='rgba(99,179,237,0.1)',
                            line=dict(width=2.5))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">🥧 Crop-wise Arrival Share</div>', unsafe_allow_html=True)
        crop_share = run_query("""
            SELECT crop, SUM(arrival_qtl) AS qtl FROM fact_arrivals
            WHERE crop IS NOT NULL GROUP BY crop ORDER BY qtl DESC
        """)
        if not crop_share.empty:
            fig = px.pie(crop_share, values="qtl", names="crop",
                        color_discrete_sequence=COLORS, hole=0.5)
            layout = {**PLOTLY_LAYOUT, "height": 370, "showlegend": True,
                      "legend": dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.15, font=dict(size=10))}
            fig.update_layout(**layout)
            fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=10)
            st.plotly_chart(fig, use_container_width=True)

    # Top Mandis + State Distribution
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('<div class="section-header">🏆 Top 10 Mandis by Arrival Volume</div>', unsafe_allow_html=True)
        top = run_query("""
            SELECT m.mandi_name, m.district, m.state, ROUND(SUM(a.arrival_qtl)) AS total_qtl
            FROM fact_arrivals a JOIN dim_mandi m USING (mandi_id)
            GROUP BY m.mandi_name, m.district, m.state ORDER BY total_qtl DESC LIMIT 10
        """)
        if not top.empty:
            fig = px.bar(top, x="total_qtl", y="mandi_name", orientation="h",
                        color="state", color_discrete_sequence=COLORS,
                        labels={"total_qtl": "Total Arrivals (Qtl)", "mandi_name": ""})
            fig.update_layout(**PLOTLY_LAYOUT, height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">🗺️ State-wise Distribution</div>', unsafe_allow_html=True)
        state_dist = run_query("""
            SELECT m.state, COUNT(DISTINCT m.mandi_id) AS mandis,
                   ROUND(SUM(a.arrival_qtl)) AS total_qtl
            FROM fact_arrivals a JOIN dim_mandi m USING (mandi_id)
            WHERE m.state != 'Unknown'
            GROUP BY m.state ORDER BY total_qtl DESC
        """)
        if not state_dist.empty:
            fig = px.bar(state_dist, x="state", y="total_qtl", text="mandis",
                        color="state", color_discrete_sequence=COLORS,
                        labels={"total_qtl": "Arrivals (Qtl)", "state": ""})
            fig.update_traces(texttemplate='%{text} mandis', textposition='outside')
            fig.update_layout(**PLOTLY_LAYOUT, height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: Price & MSP Watch
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Price & MSP Watch":
    st.markdown("# 💰 Price & MSP Watch")
    st.markdown("*Monitor wholesale prices against Minimum Support Prices — detect farmer distress early*")

    price_summary = run_query("""
        SELECT crop, ROUND(AVG(modal_price), 2) AS avg_modal, ROUND(AVG(msp), 2) AS avg_msp,
               ROUND(AVG(modal_price) - AVG(msp), 2) AS gap,
               SUM(CASE WHEN below_msp THEN 1 ELSE 0 END) AS crash_count,
               COUNT(*) AS total_records
        FROM fact_prices WHERE modal_price IS NOT NULL AND msp IS NOT NULL
        GROUP BY crop ORDER BY crash_count DESC
    """)

    if not price_summary.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Avg Modal Price (₹)", x=price_summary["crop"],
                            y=price_summary["avg_modal"], marker_color="#63b3ed",
                            text=price_summary["avg_modal"], textposition='outside'))
        fig.add_trace(go.Bar(name="Avg MSP (₹)", x=price_summary["crop"],
                            y=price_summary["avg_msp"], marker_color="#fc8181",
                            text=price_summary["avg_msp"], textposition='outside'))
        fig.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400,
                         title="Average Modal Price vs MSP by Crop")
        st.plotly_chart(fig, use_container_width=True)

    crops = run_query("SELECT DISTINCT crop FROM fact_prices WHERE crop IS NOT NULL ORDER BY crop")
    selected_crop = st.selectbox("🌾 Filter by Crop", ["All"] + crops["crop"].tolist())
    crop_filter = f"AND crop = '{selected_crop}'" if selected_crop != "All" else ""

    st.markdown('<div class="section-header">📈 Price Trend Over Time</div>', unsafe_allow_html=True)
    trend = run_query(f"""
        SELECT date, ROUND(AVG(modal_price), 2) AS avg_modal, ROUND(AVG(msp), 2) AS avg_msp
        FROM fact_prices WHERE date IS NOT NULL AND modal_price IS NOT NULL AND msp IS NOT NULL {crop_filter}
        GROUP BY date ORDER BY date
    """)
    if not trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["date"], y=trend["avg_modal"], name="Modal Price",
                                line=dict(color="#63b3ed", width=2.5), fill='tonexty'))
        fig.add_trace(go.Scatter(x=trend["date"], y=trend["avg_msp"], name="MSP (Floor)",
                                line=dict(color="#fc8181", width=2, dash="dash")))
        fig.update_layout(**PLOTLY_LAYOUT, height=400, title=f"Price Trend — {selected_crop}")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">🚨 Below-MSP Records</div>', unsafe_allow_html=True)
    below = run_query(f"""
        SELECT p.date, m.mandi_name, m.district, p.crop,
               ROUND(p.modal_price, 2) AS modal_price, ROUND(p.msp, 2) AS msp,
               ROUND(p.msp - p.modal_price, 2) AS deficit
        FROM fact_prices p LEFT JOIN dim_mandi m USING (mandi_id)
        WHERE p.below_msp {crop_filter} ORDER BY deficit DESC LIMIT 50
    """)
    if not below.empty:
        st.dataframe(below, use_container_width=True, height=350)
    else:
        st.success("✅ No price crashes found.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: Arbitrage Explorer
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Arbitrage Explorer":
    st.markdown("# 📈 Arbitrage Explorer")
    st.markdown("*The hero metric: identify cross-mandi price arbitrage opportunities*")

    col1, col2 = st.columns(2)
    with col1:
        crops = run_query("SELECT DISTINCT crop FROM fact_prices WHERE crop IS NOT NULL ORDER BY crop")
        arb_crop = st.selectbox("Select Crop", crops["crop"].tolist(), key="arb_crop")
    with col2:
        dates = run_query(f"""
            SELECT DISTINCT date FROM fact_prices
            WHERE crop = '{arb_crop}' AND date IS NOT NULL AND modal_price IS NOT NULL
            ORDER BY date DESC
        """)
        arb_date = st.selectbox("Select Date", dates["date"].tolist(), key="arb_date") if not dates.empty else None

    if arb_date:
        spread = run_query(f"""
            SELECT MAX(modal_price) - MIN(modal_price) AS price_spread,
                   MAX(modal_price) AS best, MIN(modal_price) AS worst, COUNT(*) AS cnt
            FROM fact_prices
            WHERE crop = '{arb_crop}' AND date = '{arb_date}' AND modal_price IS NOT NULL
        """)

        if not spread.empty and spread.iloc[0]["cnt"] > 0:
            cols = st.columns(4)
            with cols[0]:
                kpi_card("Price Spread", f"₹{spread.iloc[0]['price_spread']:,.2f}", "Arbitrage opportunity")
            with cols[1]:
                kpi_card("Best Price", f"₹{spread.iloc[0]['best']:,.2f}", "Highest modal", "success")
            with cols[2]:
                kpi_card("Worst Price", f"₹{spread.iloc[0]['worst']:,.2f}", "Lowest modal", "warning")
            with cols[3]:
                kpi_card("Mandis Reporting", f"{int(spread.iloc[0]['cnt'])}", "On this date")

        ranked = run_query(f"""
            SELECT m.mandi_name, m.district, m.state,
                   ROUND(p.modal_price, 2) AS modal_price, ROUND(p.msp, 2) AS msp,
                   CASE WHEN p.below_msp THEN '⚠️ Below MSP' ELSE '✅ Above MSP' END AS status
            FROM fact_prices p LEFT JOIN dim_mandi m USING (mandi_id)
            WHERE p.crop = '{arb_crop}' AND p.date = '{arb_date}' AND p.modal_price IS NOT NULL
            ORDER BY p.modal_price DESC
        """)
        if not ranked.empty:
            fig = px.bar(ranked, x="mandi_name", y="modal_price", color="status",
                        color_discrete_map={"✅ Above MSP": "#68d391", "⚠️ Below MSP": "#fc8181"},
                        labels={"modal_price": "₹ Modal Price", "mandi_name": ""})
            fig.update_layout(**PLOTLY_LAYOUT, height=400,
                             title=f"{arb_crop} Prices Across Mandis — {arb_date}")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(ranked, use_container_width=True, height=300)

    st.markdown('<div class="section-header">🔥 Largest Arbitrage Opportunities (All Time)</div>', unsafe_allow_html=True)
    top_arb = run_query("""
        SELECT crop, date,
               ROUND(MAX(modal_price) - MIN(modal_price), 2) AS spread,
               ROUND(MAX(modal_price), 2) AS best, ROUND(MIN(modal_price), 2) AS worst,
               COUNT(*) AS mandis
        FROM fact_prices WHERE modal_price IS NOT NULL
        GROUP BY crop, date HAVING COUNT(*) >= 2
        ORDER BY spread DESC LIMIT 15
    """)
    if not top_arb.empty:
        st.dataframe(top_arb, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: Farmer Advisory System (UNIQUE FEATURE)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📡 Farmer Advisory":
    st.markdown("# 📡 Farmer Advisory System")
    st.markdown("*Actionable intelligence for farmers — where to sell today for maximum returns*")

    st.markdown("""
    <div class="info-box success">
        <strong>🎯 How this works:</strong> Select your crop, and we'll rank all mandis by today's
        modal price, showing the MSP gap, price trend direction, and competitive position.
        This is the core "supply chain optimizer" — turning raw data into farmer-level decisions.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        crops = run_query("SELECT DISTINCT crop FROM fact_prices WHERE crop IS NOT NULL ORDER BY crop")
        adv_crop = st.selectbox("🌾 What crop are you selling?", crops["crop"].tolist(), key="adv_crop")
    with col2:
        # Get latest date with data for this crop
        latest = run_query(f"""
            SELECT MAX(date) AS latest_date FROM fact_prices
            WHERE crop = '{adv_crop}' AND modal_price IS NOT NULL
        """).iloc[0, 0]
        st.markdown(f"**📅 Latest available data:** `{latest}`")

    if latest:
        # Get all mandis with prices for this crop on the latest date
        advisory = run_query(f"""
            SELECT m.mandi_name, m.district, m.state, m.mandi_type,
                   ROUND(p.modal_price, 2) AS price,
                   ROUND(p.msp, 2) AS msp,
                   ROUND(p.modal_price - p.msp, 2) AS gap,
                   CASE WHEN p.modal_price >= p.msp THEN 'PROFITABLE' ELSE 'BELOW MSP' END AS verdict,
                   ROW_NUMBER() OVER (ORDER BY p.modal_price DESC) AS rank
            FROM fact_prices p
            JOIN dim_mandi m USING (mandi_id)
            WHERE p.crop = '{adv_crop}' AND p.date = '{latest}' AND p.modal_price IS NOT NULL
            ORDER BY p.modal_price DESC
        """)

        if not advisory.empty:
            best = advisory.iloc[0]
            worst = advisory.iloc[-1]

            # Hero recommendation
            st.markdown(f"""
            <div class="info-box success" style="text-align: center;">
                <span style="font-size: 0.75rem; color: #68d391; text-transform: uppercase;
                      letter-spacing: 2px; font-weight: 700;">🏆 Top Recommendation</span><br/>
                <span style="font-size: 1.6rem; font-weight: 800; color: #e2e8f0;">
                    Sell {adv_crop} at {best['mandi_name']}</span><br/>
                <span style="font-size: 1.2rem; color: #4fd1c5; font-weight: 700;">
                    ₹{best['price']:,.2f}/Qtl</span>
                <span style="font-size: 0.85rem; color: #94a3b8;">
                    &nbsp;in {best['district']}, {best['state']}</span><br/>
                <span style="font-size: 0.8rem; color: #68d391;">
                    {('✅ ₹' + f"{abs(best['gap']):,.2f}" + ' ABOVE MSP') if pd.notna(best['gap']) and best['gap'] >= 0
                     else ('⚠️ ₹' + f"{abs(best['gap']):,.2f}" + ' BELOW MSP') if pd.notna(best['gap'])
                     else '📊 MSP data unavailable for this date'}</span>
            </div>
            """, unsafe_allow_html=True)

            # Profit potential
            if len(advisory) > 1:
                savings = best['price'] - worst['price']
                st.markdown(f"""
                <div class="info-box">
                    <strong>💰 Profit potential:</strong> Selling at the best mandi vs the worst saves you
                    <strong style="color: #4fd1c5;">₹{savings:,.2f}/Qtl</strong>
                    — that's <strong style="color: #68d391;">{(savings / worst['price'] * 100):.1f}% more</strong> per quintal.
                </div>
                """, unsafe_allow_html=True)

            # Ranked list
            st.markdown('<div class="section-header">📊 All Mandis Ranked by Price</div>', unsafe_allow_html=True)

            fig = px.bar(advisory, x="mandi_name", y="price", color="verdict",
                        color_discrete_map={"PROFITABLE": "#68d391", "BELOW MSP": "#fc8181"},
                        labels={"price": f"₹/Qtl ({adv_crop})", "mandi_name": ""},
                        text="price")
            fig.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig.update_layout(**PLOTLY_LAYOUT, height=420,
                             title=f"Mandi Price Rankings — {adv_crop} ({latest})")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(advisory[["rank", "mandi_name", "district", "state", "price",
                                   "msp", "gap", "verdict"]],
                        use_container_width=True, height=350)

            # 7-day price history for top 3 mandis
            st.markdown('<div class="section-header">📈 7-Day Price History (Top 3 Mandis)</div>', unsafe_allow_html=True)
            top3_mandis = advisory.head(3)["mandi_name"].tolist()
            if top3_mandis:
                placeholders = ", ".join([f"'{m}'" for m in top3_mandis])
                history = run_query(f"""
                    SELECT p.date, m.mandi_name, ROUND(p.modal_price, 2) AS price
                    FROM fact_prices p JOIN dim_mandi m USING (mandi_id)
                    WHERE p.crop = '{adv_crop}' AND m.mandi_name IN ({placeholders})
                      AND p.modal_price IS NOT NULL AND p.date >= '{latest}'::DATE - INTERVAL 7 DAY
                    ORDER BY p.date
                """)
                if not history.empty:
                    fig = px.line(history, x="date", y="price", color="mandi_name",
                                color_discrete_sequence=COLORS,
                                labels={"price": "₹/Qtl", "date": "Date", "mandi_name": "Mandi"})
                    fig.update_layout(**PLOTLY_LAYOUT, height=350)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No price data available for this crop on the latest date.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5: Supply Chain Flow (UNIQUE — Sankey Diagram)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌐 Supply Chain Flow":
    st.markdown("# 🌐 Supply Chain Flow Visualization")
    st.markdown("*Sankey diagram showing goods flow from mandi districts to destination warehouses*")

    # Get flow data: district → destination with trip counts
    flow = run_query("""
        SELECT m.district AS source, t.destination AS target,
               COUNT(*) AS trips, ROUND(AVG(t.transit_hours), 1) AS avg_hours
        FROM fact_transport t
        JOIN dim_mandi m USING (mandi_id)
        WHERE m.district != 'Unknown'
        GROUP BY m.district, t.destination
        ORDER BY trips DESC
    """)

    if not flow.empty:
        # KPIs
        cols = st.columns(4)
        total_trips = flow["trips"].sum()
        unique_routes = len(flow)
        avg_time = run_query("SELECT ROUND(AVG(transit_hours), 1) FROM fact_transport WHERE transit_hours > 0").iloc[0, 0]
        dest_count = flow["target"].nunique()

        with cols[0]:
            kpi_card("Total Trips", f"{total_trips:,}", "Tracked shipments")
        with cols[1]:
            kpi_card("Unique Routes", f"{unique_routes}", "District → Warehouse")
        with cols[2]:
            kpi_card("Avg Transit", f"{avg_time}h", "Hours per trip")
        with cols[3]:
            kpi_card("Destinations", f"{dest_count}", "Warehouses + terminals")

        # Build Sankey
        st.markdown('<div class="section-header">🔀 District → Warehouse Flow</div>', unsafe_allow_html=True)

        sources = flow["source"].unique().tolist()
        targets = flow["target"].unique().tolist()
        all_labels = sources + targets

        source_idx = [all_labels.index(s) for s in flow["source"]]
        target_idx = [all_labels.index(t) for t in flow["target"]]

        # Color coding
        source_colors = [COLORS[i % len(COLORS)] for i in range(len(sources))]
        target_colors = ["#f6ad55", "#fc8181", "#b794f4", "#68d391", "#63b3ed", "#f687b3"]
        node_colors = source_colors + target_colors[:len(targets)]

        link_colors = [node_colors[s].replace(")", ",0.3)").replace("rgb", "rgba")
                       if "rgb" in node_colors[s]
                       else f"rgba(99,179,237,0.2)" for s in source_idx]

        fig = go.Figure(go.Sankey(
            node=dict(
                pad=20, thickness=25,
                line=dict(color="rgba(255,255,255,0.1)", width=0.5),
                label=all_labels,
                color=node_colors,
            ),
            link=dict(
                source=source_idx, target=target_idx,
                value=flow["trips"].tolist(),
                color=[f"rgba(99,179,237,0.15)"] * len(flow),
            )
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=600,
                         title="Supply Chain Flow: Mandi Districts → Destination Warehouses")
        st.plotly_chart(fig, use_container_width=True)

        # Route details table
        st.markdown('<div class="section-header">📋 Route Details</div>', unsafe_allow_html=True)
        st.dataframe(flow.rename(columns={
            "source": "Origin District", "target": "Destination",
            "trips": "Trip Count", "avg_hours": "Avg Hours"
        }), use_container_width=True, height=350)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6: Price Volatility Heatmap (UNIQUE)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔥 Price Volatility":
    st.markdown("# 🔥 Price Volatility Analysis")
    st.markdown("*Identify high-risk price fluctuation periods across crops and mandis*")

    st.markdown("""
    <div class="info-box">
        <strong>📊 Why this matters:</strong> High price volatility hurts farmers (unpredictable income)
        and traders (inventory risk). This heatmap identifies which crop-month combinations
        show the most price instability — enabling targeted policy interventions.
    </div>
    """, unsafe_allow_html=True)

    # Monthly volatility by crop
    vol = run_query("""
        SELECT crop,
               DATE_TRUNC('month', date) AS month,
               ROUND(STDDEV(modal_price), 2) AS price_stddev,
               ROUND(AVG(modal_price), 2) AS avg_price,
               ROUND(STDDEV(modal_price) / NULLIF(AVG(modal_price), 0) * 100, 2) AS cv_pct,
               COUNT(*) AS observations
        FROM fact_prices
        WHERE modal_price IS NOT NULL AND date IS NOT NULL AND crop IS NOT NULL
        GROUP BY crop, DATE_TRUNC('month', date)
        HAVING COUNT(*) >= 5
        ORDER BY month, crop
    """)

    if not vol.empty:
        vol["month_str"] = vol["month"].dt.strftime("%Y-%m")

        # Heatmap: Crop × Month with CV%
        pivot = vol.pivot_table(index="crop", columns="month_str", values="cv_pct", aggfunc="first")

        fig = px.imshow(pivot, color_continuous_scale="YlOrRd", aspect="auto",
                       labels=dict(x="Month", y="Crop", color="CV%"))
        fig.update_layout(**PLOTLY_LAYOUT, height=350,
                         title="Price Coefficient of Variation (%) — Crop × Month",
                         xaxis=dict(tickangle=45))
        st.plotly_chart(fig, use_container_width=True)

        # Volatility ranking
        st.markdown('<div class="section-header">📊 Overall Crop Volatility Ranking</div>', unsafe_allow_html=True)
        overall = run_query("""
            SELECT crop,
                   ROUND(STDDEV(modal_price), 2) AS std_dev,
                   ROUND(AVG(modal_price), 2) AS avg_price,
                   ROUND(STDDEV(modal_price) / NULLIF(AVG(modal_price), 0) * 100, 2) AS cv_pct,
                   ROUND(MIN(modal_price), 2) AS min_price,
                   ROUND(MAX(modal_price), 2) AS max_price,
                   ROUND(MAX(modal_price) - MIN(modal_price), 2) AS range
            FROM fact_prices WHERE modal_price IS NOT NULL AND crop IS NOT NULL
            GROUP BY crop ORDER BY cv_pct DESC
        """)

        if not overall.empty:
            fig = px.bar(overall, x="crop", y="cv_pct", color="cv_pct",
                        color_continuous_scale="YlOrRd", text="cv_pct",
                        labels={"cv_pct": "Coefficient of Variation (%)", "crop": ""})
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(**PLOTLY_LAYOUT, height=380, showlegend=False,
                             title="Price Volatility by Crop (higher = riskier)")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(overall, use_container_width=True, hide_index=True)

        # Box plot
        st.markdown('<div class="section-header">📦 Price Distribution by Crop</div>', unsafe_allow_html=True)
        box_data = run_query("""
            SELECT crop, modal_price FROM fact_prices
            WHERE modal_price IS NOT NULL AND crop IS NOT NULL
        """)
        if not box_data.empty:
            fig = px.box(box_data, x="crop", y="modal_price", color="crop",
                        color_discrete_sequence=COLORS,
                        labels={"modal_price": "Modal Price (₹)", "crop": ""})
            fig.update_layout(**PLOTLY_LAYOUT, height=400, showlegend=False,
                             title="Price Distribution (Box Plot)")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 7: Transport & Logistics
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚛 Transport & Logistics":
    st.markdown("# 🚛 Transport & Logistics")
    st.markdown("*Monitor transit performance, identify bottlenecks, and optimize delivery routes*")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">⏱️ Avg Transit Time by Destination</div>', unsafe_allow_html=True)
        t_avg = run_query("""
            SELECT destination, ROUND(AVG(transit_hours), 2) AS avg_hours
            FROM fact_transport WHERE transit_hours IS NOT NULL AND transit_hours >= 0
            GROUP BY destination ORDER BY avg_hours DESC
        """)
        if not t_avg.empty:
            fig = px.bar(t_avg, x="destination", y="avg_hours", color="avg_hours",
                        color_continuous_scale="Blues", text="avg_hours",
                        labels={"avg_hours": "Avg Hours", "destination": ""})
            fig.update_traces(texttemplate='%{text:.1f}h', textposition='outside')
            fig.update_layout(**PLOTLY_LAYOUT, height=400)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">🚨 Delay Rate by Destination</div>', unsafe_allow_html=True)
        d_rate = run_query("""
            SELECT destination,
                   ROUND(AVG(CASE WHEN is_delayed THEN 1.0 ELSE 0.0 END) * 100, 1) AS delay_pct
            FROM fact_transport GROUP BY destination ORDER BY delay_pct DESC
        """)
        if not d_rate.empty:
            fig = px.bar(d_rate, x="destination", y="delay_pct", color="delay_pct",
                        color_continuous_scale="Reds", text="delay_pct",
                        labels={"delay_pct": "Delay %", "destination": ""})
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(**PLOTLY_LAYOUT, height=400)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">🐢 Top 20 Worst Delays</div>', unsafe_allow_html=True)
    worst = run_query("""
        SELECT t.trip_id, m.mandi_name, m.district, t.destination,
               ROUND(t.transit_hours, 2) AS hours, ROUND(t.distance_km, 1) AS km,
               ROUND(t.distance_km / 40.0, 2) AS expected_h,
               ROUND(t.transit_hours - t.distance_km / 40.0, 2) AS excess_h
        FROM fact_transport t LEFT JOIN dim_mandi m USING (mandi_id)
        WHERE t.is_delayed AND t.transit_hours IS NOT NULL
        ORDER BY excess_h DESC LIMIT 20
    """)
    if not worst.empty:
        st.dataframe(worst, use_container_width=True, height=400)

    # Transit hours distribution
    st.markdown('<div class="section-header">📊 Transit Hours Distribution</div>', unsafe_allow_html=True)
    th = run_query("SELECT transit_hours FROM fact_transport WHERE transit_hours > 0 AND transit_hours < 50")
    if not th.empty:
        fig = px.histogram(th, x="transit_hours", nbins=50, color_discrete_sequence=["#4fd1c5"],
                          labels={"transit_hours": "Transit Hours"})
        fig.update_layout(**PLOTLY_LAYOUT, height=350, title="Transit Time Distribution")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 8: Weather Impact
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🌧️ Weather Impact":
    st.markdown("# 🌧️ Weather Impact on Supply Chain")
    st.markdown("*Analyze how rainfall and temperature affect crop arrivals nationally*")

    corr_r = run_query("""
        SELECT corr(a.total_qtl, w.total_rainfall_mm) AS rain_corr
        FROM (SELECT date, SUM(arrival_qtl) AS total_qtl FROM fact_arrivals GROUP BY date) a
        JOIN fact_weather_daily w USING (date)
    """)
    temp_r = run_query("""
        SELECT corr(a.total_qtl, w.avg_temp_c) AS temp_corr
        FROM (SELECT date, SUM(arrival_qtl) AS total_qtl FROM fact_arrivals GROUP BY date) a
        JOIN fact_weather_daily w USING (date)
    """)
    rain_c = corr_r.iloc[0, 0] if not corr_r.empty else None
    temp_c = temp_r.iloc[0, 0] if not temp_r.empty else None
    w_days = run_query("SELECT COUNT(*) FROM fact_weather_daily").iloc[0, 0]

    cols = st.columns(3)
    with cols[0]:
        kpi_card("Rainfall ↔ Arrivals", f"{rain_c:.4f}" if rain_c else "N/A", "Pearson r")
    with cols[1]:
        kpi_card("Temp ↔ Arrivals", f"{temp_c:.4f}" if temp_c else "N/A", "Pearson r")
    with cols[2]:
        kpi_card("Weather Days", f"{w_days:,}", "Unique daily aggregates")

    weather = run_query("""
        SELECT w.date, w.total_rainfall_mm, w.avg_temp_c, w.avg_humidity_pct,
               COALESCE(a.total_qtl, 0) AS total_qtl
        FROM fact_weather_daily w
        LEFT JOIN (SELECT date, SUM(arrival_qtl) AS total_qtl FROM fact_arrivals GROUP BY date) a USING (date)
        ORDER BY w.date
    """)

    if not weather.empty:
        st.markdown('<div class="section-header">🌧️ Rainfall vs Arrivals (Dual Axis)</div>', unsafe_allow_html=True)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=weather["date"], y=weather["total_rainfall_mm"],
                            name="Rainfall (mm)", marker_color="rgba(99,179,237,0.35)"), secondary_y=False)
        fig.add_trace(go.Scatter(x=weather["date"], y=weather["total_qtl"],
                                name="Arrivals (Qtl)", line=dict(color="#f6ad55", width=2.5)),
                     secondary_y=True)
        fig.update_layout(**PLOTLY_LAYOUT, height=420, title="Daily Rainfall vs National Arrivals")
        fig.update_yaxes(title_text="Rainfall (mm)", secondary_y=False)
        fig.update_yaxes(title_text="Arrivals (Qtl)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-header">🌡️ Temperature Trend</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=weather["date"], y=weather["avg_temp_c"],
                                    name="Avg Temp °C", line=dict(color="#fc8181", width=2),
                                    fill='tozeroy', fillcolor='rgba(252,129,129,0.08)'))
            fig.update_layout(**PLOTLY_LAYOUT, height=330)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">📊 Rainfall vs Arrivals (Scatter)</div>', unsafe_allow_html=True)
            fig = px.scatter(weather, x="total_rainfall_mm", y="total_qtl",
                            color="avg_temp_c", color_continuous_scale="RdYlBu_r",
                            labels={"total_rainfall_mm": "Rainfall (mm)", "total_qtl": "Arrivals (Qtl)"})
            fig.update_layout(**PLOTLY_LAYOUT, height=330,
                             title=f"r = {rain_c:.4f}" if rain_c else "")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 9: Data Quality
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Data Quality":
    st.markdown("# 🔍 Data Quality & Governance")
    st.markdown("*Full pipeline transparency — every assumption documented, every transformation logged*")

    st.markdown("""
    <div class="info-box">
        <strong>🏗️ Pipeline Reproducibility:</strong> Run <code>python src/clean.py</code> then
        <code>python src/build_warehouse.py</code> to regenerate the entire warehouse from raw data.
        Every cleaning decision is documented below with exact row counts.
    </div>
    """, unsafe_allow_html=True)

    # Row counts
    st.markdown('<div class="section-header">📊 Table Row Counts (Before → After)</div>', unsafe_allow_html=True)
    tables = {
        "dim_mandi": ("60 (3 duplicates)", "SELECT COUNT(*) FROM dim_mandi"),
        "fact_arrivals": ("25,750", "SELECT COUNT(*) FROM fact_arrivals"),
        "fact_prices": ("12,000", "SELECT COUNT(*) FROM fact_prices"),
        "fact_transport": ("10,400", "SELECT COUNT(*) FROM fact_transport"),
        "fact_weather_daily": ("15,000 sensor readings", "SELECT COUNT(*) FROM fact_weather_daily"),
    }
    tdata = []
    for n, (r, s) in tables.items():
        f = run_query(s).iloc[0, 0]
        tdata.append({"Table": n, "Raw Input": r, "Final Output": f"{f:,}"})
    st.dataframe(pd.DataFrame(tdata), use_container_width=True, hide_index=True)

    # Join success
    st.markdown('<div class="section-header">🔗 Join Success Rates</div>', unsafe_allow_html=True)
    jdata = []
    for t in ["fact_arrivals", "fact_prices", "fact_transport"]:
        total = run_query(f"SELECT COUNT(*) FROM {t}").iloc[0, 0]
        joined = run_query(f"SELECT COUNT(*) FROM {t} WHERE mandi_id IN (SELECT mandi_id FROM dim_mandi)").iloc[0, 0]
        rate = joined / total * 100 if total else 0
        jdata.append({"Table": t, "Total": f"{total:,}", "Joined": f"{joined:,}", "Rate": f"{rate:.1f}%"})
    st.dataframe(pd.DataFrame(jdata), use_container_width=True, hide_index=True)

    # Flags
    st.markdown('<div class="section-header">🏷️ Data Quality Flags</div>', unsafe_allow_html=True)
    flags = [
        ("fact_arrivals", "qty_was_corrected",
         run_query("SELECT SUM(CASE WHEN qty_was_corrected THEN 1 ELSE 0 END) FROM fact_arrivals").iloc[0,0],
         "Negative quantities → abs()"),
        ("fact_transport", "transit_hours_was_recalculated",
         run_query("SELECT SUM(CASE WHEN transit_hours_was_recalculated THEN 1 ELSE 0 END) FROM fact_transport").iloc[0,0],
         "Recomputed from timestamps"),
        ("fact_transport", "is_delayed",
         run_query("SELECT SUM(CASE WHEN is_delayed THEN 1 ELSE 0 END) FROM fact_transport").iloc[0,0],
         "Transit > 1.5× expected"),
        ("fact_prices", "below_msp",
         run_query("SELECT SUM(CASE WHEN below_msp THEN 1 ELSE 0 END) FROM fact_prices").iloc[0,0],
         "Modal price < MSP"),
    ]
    st.dataframe(pd.DataFrame([{"Table": t, "Flag": f, "Count": f"{c:,}", "Meaning": m}
                                for t, f, c, m in flags]),
                 use_container_width=True, hide_index=True)

    # Assumptions
    st.markdown('<div class="section-header">📝 Documented Assumptions</div>', unsafe_allow_html=True)
    st.markdown("""
    | # | Assumption | Justification |
    |:---:|---|---|
    | 1 | Missing quantity unit → Quintal | Most common unit (~70%) |
    | 2 | Negative arrivals → abs() | Physical impossibility; sign-entry error |
    | 3 | Missing distance_unit → km | Majority case |
    | 4 | Temperature > 50 with no unit → Fahrenheit | India never exceeds 50°C |
    | 5 | Negative rainfall → clip to 0 | Physically impossible |
    | 6 | Ambiguous DD/MM → dayfirst=True | India convention |
    | 7 | No timezone suffix → IST | India-based dataset |
    | 8 | Weather → national daily aggregate | No sensor-district mapping |
    | 9 | Delay: > 1.5× (distance/40 km/h) | 40 km/h avg truck speed |
    | 10 | mandi_name ≠ geography | Names randomized in dataset |
    """)

    # Show full report
    rp = Path(__file__).parent / "reports" / "data_quality_report.md"
    if rp.exists():
        with st.expander("📄 Full Auto-Generated Data Quality Report"):
            with open(rp, "r", encoding="utf-8") as f:
                st.markdown(f.read())


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 10: AI Agent
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Agent":
    st.markdown("# 🤖 AI-Powered Query Agent")
    st.markdown("*Ask questions in natural language → LLM generates SQL → executes on DuckDB → auto-visualizes*")

    st.markdown("""
    <div class="info-box">
        <strong>🧠 How it works:</strong>
        <ol style="margin: 0.5rem 0; padding-left: 1.2rem; color: #cbd5e1;">
            <li>Your question goes to <strong>Llama 3.3 70B</strong> (via Groq, free tier)</li>
            <li>The LLM generates SQL against our exact DuckDB schema</li>
            <li><strong>Guardrail:</strong> SQL is validated — DROP/DELETE/UPDATE are rejected</li>
            <li>SQL executes on DuckDB warehouse</li>
            <li><strong>Smart chart selection:</strong> keywords like "trend" → line, "compare" → bar, "correlation" → scatter</li>
            <li>Results rendered via Plotly</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box success">
        <strong>💡 Try these questions:</strong><br/>
        <code>Show total arrivals by crop type</code><br/>
        <code>Which mandi has the highest average transit delay?</code><br/>
        <code>Show the distribution of wholesale prices for Rice</code><br/>
        <code>Which warehouse receives the highest volume of crops?</code><br/>
        <code>Plot the daily arrival trend of Wheat</code><br/>
        <code>Compare average modal price vs MSP for each crop</code>
    </div>
    """, unsafe_allow_html=True)

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "chart" in msg and msg["chart"] is not None:
                st.plotly_chart(msg["chart"], use_container_width=True)
            if "dataframe" in msg and msg["dataframe"] is not None:
                st.dataframe(msg["dataframe"], use_container_width=True)
            if "sql" in msg and msg["sql"]:
                with st.expander("🔍 Generated SQL"):
                    st.code(msg["sql"], language="sql")

    if prompt := st.chat_input("Ask a question about the mandi supply chain data..."):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🧠 Generating SQL & analyzing..."):
                from agent import ask_agent
                result = ask_agent(prompt)

            st.markdown(result["answer_text"])
            msg_data = {"role": "assistant", "content": result["answer_text"]}

            if result["sql"]:
                msg_data["sql"] = result["sql"]
                with st.expander("🔍 Generated SQL"):
                    st.code(result["sql"], language="sql")

            if result["dataframe"] is not None and not result["dataframe"].empty:
                df = result["dataframe"]
                chart_type = result["chart_type"]
                fig = None

                try:
                    if chart_type == "line" and len(df.columns) >= 2:
                        x_col = df.columns[0]
                        fig = go.Figure()
                        for i, col in enumerate(df.columns[1:]):
                            fig.add_trace(go.Scatter(x=df[x_col], y=df[col], name=col,
                                                    line=dict(color=COLORS[i % len(COLORS)], width=2.5)))

                    elif chart_type == "bar" and len(df.columns) >= 2:
                        fig = px.bar(df, x=df.columns[0], y=df.columns[1],
                                    color_discrete_sequence=COLORS)

                    elif chart_type == "scatter" and len(df.columns) >= 2:
                        fig = px.scatter(df, x=df.columns[0], y=df.columns[1],
                                        color_discrete_sequence=COLORS)

                    if fig:
                        fig.update_layout(**PLOTLY_LAYOUT, height=400)
                        st.plotly_chart(fig, use_container_width=True)
                        msg_data["chart"] = fig

                except Exception as e:
                    st.warning(f"Chart rendering: {e}")
                    msg_data["chart"] = None

                st.dataframe(df, use_container_width=True)
                msg_data["dataframe"] = df
            else:
                msg_data["chart"] = None
                msg_data["dataframe"] = None

            st.session_state.agent_messages.append(msg_data)
