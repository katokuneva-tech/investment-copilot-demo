"""
Knowledge Base Loader — loads AFK Sistema data from knowledge_base.json.
Loaded once at import time. All exports are read-only dicts/lists.
"""
import json
import os
import re

_KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")

with open(_KB_PATH, "r", encoding="utf-8") as f:
    _RAW = json.load(f)


def parse_number(s) -> float | None:
    """Parse Russian-formatted numbers: '807,2' → 807.2, '972,0 (9М)' → 972.0, '~10' → 10.0, '—' → None."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s or s in ("—", "-", "–", "н/д", "Н/Д", ""):
        return None
    # Remove parenthetical notes like "(9М)", "(Q3)", "(1П)", "(2025 оценка)"
    s = re.sub(r"\s*\(.*?\)", "", s)
    # Remove leading ~ and >
    s = re.sub(r"^[~>≈]", "", s)
    # Remove trailing text like "г/г", "млрд", "трлн", "руб.", "%" etc
    s = re.sub(r"\s*(г/г|млрд|трлн|руб\.?|%|тыс\.?\s*т|кв\.?\s*м|чел\.?).*$", "", s, flags=re.IGNORECASE)
    # Handle ranges like "88-92" → take midpoint? No, just take first number
    # Handle "+14,7%" style — extract the number
    s = re.sub(r"^[+\-]?\s*", "", s) if re.match(r"^[+\-]\d", s) else s
    # Replace comma with dot for decimal
    s = s.replace(",", ".").replace(" ", "").strip()
    # Try to extract a number
    m = re.match(r"^[+\-]?\d+\.?\d*", s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


# Main exports
KB_OVERVIEW: dict = _RAW.get("overview", {})
KB_PORTFOLIO: list[dict] = _RAW.get("portfolio", [])
KB_FINANCIALS: dict = _RAW.get("financials", {})
KB_EVENTS: list[dict] = _RAW.get("deals", []) or _RAW.get("events", [])
KB_SECTORS: list[dict] = _RAW.get("sectors", [])
