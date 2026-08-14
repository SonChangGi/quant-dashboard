# Quant Research Web Design Prompt

> 버전: `2.2.1`
>
> 기준일: `2026-07-24`
>
> 상태: 앞으로의 기존 페이지 개선과 신규 프로젝트에 사용하는 최우선 웹 디자인 프롬프트
> 적용 범위: Quant Research Hub와 연결되는 모든 공개 웹페이지

이 문서는 단순한 스타일 참고서가 아니라 **디자인 구현 지시문, 보호 경계, 검증 계약**이다. 다음 프로젝트를 시작할 때 구현 담당자는 이 문서 전체를 먼저 읽고, 마지막의 복사용 실행 프롬프트와 함께 사용한다.

## 0. 우선순위

규칙이 충돌하면 아래 순서대로 판단한다.

1. **분석·결과 보호 경계**
2. **현재 공개된 6개 기준 사이트의 실제 디자인과 상호작용**
3. **이 문서에서 추출한 공통 디자인 계약**
4. **프로젝트 고유의 분석 목적과 필요한 예외**
5. **Toss 공개 자료에서 참고한 일반적인 디자인 원칙**

최우선 참조 사이트는 다음 6개다.

| 기준 사이트 | 공개 페이지 | 공통 디자인에 제공하는 핵심 근거 | 반드시 보존할 고유 요소 |
| --- | --- | --- | --- |
| DRAM Price Lab | [dram-price](https://sonchanggi.github.io/dram-price/) | 간결한 타이포그래피, compact shell, 상태 strip, 대표값 카드, 접힌 고급 필터·운영 상세 | 현물·고정가·`spot_proxy`, 제품·출처·지표 필터, 가격 facet, 대표 6개, 관측 표·모바일 카드, source status·fail-closed |
| Fear & Greed Flow Lab | [fearNgreed](https://sonchanggi.github.io/fearNgreed/) | 결과 우선 결론, 날짜 역할 분리, 계열·날짜 탐색, 외부 정확값 readout | KOSPI·신호·선택 전략 3패널, 연구 트랙, ETF 1X/2X, 사건 연구·백테스트·거래표 |
| ETF TOP10 Tracking | [etf-tracking](https://sonchanggi.github.io/etf-tracking/) | 고밀도 다중 계열 차트의 강조·끝 라벨·충돌 방지, 선택일·종목 readout | TOP10 비중, 편입·편출·잔차·가격효과 신호, ETF별 표와 저장 결과 |
| SOX Semiconductor | [sox](https://sonchanggi.github.io/sox/) | constituent 비교, 연동 선택, 막대·사분면 차트, 검색·정렬 고밀도 표 | snapshot date selector, source status, proxy weight, 가격·실적 모멘텀, coordinated selection, leaders, 원래 표 열 |
| Momentum Factor Lab | [momentum-factor-lab](https://sonchanggi.github.io/momentum-factor-lab/) | 결과→차트→입력→상세 구조, 선택 계열 강조, 프레젠테이션 상태 격리 | schema v5, 64 factors, 고정 70/30, best·selected·benchmark, preset·grid manifest, 입력·URL·local API, result-unavailable fail-closed |
| Best Factor Lab | [best-factor](https://sonchanggi.github.io/best-factor/) | 공식 결과와 표시 설정·재실행 입력의 분리, 고밀도 팩터 비교, 결과 결합 상태, 입력 panel의 단계적 공개 | 공식 ranking·holdout·보유 종목, best·selected·Nasdaq 비교, 11개 실제 분석 입력, `result_binding`, 입력별 CLI 전달, 기존 결과·표·JSON 계약 |

### 0.1 검증 기준선

이 문서의 규범은 계속 변하는 공개 화면을 자동 추종하지 않는다. 아래 `2026-07-24` UI 기준 commit과 공개 asset을 대조해 확정했다. 데이터 자동 갱신으로 원격 main이 앞으로 이동해도 UI 파일이 같으면 이 기준은 유지한다. UI가 바뀌면 이 문서를 검토·version-up한 뒤에만 새 기준으로 채택한다.

| 사이트 | UI 기준 commit | 기준 UI source |
| --- | --- | --- |
| DRAM | `7808d1400ae1ada880ff9ee3103fe417a0196e7a` | `frontend/src/index.css`, `App.tsx`, `components/shared-nav.tsx`, `components/price-chart.tsx` |
| Fear & Greed | `e1e1e720cf1ab406320379afadc522870e3c3032` | `index.html`, `assets/styles.css`, `assets/app.js` |
| ETF Tracking | `a11f9aa7cda743767eb4ca1781e826565778a084` | `index.html`, `assets/styles.css`, `assets/app.js` |
| SOX | `f570adf16554d8e006ee8d8b703335288ea3ce78` | `index.html`, `assets/styles.css`, `assets/app.js` |
| Momentum | `a6ef9c6ac086590e5400c6d17ef107071adfcd65` | `docs/index.html`, `docs/assets/styles.css`, `docs/assets/dashboard.js` |
| Best Factor | `269f8d4c872f5fd3275cf43747ad3a5ac4fbc8e2` | `docs/index.html`, `docs/styles.css`, `docs/app.js`, `docs/data/dashboard-config.json` |

### 0.2 여섯 사이트가 서로 다를 때

- 3개 이상에서 반복되고 분석 의미와 충돌하지 않는 패턴은 공통 기본값으로 채택한다.
- 단, 8개 메뉴·theme·입력 상태·결과 binding처럼 이 문서가 명시한 canonical contract는 기존 구현의 다수결이 아니라 **모든 페이지가 이동할 목표 규칙**이다.
- 프로젝트 분석 의미 때문에 필요한 차이는 허용된 variant로 기록한다.
- 단순히 과거 구현이 달랐다는 이유로 새 variant를 만들지 않는다.
- 한 사이트를 통째로 복사하지 않는다. **여섯 사이트의 공통 문법**을 사용한다.

## 1. 절대 보호 경계

### 1.1 디자인 작업으로 변경할 수 있는 것

- HTML 구조의 시각적 순서와 접근성 markup
- CSS token, typography, spacing, layout, responsive behavior
- 화면 표시용 컴포넌트, 차트 renderer, tooltip, readout, legend
- 표시 전용 선택·hover·focus·날짜 탐색 상태
- 중복 설명 제거와 운영 상세의 단계적 공개
- 디자인 회귀를 막는 DOM·접근성·시각 테스트

### 1.2 절대 변경하지 않는 것

- Python 수집·정제·분석·전략·백테스트 코드
- 계산식, threshold, ranking, weighting, 포지션, 체결 규칙
- 입력값에 따라 결과가 달라지는 기존 실행 경로
- 공개 JSON schema, field, 정밀도, 날짜 의미, 생성 결과
- 원본·생성 데이터 파일과 이전 결과 이력
- API·CLI 계약, 분석·결과 identity에 쓰이는 cache key, result identity
- 기존 프로젝트의 데이터 수집·분석 workflow, 자동화 주기, Pages 경로, 데이터 권리
- fail-closed, unavailable, blocked, degraded, stale 판정
- 차트 series의 값·단위·경제적 의미와 표의 열·순서·원본 행

### 1.3 혼합 파일 보호

JavaScript나 TypeScript 한 파일에 renderer와 계산 로직이 함께 있으면 파일 전체를 변경 가능하다고 보지 않는다.

- DOM 생성, class, ARIA, 표시 문자열, presentation state만 수정한다.
- 계산·normalization·selection·aggregation 함수는 동결한다.
- 수정 전후 같은 fixture·입력의 결과 JSON과 핵심 숫자가 같아야 한다.
- 기존 DOM id·`data-*` hook, fetch URL·key mapping, 입력 기본값·허용 범위는 보존한다.
- 같은 fixture의 표 행 수와 차트 series·point 수가 수정 전후 같아야 한다.
- 표시 제어가 분석 입력처럼 보이면 두 상태를 명확히 분리한다.
- 필요한 디자인을 계산 변경 없이 구현할 수 없으면 작업을 멈추고 사용자에게 알린다.

Python 파일 안에 HTML/CSS presentation template이 들어 있는 프로젝트는 해당 template 영역만 수정할 수 있다. 분석·수집·결과 함수 diff는 금지하며, 같은 fixture의 underlying 결과가 완전히 같다는 테스트가 있어야 한다.

신규 프로젝트의 frontend build·Pages 배포 workflow는 사용자가 별도로 승인한 경우에만 추가할 수 있다. 이 경우에도 분석 자동화, secret, data rights와 결과 생성 경로는 변경하지 않는다.

### 1.4 입력의 네 종류를 먼저 선언한다

모든 입력·선택·필터는 구현 전에 아래 네 종류 중 하나로 등록한다. 한 control이 두 역할을 동시에 가져서는 안 된다. 역할이 섞이면 control과 상태를 분리한다.

| `control_kind` | 의미 | 새 분석 실행 | 결과 identity 영향 | 예시 |
| --- | --- | --- | --- | --- |
| `display` | 현재 결과를 정렬·검색·강조하거나 보이는 방식만 변경 | 없음 | 없음 | 표 행 수, 화면 정렬, 검색, 차트 강조 계열, 차트 선택일 |
| `result_selector` | 이미 계산·검증된 preset, 기준일, 결과를 선택 | 없음 | 선택한 기존 result identity로 전환 | 저장 기준일, 저장 preset, 공식 결과 버전 |
| `analysis` | 권위 있는 분석 engine을 새 입력으로 실행 | 필수 | 새 config와 run identity 생성 | 분석 기간, 리밸런싱, 편입 종목 수, weighting, 팩터 집합, 거래비용 |
| `operation` | 수집·백필·강제 갱신·발행 등 운영 작업 | 운영 경로에 따름 | 분석 결과와 별도 operation identity | 전체 backfill, refresh-existing, 재발행 |

각 control은 코드 또는 검증 manifest에 다음 정보를 가져야 한다.

- 안정적인 input id
- `display`, `result_selector`, `analysis`, `operation` 중 하나인 `control_kind`
- 기본값의 출처: HTML 상수, 현재 결과, 저장 설정 중 하나
- type, 단위, 허용값·범위, 비어 있을 때 의미
- URL·local storage·request payload에 포함되는지 여부
- canonical input key와 schema version
- `analysis`이면 대응하는 API field, workflow input, CLI flag 또는 Python parameter
- 결과에서 해당 입력이 적용되었음을 확인할 field 또는 result binding
- 입력이 결과 수치를 바꾸지 않아도 정상인 명시적 no-op 조건
- 입력부터 결과까지 검증하는 binding test

화면에 입력창이 존재하거나 command 문자열이 생성된다는 사실만으로 입력 연결이 완료된 것이 아니다.

### 1.5 현재 6개 사이트의 입력 기준선

새 구현은 현재 페이지의 control 의미를 먼저 보존하고, 아래 상태보다 기능을 후퇴시키지 않는다.

| 프로젝트 | 현재 입력 경계 | 구현 원칙 |
| --- | --- | --- |
| DRAM | 8개 `display`, 차트 관찰일 1개 `result_selector` | 저장 관측만 사용한다. 사용자 분석 API를 만들거나 관찰일 선택을 재계산으로 표현하지 않는다. |
| ETF Tracking | 15개 `display`, 5개 `result_selector`, 인증된 1개 `operation` | 저장 이력 탐색과 수집 작업을 분리한다. 공개 표시·선택 control은 분석 run을 만들지 않는다. |
| SOX | 공개 5개 `display`, 1개 `result_selector`, 별도 인증 운영 작업 2개 | 저장 기준일·종목을 선택한다. 기준일 선택과 owner operation을 재계산 form으로 표현하지 않는다. |
| Momentum | 26개 독립 `analysis` ResearchInputs → 정적 preset 또는 Python job API | `analysis` 전 구간과 `resultKey` binding을 보존하고 공용 API·worker로 확장한다. |
| Best Factor | 11개 `analysis` 입력 → workflow/CLI → Python | command 생성만으로 완료 처리하지 않는다. 실제 run 제출·상태·결과 binding을 연결하기 전에는 `적용`·`재계산` CTA로 표현하지 않는다. 시가총액 metadata 부족처럼 요청값이 미적용되는 fallback은 `allow_fallback` 동의 없이 성공시키지 않는다. |
| Fear & Greed | 5개 `display`, 브라우저 13개 `analysis`, 3개 `operation` | `browser_scenario` engine을 명시하고 Python 공식 결과로 표현하지 않는다. Python 이전 전에는 JS/Python parity fixture를 통과한다. |

### 1.6 입력 → 권위 분석 engine → 결과 계약

`analysis` control은 다음 전 구간이 실제로 연결되어야 한다. 권위 분석 engine은 원칙적으로 기존 Python 진입점이다. 현재 계약이 브라우저 engine인 프로젝트는 계산 위치를 결과에 명시하고 Python 결과라고 부르지 않는다.

```text
control
→ frontend validation
→ canonical request/config serialization
→ API·workflow·CLI 전달
→ 선언된 권위 engine인 기존 Python 분석 함수·CLI 또는 검증된 browser scenario 실행
→ 입력을 포함한 run identity
→ 새 결과 저장
→ frontend가 새 결과와 입력의 결합을 검증
→ 화면 갱신
```

필수 규칙:

- Python 계산식·전략을 frontend나 API에 다시 구현하지 않는다. API와 worker는 기존 Python 진입점을 호출한다.
- frontend 기본값은 임의 placeholder가 아니라 현재 결과에 실제 적용된 설정 또는 공식 기본 설정에서 읽는다.
- 제출한 입력은 canonical form으로 정규화하고, 같은 입력은 같은 config hash를 만들어야 한다.
- 결과는 최소 `run_id`, 요청 설정의 `config_hash`, 실제 적용 설정의 `effective_config_hash`, `input_schema_version`, `data_as_of`, `calculated_at`, `code_version`, artifact URL·SHA-256 또는 동등한 identity를 가져야 한다.
- frontend는 제출한 `config_hash`와 결과의 binding이 일치할 때만 `현재 결과에 적용됨`이라고 표시한다.
- artifact를 쓰는 결과는 선언된 URL의 **실제 bytes를 가져와 byte size와 SHA-256을 검증한 뒤** payload를 채택한다. 같은 응답 envelope 안의 payload·hash를 서로 비교하거나 envelope로 가짜 run을 만들어 자기 자신과 비교하는 검증은 binding 증거가 아니다.
- binding이 없거나 다르면 이전 결과를 새 결과처럼 표시하지 않고 `대기`, `불일치`, `실패` 상태로 닫힌다.
- 비동기 분석은 `queued → running → succeeded | failed | cancelled` 상태를 구분하고, 이전 성공 결과와 새 실행 상태를 섞지 않는다.
- 비동기 조회 시간은 worker의 실제 최대 실행 시간과 publication 여유보다 짧아서는 안 된다. browser polling이 끝나도 server run은 내구 저장소에서 재조회할 수 있어야 하며, timeout·재시작·callback 누락은 성공이 아니라 명시적 실패 상태로 수렴해야 한다.
- GitHub Pages처럼 서버 실행이 없는 화면은 입력이 즉시 계산된다고 표현하지 않는다. 실제 workflow/API 실행 경로가 없으면 분석 input UI를 공개 기능처럼 만들지 않는다.
- frontend 상태는 `applied_config`, `draft_config`, `pending_run`, `bound_result`로 분리한다. draft 변경만으로 공식 카드·차트·표를 바꾸지 않는다.
- `display` 변경 전후에는 config hash, run id, Python command와 저장 결과가 변하지 않아야 한다.
- `result_selector`는 새 계산을 만들지 않고 존재하는 result identity만 선택한다.
- `operation`은 일반 공개 분석 입력과 같은 form에 섞지 않고 인증된 운영 경로에 둔다.
- `requested_inputs`, `normalized_inputs`, `effective_inputs`, `ignored_inputs`, `fallbacks`를 결과 metadata에 기록한다.
- 요청값과 실제 적용값이 다르면 조용히 성공시키지 않는다. 사용자가 명시적으로 `allow_fallback`에 동의하지 않았다면 실패 상태로 끝낸다.
- fallback이 없으면 `config_hash == effective_config_hash`여야 한다. 명시적으로 허용된 fallback이 있으면 `config_hash`는 요청 identity로 유지하고, 별도 `effective_config_hash`가 실제 적용값을 증명하며 모든 차이를 fallback record로 설명한다.

분석 task에서 Python을 수정하지 않았다는 사실은 입력 동작의 증거가 아니다. 반드시 black-box 실행으로 결과 변화를 검증한다.

### 1.7 입력 민감도와 결정성 테스트

모든 `analysis` control은 최소 다음 테스트를 통과해야 한다.

1. **전달 테스트**: control 값이 canonical config와 실제 CLI/Python parameter에 정확히 도달한다.
2. **결정성 테스트**: 같은 데이터·코드·입력으로 두 번 실행하면 허용된 비결정 요소를 제외한 핵심 결과가 같다.
3. **민감도 테스트**: 해당 입력만 의미 있게 바꾼 A/B fixture에서 그 입력이 책임지는 결과 field·행·포트폴리오·기간이 달라진다.
4. **격리 테스트**: `display` control을 바꿔도 Python command·config hash·결과 JSON은 그대로다.
5. **binding 테스트**: 결과의 입력 hash·기준일·코드 버전이 요청과 정확히 맞고, 선언된 artifact의 실제 bytes·크기·SHA-256이 검증될 때만 화면이 결과를 채택한다. envelope 자기 비교는 금지한다.
6. **실패 테스트**: 잘못된 값, timeout, worker 실패, stale result에서 이전 결과를 새 결과처럼 보이지 않는다.

실제 데이터에서 두 합법 입력이 우연히 같은 결과를 낼 수 있다. 이 경우 핵심 숫자가 같다는 이유만으로 실패시키거나, 반대로 기능을 통과 처리하지 않는다. 입력이 실제 worker argument와 새로운 config·run identity에 도달하는지 확인하고, 결과 영향이 분명한 작은 결정적 fixture로 계산 경로를 증명한다. 단순 mock 호출 횟수만으로 민감도 테스트를 대체하지 않는다.

### 1.8 백엔드·프런트엔드 분리 경계

프로젝트 규모상 분리가 유리하면 다음 책임을 사용한다.

- frontend: 표시 상태, 입력 수집, validation feedback, 실행 요청, 상태 조회, 결과 rendering
- API: schema validation, 인증·권한, run 생성, idempotency, 상태·결과 조회
- worker: 기존 Python 수집·분석 CLI 실행, artifact 검증, 결과 저장
- storage: versioned result, run metadata, config hash, data quality·freshness 상태

분리는 계산 로직 복사를 의미하지 않는다. Python 분석은 worker의 단일 source of truth로 유지한다. 정적 JSON snapshot은 삭제하지 않고 검증된 공개 결과와 장애 시 fallback으로 유지한다.

공통 frontend는 다음 경계를 사용한다.

```text
packages/
  ui/          token과 프로젝트가 소유하는 재사용 primitive
  shell/       8개 메뉴, theme, page header, status, disclosure
  charts/      frame, plot 밖 readout, 날짜·계열 선택 primitive
  contracts/   Zod 기반 control registry, run/result envelope
  data-client/ 정적 snapshot과 API result adapter
  testing/     nav·theme·binding·E2E 공통 검증
apps/
  */           프로젝트별 view-model, chart renderer, table schema
```

공통 package는 navigation·token·button·card·input shell·disclosure·table shell·chart interaction primitive만 공유한다. 프로젝트별 계산 결과 구조, series 의미, table column과 분석 정보 구조는 각 app이 소유한다. shared package로 계산식을 옮기거나 범용화를 이유로 result schema를 합치지 않는다.

`shadcn/ui`처럼 component source를 프로젝트가 직접 소유하는 방식은 사용할 수 있지만, Tailwind·Radix·특정 UI library 자체를 공통 디자인의 필수 조건으로 만들지 않는다. 현재 stack에 이미 검증된 component가 있으면 의미·접근성·상태 계약만 맞추고 전면 교체하지 않는다.

Supabase 같은 client-accessible storage를 사용할 때 browser에는 publishable key만 허용하고 RLS를 적용한다. service-role·provider credential·GitHub token은 frontend bundle과 공개 JSON에 넣지 않는다.

## 2. 제품 인상

Quant Research 제품군은 다음처럼 보여야 한다.

- 차분하고 정확한 개인 리서치 도구
- 밝은 중립 surface와 절제된 blue accent
- 숫자와 날짜가 먼저 읽히고 장식은 뒤로 물러나는 화면
- 데이터가 많아도 질서가 있고, 빈 공간이 많아도 마케팅 페이지처럼 보이지 않는 화면
- 라이트·다크 모두 같은 정보 위계와 의미를 유지하는 화면

피해야 할 표현:

- 거대한 hero와 과도한 세로 여백
- 화면 전반의 굵은 글자, badge, gradient, glow, glassmorphism
- 의미 없는 rainbow 카드와 그림자 중첩
- 모든 내용을 카드로 감싸는 card-in-card 구조
- 실제 상태를 과장하는 성공색·경고색
- 투자 행동을 재촉하거나 성과를 보장하는 문구

## 3. 공통 정보 구조

기본 순서는 다음과 같다.

1. 9개 공통 메뉴와 현재 페이지
2. 페이지 정체성, 운영 상태, 데이터 기준일
3. 결론·신호·최신 대표값
4. 3~5개의 핵심 지표
5. 가장 중요한 차트와 정확값 탐색
6. 필요한 분석 입력·필터
7. 상세 차트·표·거래·원시 관측
8. 하나의 닫힌 `데이터 · 출처 · 운영 상세`

### 3.1 첫 화면

가능하면 `1440×900`에서 다음이 보이게 한다.

- 공통 메뉴
- 페이지 제목
- 현재 결과와 기준일
- 핵심 차트의 제목·상단 또는 주요 행동

첫 화면에서 설정이 꼭 필요하면 전체 form 대신 현재 적용값과 필수 입력만 둔다. 긴 고급 설정은 접는다.

### 3.2 상태와 날짜

운영 상태와 분석 결과를 합치지 않는다.

- 운영 상태: 수집·검증·신선도·출처의 사용 가능성
- 분석 상태: 신호·포지션·가격·팩터·리스크 등 계산 결과

날짜도 다음 역할을 섞지 않는다.

| 역할 | 표시 위치 |
| --- | --- |
| 데이터 기준일 | 상단 상태 또는 핵심 결과 |
| 평가 종료일 | 해당 전략·모형 결과 |
| 차트 선택일 | 차트 정확값 readout |
| 필터 기간 | 차트 metadata |
| 생성·수집 시각 | 운영 상세 |

프로젝트에 없는 날짜 역할을 새로 만들지 않는다.

## 4. 9개 공통 메뉴

아래 registry의 label·순서·URL은 모든 사이트에서 동일해야 한다.

| 순서 | Label | URL |
| ---: | --- | --- |
| 1 | Hub | `https://sonchanggi.github.io/quant-dashboard/` |
| 2 | Fear & Greed | `https://sonchanggi.github.io/fearNgreed/` |
| 3 | Momentum | `https://sonchanggi.github.io/momentum-factor-lab/` |
| 4 | DRAM | `https://sonchanggi.github.io/dram-price/` |
| 5 | Best Factor | `https://sonchanggi.github.io/best-factor/` |
| 6 | ETF | `https://sonchanggi.github.io/etf-tracking/` |
| 7 | SOX | `https://sonchanggi.github.io/sox/` |
| 8 | Regime | `https://sonchanggi.github.io/regime/` |

### 4.1 Canonical navigation

이 항목은 기존 여섯 구현에서 가장 많은 모양을 고르는 규칙이 아니라, 기존·신규 모든 페이지가 이동할 목표 contract다.

- full-width sticky shell, 기본 높이 `58px`
- 내부 content 최대 폭 `1320px`
- brand `14px / 700`
- link `12px / 650`
- 모든 link·theme control 최소 `44×44px`
- nav shell `border-radius: 0`, 하단 `1px` border, 약한 blur만 사용
- 현재 페이지는 `primary-soft` 배경과 `primary-strong` 글자
- 현재 페이지 하나에만 `aria-current="page"`
- 첫 keyboard focus는 `본문으로 건너뛰기`
- brand label은 `Quant Research Hub`, href는 Hub URL로 통일
- 별도 gradient `Q` mark 같은 프로젝트별 장식은 공통 nav에서 사용하지 않음
- theme control은 sun/moon icon의 `44×44px` button으로 통일하고 `aria-pressed`와 `라이트 모드로 전환`·`다크 모드로 전환` 동적 label을 제공

`760px` 이하에서는 brand와 theme control을 첫 행에 유지하고, 8개 링크를 두 번째 행의 **메뉴 자체 horizontal rail**로 제공한다. 링크를 문서 밖으로 넘기거나 일부만 숨기지 않는다.

각 저장소는 메뉴를 자체 구현할 수 있지만 위 registry를 그대로 사용한다. 다른 저장소의 runtime CSS·JavaScript를 외부 import하지 않는다.

## 5. Layout·Spacing·Shape

### 5.1 폭과 gutter

- 기본 content max-width: `1240~1320px`
- desktop gutter: 최소 `16px`, 일반 `20~32px`
- mobile gutter: `12~16px`
- 한 section 안의 핵심 열은 `minmax(0, 1fr)`로 수축 가능해야 한다.

### 5.2 간격

4px/8px 계열을 사용한다.

`4, 6, 8, 12, 16, 18, 20, 24, 28, 32, 40, 48`

- compact section 간격: `14~20px`
- major section 간격: `20~28px`
- card gap: `12~18px`
- 일반 card padding: `14~18px`
- major panel padding: `18~24px`
- compact control group padding: `10~14px`
- 설명 문단과 heading margin만으로 세로 길이를 늘리지 않는다.

### 5.3 모서리와 그림자

- 기본 panel radius: `8px`
- button·input radius: `6px`
- 상태 chip·pill: `999px`
- 기존 승인 화면이 `10~16px` radius를 쓰면 프로젝트 안에서만 일관되게 유지할 수 있다.
- 그림자는 panel 구분이 border만으로 부족할 때 한 단계만 사용한다.
- dark mode에서 밝은 glow를 만들지 않는다.
- 기본 light shadow는 `0 8px 24px rgba(25, 31, 40, .07)`, compact shadow는 `0 2px 8px rgba(25, 31, 40, .045)` 이내로 사용한다.
- dark shadow는 `0 18px 44px rgba(0, 0, 0, .30)` 이내로 사용한다.

## 6. Semantic Color

색 이름이 아니라 역할을 공유한다. 아래 값은 `2026-07-24`에 현재 6개 공개 사이트와 최신 source의 computed style·CSS token을 대조한 뒤, 반복된 역할에서 선택한 **신규 프로젝트·누락 token용 fallback 팔레트**다. 기존 사이트는 의미 역할만 mapping하고 승인된 값을 이 표로 일괄 교체하지 않는다. 일부 neutral·blue 값은 기존 사이트가 채택해 온 Toss-inspired 색감 때문에 TDS 공개 팔레트와 일치한다. 이 문서는 TDS에서 신규 값을 가져오는 근거가 아니라 이미 구현·검증된 6개 사이트의 호환성을 유지하는 근거다.

| Token | Light | Dark | 용도 |
| --- | --- | --- | --- |
| `--bg` | `#f7f9fb` | `#111318` | 문서 배경 |
| `--surface` | `#ffffff` | `#181d26` | 기본 panel |
| `--surface-raised` | `#ffffff` | `#1d2430` | 선택·상승 panel |
| `--surface-soft` | `#f2f4f6` | `#242b38` | filter·header·neutral |
| `--text-primary` | `#191f28` | `#f2f4f6` | 본문 |
| `--text-strong` | `#0b1018` | `#ffffff` | 제목·핵심값 |
| `--text-muted` | `#6b7684` | `#b0bac7` | metadata |
| `--text-muted-strong` | `#4e5968` | `#d1d6df` | 보조 본문 |
| `--border` | `#e5e8eb` | `#303948` | 기본 경계 |
| `--border-strong` | `#d1d6db` | `#465267` | focus·축·강한 경계 |
| `--primary` | `#3182f6` | `#5da2ff` | 주 동작·선택 계열 |
| `--primary-strong` | `#1b64da` | `#8ec0ff` | 링크·active text |
| `--primary-soft` | `#eaf3ff` | `#182b44` | active surface |
| `--primary-soft-strong` | `#d8eaff` | `#203a5f` | active border·selection |
| `--positive` | `#008768` | `#62d4a4` | 검증된 긍정 상태 |
| `--positive-soft` | `#e5f8f2` | `#14362b` | 긍정 상태 surface |
| `--warning` | `#b76e00` | `#ffd166` | 주의·stale |
| `--warning-soft` | `#fff4df` | `#3a2d14` | 주의 상태 surface |
| `--negative` | `#e03131` | `#ff8a8a` | 오류·위험 |
| `--negative-soft` | `#fff0f0` | `#3c1d22` | 오류 상태 surface |
| `--chart-grid` | `#d8dee8` | `#344154` | 차트 격자 |
| `--chart-axis` | `#9aa4b2` | `#66758c` | 축·guide |
| `--chart-text` | `#4e5968` | `#c3ccda` | 축·legend text |
| `--chart-focal` | `#3182f6` | `#5da2ff` | 선택한 핵심 계열 |
| `--chart-alt` | `#1687a7` | `#67d4f2` | 대안 계열 |
| `--chart-secondary` | `#7c3aed` | `#b69cff` | 보조 비교 계열 |
| `--chart-benchmark` | `#8b95a1` | `#b0bac7` | 중립 benchmark |

규칙:

- 실제 저장소의 기존 변수명은 위 역할에 alias할 수 있다.
- 기존 6개 사이트의 값을 fallback hex로 강제 교체하지 않는다.
- 프로젝트 고유 의미색은 유지한다.
- blue는 기본 선택·주 동작, green·teal은 긍정 또는 대안, amber는 주의, red는 부정·오류에만 사용한다.
- 색만으로 신호를 구분하지 않는다. label, marker, dash, icon 중 하나를 함께 쓴다.
- 라이트와 다크는 같은 hex의 단순 반전이 아니다. 각 테마의 실제 대비를 따로 검증한다.
- 일반 본문·control·표는 WCAG AA 대비를 목표로 한다.

## 7. Typography

```css
font-family:
  Pretendard,
  Inter,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  "Noto Sans KR",
  sans-serif;
```

- body: `15px / 1.55 / 400~500`
- helper·table cell: `12~14px`
- 일반 보조 본문: `13~15px`
- metadata·table header·eyebrow: `11~12px`
- 조작 label과 핵심 상태: 최소 `12px`
- page title: `clamp(2rem, 4vw, 3.25rem)`, 주로 `700`
- section title: `clamp(1.35rem, 2.3vw, 1.8rem)`, `700`
- card title: 약 `14~16px`, `650~700`
- 대표 숫자: `1.45~2rem`, `700`
- button·label: `600~700`
- `800~900`은 brand·eyebrow·한 화면의 한두 개 강조에만 사용한다.

한 카드나 한 행에서는 하나의 정보만 가장 진하게 한다. 전역 `strong` 규칙으로 다수 문장을 모두 bold 처리하지 않는다.

금융 숫자는 `font-variant-numeric: tabular-nums`를 사용하고 값과 단위를 붙여 읽을 수 있게 한다. 숫자만 크게 만들고 단위·기준일을 지나치게 작게 만들지 않는다.

## 8. 공통 컴포넌트

### 8.1 Page header

- eyebrow, 한 개의 h1, 필요할 때만 한 문장 설명
- 상태·기준일은 별도 status strip 또는 summary panel
- hero를 마케팅 banner처럼 크게 만들지 않는다.

### 8.2 Status strip

- `상태`, `데이터 기준일`, 필요한 핵심 날짜·출처를 짧게 표시한다.
- 정상 상태는 한 줄, 오류·degraded만 짧은 대응 문장을 추가한다.
- 상세 사유와 자동화 내역은 운영 상세로 이동한다.

### 8.3 Result·metric card

- label → 핵심값 → 단위·기준일 순서
- 한 카드에 대표값 하나를 원칙으로 한다.
- 3~5개 핵심 지표를 먼저 보여 주고 나머지는 상세로 보낸다.
- 카드 전체를 badge와 bold로 채우지 않는다.
- 값이 없으면 `0`으로 만들지 말고 `관측 없음`, `사용 불가`를 표시한다.

### 8.4 Button·link

- 실제 동작을 예측할 수 있는 label을 쓴다.
- `확인`, `적용`만 쓰기보다 `최근 1년 보기`, `평가 종료일로`, `필터 적용`처럼 쓴다.
- primary action은 section당 1개를 기본으로 한다.
- icon-only control은 accessible name과 `44×44px` target을 갖는다.
- hover 시 `translateY(-1px)`보다 색·border 변화가 우선이다.

### 8.5 Input·filter

- label, 현재값, 단위를 붙여 제공한다.
- 분석 입력과 표시 제어를 시각적으로 구분한다.
- 분석 입력 panel은 **현재 결과에 적용된 값의 compact summary만 항상 보이고 form 본문은 기본 닫힘**으로 시작한다.
- `현재 적용값`과 `편집 중 값`을 구분하며, 성공 결과 binding 전에는 draft 값으로 공식 카드·차트·표를 바꾸지 않는다.
- 분석 입력은 기존 적용·재계산 경로를 그대로 사용하고 새 adapter는 기존 Python 진입점을 호출한다.
- 표시 제어는 공식 결과·URL·저장 설정을 바꾸지 않는다.
- 고급 필터는 기본 닫힘으로 둘 수 있지만 현재 적용값은 요약한다.
- 실제 실행 경로가 없는 command-copy UI는 `적용`, `실행`, `재계산` CTA로 표현하지 않는다. `실행 명령 복사`처럼 실제 동작을 그대로 쓴다.
- 오류는 입력 근처에서 해결 방법과 함께 표시한다.

### 8.6 Badge·status

- badge는 상태·분류·현재 선택에만 쓴다.
- 장식용 badge를 만들지 않는다.
- text와 배경 모두 의미색 대비를 충족한다.
- `정상`, `주의`, `사용 불가`처럼 짧은 상태를 먼저 보여 준다.

### 8.7 Disclosure

다음 정보는 하나의 기본 닫힘 `데이터 · 출처 · 운영 상세`로 모은다.

- 공급자와 원본 링크
- 생성·수집 시각
- fallback과 자동화 기록
- 일반 규제·면책·제한·한계
- 원본 JSON·GitHub Actions 링크

현재 결과를 사용할 수 없게 만드는 warning·error는 접지 않는다. 상세 원인만 접는다.

결과 해석에 필요한 분석 설정·신호 계산·전략 방법·팩터 선정 근거는 운영 정보와 합치지 않는다. Fear & Greed와 Momentum처럼 도메인상 필요한 방법론은 해당 결과 가까이의 별도 접힌 section으로 유지한다.

### 8.8 Loading·empty·degraded

- loading은 기존 layout 크기를 유지하는 subdued placeholder와 짧은 상태 문구로 표시한다.
- empty는 어떤 필터·데이터 조건 때문에 비었는지와 가능한 다음 행동을 말한다.
- degraded·stale은 현재 값의 사용 가능 범위와 기준일을 함께 표시한다.
- error·unavailable에서는 이전 값이나 `0`을 새 결과처럼 보이지 않는다.
- 상태 전환 때 layout이 크게 뛰거나 흰 화면이 번쩍이지 않게 한다.

### 8.9 긴 페이지 빠른 이동

Fear & Greed, ETF Tracking, SOX, Momentum처럼 긴 페이지에는 기존 상단·하단 빠른 이동을 유지할 수 있다. 짧은 페이지에는 억지로 추가하지 않는다.

- `맨 위로`, `맨 아래로`를 예측 가능한 accessible name으로 제공한다.
- 같은 `44×44px` icon button을 `8px` 간격의 세로 묶음으로 사용한다.
- desktop은 viewport 오른쪽·아래 `16~24px`에 고정한다.
- mobile은 숨기거나 normal flow의 전용 행으로 옮긴다. content 위에 fixed overlay로 띄우지 않는다.
- chart label, table control, primary CTA를 가리지 않도록 충돌 시 인접한 빈 영역으로 옮기거나 해당 방향 button을 숨긴다.
- dialog·tooltip보다 낮은 stacking layer를 사용하고 keyboard focus와 reduced motion을 지원한다.

## 9. Table

기존 표의 column·order·값은 보존한다.

- wrapper만 `overflow-x: auto`
- column이 많으면 표를 찌그러뜨리지 말고 `min-width`를 둔다.
- header는 필요하면 sticky, `11~12px / 650~700`
- cell은 `12~14px`, padding `10~14px`
- 텍스트·종목명은 왼쪽, 숫자·비율·금액은 오른쪽
- 숫자는 tabular figures, 단위와 소수점 규칙은 원본 계약 유지
- 날짜 형식은 같은 표 안에서 통일
- row border는 `--border`, hover·selected는 `--primary-soft`
- sortable table은 `aria-sort`와 현재 정렬 방향을 제공
- keyboard focus가 행 안의 링크·button에서 보이게 한다.
- mobile에서 표만 내부 스크롤하며 document overflow를 만들지 않는다.

DRAM처럼 단순 관측 목록은 모바일 카드로 바꿀 수 있다. 사건 연구·백테스트·거래·다열 분석표는 의미를 잃는 카드로 쪼개지 않고 표를 보존한다.

빈 결과, loading, 오류는 표 안에서 colspan을 맞춘 한 행으로 표시하고 가짜 행을 만들지 않는다.

## 10. Chart

기존 chart type, panel, series, axis, legend, 단위와 계산 결과를 유지한다.

아래 상호작용은 **그 구조가 이미 있거나 도메인상 필요한 차트에만** 적용한다.

- 계열 preview·pin은 multi-series comparison chart에만 적용한다.
- 날짜 입력·화살표 탐색은 date-axis chart에만 적용한다.
- 단일 series, 비시계열, 작은 요약 차트에 새 control이나 가로 scroll을 강제하지 않는다.
- SOX 같은 bar·quadrant chart는 ticker coordinated selection을 유지하고 line-chart 규칙을 적용하지 않는다.

### 10.1 기본 구성

차트 section은 다음 순서를 사용한다.

1. 제목·짧은 기간/단위
2. plot 밖 정확값 readout
3. 계열 선택·날짜 제어
4. plot
5. 필요한 한 줄 도움말
6. 접근 가능한 정확값 표

정확값 readout만 plot 밖에 고정한다. 계열·날짜 control은 plot 바로 위 또는 아래의 인접 영역에 둘 수 있다. 접근 가능한 값 대안은 같은 section의 표 또는 명확히 연결된 관측·구성종목 표로 제공할 수 있다.

### 10.2 계열 강조

- hover·focus는 임시 preview
- click·tap·Enter·Space는 pin
- line chart의 active stroke는 대체로 `3.8~4px`, context stroke는 `2~2.8px`
- line chart의 비활성 opacity는 `.12~.22`에서 실제 문맥 계열이 보이도록 theme별 조정
- bar·quadrant의 비활성 opacity는 `.35~.55`를 기준으로 하고 inset·scale·label을 함께 사용
- pointer가 떠나거나 blur되면 직전 pinned state로 복귀
- active 계열은 굵기·점·halo·label로도 구분
- 한 번에 모든 계열을 강하게 표시하지 않는다.

### 10.3 날짜 탐색

- date-axis chart에만 적용한다.
- hover는 날짜 preview, click·tap은 고정
- `ArrowLeft`, `ArrowRight`, `Home`, `End`
- date input과 `최신일로` 또는 `평가 종료일로`
- 선택일 세로 guide는 `dash 4 4`
- 선택 point와 halo를 표시
- 휴장일·누락일 처리는 기존 프로젝트 규칙을 유지

### 10.4 정확값과 tooltip

- 날짜·계열·정확값·단위는 plot 밖의 정상 흐름 readout에 둔다.
- 차트 위에 큰 absolute 정보 박스를 상시 올리지 않는다.
- tooltip은 pointer·focus에서만 잠깐 표시하고 viewport 밖이면 자동으로 위치를 바꾼다.
- tooltip은 Escape·외부 click으로 닫을 수 있어야 한다.
- custom readout과 SVG native title, 모든 시점 label을 동시에 중복 노출하지 않는다.
- 끝 라벨은 전용 gutter와 collision rule을 갖는다.
- 값이 많은 차트는 모든 label을 강제하지 않는다.

### 10.5 다중 단위와 사건

- 가격·수익률·지수·비중처럼 다른 단위는 panel·facet 또는 명확한 축으로 분리한다.
- 신호일과 체결일은 marker·shape·label로 구분한다.
- 관측이 없으면 선을 임의 보간하지 않는다.
- 선택일에 값이 없으면 `관측 없음`을 표시한다.

### 10.6 모바일

- readout과 control은 scroll canvas 밖에 둔다.
- 고밀도 chart는 plot만 `620~960px` 내부 canvas로 가로 스크롤할 수 있다.
- document 자체의 가로 overflow는 금지한다.
- chart frame 하나를 keyboard focus 지점으로 사용하고 SVG node마다 tab stop을 만들지 않는다.

## 11. UX writing

- 결론·기준일·핵심 수치·다음 행동을 먼저 쓴다.
- 같은 내용을 title, badge, helper, footer에서 반복하지 않는다.
- 제목·값·control로 의미가 분명하면 helper를 쓰지 않는다.
- Hero 설명은 필요할 때만 한 문장으로 제한한다.
- `Python이 생성한 값을 그대로 표시합니다`
- `표시 설정은 저장된 결과를 다시 계산하지 않습니다`
- `정적 JSON을 읽습니다`
- `허용구간 안이므로 방향을 추정하지 않습니다`

위와 같은 구현 설명·반복 중립 사유는 공개 화면에서 제거한다. 필요한 보호 경계는 코드·테스트·이 문서에 둔다.

중립 상태는 `추가 신호 없음`처럼 한 번만 표시한다. 규제·제한·한계는 작은 글씨로 여러 번 남겨 두지 말고 운영 상세 한 곳에 모은다.

문장은 짧고 능동적으로 쓴다. CTA는 누른 뒤 일어날 일을 말한다. 과장, 확정적 투자 표현, 사용자의 이탈을 막는 modal·interruption을 사용하지 않는다.

## 12. Theme·Accessibility·Responsive

- theme storage canonical key: `quant-research-theme`
- 유효한 query → canonical/legacy 저장값 → system preference → light 순서
- 각 프로젝트가 사용하던 모든 legacy key는 읽은 뒤 canonical key로 migration한다. 최소 `quant-dashboard-theme`, `quant-calm-theme`, `dram-price-theme`, `etf-tracking-theme`, `momentum-factor-theme`, `sox-theme`를 포함한다.
- 선택 theme는 `document.documentElement.dataset.theme`와 `color-scheme`에 동기화
- theme toggle은 `aria-pressed`와 현재 동작을 설명하는 동적 accessible label을 유지
- 라이트·다크 모두 본문·축·격자·상태·focus ring 검증
- `prefers-reduced-motion`에서 비필수 motion 제거
- native button, link, input, table semantics 우선
- focus-visible을 색과 outline으로 명확히 표시
- hover에만 의존하는 정보 금지
- chart·icon control에 accessible name 제공
- 색 외 marker·dash·text를 함께 사용
- 브라우저 200% zoom에서도 핵심 control과 값이 잘리지 않게 한다.

필수 viewport:

| 용도 | 크기 |
| --- | --- |
| Desktop | `1440×900` |
| Tablet | `1024×768` |
| Mobile | `390×844` |

`390px`에서 `document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1`이 기본 계약이다. nav, chart, table, 의도된 KPI rail만 자체 스크롤할 수 있다.

## 13. 기존 페이지 개선 절차

1. 최신 `origin/main`, 공개 URL, Pages 상태, 실제 데이터 기준일을 확인한다.
2. 기존 worktree의 사용자 변경을 확인하고 최신 main 기반 전용 branch/worktree를 사용한다.
3. 수정 금지 파일·함수·schema·결과 snapshot을 먼저 기록한다.
4. 공개 화면과 source에서 다음 inventory를 만든다.
   - 8개 메뉴
   - 모든 control의 id·`control_kind`·기본값 출처·validation·serialization
   - `analysis` control의 API/workflow/CLI·Python parameter·result binding·no-op 조건
   - visible copy와 중복
   - computed font-size·weight·line-height
   - spacing·radius·token
   - chart type·series·axis·legend·readout
   - table column·order
   - 긴 페이지의 상단·하단 빠른 이동
   - desktop/mobile scrollWidth·scrollHeight
5. 현재 프로젝트의 좋은 구성은 유지하고 이 문서와 다른 drift만 수정한다.
6. 분석·데이터 테스트와 디자인 회귀 테스트를 실행한다.
7. desktop/tablet/mobile의 light/dark를 확인한다.
8. 사용자에게 local preview를 먼저 제공한다.
9. 배포가 승인되면 commit·PR·CI·Pages·공개 readback까지 확인한다.

기존 페이지를 공통 디자인에 맞춘다는 이유로 한 번에 전체 markup과 CSS를 다시 작성하지 않는다.

## 14. 신규 프로젝트 구현 절차

1. 프로젝트의 가장 중요한 결과·날짜·차트·표·입력을 정의한다.
2. 성격이 가까운 기준 패턴을 선택한다.
   - 가격·보유비중 모니터링: DRAM·ETF
   - 신호·사건·전략 검증: Fear & Greed
   - 팩터·구성종목 비교: Momentum·SOX·Best Factor
   - 사용자 입력 기반 재실행: Momentum·Best Factor
3. 이 문서의 nav·token·typography·spacing·상태·table·chart 계약으로 시작한다.
4. 도메인에 없는 신호·날짜·interaction을 억지로 추가하지 않는다.
5. 새 frontend stack은 기존 분석 계약과 배포 구조를 바꿀 이유가 아니다.
6. framework·UI library 채택은 별도 결정이며 이 디자인 문서의 필수 조건이 아니다.
7. 결과 fixture, 각 `analysis` control의 결정적 A/B fixture, `display` control의 불변 fixture를 먼저 고정하고 UI·worker가 같은 계약을 지키는지 검증한다.
8. desktop/tablet/mobile의 light/dark와 loading·empty·degraded 상태를 확인한다.
9. 사용자에게 local preview와 변경 파일 목록을 제공하고 승인 전에는 배포하지 않는다.
10. 배포가 승인되면 commit·PR·CI·Pages와 공개 asset·데이터 readback을 확인한다.

## 15. 검증 게이트

### 15.1 보호 경계

- 분석·수집·결과 Python 함수, data JSON, 기존 데이터 workflow·schema·analysis module diff가 없어야 한다.
- Python 안의 presentation template은 허용 범위와 동일 결과 fixture 증거를 별도로 제시해야 한다.
- 혼합 JS/TS 파일은 계산 함수 diff가 없어야 한다.
- 같은 입력의 핵심 결과·날짜·정밀도·result identity가 동일해야 한다.
- 같은 fixture의 underlying row·series·point·value가 동일해야 한다. pagination·표시 필터에 따른 visible count 변화는 presentation state로만 허용한다.
- 기존 input→result, URL, API 동작이 동일해야 한다.

### 15.2 입력 → 실행 → 결과

- 모든 control의 `display`·`result_selector`·`analysis`·`operation` registry가 존재해야 한다.
- 모든 `analysis` control은 frontend field → canonical config → API·workflow·CLI → Python parameter mapping이 하나씩 증명되어야 한다.
- 같은 입력의 반복 실행은 핵심 결과가 결정적으로 같아야 한다.
- 각 `analysis` control은 실제 worker argument와 config·run identity를 바꾸고, 영향이 드러나는 결정적 A/B fixture에서 책임지는 결과 경로가 달라져야 한다.
- `display` 변경 전후 config hash·run id·Python command·결과 JSON이 같아야 한다.
- 화면이 `현재 적용`으로 표시하는 요청 config hash·effective config hash·input schema version·data as-of·code version·artifact SHA-256이 실제 결과 binding과 일치해야 한다.
- `requested_inputs`와 `effective_inputs`가 다르면 명시적 fallback 동의 또는 실패 상태가 있어야 한다.
- queued·running·failed·stale·binding mismatch에서 이전 결과를 새 계산 결과처럼 표시하지 않아야 한다.
- 입력 UI만 존재하거나 command 문자열만 생성하고 실제 Python 결과가 바뀌지 않는 상태는 완료가 아니다.

### 15.3 디자인

- 8개 메뉴 label·순서·URL 동일
- 공통 상단 메뉴 안에서 `aria-current="page"` 정확히 1개
- body `15px/1.55` 중심의 compact hierarchy
- 불필요한 `800+` weight 반복 없음
- 접근성 전용 label을 제외한 visible semantic duplicate 0건
- 구현·재계산 설명 0건
- 일반 운영·한계 상세는 닫힌 한 곳
- 현재 사용 불가 warning은 접히지 않음
- table 숫자 정렬·단위·column 보존
- chart readout과 plot·축·끝 라벨 overlap 없음
- 해당 기능이 있는 multi-series chart의 active·muted 계열과 date-axis chart의 날짜 pin·keyboard·touch 동작
- light/dark 및 세 viewport에서 document overflow 없음
- `NaN`, `undefined`, 잘린 label, 빈 tooltip 없음
- loading·empty·degraded·fail-closed 상태와 긴 한글·긴 종목명에서도 잘림·겹침 없음

### 15.4 배포

- local test와 preview 통과
- Vercel Preview는 UI 검수 환경이며 운영 snapshot·분석 성공의 증거로 취급하지 않는다.
- Preview는 검증된 GitHub Pages data origin을 read-only로 사용하고 production 데이터·current pointer를 덮어쓰지 않는다.
- 승인 후 commit·push·PR·CI·Pages 성공
- 공개 HTML·CSS·JS가 배포 대상 main의 UI commit과 일치
- 공개 JSON은 현재 원격 main의 검증된 data commit·schema·기준일과 일치
- 공개 화면에서 기준일·핵심값·interaction을 다시 확인

## 16. 완료 정의

다음이 모두 충족되어야 완료다.

1. 현재 6개 기준 사이트와 같은 제품군으로 보인다.
2. 페이지 고유의 결과 구조·차트·표·의미색은 유지된다.
3. 첫 화면에서 핵심 결과와 기준일을 찾을 수 있다.
4. 메뉴·타이포그래피·색상 역할·간격·상태·접근성이 일관된다.
5. 차트 값이 선·점·축·label을 가리지 않는다.
6. 표는 숫자와 단위를 빠르게 비교할 수 있다.
7. 반복 설명과 구현 문구가 제거된다.
8. mobile·keyboard·light/dark에서 기능이 같다.
9. 분석·결과·데이터와 기존 데이터·분석 자동화 코드는 변경되지 않는다.
10. 배포 요청이 있었다면 공개 페이지까지 검증된다.
11. 모든 `analysis` control이 실제 Python parameter 또는 명시된 권위 engine에 전달되고, 새 config·run identity와 입력 민감도 fixture의 기대 결과 경로를 만든다.
12. `display` control은 분석 identity와 저장 결과를 바꾸지 않는다.
13. 비동기 실행 결과는 요청 config·effective config·input schema·artifact hash와 binding이 일치할 때만 현재 결과로 채택된다.

## 17. Toss 참고 원칙과 사용 제한

Toss 자료에서는 일관된 정보 위계, semantic token, 간결한 문구, 예측 가능한 interaction, 접근성, component 수준의 품질 보장을 참고한다.

다음은 하지 않는다.

- TDS UI Kit, TDS package, Toss logo·icon·graphic·font를 가져오지 않는다.
- Toss 화면·component·신규 color value·motion을 Toss 자료만을 근거로 복제하지 않는다.
- `TDS 기반`, `TDS 호환`이라고 표현하지 않는다.
- 앱인토스 전용 navigation·light-mode 제약을 이 프로젝트군에 적용하지 않는다.

공개 UI Kit 라이선스는 앱인토스 애플리케이션 개발·디자인·prototype으로 사용 범위를 제한하고, 다른 프로젝트에서의 사용·복사·수정·재가공·재배포를 금지한다. 따라서 UI Kit를 사용하지 않으며, 실제 디자인 값과 component의 source of truth는 위 6개 사이트의 현재 구현과 이 문서다. 향후에도 Toss 자료에서 새 값을 직접 가져오지 않는다.

공식 참고자료:

- [TDS Mobile Colors](https://tossmini-docs.toss.im/tds-mobile/foundation/colors/)
- [TDS Typography](https://tossmini-docs.toss.im/tds-react-native/foundation/typography/)
- [TDS BarChart](https://tossmini-docs.toss.im/tds-mobile/components/Chart/bar-chart/)
- [TDS TableRow](https://tossmini-docs.toss.im/tds-mobile/components/table-row/)
- [TDS Tooltip](https://tossmini-docs.toss.im/tds-mobile/components/tooltip/)
- [Apps-in-Toss UI/UX Guide](https://developers-apps-in-toss.toss.im/design/consumer-ux-guide.html)
- [TDS Color System Update](https://toss.tech/article/tds-color-system-update)
- [Figma/TDS Mobile UI Kit License](https://developers-apps-in-toss.toss.im/design/prepare/figma-ui-license.html)

## 18. 복사용 실행 프롬프트

```text
[프로젝트 이름] 웹페이지에 Quant Research 공통 디자인을 적용해줘.

반드시 먼저 로컬 quant-dashboard/docs/web-design.md 또는 공개
https://sonchanggi.github.io/quant-dashboard/docs/web-design.md
전체를 읽고 그 문서를 최우선 디자인 계약으로 사용해.

우선순위
1. Python·분석·결과·데이터·자동화 보호
2. 현재 DRAM, Fear & Greed, ETF Tracking, SOX, Momentum Factor, Best Factor 공개 페이지와의 디자인 통일성
3. web-design.md의 nav·색상·타이포그래피·간격·컴포넌트·표·차트·접근성 계약
4. 현재 프로젝트의 고유 분석 목적과 기존 결과 구조

절대 금지
- 디자인 작업을 이유로 Python 수집·분석·전략·백테스트 계산을 수정
- 계산식·threshold·ranking·weighting·입력→결과 동작 수정
- JSON schema·값·정밀도·날짜 의미·데이터 파일 수정
- 기존 데이터·분석 workflow·Pages URL·API·CLI 계약 수정
- 기존 차트 series·축·단위와 표 column·order 변경

입력·백엔드 작업이 명시적으로 승인된 경우
- 기존 Python 계산 모듈은 그대로 두고 API·worker adapter가 기존 CLI·함수를 호출하게 해.
- 모든 control을 display, result_selector, analysis, operation으로 먼저 분류해.
- analysis control마다 frontend field → canonical config → API/workflow/CLI → Python parameter → result binding mapping을 문서화해.
- applied_config, draft_config, pending_run, bound_result를 분리하고 draft만 바꾼 상태를 공식 결과처럼 보이지 마.
- UI나 command 문자열이 있다는 이유로 완료 처리하지 말고, 각 input이 실제 worker argument와 새 result identity에 도달하며 결정적 A/B fixture의 기대 결과 경로를 바꾸는지 검증해.
- 같은 입력의 결정성, display 격리, requested/effective input 차이, 실패·stale·binding mismatch fail-closed를 함께 테스트해.

진행
1. 최신 origin/main, worktree, 공개 화면, 데이터 계약을 읽기 전용으로 감사해.
2. 수정 금지 파일·함수와 현재 결과 snapshot을 먼저 고정해.
3. 모든 visible control의 mode, 기본값 출처, validation, serialization, 실제 분석 mapping inventory를 만들어.
4. 8개 메뉴, visible copy, typography, spacing, token, chart, table, overflow inventory를 만들어.
5. 현재 프로젝트의 좋은 디자인은 보존하고 6개 기준 사이트와 다른 drift만 수정해.
6. 결과→기준일·핵심 지표→핵심 차트→입력→표·운영 상세 순서로 정리해.
7. 반복 설명, Python·JSON·재계산 구현 문구를 지우고 일반 운영 정보는 운영 상세 한 곳으로 통합해. 결과 해석에 필요한 도메인 방법론은 별도 접힘 영역으로 보존해.
8. 차트 정확값을 plot 밖에 두고, 해당 기능이 있는 차트에서만 선택 계열 강조·날짜·keyboard·mobile 동작을 검증해.
9. 표의 숫자 정렬·단위·내부 스크롤을 개선하되 원본 열과 값을 유지해.
10. 기존 분석·데이터 테스트, 입력 결정성·민감도·격리·binding 테스트와 UI 회귀 테스트를 모두 실행해.
11. 1440×900, 1024×768, 390×844의 light/dark를 확인해.

배포 전에는 local preview URL과 변경 파일 목록을 먼저 제공하고 멈춰.
사용자가 배포를 승인한 경우에만 commit·push·PR·CI·Pages·공개 readback까지 진행해.

완료 보고에는 다음을 분리해서 적어.
- 통일한 디자인
- 보존한 프로젝트 고유 요소
- 제거한 반복 문구
- 분석·결과 코드 무변경 증거
- analysis control별 실제 Python 전달·worker argument·A/B 결과 변화 증거
- display control의 분석 결과 불변 증거
- 요청 config·input schema·artifact hash와 결과 binding 일치 증거
- 테스트와 visual QA 결과
```
