"""Run all 6 acceptance test questions from Section 7 of the spec."""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent / "src"))
from agent import ask_agent

questions = [
    "Show total arrivals by crop type",
    "Which mandi has the highest average transit delay?",
    "Show the distribution of wholesale prices for Rice",
    "Which warehouse receives the highest volume of crops?",
    "Plot the daily arrival trend of Wheat",
    "Compare average modal price vs MSP for each crop",
]

print("=" * 65)
print("  AI AGENT ACCEPTANCE TESTS — Section 7")
print("=" * 65)

all_pass = True
for i, q in enumerate(questions, 1):
    r = ask_agent(q)
    ok = r["error"] is None and r["dataframe"] is not None
    rows = r["dataframe"].shape[0] if r["dataframe"] is not None else 0
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"Q{i} [{status}] chart={r['chart_type']:6s} rows={rows:3d} | {q[:55]}")
    if r.get("sql"):
        print(f"     SQL: {r['sql'][:80]}...")
    if r["error"]:
        print(f"     ERR: {r['error']}")

print("=" * 65)
print("RESULT:", "ALL PASS ✅" if all_pass else "SOME FAILURES ❌")
