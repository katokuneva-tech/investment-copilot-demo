"""Analytical tools for ReAct agent — v2 with dynamic KB reads and advanced analytics."""
import json, re, math, statistics
from typing import Any

# Load knowledge base once
_kb = None
def _get_kb():
    global _kb
    if _kb is None:
        import os
        kb_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "knowledge_base.json")
        for p in [kb_path, "/Users/e.okuneva/Desktop/knowledge_base.json"]:
            try:
                with open(os.path.normpath(p), "r") as f:
                    _kb = json.load(f)
                    break
            except FileNotFoundError:
                continue
        if _kb is None:
            _kb = {}
    return _kb


def _parse_number(val: str) -> float | None:
    """Extract numeric value from KB string like '807,2', '972,0 (9М)', '~29%'."""
    if not val or val == "—" or val == "н/д":
        return None
    # Remove common prefixes/suffixes
    clean = val.replace("\xa0", " ").replace(",", ".")
    clean = re.sub(r'\s*\(.*?\)', '', clean)  # remove (9М), (Q3), etc.
    clean = clean.strip().lstrip("~").rstrip("%xх")
    # Try to find first number
    match = re.search(r'-?[\d]+\.?\d*', clean)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def _extract_period(val: str) -> str:
    """Extract period marker from value like '972,0 (9М)' → '9М 2025'."""
    period_match = re.search(r'\((.*?)\)', val)
    if period_match:
        return period_match.group(1)
    return ""


def data_query(entity: str, metric: str = "", years: list[str] = None) -> dict:
    """Query structured data from knowledge base.

    Args:
        entity: Company name (e.g. "МТС", "Segezha") or "overview" or "all"
        metric: Optional metric filter (e.g. "выручка", "EBITDA", "долг")
        years: Optional year filter

    Returns dict with found data and source references.
    """
    kb = _get_kb()
    results = {"entity": entity, "metric": metric, "data": [], "source": "knowledge_base.json (АФК Система)"}

    if entity.lower() in ["overview", "обзор", "холдинг", "афк"]:
        overview = kb.get("overview", {})
        if metric:
            for k, v in overview.items():
                if metric.lower() in k.lower():
                    results["data"].append({"parameter": k, "value": v})
        else:
            results["data"] = [{"parameter": k, "value": v} for k, v in overview.items()]
        return results

    # Search portfolio
    portfolio = kb.get("portfolio", [])
    for company in portfolio:
        name = company.get("Актив", "")
        if entity.lower() in name.lower() or name.lower() in entity.lower():
            results["data"].append({
                "name": name,
                "sector": company.get("Сектор", ""),
                "status": company.get("Статус", ""),
                "share": company.get("Доля АФК", ""),
                "description": company.get("Описание", ""),
                "metrics": company.get("Ключевые метрики", ""),
                "ipo": company.get("IPO планы", "")
            })

    # Search financials
    financials = kb.get("financials", {})
    if isinstance(financials, dict):
        for comp_name, indicators in financials.items():
            if entity.lower() == "all" or entity.lower() in comp_name.lower() or comp_name.lower() in entity.lower():
                if not isinstance(indicators, list):
                    continue
                for ind in indicators:
                    if not isinstance(ind, dict):
                        continue
                    if metric and metric.lower() not in ind.get("Показатель", "").lower():
                        continue
                    entry = {"company": comp_name, "indicator": ind.get("Показатель", "")}
                    for year in ["2022", "2023", "2024", "2025"]:
                        if year in ind:
                            if years and year not in years:
                                continue
                            entry[year] = ind[year]
                    entry["comment"] = ind.get("Комментарий", "")
                    results["data"].append(entry)

    # Search deals/events
    deals = kb.get("deals", [])
    if isinstance(deals, list) and (entity.lower() == "all" or not results["data"]):
        for ev in deals:
            if not isinstance(ev, dict):
                continue
            if entity.lower() == "all" or entity.lower() in ev.get("Событие", "").lower() or entity.lower() in ev.get("Детали", "").lower():
                results["data"].append({"type": "deal", **ev})

    # Search sectors
    sectors = kb.get("sectors", [])
    if isinstance(sectors, list) and (entity.lower() == "all" or metric.lower() in ["сектор", "отрасл"]):
        for sec in sectors:
            if not isinstance(sec, dict):
                continue
            if entity.lower() == "all" or entity.lower() in json.dumps(sec, ensure_ascii=False).lower():
                results["data"].append({"type": "sector", **sec})

    # Search macro context if available
    macro = kb.get("macro_context", {})
    if macro and entity.lower() in ["макро", "macro", "ставка", "ставки", "инфляция", "all"]:
        results["data"].append({"type": "macro", **macro})

    # Search company profiles if available
    profiles = kb.get("company_profiles", {})
    if isinstance(profiles, dict):
        for prof_name, profile in profiles.items():
            if entity.lower() in prof_name.lower() or prof_name.lower() in entity.lower():
                results["data"].append({"type": "profile", "company": prof_name, **profile})

    return results


