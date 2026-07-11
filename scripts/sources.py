"""
Data source fetchers for the elevator industry daily digest.
xindianti.cn RSS is the primary Chinese news source.
"""

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests


# Elevator industry key signals for importance estimation
HIGH_SIGNAL_KEYWORDS = [
    "事故", "伤亡", "通报", "召回", "约谈", "罚款", "停业",
    "标准", "法规", "政策", "通知", "监管", "整治", "专项",
    "发布", "上市", "融资", "收购", "中标", "签约",
    "加装", "更新", "改造", "焕新", "国债", "补贴",
    "智慧", "智能", "物联网", "数字化", "平台",
    "康力", "博林特", "奥的斯", "通力", "迅达", "蒂森",
    "远大", "西奥", "江南嘉捷", "广日",
]

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def clean_text(value, max_chars=500):
    """Strip HTML and whitespace noise from source summaries."""
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def normalize_url(url):
    """Normalize URLs so the same story is easier to dedupe."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query, doseq=True),
        "",
    ))


def normalize_title(title):
    return re.sub(r"\W+", "", (title or "").lower())


def estimate_importance(category, title, summary, source):
    """First-pass importance signal based on elevator industry relevance."""
    text = f"{title} {summary} {source}".lower()
    score = 3

    if category == "regulation":
        score += 1  # 政策标准优先
    if any(keyword in text for keyword in HIGH_SIGNAL_KEYWORDS):
        score += 1
    if any(w in text for w in [
        "事故", "伤亡", "新标准", "gb", "tsg", "总局", "住建部",
        "市场监管局", "应急管理",
    ]):
        score += 1

    return max(1, min(5, score))


def make_item(category, title, url, summary, source, published=None, metadata=None):
    cleaned_summary = clean_text(summary)
    return {
        "category": category,
        "title": clean_text(title, max_chars=220),
        "url": url or "",
        "normalized_url": normalize_url(url),
        "summary": cleaned_summary,
        "source": source,
        "published": published,
        "importance_hint": estimate_importance(category, title, cleaned_summary, source),
        "metadata": metadata or {},
    }


def dedupe_items(items):
    """Deduplicate by normalized URL first, then normalized title."""
    seen = {}
    url_index = {}
    title_index = {}

    for item in items:
        url_key = item.get("normalized_url")
        title_key = normalize_title(item.get("title"))
        key = url_index.get(url_key) or title_index.get(title_key)

        if not key:
            key = url_key or title_key
        if not key:
            continue

        previous = seen.get(key)
        if not previous:
            seen[key] = item
            if url_key:
                url_index[url_key] = key
            if title_key:
                title_index[title_key] = key
            continue

        if len(item.get("summary", "")) > len(previous.get("summary", "")):
            item["source"] = f"{previous['source']}, {item['source']}"
            item["importance_hint"] = max(previous["importance_hint"], item["importance_hint"])
            seen[key] = item
            if url_key:
                url_index[url_key] = key
            if title_key:
                title_index[title_key] = key
        else:
            previous["source"] = f"{previous['source']}, {item['source']}"
            previous["importance_hint"] = max(previous["importance_hint"], item["importance_hint"])

    return list(seen.values())


def classify_item(title, summary):
    """Classify an article into an elevator industry category based on content."""
    text = f"{title} {summary}".lower()
    if any(w in text for w in [
        "事故", "伤亡", "起火", "坠落", "困人", "夹人", "卷入",
        "故障", "停梯", "停运", "急速下降", "冲顶", "蹲底",
        "约谈", "通报批评", "罚款", "责改", "查封",
        "消防", "救援", "被困", "脱险",
    ]):
        return "accident"
    if any(w in text for w in [
        "标准", "法规", "规则", "规程", "规范", "通知", "意见",
        "tsg", "gb ", "gb/t", "iso ", "总局", "住建部",
        "市场监管局", "特种设备", "安全监察", "检验检测",
        "行政许可", "资质", "许可",
    ]):
        return "regulation"
    if any(w in text for w in [
        "加装", "加梯", "更新", "改造", "焕新", "换新",
        "老旧", "旧楼", "国债", "补贴", "惠民",
        "既有住宅", "民生", "爬楼",
    ]):
        return "renovation"
    if any(w in text for w in [
        "中标", "签约", "合作", "发布", "上市", "投产",
        "推介会", "展会", "博览会", "论坛",
        "战略", "布局", "出海", "出口",
    ]):
        return "business"
    # Default: general industry news
    return "news"


def fetch_rss_feed(feed_url, source_name, max_items=50, cutoff_days=3):
    """Generic RSS feed fetcher, classifies items into elevator categories."""
    items = []
    try:
        resp = requests.get(feed_url, timeout=20)
        resp.raise_for_status()
        # xindianti.cn returns non-standard RSS with id attributes on <item>
        # feedparser handles it fine
        resp.encoding = "utf-8"
        feed = feedparser.parse(resp.content)
        cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
        for entry in feed.entries:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                entry_date = datetime(*published[:6], tzinfo=timezone.utc)
                if entry_date < cutoff:
                    continue
                published_at = entry_date.isoformat()
            else:
                published_at = None

            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))

            # Skip "早新闻" daily roundup items (duplicates of individual articles)
            if "早新闻" in title:
                continue

            category = classify_item(title, summary)

            items.append(make_item(
                category=category,
                title=title,
                url=entry.get("link", ""),
                summary=summary,
                source=source_name,
                published=published_at,
                metadata={"feed_url": feed_url},
            ))
            if len(items) >= max_items:
                break
    except Exception as e:
        print(f"  [{source_name}] Error: {e}")
    return items


# ── RSS sources ─────────────────────────────────────────────────────────────

RSS_SOURCES = [
    ("https://www.xindianti.cn/feed/rss.php?mid=21", "新电梯网", 50, 7),
]


def fetch_all():
    """Fetch from all sources, return categorized data."""
    news = []
    for url, name, max_items, cutoff_days in RSS_SOURCES:
        feed_items = fetch_rss_feed(url, name, max_items=max_items, cutoff_days=cutoff_days)
        print(f"  [{name}] Got {len(feed_items)} items")
        news.extend(feed_items)

    deduped = dedupe_items(news)
    print(f"Deduped {len(news)} raw items to {len(deduped)} unique items")

    # Split into categories
    data = {
        "news": [],
        "accident": [],
        "regulation": [],
        "renovation": [],
        "business": [],
    }
    for item in deduped:
        cat = item.get("category", "news")
        if cat in data:
            data[cat].append(item)
        else:
            data["news"].append(item)

    for cat, items in data.items():
        if items:
            print(f"  {cat}: {len(items)} items")

    return data
