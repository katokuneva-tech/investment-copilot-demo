"""
Portfolio companies data — 23 companies from AFK Sistema knowledge base.
10 with full financials, 13 with descriptive metadata only.
Original 5 companies retain peer comparison data for benchmarking skill.
"""
from app.data.kb_loader import KB_PORTFOLIO, KB_FINANCIALS, parse_number

# ── Mapping: KB financial section header → company slug ──
_FIN_KEY_MAP = {
    "АФК «СИСТЕМА» (КОНСОЛИДИРОВАННО)": "afk_sistema",
    "МТС (ТЕЛЕКОМ / ЭКОСИСТЕМА)": "mts",
    "OZON (E-COMMERCE / МАРКЕТПЛЕЙС)": "ozon",
    "SEGEZHA GROUP (ЛЕСОПРОМ)": "segezha",
    "ГРУППА «ЭТАЛОН» (ДЕВЕЛОПМЕНТ)": "etalon",
    "МЕДСИ (МЕДИЦИНА)": "medsi",
    "БИННОФАРМ ГРУПП (ФАРМА)": "binnopharm",
    "АГРОХОЛДИНГ «СТЕПЬ» (АГРОПРОМ)": "step",
    "COSMOS HOTEL GROUP (ГОСТИНИЦЫ)": "cosmos",
    "NATURA SIBERICA (КОСМЕТИКА)": "natura_siberica",
}

# ── Mapping: KB portfolio asset name → slug ──
_SLUG_MAP = {
    "МТС (ПАО)": "mts",
    "Ozon (OZON)": "ozon",
    "Segezha Group": "segezha",
    "Группа «Эталон»": "etalon",
    "МТС Банк": "mts_bank",
    "МЕДСИ": "medsi",
    "Биннофарм Групп": "binnopharm",
    "Агрохолдинг «Степь»": "step",
    "Cosmos Hotel Group": "cosmos",
    "Natura Siberica": "natura_siberica",
    "Sitronics Group": "sitronics",
    "ГК «Спутникс» (ex-Sitronics Space)": "sputniks",
    "Корпорация робототехники": "robotics_corp",
    "Корпорация роботов": "robot_corp",
    "РПХ «Восход»": "voshod",
    "Concept Group": "concept_group",
    "Бизнес-Недвижимость": "business_realty",
    "Аэромакс": "aeromax",
    "Электрозавод / Энергетика": "electrozavod",
    "Ниармедик": "niarmedic",
    "УК «Гжель»": "gzhel",
    "Sistema_VC / Smart Tech": "sistema_vc",
    "R&D Центр Ангелово": "angelovo_rd",
}


def _extract_financial_metric(rows: list[dict], metric_prefix: str, year: str) -> float | None:
    """Find a row whose 'Показатель' starts with metric_prefix and return the value for the given year."""
    for row in rows:
        indicator = row.get("Показатель", "")
        if indicator.lower().startswith(metric_prefix.lower()):
            return parse_number(row.get(year))
    return None


