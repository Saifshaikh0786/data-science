# 🌾 Mandi-to-Market Supply Chain Optimizer

> **TransOrg AgentIQ Datathon 2026** · Agriculture & FoodTech Track  
> An enterprise-grade agricultural supply chain intelligence platform — from raw messy data to agentic AI insights.

---

## 🏆 How We Satisfy All 4 Challenge Layers

| Layer | Requirement | Our Implementation |
|:---:|---|---|
| **1** | Data Rescue | `src/clean.py` — 5 files, 30+ transformations, full QA audit trail |
| **2** | Analytics Layer | `src/build_warehouse.py` — DuckDB star schema, 9 business metrics |
| **3** | Executive Dashboard | `app.py` — 10-page Streamlit dashboard with premium UI |
| **4 ★** | Agentic Graph AI | `src/agent.py` — NL→SQL→Chart with Groq+Gemini, 6/6 tests pass |

---

## ✨ Unique Features (What Sets Us Apart)

### 📡 Farmer Advisory System
Answers the core question every farmer has: **"Where should I sell my crop today?"**
- Ranks all mandis by today's modal price for any selected crop
- Shows MSP gap (profitable vs. distress sale), exact ₹ savings vs worst mandi
- 7-day price history for top 3 mandis

### 🌐 Supply Chain Sankey Flow
- Visual flow diagram from mandi districts → destination warehouses
- Shows trip volume on each route — instantly identifies bottlenecks

### 🔥 Price Volatility Heatmap
- Crop × Month coefficient of variation matrix
- Identifies the riskiest crop-season combinations for policy intervention
- Box plot distribution for outlier detection

### 📈 Arbitrage Explorer
- Cross-mandi price spread on any given crop + date
- Instantly shows best buying mandi, worst mandi, and ₹/Qtl opportunity

### 🤖 AI Agent with Dual LLM Fallback
- **Primary:** Groq `gpt-oss-120b` (ultra-fast inference)
- **Fallback:** Google `Gemini-2.0-Flash` (if Groq is unavailable)
- SQL guardrails reject dangerous DDL/DML operations
- DuckDB-aware prompt prevents use of unsupported functions
- Auto-selects chart type (line/bar/scatter/table) from question keywords

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     10-PAGE STREAMLIT DASHBOARD                     │
│  Executive Overview  │  Price & MSP Watch  │  Arbitrage Explorer   │
│  Farmer Advisory ★  │  Supply Chain Flow ★ │  Price Volatility ★  │
│  Transport Logistics │  Weather Impact     │  Data Quality          │
│                     🤖 AI Agent (Layer 4)                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ DuckDB SQL
                     ┌────────▼────────┐
                     │  warehouse.duckdb │
                     │  ┌─────────────┐ │
                     │  │ dim_mandi   │ │  57 rows
                     │  │ fact_arrive │ │  25,750 rows
                     │  │ fact_prices │ │  12,000 rows
                     │  │ fact_transp │ │  10,400 rows
                     │  │ fact_weather│ │  252 daily agg
                     │  └─────────────┘ │
                     └────────▲────────┘
                              │ Parquet load
               ┌──────────────┴──────────────┐
               │   src/clean.py               │
               │   Data Cleaning Pipeline     │
               └──────────────▲───────────────┘
                              │
               ┌──────────────┴──────────────┐
               │   data/raw/ (5 files)        │
               │   CSV · JSON · XLSX          │
               └─────────────────────────────┘
