# Quant Dashboard

`https://sonchanggi.github.io/quant-dashboard/`용 통합 정적 리서치 허브입니다.

## 목적

- Fear & Greed Flow Lab, 모멘텀 팩터 랩, D램(DRAM) 가격 랩, Best Factor Lab, ETF TOP10 Tracking, SOX 반도체 지수 Cockpit, US Market Regime Lab을 한 화면에서 연결합니다.
- 각 프로젝트 카드의 버튼으로 원본 GitHub Pages 페이지를 바로 엽니다.
- 공개 배포 JSON만 best-effort로 읽되, 공통 `quant-research-summary` contract와 필수 key가 맞지 않으면 fallback/준비중 상태를 보여줍니다.
- 뉴스, 프로젝트별 결과, 티커·테마 검색으로 주요 내용을 확인합니다.

## 허브 화면 구성

- News 최신 브리핑을 가장 먼저 표시하고 7개 데이터 프로젝트 요약을 이어 보여줍니다. News는 공개 발행 목록과 해당 JSON의 SHA-256을 대조한 뒤 발행일·이슈 수·원본 선정 주요 이슈 4개를 표시합니다. 긴 요약은 세 줄까지 표시하며 제목을 누르면 원문 브리핑으로 이동합니다.
- Fear & Greed는 공개 `dashboard.json`의 직전 252거래일 raw 산점도와 현재 관측점, OLS 회귀선, 잔차 구간을 표시합니다. 가로축은 KOSPI 1일 수익률(%), 세로축은 개인 순매수대금(조원)입니다. 아래 KOSPI 종가는 같은 발행의 `history.json`에서 날짜를 대조합니다. 두 그래프의 공포·탐욕은 현재 raw 회귀 잔차 구간으로 통일하며, 당시 거래 신호와 구분해 `현재 회귀 기준`으로 표시합니다. 마우스·터치·방향키로 같은 날짜를 함께 선택하고 클릭으로 고정합니다. Escape는 현재 날짜로 돌아갑니다. 가격 데이터 오류는 산점도와 분리합니다.
- Regime는 관측 소속도와 1주 예측확률을 두 그래프로 표시합니다. 기본 52주이며 26주·104주·전체 기간을 선택할 수 있습니다. 국면 배경과 실제 t+1 마커는 원본 관측 국면을 사용하고, 이력 JSON은 core의 SHA-256·발행 ID를 대조합니다.
- Momentum과 Best Factor는 같은 2×2 지표 배치와 표 시작 높이를 사용합니다.
- 시장 상태, 팩터 전략, 반도체, ETF 순으로 결과를 묶고 상단 링크로 이동합니다. 티커·테마 검색은 공개 요약 안에서 수행합니다.
- 본문에는 결과·기준일·상태를 표시하고 출처와 운영 정보는 맨 아래 닫힌 상세에 모읍니다. 반복 설명과 서술형 제약 문구는 표시하지 않습니다. 계산·수집·공개 데이터 계약은 유지합니다.

## 공통 웹 디자인 프롬프트

앞으로의 기존 페이지 개선과 신규 프로젝트는 [Quant Research Web Design Prompt](docs/web-design.md)를 최우선 디자인 계약으로 사용합니다. 이 문서는 현재 구현된 DRAM, Fear & Greed, ETF Tracking, SOX, Momentum Factor, Best Factor의 실제 디자인을 참조 스위트로 고정하고, 상위 메뉴·색상·타이포그래피·간격·컴포넌트·표·차트·접근성·검증 절차를 함께 정의합니다.

[공통 디자인 v1.2](docs/common-design-v1.md)와 [v1.2 프로젝트 적용 프롬프트](docs/common-design-v1-rollout-prompt.md)는 파일럿에서 확립한 정보 구조·차트 상태·보호 경계의 근거 문서로 유지합니다. 충돌할 경우 `docs/web-design.md`를 우선합니다.

- 프레임워크가 아니라 사용자 계약을 공유합니다.
- 여섯 기준 프로젝트의 공통 디자인 문법을 사용하되 어느 한 페이지를 통째로 복제하지 않습니다.
- 메뉴·색상 역할·정보 위계·밀도·상호작용은 맞추고 프로젝트별 차트·표·결과 구조는 유지합니다.
- 각 프로젝트의 데이터·계산·배포 경계는 유지합니다.
- 나머지 프로젝트는 한 번에 바꾸지 않고 프로젝트별 plan-goal로 적용합니다.

백엔드·프런트엔드 분리와 단계적 이전은 [Platform Architecture v1](docs/platform-architecture-v1.md)을 따릅니다. 실제 공통 package·신규 프로젝트 template·도입 방법은 [frontend foundation](platform/README.md)에, 현재 입력 경로의 읽기 전용 근거는 [6개 대시보드 control 감사](docs/control-audit-2026-07-24.md)에 기록했습니다.

## 데이터 경계

이 저장소는 다른 프로젝트의 로컬 소스 코드를 직접 import하지 않습니다. 런타임에서는 각 프로젝트의 작은 `summary.json`을 먼저 읽고, 필요한 경우에만 작은 detail JSON을 보조로 읽습니다.

