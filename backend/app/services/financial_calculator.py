"""Deterministic financial calculations. No LLM involved."""


def calculate_npv(cash_flows: list[float], discount_rate: float) -> float:
    """Standard NPV = sum(CF_t / (1+r)^t)"""
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / (1 + discount_rate) ** t
    return round(npv, 1)


def calculate_irr(cash_flows: list[float], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 100) -> float:
    """Newton-Raphson IRR solver."""
    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-12:
            break
        rate -= npv / dnpv
        if abs(npv) < tol:
            break
    return round(rate, 4)


def calculate_payback(cash_flows: list[float]) -> float:
    """Cumulative cash flow payback period."""
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0 and t > 0:
            prev_cum = cumulative - cf
            fraction = -prev_cum / cf if cf != 0 else 0
            return round(t - 1 + fraction, 1)
    return float(len(cash_flows))


def format_bln(value: float) -> str:
    """Format value in billions."""
    if abs(value) >= 1:
        return f"{value:.1f} млрд руб."
    return f"{value * 1000:.0f} млн руб."


def format_pct(value: float) -> str:
    """Format as percentage."""
    return f"{value * 100:.1f}%"