def calculate(operation: str, **kwargs) -> dict:
    """Perform financial calculations deterministically.

    Operations:
    - growth: calculate growth rate. Args: old, new
    - ratio: calculate ratio. Args: numerator, denominator
    - margin: calculate margin. Args: profit, revenue
    - npv: calculate NPV. Args: cash_flows (list), discount_rate
    - irr: calculate IRR. Args: cash_flows (list)
    - compare: compare values. Args: values (dict of name: value)
    - wacc: calculate WACC. Args: equity_cost, debt_cost, equity_weight, tax_rate
    """
    result = {"operation": operation, "inputs": kwargs}

    try:
        if operation == "growth":
            old, new = float(kwargs["old"]), float(kwargs["new"])
            pct = (new / old - 1) * 100
            result["result"] = round(pct, 1)
            result["unit"] = "%"
            result["formula"] = f"({new}/{old} - 1) * 100 = {result['result']}%"

        elif operation == "ratio":
            num, den = float(kwargs["numerator"]), float(kwargs["denominator"])
            result["result"] = round(num / den, 2)
            result["formula"] = f"{num}/{den} = {result['result']}"

        elif operation == "margin":
            profit, revenue = float(kwargs["profit"]), float(kwargs["revenue"])
            result["result"] = round(profit / revenue * 100, 1)
            result["unit"] = "%"
            result["formula"] = f"{profit}/{revenue} * 100 = {result['result']}%"

        elif operation == "npv":
            from app.services.financial_calculator import calculate_npv
            cf = [float(x) for x in kwargs["cash_flows"]]
            rate = float(kwargs["discount_rate"])
            result["result"] = calculate_npv(cf, rate)
            result["unit"] = "млрд руб."

        elif operation == "irr":
            from app.services.financial_calculator import calculate_irr
            cf = [float(x) for x in kwargs["cash_flows"]]
            result["result"] = calculate_irr(cf)
            result["unit"] = "%"

        elif operation == "compare":
            values = kwargs["values"]
            sorted_vals = sorted(values.items(), key=lambda x: float(x[1]) if x[1] != "н/д" else float('-inf'), reverse=True)
            result["ranking"] = [{"rank": i+1, "name": k, "value": v} for i, (k, v) in enumerate(sorted_vals)]
            result["leader"] = sorted_vals[0][0] if sorted_vals else None

        elif operation == "wacc":
            ke = float(kwargs["equity_cost"])
            kd = float(kwargs["debt_cost"])
            we = float(kwargs["equity_weight"])
            t = float(kwargs.get("tax_rate", 0.20))
            wd = 1 - we
            wacc_val = ke * we + kd * (1 - t) * wd
            result["result"] = round(wacc_val * 100, 1)
            result["unit"] = "%"
            result["formula"] = f"WACC = {ke:.1%} × {we:.1%} + {kd:.1%} × (1-{t:.0%}) × {wd:.1%} = {wacc_val:.1%}"
            result["components"] = {"Ke": f"{ke:.1%}", "Kd": f"{kd:.1%}", "We": f"{we:.1%}", "Wd": f"{wd:.1%}", "Tax": f"{t:.0%}"}

        else:
            result["error"] = f"Unknown operation: {operation}"
    except Exception as e:
        result["error"] = str(e)

    return result


