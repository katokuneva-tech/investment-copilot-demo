"""News monitoring service — fetch, analyze, and digest portfolio news."""
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime
from urllib.parse import urlparse

from app.services.llm_client import llm_client

# Portfolio companies with search aliases and keywords for relevance filtering
PORTFOLIO_COMPANIES = {
    "afk": {
        "name": "АФК Система",
        "queries": ["АФК Система инвестиции холдинг"],
        "keywords": ["АФК", "Система", "Sistema"],
    },
    "mts": {
        "name": "МТС",
        "queries": ["МТС телеком акции"],
        "keywords": ["МТС", "MTS"],
    },
    "ozon": {
        "name": "Ozon",
        "queries": ["Ozon маркетплейс акции"],
        "keywords": ["Ozon", "Озон"],
    },
    "segezha": {
        "name": "Segezha Group",
        "queries": ["Сегежа Group лесопромышленный"],
        "keywords": ["Сегежа", "Segezha"],
    },
    "etalon": {
        "name": "Эталон",
        "queries": ["Группа Эталон девелопер акции"],
        "keywords": ["Эталон", "Etalon"],
    },
    "medsi": {
        "name": "МЕДСИ",
        "queries": ["МЕДСИ клиники медицина"],
        "keywords": ["МЕДСИ", "Medsi"],
    },
    "binnopharm": {
        "name": "Биннофарм Групп",
        "queries": ["Биннофарм фармацевтика"],
        "keywords": ["Биннофарм", "Binnopharm"],
    },
    "step": {
        "name": "СТЕПЬ",
        "queries": ["Агрохолдинг СТЕПЬ"],
        "keywords": ["СТЕПЬ", "агрохолдинг"],
    },
    "cosmos": {
        "name": "Cosmos Hotel Group",
        "queries": ["Cosmos Hotel Group гостиницы Россия"],
        "keywords": ["Cosmos Hotel", "Космос отель"],
    },
}

# Cache
_news_cache: dict = {}  # {articles, dashboard, fetched_at}
_digest_cache: dict = {}  # {period: {digest, generated_at}}
_refresh_lock: asyncio.Lock | None = None
CACHE_TTL = 3600  # 1 hour


def _get_lock() -> asyncio.Lock:
    global _refresh_lock
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    return _refresh_lock


def _cache_valid() -> bool:
    if not _news_cache:
        return False
    return time.time() - _news_cache.get("fetched_at", 0) < CACHE_TTL


def _article_id(url: str, title: str) -> str:
    return hashlib.md5(f"{url}:{title}".encode()).hexdigest()[:12]


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _get_kb_summary() -> str:
    """Extract brief company profiles from KB for LLM context."""
    try:
        import os
        kb_path = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base.json")
        with open(kb_path, "r", encoding="utf-8") as f:
            kb = json.load(f)
        profiles = kb.get("company_profiles", {})
        parts = []
        for name, data in profiles.items():
            val = data.get("valuation_context", "")
            risks = ", ".join(data.get("key_risks", [])[:2])
            parts.append(f"- {name}: {val}. Риски: {risks}")
        return "\n".join(parts)
    except Exception:
        return ""


def _is_relevant(title: str, snippet: str, keywords: list[str]) -> bool:
    """Check if article is relevant to the company by keyword match."""
    text = (title + " " + snippet).lower()
    return any(kw.lower() in text for kw in keywords)


async def _fetch_company_news(slug: str, info: dict) -> list[dict]:
    """Fetch news for a single company using DDG news search."""
    query = info["queries"][0]
    keywords = info.get("keywords", [info["name"]])
    try:
        from duckduckgo_search import DDGS

        loop = asyncio.get_event_loop()

        def _search():
            with DDGS() as ddgs:
                # Use news() for actual news articles, with Russian region
                try:
                    results = list(ddgs.news(query, region="ru-ru", max_results=8))
                except Exception:
                    # Fallback to text search if news() fails
                    results = list(ddgs.text(query, region="ru-ru", max_results=8))
            return results

        results = await loop.run_in_executor(None, _search)

        articles = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url") or r.get("href", "")
            snippet = r.get("body", "") or r.get("snippet", "")
            date = r.get("date", "")

            if not url or title.startswith("Search error"):
                continue

            # Filter out irrelevant results
            if not _is_relevant(title, snippet, keywords):
                continue

            articles.append({
                "id": _article_id(url, title),
                "company_slug": slug,
                "company_name": info["name"],
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": _extract_domain(url),
                "published_approx": date[:10] if date else "",
                "sentiment": "neutral",
                "summary": "",
                "alert_type": None,
                "portfolio_impact": None,
            })
        return articles[:5]
    except Exception as e:
        print(f"[NEWS] Error fetching {slug}: {e}")
        return []


