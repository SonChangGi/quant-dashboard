# Quant Design Engine v0.4.3

2026-11-10 터치 탐색·길게 누른 구간 비교, 다층 금융 다크 테마. v0.4.0 API·데이터 계약은 유지한다.

공통 기준은 라이브러리 이름이 아니라 실제 화면의 가독성과 조작이다. 추세는 화면 전체 기간이 먼저 보이고, 값 확인·확대·이동은 차트 안에서 한다. 보조 조작은 접고 복원은 필요한 때만 표시한다. 원자료·계산·계열의 의미색은 보존한다.

- 차트: 터치는 관측값 탐색과 길게 누른 구간 비교를 분리한다. 휠·핀치로 확대하고 Alt·두 손가락으로 이동한다. 가격 %, 수익률·확률 %p, 결측·0 기준 구분.
- 표: 검색·정렬·CSV의 결과 일치, 숫자 정렬과 단위, 필요한 내부 스크롤.
- 카드: 중앙 shell.css 실제 참조, 24/20px 여백·16px 모서리, 중첩 프레임 축소. 의미색 유지.
- 로딩: 테마·설정을 먼저 적용하고 공간을 예약한 뒤 핵심 데이터, 부가 정보를 표시한다.

독립 예제는 ECharts 17종과 합성 데이터를 사용한다. 운영 화면은 데이터 계약을 유지하면서 적합한 렌더러를 선택한다.

[공통 지침](DESIGN-GUIDELINES.md) · [API](API.md) · [리서치 적용](research/APPLIED.md) · [패키지](quant-design-engine-0.4.3.tgz)

## 운영 화면 적용

| 화면 | 구현 내용 |
|---|---|
| [Hub](https://sonchanggi.github.io/quant-dashboard/) | 6계열·9차트 ECharts, 실제 데이터·축·범위·연결된 날짜 탐색 |
| [Factor](https://sonchanggi.github.io/factor/) | 직접 확대·이동·조건부 복원, SPY·범례·성과·낙폭·표 동기화 |
| [SOX](https://sonchanggi.github.io/sox/) | ECharts 막대·산점도, 구간 합계·영역 선택·표 연결, 모바일 순위 카드 |
| [ETF](https://sonchanggi.github.io/etf-tracking/) | 반응형 ECharts 추세, 이벤트·계열색·결측 보존, 구간 분석 |
| [DRAM](https://sonchanggi.github.io/dram-price/) | 반응형 추세·확대·복원, 날짜·제품·가격 단위와 표 동기화 |
| [Fear](https://sonchanggi.github.io/fearNgreed/) | 6개 차트 계열 재구현, 공통 시간축·신뢰구간·잔차·성과 표현 |
| [Regime](https://sonchanggi.github.io/regime/) | 반응형 확률 패널·관측 국면·실제 결과, 원래 국면색 유지 |
| [투자일지](https://invest.changgi-son.chatgpt.site) | 직접 확대·이동·관측일 선택, 접힌 보조 도구, 로딩 공간·표·카드 개선 |
| [Alpha House](https://alpha-house.changgi-son.chatgpt.site) | 모바일 2열 지표·목록, 운영 상태·층·공간색 보존, 초기 로딩 구분 |
| [News](https://sonchanggi.github.io/news/) | 8주제 색·기사·원문 보존, 카드·메타데이터·표·검색 밀도와 로딩 개선 |

투자일지의 로그인 이후 화면은 명시적 체험 데이터로 확인한다. 개별 화면에는 그 목적에 필요한 조작을 적용하며 모든 차트에 같은 보조 버튼을 추가하지 않는다.

## 0.4.4 · 구간 결과와 카드 밀도

공통 구간 표시를 ECharts, SVG, Recharts에 연결했다. 두세 계열을 읽을 여유가 있을 때는 차트 안에 날짜와 증감 값을 놓고, 나머지는 아래에 계열별 끝값과 변화량을 정렬한다. 화면 하단 고정 패널을 제거했다. Hub ETF 공통 축은 표시 선택에서 정하고, Hub·SOX 사분면은 상위와 선택한 종목을 식별한다. News 카드의 출처와 저장을 같은 묶음으로 놓는다.

[공통 지침](DESIGN-GUIDELINES.md) · [리서치 근거](research/RANGE-AND-DENSITY.md)
