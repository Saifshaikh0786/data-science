# 🌾 Mandi-to-Market Supply Chain Optimizer

> **TransOrg AgentIQ Datathon** · Agriculture & FoodTech Track  
> An intelligent agricultural supply chain analytics platform that transforms messy mandi data into actionable price discovery, logistics optimization, and weather impact insights.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT DASHBOARD                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │Executive │ │Price &   │ │Arbitrage │ │Transport │ │Weather   │ │
│  │Overview  │ │MSP Watch │ │Explorer  │ │Logistics │ │Impact    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────────────────┐  ┌───────────────────────────────────┐   │
│  │ Data Quality &       │  │ 🤖 AI Agent (NL → SQL → Chart)  │   │
│  │ Governance Dashboard │  │ Groq/Google LLM + SQL Guardrails │   │
│  └──────────────────────┘  └───────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ SQL Queries
                         ┌────────▼────────┐
                         │   DuckDB        │
                         │   Warehouse     │
                         │ ┌─────────────┐ │
                         │ │ dim_mandi   │ │
                         │ │ fact_arrive │ │
                         │ │ fact_prices │ │
                         │ │ fact_transp │ │
                         │ │ fact_weather│ │
                         │ └─────────────┘ │
                         └────────▲────────┘
                                  │ Load cleaned parquet
                   ┌──────────────┴──────────────┐
                   │   DATA CLEANING PIPELINE    │
                   │   (src/clean.py)             │
                   │                              │
                   │  • Mandi ID Canonicalization │
                   │  • Crop Name Normalization   │
                   │  • Unit Conversion (→ Qtl)   │
                   │  • Price String Parsing      │
                   │  • Messy Date Parsing        │
                   │  • Timezone Normalization    │
                   │  • Quality Flag Generation   │
                   └──────────────▲───────────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   │   RAW DATA (5 files)         │
                   │   CSV, JSON, XLSX            │
                   └──────────────────────────────┘
```

## 📊 Data Model

| Table | Type | Description |
|---|---|---|
| `dim_mandi` | Dimension | 57 unique mandis with district, state, type |
| `fact_arrivals` | Fact | 25,750 daily crop arrival records (normalized to Quintals) |
| `fact_prices` | Fact | 12,000 price records with MSP comparison |
| `fact_transport` | Fact | 10,400 truck trip records with delay detection |
| `fact_weather_daily` | Fact | National daily weather aggregate |

### Key Business Metrics
1. **Total crop arrivals** by crop and mandi
2. **Average modal price vs MSP** gap analysis
3. **Price crash detection** (modal price < MSP)
4. **Transit delay rate** by destination warehouse
5. **Weather-arrival correlation** (rainfall impact on supply)
6. **Price arbitrage score** — the hero metric for farmer decision support

## 🧹 Data Cleaning Highlights

The raw data is deliberately messy. Our pipeline handles:

- **36 crop name variants** (English/Hindi/Punjabi/Unicode) → 6 canonical crops
- **8+ mandi_id formats** → standardized `MANDIXXX`
- **Mixed quantity units** (KG, Qtl, Tonnes) → all normalized to Quintals
- **Currency-embedded price strings** (`₹6,944.79`, `Rs. 1,857`, `INR 2,183`) → clean floats
- **12+ date/time formats** with mixed DD/MM vs MM/DD, IST/UTC timezones
- **Negative values** in arrivals (abs), rainfall (clip to 0), transit hours (recompute)
- **Temperature unit detection** including embedded units in values (`"39.8°C"`)
- **Full QA audit trail** — every transformation is logged with row counts

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- A free API key from [Groq](https://console.groq.com) (for the AI Agent)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/mandi-supply-chain-optimizer.git
cd mandi-supply-chain-optimizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 4. Run the data cleaning pipeline
python src/clean.py

# 5. Build the DuckDB warehouse
python src/build_warehouse.py

# 6. Launch the dashboard
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | For AI Agent | Free key from [console.groq.com](https://console.groq.com) |
| `GOOGLE_API_KEY` | Optional fallback | Free key from [aistudio.google.com](https://aistudio.google.com) |

## 📱 Dashboard Pages

### 1. Executive Overview
KPI cards (total arrivals, avg price-MSP gap, crash count, delay rate), daily arrival trend, crop-wise distribution, top mandis.

### 2. Price & MSP Watch
Modal price vs MSP comparison by crop, price trend over time, table of mandis currently below MSP.

### 3. Arbitrage Explorer ⭐
**The hero feature** — select a crop + date to see mandis ranked by price. Instantly identifies where a farmer should sell for the best price. Displays price spread, best/worst prices, and MSP status.

### 4. Transport & Logistics
Average transit time and delay rate by destination warehouse, worst-delay routes, distance distribution.

### 5. Weather Impact
National daily rainfall vs arrivals overlay, temperature trend, rainfall-arrival scatter plot with Pearson correlation coefficient.

### 6. Data Quality & Governance
Full transparency: before/after row counts, join success rates, data quality flags, all 10 documented assumptions with justification.

### 7. AI Agent 🤖
Natural language query interface powered by LLM (Groq). Ask questions like:
- "Show total arrivals by crop type"
- "Which warehouse receives the highest volume of crops?"
- "Show the distribution of wholesale prices for Rice"

SQL is generated, validated (dangerous patterns rejected), executed, and auto-visualized.

## 🔒 Design Decisions

| Decision | Rationale |
|---|---|
| **DuckDB (in-process)** | Zero infrastructure, fast analytical queries, perfect for single-machine datathon |
| **Natural keys (no surrogates)** | Faster to build; `mandi_id` is already a clean PK after canonicalization |
| **National weather aggregate only** | No sensor→district mapping exists; presenting district-level weather as ground truth would be dishonest |
| **Single-shot LLM agent** | Simpler, more reliable, cheaper than multi-step agent loops for this scope |
| **Delay threshold: 1.5× expected** | 40 km/h avg truck speed is a documented, defensible assumption |
| **mandi_name NOT used for geography** | Names are randomized in this synthetic dataset — only district/state columns are reliable |

## 📂 Repository Structure

```
mandi-supply-chain-optimizer/
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── .env.example                  # API key template
├── .gitignore
├── data/
│   └── raw/                      # Original 5 dataset files
├── src/
│   ├── utils.py                  # Shared parsers (dates, IDs, crops, prices)
│   ├── clean.py                  # Data cleaning pipeline
│   ├── build_warehouse.py        # DuckDB warehouse builder
│   ├── metrics.sql               # Business metric queries (Section 5)
│   └── agent.py                  # AI agent (NL → SQL → Chart)
├── app.py                        # Streamlit dashboard
├── reports/
│   └── data_quality_report.md    # Auto-generated QA report
└── warehouse.duckdb              # Generated (gitignored, rebuild via scripts)
```

## ⚖️ Compliance

- ✅ No external datasets used — only the provided 5 files
- ✅ No paid API keys required (Groq free tier)
- ✅ Full data quality report with every assumption documented
- ✅ Reproducible pipeline: `clean.py` → `build_warehouse.py` → `streamlit run app.py`

---

*Built for the TransOrg AgentIQ Datathon — Agriculture & FoodTech Track*