def cross_doc_check(claim: str, docs_context: str) -> dict:
    """Verify a specific claim against document context.

    Returns whether the claim is supported, contradicted, or unverifiable.
    """
    claim_lower = claim.lower()
    numbers_in_claim = re.findall(r'[\d,.]+[%xх]?', claim)

    result = {"claim": claim, "numbers_found": numbers_in_claim, "verified": False, "status": "unverifiable"}

    for num in numbers_in_claim:
        if num in docs_context:
            result["verified"] = True
            result["status"] = "supported"
            idx = docs_context.find(num)
            start = max(0, idx - 100)
            end = min(len(docs_context), idx + 100)
            result["evidence"] = docs_context[start:end].strip()
            break

    if not result["verified"] and numbers_in_claim:
        result["status"] = "not_found_in_docs"
        result["warning"] = "Числа из утверждения НЕ найдены в документах. Возможна галлюцинация."

    return result


def portfolio_ranking(metric: str = "долг") -> dict:
    """Rank ALL portfolio companies by a metric. Reads dynamically from knowledge base.

    Args:
        metric: "долг", "выручка", "ebitda", "маржа", "дивиденды", "прибыль"

    Returns ranked list of all companies with the metric value and source.
    """
    kb = _get_kb()
    financials = kb.get("financials", {})
    portfolio = kb.get("portfolio", [])

    # Determine which metric to extract
    metric_lower = metric.lower()

    if any(x in metric_lower for x in ["дивиденд", "dividend", "выплат"]):
        metric_config = {"name": "Дивиденды", "keywords": ["дивиденд"], "search_portfolio": True}
    elif any(x in metric_lower for x in ["прибыл", "убыт", "profit", "чистая прибыль"]):
        metric_config = {"name": "Чистая прибыль / убыток", "keywords": ["чистая прибыль", "чистый убыток", "прибыль/убыток", "прибыль"], "search_portfolio": False}
    elif any(x in metric_lower for x in ["долг", "debt", "leverage", "нагрузк"]):
        metric_config = {"name": "Чистый долг / EBITDA", "keywords": ["чистый долг", "долг/ebitda", "долг/oibda", "долг"], "search_portfolio": False}
    elif any(x in metric_lower for x in ["выручк", "revenue", "продаж"]):
        metric_config = {"name": "Выручка", "keywords": ["выручка"], "search_portfolio": False}
    elif any(x in metric_lower for x in ["марж", "margin", "ebitda margin", "рентабельн"]):
        metric_config = {"name": "Маржа EBITDA", "keywords": ["рентабельность", "маржа", "oibda"], "search_portfolio": False}
    elif any(x in metric_lower for x in ["ebitda", "oibda"]):
        metric_config = {"name": "EBITDA / OIBDA", "keywords": ["oibda", "ebitda"], "search_portfolio": False}
    else:
        metric_config = {"name": "Чистый долг / EBITDA", "keywords": ["чистый долг", "долг"], "search_portfolio": False}

    ranked = []

    # Extract from financials section of KB
    for comp_name, indicators in financials.items():
        if not isinstance(indicators, list):
            continue

        # Skip holding-level consolidated data for company ranking
        if "КОНСОЛИДИРОВАННО" in comp_name.upper() and metric_config["name"] != "Чистый долг / EBITDA":
            # Include AFK consolidated only for debt metric
            pass

        for ind in indicators:
            if not isinstance(ind, dict):
                continue
            ind_name = ind.get("Показатель", "").lower()

            # Check if this indicator matches our metric keywords
            matched = any(kw in ind_name for kw in metric_config["keywords"])
            if not matched:
                continue

            # Get most recent value (prefer 2025, fall back to 2024)
            value_str = None
            period = None
            for year in ["2025", "2024", "2023"]:
                if year in ind and ind[year] and ind[year] != "—":
                    value_str = ind[year]
                    period = year
                    break

            if value_str is None:
                continue

            numeric_val = _parse_number(value_str)
            period_detail = _extract_period(value_str)
            if period_detail:
                period = f"{period_detail} {period}"

            # Short company name (strip sector info in parentheses)
            short_name = comp_name.split("(")[0].strip().replace("«", "").replace("»", "")

            entry = {
                "company": short_name,
                "metric": metric_config["name"],
                "value": numeric_val,
                "raw_value": value_str,
                "unit": ind.get("Показатель", "").split(",")[-1].strip() if "," in ind.get("Показатель", "") else "",
                "period": period,
                "source": f"KB АФК Система ({period})",
                "comment": ind.get("Комментарий", ""),
            }
            ranked.append(entry)
            break  # Only one match per company per metric

    # Enrich with portfolio data if relevant (e.g. for dividends, IPO)
    if metric_config.get("search_portfolio"):
        portfolio_names_in_ranked = {r["company"].lower() for r in ranked}
        for company in portfolio:
            name = company.get("Актив", "")
            short = name.split("(")[0].strip()
            if short.lower() not in portfolio_names_in_ranked:
                desc = company.get("Описание", "") + " " + company.get("Ключевые метрики", "")
                if any(kw in desc.lower() for kw in metric_config["keywords"]):
                    ranked.append({
                        "company": short,
                        "metric": metric_config["name"],
                        "value": None,
                        "raw_value": "см. описание",
                        "unit": "",
                        "period": "—",
                        "source": "KB АФК Система (портфель)",
                        "comment": desc[:200],
                    })

    # Sort: companies with values first (descending by absolute value), then None
    ranked.sort(key=lambda x: (x["value"] is None, -(abs(x["value"]) if x["value"] is not None else 0)))

    return {
        "metric": metric_config["name"],
        "ranking": ranked,
        "total_companies": len(ranked),
        "leader": ranked[0]["company"] if ranked and ranked[0]["value"] is not None else "н/д",
        "source": "Динамический расчёт из knowledge_base.json (АФК Система)",
    }


