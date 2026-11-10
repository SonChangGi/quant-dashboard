# 공통 디자인 지침 · v0.4.2

## 화면과 조작

- 결과를 먼저 보여준다. AI 특유의 과한 설명·반복·상투적인 제약과 한계 문구는 삭제한다.
- 제목·부제·도움말에서 같은 내용을 반복하지 않는다. 단위·기간·기준·합성 여부는 필요한 위치에 한 번 표시한다.
- 카드의 제목과 숫자는 같은 시작선과 안쪽 여백을 사용한다. 긴 이름은 줄바꿈하고 숫자·단위·결측 표시는 유지한다.
- 차트 값 확인·확대·이동은 직접 조작한다. 상시 모드 버튼과 사용법을 두지 않는다. 확대 후에만 전체 보기를 표시한다.
- 복원은 확대 범위만 되돌린다. 계열의 색·선택과 비교 기간은 보존한다.
- 비교의 기간·상단 선택·범례·요약·표는 같은 선택 집합을 사용한다. 한 계열은 항상 남기고, 같은 시작일의 양수 관측을100으로 환산한다.
- 구간 분석은 모드 선택 없이 차트를 직접 드래그한다. 드래그 중 변화량을 보여주고 놓으면 유지한다. 클릭·Escape로 해제하며, 확대·이동은 별도 모드 없이 함께 제공한다.
- 표는 검색과 데이터가 중심이다. 열·범위·밀도·CSV는 표 도구에서 사용한다. 필터를 적용한 경우 해제를 표시한다.
- 표의 셀 그래프는 전체 자료의 공통 척도를 사용한다. 필터·페이지 변경으로 축이나 순위 의미를 바꾸지 않는다.
- 값의 증가와 개선을 구분하고, %와%p·0과미제공·관측과예측을 구분한다.
- 원자료·정의·구현 JSON은 접어서 제공한다. 오류에는 문제와 해결 동작만 쓴다.
- 키보드 접근과 포커스를 유지한다. 모바일 주요 버튼은44px 이상으로 제공하고 페이지 세로 탐색을 보존한다.

## 리서치 → 공통 규칙 → 예제

각 사이트의 전체 기능이 아니라 아래에 명시한 장점과 기능을 채택한다. 독립 예제의 차트 렌더러는 ECharts이며 다른 사이트는 원칙과 패턴을 참고했다. 프로젝트 적용본은 데이터 계약과 의미색을 유지한다. 렌더러는 예제와 같은 가독성·직접 조작을 충족하는 방식으로 선택하며, 기존 SVG·Recharts의 유지 자체를 목표로 삼지 않는다.

