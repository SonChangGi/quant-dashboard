# 리서치 적용 확인 · v0.4.1

2026-11-10. 기존 조사 기록을 현재 코드와 예제에 대조했다.

| 출처 | 적용한 기능 | 코드 | 구분 |
|---|---|---|---|
| Hallmark | 주요 KPI와 비교 차트를 먼저 배치 | `demo/app.js: overview` | 원칙 적용 |
| shadcn/ui | 기간·범례·계열 선택이 요약과 표에 함께 반영 | `demo/app.js: composition` | 원칙 적용 |
| Astryx | 강조색·밀도·모서리를 같은 엔진에서 변경 | `engine/tokens.js` | 원칙 적용 |
| Carbon | 단위·증감 방향·빈 값·로딩·복구 상태 분리 | `engine/metrics.js, engine/index.js` | 원칙 적용 |
| TanStack Table | 검색·범위·정렬·페이지·CSV가 같은 결과 사용 | `engine/table.js` | 원칙 적용 |
| AG Grid | 공통 척도와 결측 구간을 유지하는 스파크라인 | `engine/table.js: columnExtent / sparkline` | 원칙 적용 |
| Observable Plot / D3 | 공통 축의 작은 다중 차트와 분포 패턴 | `engine/charts.js: small-multiples, histogram` | 원칙 적용 |
| Vega-Lite | 예측 경계·중앙선·중첩된 구간을 분리 | `engine/charts.js: fan` | 원칙 적용 |
| Apache ECharts | 17종 SVG 차트·확대·이동·원자료 접근 | `engine/charts.js, vendor/echarts.min.js` | 엔진 사용 |
| Lightweight Charts | 모드 전환 없이 값 확인·확대·이동, 조건부 복원 | `engine/charts.js: mountChart` | 원칙 적용 |
| Base UI / Radix | 필요한 상태에서만 도구 표시, 포커스 복귀 | `engine/index.js, engine/table.js` | 원칙 적용 |
| Magic UI / React Bits / Motion | 크기가 다른 정보 영역, 지속적인 장식 애니메이션 제외 | `demo/demo.css` | 선택 채택 |

## 이번에 보완한 누락

- 리서치 목록에서 실제 예제로 연결되는 경로를 추가했다. 차트 링크는 해당 패턴만 표시한다.
- 범례와 상단 체크박스, 요약 카드, 표를 동기화했다. 계열 선택을 바꿔도 차트를 재생성하지 않아 확대·고정한 관측·계열 색을 유지한다.
- SOX/MU/LSCC의 긴 제목과 결측값 카드 예제를 추가했다.
- 이전 버전의 모드 버튼·렌더러 선택 제안과 충돌하는 지침을 통합했다.

## 선택 범위

AG Grid/TanStack/Plot/Vega 등을 새 런타임으로 설치한 것은 아니다. 비교 가능한 스파크라인·일관된 행 모델·공통 축·불확실성 표현을 자체 엔진에 반영했다. Hallmark의 결제 흐름, Astryx의 React/StyleX 스택, 장식 애니메이션과 대규모 GPU 렌더러는 채택하지 않았다.

조사 원자료: `github-20261110.json`, `prior-32.json`, `expanded.json`, `github-raw/`. 과거 소스 조회 시점의 기록이며 현재 인기도를 다시 측정한 자료는 아니다. UI 직접 관찰은 `UI-RESEARCH.md`, 최신 검증은 `../QA.md`를 따른다.

## 실제 프로젝트 적용 검증

위 표는 독립 가이드의 구현이다. 배포본 기준 프로젝트별 기능 적용과 Aside 조작 증거는 [조작 검토](../RELEASE.md)에 별도로 기록한다.

## 운영 화면 재정렬 · 2026-11-10

독립 예제에 머물던 축·직접 탐색·상태 표현을 운영 화면에 연결했다. Hub·SOX·ETF·Fear·DRAM·Regime의 차트는 반응형 구현으로 교체하고, Factor·투자일지는 기존 데이터와 관측일 연결을 보존하면서 직접 탐색을 보강했다. Carbon의 상태 구분은 로딩 공간과 실제 0의 구분에, TanStack/AG Grid의 원칙은 정렬·선택·내보내기 일치에 반영했다. 주제색·종목색·국면색은 공통 청록색으로 덮지 않는다. 화면별 적용 내용은 RELEASE.md를 따른다.
