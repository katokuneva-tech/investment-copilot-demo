from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.companies import COMPANIES
from app.services.pdf_generator import ReportPDF

# Only benchmark companies that have peer comparison data
_BENCH_KEYS = ["mts", "segezha", "etalon", "binnopharm", "step"]


def _fmt(val, suffix="", default="н/д"):
    if val is None:
        return default
    if isinstance(val, float):
        if abs(val) >= 100:
            return f"{val:,.0f}{suffix}".replace(",", " ")
        return f"{val:.1f}{suffix}"
    return str(val)


class BenchmarkingSkill(BaseSkill):
    async def handle(self, message: str, session_id: str, extra_context: str = "") -> ChatResponse:
        rows = []
        chart_data = []
        for key in _BENCH_KEYS:
            c = COMPANIES[key]
            ev = c.get("ev_ebitda")
            peer_ev = c.get("peer_ev_ebitda_avg")
            rev = c.get("revenue_2024") or c.get("revenue_2025")
            ebitda = c.get("ebitda_2024") or c.get("ebitda_2025")
            margin = c.get("ebitda_margin")
            debt = c.get("net_debt_ebitda")
            mcap = c.get("market_cap")

            premium = ((ev / peer_ev) - 1) * 100 if ev and peer_ev else 0
            rows.append([
                c["name"], c["sector"],
                _fmt(mcap), _fmt(rev), _fmt(ebitda),
                _fmt(margin, "%"), _fmt(debt, "x"),
                _fmt(ev, "x"), _fmt(peer_ev, "x"),
                f"{premium:+.0f}%",
            ])
            if ev and peer_ev:
                chart_data.append({"name": c["name"], "company": ev, "peers": peer_ev})

        # PDF
        pdf = ReportPDF("Бенчмаркинг портфеля АФК Система")
        pdf.add_title_page(subtitle="Сравнение с рыночными аналогами", date="Март 2026")
        pdf.pdf.add_page()
        pdf.add_section("1. Сводная таблица", "Сравнение ключевых мультипликаторов портфельных компаний с медианой отраслевых аналогов.")
        pdf_rows = [[c["name"], f"{c.get('ev_ebitda', 'н/д')}x", f"{c.get('peer_ev_ebitda_avg', 'н/д')}x",
                     _fmt(c.get("ebitda_margin"), "%"), f"{c.get('peer_margin_avg', 'н/д')}%"]
                    for c in [COMPANIES[k] for k in _BENCH_KEYS]]
        pdf.add_table(["Компания", "EV/EBITDA", "Peers EV/EBITDA", "Маржа", "Peers маржа"], pdf_rows)

        pdf.add_section("2. Ключевые выводы", (
            "1. Segezha торгуется с премией 42% к аналогам (8.5x vs 6.0x), при этом "
            "долговая нагрузка критическая (Долг/OIBDA = 14.4x за 2023). Премия "
            "необоснована — высокий риск реструктуризации.\n\n"
            "2. МТС торгуется с премией 11% при маржинальности 34.7% — "
            "оценка справедливая. Выручка впервые >800 млрд (807.2).\n\n"
            "3. Биннофарм — дисконт 13% к фарма-аналогам. Потенциал "
            "переоценки при IPO в 2026.\n\n"
            "4. СТЕПЬ и Эталон торгуются вблизи медианы аналогов.\n\n"
            "Примечание: бенчмаркинг доступен для 5 публичных компаний с peer-данными. "
            "Для 18 непубличных активов данные о мультипликаторах отсутствуют."
        ))
        report_id, _ = pdf.save()

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                "## Бенчмаркинг портфеля АФК Система\n\n"
                "Сравнение EV/EBITDA 5 ключевых компаний с медианой отраслевых аналогов:\n\n"
                "- **Segezha**: премия +42% (8.5x vs 6.0x) — **необоснована** при Долг/OIBDA 14.4x\n"
                "- **МТС**: премия +11%, обоснована маржинальностью 34.7%. Выручка 807.2 млрд\n"
                "- **Биннофарм**: дисконт -13% — потенциал переоценки при IPO 2026\n"
                "- **СТЕПЬ** и **Эталон**: торгуются вблизи рыночных уровней\n\n"
                "_Бенчмаркинг доступен для 5 публичных компаний. Для остальных 18 активов peer-данные отсутствуют._"
            )),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Сектор", "Капит.", "Выр.", "EBITDA", "Маржа", "Долг/E", "EV/EBITDA", "Peers", "Премия"],
                "rows": rows,
                "caption": "Бенчмаркинг: портфельные компании vs аналоги",
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
        ])
