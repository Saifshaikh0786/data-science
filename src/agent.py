"""
Smol Agent — Section 7 of the build spec.
Single-shot LLM call that generates SQL from natural language questions,
with guardrails and keyword-based chart type override.
"""

import os
import re
import json
import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "warehouse.duckdb"

# ── Schema context for the LLM ──
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

IMPORTANT NOTES:
- The 6 crops are: Wheat, Rice, Cotton, Sugarcane, Maize, Mustard
- The 6 destinations are: WH-Central, WH-West, WH-South, WH-North, WH-East, Export-Terminal
- Weather data is national daily aggregate only (no district column in fact_weather_daily)
- mandi_name is NOT a reliable geography indicator — use district/state columns for location queries
- To find a mandi by name (e.g. "Amritsar mandi"), search dim_mandi.mandi_name ILIKE '%Amritsar%'
- Use ILIKE for case-insensitive text matching
- Dates are in the range of 2026 (synthetic data)

DuckDB SQL RULES (CRITICAL — follow exactly):
- DuckDB does NOT have width_bucket(). For distributions/histograms, use: FLOOR(column / bin_size) * bin_size AS bin
- DuckDB does NOT have MEDIAN(). Use PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY column) instead
- Use DATE_TRUNC('month', date) for monthly aggregation
- Use EXTRACT(DOW FROM date) for day-of-week
- String aggregation: use STRING_AGG(column, ', ')
- For LIMIT queries, use LIMIT N (not TOP N)

Reply with ONLY valid JSON (no markdown, no explanation outside JSON):
{"sql": "YOUR SQL QUERY", "chart_type": "line|bar|scatter|table", "explanation": "brief explanation"}
"""

# ── Dangerous SQL patterns to reject ──
DANGEROUS_PATTERNS = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|ATTACH|PRAGMA|CREATE|ALTER|TRUNCATE)\b|;--',
    re.IGNORECASE
)

# ── Keyword → chart_type overrides ──
CHART_OVERRIDES = [
    (r'trend|over time|daily|monthly|weekly', 'line'),
    (r'compare|top|vs|versus|ranking', 'bar'),
    (r'relationship|correlation|corr', 'scatter'),
    (r'distribution|spread|histogram', 'bar'),
]


def get_llm_client():
    """Get an OpenAI-compatible client (Groq primary, Google fallback)."""
    groq_key = os.environ.get("GROQ_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if groq_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            return client, "openai/gpt-oss-120b"
        except Exception:
            pass

    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            return "google", "gemini-2.0-flash"
        except Exception:
            pass

    return None, None


def ask_agent(question: str):
    """
    Send a natural language question to the LLM, get SQL + chart_type back,
    execute it, return results.

    Returns dict: {answer_text, chart_type, sql, dataframe, error}
    """
    client, model = get_llm_client()

    if client is None:
        return {
            "answer_text": "⚠️ No API key configured. Set GROQ_API_KEY or GOOGLE_API_KEY in your environment.",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": "no_api_key"
        }

    # ── Call the LLM ──
    try:
        if client == "google":
            import google.generativeai as genai
            gmodel = genai.GenerativeModel(model)
            response = gmodel.generate_content(
                f"{SCHEMA_PROMPT}\n\nUser question: {question}"
            )
            raw_response = response.text
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SCHEMA_PROMPT},
                    {"role": "user", "content": question}
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            raw_response = response.choices[0].message.content
    except Exception as e:
        return {
            "answer_text": f"⚠️ LLM API error: {str(e)}",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": str(e)
        }

    # ── Parse JSON response ──
    try:
        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        parsed = json.loads(cleaned)
        sql = parsed.get("sql", "")
        chart_type = parsed.get("chart_type", "table")
        explanation = parsed.get("explanation", "")
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "answer_text": f"⚠️ Could not parse LLM response as JSON.\n\nRaw response:\n{raw_response}",
            "chart_type": "table",
            "sql": None,
            "dataframe": None,
            "error": f"json_parse_error: {e}"
        }

    # ── Guardrail: reject dangerous SQL ──
    if DANGEROUS_PATTERNS.search(sql):
        return {
            "answer_text": "🚫 The generated SQL contains potentially dangerous operations and was rejected.",
            "chart_type": "table",
            "sql": sql,
            "dataframe": None,
            "error": "dangerous_sql"
        }

    # ── Keyword safety net: override chart_type if needed ──
    q_lower = question.lower()
    for pattern, override in CHART_OVERRIDES:
        if re.search(pattern, q_lower):
            chart_type = override
            break

    # ── Execute SQL ──
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

    return {
        "answer_text": explanation,
        "chart_type": chart_type,
        "sql": sql,
        "dataframe": df,
        "error": None
    }
