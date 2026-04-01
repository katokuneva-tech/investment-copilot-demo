"""
Orchestrator — routes user requests to specialist agents based on use case,
runs them in parallel, then synthesizes via FundDirector.

Use cases:
  UC1 portfolio  — FinancialAgent + SentimentAgent → FundDirector
  UC2 investment — FinancialAgent + MarketAgent + RiskAgent + BenchmarkAgent → FundDirector
  UC3 market     — MarketAgent (x3 queries) → FundDirector
  UC4 benchmark  — BenchmarkAgent + FinancialAgent → FundDirector
  UC5 committee  — Light (Fin+Risk+Sent) or Full (all 5) → FundDirector
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

from app.agents.base_agent import AgentResult, run_agents_parallel
from app.agents.financial import FinancialAgent
from app.agents.market import MarketAgent
from app.agents.risk import RiskAgent
from app.agents.sentiment import SentimentAgent
from app.agents.benchmark import BenchmarkAgent
from app.agents.fund_director import FundDirector, run_qa_loop
from app.agents.data_guard import DataGuard, apply_corrections
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

# ── Use case → skill_id mapping ──────────────────────────────────────────

USE_CASE_MAP = {
    "portfolio_analytics": "portfolio",
    "investment_analysis": "investment",
    "market_research": "market",
    "benchmarking": "benchmark",
    "committee_advisor": "committee",
}


@dataclass
class OrchestratorResult:
    """Final output from the orchestrator pipeline."""
    use_case: str
    final_answer: str
    agent_results: list[AgentResult]
    director_result: AgentResult | None
    total_elapsed_sec: float
    agents_used: list[str]


# ── Intent classification ────────────────────────────────────────────────

CLASSIFY_PROMPT = """Определи тип запроса пользователя по портфелю АФК Система.

Варианты:
- portfolio_analytics — вопрос по портфельным компаниям (выручка, долг, дивиденды, рост, ковенанты, менеджмент)
- investment_analysis — оценка инвестиционного проекта/сделки (NPV, IRR, предпосылки, due diligence)
- market_research — анализ рынка/сектора (размер, рост, игроки, тренды, M&A)
- benchmarking — сравнение компаний с аналогами (мультипликаторы, peers, implied valuation)
- committee_advisor — подготовка к комитету, анализ материалов сделки, протокол

