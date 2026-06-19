# Quant Dashboard

`https://sonchanggi.github.io/quant-dashboard/`용 통합 정적 리서치 허브입니다.

## 목적

- 모멘텀 팩터 랩, D램(DRAM) 가격 랩, Best Factor Lab, ETF TOP10 Tracking, 기업 가치평가 Lab을 한 화면에서 요약합니다.
- 각 프로젝트 카드의 버튼으로 원본 GitHub Pages 페이지를 바로 엽니다.
- 공개 배포 JSON만 best-effort로 읽되, 명시한 schema/contract version과 필수 key가 맞지 않으면 fallback/준비중 상태를 보여줍니다.
- 리서치 브리핑, 관심 티커 연결, 데이터 상태 패널로 “오늘 무엇을 확인할지”를 먼저 보여줍니다.

## 데이터 경계

이 저장소는 다른 프로젝트의 로컬 소스 코드를 직접 import하지 않습니다. 런타임에서 읽는 값은 아래 공개 URL뿐입니다.

- `https://sonchanggi.github.io/momentum-factor-lab/data/dashboard.json`
- `https://sonchanggi.github.io/dram-price/data/prices.json`
- `https://sonchanggi.github.io/dram-price/data/series.json`
- `https://sonchanggi.github.io/dram-price/data/status.json`
- `https://sonchanggi.github.io/best-factor/data/latest-results.json`
- `https://sonchanggi.github.io/etf-tracking/data/dashboard.json`
- `https://sonchanggi.github.io/valuation/data/index.json`

공개 JSON 구조가 바뀌거나 네트워크가 실패하면 대시보드는 마지막 확인 스냅샷 또는 오류 상태를 보여주고, 원본 페이지 링크는 계속 유지합니다. 중앙 허브의 숫자는 투자 결론이 아니라 원본 프로젝트의 방법론, 가격 기준일, 데이터 품질, 한계를 확인하기 위한 출발점입니다.

## 로컬 실행

정적 파일이므로 별도 빌드가 필요 없습니다.

```bash
python3 -m http.server 8080
# http://localhost:8080 열기
```

## 검증

```bash
npm test
npm run test:live  # 공개 GitHub Pages JSON 계약을 네트워크로 확인할 때만 실행
```

검증은 Node 내장 기능만 사용하며 다음을 확인합니다.

- 다섯 프로젝트 원본 링크 존재
- 가치평가 프로젝트 링크와 데이터 endpoint 존재
- 공개 JSON endpoint 상수 존재
- Momentum / D램(DRAM) / Best Factor / ETF Tracking / Valuation parser와 fallback 존재
- freshness/status 표시 hook 존재
- Research Cockpit, Watchlist, Data Health hook 존재
- 선택형 live contract smoke로 공개 JSON row 수, schema/contract version, 최신성, payload 크기 확인
- 투자 조언이 아니라는 disclaimer 존재
- sibling 프로젝트 로컬 경로를 참조하지 않음

## 주의

본 페이지는 개인 리서치와 프로젝트 허브를 위한 화면이며 투자, 세무, 법률 또는 매매 조언이 아닙니다.