# =============================================
# NEW ANALYTICAL TOOLS (v2)
# =============================================

def sensitivity_analysis(cash_flows: list, base_rate: float, variable: str = "discount_rate",
                         range_pct: float = 0.3, steps: int = 5) -> dict:
    """Generate NPV sensitivity table by varying one key parameter.

    Args:
        cash_flows: list of cash flows (first is typically negative = investment)
        base_rate: base discount rate (e.g. 0.15 for 15%)
        variable: which variable to vary ("discount_rate" or "revenue")
        range_pct: variation range as fraction (0.3 = ±30%)
        steps: number of steps on each side

    Returns matrix of NPV values at different parameter levels.
    """
    from app.services.financial_calculator import calculate_npv

    cf = [float(x) for x in cash_flows]
    base_rate = float(base_rate)
    range_pct = float(range_pct)
    steps = int(steps)

    result = {"variable": variable, "base_rate": base_rate, "base_npv": None, "sensitivity": []}

    try:
        base_npv = calculate_npv(cf, base_rate)
        result["base_npv"] = base_npv

        if variable == "discount_rate":
            for i in range(-steps, steps + 1):
                delta = range_pct * i / steps
                rate = base_rate * (1 + delta)
                if rate <= 0:
                    continue
                npv = calculate_npv(cf, rate)
                result["sensitivity"].append({
                    "rate": round(rate * 100, 1),
                    "rate_label": f"{rate:.1%}",
                    "npv": npv,
                    "delta_from_base": round(npv - base_npv, 2),
                    "delta_pct": round((npv - base_npv) / abs(base_npv) * 100, 1) if base_npv != 0 else 0,
                })
        elif variable == "revenue":
            # Vary all positive cash flows (revenue proxy)
            for i in range(-steps, steps + 1):
                delta = range_pct * i / steps
                adjusted_cf = []
                for c in cf:
                    if c > 0:
                        adjusted_cf.append(c * (1 + delta))
                    else:
                        adjusted_cf.append(c)  # Keep investment fixed
                npv = calculate_npv(adjusted_cf, base_rate)
                result["sensitivity"].append({
                    "revenue_change": f"{delta:+.0%}",
                    "npv": npv,
                    "delta_from_base": round(npv - base_npv, 2),
                    "delta_pct": round((npv - base_npv) / abs(base_npv) * 100, 1) if base_npv != 0 else 0,
                })

        # 2D sensitivity: discount_rate vs revenue (compact 5x5)
        result["matrix_2d"] = []
        rates = [base_rate * (1 + range_pct * i / 3) for i in range(-3, 4) if base_rate * (1 + range_pct * i / 3) > 0]
        revenue_deltas = [-0.2, -0.1, 0, 0.1, 0.2]
        for rate in rates:
            row = {"rate": f"{rate:.1%}"}
            for rd in revenue_deltas:
                adj_cf = [c * (1 + rd) if c > 0 else c for c in cf]
                npv = calculate_npv(adj_cf, rate)
                row[f"rev_{rd:+.0%}"] = npv
            result["matrix_2d"].append(row)
        result["matrix_2d_labels"] = {"rows": "Ставка дисконтирования", "cols": "Изменение выручки"}

    except Exception as e:
        result["error"] = str(e)

    return result


