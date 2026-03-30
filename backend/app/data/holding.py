"""
Holding-level data: overview, events, sectors, IPO candidates.
"""
from app.data.kb_loader import KB_OVERVIEW, KB_EVENTS, KB_SECTORS, KB_PORTFOLIO

# 30 parameters about AFK Sistema holding
HOLDING_OVERVIEW = KB_OVERVIEW

# Key deals and events (2025-2026), sorted by date descending
HOLDING_EVENTS = sorted(KB_EVENTS, key=lambda e: e.get("Дата", ""), reverse=True)

# 17 sector mappings
SECTORS = KB_SECTORS

# IPO candidates — non-public companies with IPO plans mentioned
IPO_CANDIDATES = [
    {
        "name": p.get("Актив", ""),
        "sector": p.get("Сектор", ""),
        "stake": p.get("Доля АФК", ""),
        "ipo_plans": p.get("IPO планы", ""),
        "key_metrics": p.get("Ключевые метрики", ""),
    }
    for p in KB_PORTFOLIO
    if "IPO" in str(p.get("IPO планы", ""))
    and "Публичный" not in str(p.get("Статус", ""))
]
