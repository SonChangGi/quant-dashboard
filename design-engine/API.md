# API · v0.4.1

## 공통

`createEngine(root,{theme:'dark'|'light',echarts})` → `mount`, `setTheme`, `getTheme`, `destroy`.
`mount(host,spec,{onSelect,onRange,onRetry})` → `update`, `getState`, `destroy`, `element`, `renderer`.
root 내부 host에 mount한다. title은 필수. source,description,unit은 표시용. 입력은 복사하고 update 전에 검증한다. kind 변경은 destroy 후 새 mount. theme은 root에만 적용한다. 여러 root를 두면 각각 다르게 설정할 수 있다. 전체 destroy는 소유한 mount만 제거한다.

## 차트 spec

정확한 타입은 `engine/index.d.ts`; 실행 예시는 `demo/fixtures.js`.

| kind | 데이터 | 규칙 |
|---|---|---|
| line / area / small-multiples | x, series[{name,data}] | 길이 일치, 고유 이름·x, null 허용. 결측 연결 없음 |
| bar / diverging | rows[{name,value}] | 0 기준 막대 / 대칭 발산 축 |
| slope / dumbbell | rows[{name,start,end}] | 명시적인 두 조건; startLabel,endLabel |
| scatter | points[{name,x,y,group?}] | 유한한 x,y; 그룹별 계열 |
| heatmap | x,y,values[[xIndex,yIndex,value]] | null 생략, 기본 대칭 색 범위 |
| boxplot | rows[{name,values:[min,q1,median,q3,max]}] | 순서 검사; 통계 자동 계산 없음 |
| histogram | bins[{start,end,count}] | 동일 폭, 비중첩, 정수 빈도; 자동 bin 없음 |
| waterfall | rows[{name,value,type:'delta'|'total'}],initial | total은 절대값. initial 생략 시 첫 total이 시작값. 명시한 initial은 첫 total과 일치해야 함. verifyTotals:true이면 중간/최종 total의 합산 일치 검사 |
| range | rows[{name,low,high,value?}] | low≤value≤high. 범위의 의미는 설명에 명시 |
| calendar | values[[date,value]],range | YYYY-MM-DD 검증. 날짜 중복·범위 이탈 거절 |

차트 renderer는 `select(index|null)`, `setRange(start,end)`, `setLegend(name,visible)`, `setMode('inspect'|'select'|'zoom')`, `setZoom(startPercent,endPercent)`, `resetView()`를 지원한다. 시계열 방향키/Home/End=선택, Shift+방향키=구간, Escape=해제. 기본 inspect는 차트 안 휠 확대와 드래그 이동을 지원한다. 선택·확대·범례는 테마 변경 중 보존한다. resetView는 전체 계열과 범위를 복원한다.

onSelect는 시계열에서 `{index,x,series:[{name,value}]}`, 표에서 원본 행의 복사본, 해제에서 null. onRange는 `{startIndex,endIndex,start,end}` 또는 null. 산점도 등 비시계열은 tooltip과 원자료 표를 제공하며 시계열 선택 이벤트를 보장하지 않는다.

## 표

kind:'table', columns:[{key,label,type,unit?,group?}], rows:[{id,...}], variant:'standard'|'ranked'|'grouped'|'matrix', rowGroup?:key.

type=text/number/percent/sparkline/bar. percent는 **12.5를 12.5%로 표시**한다(0.125 자동 변환 없음). sparkline은 숫자/null 배열. 숫자 정렬은 유한한 숫자만 사용하며 null은 양방향 정렬 모두 마지막. CSV 텍스트 수식 방지, raw 음수 숫자 보존. 행 수가 매우 큰 경우 가상 스크롤 adapter 필요.

## 상태

kind:'status', state:'loading'|'empty'|'error'. error는 onRetry가 있을 때 실제 버튼 표시. 데이터 요청/취소 자체는 소비자의 책임이다. 렌더링 코어가 네트워크를 소유하지 않는다.

## React / Python 연결 경계

React에서는 ref와 effect에서 mount하고 cleanup에서 destroy, 별도 effect에서 update한다. 이 버전은 React wrapper를 패키지로 제공하지 않는다. Python은 같은 spec을 JSON 파일로 저장하고 HTML이 이를 fetch하여 mount한다. 계산은 기존 Python 계층에 남긴다. 검증 완료된 독립 HTML 소비자는 demo/consumer.html이다.

## 카드·표·토큰 계약

### 개인화 토큰

