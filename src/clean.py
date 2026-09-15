"""
Data cleaning pipeline — Section 3 of the build spec.
Reads raw data files from data/raw/, cleans per documented rules,
and writes cleaned DataFrames to data/cleaned/ as parquet files.
Also generates a data_quality_report.md.
"""

import os
import sys
import re
import json
import math
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    canonical_mandi_id, canonical_crop, parse_arrival_quantity,
    clean_price, parse_messy_date, parse_messy_datetime,
    parse_messy_timestamp_with_tz, normalize_unit
)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
CLEANED_DIR = Path(__file__).parent.parent / "data" / "cleaned"
REPORT_PATH = Path(__file__).parent.parent / "reports" / "data_quality_report.md"

# QA log collector
qa_log = []

def log_qa(section, message, count=None):
    entry = f"- **{section}**: {message}"
    if count is not None:
        entry += f" ({count} rows)"
    qa_log.append(entry)
    print(f"  [QA] {section}: {message}" + (f" ({count} rows)" if count is not None else ""))


# ═══════════════════════════════════════════════════════════════════════════════
# 3.1 Mandi Master
# ═══════════════════════════════════════════════════════════════════════════════
def clean_mandi_master():
    print("\n═══ Cleaning: track3_mandi_master.csv ═══")
    df = pd.read_csv(RAW_DIR / "track3_mandi_master.csv", dtype=str)
    original_count = len(df)
    log_qa("3.1 Mandi Master", f"Raw rows loaded", original_count)

    # Replace 'NA' strings with actual NaN
    df.replace({"NA": np.nan, "na": np.nan, "": np.nan}, inplace=True)

    # Canonicalize mandi_id
    df["mandi_id"] = df["mandi_id"].apply(canonical_mandi_id)

    # Drop exact duplicate rows
    before_dedup = len(df)
    df = df.drop_duplicates(subset="mandi_id", keep="first")
    dupes_removed = before_dedup - len(df)
    log_qa("3.1 Mandi Master", f"Exact duplicate mandi_id rows removed", dupes_removed)

    # District casing normalization
    df["district"] = df["district"].str.strip().str.title()

    # Missing district/state: set to "Unknown"
    missing_district = df["district"].isna().sum()
    missing_state_only = (df["state"].isna() & df["district"].notna()).sum()
    df.loc[df["district"].isna(), "district"] = "Unknown"

    # Build district→state lookup from non-null rows
    lookup_rows = df.dropna(subset=["district", "state"])
    lookup_rows = lookup_rows[lookup_rows["district"] != "Unknown"]
    district_to_state = lookup_rows.drop_duplicates(subset="district").set_index("district")["state"].to_dict()

    # Backfill missing state from district lookup
    for idx, row in df.iterrows():
        if pd.isna(row["state"]) and row["district"] != "Unknown":
            df.at[idx, "state"] = district_to_state.get(row["district"], None)

    # Remaining missing state → Unknown
    still_missing_state = df["state"].isna().sum()
    df.loc[df["state"].isna(), "state"] = "Unknown"

    log_qa("3.1 Mandi Master", f"Rows with district set to 'Unknown'", missing_district)
    log_qa("3.1 Mandi Master", f"Rows with state backfilled from district lookup", missing_state_only)
    log_qa("3.1 Mandi Master", f"Rows with state still 'Unknown' after backfill", still_missing_state)

    # Log mandi_ids with Unknown district
    unknown_mandis = df[df["district"] == "Unknown"]["mandi_id"].tolist()
    if unknown_mandis:
        log_qa("3.1 Mandi Master", f"Mandi IDs with Unknown district: {unknown_mandis}")

    # Mandi type normalization
    df["mandi_type"] = df["mandi_type"].str.strip().str.title()
    mandi_type_missing = df["mandi_type"].isna().sum()
    df.loc[df["mandi_type"].isna(), "mandi_type"] = "Unknown"
    log_qa("3.1 Mandi Master", f"Mandi type missing → set to 'Unknown'", mandi_type_missing)

    # total_area_acres → numeric, leave null if missing
    df["total_area_acres"] = pd.to_numeric(df["total_area_acres"], errors="coerce")
    area_null = df["total_area_acres"].isna().sum()
    log_qa("3.1 Mandi Master", f"total_area_acres null (left as-is)", area_null)

    # State casing
    df["state"] = df["state"].str.strip().str.title()

    print(f"  → dim_mandi: {len(df)} rows")
    log_qa("3.1 Mandi Master", f"Final dim_mandi rows", len(df))
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 3.2 Mandi Arrivals
# ═══════════════════════════════════════════════════════════════════════════════
def clean_arrivals():
    print("\n═══ Cleaning: track3_mandi_arrivals.csv ═══")
    df = pd.read_csv(RAW_DIR / "track3_mandi_arrivals.csv", dtype=str)
    original_count = len(df)
    log_qa("3.2 Arrivals", f"Raw rows loaded", original_count)

    df.replace({"NA": np.nan, "na": np.nan, "": np.nan}, inplace=True)

    # Canonicalize mandi_id
    df["mandi_id"] = df["mandi_id"].apply(canonical_mandi_id)
    null_mandi = df["mandi_id"].isna().sum()
    log_qa("3.2 Arrivals", f"mandi_id null after canonicalization", null_mandi)

    # Canonicalize crop_name
    df["crop"] = df["crop_name"].apply(canonical_crop)
    unmapped_crops = df[df["crop"].isna() & df["crop_name"].notna()]["crop_name"].unique()
    if len(unmapped_crops) > 0:
        log_qa("3.2 Arrivals", f"Unmapped crop names: {list(unmapped_crops)}")
    null_crop = df["crop"].isna().sum()
    log_qa("3.2 Arrivals", f"crop null after canonicalization", null_crop)

    # Parse arrival_quantity with unit conversion
    results = df.apply(
        lambda r: parse_arrival_quantity(r["arrival_quantity"], r["unit"]), axis=1
    )
    df["arrival_qtl"] = [r[0] for r in results]
    df["unit_was_assumed"] = [r[1] for r in results]
    df["qty_was_corrected"] = [r[2] for r in results]

    neg_corrected = df["qty_was_corrected"].sum()
    unit_assumed = df["unit_was_assumed"].sum()
    log_qa("3.2 Arrivals", f"Negative quantities corrected (abs)", neg_corrected)
    log_qa("3.2 Arrivals", f"Unit defaulted to Quintal (assumed)", unit_assumed)

    # Parse dates
    date_results = df["date"].apply(parse_messy_date)
    df["date_parsed"] = [r[0] for r in date_results]
    df["date_confidence"] = [r[1] for r in date_results]

    failed_dates = (df["date_confidence"] == "failed").sum()
    low_conf_dates = (df["date_confidence"] == "low_confidence").sum()
    log_qa("3.2 Arrivals", f"Date parse: failed", failed_dates)
    log_qa("3.2 Arrivals", f"Date parse: low_confidence", low_conf_dates)

    # Use parsed date
    df["date"] = df["date_parsed"]

    # farmer_count → numeric
    df["farmer_count"] = pd.to_numeric(df["farmer_count"], errors="coerce")

    # arrival_id: fill nulls with generated IDs
    null_ids = df["arrival_id"].isna().sum()
    for idx in df[df["arrival_id"].isna()].index:
        df.at[idx, "arrival_id"] = f"GEN_{idx}"
    log_qa("3.2 Arrivals", f"arrival_id null → generated fallback IDs", null_ids)

    # Keep relevant columns
    result = df[["arrival_id", "date", "mandi_id", "crop", "variety",
                  "arrival_qtl", "farmer_count", "qty_was_corrected"]].copy()

    print(f"  → fact_arrivals: {len(result)} rows")
    log_qa("3.2 Arrivals", f"Final fact_arrivals rows", len(result))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3.3 Price and MSP