def scenario_analysis(base_cf: list, discount_rate: float,
                      optimistic_adj: float = 0.15, pessimistic_adj: float = -0.25,
                      prob_bull: float = 0.2, prob_base: float = 0.5, prob_bear: float = 0.3) -> dict:
    """Bull/Base/Bear scenario analysis with probability-weighted expected NPV.

    Args:
        base_cf: base case cash flows
        discount_rate: discount rate
        optimistic_adj: revenue adjustment for bull case (e.g. 0.15 = +15%)
        pessimistic_adj: revenue adjustment for bear case (e.g. -0.25 = -25%)
        prob_bull/base/bear: scenario probabilities (must sum to 1.0)
    """
    from app.services.financial_calculator import calculate_npv, calculate_irr

    cf = [float(x) for x in base_cf]
    rate = float(discount_rate)
    opt = float(optimistic_adj)
    pess = float(pessimistic_adj)
    pb, pba, pbe = float(prob_bull), float(prob_base), float(prob_bear)

    result = {"scenarios": [], "expected_npv": None, "expected_irr": None}

    try:
        scenarios = [
            ("Bull Case", opt, pb),
            ("Base Case", 0.0, pba),
            ("Bear Case", pess, pbe),
        ]

        npvs = []
        for name, adj, prob in scenarios:
            adj_cf = [c * (1 + adj) if c > 0 else c for c in cf]
            npv = calculate_npv(adj_cf, rate)
            irr = calculate_irr(adj_cf)
            payback = _calc_payback(adj_cf)

            scenario = {
                "name": name,
                "revenue_adjustment": f"{adj:+.0%}",
                "probability": f"{prob:.0%}",
                "npv": npv,
                "irr": irr,
                "payback_years": payback,
                "weighted_npv": round(npv * prob, 2),
            }
            result["scenarios"].append(scenario)
            npvs.append((npv, irr, prob))

        result["expected_npv"] = round(sum(n * p for n, _, p in npvs), 2)
        result["expected_irr"] = round(sum(i * p for _, i, p in npvs if i is not None), 1) if all(i is not None for _, i, _ in npvs) else None
        result["unit"] = "млрд руб."
        result["recommendation"] = "ПОЛОЖИТЕЛЬНАЯ" if result["expected_npv"] > 0 and npvs[2][0] > -abs(cf[0]) * 0.5 else "ТРЕБУЕТ ДОРАБОТКИ" if result["expected_npv"] > 0 else "ОТРИЦАТЕЛЬНАЯ"

    except Exception as e:
        result["error"] = str(e)

    return result


def _calc_payback(cash_flows: list) -> float | None:
    """Calculate simple payback period."""
    cumulative = 0
    for i, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0 and i > 0:
            # Interpolate
            prev = cumulative - cf
            if cf > 0:
                return round(i - 1 + abs(prev) / cf, 1)
            return float(i)
    return None


