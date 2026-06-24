#!/usr/bin/env python3
"""
fetch_trials.py
───────────────
ClinicalTrials.gov v2 API에서 추적 종목의 진행 중 Phase 3 시험을 받아
data/trials.json 으로 저장합니다.

- 공식 API, 키·인증 불필요 (https://clinicaltrials.gov/api/v2/studies)
- primary completion date 의 ESTIMATED / ACTUAL 타입을 그대로 보존
- GitHub Actions(클라우드)에서 매일 자동 호출 — 크레딧 0

종목→스폰서명 매핑은 SPONSORS 에서 관리. 티커가 아니라 CT.gov에
등록된 정식 스폰서명으로 조회해야 정확히 잡힙니다.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://clinicaltrials.gov/api/v2/studies"

# 티커 → ClinicalTrials.gov 스폰서명 (정식 등록명 기준)
SPONSORS = {
    "UTHR": "United Therapeutics",
    "ACHV": "Achieve Life Sciences",
    "LLY": "Eli Lilly and Company",
    "NVO": "Novo Nordisk A/S",
    "GILD": "Gilead Sciences",
    "MRK": "Merck Sharp & Dohme LLC",
    "RVMD": "Revolution Medicines, Inc.",
    "ABBV": "AbbVie",
}

# 진행 중으로 간주할 상태 (topline 전 단계)
STATUSES = "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION|NOT_YET_RECRUITING"


def fetch_one(ticker: str, sponsor: str) -> list:
    params = urllib.parse.urlencode({
        "query.spons": sponsor,
        "filter.overallStatus": STATUSES.replace("|", ","),
        "filter.advanced": "AREA[Phase]PHASE3",
        "pageSize": 50,
        "fields": ",".join([
            "NCTId", "BriefTitle", "OverallStatus", "Phase",
            "PrimaryCompletionDate", "PrimaryCompletionDateType",
            "StartDate", "LeadSponsorName", "InterventionName", "Condition",
        ]),
        "sort": "PrimaryCompletionDate:asc",
    })
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "CatalystDesk/1.0 (research dashboard)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    out = []
    for s in data.get("studies", []):
        ps = s.get("protocolSection", {})
        idm = ps.get("identificationModule", {})
        stm = ps.get("statusModule", {})
        dm = ps.get("designModule", {})
        am = ps.get("armsInterventionsModule", {})
        cm = ps.get("conditionsModule", {})

        pcd = stm.get("primaryCompletionDateStruct", {})
        date_raw = pcd.get("date", "")            # "2026-09" 또는 "2026-09-30"
        date_type = pcd.get("type", "")           # "ESTIMATED" | "ACTUAL"

        # 약물명 (intervention 중 DRUG/BIOLOGICAL 우선)
        drugs = []
        for iv in am.get("interventions", []):
            if iv.get("type") in ("DRUG", "BIOLOGICAL"):
                drugs.append(iv.get("name", ""))
        drug_str = ", ".join(d for d in drugs[:2] if d)

        out.append({
            "ticker": ticker,
            "nct": idm.get("nctId", ""),
            "title": (idm.get("briefTitle", "") or "")[:120],
            "drug": drug_str,
            "phase": ",".join(dm.get("phases", [])),
            "status": stm.get("overallStatus", ""),
            "pcd": date_raw,
            "pcd_type": date_type,          # ESTIMATED / ACTUAL — 대시보드에서 배지로 구분
            "condition": ", ".join(cm.get("conditions", [])[:2]),
            "url": f"https://clinicaltrials.gov/study/{idm.get('nctId','')}",
        })
    return out


def main():
    all_trials = []
    for ticker, sponsor in SPONSORS.items():
        try:
            trials = fetch_one(ticker, sponsor)
            all_trials.extend(trials)
            print(f"[ok]   {ticker} ({sponsor}): {len(trials)} Phase 3 trials")
        except Exception as e:
            print(f"[error] {ticker}: {e}")
        time.sleep(1)  # API 예의상 간격

    all_trials.sort(key=lambda t: (t.get("pcd") or "9999", t.get("ticker", "")))

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "ClinicalTrials.gov API v2",
        "trials": all_trials,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/trials.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nsaved data/trials.json — {len(all_trials)} trials, {len(SPONSORS)} sponsors")


if __name__ == "__main__":
    main()
