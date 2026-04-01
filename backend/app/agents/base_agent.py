"""
Base class for specialist agents.
Each agent has a role, system prompt, set of tools, and produces structured output.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Structured output from a specialist agent."""
    agent_name: str
    role: str
    content: str
    tables: list[dict] = field(default_factory=list)
    red_flags: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.8
    elapsed_sec: float = 0.0
    error: str | None = None


class BaseAgent:
    """Base specialist agent. Subclasses override ROLE, SYSTEM_PROMPT, and optionally run()."""

    NAME: str = "base"
    ROLE: str = "analyst"
    SYSTEM_PROMPT: str = "You are a helpful analyst."
    MODEL_TIER: str = "standard"  # "standard" or "deep" (opus)
    MAX_TOKENS: int = 4096

    def __init__(self, context: str = "", user_query: str = ""):
        self.context = context
        self.user_query = user_query

    async def run(self) -> AgentResult:
        """Execute the agent's analysis. Override in subclasses for custom logic."""
        start = time.monotonic()
        try:
            messages = self._build_messages()
            response = await llm_client.chat(
                system=self.SYSTEM_PROMPT,
                messages=messages,
                temperature=0.15,
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
            elapsed = time.monotonic() - start
            logger.error(f"Agent {self.NAME} failed: {e}")
            return AgentResult(
                agent_name=self.NAME,
                role=self.ROLE,
                content="",
                elapsed_sec=round(elapsed, 1),
                error=str(e),
            )

    def _build_messages(self) -> list[dict]:
        """Build message list for LLM call."""
        parts = []
        if self.context:
            parts.append(f"## Контекст\n{self.context}")
        parts.append(f"## Задача\n{self.user_query}")
        return [{"role": "user", "content": "\n\n".join(parts)}]


AGENT_TIMEOUT_SEC = 30  # Max time per agent before timeout


async def _run_with_timeout(agent: BaseAgent, timeout: float) -> AgentResult:
    """Run a single agent with a timeout."""
    try:
        return await asyncio.wait_for(agent.run(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Agent {agent.NAME} timed out after {timeout}s")
        return AgentResult(
            agent_name=agent.NAME,
            role=agent.ROLE,
            content="",
            error=f"Таймаут ({timeout}с)",
        )
    except Exception as e:
        logger.error(f"Agent {agent.NAME} crashed: {type(e).__name__}: {e}")
        return AgentResult(
            agent_name=agent.NAME,
            role=agent.ROLE,
            content="",
            error=f"{type(e).__name__}: {e}",
        )


async def run_agents_parallel(agents: list[BaseAgent], timeout: float = AGENT_TIMEOUT_SEC) -> list[AgentResult]:
    """Run multiple agents concurrently with per-agent timeout."""
    tasks = [_run_with_timeout(agent, timeout) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final.append(AgentResult(
                agent_name=agents[i].NAME,
                role=agents[i].ROLE,
                content="",
                error=str(result),
            ))
        else:
            final.append(result)
    return final
