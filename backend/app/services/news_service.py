"""News monitoring service — RSS feeds from Russian financial media + AI analysis."""
import asyncio
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape
from urllib.parse import urlparse

import httpx

from app.services.llm_client import llm_client

# ── RSS Sources ──────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {"name": "РБК", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/corp.xml"},
    {"name": "Интерфакс", "url": "https://www.interfax.ru/rss.asp"},
    {"name": "ТАСС Экономика", "url": "https://tass.ru/rss/ekonomika.xml"},
    {"name": "Smart-lab", "url": "https://smart-lab.ru/rss/"},
    {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss/news"},
]

# ── Portfolio companies with keyword variations for matching ─────────────────
PORTFOLIO_COMPANIES = {
    "afk": {
        "name": "АФК Система",
        "keywords": ["АФК Система", "АФК «Система»", "Sistema", "AFKS"],
    },
    "mts": {
        "name": "МТС",
        "keywords": ["МТС", "MTS", "MTSS"],
    },
    "ozon": {
        "name": "Ozon",
        "keywords": ["Ozon", "Озон", "OZON"],
    },
    "segezha": {
        "name": "Segezha Group",
        "keywords": ["Сегежа", "Segezha", "SGZH"],
    },
    "etalon": {
        "name": "Эталон",
        "keywords": ["Эталон", "Etalon", "ETLN"],
    },
    "medsi": {
        "name": "МЕДСИ",
        "keywords": ["МЕДСИ", "Medsi"],
    },
    "binnopharm": {
        "name": "Биннофарм Групп",
        "keywords": ["Биннофарм", "Binnopharm"],
    },
    "step": {
        "name": "СТЕПЬ",
        "keywords": ["СТЕПЬ", "агрохолдинг СТЕПЬ", "Степь агро"],
    },
    "cosmos": {
        "name": "Cosmos Hotel Group",
        "keywords": ["Cosmos Hotel", "Космос отель", "Cosmos Group"],
    },
}

# ── Cache ────────────────────────────────────────────────────────────────────
_news_cache: dict = {}
_digest_cache: dict = {}
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


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    import re
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


# ── RSS Fetching ─────────────────────────────────────────────────────────────

async def _fetch_rss(client: httpx.AsyncClient, feed: dict) -> list[dict]:
    """Fetch and parse a single RSS feed. Returns raw articles."""
    url = feed["url"]
    source_name = feed["name"]
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        content = resp.text

        root = ET.fromstring(content)

        # Handle both RSS 2.0 and Atom formats
        articles = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0: <channel><item>
        items = root.findall(".//item")
        if not items:
            # Atom: <entry>
            items = root.findall(".//atom:entry", ns) or root.findall(".//entry")

        for item in items[:50]:  # limit per feed
            title = ""
            link = ""
            description = ""
            pub_date = ""

            # RSS 2.0
            t = item.find("title")
            if t is not None and t.text:
                title = t.text.strip()

            l = item.find("link")
            if l is not None:
                link = (l.text or l.get("href", "")).strip()

            d = item.find("description")
            if d is not None and d.text:
                description = _strip_html(d.text)[:300]

            p = item.find("pubDate")
            if p is not None and p.text:
                pub_date = p.text.strip()

            # Atom fallback
            if not title:
                t = item.find("atom:title", ns)
                if t is not None and t.text:
                    title = t.text.strip()
            if not link:
                l = item.find("atom:link", ns)
                if l is not None:
                    link = l.get("href", "")
            if not description:
                d = item.find("atom:summary", ns) or item.find("atom:content", ns)
                if d is not None and d.text:
                    description = _strip_html(d.text)[:300]

            if title and link:
                articles.append({
                    "title": title,
                    "url": link,
                    "snippet": description,
                    "source": source_name,
                    "pub_date": pub_date,
                })

        return articles
    except Exception as e:
        print(f"[NEWS] RSS error {source_name}: {e}")
        return []


def _match_company(title: str, snippet: str) -> tuple[str, str] | None:
    """Match article to a portfolio company. Returns (slug, name) or None."""
    text = (title + " " + snippet).lower()
    for slug, info in PORTFOLIO_COMPANIES.items():
        for kw in info["keywords"]:
            if kw.lower() in text:
                return slug, info["name"]
    return None