async def fetch_all_news() -> list[dict]:
    """Fetch news for all portfolio companies in batches."""
    all_articles = []
    companies = list(PORTFOLIO_COMPANIES.items())

    # Batch by 4 companies with 1s delay between batches
    batch_size = 4
    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]
        tasks = [_fetch_company_news(slug, info) for slug, info in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        if i + batch_size < len(companies):
            await asyncio.sleep(1.0)

    # Deduplicate by url
    seen_urls = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)

    return unique


async def _analyze_batch(articles: list[dict]) -> list[dict]:
    """Analyze articles with LLM: sentiment, summary, alerts, portfolio impact. One call."""
    if not articles:
        return articles

    kb_summary = _get_kb_summary()

    items_text = ""
    for i, a in enumerate(articles[:60]):  # limit to 60 articles
        items_text += f"\n[{i}] Компания: {a['company_name']}\nЗаголовок: {a['title']}\nФрагмент: {a['snippet'][:200]}\n"

    prompt = f"""Ты — инвестиционный аналитик АФК Система. Проанализируй новости по портфельным компаниям.

Для КАЖДОЙ новости определи:
1. sentiment: "positive" | "negative" | "neutral"
2. summary: одно предложение на русском (суть новости)
3. alert_type: null или один из: "ipo", "management", "legal", "rating", "deal", "debt", "regulatory"
   (только если новость действительно важная — IPO, смена руководства, суд, рейтинг, сделка, долг, регулятор)
4. portfolio_impact: null или объект с полями:
   - metric: какой финансовый показатель затронут (EV/EBITDA, выручка, долг, маржа и т.д.)
   - direction: "positive" | "negative" | "risk" | "opportunity"
   - context: краткое пояснение привязки к портфелю (1 предложение)

Данные по портфелю для привязки:
{kb_summary}

Новости:
{items_text}

Верни JSON-массив (без markdown):
[{{"index": 0, "sentiment": "...", "summary": "...", "alert_type": null, "portfolio_impact": null}}, ...]"""

    try:
        response = await llm_client.chat(
            system="Ты аналитик. Верни ТОЛЬКО JSON-массив, без markdown-обёрток.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        # Extract JSON from response
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        analysis = json.loads(text)

        for item in analysis:
            idx = item.get("index", -1)
            if 0 <= idx < len(articles):
                articles[idx]["sentiment"] = item.get("sentiment", "neutral")
                articles[idx]["summary"] = item.get("summary", "")
                articles[idx]["alert_type"] = item.get("alert_type")
                impact = item.get("portfolio_impact")
                if impact and isinstance(impact, dict):
                    articles[idx]["portfolio_impact"] = {
                        "company_slug": articles[idx]["company_slug"],
                        "metric": impact.get("metric", ""),
                        "direction": impact.get("direction", "neutral"),
                        "context": impact.get("context", ""),
                    }
    except Exception as e:
        print(f"[NEWS] LLM analysis error: {e}")
        # Fallback: all neutral, no alerts

    return articles


def get_dashboard_metrics(articles: list[dict]) -> dict:
    """Compute dashboard metrics from analyzed articles."""
    total = len(articles)
    positive = sum(1 for a in articles if a["sentiment"] == "positive")
    negative = sum(1 for a in articles if a["sentiment"] == "negative")
    neutral = total - positive - negative

    # Sentiment by company
    company_stats: dict[str, dict] = {}
    for a in articles:
        slug = a["company_slug"]
        if slug not in company_stats:
            company_stats[slug] = {"slug": slug, "name": a["company_name"], "positive": 0, "negative": 0, "neutral": 0, "total": 0}
        company_stats[slug][a["sentiment"]] = company_stats[slug].get(a["sentiment"], 0) + 1
        company_stats[slug]["total"] += 1

    sentiment_by_company = sorted(company_stats.values(), key=lambda x: x["total"], reverse=True)

    # Alerts
    alerts = []
    for a in articles:
        if a.get("alert_type"):
            severity = "high" if a["sentiment"] == "negative" else "medium"
            alerts.append({
                "id": a["id"],
                "company_slug": a["company_slug"],
                "company_name": a["company_name"],
                "alert_type": a["alert_type"],
                "title": a["title"],
                "description": a.get("summary", a["snippet"][:100]),
                "severity": severity,
            })

    # Top companies by count
    top_companies = [{"slug": c["slug"], "name": c["name"], "count": c["total"]} for c in sentiment_by_company[:5]]

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "sentiment_by_company": sentiment_by_company,
        "alerts": alerts,
        "top_companies": top_companies,
    }


