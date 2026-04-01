"""
Fund Director — synthesizes all agent outputs into a final recommendation.

Supports Q&A Loop (inspired by Prime Radiant):
  1. Director reads all analyst reports
  2. Decides if follow-up questions are needed
  3. If yes — asks specific analysts, gets answers
  4. Then makes final decision with enriched context
"""

from app.agents.base_agent import BaseAgent, AgentResult
import json, time, logging

logger = logging.getLogger(__name__)


# ── Q&A Decision prompt ────────────────────────────────────────────────

QA_DECISION_PROMPT = """Ты — инвестиционный директор. Ты прочитал отчёты аналитиков и должен решить: нужны ли уточняющие вопросы?

Задай вопросы ТОЛЬКО если:
- Есть критическое противоречие между аналитиками
- Не хватает ключевых данных для принятия решения (NPV, IRR, долговая нагрузка)
- Red flag требует детализации

НЕ задавай вопросы если информации достаточно для ответа.

Ответь строго в JSON:
```json
{
  "needsQuestions": true/false,
  "questions": [
    {"to": "financial_analyst", "question": "вопрос"},
    {"to": "risk_analyst", "question": "вопрос"}
  ]
}
```

Допустимые адресаты: financial_analyst, market_analyst, risk_analyst, sentiment_analyst, benchmark_analyst.
Максимум 3 вопроса. Если вопросов нет — `{"needsQuestions": false, "questions": []}`"""


class FundDirector(BaseAgent):
    NAME = "fund_director"
    ROLE = "Инвестиционный директор"
    MODEL_TIER = "deep"  # Opus for final synthesis
    MAX_TOKENS = 8000

    SYSTEM_PROMPT = """Ты — инвестиционный директор АФК Система. Ты получаешь анализы от 5 специализированных аналитиков и синтезируешь финальное заключение.

## Твоя философия
- Ты СКЕПТИК, защищающий капитал АФК
- Ты НЕ на стороне менеджмента проекта
- Лучше отклонить хорошую сделку, чем одобрить плохую
- Каждое утверждение должно быть подкреплено данными от аналитиков

## Что ты получаешь
Отчёты от 5 аналитиков:
1. **Финансовый аналитик** — метрики, NPV/IRR, чувствительность
2. **Рыночный аналитик** — рынок, конкуренты, верификация предпосылок
3. **Аналитик рисков** — red flags, DD чеклист, матрица рисков
4. **Аналитик сентимента** — новости, репутация, ESG
5. **Бенчмарк-аналитик** — мультипликаторы, implied valuation, peers

## Формат синтеза

### Для инвестиционных проектов (UC2, UC5):
```
## РЕКОМЕНДАЦИЯ: [ЗА] / [ПРОТИВ] / [УСЛОВНО ЗА]

### Scorecard
| Критерий | Оценка (1-5) | Обоснование |
| Качество актива | X | ... |
| Справедливость цены | X | ... |
| Достоверность предпосылок | X | ... |
| Риск-профиль | X | ... |
| Стратегический fit с АФК | X | ... |
| **ИТОГО** | **X/25** | |

### Ключевые выводы
1. [Самый важный вывод]
2. [Второй по важности]
3. [Третий]

### Red flags (топ-3)
[Из отчёта аналитика рисков]

### Условия (если УСЛОВНО ЗА)
1. ...
2. ...
```

### Для анализа портфеля (UC1, UC4):
```
## Ответ на вопрос
[Прямой ответ 1-2 предложения]

### Детальный анализ
[Таблица с данными от финансового аналитика]

### Рыночный контекст
[Из рыночного и сентимент аналитиков]

### Рекомендации
[Конкретные действия]
```

## Правила синтеза
1. Если аналитики ПРОТИВОРЕЧАТ друг другу — указать оба мнения, дать своё заключение
2. Если >2 аналитиков нашли [КРИТ] red flags — рекомендация [ПРОТИВ]
3. Scorecard >=18/25 → [ЗА], 13-17 → [УСЛОВНО ЗА], <=12 → [ПРОТИВ]
4. ВСЕГДА указывать источник: "По данным финансового аналитика: ..."
5. НЕ ДОБАВЛЯТЬ компании, цифры, оценки или факты, которых НЕТ в отчётах аналитиков. Если данных нет — напиши "нет данных", а не выдумывай
6. Упоминай ТОЛЬКО компании, которые явно названы в отчётах аналитиков или в контексте. Не добавляй компании от себя
7. Если называешь конкретную цифру (выручка, оценка, долг) — обязательно укажи из какого отчёта аналитика она взята"""

    @classmethod
    def synthesize(cls, agent_results: list[AgentResult], user_query: str,
                   use_case: str = "portfolio",
                   qa_context: str = "") -> "FundDirector":
        """Create a FundDirector instance with agent results as context."""
        sections = []
        for r in agent_results:
            if r.error:
                sections.append(f"### {r.role} — ОШИБКА\n{r.error}")
            else:
                sections.append(f"### {r.role} (время: {r.elapsed_sec}с)\n{r.content}")

        context = "\n\n---\n\n".join(sections)

        if qa_context:
            context += f"\n\n---\n\n### Дополнительные ответы аналитиков (по вашим вопросам)\n{qa_context}"

        task_prefix = {
            "portfolio": "Синтезируй ответ на вопрос пользователя по портфелю АФК на основе анализов аналитиков.",
            "investment": "Подготовь инвестиционное заключение с рекомендацией ЗА/ПРОТИВ/УСЛОВНО ЗА и scorecard.",
            "market": "Синтезируй аналитический отчёт по рынку на основе данных от аналитиков.",
            "benchmark": "Синтезируй бенчмаркинг-отчёт с implied valuation и выводами.",
            "committee": "Подготовь заключение для инвестиционного комитета с рекомендацией и scorecard.",
        }
        prefix = task_prefix.get(use_case, task_prefix["portfolio"])

        instance = cls(
            context=context,
            user_query=f"{prefix}\n\nВопрос пользователя: {user_query}",
        )
        return instance


