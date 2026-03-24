from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.companies import COMPANIES, COMPANY_ORDER


class PortfolioAnalyticsSkill(BaseSkill):
    async def handle(self, message: str, session_id: str) -> ChatResponse:
        if self._match(message, ["рост", "растет", "быстр", "лидер", "выручк"]):
            return self._growth_analysis()
        elif self._match(message, ["долг", "долгов", "ковенант", "leverage"]):
            return self._debt_analysis()
        elif self._match(message, ["дивиденд", "выплат"]):
            return self._dividend_analysis()
        else:
            return self._portfolio_overview()

    def _portfolio_overview(self) -> ChatResponse:
        rows = []
        chart_data = []
        for key in COMPANY_ORDER:
            c = COMPANIES[key]
            rows.append([
                c["name"], c["sector"],
                f"{c['revenue_2025']:.0f}",
                f"{c['ebitda_margin']}%",
                f"{c['net_debt_ebitda']}x",
                f"{c['revenue_growth']:+.1f}%",
                f"{c['ev_ebitda']}x",
            ])
            chart_data.append({"name": c["name"], "revenue": c["revenue_2025"], "ebitda_margin": c["ebitda_margin"]})

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="## Обзор портфеля АФК Система\n\nПортфель включает 5 ключевых компаний в различных секторах. МТС остается якорным активом с наибольшей выручкой (679 млрд) и высокой маржинальностью (42%). СТЕПЬ и Биннофарм демонстрируют наибольшую динамику роста. Segezha остается под давлением из-за высокой долговой нагрузки."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Выручка, млрд", "Маржа EBITDA", "Долг/EBITDA", "Рост YoY", "EV/EBITDA"],
                "rows": rows,
                "caption": "Ключевые финансовые показатели портфельных компаний (2025)",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Выручка портфельных компаний (2025, млрд руб.)",
                "x_key": "name",
                "series": [{"name": "Выручка", "data_key": "revenue", "color": "#E11D48"}],
                "data": chart_data,
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_1", "title": "Годовой отчет МТС 2025", "type": "annual_report", "page": "стр. 45"},
                {"id": "src_2", "title": "Консолидированная отчетность Segezha 2025", "type": "financial_statement", "page": "стр. 12"},
                {"id": "src_3", "title": "МСФО Эталон 2025", "type": "financial_statement", "page": "стр. 8"},
            ]),
        ])

    def _growth_analysis(self) -> ChatResponse:
        sorted_companies = sorted(COMPANY_ORDER, key=lambda k: COMPANIES[k]["revenue_growth"], reverse=True)
        rows = []
        chart_data = []
        for key in sorted_companies:
            c = COMPANIES[key]
            rows.append([c["name"], c["sector"], f"{c['revenue_2024']:.0f}", f"{c['revenue_2025']:.0f}", f"{c['revenue_growth']:+.1f}%"])
            chart_data.append({"name": c["name"], "2023": c["revenue_2023"], "2024": c["revenue_2024"], "2025": c["revenue_2025"]})

        leader = COMPANIES[sorted_companies[0]]
        second = COMPANIES[sorted_companies[1]]

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## Анализ роста выручки\n\n**Лидер роста — {leader['name']}** с темпом +{leader['revenue_growth']}% год к году. На втором месте — {second['name']} (+{second['revenue_growth']}%).\n\n{leader['name']}: {leader['description']}\n\nСамый медленный рост у Segezha Group (+2.9%), что связано с давлением на мировые цены на пиломатериалы и сложной макроситуацией в секторе."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Выручка 2024", "Выручка 2025", "Рост"],
                "rows": rows,
                "caption": "Рейтинг портфельных компаний по росту выручки",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Динамика выручки портфельных компаний (млрд руб.)",
                "x_key": "name",
                "series": [
                    {"name": "2023", "data_key": "2023", "color": "#94A3B8"},
                    {"name": "2024", "data_key": "2024", "color": "#3B82F6"},
                    {"name": "2025", "data_key": "2025", "color": "#E11D48"},
                ],
                "data": chart_data,
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_step", "title": "Годовой отчет СТЕПЬ 2025", "type": "annual_report", "page": "стр. 18"},
                {"id": "src_binno", "title": "Отчетность Биннофарм 2025", "type": "financial_statement", "page": "стр. 5"},
            ]),
        ])

    def _debt_analysis(self) -> ChatResponse:
        sorted_companies = sorted(COMPANY_ORDER, key=lambda k: COMPANIES[k]["net_debt_ebitda"], reverse=True)
        rows = []
        for key in sorted_companies:
            c = COMPANIES[key]
            risk = "⚠️ РИСК" if c["covenant_risk"] else "OK"
            rows.append([c["name"], f"{c['net_debt']:.0f}", f"{c['ebitda_2025']:.1f}", f"{c['net_debt_ebitda']}x", f"{c['covenant_threshold']}x", risk])

        chart_data = [{"name": COMPANIES[k]["name"], "debt_ratio": COMPANIES[k]["net_debt_ebitda"], "threshold": COMPANIES[k]["covenant_threshold"]} for k in sorted_companies]

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="## Анализ долговой нагрузки\n\n**⚠️ Критическая ситуация: Segezha Group** — Чистый долг/EBITDA = 4.2x при ковенантном пороге 4.5x. Буфер составляет всего 0.3x, что означает высокий риск нарушения ковенантов при любом ухудшении операционных показателей.\n\nSegezha приостановила выплату дивидендов и реализует программу снижения долга. При текущих темпах EBITDA снижение долговой нагрузки до приемлемого уровня (3.0x) займет 3-4 года.\n\nОстальные компании портфеля находятся в комфортной зоне — все ниже 2.5x."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Чист. долг, млрд", "EBITDA, млрд", "Долг/EBITDA", "Ковенант", "Статус"],
                "rows": rows,
                "caption": "Долговая нагрузка и ковенантные ограничения",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "Чистый долг / EBITDA vs ковенантный порог",
                "x_key": "name",
                "series": [
                    {"name": "Долг/EBITDA", "data_key": "debt_ratio", "color": "#E11D48"},
                    {"name": "Ковенантный порог", "data_key": "threshold", "color": "#94A3B8"},
                ],
                "data": chart_data,
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_seg_debt", "title": "Кредитное соглашение Segezha (синдицированный кредит)", "type": "legal", "page": "п. 8.2 Финансовые ковенанты"},
                {"id": "src_seg_report", "title": "Квартальный отчет Segezha Q4 2025", "type": "financial_statement", "page": "стр. 32"},
            ]),
        ])

    def _dividend_analysis(self) -> ChatResponse:
        rows = []
        for key in COMPANY_ORDER:
            c = COMPANIES[key]
            can = "✅ Да" if c["can_pay_dividends"] else "❌ Нет"
            fcf = f"{c['fcf_2025']:.1f}" if c["fcf_2025"] > 0 else f"{c['fcf_2025']:.1f}"
            rows.append([c["name"], fcf, f"{c['dividend_yield']}%", can, c["dividend_policy"]])

        payers = [COMPANIES[k]["name"] for k in COMPANY_ORDER if COMPANIES[k]["can_pay_dividends"]]

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=f"## Дивидендный потенциал портфеля\n\n**{len(payers)} из 5 компаний** способны выплатить дивиденды в 2025 году: {', '.join(payers)}.\n\n**МТС** — главный дивидендный актив портфеля с доходностью 12.5% и стабильной дивидендной политикой (не менее 35 руб./акция).\n\n**Segezha Group** не может выплачивать дивиденды из-за отрицательного FCF (-5.2 млрд) и критической долговой нагрузки. Дивиденды приостановлены до нормализации баланса."),
            ContentBlock(type="table", data={
                "headers": ["Компания", "FCF, млрд", "Див. доходность", "Может платить", "Дивидендная политика"],
                "rows": rows,
                "caption": "Дивидендный анализ портфельных компаний",
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_div", "title": "Дивидендная политика МТС", "type": "corporate_policy", "page": ""},
                {"id": "src_seg_div", "title": "Решение СД Segezha о приостановке дивидендов", "type": "corporate_policy", "page": ""},
            ]),
        ])