async def fetch_all_news() -> list[dict]:
    """Fetch RSS feeds and match articles to portfolio companies."""
    async with httpx.AsyncClient(
        headers={"User-Agent": "MWS-CopilotBot/1.0"},
        follow_redirects=True,
    ) as client:
        tasks = [_fetch_rss(client, feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten all RSS articles
    all_raw = []
    for result in results:
        if isinstance(result, list):
            all_raw.extend(result)

    print(f"[NEWS] Fetched {len(all_raw)} raw RSS articles from {len(RSS_FEEDS)} feeds")

    # Match to portfolio companies
    matched = []
    seen_urls = set()
    for raw in all_raw:
        if raw["url"] in seen_urls:
            continue

        match = _match_company(raw["title"], raw["snippet"])
        if not match:
            continue

        slug, company_name = match
        seen_urls.add(raw["url"])
        matched.append({
            "id": _article_id(raw["url"], raw["title"]),
            "company_slug": slug,
            "company_name": company_name,
            "title": raw["title"],
            "url": raw["url"],
            "snippet": raw["snippet"],
            "source": raw["source"],
            "published_approx": raw.get("pub_date", "")[:16],
            "sentiment": "neutral",
            "summary": "",
            "alert_type": None,
            "portfolio_impact": None,
        })

    print(f"[NEWS] Matched {len(matched)} articles to portfolio companies")
    return matched


# ── LLM Analysis ─────────────────────────────────────────────────────────────

async def _analyze_batch(articles: list[dict]) -> list[dict]:
    """Analyze articles with LLM: sentiment, summary, alerts, portfolio impact."""
    if not articles:
        return articles

    kb_summary = _get_kb_summary()

    items_text = ""
    for i, a in enumerate(articles[:60]):
        items_text += f"\n[{i}] Компания: {a['company_name']}\nЗаголовок: {a['title']}\nФрагмент: {a['snippet'][:200]}\nИсточник: {a['source']}\n"

    prompt = f"""Ты — инвестиционный аналитик АФК Система. Проанализируй новости по портфельным компаниям.

Для КАЖДОЙ новости определи:
1. sentiment: "positive" | "negative" | "neutral"
2. summary: одно предложение на русском (суть новости для инвестора)
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

    return articles


# ── Dashboard Metrics ────────────────────────────────────────────────────────

def get_dashboard_metrics(articles: list[dict]) -> dict:
    """Compute dashboard metrics from analyzed articles."""
    total = len(articles)
    positive = sum(1 for a in articles if a["sentiment"] == "positive")
    negative = sum(1 for a in articles if a["sentiment"] == "negative")
    neutral = total - positive - negative

    company_stats: dict[str, dict] = {}
    for a in articles:
        slug = a["company_slug"]
        if slug not in company_stats:
            company_stats[slug] = {"slug": slug, "name": a["company_name"], "positive": 0, "negative": 0, "neutral": 0, "total": 0}
        company_stats[slug][a["sentiment"]] = company_stats[slug].get(a["sentiment"], 0) + 1
        company_stats[slug]["total"] += 1

    sentiment_by_company = sorted(company_stats.values(), key=lambda x: x["total"], reverse=True)

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


# ── Cache Management ─────────────────────────────────────────────────────────

async def _ensure_cache() -> None:
    """Ensure cache is populated, with lock to prevent concurrent refreshes."""
    if _cache_valid():
        return
    async with _get_lock():
        if _cache_valid():
            return
        await refresh_news()


async def refresh_news() -> dict:
    """Fetch + analyze + cache."""
    articles = await fetch_all_news()
    articles = await _analyze_batch(articles)
    dashboard = get_dashboard_metrics(articles)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

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

    # Clear digest cache on refresh
    _digest_cache.clear()

    return _news_cache


# ── Public API ───────────────────────────────────────────────────────────────

async def get_news(company: str | None = None, sentiment: str | None = None, limit: int = 50) -> dict:
    await _ensure_cache()
    articles = _news_cache.get("articles", [])

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
    await _ensure_cache()
    return _news_cache.get("dashboard", {})


async def get_alerts() -> list[dict]:
    await _ensure_cache()
    return _news_cache.get("dashboard", {}).get("alerts", [])


def get_companies() -> list[dict]:
    return [{"slug": slug, "name": info["name"]} for slug, info in PORTFOLIO_COMPANIES.items()]


async def generate_digest(period: str = "day") -> dict:
    """Generate AI analytical digest."""
    cached = _digest_cache.get(period)
    if cached and time.time() - cached.get("generated_at_ts", 0) < 1800:
        return cached

    await _ensure_cache()

    articles = _news_cache.get("articles", [])
    if not articles:
        return {"digest": "Нет новостей по портфельным компаниям в текущих RSS-лентах.", "period": period, "article_count": 0, "generated_at": ""}

    summaries = []
    for a in articles[:40]:
        sentiment_emoji = {"positive": "+", "negative": "-", "neutral": "="}.get(a["sentiment"], "=")
        summaries.append(f"[{sentiment_emoji}] {a['company_name']}: {a.get('summary') or a['title']} ({a['source']})")

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