`index.html`의 `quant-supabase-url`과 `quant-supabase-publishable-key`가 명시적으로 설정된 환경에서는 공개 RLS view의 게시 metadata를 함께 조회합니다. 두 값은 기본적으로 비어 있으며, 설정되지 않았거나 조회가 실패하면 기존 Pages `summary.json` 경로만 사용합니다. Metadata의 기준일과 실제 표시한 summary 기준일이 다르면 어느 한쪽을 새 결과로 간주하지 않고 불일치 상태로 닫힙니다. 브라우저에는 publishable key만 허용하며 service-role key는 사용하지 않습니다.

- `https://sonchanggi.github.io/momentum-factor-lab/data/summary.json`
- `https://sonchanggi.github.io/fearNgreed/data/summary.json`
- `https://sonchanggi.github.io/fearNgreed/data/dashboard.json`
- `https://sonchanggi.github.io/dram-price/data/summary.json`
- `https://sonchanggi.github.io/dram-price/data/prices.json`
- `https://sonchanggi.github.io/dram-price/data/series.json`
- `https://sonchanggi.github.io/dram-price/data/status.json`
- `https://sonchanggi.github.io/best-factor/data/summary.json`
- `https://sonchanggi.github.io/etf-tracking/data/summary.json`
- `https://sonchanggi.github.io/etf-tracking/data/dashboard.json`
- `https://sonchanggi.github.io/sox/data/summary.json`
- `https://sonchanggi.github.io/regime/data/regime-core.json` (v5 핵심 결과; 현재 국면 소속도·다음 주 예측 확률·이탈 확률)

`summary.json`의 공통 필드는 `schemaVersion`, `contract`, `projectId`, `generatedAt`, `dataAsOf`, `status`, `coverage`, `primaryEntities`, `limitations`, `automation`입니다. 대형 원본 payload는 원본 프로젝트에 남겨두고 중앙 허브는 ticker/theme dossier와 health 상태에 필요한 작은 요약부터 사용합니다.

허브는 8개 프로젝트 링크와 7개 데이터 패널, News 브리핑을 제공합니다. Regime 상태도 health 집계에 포함합니다. Regime 어댑터는 합성 데모 계약 또는 개인·비상업 live-derived 계약(`alpha_vantage/private_noncommercial`, `alfred/user_confirmed_ml_storage_derived`)을 정확히 만족할 때만 값을 표시합니다.

각 패널에는 upstream 계약이 `expectedFreshnessDays`를 생략해도 적용되는 프로젝트별 보수적 freshness 기본값이 있습니다. `.github/workflows/public-data-health.yml`은 마지막 예약 재시도 이후와 Platform Foundation 성공 후 `npm run test:live`를 실행합니다. Upstream `degraded`/`stale`와 freshness 초과는 보고서·Actions summary·artifact에 계속 기록하지만, 공개 페이지가 읽을 수 있는 계약을 유지하는 동안에는 실패 메일을 만들지 않습니다. 404·잘못된 JSON·schema 계약 오류와 동시에 2개 이상 프로젝트를 관측할 수 없는 broad observability 장애처럼 실제 화면을 깨뜨리는 문제만 실패 gate 대상입니다. 마지막 일일 예약은 web-breaking incident의 숫자·날짜 변화를 정규화한 fingerprint를 30일간 보존해 새 장애나 장애 유형 변경 때만 다시 실패합니다. 전체 bounded JSON 보고서는 14일간 Actions artifact로 보존됩니다.

정적 Hub는 `.github/workflows/pages.yml`이 Platform Foundation을 통과한 정확한 `main` revision에서 `index.html`과 `assets/`만 allowlist artifact로 만들고, 배포 직전 원격 SHA를 다시 확인한 뒤 공개 핵심 파일을 byte-for-byte 검증합니다. 저장소의 Pages source는 이 workflow를 반영할 때 `GitHub Actions`로 한 번 전환해야 하며, 기존 branch/Jekyll 배포를 동시에 유지하지 않습니다.

공개 JSON 구조가 바뀌거나 네트워크가 실패하면 대시보드는 마지막 확인 스냅샷 또는 오류 상태를 보여주고, 원본 페이지 링크는 계속 유지합니다.

## 로컬 실행

정적 파일이므로 별도 빌드가 필요 없습니다.

```bash
python3 -m http.server 8080
# http://localhost:8080 열기
```

## 검증

```bash
npm test
npm run test:live  # 공개 GitHub Pages JSON 계약을 네트워크로 확인할 때만 실행
```

검증은 Node 내장 기능만 사용하며 다음을 확인합니다.

- 모든 프로젝트 원본 링크 존재
- 모든 활성 프로젝트 링크와 `summary.json` endpoint 존재
- 공개 summary/detail endpoint 상수 존재
- Fear & Greed / Momentum / D램(DRAM) / Best Factor / ETF Tracking / SOX / Regime parser와 fallback 존재
- freshness/status 표시 hook 존재
- Research Cockpit, 티커·테마 Dossier, Data Health/automation hook 존재
- 선택형 live contract smoke로 공개 JSON row 수, schema/contract version, 최신성, payload 크기 확인
- News 우선 배치, 산점도 단위·발행 일치·음수 축·오류 격리
- sibling 프로젝트 로컬 경로를 참조하지 않음