async def _ensure_cache() -> None:
    """Ensure cache is populated, with lock to prevent concurrent refreshes."""
    if _cache_valid():
        return
    async with _get_lock():
        # Double-check after acquiring lock
        if _cache_valid():
            return
        await refresh_news()


async def refresh_news() -> dict:
    """Fetch + analyze + cache. Returns full news response."""
    articles = await fetch_all_news()
    print(f"[NEWS] Fetched {len(articles)} articles")
    articles = await _analyze_batch(articles)
    dashboard = get_dashboard_metrics(articles)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build companies list
    company_counts: dict[str, dict] = {}
    for a in articles:
        slug = a["company_slug"]
        if slug not in company_counts:
            company_counts[slug] = {"slug": slug, "name": a["company_name"], "article_count": 0}
        company_counts[slug]["article_count"] += 1

    _news_cache.update({
        "articles": articles,
        "dashboard": dashboard,
        "companies": sorted(company_counts.values(), key=lambda x: x["article_count"], reverse=True),
        "last_updated": now,
        "fetched_at": time.time(),
    })

    return _news_cache


async def get_news(company: str | None = None, sentiment: str | None = None, limit: int = 50) -> dict:
    """Get cached or fresh news, with optional filters."""
    await _ensure_cache()

    articles = _news_cache.get("articles", [])

    # Server-side filtering (optional, client can also filter)
    if company and company != "all":
        articles = [a for a in articles if a["company_slug"] == company]
    if sentiment and sentiment != "all":
        articles = [a for a in articles if a["sentiment"] == sentiment]

    return {
        "articles": articles[:limit],
        "last_updated": _news_cache.get("last_updated", ""),
        "companies": _news_cache.get("companies", []),
    }


async def get_dashboard() -> dict:
    """Get dashboard metrics."""
    await _ensure_cache()
    return _news_cache.get("dashboard", {})


async def get_alerts() -> list[dict]:
    """Get active alerts."""
    await _ensure_cache()
    return _news_cache.get("dashboard", {}).get("alerts", [])


def get_companies() -> list[dict]:
    """Get portfolio companies list for filter dropdown."""
    return [{"slug": slug, "name": info["name"]} for slug, info in PORTFOLIO_COMPANIES.items()]


async def generate_digest(period: str = "day") -> dict:
    """Generate AI analytical digest. One LLM call."""
    # Check digest cache
    cached = _digest_cache.get(period)
    if cached and time.time() - cached.get("generated_at_ts", 0) < 1800:  # 30 min cache
        return cached

    await _ensure_cache()

    articles = _news_cache.get("articles", [])
    if not articles:
        return {"digest": "Нет данных для дайджеста.", "period": period, "article_count": 0, "generated_at": ""}

    # Prepare summaries for LLM
    summaries = []
    for a in articles[:40]:
        sentiment_emoji = {"positive": "+", "negative": "-", "neutral": "="}.get(a["sentiment"], "=")
        summaries.append(f"[{sentiment_emoji}] {a['company_name']}: {a.get('summary') or a['title']}")

    kb_summary = _get_kb_summary()
    period_label = "сегодня" if period == "day" else "за неделю"

    prompt = f"""Составь аналитический дайджест новостей по портфелю АФК Система ({period_label}).

Новости ({len(summaries)} шт.):
{chr(10).join(summaries)}

Данные портфеля:
{kb_summary}

Формат ответа (markdown):

## Ключевые события
(3-5 самых важных новостей с контекстом)

## Влияние на портфель
(привязка к конкретным метрикам: выручка, EBITDA, мультипликаторы, долг)

## Риски и красные флаги
(негативные новости → конкретные последствия для холдинга)

## Возможности
(позитивные новости → потенциал роста)

## Рекомендации для инвесткомитета
(2-3 конкретных action items)"""

    try:
        response = await llm_client.chat(
            system="Ты старший инвестиционный аналитик АФК Система. Пиши на русском, кратко и по делу.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        result = {
            "digest": response.strip(),
            "period": period,
            "article_count": len(articles),
            "generated_at": now,
            "generated_at_ts": time.time(),
        }
        _digest_cache[period] = result
        return result
    except Exception as e:
        print(f"[NEWS] Digest generation error: {e}")
        return {"digest": f"Ошибка генерации дайджеста: {e}", "period": period, "article_count": 0, "generated_at": ""}