```

---

## 📊 Data Cleaning — What We Fixed

| Table | Raw Rows | Final Rows | Key Transformations |
|---|---|---|---|
| dim_mandi | 60 | 57 | 3 exact duplicates removed; 36 mandi_id format variants → canonical `MANDIXXX`; state backfilled from district lookup |
| fact_arrivals | 25,750 | 25,750 | 36 crop name variants → 6 canonical; 1,261 negative quantities corrected (abs); 484 missing arrival_ids generated |
| fact_prices | 12,000 | 12,000 | Currency strings (`₹`, `Rs`, `INR`) stripped; 3,667 below-MSP events flagged |
| fact_transport | 10,400 | 10,400 | 1,440 transit hours recomputed from timestamps; 1,553 miles→km conversions; 81 delayed trips flagged |
| fact_weather_daily | 15,000 | 252 | 715 UNKNOWN sensors excluded; 1,484 bad timestamps dropped; 1,281 negative rainfalls clipped; aggregated to national daily |

### Documented Assumptions (10 Total)
1. Missing quantity unit → Quintal (India convention, most common ~70%)
2. Negative arrivals → abs() (physical impossibility, sign-entry error)
3. Missing distance_unit → km (majority case)
4. Temperature > 50 with no unit → Fahrenheit → converted to °C
5. Negative rainfall → clip to 0 (physically impossible)
6. Ambiguous DD/MM date → dayfirst=True (India convention)
7. No timezone suffix → IST (India-based dataset)
8. Weather → national daily aggregate (no sensor-district mapping provided)
9. Delay threshold: transit > 1.5× (distance / 40 km/h)
10. mandi_name ≠ geography (names are randomized flavor text in this dataset)

---

## 📈 Business Metrics Delivered

| Metric | Value |
|---|---|
| Total national arrivals | 6,417,738 Qtl |
| Avg modal price vs MSP gap | +₹82.59/Qtl |
| Price crash instances (below MSP) | 3,667 |
| Transport delay rate | 0.8% |
| Active mandis | 57 |
| Join success rate (arrivals) | 100% |

---

## 🚀 Quick Start

### Prerequisites
```powershell
pip install -r requirements.txt
```

### 1. Run the cleaning pipeline
```powershell
python src/clean.py
```

### 2. Build the warehouse
```powershell
python src/build_warehouse.py
```

### 3. Launch the dashboard
```powershell
streamlit run app.py
```
Dashboard opens at **http://localhost:8501**

### 4. Configure AI Agent (optional but recommended)
```powershell
# Copy template
copy .env.example .env
# Edit .env and add your Groq key (free at https://console.groq.com)
# GROQ_API_KEY=gsk_your_key_here
```

### 5. Run acceptance tests
```powershell
python test_agent.py   # All 6/6 pass
```

---

## 🤖 AI Agent — How It Works

```
User question (natural language)
        ↓
Keyword analysis → chart_type hint (line/bar/scatter/table)
        ↓
LLM call (Groq primary → Google Gemini fallback)
  [Schema context + DuckDB SQL rules injected]
        ↓
JSON parse → {sql, chart_type, explanation}
        ↓
SQL Guardrail (DROP/DELETE/UPDATE → rejected)
        ↓
DuckDB execution → DataFrame
        ↓
Plotly chart + data table rendered in Streamlit
```

**Acceptance Test Results (Section 7):**
| # | Question | Status | Chart |
|:---:|---|:---:|---|
| 1 | Show total arrivals by crop type | ✅ PASS | Bar |
| 2 | Which mandi has the highest average transit delay? | ✅ PASS | Bar |
| 3 | Show the distribution of wholesale prices for Rice | ✅ PASS | Bar |
| 4 | Which warehouse receives the highest volume of crops? | ✅ PASS | Bar |
| 5 | Plot the daily arrival trend of Wheat | ✅ PASS | Line |
| 6 | Compare average modal price vs MSP for each crop | ✅ PASS | Bar |

---

## 📁 Project Structure

```
mandi-supply-chain-optimizer/
├── app.py                      # 10-page Streamlit dashboard
├── requirements.txt            # All Python dependencies
├── .env.example                # API key template (copy → .env)
├── test_agent.py               # 6-question acceptance test suite
│
├── src/
│   ├── agent.py                # NL→SQL→Chart AI Agent
│   ├── clean.py                # Data cleaning pipeline
│   ├── build_warehouse.py      # DuckDB warehouse builder
│   ├── metrics.sql             # Business metric queries
│   └── utils.py                # Shared parsers & utilities
│
├── data/
│   └── raw/                    # Original 5 messy input files
│       ├── track3_mandi_master.csv
│       ├── track3_mandi_arrivals.csv
│       ├── track3_price_and_msp.json
│       ├── track3_transport_logistics.csv
│       └── track3_weather_sensors.xlsx
│
└── reports/
    └── data_quality_report.md  # Auto-generated QA report
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Data Cleaning | Python, Pandas, python-dateutil |
| Data Warehouse | DuckDB (in-process analytical DB) |
| Serialization | Apache Parquet (via PyArrow) |
| Dashboard | Streamlit + Plotly |
| AI Agent | OpenAI-compatible API (Groq + Google Gemini) |
| LLM Models | Groq `openai/gpt-oss-120b` · Google `gemini-2.0-flash` |

---

*Built for TransOrg AgentIQ Datathon 2026 — Agriculture & FoodTech Track*
