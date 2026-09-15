"""
Build DuckDB warehouse from cleaned parquet files.
Section 2 of the build spec — loads into the target data model.
"""

import sys
import duckdb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

CLEANED_DIR = Path(__file__).parent.parent / "data" / "cleaned"
DB_PATH = Path(__file__).parent.parent / "warehouse.duckdb"


def build_warehouse():
    print("🏗️  Building DuckDB warehouse...")

    # Remove old DB if exists
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))

    # ── dim_mandi ──
    con.execute(f"""
        CREATE TABLE dim_mandi AS
        SELECT * FROM read_parquet('{CLEANED_DIR / "dim_mandi.parquet"}')
    """)
    count = con.execute("SELECT COUNT(*) FROM dim_mandi").fetchone()[0]
    print(f"  ✅ dim_mandi: {count} rows")

    # ── fact_arrivals ──
    con.execute(f"""
        CREATE TABLE fact_arrivals AS
        SELECT * FROM read_parquet('{CLEANED_DIR / "fact_arrivals.parquet"}')
    """)
    count = con.execute("SELECT COUNT(*) FROM fact_arrivals").fetchone()[0]
    print(f"  ✅ fact_arrivals: {count} rows")

    # ── fact_prices ──
    con.execute(f"""
        CREATE TABLE fact_prices AS
        SELECT * FROM read_parquet('{CLEANED_DIR / "fact_prices.parquet"}')
    """)
    count = con.execute("SELECT COUNT(*) FROM fact_prices").fetchone()[0]
    print(f"  ✅ fact_prices: {count} rows")

    # ── fact_transport ──
    con.execute(f"""
        CREATE TABLE fact_transport AS
        SELECT * FROM read_parquet('{CLEANED_DIR / "fact_transport.parquet"}')
    """)
    count = con.execute("SELECT COUNT(*) FROM fact_transport").fetchone()[0]
    print(f"  ✅ fact_transport: {count} rows")

    # ── fact_weather_daily ──
    con.execute(f"""
        CREATE TABLE fact_weather_daily AS
        SELECT * FROM read_parquet('{CLEANED_DIR / "fact_weather_daily.parquet"}')
    """)
    count = con.execute("SELECT COUNT(*) FROM fact_weather_daily").fetchone()[0]
    print(f"  ✅ fact_weather_daily: {count} rows")

    # ── Sanity check: run the Section 5 business metric queries ──
    print("\n📊 Running sanity-check queries (Section 5)...\n")

    # Query 1: Total crop arrivals by crop
    print("── Q1: Total crop arrivals (Quintals) by crop ──")
    result = con.execute("""
        SELECT crop, SUM(arrival_qtl) AS total_arrival_qtl
        FROM fact_arrivals GROUP BY crop ORDER BY total_arrival_qtl DESC
    """).fetchdf()
    print(result.to_string(index=False))

    # Query 2: Average modal price vs MSP
    print("\n── Q2: Average modal price vs MSP by crop ──")
    result = con.execute("""
        SELECT crop, ROUND(AVG(modal_price), 2) AS avg_modal_price, ROUND(AVG(msp), 2) AS avg_msp,
               ROUND(AVG(modal_price) - AVG(msp), 2) AS avg_gap
        FROM fact_prices WHERE modal_price IS NOT NULL AND msp IS NOT NULL
        GROUP BY crop
    """).fetchdf()
    print(result.to_string(index=False))

    # Query 3: Price crash count
    print("\n── Q3: Price crash instances (modal < MSP) ──")
    result = con.execute("SELECT COUNT(*) AS crash_count FROM fact_prices WHERE below_msp").fetchone()
    print(f"  Total crashes: {result[0]}")

    # Query 4: Avg transit time by destination
    print("\n── Q4: Average transit time by destination ──")
    result = con.execute("""
        SELECT destination, ROUND(AVG(transit_hours), 2) AS avg_hours
        FROM fact_transport WHERE transit_hours IS NOT NULL AND transit_hours >= 0
        GROUP BY destination ORDER BY avg_hours DESC
    """).fetchdf()
    print(result.to_string(index=False))

    # Query 5: Transit delay rate
    print("\n── Q5: Transit delay rate by destination ──")
    result = con.execute("""
        SELECT destination, ROUND(AVG(CASE WHEN is_delayed THEN 1 ELSE 0 END), 4) AS delay_rate
        FROM fact_transport GROUP BY destination
    """).fetchdf()
    print(result.to_string(index=False))

    # Query 7: Top 5 mandis by volume
    print("\n── Q7: Top 5 mandis by arrival volume ──")
    result = con.execute("""
        SELECT m.mandi_name, m.district, ROUND(SUM(a.arrival_qtl), 2) AS total_qtl
        FROM fact_arrivals a JOIN dim_mandi m USING (mandi_id)
        GROUP BY m.mandi_name, m.district ORDER BY total_qtl DESC LIMIT 5
    """).fetchdf()
    print(result.to_string(index=False))

    con.close()
    print(f"\n✅ Warehouse built at: {DB_PATH}")


if __name__ == "__main__":
    build_warehouse()
