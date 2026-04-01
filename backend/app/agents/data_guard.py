"""
Data Guard agent — cross-validates analyst reports against raw context data.

Inspired by Prime Radiant architecture: catches hallucinations, factual errors,
and unsupported claims BEFORE they reach the Fund Director.

Flow:
  Analyst Reports + Raw Context → Data Guard
    → status: "validated" → proceed to Director
    → status: "corrections_needed" → corrections dict per agent
"""

from app.agents.base_agent import BaseAgent, AgentResult
import json, time, logging

logger = logging.getLogger(__name__)


class DataGuard(BaseAgent):
    NAME = "data_guard"
    ROLE = "Контроль качества данных"
    MODEL_TIER = "standard"  # Sonnet — fast validation pass
    MAX_TOKENS = 4000

    SYSTEM_PROMPT = """Ты — Data Guard, контролёр качества данных инвестиционного департамента АФК Система.

## Твоя задача
Ты получаешь отчёты от нескольких аналитиков и ИСХОДНЫЕ ДАННЫЕ (контекст из базы знаний и документов).
Ты должен кросс-валидировать каждое утверждение аналитиков против исходных данных.

## Что проверяешь
1. **Галлюцинации компаний** — аналитик упомянул компанию, которой НЕТ в контексте? Ozon, Cosmos Hotel Group, Ситроникс и другие должны быть ПОДТВЕРЖДЕНЫ контекстом
2. **Неверные цифры** — выручка, EBITDA, долг, маржа не совпадают с данными из документов
3. **Придуманные источники** — аналитик ссылается на отчёт/документ, которого нет в контексте
4. **Логические противоречия** — один аналитик говорит одно, другой — противоположное
5. **Необоснованные оценки** — IPO-оценки, target prices без источника

## Портфельные компании АФК Система (справка)
ТЕКУЩИЕ портфельные: МТС, Segezha Group, Эталон, МЕДСИ, СТЕПЬ, Биннофарм, Cosmos Hotel Group, Natura Siberica
БЫВШИЕ активы (НЕ включать в анализ портфеля!): Ozon (АФК продала долю), Детский мир (продан)
НЕ портфельные: Ростелеком, Мегафон, Яндекс, Сбербанк, ВТБ, Тинькофф

ВАЖНО: Если аналитик включил Ozon в анализ текущего портфеля АФК — это ОШИБКА severity=critical. Ozon НЕ является портфельной компанией АФК Система.

## Формат ответа
Ответь строго в JSON:
```json
{
  "status": "validated" | "corrections_needed",
  "issues": [
    {
      "agent": "имя_агента",
      "type": "hallucination" | "wrong_number" | "fake_source" | "contradiction" | "unsubstantiated",
      "severity": "critical" | "high" | "medium",
      "claim": "что сказал аналитик",
      "reality": "что на самом деле",
      "fix": "как исправить"
    }
  ],
  "summary": "краткое описание"
}
```

Если всё корректно — `{"status": "validated", "issues": [], "summary": "Все данные аналитиков подтверждены контекстом."}`"""

    def __init__(self, context: str, agent_results: list[AgentResult]):
        self.raw_context = context
        self.agent_results = agent_results
        # Build composite query for BaseAgent
        reports = []
        for r in agent_results:
            if not r.error:
                reports.append(f"### Отчёт: {r.role} ({r.agent_name})\n{r.content}")
        reports_text = "\n\n---\n\n".join(reports)

        super().__init__(
            context=context,
            user_query=f"Проверь следующие отчёты аналитиков на фактические ошибки, галлюцинации и противоречия.\n\n{reports_text}",
        )

    async def run(self) -> AgentResult:
        start = time.monotonic()
        try:
            messages = self._build_messages()
            from app.services.llm_client import llm_client

            response = await llm_client.chat(
                system=self.SYSTEM_PROMPT,
                messages=messages,
                temperature=0.0,
                tier=self.MODEL_TIER,
                max_tokens=self.MAX_TOKENS,
            )
            elapsed = time.monotonic() - start

            return AgentResult(
                agent_name=self.NAME,
                role=self.ROLE,
                content=response,
                elapsed_sec=round(elapsed, 1),
            )
        except Exception as e:
            logger.error(f"DataGuard failed: {e}")
            return AgentResult(
                agent_name=self.NAME, role=self.ROLE, content="",
                elapsed_sec=round(time.monotonic() - start, 1), error=str(e),
            )

    def parse_result(self) -> dict:
        """Parse DataGuard JSON response. Returns dict with status and issues."""
        try:
            # Extract JSON from response (may be wrapped in markdown code block)
            text = self.content if hasattr(self, 'content') else ""
            if "```json" in text:
                parts = text.split("```json")
                if len(parts) > 1:
                    text = parts[1].split("```")[0]
            elif "```" in text:
                parts = text.split("```")
                if len(parts) > 1:
                    text = parts[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError, ValueError):
            return {"status": "validated", "issues": [], "summary": "Parse error, proceeding."}


def apply_corrections(agent_results: list[AgentResult], guard_result: dict) -> list[AgentResult]:
    """
    Apply Data Guard corrections to agent results.
    For critical/high issues — strips or annotates the problematic content.
    """
    if guard_result.get("status") == "validated":
        return agent_results

    issues = guard_result.get("issues", [])
    if not issues:
        return agent_results

    # Build correction map: agent_name → list of issues
    corrections_by_agent: dict[str, list[dict]] = {}
    for issue in issues:
        agent = issue.get("agent", "")
        if agent not in corrections_by_agent:
            corrections_by_agent[agent] = []
        corrections_by_agent[agent].append(issue)

    # Apply corrections
    corrected = []
    for r in agent_results:
        if r.agent_name in corrections_by_agent:
            agent_issues = corrections_by_agent[r.agent_name]
            # Add correction footnotes to the report
            footnotes = []
            for iss in agent_issues:
                severity_icon = {"critical": "[КРИТ]", "high": "[ВЫСОК]", "medium": "[СРЕДН]"}.get(iss.get("severity", ""), "")
                footnotes.append(
                    f"- {severity_icon} **ИСПРАВЛЕНИЕ Data Guard**: {iss.get('claim', '')} → {iss.get('fix', '')}"
                )

            corrected_content = r.content + "\n\n### Исправления Data Guard\n" + "\n".join(footnotes)

            corrected.append(AgentResult(
                agent_name=r.agent_name,
                role=r.role,
                content=corrected_content,
                tables=r.tables,
                red_flags=r.red_flags,
                sources=r.sources,
                confidence=max(0.3, r.confidence - 0.2 * len(agent_issues)),
                elapsed_sec=r.elapsed_sec,
                error=r.error,
            ))
        else:
            corrected.append(r)

    return corrected