def comparable_valuation(target_ebitda: float, peer_multiples: list, target_net_debt: float = 0) -> dict:
    """Implied valuation from peer EV/EBITDA multiples.

    Args:
        target_ebitda: target company EBITDA (млрд руб.)
        peer_multiples: list of peer EV/EBITDA multiples (e.g. [6.5, 7.2, 8.1, 5.8])
        target_net_debt: target net debt for equity bridge (млрд руб.)

    Returns valuation range (25th, median, 75th percentile).
    """
    ebitda = float(target_ebitda)
    debt = float(target_net_debt)
    multiples = sorted([float(m) for m in peer_multiples])

    result = {"target_ebitda": ebitda, "target_net_debt": debt, "peer_count": len(multiples)}

    try:
        if len(multiples) < 2:
            result["error"] = "Нужно минимум 2 пира для анализа"
            return result

        median_m = statistics.median(multiples)
        p25 = multiples[max(0, len(multiples) // 4)]
        p75 = multiples[min(len(multiples) - 1, 3 * len(multiples) // 4)]
        mean_m = statistics.mean(multiples)

        result["multiples"] = {
            "all": multiples,
            "p25": round(p25, 1),
            "median": round(median_m, 1),
            "p75": round(p75, 1),
            "mean": round(mean_m, 1),
        }

        # Implied EV
        result["implied_ev"] = {
            "low": round(ebitda * p25, 1),
            "mid": round(ebitda * median_m, 1),
            "high": round(ebitda * p75, 1),
            "unit": "млрд руб.",
        }

        # Implied equity
        result["implied_equity"] = {
            "low": round(ebitda * p25 - debt, 1),
            "mid": round(ebitda * median_m - debt, 1),
            "high": round(ebitda * p75 - debt, 1),
            "unit": "млрд руб.",
        }

        result["formula"] = f"Implied EV = EBITDA ({ebitda} млрд) × EV/EBITDA (median {median_m:.1f}x) = {ebitda * median_m:.1f} млрд руб."

    except Exception as e:
        result["error"] = str(e)

    return result


def financial_health_score(company_name: str) -> dict:
    """Compute composite financial health score for a portfolio company.

    Reads data from KB and scores on: debt load, profitability, margins, growth, dividend capacity.
    Returns letter grade A-F with justification.
    """
    kb = _get_kb()
    financials = kb.get("financials", {})

    # Find company in KB
    comp_data = None
    comp_key = None
    for key, indicators in financials.items():
        if company_name.lower() in key.lower():
            comp_data = indicators
            comp_key = key
            break

    if not comp_data:
        return {"company": company_name, "error": f"Компания '{company_name}' не найдена в базе знаний"}

    result = {"company": comp_key, "scores": {}, "raw_data": {}, "grade": None, "total_score": 0}

    # Extract key metrics from indicators
    metrics = {}
    for ind in comp_data:
        if not isinstance(ind, dict):
            continue
        name = ind.get("Показатель", "").lower()
        # Get most recent value
        for year in ["2025", "2024", "2023"]:
            if year in ind and ind[year] and ind[year] != "—":
                val = _parse_number(ind[year])
                if val is not None:
                    metrics[name] = {"value": val, "raw": ind[year], "year": year, "comment": ind.get("Комментарий", "")}
                break

    result["raw_data"] = {k: v["raw"] for k, v in metrics.items()}

    # Score components (each 0-10)
    scores = {}

    # 1. Revenue growth
    for key in metrics:
        if "выручка" in key:
            comment = metrics[key].get("comment", "")
            growth_match = re.search(r'([+-]?\d+[.,]?\d*)\s*%', comment)
            if growth_match:
                growth = float(growth_match.group(1).replace(",", "."))
                if growth > 30: scores["revenue_growth"] = 10
                elif growth > 20: scores["revenue_growth"] = 8
                elif growth > 10: scores["revenue_growth"] = 7
                elif growth > 0: scores["revenue_growth"] = 5
                elif growth > -10: scores["revenue_growth"] = 3
                else: scores["revenue_growth"] = 1
                result["raw_data"]["growth"] = f"{growth}%"
            break

    # 2. EBITDA margin proxy
    revenue_val = None
    ebitda_val = None
    for key in metrics:
        if "выручка" in key and revenue_val is None:
            revenue_val = metrics[key]["value"]
        if any(x in key for x in ["oibda", "ebitda"]) and "рентабельность" not in key and ebitda_val is None:
            ebitda_val = metrics[key]["value"]

    if revenue_val and ebitda_val and revenue_val > 0:
        margin = ebitda_val / revenue_val * 100
        if margin > 30: scores["ebitda_margin"] = 9
        elif margin > 20: scores["ebitda_margin"] = 7
        elif margin > 10: scores["ebitda_margin"] = 5
        elif margin > 0: scores["ebitda_margin"] = 3
        else: scores["ebitda_margin"] = 1
        result["raw_data"]["ebitda_margin"] = f"{margin:.1f}%"

    # 3. Profitability
    for key in metrics:
        if "прибыль" in key or "убыток" in key:
            val = metrics[key]["value"]
            if val > 10: scores["profitability"] = 9
            elif val > 0: scores["profitability"] = 7
            elif val > -5: scores["profitability"] = 4
            elif val > -20: scores["profitability"] = 2
            else: scores["profitability"] = 0
            break

    # 4. Debt load
    for key in metrics:
        if "долг" in key:
            comment = metrics[key].get("comment", "")
            ratio_match = re.search(r'(\d+[.,]?\d*)\s*x', comment)
            if ratio_match:
                ratio = float(ratio_match.group(1).replace(",", "."))
                if ratio < 1: scores["debt_load"] = 10
                elif ratio < 2: scores["debt_load"] = 8
                elif ratio < 3: scores["debt_load"] = 6
                elif ratio < 5: scores["debt_load"] = 3
                else: scores["debt_load"] = 1
                result["raw_data"]["debt_ebitda"] = f"{ratio}x"
            break

    # Calculate total
    if scores:
        weights = {"revenue_growth": 0.25, "ebitda_margin": 0.25, "profitability": 0.25, "debt_load": 0.25}
        total = sum(scores.get(k, 5) * w for k, w in weights.items())
        result["total_score"] = round(total, 1)
        result["scores"] = {k: {"score": v, "max": 10} for k, v in scores.items()}

        # Letter grade
        if total >= 8: result["grade"] = "A"
        elif total >= 6.5: result["grade"] = "B"
        elif total >= 5: result["grade"] = "C"
        elif total >= 3: result["grade"] = "D"
        else: result["grade"] = "F"

        grade_descriptions = {
            "A": "Отличное финансовое здоровье. Кандидат на IPO / дивиденды.",
            "B": "Хорошее финансовое здоровье. Стабильный актив.",
            "C": "Удовлетворительное. Есть зоны для улучшения.",
            "D": "Слабое финансовое здоровье. Требует внимания.",
            "F": "Критическое состояние. Требует реструктуризации."
        }
        result["assessment"] = grade_descriptions.get(result["grade"], "")
    else:
        result["grade"] = "N/A"
        result["assessment"] = "Недостаточно данных для оценки"

    return result


# =============================================
# TOOL REGISTRY
# =============================================

TOOLS = {
    "data_query": {
        "fn": data_query,
        "description": "Запрос структурированных данных из базы знаний. Параметры: entity (название компании или 'all'/'overview'/'макро'), metric (опционально: 'выручка', 'EBITDA', 'долг'), years (опционально: ['2024', '2025'])",
        "examples": [
            'data_query(entity="МТС", metric="выручка")',
            'data_query(entity="all", metric="EBITDA")',
            'data_query(entity="overview")',
            'data_query(entity="макро")',
        ]
    },
    "calculate": {
        "fn": calculate,
        "description": "Детерминированные финансовые расчёты. Операции: growth(old, new), ratio(numerator, denominator), margin(profit, revenue), npv(cash_flows, discount_rate), irr(cash_flows), compare(values), wacc(equity_cost, debt_cost, equity_weight, tax_rate)",
        "examples": [
            'calculate(operation="growth", old=530, new=608)',
            'calculate(operation="npv", cash_flows=[-3500, 256, 268, 280, 295], discount_rate=0.15)',
            'calculate(operation="wacc", equity_cost=0.22, debt_cost=0.16, equity_weight=0.6, tax_rate=0.20)',
        ]
    },
    "cross_doc_check": {
        "fn": cross_doc_check,
        "description": "Проверка утверждения против документов. Возвращает verified=True/False и evidence.",
        "examples": [
            'cross_doc_check(claim="Рост выручки МТС +19%", docs_context="...")',
        ]
    },
    "portfolio_ranking": {
        "fn": portfolio_ranking,
        "description": "Ранжирование ВСЕХ компаний портфеля по метрике (динамически из KB). Метрики: 'долг', 'выручка', 'ebitda', 'маржа', 'дивиденды', 'прибыль'. ИСПОЛЬЗУЙ для сравнительных и обзорных вопросов.",
        "examples": [
            'portfolio_ranking(metric="долг")',
            'portfolio_ranking(metric="выручка")',
            'portfolio_ranking(metric="дивиденды")',
            'portfolio_ranking(metric="прибыль")',
        ]
    },
    "sensitivity_analysis": {
        "fn": sensitivity_analysis,
        "description": "Анализ чувствительности NPV. Генерирует таблицу NPV при вариации ставки дисконтирования и/или выручки. ОБЯЗАТЕЛЬНО для инвестиционного анализа.",
        "examples": [
            'sensitivity_analysis(cash_flows=[-3500, 256, 268, 280, 295, 310], base_rate=0.15)',
            'sensitivity_analysis(cash_flows=[-3500, 256, 268, 280], base_rate=0.15, variable="revenue", range_pct=0.3)',
        ]
    },
    "scenario_analysis": {
        "fn": scenario_analysis,
        "description": "Сценарный анализ Bull/Base/Bear с вероятностно-взвешенным NPV/IRR. Показывает NPV при оптимистичном, базовом и пессимистичном сценариях.",
        "examples": [
            'scenario_analysis(base_cf=[-3500, 256, 268, 280, 295], discount_rate=0.15)',
            'scenario_analysis(base_cf=[-3500, 256, 268, 280], discount_rate=0.15, optimistic_adj=0.2, pessimistic_adj=-0.3)',
        ]
    },
    "comparable_valuation": {
        "fn": comparable_valuation,
        "description": "Оценка через мультипликаторы аналогов (EV/EBITDA). Рассчитывает implied EV и equity value на основе медианы пиров.",
        "examples": [
            'comparable_valuation(target_ebitda=279.7, peer_multiples=[5.2, 6.1, 7.3, 4.8], target_net_debt=458.3)',
        ]
    },
    "financial_health_score": {
        "fn": financial_health_score,
        "description": "Композитный скор финансового здоровья компании (A-F). Оценивает: рост выручки, маржу, прибыльность, долговую нагрузку. Данные из KB.",
        "examples": [
            'financial_health_score(company_name="МТС")',
            'financial_health_score(company_name="Segezha")',
        ]
    },
}

def get_tools_description() -> str:
    """Get formatted tool descriptions for the system prompt."""
    lines = ["ДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"]
    for name, tool in TOOLS.items():
        lines.append(f"### {name}")
        lines.append(f"{tool['description']}")
        lines.append("Примеры вызова:")
        for ex in tool["examples"]:
            lines.append(f"  {ex}")
        lines.append("")
    return "\n".join(lines)

def execute_tool(tool_call: str, docs_context: str = "") -> dict:
    """Parse and execute a tool call string.

    Expects format: tool_name(arg1="val1", arg2="val2")
    """
    match = re.match(r'(\w+)\((.*)\)', tool_call.strip(), re.DOTALL)
    if not match:
        return {"error": f"Cannot parse tool call: {tool_call}"}

    name = match.group(1)
    args_str = match.group(2)

    if name not in TOOLS:
        return {"error": f"Unknown tool: {name}"}

    kwargs = {}
    for m in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*?)"|\'([^\']*?)\'|\[([^\]]*)\]|\{([^}]*)\}|([^,\)]+))', args_str):
        key = m.group(1)
        val = m.group(2) or m.group(3) or None
        if val is None:
            if m.group(4) is not None:  # list
                val = [x.strip().strip('"\'') for x in m.group(4).split(",")]
            elif m.group(5) is not None:  # dict
                val = {}
                for pair in re.finditer(r'"([^"]+)":\s*([^,}]+)', m.group(5)):
                    val[pair.group(1)] = pair.group(2).strip().strip('"\'')
            else:
                val = m.group(6).strip()
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except ValueError:
                    pass
        kwargs[key] = val

    if name == "cross_doc_check" and "docs_context" not in kwargs:
        kwargs["docs_context"] = docs_context

    try:
        result = TOOLS[name]["fn"](**kwargs)
        return result
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
