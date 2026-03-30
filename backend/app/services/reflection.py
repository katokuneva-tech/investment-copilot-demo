"""Reflection node — single-pass LLM-judge verifies answer quality."""
from app.services.llm_client import llm_client

REFLECTION_PROMPT = """Ты — верификатор ответов инвестиционного копилота АФК Система.

Проверь ответ аналитика по двум критериям:

1. ФАКТИЧЕСКАЯ ТОЧНОСТЬ:
   - Есть ли ЯВНЫЕ ГАЛЛЮЦИНАЦИИ — цифры, которых НЕТ в данных инструментов/документах?
   - Есть ли ВЫДУМАННЫЕ СУЩНОСТИ — компании или факты, которых нет в данных?
   - Есть ли ГРУБЫЕ ЧИСЛОВЫЕ ОШИБКИ — перепутан порядок, знак, единицы (млн/млрд)?

2. АНАЛИТИЧЕСКАЯ ПОЛНОТА:
   - Рассмотрены ли все релевантные компании/данные?
   - Подкреплены ли выводы цифрами?
   - Указаны ли периоды и источники?

НЕ считай ошибками: пометки "н/д", неполный список если данных нет, стиль.

ОТВЕТ — строго одна строка:
- Если всё ОК: PASS
- Если есть критическая ошибка: FAIL: [точная цитата выдуманного факта]
- Если неполно: INCOMPLETE: [что пропущено, кратко]"""


async def reflect(question: str, answer: str, context_snippet: str, skill_id: str = "") -> tuple[bool, str]:
    """Run single-pass reflection on an answer. Returns (passed, details)."""

    try:
        result = await llm_client.chat(
            system=REFLECTION_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Вопрос: {question}\n\n"
                    f"Данные инструментов/документов:\n{context_snippet[:4000]}\n\n"
                    f"Ответ аналитика:\n{answer[:3000]}"
                )
            }],
            temperature=0.0,
            max_tokens=512,
        )
        result_clean = result.strip()
        if result_clean.upper().startswith("PASS"):
            return True, "PASS"
        elif result_clean.upper().startswith("FAIL"):
            return False, f"FACTUAL: {result_clean}"
        elif result_clean.upper().startswith("INCOMPLETE"):
            return False, result_clean
        else:
            return True, "PASS"
    except Exception as e:
        return True, f"Reflection skipped: {e}"
