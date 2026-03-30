from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.market import MARKET_DATA
from app.services.pdf_generator import ReportPDF


class MarketResearchSkill(BaseSkill):
    async def handle(self, message: str, session_id: str, extra_context: str = "") -> ChatResponse:
        m = MARKET_DATA["logistics"]

        # Generate PDF
        pdf = ReportPDF(m["name"])
        pdf.add_title_page(subtitle="Аналитический обзор рынка", date="Март 2026")

        pdf.pdf.add_page()
        pdf.add_section("1. Размер и динамика рынка", (
            f"Объем рынка в 2025 году: {m['size_2025_trln']} трлн руб.\n"
            f"Среднегодовой темп роста (CAGR): {m['cagr_pct']}%\n\n"
            "Рынок логистики и складской недвижимости демонстрирует устойчивый рост, "
            "главным образом за счет развития e-commerce и дефицита качественных складских площадей."
        ))
        size_rows = [[str(h["year"]), f"{h['size']:.1f}"] for h in m["size_history"]]
        pdf.add_table(["Год", "Объем, трлн руб."], size_rows)

        pdf.add_section("2. Структура рынка по сегментам", "")
        seg_rows = [[s["name"], f"{s['share']}%", s["margin"]] for s in m["segments"]]
        pdf.add_table(["Сегмент", "Доля", "Маржинальность"], seg_rows)

        pdf.add_section("3. Ключевые игроки", "")
        player_rows = [[p["name"], f"{p['share']}%", f"{p['revenue']} млрд"] for p in m["players"]]
        pdf.add_table(["Компания", "Доля рынка", "Выручка"], player_rows)

        wh = m["warehouse_metrics"]
        pdf.add_section("4. Складская недвижимость", "")
        pdf.add_metrics_box({
            "Общий фонд": f"{wh['total_stock_mln_sqm']} млн кв.м",
            "Вакансия": f"{wh['vacancy_rate_pct']}%",
            "Средняя ставка класс А": f"{wh['avg_rent_class_a']:,} руб./кв.м/год",
            "Новое строительство 2025": f"{wh['new_supply_2025_mln_sqm']} млн кв.м",
            "Доля Москвы": f"{wh['moscow_share_pct']}%",
        })

        pdf.add_section("5. Сделки M&A", "")
        ma_rows = [[d["year"], d["buyer"], d["target"], d["value"]] for d in m["ma_deals"]]
        pdf.add_table(["Год", "Покупатель", "Актив", "Сумма"], ma_rows)

        pdf.add_section("6. Ключевые тренды", "")
        pdf.add_bullet_list(m["trends"])

        pdf.add_section("7. Риски", "")
        pdf.add_bullet_list(m["risks"])

        report_id, _ = pdf.save()

        # Chat response
        seg_chart = [{"name": s["name"], "share": s["share"]} for s in m["segments"]]
        size_chart = [{"name": str(h["year"]), "size": h["size"]} for h in m["size_history"]]

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                f"## {m['name']}\n\n"
                f"**Объем рынка:** {m['size_2025_trln']} трлн руб. (2025), CAGR {m['cagr_pct']}%\n\n"
                f"Рынок логистики и складской недвижимости в России продолжает активный рост. "
                f"Ключевой драйвер — e-commerce (+25% г/г). Дефицит складских площадей класса А "
                f"(вакансия всего {wh['vacancy_rate_pct']}%) поддерживает рост ставок аренды.\n\n"
                f"### Ключевые метрики складского сегмента\n"
                f"- Общий фонд: {wh['total_stock_mln_sqm']} млн кв.м\n"
                f"- Вакансия: {wh['vacancy_rate_pct']}% (исторический минимум)\n"
                f"- Ставка аренды класс А: {wh['avg_rent_class_a']:,} руб./кв.м/год\n"
                f"- Новое строительство: {wh['new_supply_2025_mln_sqm']} млн кв.м в 2025"
            )),
            ContentBlock(type="chart", data={
                "chart_type": "line",
                "title": "Динамика рынка логистики (трлн руб.)",
                "x_key": "name",
                "series": [{"name": "Объем рынка", "data_key": "size", "color": "#E11D48"}],
                "data": size_chart,
            }),
            ContentBlock(type="table", data={
                "headers": ["Компания", "Доля рынка", "Выручка, млрд"],
                "rows": [[p["name"], f"{p['share']}%", f"{p['revenue']}"] for p in m["players"]],
                "caption": "Ключевые игроки рынка логистики",
            }),
            ContentBlock(type="pdf_link", data={
                "report_id": report_id,
                "title": "Аналитический обзор рынка логистики",
                "description": "PDF, 7 страниц — размер рынка, сегменты, игроки, M&A, тренды",
            }),
        ])
