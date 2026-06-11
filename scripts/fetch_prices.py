#!/usr/bin/env python3
"""
Twelve Data API에서 추적 티커들의 일봉(EOD) 데이터를 받아
data/prices.json 으로 저장합니다.

- 무료 티어: 800 크레딧/일, 8 크레딧/분 → 티커 간 8.5초 간격으로 호출
- 실행: TWELVE_DATA_API_KEY=발급키 python scripts/fetch_prices.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.twelvedata.com/time_series"
OUTPUT_SIZE = "365"  # 최근 1년 일봉

KEY = os.environ.get("TWELVE_DATA_API_KEY")
if not KEY:
    sys.exit("환경변수 TWELVE_DATA_API_KEY 가 설정되지 않았습니다.")

with open("data/tickers.json", encoding="utf-8") as f:
    tickers = json.load(f)

out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": {}}

for i, sym in enumerate(tickers):
    params = urllib.parse.urlencode(
        {"symbol": sym, "interval": "1day", "outputsize": OUTPUT_SIZE, "apikey": KEY}
    )
    try:
        with urllib.request.urlopen(f"{API}?{params}", timeout=30) as r:
            data = json.loads(r.read())
        if data.get("status") != "ok" or "values" not in data:
            print(f"[skip] {sym}: {data.get('message', 'unknown error')}")
        else:
            vals = list(reversed(data["values"]))  # 응답은 최신순 → 과거순으로 뒤집기
            out["series"][sym] = [
                {"d": v["datetime"], "c": round(float(v["close"]), 2)} for v in vals
            ]
            print(f"[ok]   {sym}: {len(vals)} days")
    except Exception as e:
        print(f"[error] {sym}: {e}")

    if i < len(tickers) - 1:
        time.sleep(8.5)  # 무료 티어 분당 호출 제한 준수

os.makedirs("data", exist_ok=True)
with open("data/prices.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)

print(f"\nsaved data/prices.json ({len(out['series'])}/{len(tickers)} tickers)")
