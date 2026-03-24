from app.skills.base import BaseSkill
from app.models.schemas import ChatResponse, ContentBlock
from app.data.committee import COMMITTEE_MATERIALS


class CommitteeAdvisorSkill(BaseSkill):
    async def handle(self, message: str, session_id: str) -> ChatResponse:
        if self._match(message, ["противоречи", "расхожден", "несоответств"]):
            return self._find_contradictions()
        elif self._match(message, ["риск", "угроз"]):
            return self._risk_analysis()
        elif self._match(message, ["рекоменд", "стоит ли", "входить", "за и против"]):
            return self._recommendation()
        else:
            return self._overview()

    def _overview(self) -> ChatResponse:
        docs = COMMITTEE_MATERIALS["documents"]
        doc_list = "\n".join([f"- **{d['title']}** ({d['type']}, {d['pages']} стр.)" for d in docs])
        contra_count = len(COMMITTEE_MATERIALS["contradictions"])
        risk_count = len(COMMITTEE_MATERIALS["risks"])

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                "## Обзор материалов инвестиционного комитета\n\n"
                f"Загружено **{len(docs)} документа** общим объемом {sum(d['pages'] for d in docs)} страниц:\n\n"
                f"{doc_list}\n\n"
                f"### Предварительный анализ\n"
                f"- Выявлено **{contra_count} противоречия** между документами\n"
                f"- Идентифицировано **{risk_count} рисков** различной степени критичности\n\n"
                "Задайте уточняющий вопрос: противоречия, риски, рекомендация по сделке."
            )),
            ContentBlock(type="sources", data=[
                {"id": d["id"], "title": d["title"], "type": d["type"], "page": f"{d['pages']} стр."} for d in docs
            ]),
        ])

    def _find_contradictions(self) -> ChatResponse:
        contras = COMMITTEE_MATERIALS["contradictions"]
        rows = []
        for c in contras:
            docs_involved = c.get("doc3", None)
            if docs_involved:
                row = [c["parameter"], f"{c['doc1']}: {c['doc1_value']} ({c['doc1_page']})",
                       f"{c['doc2']}: {c['doc2_value']} ({c['doc2_page']})",
                       f"{c['doc3']}: {c['doc3_value']} ({c['doc3_page']})"]
            else:
                row = [c["parameter"], f"{c['doc1']}: {c['doc1_value']} ({c['doc1_page']})",
                       f"{c['doc2']}: {c['doc2_value']} ({c['doc2_page']})", "—"]
            rows.append(row)

        text_parts = ["## Выявленные противоречия между документами\n"]
        for i, c in enumerate(contras, 1):
            severity_marker = "🔴" if c["severity"] == "high" else "🟡"
            text_parts.append(f"### {severity_marker} Противоречие {i}: {c['parameter']}\n")
            text_parts.append(f"- **{c['doc1']}** ({c['doc1_page']}): {c['doc1_value']}")
            text_parts.append(f"- **{c['doc2']}** ({c['doc2_page']}): {c['doc2_value']}")
            if c.get("doc3"):
                text_parts.append(f"- **{c['doc3']}** ({c['doc3_page']}): {c['doc3_value']}")
            text_parts.append(f"\n*{c['comment']}*\n")

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data="\n".join(text_parts)),
            ContentBlock(type="table", data={
                "headers": ["Параметр", "Документ 1", "Документ 2", "Документ 3"],
                "rows": rows,
                "caption": "Сводка противоречий между документами",
            }),
            ContentBlock(type="sources", data=[
                {"id": "doc_mgmt_pres", "title": "Презентация менеджмента", "type": "presentation", "page": "стр. 8, 12, 15"},
                {"id": "doc_fin_model", "title": "Финансовая модель", "type": "financial_model", "page": "вкл. Допущения, CF"},
                {"id": "doc_appraiser", "title": "Отчет оценщика", "type": "appraisal", "page": "стр. 23, 31"},
            ]),
        ])

    def _risk_analysis(self) -> ChatResponse:
        risks = COMMITTEE_MATERIALS["risks"]
        rows = []
        for r in risks:
            sev = {"high": "🔴 Высокая", "medium": "🟡 Средняя", "low": "🟢 Низкая"}[r["severity"]]
            prob = {"high": "Высокая", "medium": "Средняя", "low": "Низкая"}[r["probability"]]
            rows.append([r["name"], sev, prob, r["impact"]])

        text = "## Анализ рисков сделки\n\n"
        for i, r in enumerate(risks, 1):
            marker = {"high": "🔴", "medium": "🟡", "low": "🟢"}[r["severity"]]
            text += f"**{i}. {marker} {r['name']}**\n"
            text += f"- Влияние: {r['impact']}\n"
            text += f"- Источник: {r['source']}\n\n"

        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=text),
            ContentBlock(type="table", data={
                "headers": ["Риск", "Критичность", "Вероятность", "Влияние"],
                "rows": rows,
                "caption": "Матрица рисков инвестиционного проекта",
            }),
            ContentBlock(type="sources", data=[
                {"id": r["id"], "title": r["name"], "type": "risk_analysis", "page": r["source"]} for r in risks[:3]
            ]),
        ])

    def _recommendation(self) -> ChatResponse:
        return ChatResponse(session_id="", blocks=[
            ContentBlock(type="text", data=(
                "## Рекомендация по сделке: Логистический хаб Подмосковье\n\n"
                "### ✅ Аргументы ЗА\n"
                "1. **IRR (18.5%) > WACC (12%)** — проект создает стоимость для акционеров\n"
                "2. **Растущий рынок** — складская недвижимость +9% CAGR, дефицит предложения\n"
                "3. **Стратегическая синергия** — экспозиция на логистику дополняет портфель АФК\n"
                "4. **Вакансия на минимуме** (3.2%) — высокий спрос на качественные площади\n\n"
                "### ❌ Аргументы ПРОТИВ\n"
                "1. **Оптимистичные предпосылки** — заполняемость 95% при рынке 88-92%\n"
                "2. **Расхождения в документах** — 3 противоречия между менеджментом и оценщиком\n"
                "3. **Конкурентное давление** — оценщик выявил 3 конкурента в радиусе 30 км\n"
                "4. **Макро-риски** — рост ставки ЦБ может увеличить WACC\n\n"
                "### 📋 Итоговая рекомендация\n"
                "**Условно положительная** — при выполнении следующих условий:\n"
                "1. Корректировка заполняемости до 90% в финансовой модели\n"
                "2. Обеспечение якорного арендатора на 30%+ площадей\n"
                "3. Обновление сметы строительства с учетом инфраструктуры\n"
                "4. Устранение расхождений между презентацией и моделью\n\n"
                "*При консервативных допущениях NPV = 0.8 млрд, IRR = 15.2% — проект остается привлекательным.*"
            )),
            ContentBlock(type="sources", data=[
                {"id": "doc_all", "title": "Все материалы инвесткомитета", "type": "committee_materials", "page": "4 документа, 102 стр."},
                {"id": "calc", "title": "Финансовый калькулятор (NPV/IRR)", "type": "calculation", "page": "Детерминированный расчет"},
            ]),
        ])
