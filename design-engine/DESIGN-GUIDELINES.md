# 공통 디자인 지침 · v0.4.1

## 화면과 조작

- 결과를 먼저 보여준다. AI 특유의 과한 설명·반복·상투적인 제약과 한계 문구는 삭제한다.
- 제목·부제·도움말에서 같은 내용을 반복하지 않는다. 단위·기간·기준·합성 여부는 필요한 위치에 한 번 표시한다.
- 카드의 제목과 숫자는 같은 시작선과 안쪽 여백을 사용한다. 긴 이름은 줄바꿈하고 숫자·단위·결측 표시는 유지한다.
- 차트 값 확인·확대·이동은 직접 조작한다. 상시 모드 버튼과 사용법을 두지 않는다. 확대 후에만 전체 보기를 표시한다.
- 복원은 확대 범위만 되돌린다. 계열의 색·선택과 비교 기간은 보존한다.
- 비교의 기간·상단 선택·범례·요약·표는 같은 선택 집합을 사용한다. 한 계열은 항상 남기고, 같은 시작일의 양수 관측을100으로 환산한다.
- 구간 분석은 필요할 때 옵션에서 연다. 선택 중 완료, 선택 후 해제 동작을 표시한다.
- 표는 검색과 데이터가 중심이다. 열·범위·밀도·CSV는 표 도구에서 사용한다. 필터를 적용한 경우 해제를 표시한다.
- 표의 셀 그래프는 전체 자료의 공통 척도를 사용한다. 필터·페이지 변경으로 축이나 순위 의미를 바꾸지 않는다.
- 값의 증가와 개선을 구분하고, %와%p·0과미제공·관측과예측을 구분한다.
- 원자료·정의·구현 JSON은 접어서 제공한다. 오류에는 문제와 해결 동작만 쓴다.
- 키보드 접근과 포커스를 유지한다. 모바일 주요 버튼은44px 이상으로 제공하고 페이지 세로 탐색을 보존한다.

## 리서치 → 공통 규칙 → 예제

각 사이트의 전체 기능이 아니라 아래에 명시한 장점과 기능을 채택한다. 독립 예제의 차트 렌더러는 ECharts이며 다른 사이트는 원칙과 패턴을 참고했다. 프로젝트 적용본은 기존 SVG·Recharts 등과 데이터 계약을 유지한다.

| 주요 출처 | 채택한 장점·기능 | 현재 예제 |
|---|---|---|
| [Hallmark](https://www.usehallmark.com/themes/dusk/) | 주요 KPI와 비교 차트를 먼저 배치 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#overview) |
| [shadcn/ui](https://ui.shadcn.com/view/new-york-v4/dashboard-01) | 기간·범례·계열 선택이 요약과 표에 함께 반영 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#compose) |
| [Astryx](https://astryx.atmeta.com/sandbox/pages/example-cards/) | 강조색·밀도·모서리를 같은 엔진에서 변경 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#foundations) |
| [Carbon](https://carbondesignsystem.com/data-visualization/overview/) | 단위·증감 방향·빈 값·로딩·복구 상태 분리 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#foundations) |
| [TanStack Table](https://tanstack.com/table/latest/docs/guide/row-models) | 검색·범위·정렬·페이지·CSV가 같은 결과 사용 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#tables) |
| [AG Grid](https://www.ag-grid.com/javascript-data-grid/sparklines-overview/) | 공통 척도와 결측 구간을 유지하는 스파크라인 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#tables) |
| [Observable Plot / D3](https://observablehq.com/plot/features/facets) | 공통 축의 작은 다중 차트와 분포 패턴 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1&pattern=small-multiples#charts) |
| [Vega-Lite](https://vega.github.io/vega-lite/docs/errorband.html) | 예측 경계·중앙선·중첩된 구간을 분리 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1&pattern=fan#charts) |
| [Apache ECharts](https://echarts.apache.org/en/index.html) | 17종 SVG 차트·확대·이동·원자료 접근 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#charts) |
| [Lightweight Charts](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/HandleScaleOptions) | 모드 전환 없이 값 확인·확대·이동, 조건부 복원 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#compose) |
| [Base UI / Radix](https://base-ui.com/) | 필요한 상태에서만 도구 표시, 포커스 복귀 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#compose) |
| [Magic UI / React Bits / Motion](https://magicui.design/docs/components/bento-grid) | 크기가 다른 정보 영역, 지속적인 장식 애니메이션 제외 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#overview) |

[적용 확인과 코드 위치](research/APPLIED.md) · [로컬 적용 현황](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.1#research)

## 배포본에 적용할 때

- 스타일 적용과 기능 적용을 구분한다. 검색·범례·기간·표·CSV를 실제로 조작해 동일한 선택 상태를 사용하는지 확인한다.
- 기간 변경 시 선택은 배열 위치가 아닌 날짜로 유지한다. 해당 날짜가 새 기간에 없으면 선택을 해제한다.
- 검색 결과에도 원래 순위·비중·축 척도를 유지한다. 없는 결과에서 초기화하고 입력으로 돌아갈 수 있어야 한다.
- 지원하지 않는 확대·이동은 안내하거나 지원한다고 기록하지 않는다. 차트 종류는 분석 질문에 필요한 경우에 추가한다.

[배포본 기준 조작 확인](RELEASE.md)