def _build_financials(slug: str, fin_key: str) -> dict:
    """Build financial fields from KB_FINANCIALS for a given company."""
    rows = KB_FINANCIALS.get(fin_key, [])
    if not rows:
        return {"has_financials": False}

    data = {"has_financials": True}

    # Revenue
    for y in ["2022", "2023", "2024", "2025"]:
        data[f"revenue_{y}"] = _extract_financial_metric(rows, "Выручка", y)

    # EBITDA / OIBDA
    for y in ["2022", "2023", "2024", "2025"]:
        val = _extract_financial_metric(rows, "OIBDA", y)
        if val is None:
            val = _extract_financial_metric(rows, "EBITDA", y)
        if val is None:
            val = _extract_financial_metric(rows, "Скорр. EBITDA", y)
        data[f"ebitda_{y}"] = val

    # Net profit
    for y in ["2024", "2025"]:
        val = _extract_financial_metric(rows, "Чистая прибыль", y)
        if val is None:
            val = _extract_financial_metric(rows, "Чистый убыток", y)
            if val is not None:
                val = -abs(val)
        data[f"net_profit_{y}"] = val

    # Net debt
    data["net_debt"] = _extract_financial_metric(rows, "Чистый долг", "2025")
    if data["net_debt"] is None:
        data["net_debt"] = _extract_financial_metric(rows, "Чистый долг", "2024")
    if data["net_debt"] is None:
        data["net_debt"] = _extract_financial_metric(rows, "Общий долг", "2024")

    # Debt/EBITDA — try explicit row first, then calculate
    data["net_debt_ebitda"] = _extract_financial_metric(rows, "Долг/EBITDA", "2025")
    if data["net_debt_ebitda"] is None:
        data["net_debt_ebitda"] = _extract_financial_metric(rows, "Долг/EBITDA", "2024")
    if data["net_debt_ebitda"] is None:
        data["net_debt_ebitda"] = _extract_financial_metric(rows, "Долг/OIBDA", "2024")
    # Try to extract debt ratio from comments
    if data["net_debt_ebitda"] is None:
        for row in rows:
            comment = row.get("Комментарий", "")
            if "долг" in comment.lower() or "oibda" in comment.lower() or "ebitda" in comment.lower():
                import re
                m = re.search(r'(\d+[,.]?\d*)\s*x', comment)
                if m:
                    data["net_debt_ebitda"] = parse_number(m.group(1))
                    break
    # Calculate from net_debt / annual ebitda if still missing
    if data["net_debt_ebitda"] is None and data.get("net_debt") and data.get("net_debt") > 0:
        ebitda = data.get("ebitda_2024")  # Prefer full-year data
        if ebitda and ebitda > 0:
            data["net_debt_ebitda"] = round(data["net_debt"] / ebitda, 1)

    # Calculate margin if possible
    r = data.get("revenue_2025") or data.get("revenue_2024")
    e = data.get("ebitda_2025") or data.get("ebitda_2024")
    data["ebitda_margin"] = round(e / r * 100, 1) if (r and e and r > 0) else None

    # Revenue growth — prefer year-over-year from comments, then calculate
    data["revenue_growth"] = None
    for row in rows:
        comment = row.get("Комментарий", "")
        indicator = row.get("Показатель", "")
        if "выручка" in indicator.lower() or "gmv" in indicator.lower():
            import re
            m = re.search(r'[+](\d+[,.]?\d*)\s*%', comment)
            if m:
                data["revenue_growth"] = parse_number(m.group(1))
                break
    if data["revenue_growth"] is None:
        r24 = data.get("revenue_2024")
        r23 = data.get("revenue_2023")
        if r24 and r23 and r23 > 0:
            data["revenue_growth"] = round((r24 / r23 - 1) * 100, 1)

    return data


# ── Peer comparison data (preserved from original mock for benchmarking) ──
_PEER_DATA = {
    "mts": {
        "ev_ebitda": 4.2, "market_cap": 620.0, "dividend_yield": 12.5,
        "can_pay_dividends": True, "covenant_risk": False, "covenant_threshold": 3.0,
        "fcf_2025": 95.0, "dividend_policy": "Не менее 35 руб. на акцию ежегодно",
        "peers": ["Билайн", "МегаФон", "Ростелеком"],
        "peer_ev_ebitda_avg": 3.8, "peer_margin_avg": 38.0,
    },
    "segezha": {
        "ev_ebitda": 8.5, "market_cap": 28.0, "dividend_yield": 0.0,
        "can_pay_dividends": False, "covenant_risk": True, "covenant_threshold": 4.5,
        "fcf_2025": -5.2, "dividend_policy": "Дивиденды приостановлены до снижения долговой нагрузки",
        "peers": ["Илим", "Sveza", "Mercer International"],
        "peer_ev_ebitda_avg": 6.0, "peer_margin_avg": 15.0,
    },
    "etalon": {
        "ev_ebitda": 5.0, "market_cap": 60.0, "dividend_yield": 5.0,
        "can_pay_dividends": True, "covenant_risk": False, "covenant_threshold": 3.5,
        "fcf_2025": 12.0, "dividend_policy": "25-50% чистой прибыли по МСФО",
        "peers": ["ПИК", "ЛСР", "Самолет"],
        "peer_ev_ebitda_avg": 4.5, "peer_margin_avg": 20.0,
    },
    "binnopharm": {
        "ev_ebitda": 7.0, "market_cap": 62.0, "dividend_yield": 3.0,
        "can_pay_dividends": True, "covenant_risk": False, "covenant_threshold": 3.0,
        "fcf_2025": 6.5, "dividend_policy": "Не менее 25% чистой прибыли",
        "peers": ["Фармстандарт", "Отисифарм", "Renewal"],
        "peer_ev_ebitda_avg": 8.0, "peer_margin_avg": 20.0,
    },
    "step": {
        "ev_ebitda": 5.5, "market_cap": 43.0, "dividend_yield": 4.0,
        "can_pay_dividends": True, "covenant_risk": False, "covenant_threshold": 3.0,
        "fcf_2025": 5.5, "dividend_policy": "25% чистой прибыли при Чистый долг/EBITDA < 2.5x",
        "peers": ["Русагро", "Черкизово", "ЭкоНива"],
        "peer_ev_ebitda_avg": 5.0, "peer_margin_avg": 18.0,
    },
}

