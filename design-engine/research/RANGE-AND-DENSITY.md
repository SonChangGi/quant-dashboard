# 구간 비교와 밀도 · 2026-11-10

| 참고한 화면 또는 문서 | 직접 확인한 내용 | 반영 |
| --- | --- | --- |
| [Google Finance NVDA](https://www.google.com/finance/quote/NVDA:NASDAQ?window=1Y) | Aside에서 1년 차트와 포인터 조작. 조회 가격과 등락 숫자는 플롯 상단 가까이 표시되며 기간 전체의 등락률은 가격 머리말에 있었다. 확인한 베타 화면에서 일반 마우스 드래그의 사용자 지정 구간 측정은 재현되지 않았다. | 조회 위치 가까이에 숫자를 놓고 기간과 증감 값을 분리한다. 선택 제스처는 기존 Quant 규칙을 따른다. |
| [TradingView 구간 측정](https://www.tradingview.com/support/solutions/43000516996-date-and-price-range-drawing-tools/) | 기간 음영, 측정의 시작과 끝, 절대 차이와 상대 변화율 구분. | Factor는 양 끝 마커와 범위 음영, 각 계열의 부호 있는 %p를 함께 보인다. |
| [Toss Securities](https://www.tossinvest.com/) · [Toss Design System 발표](https://static.toss.im/slash21/pdf/%5B%ED%86%A0%EC%8A%A4_SLASH%2021%5D%20TDS%EB%A1%9C%20UI%20%EC%8C%93%EA%B8%B0%2C%20%EA%B7%B8%20%EB%A7%8E%EB%8D%98%20%EC%BD%94%EB%93%9C%EB%8A%94%20%EB%88%84%EA%B0%80%20%EB%8B%A4%20%EC%B9%98%EC%9B%A0%EC%9D%84%EA%B9%8C_%EB%B0%95%EB%AF%BC%EC%88%98.pdf) | Aside에서 공개 증권 홈. 강한 제목·숫자와 보조 정보, 간격으로 그룹을 나눈다. 디자인 시스템 발표는 일관된 컴포넌트의 공개 근거다. | News의 주제·출처·저장 묶음, 얇은 경계와 차분한 바탕 위에 주된 제목과 수치 강조. 토스의 색이나 로고를 복제하지 않는다. |
| [Datawrapper 산점도](https://www.datawrapper.de/academy/how-to-create-a-scatter-plot) · [주석](https://www.datawrapper.de/docs/how-to-create-text-annotations) | 좁은 화면에서는 자동 라벨 수가 줄고, 점과 레이블 충돌을 피한다. 크기에 따라 주석의 위치를 바꾼다. | Hub·SOX 라벨은 기본 3~5개와 선택 종목에 집중한다. 각 점은 범례와 선택을 통해 식별할 수 있다. 차트에 주석이 들어갈 실제 너비와 높이를 측정한다. |
| [TradingView 차트 표현 설정](https://tradingview.com/charting-library-docs/latest/customization/overrides/chart-overrides/) | 플롯·축·크로스헤어·가격 라벨 배경은 서로 다른 표현 역할이다. | 다크에서 바탕 #101521, 카드 #171e2d, 비교 패널 #222d42를 분리한다. 본문 #edf2fb, 보조 #a8b5cc, 강조 #78d9e1을 독립 역할로 유지한다. |

| [Financial Times Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary) · [W3C 그래픽 대비 사례](https://www.w3.org/WAI/WCAG21/understanding/non-text-contrast.html) | 시간 변화·상관·순위의 목적에 따라 그래프를 선택하고, 수치를 읽는 대체 경로를 둔다. | 시간 구간 변화, 산점도 영역 선택, 비중 합계의 이름과 단위를 각각 구분한다. 그래프 색 외에 종목명과 데이터 표를 제공한다. |

완료 기준은 실제 화면의 교차점, 라벨의 채운 글자, 시계열 두 끝값과 구간 계산, 모바일 드래그 중 결과, 선택 해제, 확대 후 좌표, 긴 기사 제목과 출처다. 범례나 색으로만 의미를 전달하지 않는다.
