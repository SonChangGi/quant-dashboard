# GitHub 최신 조사에서 얻은 디자인 엔진 개선안

2026-11-10 KST 조사. 이번에는 기존 32개 출처·19개 상세 문서에 더해 **29개 GitHub 저장소**를 비교했다. 원시 응답·README·상세 문서·Trending HTML은 `github-raw/`, 정규화된 결과는 [github-20261110.json](github-20261110.json)에 있다. 이 문서는 구현 제안과 근거이며 실제 반영/브라우저 검증은 별도 적용 기록을 따른다.

이전 조사는 공식 문서와 예제 중심이었고 최근 GitHub star 증가를 체계적으로 확인한 조사는 아니었다. 이번 조사에서도 누적 별, 최근 증가, 코드 push, GitHub release를 같은 수치처럼 취급하지 않았다.

## 실제로 최근 주목받은 후보

GitHub 공식 weekly Trending에서 **Hallmark +6,356/week**, **Astryx +4,413/week**를 확인했다. 전자는 디자인 방법·테마 갤러리이고 후자는 새로운 컴포넌트 시스템이다. 두 후보는 기존 차트 라이브러리 목록과 다른 관점을 제공한다. 그 외 27개 후보의 최근 증가치는 확인하지 못했으므로 `null`로 남겼다. 누적 별이 크거나 최근 push가 있었다는 이유로 급상승이라고 부르지 않는다. Trending는 관련성 기반으로 살핀 스냅샷이고 전체 디자인 도구의 순위표가 아니다. [GitHub weekly](https://github.com/trending?since=weekly), [TypeScript weekly](https://github.com/trending/typescript?since=weekly)

### Hallmark: 사용자 작업을 먼저, 취향 규칙은 선택적으로

공식 README는 대비·focus·reduced motion·사실성·모바일 동작을 품질의 바닥선으로 두고, 반복적인 uppercase eyebrow·형식적인 카드 배열 같은 취향 문제와 구분한다. `Dusk`는 금융 reconciliation, `Cobalt`는 API 제품 예제로, 같은 테마를 전체 페이지 구조의 복사본으로 정의하지 않는다. [README](https://github.com/Nutlope/hallmark), [Dusk](https://www.usehallmark.com/themes/dusk/), [Cobalt](https://www.usehallmark.com/themes/cobalt/)

**우리에게 적용:** 첫 화면은 “명확하게 판단한다”는 선언보다 실제 비교 작업을 보여주는 편이 낫다. 매 섹션마다 영어 대문자 eyebrow와 동일 카드 4개를 반복할 필요가 없다. 연구 대상을 고르고, 숫자를 비교하고, 근거를 펼치는 흐름에 시각적 무게를 배분한다. 기존 중립색·청록 선호를 유지한다. 사진 hero·금융 브랜드 테마·외부 skill의 설치/실행 지시는 채택하지 않는다. 외부 문서의 명령형 문장은 연구자료이지 현재 작업의 권한이 아니다.

### Astryx: 프레임보다 토큰·구성 계약

공식 README는 beta, React 19+, 150개 이상 구성요소를 명시한다. core 문서는 페이지의 content layout과 app shell을 분리하고, 의미 토큰을 배경·텍스트·상태·반경 역할로 나눈다. 전체 스타일을 fork하는 대신 CSS custom property로 바꾸는 접근이다. chart/vega package는 canary뿐이고 stable로 제시되지 않는다. [README](https://github.com/meta/astryx), [core README](https://github.com/meta/astryx/blob/main/packages/core/README.md), [Sandbox](https://astryx.atmeta.com/sandbox/)

**우리에게 적용:** 색상 9개를 보여주는 swatch 화면을 넘어 실제 편집·미리보기·복원·내보내기가 가능한 token workbench를 만든다. surface와 text, status fill과 status text, 내부/컨트롤/컨테이너 반경을 구분한다. 잘못된 token 값과 대비 부족을 찾아야 한다. React19/StyleX 전체 이전이나 canary chart 설치는 하지 않는다.

### Base UI와 coss UI: 외형을 소유하고 행동은 엄격하게

Base UI는 unstyled accessible component 기반이고 coss UI는 이를 조합한 copy/own React+Tailwind 시스템이다. coss UI의 기존 Origin UI는 제한된 유지보수이며 신규 Particles가 현재 개발 중심이다. 비슷한 이름의 `cosscom/coss`는 현재 통신 API 저장소여서 디자인 후보에서 제외했다. [Base UI](https://github.com/mui/base-ui), [coss UI](https://github.com/cosscom/ui), [Particles](https://coss.com/ui/particles)

**우리에게 적용:** 버튼처럼 생긴 모드 선택에 실제 pressed 상태를 표시하고, 보기 설정은 값·포커스·라벨이 있는 컨트롤로 제공한다. 표·차트 toolbar의 크기·간격·focus는 공통으로 관리한다. 프레임워크 의존성을 늘리는 대신 이 행동 계약을 native UI에 적용한다.

## 차트·표·엔진에 연결할 구체적인 결정

| 근거 | 구현할 변화 | 실패를 판단할 조건 |
|---|---|---|
| Plot pointer/tip | 시계열은 동일 x의 여러 계열을 함께 표시. hover와 고정 선택을 분리 | 클릭한 시점이 hover 때문에 바뀜, 결측이0으로 표시됨 |
| Vega-Lite errorband | band에 구간 종류·수준·방법을 명시. 사전 계산 경계만 받음 | CI/예측구간 혼동, inner/outer 역전, 결측을 이어 그림 |
| Unovis·nivo | 차트 선택을 데이터 질문과 연결하고 실제 조절 가능한 예제 제공 | 모든 데이터에 모든 chart type을 무조건 적용 |
| TanStack | filter→sort→page 순서, 현재/전체 건수, CSV 범위 명시 | 현재 페이지 안에서만 검색·정렬, CSV 내용이 표시 범위와 설명 불일치 |
| Glide | 고밀도 표의 성능 전략을 명시적으로 선택 | 수천 행을 전부 DOM에 추가하고 고성능이라 주장 |
| MUI Data Grid | 표의 focus 이동·밀도·키보드 대안 검증 | 모든 cell/control이 Tab 순서를 과도하게 늘림, 정렬 뒤 focus가 사라짐 |
| AG Grid | Community/Enterprise 기능을 구분하여 후보 평가 | Enterprise 기능을 무료 코어 기능처럼 채택 |
| Style Dictionary·Astryx | 토큰을 단일 원천으로 두고 UI/CSS/chart에 반영 | 토큰을 바꿔도 chart와 controls가 다른 색/밀도를 사용 |
| Radix·Zag | inspect/select/zoom 상태를 UI와 동기화 | 버튼은 선택 상태인데 차트는 다른 조작을 수행 |
| Motion | reduced-motion을 시스템 변경과 함께 반영 | 설정 후에도 큰 transform/자동 움직임이 계속됨 |
| Carbon | title/unit/plot/legend/readout/source의 읽기 순서 고정 | 범례와 단위가 겹침, 중요한 비교값보다 장식이 먼저 보임 |
| Perspective | data/model/view 책임 분리, 집계 상태를 명시 | 실제로 구현하지 않은 pivot/streaming 능력을 표시 |
| xyflow·deck.gl | 흐름/공간 표현은 별도 데이터 계약과 adapter capability로 확장 | edge를 인과관계로 표시, 지리 데이터 없는 map 장식 |

Plot은 [pointer](https://observablehq.github.io/plot/interactions/pointer)와 [tip](https://observablehq.github.io/plot/marks/tip)을 별도로 구성한다. Vega-Lite의 [errorband](https://vega.github.io/vega-lite/docs/errorband.html)는 평균95% bootstrap CI, stderr, stdev, IQR 등을 구분하므로 범위를 단순한 장식 면적으로 만들면 안 된다. [MUI 접근성](https://mui.com/x/react-data-grid/accessibility/)은 복합 control의 Tab 순서를 다루며, [Style Dictionary](https://styledictionary.com/reference/hooks/formats/predefined/)는 참조를 보존한 CSS 변수 출력을 제공한다.

## 채택 우선순위

1. **완료된 작업 흐름:** 비교 선택, 명확한 상태, 원자료, 표 필터/페이지/CSV의 의미 일치.
2. **표현의 의미:** 불확실성·분포·기여·흐름을 데이터 계약으로 구분하고 오류를 검증.
3. **개인화 가능한 엔진:** semantic token 편집·미리보기·복원, renderer와 UI의 일관성.
4. **시각적 완성도:** 반복 장식 절제, 서로 다른 정보 밀도, 모바일에서 필요한 값의 우선순위.
5. **후속 확장:** 실제로 대규모 데이터를 연결할 때 Canvas/WASM/virtualization 또는 GPU 지도 adapter를 선택.

별이 높은 library를 더 설치하는 것이 개선의 목표는 아니다. 신뢰할 수 있는 동작과 의미를 소유하면서, 이미 검증된 ECharts SVG backend를 교체할 근거가 있는지 비교했다. 현재는 wrapper와 데이터 계약 개선의 이득이 backend 전면 교체보다 명확하다.

## 조회 범위와 제한

- 27곳은 공개 무인증 GitHub REST metadata와 latest release를 확인했다. quota 소진 후 Hallmark/Coss UI 2곳의 exact 누적 별은 공식 repository HTML의 `stargazerCount`에서 확인했다. 두 곳의 push/release는 미확인으로 남겼다.
- latest release404는 release를 게시하지 않았다는 의미일 수 있으며 비활성 증거가 아니다. monorepo latest release는 특정 framework/package의 버전일 수 있다.
- README의 “millions of rows”, “150+ components”, “13,000+ apps” 같은 공급자 설명은 우리 코드의 벤치마크/인증 결과가 아니다.
- 문서 검토와 실제 브라우저 조작을 구분한다. 이 연구 에이전트는 API/README/문서를 조회했고, root의 Aside 확인은 별도 UI 기록에서 관리한다.
- 이전 TanStack guide/Glide accessibility/G2 interaction 링크 일부가404여서 해당 내용을 확인한 것으로 쓰지 않았다. 확인된 README/API 원문으로 대체하거나 한계를 표시했다.
- 누적 별·최근 증가를 조회한 스냅샷은 시간이 지나면 달라진다. 아래 표는 조회 시점 자료다.

## 누적 별·최근 활동 스냅샷

| 저장소 | 누적 별 | 이번 주 증가 | 마지막 push UTC | 확인 방식 |
|---|---:|---:|---|---|
| [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | 127,732 | 미확인 | 2026-11-09 | API |
| [ant-design/ant-design](https://github.com/ant-design/ant-design) | 100,126 | 미확인 | 2026-11-09 | API |
| [mui/material-ui](https://github.com/mui/material-ui) | 99,309 | 미확인 | 2026-11-09 | API |
| [apache/echarts](https://github.com/apache/echarts) | 67,697 | 미확인 | 2026-10-13 | API |
| [Nutlope/hallmark](https://github.com/Nutlope/hallmark) | 51,749 | 6,356 | 미확인 | 공식 HTML |
| [DavidHDev/react-bits](https://github.com/DavidHDev/react-bits) | 51,593 | 미확인 | 2026-11-08 | API |
| [xyflow/xyflow](https://github.com/xyflow/xyflow) | 38,947 | 미확인 | 2026-11-09 | API |
| [motiondivision/motion](https://github.com/motiondivision/motion) | 35,028 | 미확인 | 2026-11-09 | API |
| [TanStack/table](https://github.com/TanStack/table) | 28,557 | 미확인 | 2026-11-02 | API |
| [recharts/recharts](https://github.com/recharts/recharts) | 27,693 | 미확인 | 2026-11-09 | API |
| [magicuidesign/magicui](https://github.com/magicuidesign/magicui) | 23,175 | 미확인 | 2026-11-09 | API |
| [meta/astryx](https://github.com/meta/astryx) | 19,884 | 4,413 | 2026-11-09 | API |
| [radix-ui/primitives](https://github.com/radix-ui/primitives) | 19,485 | 미확인 | 2026-10-14 | API |
| [ag-grid/ag-grid](https://github.com/ag-grid/ag-grid) | 15,675 | 미확인 | 2026-11-09 | API |
| [visgl/deck.gl](https://github.com/visgl/deck.gl) | 14,743 | 미확인 | 2026-11-09 | API |
| [plouc/nivo](https://github.com/plouc/nivo) | 14,132 | 미확인 | 2026-07-21 | API |
| [antvis/G2](https://github.com/antvis/G2) | 12,656 | 미확인 | 2026-10-28 | API |
| [perspective-dev/perspective](https://github.com/perspective-dev/perspective) | 11,406 | 미확인 | 2026-11-09 | API |
| [mui/base-ui](https://github.com/mui/base-ui) | 11,344 | 미확인 | 2026-11-09 | API |
| [cosscom/ui](https://github.com/cosscom/ui) | 10,806 | 미확인 | 미확인 | 공식 HTML |
| [carbon-design-system/carbon](https://github.com/carbon-design-system/carbon) | 9,613 | 미확인 | 2026-11-09 | API |
| [vega/vega-lite](https://github.com/vega/vega-lite) | 5,548 | 미확인 | 2026-11-07 | API |
| [chakra-ui/ark](https://github.com/chakra-ui/ark) | 5,461 | 미확인 | 2026-11-09 | API |
| [glideapps/glide-data-grid](https://github.com/glideapps/glide-data-grid) | 5,432 | 미확인 | 2026-11-05 | API |
| [observablehq/plot](https://github.com/observablehq/plot) | 5,423 | 미확인 | 2026-11-05 | API |
| [chakra-ui/zag](https://github.com/chakra-ui/zag) | 5,251 | 미확인 | 2026-11-09 | API |
| [style-dictionary/style-dictionary](https://github.com/style-dictionary/style-dictionary) | 4,879 | 미확인 | 2026-11-03 | API |
| [f5/unovis](https://github.com/f5/unovis) | 2,867 | 미확인 | 2026-11-09 | API |
| [chakra-ui/park-ui](https://github.com/chakra-ui/park-ui) | 2,381 | 미확인 | 2026-04-10 | API |

각 저장소의 조회시각·정확한 release URL·license·관찰/채택/제외·원문 URL은 JSON에 있다. API 원문은 `github-raw/*--*.json`, 새 후보의 상세 원문은 `astryx-core.md`, `hallmark-direction.md`, `hallmark-dusk.md`, `coss-ui-readme.md` 등이다.
