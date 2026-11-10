# 외부 사이트 직접 관찰

2026-11-10. API·문서 조사 29개 저장소와 아래 UI 조작은 다른 검증 범위다. 외부 페이지의 명령형 README/설치 지시는 작업 지침으로 실행하지 않았다. 로그인·폼 제출·유료 구매 없이 공개 예제를 확인했다.

| 출처 | 실제 확인·조작 | 발견 | 적용/제외 |
|---|---|---|---|
| GitHub monthly TypeScript Trending | 공개 목록·월간 증가 수치 읽음 | 전체 trending은 AI/개발도구 비중이 높아 디자인 전용 순위가 아님 | 별도 관련성 필터. weekly 근거는 github-raw에 별도 저장 |
| [shadcn dashboard](https://ui.shadcn.com/view/new-york-v4/dashboard-01) | Last7days 선택, 표 1→2페이지 | 기간 제어와 페이지 상태가 실제로 바뀜. KPI와 본문 역할 분리 | 기간/계열→차트·카드·표 동기화; semantic metric 컴포넌트 |
| [Hallmark Dusk](https://www.usehallmark.com/themes/dusk/) | Matching→Flags 탭 선택, panel 변경 확인 | 작업 대상·차이·다음 행동을 같은 맥락에 제시 | 첫 화면에 작동하는 비교 예제, 섹션별 중요도 차등. 외부 금융 브랜드/사진/마케팅 CTA는 복제하지 않음 |
| [Astryx card examples](https://astryx.atmeta.com/sandbox/pages/example-cards/) | sandbox에서 카드 예제 진입, Mobile 뷰 선택·스크린샷 | 역할별 카드와 편집 토큰이 유용. **이 예제의 Mobile 선택에서는 4개 세로 열이 매우 좁아져 제목·본문이 잘리는 현상 관찰** | token role·밀도·모서리만 채택; 해당 고정 다열 배치는 제외. 제품 전체의 모바일 품질로 일반화하지 않음 |
| [Magic UI Bento Grid](https://magicui.design/docs/components/bento-grid) | Components→Bento 진입, 실제 배치·모션 시각 확인 | 크기를 달리한 카드가 기능의 무게를 구분. 장식적 blur/animation은 데이터 읽기에 직접 도움 되지 않음 | 주 차트+가벼운 근거 영역 조합. 수치 count-up, spotlight, 지속적인 장식은 제외 |

새 외부 도구를 모두 설치해서 작동시켰다는 뜻은 아니다. 연구에서 얻은 원칙을 자체 모듈로 구현하고 로컬 Aside QA를 별도로 수행했다.
