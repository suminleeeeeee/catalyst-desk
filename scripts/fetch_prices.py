#!/usr/bin/env python3
"""
Toss증권 Open API에서 추적 티커들의 일봉(EOD) 데이터를 받아
data/prices.json 으로 저장합니다. (이전 Twelve Data 대체)

- 인증: OAuth2 Client Credentials → access token 발급 후 Bearer 호출
- /api/v1/candles 는 1회 최대 200봉 → before 커서로 페이지네이션해 ~1년치 확보
- 미국 종목은 일반 티커(symbol=LLY)로 그대로 조회. 토스 미커버 종목은 [skip].
- 출력 형식은 이전과 동일: {"updated", "series": {SYM: [{"d","c"}, ...]}}  (대시보드 무수정)
- 실행: TOSS_CLIENT_ID=... TOSS_CLIENT_SECRET=... python scripts/fetch_prices.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://openapi.tossinvest.com"
TOKEN_URL = f"{BASE}/oauth2/token"
CANDLE_URL = f"{BASE}/api/v1/candles"

TARGET_DAYS = 365      # 확보 목표 봉 수 (대략 최근 1년)
PAGE = 200             # candles 1회 최대 (API 상한)
MAX_PAGES = 3          # 200*3=600봉이면 1년치 충분

CLIENT_ID = os.environ.get("TOSS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TOSS_CLIENT_SECRET")
if not (CLIENT_ID and CLIENT_SECRET):
    sys.exit("환경변수 TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 가 설정되지 않았습니다.")


def get_token() -> str:
    """OAuth2 client_credentials 로 access token 발급 (x-www-form-urlencoded)."""
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        print(f"[token] HTTP {e.code} {e.reason} — 응답본문: {detail}")
        raise
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"토큰 발급 실패: {data}")
    return token


def fetch_candles(token: str, symbol: str) -> list:
    """일봉을 ~TARGET_DAYS 개 모을 때까지 before 커서로 페이지네이션."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "CatalystDesk/1.0 (research dashboard)",
    }
    rows = {}            # date(YYYY-MM-DD) -> close  (중복 제거)
    before = None
    for _ in range(MAX_PAGES):
        params = {"symbol": symbol, "interval": "1d", "count": PAGE, "adjusted": "true"}
        if before:
            params["before"] = before     # exclusive, ISO 8601 — 이 시각 이전 봉만
        req = urllib.request.Request(f"{CANDLE_URL}?{urllib.parse.urlencode(params)}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        result = data.get("result", data)         # 응답 래퍼: result.candles / result.nextBefore
        candles = result.get("candles", []) or []
        if not candles:
            break
        for c in candles:
            ts = (c.get("timestamp") or "")[:10]  # "2026-03-25T09:00:00+09:00" -> "2026-03-25"
            cp = c.get("closePrice")
            if ts and cp is not None:
                rows[ts] = round(float(cp), 2)
        before = result.get("nextBefore")
        if not before or len(rows) >= TARGET_DAYS:
            break
        time.sleep(0.2)
    series = [{"d": d, "c": rows[d]} for d in sorted(rows)]   # 과거→최신 정렬
    return series[-TARGET_DAYS:]


def main():
    with open("data/tickers.json", encoding="utf-8") as f:
        tickers = json.load(f)

    token = get_token()
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Toss Securities Open API",
        "series": {},
    }

    ok = 0
    for sym in tickers:
        try:
            series = fetch_candles(token, sym)
            if series:
                out["series"][sym] = series
                ok += 1
                print(f"[ok]   {sym}: {len(series)} days")
            else:
                print(f"[skip] {sym}: no candles (토스 미커버 가능성)")
        except urllib.error.HTTPError as e:
            print(f"[error] {sym}: HTTP {e.code} {e.reason}")
        except Exception as e:
            print(f"[error] {sym}: {e}")
        time.sleep(0.2)   # 시세 API 분당 수백 콜 — 가벼운 간격이면 충분

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"\nsaved data/prices.json ({ok}/{len(tickers)} tickers)")


if __name__ == "__main__":
    main()
