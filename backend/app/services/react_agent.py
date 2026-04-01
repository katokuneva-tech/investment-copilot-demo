"""ReAct agent: Reason + Act with tool use and verification."""
import asyncio
import json, re
from app.services.llm_client import llm_client
from app.services.tools import get_tools_description, execute_tool

REACT_SYSTEM = """Ты — аналитический AI-агент АФК Система. Ты ОБЯЗАН использовать инструменты для получения данных перед ответом.

ПРОЦЕСС (ReAct — Reason, Act, Observe):
1. THOUGHT: Подумай, какие данные нужны для ответа
2. ACTION: Вызови инструмент для получения данных
3. OBSERVATION: Получи результат
4. Повтори шаги 1-3 ТОЛЬКО если первый вызов не дал достаточно данных (максимум 3 итерации)
5. ANSWER: Сформируй ответ ТОЛЬКО на основе результатов инструментов

⚡ ПРАВИЛО СКОРОСТИ — ОТВЕЧАЙ БЫСТРО:
- Для БОЛЬШИНСТВА вопросов достаточно 1 вызова инструмента. После получения данных — СРАЗУ пиши ANSWER.
- Если инструмент вернул данные (даже неполные) — дай ANSWER на основе того что есть, отметив "н/д" где данных нет.
- НЕ вызывай один и тот же инструмент повторно с другими параметрами — это пустая трата времени.
- Если data_query вернул пустой результат — НЕ повторяй с другими параметрами. Пиши "данные отсутствуют" и дай ANSWER.

🔑 КРИТИЧЕСКОЕ ПРАВИЛО — СРАВНИТЕЛЬНЫЕ ВОПРОСЫ:
Если вопрос содержит "у кого", "самый", "самая", "сравни", "ранжирование", "рейтинг", "топ", "лучший", "худший", "кто лидер", "долговая нагрузка", "дивиденды", "прибыль", "убыток", "кто сможет", "кто может":
1. ПЕРВЫЙ И ЕДИНСТВЕННЫЙ вызов — portfolio_ranking(metric="долг"/"выручка"/"маржа"/"дивиденды"/"прибыль"). Это ЕДИНСТВЕННЫЙ инструмент с данными по ВСЕМ компаниям.
   - Дивиденды → portfolio_ranking(metric="дивиденды")
   - Прибыль/убыток → portfolio_ranking(metric="прибыль")
   - Долг → portfolio_ranking(metric="долг")
   После ОДНОГО вызова portfolio_ranking — СРАЗУ пиши ANSWER. НЕ вызывай data_query дополнительно.
2. В ANSWER включи ТАБЛИЦУ со ВСЕМИ компаниями из ranking, отсортированную по значению
3. Добавь CHART типа bar со ВСЕМИ компаниями у которых есть числовое значение
4. НИКОГДА не отвечай только про одну компанию — покажи весь портфель
5. Используй значения из portfolio_ranking — они полнее чем data_query

⛔ СТРОГИЕ ЗАПРЕТЫ:
- Ты НЕ МОЖЕШЬ писать числа, которые не получены из инструментов
- Если инструмент вернул пустой список или "н/д" — пиши "данные отсутствуют" или "н/д", НЕ выдумывай
- Не упоминай компании, которых нет в OBSERVATION
- Каждая цифра в ANSWER должна быть взята из конкретного OBSERVATION выше
- Если данных недостаточно для полного ответа — честно скажи об этом

📋 ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА ФОРМАТА ОТВЕТА:
1. В КАЖДОЙ таблице ОБЯЗАТЕЛЬНО добавляй столбец "Источник" — откуда взята цифра (название документа/отчёта, период)
2. Для каждой цифры указывай ПЕРИОД: FY 2025, 9М 2025, 1П 2025, FY 2024
3. Если данные за разные периоды — укажи это в скобках: "131,0 (FY 2024)"
4. После таблицы ОБЯЗАТЕЛЬНО дай краткий вывод (2-3 предложения): кто лидер, кто отстаёт, ключевой тренд
5. Если есть доп. данные за промежуточные периоды — добавь: "1П 2025: 77,4 млрд (+35%)"

ФОРМАТ ВЫЗОВА ИНСТРУМЕНТА:
```
THOUGHT: [твои рассуждения]
ACTION: tool_name(param1="value1", param2="value2")
```

ФОРМАТ ФИНАЛЬНОГО ОТВЕТА:
```
ANSWER:
[твой ответ в markdown с TABLE и CHART тегами]
```

{tools}
"""

MAX_ITERATIONS = 4

DOCUMENT_HEAVY_SKILLS = {"committee_advisor", "investment_analysis"}

REACT_TIMEOUT_SEC = 90  # Total timeout for the entire ReAct loop