# ═══════════════════════════════════════════════════════════════════════════════
def clean_prices():
    print("\n═══ Cleaning: track3_price_and_msp.json ═══")
    with open(RAW_DIR / "track3_price_and_msp.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    original_count = len(df)
    log_qa("3.3 Prices", f"Raw rows loaded", original_count)

    # Canonicalize mandi_id
    df["mandi_id"] = df["mandi_id"].apply(canonical_mandi_id)
    null_mandi = df["mandi_id"].isna().sum()
    log_qa("3.3 Prices", f"mandi_id null after canonicalization", null_mandi)

    # Canonicalize crop_name
    df["crop"] = df["crop_name"].apply(canonical_crop)
    null_crop = df["crop"].isna().sum()
    log_qa("3.3 Prices", f"crop null after canonicalization", null_crop)

    # Clean prices
    for col in ["min_price", "max_price", "modal_price", "msp"]:
        df[col] = df[col].apply(clean_price)
        null_count = df[col].isna().sum()
        log_qa("3.3 Prices", f"{col} null after cleaning", null_count)

    # Parse dates
    date_results = df["date"].apply(parse_messy_date)
    df["date_parsed"] = [r[0] for r in date_results]
    df["date_confidence"] = [r[1] for r in date_results]

    failed_dates = (df["date_confidence"] == "failed").sum()
    low_conf_dates = (df["date_confidence"] == "low_confidence").sum()
    log_qa("3.3 Prices", f"Date parse: failed", failed_dates)
    log_qa("3.3 Prices", f"Date parse: low_confidence", low_conf_dates)

    df["date"] = df["date_parsed"]

    # District: clean but we'll prefer dim_mandi's district after join
    df["district"] = df["district"].astype(str).str.strip().str.title()
    df.loc[df["district"].isin(["Nan", "None", ""]), "district"] = None

    # Derived flag: below_msp
    df["below_msp"] = False
    mask = df["modal_price"].notna() & df["msp"].notna()
    df.loc[mask, "below_msp"] = df.loc[mask, "modal_price"] < df.loc[mask, "msp"]
    below_count = df["below_msp"].sum()
    log_qa("3.3 Prices", f"Rows where modal_price < msp (below MSP)", below_count)

    result = df[["record_id", "date", "mandi_id", "district", "crop",
                  "min_price", "max_price", "modal_price", "msp", "below_msp"]].copy()

    print(f"  → fact_prices: {len(result)} rows")
    log_qa("3.3 Prices", f"Final fact_prices rows", len(result))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3.4 Transport Logistics
# ═══════════════════════════════════════════════════════════════════════════════
def clean_transport():
    print("\n═══ Cleaning: track3_transport_logistics.csv ═══")
    df = pd.read_csv(RAW_DIR / "track3_transport_logistics.csv", dtype=str)
    original_count = len(df)
    log_qa("3.4 Transport", f"Raw rows loaded", original_count)

    df.replace({"NA": np.nan, "na": np.nan, "": np.nan}, inplace=True)

    # Canonicalize mandi_id
    df["mandi_id"] = df["mandi_id"].apply(canonical_mandi_id)

    # Parse departure/arrival times
    dep_results = df["departure_time"].apply(parse_messy_datetime)
    df["departure_ts"] = [r[0] for r in dep_results]
    df["dep_confidence"] = [r[1] for r in dep_results]

    arr_results = df["arrival_time"].apply(parse_messy_datetime)
    df["arrival_ts"] = [r[0] for r in arr_results]
    df["arr_confidence"] = [r[1] for r in arr_results]

    dep_failed = (df["dep_confidence"] == "failed").sum()
    arr_failed = (df["arr_confidence"] == "failed").sum()
    log_qa("3.4 Transport", f"departure_time parse failed", dep_failed)
    log_qa("3.4 Transport", f"arrival_time parse failed", arr_failed)

    # transit_hours: numeric
    df["transit_hours_raw"] = pd.to_numeric(df["transit_hours"], errors="coerce")

    # Recompute transit_hours where raw is null or negative
    df["transit_hours_was_recalculated"] = False
    for idx, row in df.iterrows():
        raw_th = row["transit_hours_raw"]
        needs_recompute = pd.isna(raw_th) or raw_th < 0

        if needs_recompute and pd.notna(row["departure_ts"]) and pd.notna(row["arrival_ts"]):
            delta = (row["arrival_ts"] - row["departure_ts"]).total_seconds() / 3600
            if delta >= 0:
                df.at[idx, "transit_hours_raw"] = delta
                df.at[idx, "transit_hours_was_recalculated"] = True
            else:
                # arrival before departure → swap and recalculate
                delta = abs(delta)
                df.at[idx, "transit_hours_raw"] = delta
                df.at[idx, "transit_hours_was_recalculated"] = True

    df["transit_hours"] = df["transit_hours_raw"]
    null_th = df["transit_hours"].isna().sum()
    negative_th = (df["transit_hours"] < 0).sum()
    recalculated = df["transit_hours_was_recalculated"].sum()
    log_qa("3.4 Transport", f"transit_hours null (after recompute)", null_th)
    log_qa("3.4 Transport", f"transit_hours negative (after recompute)", negative_th)
    log_qa("3.4 Transport", f"transit_hours recalculated from timestamps", recalculated)

    # Distance + distance_unit
    df["distance_raw"] = pd.to_numeric(df["distance"], errors="coerce")
    df["distance_unit"] = df["distance_unit"].str.strip().str.lower()
    df["distance_unit_was_assumed"] = False

    # Default missing unit to km
    missing_unit = df["distance_unit"].isna().sum()
    df.loc[df["distance_unit"].isna(), "distance_unit"] = "km"
    df.loc[df["distance_unit"].isna(), "distance_unit_was_assumed"] = True
    log_qa("3.4 Transport", f"distance_unit missing → defaulted to km", missing_unit)

    # Convert miles → km
    miles_mask = df["distance_unit"].isin(["miles", "mile", "mi"])
    miles_count = miles_mask.sum()
    df.loc[miles_mask, "distance_raw"] = df.loc[miles_mask, "distance_raw"] * 1.60934
    log_qa("3.4 Transport", f"distance converted from miles to km", miles_count)

    df["distance_km"] = df["distance_raw"]

    # Vehicle number normalization
    df["vehicle_no"] = df["vehicle_no"].apply(
        lambda v: re.sub(r'[\s\-]', '', str(v)).upper() if pd.notna(v) else None
    )

    # Destination (already clean)
    df["destination"] = df["destination_warehouse"]

    # Delay flag: expected_hours = distance_km / 40.0, is_delayed = transit_hours > 1.5 × expected
    df["is_delayed"] = False
    valid_mask = df["transit_hours"].notna() & df["distance_km"].notna() & (df["distance_km"] > 0)
    df.loc[valid_mask, "expected_hours"] = df.loc[valid_mask, "distance_km"] / 40.0
    delay_mask = valid_mask & (df["transit_hours"] > 1.5 * df["expected_hours"])
    df.loc[delay_mask, "is_delayed"] = True
    delay_count = df["is_delayed"].sum()
    log_qa("3.4 Transport", f"Trips flagged as delayed (>1.5× expected)", delay_count)

    result = df[["trip_id", "mandi_id", "destination", "departure_ts", "arrival_ts",
                  "transit_hours", "distance_km", "vehicle_no", "driver_id",
                  "transit_hours_was_recalculated", "is_delayed"]].copy()

    print(f"  → fact_transport: {len(result)} rows")
    log_qa("3.4 Transport", f"Final fact_transport rows", len(result))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3.5 Weather Sensors
# ═══════════════════════════════════════════════════════════════════════════════
def clean_weather():
    print("\n═══ Cleaning: track3_weather_sensors.xlsx ═══")
    df = pd.read_excel(RAW_DIR / "track3_weather_sensors.xlsx", sheet_name="sensor_logs", dtype=str)
    original_count = len(df)
    log_qa("3.5 Weather", f"Raw rows loaded", original_count)

    df.replace({"NA": np.nan, "na": np.nan, "": np.nan}, inplace=True)

    # Exclude UNKNOWN sensor_id
    unknown_sensors = (df["sensor_id"] == "UNKNOWN").sum()
    df = df[df["sensor_id"] != "UNKNOWN"]
    log_qa("3.5 Weather", f"Rows with sensor_id='UNKNOWN' excluded", unknown_sensors)

    # Parse timestamps with timezone handling
    ts_results = df["timestamp"].apply(parse_messy_timestamp_with_tz)
    df["timestamp_parsed"] = [r[0] for r in ts_results]
    df["ts_confidence"] = [r[1] for r in ts_results]
    df["tz_source"] = [r[2] for r in ts_results]

    # Drop rows with no timestamp
    no_ts = df["timestamp_parsed"].isna().sum()
    df = df[df["timestamp_parsed"].notna()]
    log_qa("3.5 Weather", f"Rows dropped due to missing/unparseable timestamp", no_ts)

    # Extract date from timestamp
    df["date"] = df["timestamp_parsed"].dt.normalize()

    # ── Temperature parsing ──
    df["temp_unit_was_assumed"] = False
    temp_values = []
    for idx, row in df.iterrows():
        raw_temp = row["temperature"]
        raw_unit = row["temp_unit"]

        if pd.isna(raw_temp):
            temp_values.append(None)
            continue

        temp_str = str(raw_temp).strip()
        unit = None
        value = None

        # Check if unit is embedded in value (e.g. "39.8°C")
        emb_match = re.match(r'^([\d.\-]+)\s*°?([CcFf])', temp_str)
        if emb_match:
            value = float(emb_match.group(1))
            u = emb_match.group(2).upper()
            unit = "Celsius" if u == "C" else "Fahrenheit"
        else:
            try:
                value = float(temp_str)
            except ValueError:
                temp_values.append(None)
                continue

            # Use temp_unit column
            if pd.notna(raw_unit):
                u = str(raw_unit).strip().lower()
                if u in ("c", "°c", "celsius"):
                    unit = "Celsius"
                elif u in ("f", "°f", "fahrenheit"):
                    unit = "Fahrenheit"

            # Heuristic fallback
            if unit is None:
                unit = "Fahrenheit" if value > 50 else "Celsius"
                df.at[idx, "temp_unit_was_assumed"] = True

        # Convert to Celsius
        if unit == "Fahrenheit":
            value = (value - 32) * 5 / 9

        temp_values.append(value)

    df["temp_c"] = temp_values
    assumed_temp = df["temp_unit_was_assumed"].sum()
    log_qa("3.5 Weather", f"Temperature unit assumed via heuristic", assumed_temp)

    # ── Rainfall parsing ──
    df["rainfall_was_clipped"] = False
    rainfall_values = []
    for idx, row in df.iterrows():
        raw_rain = row["rainfall"]
        raw_unit = row["rain_unit"]

        if pd.isna(raw_rain):
            rainfall_values.append(None)
            continue

        try:
            value = float(str(raw_rain).strip())
        except ValueError:
            rainfall_values.append(None)
            continue

        # Convert inches → mm
        if pd.notna(raw_unit):
            u = str(raw_unit).strip().lower()
            if u in ("in", "inch", "inches"):
                value = value * 25.4

        # Clip negatives
        if value < 0:
            value = 0
            df.at[idx, "rainfall_was_clipped"] = True

        rainfall_values.append(value)

    df["rainfall_mm"] = rainfall_values
    clipped = df["rainfall_was_clipped"].sum()
    log_qa("3.5 Weather", f"Negative rainfall clipped to 0", clipped)

    # ── Humidity ──
    df["humidity_pct"] = pd.to_numeric(df["humidity_percent"], errors="coerce")
    # Clip to 0-100
    out_of_range = ((df["humidity_pct"] < 0) | (df["humidity_pct"] > 100)).sum()
    df["humidity_pct"] = df["humidity_pct"].clip(0, 100)
    if out_of_range > 0:
        log_qa("3.5 Weather", f"Humidity out-of-range clipped", out_of_range)

    # ── Aggregate to daily national ──
    daily = df.groupby("date").agg(
        avg_temp_c=("temp_c", "mean"),
        total_rainfall_mm=("rainfall_mm", "sum"),
        avg_humidity_pct=("humidity_pct", "mean"),
    ).reset_index()

    print(f"  → fact_weather_daily: {len(daily)} rows")
    log_qa("3.5 Weather", f"Final fact_weather_daily rows", len(daily))
    return daily


# ═══════════════════════════════════════════════════════════════════════════════
# Main runner
# ═══════════════════════════════════════════════════════════════════════════════
def run_all():
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    print("🔧 Starting data cleaning pipeline...\n")

    dim_mandi = clean_mandi_master()
    fact_arrivals = clean_arrivals()
    fact_prices = clean_prices()
    fact_transport = clean_transport()
    fact_weather_daily = clean_weather()

    # Save as parquet
    dim_mandi.to_parquet(CLEANED_DIR / "dim_mandi.parquet", index=False)
    fact_arrivals.to_parquet(CLEANED_DIR / "fact_arrivals.parquet", index=False)
    fact_prices.to_parquet(CLEANED_DIR / "fact_prices.parquet", index=False)
    fact_transport.to_parquet(CLEANED_DIR / "fact_transport.parquet", index=False)
    fact_weather_daily.to_parquet(CLEANED_DIR / "fact_weather_daily.parquet", index=False)

    print("\n✅ All cleaned data saved to data/cleaned/")

    # ── Compute join success rates for QA ──
    valid_mandis = set(dim_mandi["mandi_id"].dropna().unique())
    arr_join = fact_arrivals["mandi_id"].isin(valid_mandis).mean() * 100
    price_join = fact_prices["mandi_id"].isin(valid_mandis).mean() * 100
    transport_join = fact_transport["mandi_id"].isin(valid_mandis).mean() * 100
    log_qa("Join Rates", f"Arrivals → dim_mandi join success: {arr_join:.1f}%")
    log_qa("Join Rates", f"Prices → dim_mandi join success: {price_join:.1f}%")
    log_qa("Join Rates", f"Transport → dim_mandi join success: {transport_join:.1f}%")

    # ── Write QA report ──
    report_lines = [
        "# Data Quality Report",
        "",
        "**Generated by:** `src/clean.py`",
        f"**Pipeline run timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary of Cleaning Actions & Assumptions",
        "",
    ]
    report_lines.extend(qa_log)
    report_lines.extend([
        "",
        "## Row Counts (Before → After)",
        "",
        "| Table | Raw Rows | Final Rows |",
        "|---|---|---|",
        f"| dim_mandi | 60 (with duplicates) | {len(dim_mandi)} |",
        f"| fact_arrivals | 25,750 | {len(fact_arrivals)} |",
        f"| fact_prices | 12,000 | {len(fact_prices)} |",
        f"| fact_transport | 10,400 | {len(fact_transport)} |",
        f"| fact_weather_daily | 15,000 (sensor readings) | {len(fact_weather_daily)} (daily aggregates) |",
        "",
        "## Documented Assumptions",
        "",
        "1. **Missing quantity unit** → defaulted to Quintal (the most common unit in the dataset)",
        "2. **Negative arrival quantities** → treated as sign-entry errors, abs() applied",
        "3. **Missing distance_unit** → defaulted to km (majority case)",
        "4. **Temperature heuristic** → values > 50 assumed Fahrenheit, else Celsius (when no unit available)",
        "5. **Negative rainfall** → clipped to 0 (physically impossible)",
        "6. **Date parsing** → dayfirst=True default for ambiguous DD/MM vs MM/DD (India-based dataset)",
        "7. **Timezone** → strings ending in UTC converted to IST (+5:30); all others assumed IST",
        "8. **Weather aggregation** → national daily aggregate (no sensor-to-district mapping exists)",
        "9. **Transit delay** → is_delayed = transit_hours > 1.5 × (distance_km / 40 km/h)",
        "10. **Mandi names** → NOT used for geography inference (randomized in dataset, per Rule 1)",
        "",
    ])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"📊 Data quality report written to {REPORT_PATH}")

    return {
        "dim_mandi": dim_mandi,
        "fact_arrivals": fact_arrivals,
        "fact_prices": fact_prices,
        "fact_transport": fact_transport,
        "fact_weather_daily": fact_weather_daily,
    }


if __name__ == "__main__":
    run_all()
