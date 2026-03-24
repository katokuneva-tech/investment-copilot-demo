from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.companies import COMPANIES, COMPANY_ORDER
from app.services.pdf_generator import ReportPDF


class BenchmarkingSkill(BaseSkill):
    async def handle(self, message: str, session_id: str) -> ChatResponse:
        rows = []
        chart_data = []
        for key in COMPANY_ORDER:
            c = COMPANIES[key]
            premium = ((c["ev_ebitda"] / c["peer_ev_ebitda_avg"]) - 1) * 100
            rows.append([
                c["name"], c["sector"],
                f"{c['market_cap']:.0f}",
                f"{c['revenue_2025']:.0f}",
                f"{c['ebitda_2025']:.1f}",
                f"{c['ebitda_margin']}%",
                f"{c['net_debt_ebitda']}x",
                f"{c['ev_ebitda']}x",
                f"{c['peer_ev_ebitda_avg']}x",
                f"{premium:+.0f}%",
            ])
            chart_data.append({
                "name": c["name"],
                "company": c["ev_ebitda"],
                "peers": c["peer_ev_ebitda_avg"],
            })

        # PDF
        pdf = ReportPDF("Бенчмаркинг портфеля АФК Система")
        pdf.add_title_page(subtitle="Сравнение с рыночными аналогами", date="Март 2026")
        pdf.pdf.add_page()
        pdf.add_section("1. Сводная таблица", "Сравнение ключевых мультипликаторов портфельных компаний с медианой отраслевых аналогов.")
        pdf_rows = [[c["name"], f"{c['ev_ebitda']}x", f"{c['peer_ev_ebitda_avg']}x", f"{c['ebitda_margin']}%", f"{c['peer_margin_avg']}%"] for c in [COMPANIES[k] for k in COMPANY_ORDER]]
        pdf.add_table(["Компания", "EV/EBITDA", "Peers EV/EBITDA", "Маржа", "Peers маржа"], pdf_rows)

        pdf.add_section("2. Ключевые выводы", (
            "1. Segezha торгуется с премией 42% к аналогам (8.5x vs 6.0x), что объясняется "
            "ожиданиями рынка по восстановлению цен на пиломатериалы. Однако при текущей "
            "долговой нагрузке (4.2x) премия выглядит необоснованной.\n\n"
            "2. МТС торгуется с премией 11% к аналогам при значительно более высокой "
            "маржинальности (42% vs 38%). Оценка справедливая.\n\n"
            "3. Биннофарм торгуется с дисконтом 13% к фармацевтическим аналогам, несмотря на "
            "опережающий рост (+16%). Потенциал переоценки при сохранении темпов роста.\n\n"
            "4. СТЕПЬ и Эталон торгуются вблизи медианы отраслевых аналогов."
        ))
        report_id, _ = pdf.save()

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                "## Бенчмаркинг портфеля АФК Система\n\n"
                "Сравнение EV/EBITDA портфельных компаний с медианой отраслевых аналогов:\n\n"
                "- **Segezha**: торгуется с премией +42% к аналогам (8.5x vs 6.0x) — переоценена при текущей долговой нагрузке\n"
                "- **МТС**: премия +11%, обоснована высокой маржинальностью (42% vs 38%)\n"
                "- **Биннофарм**: дисконт -13% к фарма-аналогам — потенциал переоценки\n"
                "- **СТЕПЬ** и **Эталон**: торгуются вблизи рыночных уровней"
            )),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Капит., млрд", "Выр., млрд", "EBITDA, млрд", "Маржа", "Долг/EBITDA", "EV/EBITDA", "Peers", "Премия"],
                "rows": rows,
                "caption": "Бенчмаркинг портфельных компаний vs отраслевые аналоги (2025)",
            }),
            ContentBlock(type="chart", data={
                "chart_type": "bar",
                "title": "EV/EBITDA: компания vs аналоги",
                "x_key": "name",
                "series": [
                    {"name": "Компания", "data_key": "company", "color": "#E11D48"},
                    {"name": "Аналоги (медиана)", "data_key": "peers", "color": "#94A3B8"},
                ],
                "data": chart_data,
            }),
            ContentBlock(type="pdf_link", data={
                "report_id": report_id,
                "title": "Бенчмаркинг портфеля АФК Система",
                "description": "PDF — сравнительные таблицы, мультипликаторы, ранжирование",
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_bench", "title": "Данные Bloomberg Terminal", "type": "market_data", "page": ""},
                {"id": "src_peers", "title": "Отраслевые обзоры аналитиков", "type": "market_report", "page": ""},
            ]),
        ])
