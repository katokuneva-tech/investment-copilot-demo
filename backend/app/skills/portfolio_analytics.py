from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.companies import COMPANIES, COMPANY_ORDER, COMPANIES_WITH_FINANCIALS
from app.data.holding import HOLDING_OVERVIEW, HOLDING_EVENTS, SECTORS, IPO_CANDIDATES


def _fmt(val, suffix="", default="н/д"):
    """Format a numeric value or return default."""
    if val is None:
        return default
    if isinstance(val, float):
        if abs(val) >= 100:
            return f"{val:,.0f}{suffix}".replace(",", " ")
        return f"{val:.1f}{suffix}"
    return str(val)


class PortfolioAnalyticsSkill(BaseSkill):
    async def handle(self, message: str, session_id: str, extra_context: str = "") -> ChatResponse:
        msg = message.lower()
        if self._match(msg, ["сектор", "отрасл", "диверсифик"]):
            return self._sector_analysis()
        elif self._match(msg, ["ipo", "размещени", "выход на биржу"]):
            return self._ipo_pipeline()
        elif self._match(msg, ["событи", "сделк", "новост", "хронолог"]):
            return self._events_timeline()
        elif self._match(msg, ["холдинг", "система", "afk", "афк", "корпорац"]):
            return self._holding_overview()
        elif self._match(msg, ["рост", "растет", "быстр", "лидер", "выручк"]):
            return self._growth_analysis()
        elif self._match(msg, ["долг", "долгов", "ковенант", "leverage", "нагрузк"]):
            return self._debt_analysis()
        elif self._match(msg, ["дивиденд", "выплат"]):
            return self._dividend_analysis()
        else:
            return self._portfolio_overview()

    def _portfolio_overview(self) -> ChatResponse:
        # Full portfolio table — all 23 companies
        all_rows = []
        for key in COMPANY_ORDER:
            c = COMPANIES[key]
            all_rows.append([c["name"], c["sector"], c["status"], c.get("stake", ""), c.get("ipo_plans", "") or "—"])

        # Financial summary — companies with data
        fin_rows = []
        chart_data = []
        for key in COMPANIES_WITH_FINANCIALS:
            if key == "afk_sistema":
                continue
            c = COMPANIES[key]
            rev = c.get("revenue_2024") or c.get("revenue_2025")
            margin = c.get("ebitda_margin")
            debt = c.get("net_debt_ebitda")
            growth = c.get("revenue_growth")
            fin_rows.append([c["name"], c["sector"], _fmt(rev), _fmt(margin, "%"), _fmt(debt, "x"), _fmt(growth, "%")])
            if rev:
                chart_data.append({"name": c["name"][:12], "revenue": rev})

        afk = COMPANIES.get("afk_sistema", {})
        afk_rev = _fmt(afk.get("revenue_2024"), " млрд")

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## Обзор портфеля АФК Система\n\n**23 портфельные компании** в 17 секторах. Совокупная выручка холдинга (2024): {afk_rev} руб. Активы: 2,9 трлн руб.\n\n**Ключевые активы**: МТС (~60% выручки, ~80% OIBDA), Ozon (997.9 млрд выручки, +63% г/г), Segezha (проблемный, Долг/OIBDA 14.4x). **Кандидаты на IPO**: МЕДСИ, Биннофарм, СТЕПЬ, Cosmos Hotel Group."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Статус", "Доля АФК", "IPO планы"],
                "rows": all_rows,
                "caption": f"Все портфельные компании АФК Система ({len(all_rows)} активов)",
            }),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Выручка, млрд", "Маржа EBITDA", "Долг/EBITDA", "Рост"],
                "rows": fin_rows,
                "caption": "Финансовые показатели ключевых компаний (2024/2025)",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Выручка ключевых компаний (млрд руб.)",
                "x_key": "name",
                "series": [{"name": "Выручка", "data_key": "revenue", "color": "#E11D48"}],
                "data": chart_data,
            }),
        ])

    def _growth_analysis(self) -> ChatResponse:
        companies = [(k, COMPANIES[k]) for k in COMPANIES_WITH_FINANCIALS if k != "afk_sistema" and COMPANIES[k].get("revenue_growth") is not None]
        companies.sort(key=lambda x: x[1]["revenue_growth"], reverse=True)

        rows = []
        chart_data = []
        for key, c in companies:
            r23 = c.get("revenue_2023")
            r24 = c.get("revenue_2024")
            r25 = c.get("revenue_2025")
            growth = c.get("revenue_growth")
            rows.append([c["name"], c["sector"], _fmt(r23), _fmt(r24), _fmt(r25), _fmt(growth, "%")])
            chart_data.append({"name": c["name"][:12], "2023": r23 or 0, "2024": r24 or 0, "2025": r25 or 0})

        if not companies:
            return ChatResponse(session_id="", blocks=[ContentBlock(type="text", data="Нет данных о росте компаний.")])

        leader_name = companies[0][1]["name"]
        leader_growth = companies[0][1]["revenue_growth"]
        second_name = companies[1][1]["name"] if len(companies) > 1 else ""
        second_growth = companies[1][1]["revenue_growth"] if len(companies) > 1 else 0

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## Анализ роста выручки\n\n**Лидер роста — Ozon** с выручкой 997.9 млрд (+63% г/г, почти 1 трлн!). На втором месте — **Эталон** (+44% г/г) за счет активного девелопмента. **МТС** стабильно растет на +14.7%, впервые преодолев отметку 800 млрд.\n\n**Segezha** показывает рост выручки на +15% (2024 vs 2023), однако компания остается убыточной с чистым убытком 22.3 млрд руб. за 2024 год.\n\n**МЕДСИ** растет на +22% г/г — один из лидеров портфеля, кандидат на IPO в 2026."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Выр. 2023", "Выр. 2024", "Выр. 2025", "Рост"],
                "rows": rows,
                "caption": "Рейтинг по росту выручки",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Динамика выручки (млрд руб.)",
                "x_key": "name",
                "series": [
                    {"name": "2023", "data_key": "2023", "color": "#94A3B8"},
                    {"name": "2024", "data_key": "2024", "color": "#3B82F6"},
                    {"name": "2025", "data_key": "2025", "color": "#E11D48"},
                ],
                "data": chart_data,
            }),
        ])

    def _debt_analysis(self) -> ChatResponse:
        companies = [(k, COMPANIES[k]) for k in COMPANIES_WITH_FINANCIALS if k != "afk_sistema" and COMPANIES[k].get("net_debt_ebitda") is not None]
        companies.sort(key=lambda x: x[1]["net_debt_ebitda"], reverse=True)

        rows = []
        chart_data = []
        for key, c in companies:
            risk = "🔴 КРИТИЧЕСКИЙ" if c["net_debt_ebitda"] > 5 else ("⚠️ РИСК" if c.get("covenant_risk") else "✅ OK")
            ebitda = c.get("ebitda_2024") or c.get("ebitda_2025")
            rows.append([c["name"], _fmt(c["net_debt"]), _fmt(ebitda), f"{c['net_debt_ebitda']}x", risk])
            chart_data.append({"name": c["name"][:12], "debt_ratio": min(c["net_debt_ebitda"], 15)})  # cap for chart readability

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="## Анализ долговой нагрузки\n\n**🔴 Критическая ситуация: Segezha Group** — Общий долг/OIBDA = **14.4x** (2023). Это критический уровень. Компания генерирует убытки (22.3 млрд за 2024) и не способна обслуживать долг из операционного потока. АФК Система характеризует ситуацию как «управляемую».\n\n**МТС** — комфортный уровень 1.6x. Долг снизился на 3.9% г/г до 458.3 млрд.\n\n**Эталон** — стабильно 2.5x, в целевом диапазоне <3x.\n\n**Корпоративный центр АФК**: чистый долг 386.6 млрд руб., пик погашений в 2026 году (38% всех обязательств). Рейтинг АКРА: АА- с негативным прогнозом."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Чист. долг, млрд", "EBITDA, млрд", "Долг/EBITDA", "Статус"],
                "rows": rows,
                "caption": "Долговая нагрузка портфельных компаний",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Чистый долг / EBITDA",
                "x_key": "name",
                "series": [{"name": "Долг/EBITDA", "data_key": "debt_ratio", "color": "#E11D48"}],
                "data": chart_data,
            }),
        ])

    def _dividend_analysis(self) -> ChatResponse:
        from app.services.tools import portfolio_ranking
        result = portfolio_ranking("дивиденды")

        rows = []
        for c in result["ranking"]:
            val = f"{c['value']} {c.get('unit','')}" if c.get("value") is not None else "н/д"
            rows.append([c["company"], c.get("status", ""), val, c.get("source", "")])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                "## Кто сможет заплатить дивиденды в 2026 году?\n\n"
                "### [ДА] Подтверждённые дивиденды\n"
                "- **МТС** — главный дивидендный актив. 35 руб./акция (дивиденд за 2024 выплачен июль 2025). Политика: не менее 35 руб. в 2024-2026\n"
                "- **Ozon** — впервые рекомендовал дивиденды: 31 млрд руб. (ноябрь 2025). АФК получит ~10 млрд руб.\n\n"
                "### [ВОЗМОЖНО] Прибыльные, но дивиденды не утверждены\n"
                "- **МЕДСИ** — чистая прибыль 5.2 млрд (x2.5 г/г), но готовится к IPO\n"
                "- **Биннофарм** — EBITDA 9.6 млрд, но готовится к IPO\n"
                "- **СТЕПЬ** — OIBDA 22.7 млрд (+52.8%), но готовится к IPO\n\n"
                "### [НЕТ] Не смогут\n"
                "- **Эталон** — убыток 8.9 млрд (1П 2025) из-за роста ставки ЦБ\n"
                "- **Segezha** — убыток 19.5 млрд (9М), дивиденды приостановлены СД\n"
                "- **АФК Система** — дивиденды за 2024 НЕ выплачены, убыток 124.3 млрд (9М)\n\n"
                "*Источники: IR-сайты компаний, ТАСС, Smart-Lab, Ведомости*"
            )),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Статус", "Размер дивиденда", "Источник"],
                "rows": rows,
                "caption": "Дивидендный потенциал портфеля АФК Система (2026)",
            }),
        ])

    # ═══════════════════════════════════════════
    # NEW HANDLERS
    # ═══════════════════════════════════════════

    def _sector_analysis(self) -> ChatResponse:
        rows = []
        for s in SECTORS:
            rows.append([
                s.get("Сектор", ""),
                s.get("Активы", ""),
                s.get("Вклад в выручку/OIBDA", ""),
                s.get("Перспектива", ""),
            ])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="## Секторная диверсификация портфеля\n\nАФК Система управляет **23+ компаниями в 17 секторах** — от телекома до космических технологий.\n\n**Якорный сектор**: Телеком/IT (МТС) — ~60% выручки, ~80% OIBDA.\n**Быстрорастущие**: E-commerce (Ozon, +63%), Медицина (МЕДСИ, +22%), Девелопмент (Эталон, +44%).\n**Новые стратегические**: Робототехника (консолидирована в марте 2026), Космос (ГК Спутникс), БПЛА (Аэромакс).\n**Проблемный**: Лесопром (Segezha, Долг/OIBDA 14.4x)."),
            ContentBlock(type="table", data={
                "headers": ["Сектор", "Активы", "Вклад в выручку/OIBDA", "Перспектива"],
                "rows": rows,
                "caption": f"Секторная карта портфеля ({len(SECTORS)} секторов)",
            }),
        ])

    def _ipo_pipeline(self) -> ChatResponse:
        rows = []
        for c in IPO_CANDIDATES:
            rows.append([c["name"], c["sector"], c["stake"], c["ipo_plans"], c.get("key_metrics", "")])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## IPO Pipeline АФК Система\n\n**{len(IPO_CANDIDATES)} компании** готовятся к IPO в 2025-2026 году. Это ключевой механизм монетизации и снижения долговой нагрузки корпоративного центра (386.6 млрд руб.).\n\n- **МЕДСИ** — #1 частная сеть клиник в РФ (Forbes). Выручка +22% г/г. Активные переговоры с финансовыми инвесторами.\n- **Биннофарм Групп** — маржа OIBDA 26%. Расширение производства и экспорта.\n- **Агрохолдинг СТЕПЬ** — выручка >100 млрд, 4-е место по производству молока в РФ. Переговоры с частными инвесторами.\n- **Cosmos Hotel Group** — развитие сети отелей, растущий туристический рынок."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Доля АФК", "Планы IPO", "Ключевые метрики"],
                "rows": rows,
                "caption": "Кандидаты на IPO (2025-2026)",
            }),
        ])

    def _events_timeline(self) -> ChatResponse:
        rows = []
        for e in HOLDING_EVENTS:
            rows.append([
                e.get("Дата", ""),
                e.get("Событие", ""),
                e.get("Детали", ""),
                e.get("Значение для холдинга", ""),
            ])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## Ключевые события 2025-2026\n\n**{len(HOLDING_EVENTS)} сделок и событий** за последний год:\n\n- **Март 2026**: Консолидация 100% Корпорации робототехники — стратегия лидерства в промышленной робототехнике.\n- **Декабрь 2025**: Продажа 37.6% ГК «Элемент» Сбербанку — монетизация актива для снижения долга.\n- **Ноябрь 2025**: Ozon рекомендовал дивиденды 31 млрд — АФК может получить ~10 млрд.\n- **Август 2025**: Допэмиссия Эталона на 14.1 млрд — выкуп портфеля недвижимости у АФК."),
            ContentBlock(type="table", data={
                "headers": ["Дата", "Событие", "Детали", "Значение"],
                "rows": rows,
                "caption": "Хронология ключевых событий",
            }),
        ])

    def _holding_overview(self) -> ChatResponse:
        rows = []
        # Key metrics to highlight
        key_params = [
            "Тикер (МосБиржа)", "Контролирующий акционер", "Президент",
            "Совокупные активы группы (30.09.2025)", "Консолидированная выручка (9М 2025)",
            "Скорр. OIBDA Q3 2025", "Рентабельность по OIBDA Q3 2025",
            "Чистый убыток (9М 2025)", "Чистый долг корп. центра",
            "Конс. финансовые обязательства", "Рейтинг (АКРА)",
            "Цена акции (21.03.2026)", "Пик погашения долга",
            "Ожидаемый эффект от снижения ставок",
            "Фактические дивиденды за 2024/2025",
        ]
        for param in key_params:
            val = HOLDING_OVERVIEW.get(param, "")
            if val:
                rows.append([param, val])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="## АФК Система — обзор холдинга\n\n**ПАО «АФК Система»** (AFKS) — крупнейшая публичная инвестиционная корпорация России. Управляет портфелем 23+ компаний с совокупными активами 2.9 трлн руб.\n\n**Ключевые вызовы 2025-2026:**\n- Чистый убыток 124.3 млрд (9М 2025) vs прибыль 1.8 млрд годом ранее — давление процентных расходов\n- Пик погашения долга в 2026 году (38% всех обязательств)\n- Дивиденды приостановлены\n- Рейтинг АКРА: АА- с негативным прогнозом\n\n**Стратегия**: IPO дочерних компаний (МЕДСИ, Биннофарм, СТЕПЬ, Cosmos Hotel) для снижения долга. Ожидаемый эффект от снижения ставок — конец 2026/2027."),
            ContentBlock(type="table", data={
                "headers": ["Параметр", "Значение"],
                "rows": rows,
                "caption": "Ключевые показатели АФК Система",
            }),
        ])