`createEngine(root,{theme,echarts,design})`, `engine.configure(partialDesign)`, `engine.getDesign()`.
`design`은 density=`comfortable|compact`, corners=`soft|square`, accent=`cyan|blue|violet`.
변경은 해당 root의 CSS 변수와 chart palette에만 반영한다. theme 변경에도 config/선택 상태를 보존한다. 지원하지 않는 값은 기존 설정을 변경하기 전에 거절한다. `contrastRatio('#rrggbb','#rrggbb')`는 sRGB WCAG2 대비값이다. 현재 모든 palette의 text/muted/accent와 surface 대비를 검사한다. 전체 접근성 인증은 아니다.

### metric

`{kind:'metric',title,value:number|null,unit?,precision?:0..6,history?:(number|null)[],comparison?:{value,label,mode:'absolute'|'relative',desirable:'higher'|'lower'|'neutral'}}`.
absolute는 value−comparison.value. unit='%'이면 변화 단위는 %p. relative는 양수 기준 대비 변화율이며 기준0은 계산 불가, 음수 기준은 거절한다. 좋아지는 방향을 명시하므로 감소가 개선일 수 있다. null은—, history null은 gap. `metricChange(spec)`는 pure 결과를 제공한다.

### 비교 변환

`rebaseComparison(spec,startIndex,endIndex,base=100)`.
같은 x 배열의 모든 계열을 같은 startIndex에서 환산한다. 각 시작값은 유한한 양수여야 하며, 시작일이 결측인 계열만 다른 날짜로 이동시키지 않는다. 2개 이상 관측이 필요하다. 중간/종료 null은 유지한다. 이 함수는 통화·배당·거래비용 동등성을 자동 검사하지 않는다. 비교 페이지의 기간 변화는 종료 기준값−100이며 연환산 수익률이 아니다.

### 새로운 차트

- **fan**: `x:YYYY-MM-DD[]`, `observed`, `center`, `forecastStart:index`, `intervalKind:'prediction'|'confidence'|'scenario'`, `method:string`, `intervals:[{level:0..1,low,high}]`. 날짜 오름차순, 시계열 길이, 경계 전후 null, 중앙값 포함, 중첩 범위를 검증한다. 자동 추정 없음. axis tooltip/원자료 표 제공; 시계열 선택 API는 이 kind에서 제공하지 않는다.
- **bullet**: `rows:[{name,value>=0,target>=0,ranges:[r1,r2,r3]}]`. 세 양수 경계는 증가하고 실적/목표가 최댓값 안에 있어야 한다. 행 전체 공통0축.
- **treemap**: `nodes:[{name,value?,children?}]`. 잎 value는 비음수. 자식이 있으면 optional value는 자식합과 일치. 순환/중복 형제명/깊이32 초과/전체0은 거절. 비교 레이아웃이 클릭으로 바뀌지 않도록 drill 동작을 사용하지 않는다.

### 표 강화

`pageSize` 기본20, 허용1..500. `rankBy` 숫자 열 key, `rankDirection:'asc'|'desc'` 기본desc. ranked는 전체 입력의 안정 순위(동률1·1·3)를 표시하며 필터/정렬로 다시 매기지 않는다.
숫자 범위는 하한/상한 포함. 잘못된 범위는 이전 조건 유지. search→numericFilter→sort→page 순서. CSV는 현재 페이지가 아니라 필터/정렬된 전체 행과 표시 열을 내보낸다. sparkline/막대/matrix의 척도는 현재 페이지가 아닌 전체 입력 열 기준. 배열 위치는 category order이며 실제 날짜 간격으로 해석하지 않는다.
`getState`는 기존 필드 외 `pageIndex,pageSize,pageRowIds,numericFilter` 제공.


## 직접 조작 기본값

line/area는 기본적으로 값 읽기와 inside 확대·이동을 함께 제공한다. 상시 모드 버튼과 슬라이더는 표시하지 않는다. `zoom:false`는 확대를 끈다. `brush:true`와 `onRange`가 함께 있을 때만 옵션에 구간 선택을 표시한다. `renderer.resetZoom()`은 범위만 복원하며 계열·관측 선택은 유지한다. 기존 `resetView()`는 전체 상태 복원 API로 유지한다. `setMode('inspect')`는 이제 값 읽기와 기본 확대·이동이 함께 가능한 상태다.

## 범례 연결

`engine.mount(host, spec, {onLegendChange(visible) {}})`는 사용자 범례 변경 시 계열명→표시 여부를 전달한다. 비교 예제는 이 이벤트로 체크박스·카드·표를 갱신하며 차트는 재생성하지 않는다. `renderer.setLegend(name, visible)`는 다른 입력에서 범례를 제어한다.
