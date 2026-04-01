"""
Multi-agent architecture for Investment Copilot v2.

Layers:
- orchestrator.py  — routes requests to specialist agents, aggregates results
- base_agent.py    — base class for all specialist agents
- financial.py     — financial analyst (МСФО, DCF, debt, covenants)
- market.py        — market analyst (TAM, competitors, M&A, trends)
- risk.py          — risk analyst (red flags, stress tests)
- sentiment.py     — sentiment analyst (news, ESG, reputation)
- benchmark.py     — benchmark analyst (peers, multiples, valuation)
- fund_director.py — synthesizes all agent outputs into recommendation
"""
