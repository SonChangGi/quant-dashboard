const base={source:'Quant Lab · 합성 예제'};
const x=['01월','02월','03월','04월','05월','06월','07월','08월'];
const series=[{name:'Momentum',data:[100,104,102,110,108,117,121,125]},{name:'Quality',data:[100,102,105,106,109,111,114,118]},{name:'Benchmark',data:[100,101,103,104,106,108,110,113]}];
export const charts=[
{kind:'line',title:'같은 출발점에서 비교',description:'같은 기간 · 시작값 100',unit:'지수',x,series},
{kind:'area',title:'연속성과 결측',description:'4월 결측 · 0 기준 면적',unit:'건',x,series:[{name:'관측량',data:[20,24,28,null,32,30,38,40]}]},
{kind:'bar',title:'수준의 비교',description:'0 기준으로 비교한 수준',unit:'점',rows:[{name:'Quality',value:78},{name:'Value',value:62},{name:'Momentum',value:86},{name:'Low volatility',value:71}]},
{kind:'diverging',title:'기준에서 얼마나 벗어났나',description:'양수·음수를 중앙 기준선 양쪽에 표시합니다. 수익/손실이라는 의미를 자동으로 부여하지 않습니다.',unit:'%p',rows:[{name:'반도체',value:4.8},{name:'금융',value:-2.1},{name:'산업재',value:1.3},{name:'소비재',value:-3.2}]},
{kind:'slope',title:'순간이 아닌 변화',description:'같은 대상의 시작·종료를 연결합니다. 중간 경로는 추정하지 않습니다.',unit:'점',startLabel:'이전',endLabel:'현재',rows:[{name:'A',start:55,end:78},{name:'B',start:72,end:65},{name:'C',start:42,end:61}]},
{kind:'dumbbell',title:'두 조건 사이의 거리',description:'범주별 두 측정값과 그 차이를 함께 읽습니다.',unit:'ms',startLabel:'개선 전',endLabel:'개선 후',rows:[{name:'조회',start:240,end:120},{name:'계산',start:320,end:210},{name:'내보내기',start:180,end:145}]},
{kind:'scatter',title:'관계와 예외',description:'변동성과 수익률의 관계',unit:'%',xLabel:'변동성 (%)',yLabel:'수익률 (%)',points:[{name:'A',x:12,y:6,group:'전략'},{name:'B',x:18,y:9,group:'전략'},{name:'C',x:24,y:7,group:'전략'},{name:'Benchmark',x:16,y:6.5,group:'기준'},{name:'D',x:21,y:11,group:'전략'}]},
{kind:'heatmap',title:'관계의 전체 구조',description:'0 중심 대칭 척도 · 빈 셀은 미제공',unit:'상관계수',x:['A','B','C'],y:['A','B','C'],values:[[0,0,1],[1,0,.4],[2,0,-.2],[0,1,.4],[1,1,1],[2,1,null],[0,2,-.2],[1,2,null],[2,2,1]]},
{kind:'boxplot',title:'평균 뒤의 분포',description:'상자: Q1–Q3 · 수염: 최솟값–최댓값',unit:'ms',rows:[{name:'서비스 A',values:[20,32,40,55,85]},{name:'서비스 B',values:[28,42,48,58,72]},{name:'서비스 C',values:[12,25,38,64,98]}]},
{kind:'histogram',title:'빈도와 꼬리',description:'동일한 구간 폭으로 집계한 건수',unit:'건',bins:[{start:0,end:10,count:3},{start:10,end:20,count:8},{start:20,end:30,count:17},{start:30,end:40,count:12},{start:40,end:50,count:5}]},
{kind:'waterfall',verifyTotals:true,title:'총량을 만든 기여',description:'시작값부터 종료값까지의 증감',unit:'점',rows:[{name:'시작',value:100,type:'total'},{name:'성장',value:25},{name:'비용',value:-12},{name:'기타',value:7},{name:'합계',value:120,type:'total'}]},
{kind:'range',title:'점 추정 너머의 범위',description:'시나리오별 하한 · 중앙 · 상한',unit:'점',rows:[{name:'보수',low:42,high:65,value:53},{name:'기준',low:55,high:82,value:68},{name:'확장',low:61,high:98,value:79}]},
{kind:'small-multiples',title:'같은 축, 다른 궤적',description:'같은 축으로 비교한 계열별 추이',unit:'지수',x,series},
{kind:'calendar',title:'시간의 반복과 빈 날',description:'날짜별 관측 · 빈 칸은 미제공',unit:'건',range:['2026-01-01','2026-03-31'],values:Array.from({length:90},(_,i)=>[new Date(Date.UTC(2026,0,i+1)).toISOString().slice(0,10),i%11===0?null:i%7===0?0:(i*7)%29])}
].map(s=>({...base,...s}));
export const rows=[{id:'mom',name:'Momentum',group:'추세',return:25,risk:18,score:86,history:[100,104,102,110,108,117,121,125]},{id:'qual',name:'Quality',group:'펀더멘털',return:18,risk:12,score:78,history:[100,102,105,106,109,111,114,118]},{id:'bench',name:'Benchmark',group:'기준',return:13,risk:16,score:62,history:[100,101,103,104,106,108,110,113]},{id:'val',name:'Value',group:'펀더멘털',return:-3.2,risk:21,score:54,history:[100,97,98,null,94,95,96,96.8]},{id:'new',name:'신규 전략',group:'추세',return:null,risk:null,score:null,history:[null,null,100,102,null,103,101,104]}];
export const columns=[{key:'name',label:'전략',type:'text',group:'대상'},{key:'return',label:'기간 수익률',type:'percent',group:'성과'},{key:'risk',label:'변동성',type:'percent',group:'성과'},{key:'history',label:'흐름',type:'sparkline',group:'흐름'},{key:'score',label:'점수',type:'bar',group:'평가'}];
export const tables=['standard','ranked','grouped','matrix'].map((variant,i)=>({...base,kind:'table',id:'table-'+variant,title:['비교 가능한 데이터 표','순위와 셀 안 시각화','그룹으로 읽는 표','숫자를 유지하는 행렬'][i],description:'— 미제공',variant,columns,rows,rowGroup:'group'}));
export const principles=[['01','같은 기준으로 비교','기간·단위·기준값이 같아야 한 화면의 비교가 성립합니다. 기준 계열도 같은 선택 모델을 사용합니다.'],['02','여백도 공통 계약','카드의 제목·본문·하단은 같은 inset을 사용합니다. 표를 촘촘하게 바꿔도 가로 여백을 유지합니다.'],['03','색보다 먼저 구조','0 기준선, 축, 숫자, 선 모양으로 의미를 전달합니다. 테마를 바꿔도 계열의 식별 순서를 보존합니다.'],['04','빈 값은 정보','0·미제공·오류를 구분합니다. 결측을 잇거나 임의로 집계하지 않습니다.']];