async def run_react_agent(
    message: str,
    skill_prompt: str,
    context: str,
    history: list[dict] = None,
    skill_id: str = "",
) -> tuple[str, list[dict]]:
    """Run ReAct agent loop. Returns (final_answer, tool_calls_log)."""
    try:
        return await asyncio.wait_for(
            _run_react_agent_inner(message, skill_prompt, context, history, skill_id),
            timeout=REACT_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        return "Превышено время ожидания анализа. Попробуйте упростить вопрос.", []


async def _run_react_agent_inner(
    message: str,
    skill_prompt: str,
    context: str,
    history: list[dict] = None,
    skill_id: str = "",
) -> tuple[str, list[dict]]:
    """Inner ReAct loop implementation."""

    tools_desc = get_tools_description()
    system = REACT_SYSTEM.format(tools=tools_desc) + "\n\n" + skill_prompt

    ctx_limit = 60000 if skill_id in DOCUMENT_HEAVY_SKILLS else 15000
    if context:
        system += f"\n\nКОНТЕКСТ ДОКУМЕНТОВ:\n{context[:ctx_limit]}"

    messages = []
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": message})

    tool_log = []

    for iteration in range(MAX_ITERATIONS):
        # Call LLM
        response = await llm_client.chat(system, messages)

        # Check if response contains an ACTION
        action_match = re.search(r'ACTION:\s*(.+?)(?:\n|$)', response, re.DOTALL)

        if action_match and "ANSWER:" not in response:
            # Execute tool
            tool_call = action_match.group(1).strip()
            tool_call = tool_call.strip('`')

            result = execute_tool(tool_call, docs_context=context[:10000])

            tool_log.append({
                "iteration": iteration + 1,
                "thought": re.search(r'THOUGHT:\s*(.+?)(?:ACTION|$)', response, re.DOTALL),
                "action": tool_call,
                "result": result
            })
            # Clean up thought match
            if tool_log[-1]["thought"]:
                tool_log[-1]["thought"] = tool_log[-1]["thought"].group(1).strip()

            # Add to conversation — only action+observation, drop previous context bloat
            messages.append({"role": "assistant", "content": response})

            # Format observation — compact
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
            if len(result_str) > 6000:
                result_str = result_str[:6000] + "\n... (truncated)"

            messages.append({"role": "user", "content": f"OBSERVATION:\n{result_str}\n\nЕсли данных достаточно — дай ANSWER."})

        else:
            # Extract final answer
            answer_match = re.search(r'ANSWER:\s*(.*)', response, re.DOTALL)
            if answer_match:
                answer = answer_match.group(1).strip()
            else:
                answer = response

            return answer, tool_log

    # Max iterations reached — return what we have
    return response, tool_log


async def run_react_agent_stream(
    message: str,
    skill_prompt: str,
    context: str,
    history: list[dict] = None,
    skill_id: str = "",
):
    """Run ReAct agent and yield progress updates."""

    tools_desc = get_tools_description()
    system = REACT_SYSTEM.format(tools=tools_desc) + "\n\n" + skill_prompt

    ctx_limit = 60000 if skill_id in DOCUMENT_HEAVY_SKILLS else 15000
    if context:
        system += f"\n\nКОНТЕКСТ ДОКУМЕНТОВ:\n{context[:ctx_limit]}"

    messages = []
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": message})

    for iteration in range(MAX_ITERATIONS):
        response = await llm_client.chat(system, messages)

        action_match = re.search(r'ACTION:\s*(.+?)(?:\n|$)', response, re.DOTALL)

        if action_match and "ANSWER:" not in response:
            tool_call = action_match.group(1).strip().strip('`')

            # Yield thinking status
            thought = re.search(r'THOUGHT:\s*(.+?)(?:ACTION|$)', response, re.DOTALL)
            if thought:
                yield {"type": "thinking", "content": thought.group(1).strip()[:200]}
            yield {"type": "tool_call", "content": tool_call}

            result = execute_tool(tool_call, docs_context=context[:10000])
            yield {"type": "tool_result", "content": json.dumps(result, ensure_ascii=False)[:2000]}

            messages.append({"role": "assistant", "content": response})
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
            if len(result_str) > 6000:
                result_str = result_str[:6000] + "\n... (truncated)"
            messages.append({"role": "user", "content": f"OBSERVATION:\n{result_str}\n\nЕсли данных достаточно — дай ANSWER."})
        else:
            answer_match = re.search(r'ANSWER:\s*(.*)', response, re.DOTALL)
            answer = answer_match.group(1).strip() if answer_match else response
            yield {"type": "answer", "content": answer}
            return

    yield {"type": "answer", "content": response}
