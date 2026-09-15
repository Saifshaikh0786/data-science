"""
Agentic Graph AI — Section 7 / Layer 4 (Bonus)
Enterprise-grade NL → SQL → Chart agent with:
  • Multi-provider LLM support (Groq primary, Google Gemini fallback)
  • Automatic retry with provider failover
  • SQL guardrails (dangerous DDL/DML rejected)
  • DuckDB-aware schema context
  • Keyword-based chart type override
  • Rich narrative answer generation
"""

import os
import re
import json
import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "warehouse.duckdb"

# ── Schema context for the LLM ──────────────────────────────────────────────
SCHEMA_PROMPT = """You are a SQL assistant for an agricultural supply chain data warehouse stored in DuckDB.
You ONLY have access to these tables and columns — never invent a column or table name:

TABLE dim_mandi:
  mandi_id TEXT (PK, format 'MANDIXXX'), mandi_name TEXT, district TEXT, state TEXT, mandi_type TEXT, total_area_acres DOUBLE

TABLE fact_arrivals:
  arrival_id TEXT, date DATE, mandi_id TEXT (FK→dim_mandi), crop TEXT, variety TEXT, arrival_qtl DOUBLE, farmer_count DOUBLE, qty_was_corrected BOOLEAN

TABLE fact_prices:
  record_id TEXT, date DATE, mandi_id TEXT (FK→dim_mandi), district TEXT, crop TEXT, min_price DOUBLE, max_price DOUBLE, modal_price DOUBLE, msp DOUBLE, below_msp BOOLEAN

TABLE fact_transport:
  trip_id TEXT, mandi_id TEXT (FK→dim_mandi), destination TEXT, departure_ts TIMESTAMP, arrival_ts TIMESTAMP, transit_hours DOUBLE, distance_km DOUBLE, vehicle_no TEXT, driver_id TEXT, transit_hours_was_recalculated BOOLEAN, is_delayed BOOLEAN

TABLE fact_weather_daily:
  date DATE, avg_temp_c DOUBLE, total_rainfall_mm DOUBLE, avg_humidity_pct DOUBLE

IMPORTANT DOMAIN NOTES:
- The 6 crops are: Wheat, Rice, Cotton, Sugarcane, Maize, Mustard
- The 6 destinations are: WH-Central, WH-West, WH-South, WH-North, WH-East, Export-Terminal
- Weather data is national daily aggregate only (no district column in fact_weather_daily)
- mandi_name is NOT a reliable geography indicator — use district/state columns for location queries
- To find a mandi by name (e.g. "Amritsar mandi"), search dim_mandi.mandi_name ILIKE '%Amritsar%'
- Use ILIKE for case-insensitive text matching
- Dates are in the range of 2026 (synthetic data)
- "arrivals" means quantity of produce arriving at mandis measured in Quintals (arrival_qtl)
- "price crash" means modal_price < msp (below_msp = true)
- "delay" means transit time exceeded 1.5x expected (is_delayed = true)
- For "warehouse" questions, the warehouse is the destination in fact_transport

DuckDB SQL RULES (CRITICAL — follow exactly):
- DuckDB does NOT have width_bucket(). For distributions/histograms, use: FLOOR(column / bin_size) * bin_size AS bin
- DuckDB does NOT have MEDIAN(). Use PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY column) instead
- Use DATE_TRUNC('month', date) for monthly aggregation
- Use EXTRACT(DOW FROM date) for day-of-week
- String aggregation: use STRING_AGG(column, ', ')
- For LIMIT queries, use LIMIT N (not TOP N)
- Use ROUND() for cleaner numeric output

Reply with ONLY valid JSON (no markdown, no explanation outside JSON):
{"sql": "YOUR SQL QUERY", "chart_type": "line|bar|scatter|table", "explanation": "2-3 sentence business insight explaining the result"}
"""

# ── Dangerous SQL patterns to reject ─────────────────────────────────────────
DANGEROUS_PATTERNS = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|ATTACH|PRAGMA|CREATE|ALTER|TRUNCATE|COPY|EXPORT|IMPORT)\b|;--|\/\*',
    re.IGNORECASE
)

# ── Keyword → chart_type overrides ───────────────────────────────────────────
CHART_OVERRIDES = [
    (r'trend|over time|daily|monthly|weekly|timeline', 'line'),
    (r'compare|top|vs|versus|ranking|rank|highest|lowest|best|worst', 'bar'),
    (r'relationship|correlation|corr|impact|effect', 'scatter'),
    (r'distribution|spread|histogram|range', 'bar'),
    (r'share|proportion|percentage|breakdown|composition', 'bar'),
    (r'flow|route|path', 'bar'),
]


