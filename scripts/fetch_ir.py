#!/usr/bin/env python3
"""
fetch_ir.py
───────────
대형주 IR 보도자료 RSS 피드를 긁어, catalyst 가능성이 높은 항목만
키워드(1단계 포함 키워드)로 필터해 data/ir_news.json 으로 저장합니다.

- RSS 표준 XML 파싱 (외부 라이브러리 없이 표준 라이브러리만)
- 키 불필요, GitHub Actions에서 매일 자동 — 크레딧 0
- 제목 + 본문 첫 문단(description) 둘 다에서 키워드 탐색

현재 RSS 확인된 곳: LLY. 나머지(NVO/GILD/MRK)는 RSS 확인되는 대로 FEEDS에 추가.
"""
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

# 티커 → IR 보도자료 RSS 피드 URL
FEEDS = {
    "LLY": "https://investor.lilly.com/rss/news-releases.xml",
}

# 1단계 포함 키워드. 긴 구절은 단순 포함, 짧은 약어는 단어 경계로 정확 매칭.
# (약물명 "Foundayo" 안의 "nda" 같은 오탐 방지)
KEYWORDS_SUBSTR = [   # 그대로 포함되면 매칭 (충분히 길어 오탐 위험 낮음)
    "topline", "top-line", "phase 3", "phase iii", "phase 2", "phase ii",
    "primary endpoint", "met the primary", "primary completion",
    "fda approval", "fda approves", "fda approved", "pdufa",
    "breakthrough therapy", "priority review",
    "submission", "interim results", "pivotal", "results from",
]
KEYWORDS_WORD = [     # 단어 경계(\b)로만 매칭 (짧은 약어 — 오탐 방지)
    "approved", "bla", "nda", "snda", "sbla",
]

LIMIT_PER_FEED = 40   # 피드당 최근 N건만 검사


def clean(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"<[^>]+>", "", text)          # 혹시 남은 태그 제거
    text = re.sub(r"\s+", " ", text).strip()
    return text


def matched_keywords(title: str, desc: str) -> list:
    blob = (title + " " + desc).lower()
    hits = []
    for kw in KEYWORDS_SUBSTR:
        if kw in blob:
            hits.append(kw)
    for kw in KEYWORDS_WORD:
        if re.search(r"\b" + re.escape(kw) + r"\b", blob):
            hits.append(kw)
    return hits


def fetch_feed(ticker: str, url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "CatalystDesk/1.0 (research dashboard)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    root = ET.fromstring(raw)

    out = []
    items = root.findall(".//item")[:LIMIT_PER_FEED]
    for it in items:
        title = clean(it.findtext("title", ""))
        link = (it.findtext("link", "") or "").strip()
        desc = clean(it.findtext("description", ""))
        pub = it.findtext("pubDate", "") or ""

        # 발행일 → YYYY-MM-DD
        date_str = ""
        try:
            dt = parsedate_to_datetime(pub)
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        hits = matched_keywords(title, desc)
        if not hits:
            continue   # 키워드 없으면 catalyst 후보 아님 → 스킵 (Shaq 캠페인 등 노이즈 제거)

        out.append({
            "ticker": ticker,
            "date": date_str,
            "title": title,
            "summary": desc[:300],
            "url": link,
            "keywords": hits,
        })
    return out


def main():
    all_news = []
    for ticker, url in FEEDS.items():
        try:
            news = fetch_feed(ticker, url)
            all_news.extend(news)
            print(f"[ok]   {ticker}: {len(news)} catalyst-relevant releases")
        except Exception as e:
            print(f"[error] {ticker}: {e}")

    all_news.sort(key=lambda n: n.get("date", ""), reverse=True)  # 최신순

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Company IR RSS feeds (keyword-filtered)",
        "news": all_news,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/ir_news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nsaved data/ir_news.json — {len(all_news)} releases, {len(FEEDS)} feeds")


if __name__ == "__main__":
    main()