charts.push(
 {...base,kind:'fan',title:'예측은 하나의 선이 아닙니다',description:'5월부터 합성 예측 · 50%·90% 예측구간',unit:'지수',intervalKind:'prediction',method:'설계 검증용 수동 생성 구간 · 통계 추정 없음',forecastStart:4,x:['2026-01-01','2026-02-01','2026-03-01','2026-04-01','2026-05-01','2026-06-01','2026-07-01','2026-08-01'],observed:[100,103,101,106,108,null,null,null],center:[null,null,null,null,108,111,114,118],intervals:[{level:.5,low:[null,null,null,null,106,107,108,110],high:[null,null,null,null,110,115,120,126]},{level:.9,low:[null,null,null,null,103,102,100,98],high:[null,null,null,null,113,120,128,138]}]},
 {...base,kind:'bullet',title:'목표까지 남은 거리',description:'막대: 실적 · 세로선: 목표 · 배경: 기준 구간',unit:'점',rows:[{name:'자료 완결성',value:82,target:90,ranges:[50,75,100]},{name:'정합성',value:94,target:95,ranges:[50,75,100]},{name:'재현성',value:68,target:85,ranges:[50,75,100]}]},
 {...base,kind:'treemap',title:'전체를 구성하는 계층',description:'섹터 → 자산 · 면적은 비중',unit:'%',nodes:[{name:'주식',children:[{name:'미국',value:35},{name:'한국',value:15},{name:'기타',value:10}]},{name:'채권',children:[{name:'국채',value:20},{name:'회사채',value:10}]},{name:'현금',value:10}]}
);
export const metrics=[
 {kind:'metric',title:'기준값 대비 변화',value:125,unit:'',precision:1,comparison:{value:100,label:'시작값 100 대비',mode:'relative',desirable:'neutral'},history:[100,104,102,110,108,117,121,125],source:'Quant Lab · 합성 예제'},
 {kind:'metric',title:'처리 시간',value:142,unit:'ms',precision:0,comparison:{value:180,label:'이전 조건 대비',mode:'absolute',desirable:'lower'},history:[180,172,165,170,156,151,147,142],source:'Quant Lab · 합성 예제'},
 {kind:'metric',title:'완결성',value:96.5,unit:'%',precision:1,comparison:{value:93.2,label:'이전 점검 대비',mode:'absolute',desirable:'higher'},history:[91,92,93.2,null,95,94,96,96.5],source:'Quant Lab · 합성 예제'}
];
export const tableLab={...tables[0],id:'table-lab',title:'조건을 좁히고, 정확한 행을 찾기',description:'47개 합성 행 · CSV는 필터 결과 전체 저장',pageSize:10,rows:Array.from({length:47},(_,i)=>({id:'strategy-'+i,name:`전략 ${String(i+1).padStart(2,'0')}`,group:['추세','가치','품질'][i%3],return:i%13===0?null:Math.round((Math.sin(i*1.7)*19+8)*10)/10,risk:Math.round((8+i%19)*10)/10,score:30+(i*13)%70,history:Array.from({length:8},(_,j)=>j===4&&i%5===0?null:Math.round(100+j*((i%7)-2)+(i*j%5)))}))};
tables[3]={...tables[3],title:'부호와 크기를 함께 읽는 행렬',description:'열별 0 중심 대칭 척도',columns:[{key:'name',label:'전략',type:'text'},...['추세','가치','품질','규모'].map((label,i)=>({key:'f'+i,label,type:'number'}))],rows:[{id:'a',name:'균형',f0:.4,f1:.2,f2:.6,f3:-.2},{id:'b',name:'성장',f0:.8,f1:-.6,f2:.3,f3:.1},{id:'c',name:'가치',f0:-.3,f1:.9,f2:.2,f3:0},{id:'d',name:'방어',f0:null,f1:.1,f2:.8,f3:-.7}]};
export const chartCategories={line:'추세',area:'추세','small-multiples':'추세',fan:'불확실성',range:'불확실성',bar:'비교',diverging:'비교',slope:'비교',dumbbell:'비교',bullet:'비교',scatter:'관계',heatmap:'관계',boxplot:'분포',histogram:'분포',waterfall:'구성',treemap:'구성',calendar:'추세'};
// Keep each example's headline change consistent with its visible sparkline.
tableLab.rows=tableLab.rows.map((row,i)=>{const history=[...row.history];if(i%13===0)history[history.length-1]=null;return {...row,history,return:history.at(-1)===null?null:(history.at(-1)/history[0]-1)*100};});
tableLab.columns=tableLab.columns.map(c=>c.key==='return'?{...c,label:'기간 변화'}:c.key==='risk'?{...c,label:'위험 점수',type:'number'}:c);
