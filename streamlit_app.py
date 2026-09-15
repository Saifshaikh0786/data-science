"""
Streamlit Community Cloud entrypoint.
Forwarding entry point to app.py.
"""
from pathlib import Path
import runpy

app_path = Path(__file__).parent / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
