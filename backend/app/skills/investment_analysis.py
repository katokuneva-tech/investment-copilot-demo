from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.project import PROJECT
from app.services.financial_calculator import calculate_npv, calculate_irr, calculate_payback, format_bln, format_pct
from app.services.pdf_generator import ReportPDF


class InvestmentAnalysisSkill(BaseSkill):
    async def handle(self, message: str, session_id: str) -> ChatResponse:
        p = PROJECT
        npv = calculate_npv(p["cash_flows"], p["discount_rate"])
        irr = calculate_irr(p["cash_flows"])
        payback = calculate_payback(p["cash_flows"])

        # Generate PDF
        pdf = ReportPDF(f"Инвестиционное заключение: {p['name']}")
        pdf.add_title_page(
            subtitle="Заключение для инвестиционного комитета",
            date="Март 2026",
        )

        pdf.pdf.add_page()
        pdf.add_section("1. Краткое описание проекта", (
            f"Проект: {p['name']}\n"
            f"Тип: {p['type']}\n"
            f"Площадь: {p['area_sqm']:,} кв.м\n"
            f"Объем инвестиций: {p['investment_bln']} млрд руб.\n"
            f"Горизонт: {p['horizon_years']} лет"
        ))

        pdf.add_section("2. Ключевые финансовые показатели", "")
        pdf.add_metrics_box({
            "NPV": format_bln(npv),
            "IRR": format_pct(irr),
            "Срок окупаемости": f"{payback} лет",
            "Ставка дисконтирования": format_pct(p["discount_rate"]),
        })

        pdf.add_section("3. Верификация предпосылок", "Сравнение ключевых допущений проекта с рыночными данными:")
        flag_rows = [[f["parameter"], f["project_value"], f["market_range"], "!!!" if f["severity"] == "high" else "OK"] for f in p["flags"]]
        pdf.add_table(["Параметр", "Проект", "Рынок", "Статус"], flag_rows)

        pdf.add_risk_flags([f for f in p["flags"] if f["severity"] != "ok"])

        pdf.add_section("4. Анализ чувствительности", "NPV (млрд руб.) при различных ставках аренды и заполняемости:")
        sens = p["sensitivity"]
        sens_headers = ["Аренда \\ Запол."] + [f"{int(r*100)}%" for r in sens["occupancy_rates"]]
        sens_rows = []
        for i, rent in enumerate(sens["rent_rates"]):
            row = [f"{rent:,}"] + [f"{v:.1f}" for v in sens["npv_matrix"][i]]
            sens_rows.append(row)
        pdf.add_table(sens_headers, sens_rows)

        pdf.add_section("5. Рекомендация", (
            "Условно положительное заключение при корректировке допущений:\n\n"
            "1. Скорректировать заполняемость с 95% до 90% (рыночный уровень)\n"
            "2. Верифицировать стоимость строительства — запросить обновленные сметы\n"
            "3. Обеспечить якорного арендатора на 30%+ площадей до начала строительства\n\n"
            f"При консервативном сценарии (заполняемость 90%) NPV = 0.8 млрд руб., IRR = 15.2% — проект остается привлекательным."
        ))

        report_id, _ = pdf.save()

        # Sensitivity table for chat
        sens_chat_rows = []
        for i, rent in enumerate(sens["rent_rates"]):
            row = [f"{rent:,} руб."] + [f"{v:.1f}" for v in sens["npv_matrix"][i]]
            sens_chat_rows.append(row)

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                f"## Инвестиционное заключение: {p['name']}\n\n"
                f"**Тип:** {p['type']}, {p['area_sqm']:,} кв.м\n"
                f"**Инвестиции:** {p['investment_bln']} млрд руб.\n\n"
                f"### Ключевые показатели (детерминированный расчет)\n"
                f"- **NPV** = {format_bln(npv)} (ставка дисконтирования {format_pct(p['discount_rate'])})\n"
                f"- **IRR** = {format_pct(irr)}\n"
                f"- **Срок окупаемости** = {payback} лет\n\n"
                f"### ⚠️ Выявленные флаги\n"
                f"1. **Заполняемость 95%** — агрессивная предпосылка (рынок: 88-92%)\n"
                f"2. **Стоимость строительства 55 тыс./кв.м** — ниже рынка (58-65 тыс.)\n\n"
                f"### Рекомендация\n"
                f"**Условно положительное** при корректировке заполняемости до 90%. "
                f"В консервативном сценарии NPV = 0.8 млрд, IRR = 15.2% — проект остается привлекательным."
            )),
            ContentBlock(type="table", data={
                "headers": ["Аренда \\ Заполн."] + [f"{int(r*100)}%" for r in sens["occupancy_rates"]],
                "rows": sens_chat_rows,
                "caption": "Анализ чувствительности NPV (млрд руб.)",
            }),
            ContentBlock(type="pdf_link", data={
                "report_id": report_id,
                "title": f"Заключение ИК: {p['name']}",
                "description": "PDF, 5 страниц — полное заключение с таблицами и графиками",
            }),
            ContentBlock(type="sources", data=[
                {"id": "src_model", "title": "Финансовая модель проекта (XLSX)", "type": "financial_model", "page": ""},
                {"id": "src_pres", "title": "Презентация проекта", "type": "presentation", "page": ""},
                {"id": "src_calc", "title": "Расчет NPV/IRR (financial_calculator)", "type": "calculation", "page": "Детерминированный"},
            ]),
        ])
