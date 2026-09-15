"""
Shared utility functions for Mandi Supply Chain Optimizer.
Section 3.6 & 4 of the build spec — canonical parsers and lookup tables.
"""

import re
import pandas as pd
from dateutil import parser as dateutil_parser

# ─── Section 4: Canonical Crop Mapping ────────────────────────────────────────
# Case-insensitive match. Order matters: longer/more-specific first.
CROP_MAP = {
    # Wheat
    "wheat": "Wheat", "gehun": "Wheat", "kanak": "Wheat", "गेहूं": "Wheat",
    # Rice
    "rice": "Rice", "chawal": "Rice", "paddy": "Rice", "dhaan": "Rice",
    "basmati": "Rice", "चावल": "Rice", "धान": "Rice",
    # Cotton
    "cotton": "Cotton", "kapas": "Cotton", "narma": "Cotton", "कपास": "Cotton",
    # Sugarcane
    "sugarcane": "Sugarcane", "ganna": "Sugarcane", "ganne": "Sugarcane", "गन्ना": "Sugarcane",
    # Maize
    "corn": "Maize", "maize": "Maize", "makka": "Maize", "makki": "Maize", "मक्का": "Maize",
    # Mustard
    "mustard": "Mustard", "sarso": "Mustard", "sarson": "Mustard", "सरसों": "Mustard",
}

def canonical_crop(raw):
    """Map a raw crop name to one of the 6 canonical crops."""
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    key = str(raw).strip().lower()
    return CROP_MAP.get(key, None)


# ─── Section 4: Mandi ID Canonicalizer ────────────────────────────────────────
def canonical_mandi_id(raw):
    """
    Normalize messy mandi_id formats to 'MANDIXXX' (3-digit zero-padded).
    Handles: MANDI026, mandi050, mandi_049, MANDI-054, 056, M045, M005, etc.
    """
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    if s == "":
        return None
    m = re.search(r'\d+', s)
    return f"MANDI{int(m.group()):03d}" if m else None


# ─── Section 4: Quantity Unit Normalization ───────────────────────────────────
UNIT_MULTIPLIER = {
    # Quintal family → ×1
    "q": 1, "qtl": 1, "quintal": 1, "quintals": 1,
    # KG family → ×0.01
    "kg": 0.01, "kgs": 0.01, "kilo": 0.01,
    # Tonne family → ×10
    "t": 10, "tonnes": 10, "mt": 10,
}

def normalize_unit(raw_unit):
    """Return (canonical_unit_name, multiplier_to_quintal)."""
    if pd.isna(raw_unit) or str(raw_unit).strip() == "":
        return None, None
    key = str(raw_unit).strip().lower()
    mult = UNIT_MULTIPLIER.get(key, None)
    if mult is not None:
        return key, mult
    return None, None


def parse_arrival_quantity(raw_qty, raw_unit):
    """
    Parse messy arrival_quantity strings.
    Returns (value_in_qtl, unit_was_assumed: bool, qty_was_corrected: bool)
    """
    if pd.isna(raw_qty):
        return None, False, False

    s = str(raw_qty).strip()
    if s == "":
        return None, False, False

    # Try to extract embedded unit from the quantity string (e.g. "415.88 qtl", "22,697.0 KG")
    embedded_unit = None
    unit_match = re.search(r'[a-zA-Z]+$', s)
    if unit_match:
        embedded_unit = unit_match.group().strip()
        s = s[:unit_match.start()].strip()

    # Strip commas and parse number
    s = s.replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return None, False, False

    # Determine unit: embedded first, then column, then default to Qtl
    unit_was_assumed = False
    if embedded_unit:
        _, mult = normalize_unit(embedded_unit)
    else:
        _, mult = normalize_unit(raw_unit)

    if mult is None:
        mult = 1  # Default to Quintal
        unit_was_assumed = True

    # Handle negatives (sign-entry error)
    qty_was_corrected = False
    if value < 0:
        value = abs(value)
        qty_was_corrected = True

    return value * mult, unit_was_assumed, qty_was_corrected


# ─── Section 4: Price String Cleaner ──────────────────────────────────────────
def clean_price(raw):
    """Strip currency symbols and commas from price values."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        import math
        if math.isnan(raw):
            return None
        return float(raw)
    s = str(raw).strip()
    if s == "":
        return None
    s = re.sub(r'[₹,]|Rs\.?|INR|/-', '', s).strip()
    try:
        return float(s)
    except ValueError:
        return None


# ─── Section 3.6: Shared Messy Date Parser ───────────────────────────────────
EXPLICIT_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%m-%d-%Y", "%d-%b-%Y",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M",
    "%m-%d-%Y %I:%M %p", "%d-%b-%Y %H:%M:%S",
]

def parse_messy_datetime(raw):
    """
    Parse extremely inconsistent date/datetime strings.
    Returns (parsed_datetime, confidence: str)
    confidence is one of: 'high_confidence', 'low_confidence', 'failed', 'missing'
    """
    if pd.isna(raw) or str(raw).strip() == "":
        return pd.NaT, "missing"
    s = str(raw).strip()

    # Strip timezone suffixes (we'll handle conversion separately)
    tz_suffix = None
    for tz in (" IST", " UTC"):
        if s.endswith(tz):
            tz_suffix = tz.strip()
            s = s[:-len(tz)]
            break

    for fmt in EXPLICIT_FORMATS:
        try:
            dt = pd.to_datetime(s, format=fmt)
            return dt, "high_confidence"
        except (ValueError, TypeError):
            continue

    try:
        # Last resort: day-first is the reasonable default for India-based data
        dt = dateutil_parser.parse(s, dayfirst=True)
        return pd.Timestamp(dt), "low_confidence"
    except Exception:
        return pd.NaT, "failed"


def parse_messy_date(raw):
    """Parse a date string and return just the date part + confidence."""
    dt, conf = parse_messy_datetime(raw)
    if pd.isna(dt):
        return pd.NaT, conf
    return dt.normalize(), conf  # normalize strips time, keeps date


def parse_messy_timestamp_with_tz(raw):
    """
    Parse datetime string, handling IST/UTC timezone suffixes.
    Returns (datetime_in_IST, confidence, tz_source)
    """
    if pd.isna(raw) or str(raw).strip() == "":
        return pd.NaT, "missing", None

    s = str(raw).strip()
    tz_source = "assumed_IST"

    if s.endswith(" UTC"):
        tz_source = "converted_from_UTC"
        s = s[:-4]
    elif s.endswith(" IST"):
        tz_source = "IST"
        s = s[:-4]

    dt, conf = parse_messy_datetime(s)
    if pd.isna(dt):
        return pd.NaT, conf, None

    # Convert UTC → IST (add 5:30)
    if tz_source == "converted_from_UTC":
        dt = dt + pd.Timedelta(hours=5, minutes=30)

    return dt, conf, tz_source
