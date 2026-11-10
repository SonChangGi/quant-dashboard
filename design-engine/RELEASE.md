# Quant Design Engine v0.4.1

2026-11-10 운영 적용판. 기존 v0.4.0 API·데이터 계약을 유지한다.

- 비교: 범례·성과·낙폭·표의 선택 상태를 연결하고 최소 한 계열을 유지한다.
- 날짜: 기간이 바뀌어도 같은 관측일을 유지하며, 범위를 벗어나면 초기화한다.
- 표: 검색·정렬·CSV가 같은 결과를 사용한다. 원래 순위·비중은 유지한다.
- 조작: 직접 탐색을 우선하며 보조 도구는 접고 초기화는 필요한 상태에서만 표시한다.
- 화면: 의미별 색, 일관된 카드 여백, 모바일 44px 조작 영역, 키보드·포커스 복귀.

독립 예제는 ECharts 기반 17종 차트와 합성 데이터를 사용한다. 실제 프로젝트는 기존 SVG·Recharts 등과 데이터 계약을 보존하며 해당 화면에 필요한 기능을 적용한다.

[공통 지침](DESIGN-GUIDELINES.md) · [API](API.md) · [리서치 적용](research/APPLIED.md)

차트 접근성 이름에서 제목 중복을 제거하고 의미·키보드 탐색 정보는 유지했다.

[패키지 다운로드](quant-design-engine-0.4.1.tgz)

## 운영 화면의 적용 범위

| 화면 | 적용한 조작·표현 |
|---|---|
| [Hub](https://sonchanggi.github.io/quant-dashboard/) | 연결된 날짜 탐색, 접힌 차트 도구, 검색·정렬·CSV |
| [Factor](https://sonchanggi.github.io/factor/) | 범례·성과·낙폭·표 동기화, 확대·이동·조건부 복원 |
| [SOX](https://sonchanggi.github.io/sox/) | 긴 이름의 2행 카드, 점수 필터·검색·같은 결과 CSV |
| [ETF](https://sonchanggi.github.io/etf-tracking/) | 검색·정렬 순서와 CSV 일치, 원래 순위 유지 |
| [DRAM](https://sonchanggi.github.io/dram-price/) | 날짜·제품 탐색, 가격 정렬, 모바일 내부 가로 탐색 |
| [Fear](https://sonchanggi.github.io/fearNgreed/) | 직접 구간 측정, 검색 복구, 숫자 정렬·CSV |
| [Regime](https://sonchanggi.github.io/regime/) | 관측·예측 구분, 날짜·구간 선택, 확률 변화 %p |
| [투자일지](https://invest.changgi-son.chatgpt.site) | 기간 변경 시 관측일 유지, 표 검색·정렬·초기화 |
| [Alpha House](https://alpha-house.changgi-son.chatgpt.site) | 접힌 필터, 검색 결과·초기화, 실제 운영 상태 유지 |
| [News](https://sonchanggi.github.io/news/) | 기사·원문 보존, 검색 복구·집중 읽기·목록 복귀 |

프로젝트별 기존 렌더러와 수치 계산을 유지한다. 독립 가이드의 모든 차트 종류나 확대 기능이 모든 화면에 적용된 것은 아니다. 투자일지 로그인 이후 조작 검증은 명시적 예시 데이터로 수행했다.