Ответь ОДНИМ словом — id скилла. Если не уверен, ответь portfolio_analytics."""


async def classify_intent(message: str) -> str:
    """Classify user intent into one of 5 use cases."""
    try:
        response = await llm_client.chat(
            system=CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": message}],
            temperature=0.0,
            max_tokens=50,
        )
        skill_id = response.strip().lower().replace('"', '').replace("'", "")
        if skill_id in USE_CASE_MAP:
            return skill_id
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
    return "portfolio_analytics"


# ── Agent factory per use case ───────────────────────────────────────────

def _extract_companies(message: str, context: str) -> list[str]:
    """Extract company names mentioned in message/context for news search."""
    known = ["МТС", "Segezha", "Эталон", "МЕДСИ", "Биннофарм",
             "СТЕПЬ", "Cosmos Hotel Group", "Natura Siberica",
             "АФК Система"]
    found = []
    text = (message + " " + context).lower()
    for c in known:
        if c.lower() in text:
            found.append(c)
    # If no specific company mentioned and it's a portfolio question, include top ones
    if not found:
        found = ["АФК Система", "МТС", "Segezha", "Эталон", "СТЕПЬ"]
    return found[:5]


def _is_committee_light(message: str) -> bool:
    """Detect if a committee query needs all 5 agents (full) or can use 3 (light).

    Full = requires specific financial modeling (NPV/IRR calc, deal valuation, DD).
    Light = everything else (questions, summaries, overviews, risk lists, protocols).
    """
    msg = message.lower()
    # Only these very specific triggers warrant full 5-agent pipeline
    full_triggers = [
        "рассчитай npv", "рассчитай irr", "оцени сделку", "оценка сделки",
        "оцени стоимость", "мультипликаторы сделки", "implied valuation",
    ]
    return not any(t in msg for t in full_triggers)


def _extract_search_queries(message: str, use_case: str) -> list[str]:
    """Generate web search queries based on user message and use case."""
    queries = []
    if use_case == "market":
        queries = [
            f"{message} размер рынка Россия 2025",
            f"{message} ключевые игроки доля рынка",
            f"{message} M&A сделки 2024 2025 2026",
        ]
    elif use_case == "benchmark":
        queries = [
            f"{message} EV/EBITDA мультипликаторы аналоги",
            f"{message} финансовые показатели конкуренты",
        ]
    elif use_case == "investment":
        queries = [
            f"{message} рынок размер рост Россия",
            f"{message} аналоги мультипликаторы сделки",
        ]
    return queries


def build_agents(use_case: str, message: str, context: str) -> list:
    """Build the right set of agents for a given use case."""
    companies = _extract_companies(message, context)
    search_q = _extract_search_queries(message, use_case)

    if use_case == "portfolio":
        return [
            FinancialAgent(context=context, user_query=message),
            SentimentAgent(context=context, user_query=f"Найди последние новости и оцени сентимент по компаниям: {', '.join(companies)}", companies=companies),
        ]

    elif use_case == "investment":
        return [
            FinancialAgent(context=context, user_query=f"Проанализируй финансовую модель и рассчитай NPV/IRR. Проведи анализ чувствительности.\n\nЗапрос: {message}"),
            MarketAgent(context=context, user_query=f"Верифицируй предпосылки финмодели против рыночных данных. Найди размер и динамику рынка.\n\nЗапрос: {message}", search_queries=search_q),
            RiskAgent(context=context, user_query=f"Найди red flags, составь матрицу рисков и DD чеклист.\n\nЗапрос: {message}"),
            BenchmarkAgent(context=context, user_query=f"Найди аналоги, сравни мультипликаторы, оцени справедливость цены.\n\nЗапрос: {message}", search_queries=search_q),
        ]

    elif use_case == "market":
        return [
            MarketAgent(context=context, user_query=f"Размер рынка, динамика, сегменты, маржинальность.\n\nЗапрос: {message}", search_queries=[search_q[0]] if search_q else []),
            MarketAgent(context=context, user_query=f"Ключевые игроки, доли рынка, M&A сделки.\n\nЗапрос: {message}", search_queries=[search_q[1]] if len(search_q) > 1 else []),
            SentimentAgent(context=context, user_query=f"Тренды, регуляторика, прогнозы, основные новости.\n\nЗапрос: {message}", companies=[]),
        ]

    elif use_case == "benchmark":
        return [
            BenchmarkAgent(context=context, user_query=f"Найди аналоги и сравни мультипликаторы.\n\nЗапрос: {message}", search_queries=search_q),
            FinancialAgent(context=context, user_query=f"Рассчитай implied valuation, премии/дисконты к медиане peers.\n\nЗапрос: {message}"),
        ]

    elif use_case == "committee":
        is_light = _is_committee_light(message)
        if is_light:
            # Light mode: 2 agents, zero WebSearch — fast document analysis
            logger.info("Committee LIGHT mode: Fin + Risk (no WebSearch)")
            return [
                FinancialAgent(context=context, user_query=f"Проанализируй документы и подготовь финансовую сводку: метрики, противоречия, ключевые цифры.\n\nЗапрос: {message}"),
                RiskAgent(context=context, user_query=f"Проанализируй документы: red flags, риски, DD чеклист, вопросы для менеджмента.\n\nЗапрос: {message}"),
            ]
        else:
            # Full mode: specific deal/investment analysis — all 5 agents
            logger.info("Committee FULL mode: all 5 agents + WebSearch")
            return [
                FinancialAgent(context=context, user_query=f"Проверь IRR/NPV, найди противоречия между документами.\n\nЗапрос: {message}"),
                MarketAgent(context=context, user_query=f"Проверь рыночный контекст и предпосылки.\n\nЗапрос: {message}", search_queries=search_q),
                RiskAgent(context=context, user_query=f"Найди все red flags, составь DD чеклист и вопросы для менеджмента.\n\nЗапрос: {message}"),
                SentimentAgent(context=context, user_query=f"Проверь репутацию контрагента и информационный фон.\n\nЗапрос: {message}", companies=companies),
                BenchmarkAgent(context=context, user_query=f"Сравни мультипликатор сделки с аналогами.\n\nЗапрос: {message}", search_queries=search_q),
            ]

    # Fallback
    return [
        FinancialAgent(context=context, user_query=message),
    ]


# ── Main orchestration ───────────────────────────────────────────────────

async def orchestrate(
    skill_id: str,
    message: str,
    context: str,
    history: list[dict] | None = None,
) -> OrchestratorResult:
    """
    Main entry point for v2 multi-agent pipeline.

    1. Classify intent (if skill_id == "auto")
    2. Build specialist agents for the use case
    3. Run agents in parallel
    4. Synthesize via FundDirector
    5. Return structured result
    """
    start = time.monotonic()

    # Step 1: Intent classification
    if skill_id == "auto":
        skill_id = await classify_intent(message)
    use_case = USE_CASE_MAP.get(skill_id, "portfolio")

    logger.info(f"Orchestrator: use_case={use_case}, skill_id={skill_id}")

    # Step 2: Build agents
    agents = build_agents(use_case, message, context)
    agent_names = [a.NAME for a in agents]
    logger.info(f"Orchestrator: launching {len(agents)} agents: {agent_names}")

    # Step 3: Run in parallel
    agent_results = await run_agents_parallel(agents)

    # Log results
    for r in agent_results:
        status = "OK" if not r.error else f"ERROR: {r.error}"
        logger.info(f"  {r.agent_name}: {status} ({r.elapsed_sec}s)")

    # Step 4: Data Guard — cross-validate analyst reports
    successful_results = [r for r in agent_results if not r.error]
    director_result = None

    # Data Guard only for 3+ agents (skip for light committee with 2 agents — Director handles validation)
    if successful_results and len(successful_results) >= 3:
        guard = DataGuard(context=context, agent_results=successful_results)
        guard_result = await guard.run()
        agent_results.append(guard_result)  # Track in results

        if guard_result.content:
            try:
                parsed = guard.parse_result()
                parsed["_raw"] = guard_result.content  # Preserve for debugging
                guard_result.content = guard_result.content  # Keep original for logging
                n_issues = len(parsed.get("issues", []))
                logger.info(f"DataGuard: status={parsed.get('status')}, issues={n_issues}")

                if parsed.get("status") == "corrections_needed" and n_issues > 0:
                    successful_results = apply_corrections(successful_results, parsed)
                    logger.info(f"DataGuard: applied corrections to {n_issues} issues")
            except Exception as e:
                logger.warning(f"DataGuard parse failed, proceeding: {e}")

    # Step 5: Director Q&A loop (only for complex use cases — investment or full committee)
    qa_context = ""
    needs_qa = (
        successful_results
        and len(successful_results) >= 3
        and (
            use_case == "investment"
            or (use_case == "committee" and not _is_committee_light(message))
        )
    )
    if needs_qa:
        try:
            qa_context = await run_qa_loop(successful_results, message, context)
            if qa_context:
                logger.info(f"Director Q&A: received follow-up answers ({len(qa_context)} chars)")
        except Exception as e:
            logger.warning(f"Director Q&A loop failed, proceeding: {e}")

    # Step 6: Synthesize via FundDirector
    if successful_results:
        director = FundDirector.synthesize(
            agent_results=successful_results,
            user_query=message,
            use_case=use_case,
            qa_context=qa_context,
        )
        director_result = await director.run()

    # Build final answer
    if director_result and not director_result.error:
        final_answer = director_result.content
    elif successful_results:
        # Fallback: concatenate agent results
        final_answer = "\n\n---\n\n".join(
            f"## {r.role}\n{r.content}" for r in successful_results
        )
    else:
        final_answer = "Не удалось получить анализ. Все агенты вернули ошибки."

    total = time.monotonic() - start

    return OrchestratorResult(
        use_case=use_case,
        final_answer=final_answer,
        agent_results=agent_results,
        director_result=director_result,
        total_elapsed_sec=round(total, 1),
        agents_used=agent_names,
    )


async def orchestrate_stream(
    skill_id: str,
    message: str,
    context: str,
    history: list[dict] | None = None,
):
    """
    Streaming version of orchestrate.
    Yields SSE-compatible events as agents complete and director synthesizes.
    """
    import json

    # Step 1: Classify
    if skill_id == "auto":
        skill_id = await classify_intent(message)
    use_case = USE_CASE_MAP.get(skill_id, "portfolio")

    # Step 2: Build agents
    agents = build_agents(use_case, message, context)
    agent_names = [a.NAME for a in agents]

    # Emit: agents started
    yield json.dumps({
        "type": "agents_started",
        "agents": [{"name": a.NAME, "role": a.ROLE} for a in agents],
        "use_case": use_case,
    })

    # Step 3: Run agents with staggered start + timeout
    from app.agents.base_agent import AGENT_TIMEOUT_SEC, _run_with_timeout
    tasks = {}
    for i, a in enumerate(agents):
        if i > 0:
            await asyncio.sleep(1.5)  # Stagger to avoid rate limits
        tasks[a.NAME] = asyncio.create_task(_run_with_timeout(a, AGENT_TIMEOUT_SEC))
    agent_results: list[AgentResult] = []

    # Wait for each to complete, emit progress
    for name, task in tasks.items():
        result = await task
        agent_results.append(result)
        status = "done" if not result.error else "error"
        yield json.dumps({
            "type": "agent_progress",
            "agent": name,
            "role": result.role,
            "status": status,
            "elapsed": result.elapsed_sec,
            "error": result.error or "",
            "preview": result.content[:200] if result.content else result.error or "",
        })

    # Step 4: Data Guard validation
    successful = [r for r in agent_results if not r.error]

    # Data Guard only for 3+ agents (skip for light committee — Director handles validation)
    if successful and len(successful) >= 3:
        yield json.dumps({"type": "status", "message": "Проверяю данные (Data Guard)..."})

        guard = DataGuard(context=context, agent_results=successful)
        guard_result = await guard.run()

        if guard_result.content and not guard_result.error:
            try:
                parsed = guard.parse_result()
                n_issues = len(parsed.get("issues", []))
                guard_status = parsed.get("status", "validated")

                yield json.dumps({
                    "type": "agent_progress",
                    "agent": "data_guard",
                    "role": "Data Guard",
                    "status": "done",
                    "elapsed": guard_result.elapsed_sec,
                    "preview": f"{guard_status}: {n_issues} issues" if n_issues else "validated",
                })

                if guard_status == "corrections_needed" and n_issues > 0:
                    successful = apply_corrections(successful, parsed)
            except Exception:
                pass

    # Step 5: Director Q&A loop (only for investment or full committee with deal analysis)
    qa_context = ""
    needs_qa = (
        successful
        and len(successful) >= 3
        and (
            use_case == "investment"
            or (use_case == "committee" and not _is_committee_light(message))
        )
    )
    if needs_qa:
        yield json.dumps({"type": "status", "message": "Директор уточняет у аналитиков..."})

        try:
            qa_context = await run_qa_loop(successful, message, context)
            if qa_context:
                yield json.dumps({
                    "type": "agent_progress",
                    "agent": "director_qa",
                    "role": "Q&A Директора",
                    "status": "done",
                    "elapsed": 0,
                    "preview": f"Получены ответы на уточняющие вопросы",
                })
        except Exception:
            pass

    # Step 6: Synthesize
    yield json.dumps({"type": "status", "message": "Синтезирую заключение..."})

    if successful:
        director = FundDirector.synthesize(
            agent_results=successful,
            user_query=message,
            use_case=use_case,
            qa_context=qa_context,
        )

        # Stream the director's response
        try:
            messages = director._build_messages()
            async for chunk in llm_client.stream(
                system=director.SYSTEM_PROMPT,
                messages=messages,
                temperature=0.15,
            ):
                yield json.dumps({"type": "text", "content": chunk})
        except Exception as e:
            # Fallback to non-streaming
            result = await director.run()
            yield json.dumps({"type": "text", "content": result.content})
    else:
        yield json.dumps({
            "type": "text",
            "content": "Не удалось получить анализ от агентов.",
        })

    # Emit: done
    yield json.dumps({
        "type": "done",
        "agents_used": agent_names,
        "use_case": use_case,
    })