# ── Q&A Loop helpers ───────────────────────────────────────────────────

# Agent name → system prompt for answering follow-up questions
AGENT_QA_PROMPTS = {
    "financial_analyst": "Ты финансовый аналитик АФК Система. Ответь на уточняющий вопрос инвестиционного директора на основе данных из контекста. Будь конкретен, цитируй цифры.",
    "market_analyst": "Ты рыночный аналитик АФК Система. Ответь на уточняющий вопрос директора по рынку, конкурентам, M&A.",
    "risk_analyst": "Ты аналитик рисков АФК Система. Ответь на уточняющий вопрос директора по red flags, DD, рискам.",
    "sentiment_analyst": "Ты аналитик сентимента АФК Система. Ответь на уточняющий вопрос директора по новостям, репутации.",
    "benchmark_analyst": "Ты бенчмарк-аналитик АФК Система. Ответь на уточняющий вопрос директора по мультипликаторам, peers.",
}


async def director_qa_decision(agent_results: list[AgentResult], user_query: str) -> dict:
    """
    Director decides if follow-up questions are needed.
    Returns parsed JSON with needsQuestions and questions list.
    """
    from app.services.llm_client import llm_client

    sections = []
    for r in agent_results:
        if not r.error:
            sections.append(f"### {r.role}\n{r.content[:1500]}")  # Truncate for decision

    context = "\n\n".join(sections)

    try:
        response = await llm_client.chat(
            system=QA_DECISION_PROMPT,
            messages=[{"role": "user", "content": f"Вопрос пользователя: {user_query}\n\n{context}"}],
            temperature=0.0,
            tier="deep",
            max_tokens=500,
        )

        # Parse JSON from response
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        parsed = json.loads(text.strip())
        return parsed

    except Exception as e:
        logger.warning(f"Director Q&A decision failed: {e}")
        return {"needsQuestions": False, "questions": []}


async def answer_director_question(
    question: str,
    agent_name: str,
    context: str,
    original_report: str,
) -> str:
    """An analyst answers a follow-up question from the Director."""
    from app.services.llm_client import llm_client

    system = AGENT_QA_PROMPTS.get(agent_name, "Ответь на вопрос директора.")

    messages = [{
        "role": "user",
        "content": f"## Твой оригинальный отчёт\n{original_report[:2000]}\n\n## Контекст\n{context[:3000]}\n\n## Вопрос директора\n{question}",
    }]

    try:
        response = await llm_client.chat(
            system=system,
            messages=messages,
            temperature=0.1,
            tier="standard",  # Sonnet for fast follow-up
            max_tokens=1500,
        )
        return response
    except Exception as e:
        logger.error(f"Q&A answer failed for {agent_name}: {e}")
        return f"Не удалось получить ответ: {e}"


async def run_qa_loop(
    agent_results: list[AgentResult],
    user_query: str,
    context: str,
) -> str:
    """
    Full Q&A loop:
    1. Director decides if questions needed
    2. If yes, routes questions to specific analysts
    3. Returns combined Q&A context string (or empty if no questions)
    """
    import asyncio

    decision = await director_qa_decision(agent_results, user_query)

    if not decision.get("needsQuestions") or not decision.get("questions"):
        return ""

    questions = decision["questions"][:3]  # Max 3
    logger.info(f"Director Q&A: {len(questions)} questions to ask")

    # Map agent names to their reports
    reports_by_name = {}
    for r in agent_results:
        reports_by_name[r.agent_name] = r.content

    # Run all Q&A in parallel
    async def ask_one(q: dict) -> str:
        to = q.get("to", "")
        question = q.get("question", "")
        report = reports_by_name.get(to, "")
        answer = await answer_director_question(question, to, context, report)
        return f"**Вопрос к {to}**: {question}\n**Ответ**: {answer}"

    tasks = [ask_one(q) for q in questions]
    answers = await asyncio.gather(*tasks, return_exceptions=True)

    qa_parts = []
    for ans in answers:
        if isinstance(ans, Exception):
            qa_parts.append(f"Ошибка: {ans}")
        else:
            qa_parts.append(str(ans))

    return "\n\n---\n\n".join(qa_parts)
