# Catalyst Desk · Live

미국 바이오파마 워치리스트의 **주가 차트 위에 catalyst를 오버레이**하고,
각 catalyst 발생 시점의 **실제 주가 반응(D+1 / D+5)을 자동 추적**하는 대시보드입니다.

- 주가 수집: GitHub Actions가 매일 미국 장 마감 후(KST 07:30) Twelve Data에서 일봉을 받아 `data/prices.json` 커밋
- 배포: Netlify가 커밋을 감지해 자동 재배포 (약가 모니터링 툴과 동일 패턴)
- catalyst 데이터: 브라우저 localStorage + Claude "Catalyst Desk" 아티팩트의 JSON 내보내기 파일 가져오기

---

## 설치 (1회, 약 15분)

### 1. Twelve Data 무료 API 키 발급
1. https://twelvedata.com 가입 → 대시보드에서 API Key 복사
2. 무료 티어: 800콜/일, 8콜/분 — 티커 30개 일일 수집에 충분 (스크립트가 호출 간격 8.5초 자동 준수)

### 2. GitHub 저장소 생성
1. 새 저장소 생성 (private 권장)
2. 이 폴더의 파일 전체를 업로드 (`.github` 폴더 포함 — 누락 주의!)
3. **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `TWELVE_DATA_API_KEY`
   - Secret: 발급받은 키

### 3. 첫 수집 실행
1. **Actions 탭 → "Fetch daily prices" → Run workflow** (수동 실행)
2. 약 2~3분 후 완료 → `data/prices.json` 이 커밋됐는지 확인
3. 이후 매 거래일 KST 07:30에 자동 실행됩니다

### 4. Netlify 연결
1. Netlify → **Add new site → Import an existing project** → GitHub 저장소 선택
2. Build command: 비워두기 / Publish directory: `/` (정적 사이트라 빌드 불필요)
3. Deploy → 발급된 URL로 접속

### 5. Catalyst 데이터 가져오기
1. Claude의 Catalyst Desk 아티팩트에서 **"JSON 내보내기"**
2. 배포된 대시보드에서 **"JSON 가져오기"** 로 해당 파일 업로드
3. 또는 대시보드에서 직접 추가

---

## 사용법

- **차트 마커**: 색 농도·크기 = 3단계 프레임워크 (Topline 진한 보라 > 학회 발표 > 논문 연보라, Regulatory는 청록)
- **마커 클릭**: 해당 catalyst의 D+1 / D+5 실제 주가 반응 표시 (직전 거래일 종가 대비)
- **점선 마커**: 예정된 catalyst 또는 월 단위(YYYY-MM) 날짜 — 차트 우측 보라 음영이 "예정 구간"
- **티커 추가/변경**: `data/tickers.json` 수정 후 커밋 → 다음 수집부터 반영

## 주의

- 무료 티어 특성상 데이터는 EOD(종가) 기준이며 지연이 있을 수 있습니다.
- catalyst 데이터는 브라우저 localStorage에 저장되므로, 기기를 바꾸면 JSON 가져오기로 옮기세요.
- D+1/D+5 반응은 단순 종가 비교입니다. 시장 전체 움직임(베타)은 보정하지 않으므로, 필요하면 XBI 대비 상대수익으로 해석하세요.
