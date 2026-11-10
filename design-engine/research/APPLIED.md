# 리서치 적용 확인 · v0.4.3

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

### 2026-11-10 · 토스와 토스증권 실제 화면 검토
- https://toss.im/ : 큰 제목, 여백으로 나눈 섹션, 간결한 상단 탐색을 확인.
- https://www.tossinvest.com/ : 라이트 및 실제 다크 전환 화면에서 지수·목록·차트·관심 목록의 위계를 확인. 하나의 표면 내부 정렬, 얕은 구분선, 낮은 강조 밀도를 공통 카드 계약에 반영.
- 적용: 중앙 shell.css의 opt-in 카드/표 규격, 중첩 프레임 제거, 모바일 plot 폭 확보. 금융·주제 의미색 보존.
- 직접조작: 엔진 drag.js와 각 renderer 연결에서 모드 없는 범위 비교, 확대·이동 공존. 합성 Touch 이벤트 검증은 물리 기기의 멀티터치 확인과 구분한다.

## 0.4.3 금융 화면 검토

2026-11-10에 이전 조사 기록과 별도로 확인했다. 실화면, 제품 시연, 공식 조작 문서를 구분했다.

| 출처 | 확인한 화면·문서 | 코드에 반영한 내용 |
| --- | --- | --- |
| [토스](https://toss.im/) | 공개 웹의 제목과 섹션 간격 | 카드 안의 제목·메타·본문 시작선을 일치시킴 |
| [토스증권](https://www.tossinvest.com/) | 실제 라이트·다크 전환, 지수 카드·순위 표·관심 목록, 390px 폭 | 페이지·카드·상세값의 밝기 차이와 절제된 선, 상승·하락의 고유 색을 분리 |
| [토스 디자인 시스템](https://toss.tech/article/43385) | 공식 디자인 글 · 명도와 색상 역할을 분리 | 바탕·카드·툴팁의 밝기 단계와 의미색을 별도 토큰으로 관리 |
| [TradingView Advanced Charts](https://www.tradingview.com/charting-library-docs/latest/mobile_specifics/) | 공식 조작 문서 · 손가락 조작을 입력 의도별로 분리 | 가로 관측값 탐색·정지 후 비교·핀치·세로 스크롤을 독립 상태로 구현 |
| [Robinhood Legend](https://robinhood.com/newsroom/introducing-robinhood-legend-charts-on-mobile/) | 공식 모바일 제품 시연 · 금융 계열이 앞에 오는 낮은 강조 밀도 | 보조 격자와 계열을 분리하고 차트 제목 옆 설정 메뉴를 제거 |
| [Koyfin](https://www.koyfin.com/features/advanced-graphing/) | 공식 제품 화면 · 여러 축과 벤치마크 비교 | 연결 패널의 날짜 좌표 정렬과 계열 간 선 색·모양 분리 |
| [Stock Analysis](https://stockanalysis.com/stocks/aapl/) | 모바일 실화면 · 작은 화면에서 숫자와 추세 우선 | 모바일에서 차트 옆 제어판을 없애고 표·정확값을 그래프 아래에 배치 |
| [Yahoo Finance](https://finance.yahoo.com/quote/AAPL/chart/) | 데스크톱 실화면 · 통화·현재값·축의 분명한 레이아웃 | 통화·단위·기준일을 가격과 함께 표시하고 보조 데이터 접근을 분리 |

TradingView의 길게 누르기는 원본에서 크로스헤어를 활성화한다. 이 엔진은 사용자가 요청한 대로 길게 누르기를 구간 비교에 쓰고, 곧바로 가로로 움직이는 제스처를 관측값 탐색에 연결했다. 토스증권 390px에서는 관심 목록이 화면을 대부분 차지하므로 그 레이아웃은 채택하지 않았다.