def _get_providers():
    """Return a list of (provider_name, call_fn) tuples in priority order."""
    providers = []

    groq_key = os.environ.get("GROQ_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if not groq_key or not google_key:
        try:
            import streamlit as _st
            if not groq_key and hasattr(_st, "secrets") and "GROQ_API_KEY" in _st.secrets:
                groq_key = _st.secrets["GROQ_API_KEY"]
            if not google_key and hasattr(_st, "secrets") and "GOOGLE_API_KEY" in _st.secrets:
                google_key = _st.secrets["GOOGLE_API_KEY"]
        except Exception:
            pass

    if groq_key:
        def call_groq(question):
            from openai import OpenAI
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            resp = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": SCHEMA_PROMPT},
                    {"role": "user", "content": question}
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            return resp.choices[0].message.content
        providers.append(("Groq/gpt-oss-120b", call_groq))

    if google_key:
        def call_google(question):
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            resp = model.generate_content(f"{SCHEMA_PROMPT}\n\nUser question: {question}")
            return resp.text
        providers.append(("Google/Gemini-2.0-Flash", call_google))

    return providers


def _parse_llm_json(raw: str):
    """Extract JSON from LLM response, handling markdown fences and edge cases."""
    cleaned = raw.strip()
    # Strip markdown code fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    # Try to find JSON object if there's surrounding text
    match = re.search(r'\{[^{}]*"sql"[^{}]*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def ask_agent(question: str):
    """
    Send a natural language question to the LLM, get SQL + chart_type back,
    execute it, return results.

    Returns dict: {answer_text, chart_type, sql, dataframe, error}
    """
    providers = _get_providers()

    if not providers:
        return {
            "answer_text": "⚠️ No API key configured. Set GROQ_API_KEY or GOOGLE_API_KEY in .env",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": "no_api_key"
        }

    # ── Try each provider with retry ─────────────────────────────────────
    last_error = None
    raw_response = None

    for provider_name, call_fn in providers:
        for attempt in range(2):  # 2 attempts per provider
            try:
                raw_response = call_fn(question)
                break  # success
            except Exception as e:
                last_error = f"{provider_name} attempt {attempt+1}: {str(e)}"
                continue
        if raw_response:
            break

    if raw_response is None:
        return {
            "answer_text": f"⚠️ All LLM providers failed.\n\nLast error: {last_error}",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": last_error
        }

    # ── Parse JSON response ──────────────────────────────────────────────
    try:
        parsed = _parse_llm_json(raw_response)
        sql = parsed.get("sql", "")
        chart_type = parsed.get("chart_type", "table")
        explanation = parsed.get("explanation", "")
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "answer_text": f"⚠️ Could not parse LLM response.\n\nRaw:\n{raw_response[:500]}",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": f"json_parse_error: {e}"
        }

    # ── Guardrail: reject dangerous SQL ──────────────────────────────────
    if DANGEROUS_PATTERNS.search(sql):
        return {
            "answer_text": "🚫 Generated SQL contains dangerous operations (DDL/DML) and was rejected for safety.",
            "chart_type": "table",
            "sql": sql,
            "dataframe": None,
            "error": "dangerous_sql"
        }

    # ── Keyword override for chart type ──────────────────────────────────
    q_lower = question.lower()
    for pattern, override in CHART_OVERRIDES:
        if re.search(pattern, q_lower):
            chart_type = override
            break

    # ── Execute SQL on DuckDB ────────────────────────────────────────────
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute(sql).fetchdf()
        con.close()
    except Exception as e:
        return {
            "answer_text": f"⚠️ SQL execution error: {str(e)}\n\n**Generated SQL:**\n```sql\n{sql}\n```",
            "chart_type": "table",
            "sql": sql,
            "dataframe": None,
            "error": str(e)
        }

    # ── Build rich answer text ───────────────────────────────────────────
    answer_parts = []
    if explanation:
        answer_parts.append(explanation)

    # Add data summary
    if df is not None and not df.empty:
        rows, cols = df.shape
        answer_parts.append(f"📊 **Result:** {rows} row{'s' if rows != 1 else ''}, {cols} column{'s' if cols != 1 else ''}")

        # Auto-summarize if small result
        if rows == 1 and cols <= 3:
            vals = [f"**{c}**: {df.iloc[0][c]}" for c in df.columns]
            answer_parts.append(" · ".join(vals))
        elif rows <= 6 and cols == 2:
            # Compact summary for small multi-row results
            col0, col1 = df.columns[0], df.columns[1]
            top_val = df.iloc[0]
            answer_parts.append(f"🏆 Top: **{top_val[col0]}** = {top_val[col1]}")

    return {
        "answer_text": "\n\n".join(answer_parts) if answer_parts else "Query executed successfully.",
        "chart_type": chart_type,
        "sql": sql,
        "dataframe": df,
        "error": None
    }
