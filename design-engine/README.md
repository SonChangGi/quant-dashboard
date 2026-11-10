# Quant Design Engine · v0.4.2

개인 연구 웹페이지의 공통 디자인 엔진과 작동하는 예제.

[로컬 미리보기](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2) · [리서치 적용 현황](https://sonchanggi.github.io/quant-dashboard/design-engine/?v=0.4.2#research) · [운영 적용 기록](RELEASE.md)

```sh
cd quant-design-engine
npm run dev
```

- 차트17종, 카드·표·상태 예제, 토큰 편집, 스펙 스튜디오
- 기간·범례·계열·요약·표를 연결한 비교 화면
- 원문 → 공통 규칙 → 예제를 연결한12개 핵심 적용 항목
- 상시 도구를 줄이고 직접 조작과 상황별 동작을 제공

## 문서와 재사용

[공통 지침](DESIGN-GUIDELINES.md), [리서치 적용표](research/APPLIED.md), [API](API.md), [검증](QA.md).

`engine/`과`vendor/`를 함께 사용하거나 `quant-design-engine-0.4.2.tgz`를 로컬 패키지로 사용한다. `demo/consumer.html`은 같은 모듈의 독립 예제다.

```js
import {createEngine} from './engine/index.js';
const engine = createEngine(root, {theme:'dark', echarts});
const view = engine.mount(host, spec);
view.update(nextSpec);
engine.configure({density:'compact'});
engine.setTheme('light');
view.destroy();
```

`npm test` / `npm run check`. 예제 데이터는 합성이다. 차트 런타임은 ECharts6.1.0 SVG이며 소스·폰트·라이선스는 로컬에 포함한다.
