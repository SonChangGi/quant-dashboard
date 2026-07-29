# Quant Dashboard

`https://sonchanggi.github.io/quant-dashboard/`용 통합 정적 리서치 허브입니다.

## 목적

- Fear & Greed Flow Lab, 모멘텀 팩터 랩, D램(DRAM) 가격 랩, Best Factor Lab, ETF TOP10 Tracking, SOX 반도체 지수 Cockpit, Port Portfolio Dashboard, Kelly Allocation Lab을 한 화면에서 연결합니다.
- 각 프로젝트 카드의 버튼으로 원본 GitHub Pages 페이지를 바로 엽니다. Port 카드는 포트폴리오 비중/ETF 기초 노출 도구로 이동합니다.
- 공개 배포 JSON만 best-effort로 읽되, 공통 `quant-research-summary` contract와 필수 key가 맞지 않으면 fallback/준비중 상태를 보여줍니다.
- 리서치 브리핑, 티커·테마 dossier, 데이터 상태/자동화 패널로 “오늘 무엇을 확인할지”와 “어떤 한계를 같이 읽어야 하는지”를 먼저 보여줍니다.

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
- `https://sonchanggi.github.io/dram-price/data/summary.json`
- `https://sonchanggi.github.io/dram-price/data/prices.json`
- `https://sonchanggi.github.io/dram-price/data/series.json`
- `https://sonchanggi.github.io/dram-price/data/status.json`
- `https://sonchanggi.github.io/best-factor/data/summary.json`
- `https://sonchanggi.github.io/etf-tracking/data/summary.json`
- `https://sonchanggi.github.io/etf-tracking/data/dashboard.json`
- `https://sonchanggi.github.io/sox/data/summary.json`
- `https://sonchanggi.github.io/port/data/summary.json`
- `https://sonchanggi.github.io/kelly/data/summary.json`

`summary.json`의 공통 필드는 `schemaVersion`, `contract`, `projectId`, `generatedAt`, `dataAsOf`, `status`, `coverage`, `primaryEntities`, `limitations`, `automation`입니다. 대형 원본 payload는 원본 프로젝트에 남겨두고 중앙 허브는 ticker/theme dossier와 health 상태에 필요한 작은 요약부터 사용합니다.

허브는 8개 프로젝트 링크와 8개 공개 요약 패널을 제공합니다. Port도 독립 `summary.json`의 가격/history/holdings 품질과 자동화 링크를 health 집계에 포함합니다. Kelly는 독립 Pages의 `summary.json` 하나만 읽되, 최댓값 하나가 아니라 자산별 최소·최대 기준일, fresh/stale/latest counts와 stable reason code를 표시합니다. Kelly의 `unavailable`은 계약 실패가 아니라 검증된 시장 시계열이 아직 공개되지 않은 정상 상태일 수 있으므로, 네트워크 fallback과 구분해 표시합니다.

각 패널에는 upstream 계약이 `expectedFreshnessDays`를 생략해도 적용되는 프로젝트별 보수적 freshness 기본값이 있습니다. `.github/workflows/public-data-health.yml`은 마지막 예약 재시도 이후와 Platform Foundation 성공 후 `npm run test:live`를 실행합니다. Upstream `degraded`/`stale` 상태와 Kelly reason code는 운영 경고로 기록합니다. HTTP 429/5xx·timeout 같은 단일 프로젝트 전송 장애만 `transient`로 허용하며, 동시에 2개 이상 프로젝트를 관측할 수 없으면 hard observability failure로 승격합니다. 404/JSON·schema 계약 오류와 freshness 초과도 hard failure입니다. 전체 bounded JSON 보고서는 14일간 Actions artifact로 보존됩니다.

공개 JSON 구조가 바뀌거나 네트워크가 실패하면 대시보드는 마지막 확인 스냅샷 또는 오류 상태를 보여주고, 원본 페이지 링크는 계속 유지합니다. 중앙 허브의 숫자는 투자 결론이 아니라 원본 프로젝트의 방법론, 가격 기준일, 데이터 품질, 한계를 확인하기 위한 출발점입니다.

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
- Fear & Greed / Momentum / D램(DRAM) / Best Factor / ETF Tracking / SOX / Port / Kelly parser와 fallback 존재
- freshness/status 표시 hook 존재
- Research Cockpit, 티커·테마 Dossier, Data Health/automation hook 존재
- 선택형 live contract smoke로 공개 JSON row 수, schema/contract version, 최신성, payload 크기 확인
- 투자 조언이 아니라는 disclaimer 존재
- sibling 프로젝트 로컬 경로를 참조하지 않음

## 주의

본 페이지는 개인 리서치와 프로젝트 허브를 위한 화면이며 투자, 세무, 법률 또는 매매 조언이 아닙니다.