| 주요 출처 | 채택한 장점·기능 | 현재 예제 |
|---|---|---|
| [Hallmark](https://www.usehallmark.com/themes/dusk/) | 주요 KPI와 비교 차트를 먼저 배치 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#overview) |
| [shadcn/ui](https://ui.shadcn.com/view/new-york-v4/dashboard-01) | 기간·범례·계열 선택이 요약과 표에 함께 반영 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#compose) |
| [Astryx](https://astryx.atmeta.com/sandbox/pages/example-cards/) | 강조색·밀도·모서리를 같은 엔진에서 변경 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#foundations) |
| [Carbon](https://carbondesignsystem.com/data-visualization/overview/) | 단위·증감 방향·빈 값·로딩·복구 상태 분리 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#foundations) |
| [TanStack Table](https://tanstack.com/table/latest/docs/guide/row-models) | 검색·범위·정렬·페이지·CSV가 같은 결과 사용 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#tables) |
| [AG Grid](https://www.ag-grid.com/javascript-data-grid/sparklines-overview/) | 공통 척도와 결측 구간을 유지하는 스파크라인 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#tables) |
| [Observable Plot / D3](https://observablehq.com/plot/features/facets) | 공통 축의 작은 다중 차트와 분포 패턴 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2&pattern=small-multiples#charts) |
| [Vega-Lite](https://vega.github.io/vega-lite/docs/errorband.html) | 예측 경계·중앙선·중첩된 구간을 분리 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2&pattern=fan#charts) |
| [Apache ECharts](https://echarts.apache.org/en/index.html) | 17종 SVG 차트·확대·이동·원자료 접근 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#charts) |
| [Lightweight Charts](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/HandleScaleOptions) | 모드 전환 없이 값 확인·확대·이동, 조건부 복원 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#compose) |
| [Base UI / Radix](https://base-ui.com/) | 필요한 상태에서만 도구 표시, 포커스 복귀 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#compose) |
| [Magic UI / React Bits / Motion](https://magicui.design/docs/components/bento-grid) | 크기가 다른 정보 영역, 지속적인 장식 애니메이션 제외 | [예제](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#overview) |

[적용 확인과 코드 위치](research/APPLIED.md) · [로컬 적용 현황](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#research)

## 배포본에 적용할 때

- 스타일 적용과 기능 적용을 구분한다. 검색·범례·기간·표·CSV를 실제로 조작해 동일한 선택 상태를 사용하는지 확인한다.
- 기간 변경 시 선택은 배열 위치가 아닌 날짜로 유지한다. 해당 날짜가 새 기간에 없으면 선택을 해제한다.
- 검색 결과에도 원래 순위·비중·축 척도를 유지한다. 없는 결과에서 초기화하고 입력으로 돌아갈 수 있어야 한다.
- 지원하지 않는 확대·이동은 안내하거나 지원한다고 기록하지 않는다. 차트 종류는 분석 질문에 필요한 경우에 추가한다.

[배포본 기준 조작 확인](RELEASE.md)

## 운영 반영

테마 변경 후 실제 계산된 배경·표면·강조색을 확인한다. 토큰 선언만으로 적용됐다고 판단하지 않는다. 긴 카드 이름과 범례 버튼은 데스크톱·모바일에서 함께 확인한다.

변경한 CSS·JS는 내용 해시로 캐시를 갱신한다. 배포 파일과 검증한 빌드의 일치, 공개 화면의 조작 결과를 확인한다. 로컬 탐색 코드·인증 대체 응답·관측 스냅샷은 운영 소스로 옮기지 않는다.

## 실제 화면 적용 기준 · 2026-11-10 보완

- 정보 순서는 제목·단위·간결한 의미색 범례 → 그래프 → 선택 날짜의 상세 값으로 정리한다. 큰 설정 영역이나 선택값 카드가 차트보다 먼저 화면을 차지하지 않게 한다.
- 연결된 패널은 같은 날짜의 실제 픽셀 X 좌표가 같아야 한다. 축 글자 폭에 따라 plot 영역이 달라지지 않도록 공통 좌우 여백을 확보하고, 날짜 눈금은 필요하면 마지막 패널에만 둔다.
- 공통 버튼 스타일은 계열 범례의 의미색을 덮지 않는다. 상태·상승/하락·주제·계열 색은 버튼 안에서도 유지하며, 선택 여부는 테두리·굵기·불투명도로 함께 구분한다.

- 차트는 첫 화면에서 전체 표시 기간과 축을 읽을 수 있게 맞춘다. 고정 폭 차트를 잘라서 가로 스크롤만 제공하는 방식은 모바일 대응 완료로 간주하지 않는다. 시계열의 상세 탐색은 차트 내부 확대·이동으로 처리한다.
- 차트 제목은 카드에 한 번만, 단위는 축 또는 값에 한 번만 표시한다. 범례와 툴팁은 카드 내부에 들어와야 한다. 끝값 라벨을 쓸 때는 공간을 확보하고, 좁은 화면에서는 겹치거나 자르는 대신 툴팁·요약으로 전달한다.
- 시계열은 기본 값 읽기·확대·이동, 확대 후에만 전체 보기, 범례 선택을 제공한다. 수치 비교의 기준·결측·관측/예측 경계·거래 마커는 표현 변경 중에도 유지한다.
- 변경 전에 화면별 보존 목록을 작성한다. 주제·상승/하락·상태·계열의 의미색, 계산·단위·원자료·검색·정렬·CSV·키보드·자동화 연결을 구분한다. 모든 글자를 공통 강조색으로 덮지 않는다.
- 로딩 순서는 테마/저장 설정 → 기본 레이아웃/자리 확보 → 필수 데이터와 핵심 결과 → 부가 시각화다. 데이터가 없을 때 0 또는 정상 상태를 잠깐 표시하지 않는다. 기존 정상 값이 있는 새로고침에서는 값을 보존한다.
- 표의 첫 식별 열, 수치 정렬과 단위, 긴 이름, 결측, 빈 검색 결과를 확인한다. 표는 필요한 경우 내부 가로 탐색을 허용하되 차트의 잘림을 같은 방식으로 정당화하지 않는다.
- 검증은 메인 화면 하나가 아니라 각 차트 유형·주요 탭·빈 상태·반복 조작을 포함한다. 데스크톱과 모바일에서 축·라벨·툴팁·선택 결과를 직접 확인하고, 계산 테스트와 화면 검증 결과를 구분한다.

### 차트 어댑터 회귀 검증

- 정책·레버리지·비용·기간 입력을 바꿀 때마다 그래프·표·체결 원장이 같은 조건과 범위를 사용하는지 확인한다. 선택한 기간의 끝값을 원자료 및 표의 값과 대조한다.
- 기존 렌더러와 새 키보드 핸들러가 한 입력을 중복 처리하지 않게 한다. 방향키 한 번에 관측일 하나만 이동하며, 툴팁·선택 날짜·상세 값이 함께 바뀌는지 연속 입력으로 확인한다.
- 진입·청산·교체 마커는 실제 체결 원장의 상태와 대조한다. 각 상태에 대응하는 색·기호를 유지하고, 렌더러 변경 전후에 거래 날짜와 마커가 일치하는지 확인한다.

## 공통 표면과 직접 조작 · 0.4.2

모든 프로젝트는 초기 HTML에서 [공통 shell.css](https://sonchanggi.github.io/quant-dashboard/shared/design/tokens/0.4.2/shell.css)를 참조한다. 앱 CSS 뒤에 로드하며, 기존 startup 계약이 있는 앱에서는 startup CSS 바로 앞에 둔다. 역할은 `data-quant-card`, `data-quant-card-grid`, `data-quant-section`, `data-quant-metrics`, `data-quant-table`로 연결한다. 프로젝트별 복사본은 공통 파일의 대체 원본으로 편집하지 않는다.

카드는 24px, 모바일 20px 안쪽 여백과 16px 모서리를 사용한다. 카드 간격은 20/16px, 섹션 간격은 32/24px이다. 카드 안에 카드를 겹쳐 감싸지 않는다. 표와 차트는 같은 표면에서 정렬하고, 차트 안쪽 여백은 축과 데이터 가독성에 필요한 만큼만 둔다.

[토스](https://toss.im/)의 명확한 제목·여백 위계와 [토스증권](https://www.tossinvest.com/)의 다크 화면에서 확인한 낮은 대비 구분선, 목록 중심 배치, 절제된 컨트롤을 반영한다. 청록은 선택·주요 행동에 사용하며 뉴스 주제색, 상승·하락, 차트 계열색은 각 의미를 보존한다. 과도한 설명·중복 사용법·장식용 강조선은 추가하지 않는다.

시계열 차트는 모드 선택 없이 드래그하는 동안 날짜·시작값·끝값·변화량을 표시한다. 양수 가격은 %, 수익률·확률 수준은 %p, 점수는 절대 차이를 사용한다. 시작값이 0 이하이면 절대 차이와 변화율 —를 표시한다. 결측을 보간해서 비교하지 않는다. 역방향 드래그는 시간순으로 정규화한다. 휠 확대·Alt 드래그 이동·두 손가락 확대/이동을 유지한다. 카테고리 차트는 구간 합계·범위 등 의미에 맞게 선택하며 수익률로 바꾸지 않는다.
