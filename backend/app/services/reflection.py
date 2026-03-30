"""Reflection node — single-pass LLM-judge verifies answer quality."""
from app.services.llm_client import llm_client

VERIFY_PROMPT = """Ты — верификатор ответов инвестиционного копилота АФК Система.

Проверь ответ аналитика по двум блокам:

БЛОК 1 — ФАКТИЧЕСКАЯ ТОЧНОСТЬ:
- Есть ли цифры, которых НЕТ в данных?
- Упоминаются ли компании/факты, которых нет в данных?
- Перепутан порядок величин (млн/млрд), знак (+/-)?

БЛОК 2 — ПОЛНОТА:
- Покрыты ли все релевантные компании/показатели?
- Указаны ли периоды для цифр?
- Есть ли выводы, а не только перечисление?

НЕ считай ошибками: пометки "н/д", округления, стиль изложения, неполный список если данных нет.

ОТВЕТ — строго одна строка:
- PASS — если ответ корректен и достаточно полон
- FAIL: [конкретная проблема]
- INCOMPLETE: [что пропущено]"""


async def reflect(question: str, answer: str, context_snippet: str, skill_id: str = "") -> tuple[bool, str]:
    """Run single-pass reflection on an answer. Returns (passed, details)."""
    try:
        result = await llm_client.chat(
            system=VERIFY_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Вопрос: {question}\n\n"
                    f"Данные инструментов/документов:\n{context_snippet[:5000]}\n\n"
                    f"Ответ аналитика:\n{answer[:4000]}"
                )
            }],
            temperature=0.0,
            max_tokens=256,
        )
        result_clean = result.strip()
        if result_clean.upper().startswith("FAIL") or result_clean.upper().startswith("INCOMPLETE"):
            return False, result_clean
    except Exception:
        pass

    return True, "PASS"