# ── Build COMPANIES dict ──
COMPANIES: dict[str, dict] = {}

for p in KB_PORTFOLIO:
    asset_name = p.get("Актив", "")
    slug = _SLUG_MAP.get(asset_name)
    if not slug:
        # Generate slug from asset name
        slug = asset_name.lower().replace(" ", "_").replace("«", "").replace("»", "")

    company = {
        "name": asset_name,
        "name_en": slug.upper(),
        "slug": slug,
        "sector": p.get("Сектор", ""),
        "status": p.get("Статус", ""),
        "stake": p.get("Доля АФК", ""),
        "description": p.get("Описание", ""),
        "key_metrics": p.get("Ключевые метрики", ""),
        "ipo_plans": p.get("IPO планы", ""),
        "has_financials": False,
    }

    # Try to find financials
    for fin_key, fin_slug in _FIN_KEY_MAP.items():
        if fin_slug == slug:
            fin_data = _build_financials(slug, fin_key)
            company.update(fin_data)
            break

    # Add peer comparison data if available
    if slug in _PEER_DATA:
        company.update(_PEER_DATA[slug])

    # Special handling: Segezha real debt/EBITDA is 14.4x from KB
    if slug == "segezha":
        if company.get("net_debt_ebitda") and company["net_debt_ebitda"] > 10:
            company["covenant_risk"] = True

    # Special: Ozon dividend recommendation
    if slug == "ozon":
        company["can_pay_dividends"] = True
        company["dividend_policy"] = "Рекомендованы дивиденды 31 млрд руб. (ноябрь 2025)"
        company["dividend_yield"] = 0  # First time

    COMPANIES[slug] = company

# Add consolidated AFK Sistema as a special entry
_afk_fin = _build_financials("afk_sistema", "АФК «СИСТЕМА» (КОНСОЛИДИРОВАННО)")
COMPANIES["afk_sistema"] = {
    "name": "АФК Система (конс.)",
    "name_en": "AFK Sistema",
    "slug": "afk_sistema",
    "sector": "Инвестиционный холдинг",
    "status": "Публичный",
    "stake": "—",
    "description": "Публичная инвестиционная корпорация с 23+ портфельными компаниями",
    "key_metrics": "2.9 трлн активов, 140 тыс. сотрудников, >150 млн потребителей",
    "ipo_plans": "Публичный актив, тикер AFKS",
    **_afk_fin,
}

# ── Ordered lists ──
COMPANY_ORDER = [slug for slug in (
    [_SLUG_MAP.get(p["Актив"], "") for p in KB_PORTFOLIO]
) if slug and slug in COMPANIES]

COMPANIES_WITH_FINANCIALS = [
    slug for slug in COMPANY_ORDER if COMPANIES.get(slug, {}).get("has_financials")
]

# Add afk_sistema to financials list
if "afk_sistema" not in COMPANIES_WITH_FINANCIALS:
    COMPANIES_WITH_FINANCIALS.insert(0, "afk_sistema")
