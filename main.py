import json
import math
from datetime import date, timedelta

import FinanceDataReader as fdr
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

CODE, NAME = "005930", "삼성전자"


@app.get("/", response_class=HTMLResponse)
def read_home():
    return PAGE


@app.get("/samsung")
def samsung():
    # shortcut: 요청마다 새로 조회함, 트래픽이 늘면 일 단위 캐시 추가
    try:
        df = fdr.DataReader(CODE, date.today() - timedelta(days=730))
    except Exception as e:
        raise HTTPException(502, f"주가 데이터 조회 실패: {e}")
    if len(df) < 2:
        raise HTTPException(502, "주가 데이터가 비어 있습니다")

    c = df["Close"]
    for n in (5, 20, 60, 120):
        df[f"MA{n}"] = c.rolling(n).mean()
    d = c.diff()  # RSI: Wilder 평활
    gain = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI14"] = 100 - 100 / (1 + gain / loss)
    df["MACD"] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    std20 = c.rolling(20).std()
    df["BB_Upper"] = df["MA20"] + 2 * std20
    df["BB_Lower"] = df["MA20"] - 2 * std20
    df["Change"] *= 100  # 비율 → %

    year = df.tail(252)
    summary = {
        "change": float(c.iloc[-1] - c.iloc[-2]),
        "high_52w": float(year["High"].max()),
        "low_52w": float(year["Low"].min()),
        "avg_volume_20": round(float(df["Volume"].tail(20).mean())),
        "volatility_20": round(float(c.pct_change().tail(20).std() * math.sqrt(252) * 100), 2),
    }
    df.index = df.index.strftime("%Y-%m-%d")
    # to_json이 NaN → null, numpy 타입 → 기본 타입 변환을 한 번에 처리
    rows = json.loads(df.round(2).reset_index(names="Date").to_json(orient="records"))
    return {"code": CODE, "name": NAME, "updated": rows[-1]["Date"], "summary": summary, "data": rows}


PAGE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>삼성전자 · 005930</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js" integrity="sha384-JZigAjwiaZtkUbA44CWkPaT3iBb/mU5pO6QOANp+OqHd4q+1+7MG1kzp2OOP9ZfP" crossorigin="anonymous"></script>
<style>
/* 상승 빨강 · 하락 파랑(국내 관례), 강조는 앰버 — 방향색과 겹치지 않게 */
:root{--bg:#0f1115;--fg:#eceef1;--dim:#9aa1ab;--line:#262a33;--up:#f04452;--dn:#3d8bfd;--ac:#f5b942;
  --f:'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;--ease:cubic-bezier(.16,1,.3,1)}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--bg)}
body{background:var(--bg);color:var(--fg);font:400 15px/1.6 var(--f);font-feature-settings:'tnum';letter-spacing:-.01em;overflow-x:hidden;-webkit-font-smoothing:antialiased}
::selection{background:var(--ac);color:var(--bg)}
.up{color:var(--up)}
.dn{color:var(--dn)}
a{color:inherit}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
:focus-visible{outline:2px solid var(--ac);outline-offset:3px}

.grain{position:fixed;inset:-50%;width:200%;height:200%;pointer-events:none;z-index:90;opacity:.035;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  animation:grain 1.2s steps(5) infinite}
@keyframes grain{0%{transform:translate(0,0)}25%{transform:translate(-3%,2%)}50%{transform:translate(2%,-4%)}75%{transform:translate(-2%,3%)}100%{transform:translate(3%,1%)}}

.loader{position:fixed;top:0;left:0;height:2px;width:0;background:var(--ac);z-index:100;animation:load 2.4s var(--ease) forwards}
body.ready .loader{width:100%!important;opacity:0;transition:width .4s,opacity .6s .4s}
@keyframes load{to{width:72%}}

.wrap{max-width:1320px;margin:0 auto;padding:0 40px}
.top{display:flex;justify-content:space-between;gap:16px;padding:20px 0;font:500 13px var(--f);color:var(--dim);border-bottom:1px solid var(--line)}
.top a{text-decoration:none;color:var(--fg);border-bottom:1px solid var(--ac)}
.top a:hover{color:var(--ac)}

.ticker{overflow:hidden;border-bottom:1px solid var(--line);white-space:nowrap;font:500 13px var(--f);padding:11px 0;mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent)}
.track{display:inline-block;animation:marquee 60s linear infinite}
.track span{margin-right:36px;color:var(--dim)}
.track b{font-weight:600;margin-left:8px}
@keyframes marquee{to{transform:translateX(-50%)}}

.reveal{opacity:0;transform:translateY(28px);transition:opacity 1.1s var(--ease),transform 1.1s var(--ease);transition-delay:calc(var(--d,0)*120ms)}
body.ready .reveal{opacity:1;transform:none}

.hero{display:grid;grid-template-columns:1.3fr 1fr;align-items:end;gap:40px;padding:72px 0 40px}
.idx{font:700 12px var(--f);color:var(--ac);letter-spacing:.06em}
h1{font:800 clamp(56px,9vw,128px)/1 var(--f);letter-spacing:-.05em;margin-top:16px}
.en{font:500 clamp(16px,1.6vw,20px) var(--f);color:var(--dim);margin-top:12px}
.price{text-align:right}
.big{font:700 clamp(44px,6.4vw,92px)/1 var(--f);letter-spacing:-.045em;margin-top:6px}
.big small{font-size:.28em;font-weight:500;color:var(--dim);margin-left:8px;letter-spacing:0}
#chg{font:700 20px var(--f);margin-top:14px;display:flex;justify-content:flex-end;gap:14px}
.rule{height:1px;background:var(--ac);transform:scaleX(0);transform-origin:left;transition:transform 1.6s var(--ease) .3s}
body.ready .rule{transform:scaleX(1)}

.ohlc{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}
.cell{padding:22px 0 22px 20px;border-left:1px solid var(--line)}
.cell:first-child{border-left:0;padding-left:0}
.lbl{font:500 13px var(--f);color:var(--dim)}
.val{font:600 24px var(--f);margin-top:4px;letter-spacing:-.02em}

.sec{padding:56px 0 0}
.sechead{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
.sechead h2{font:700 clamp(24px,2.6vw,32px) var(--f);letter-spacing:-.035em}
.sechead h2 .idx{margin-right:12px;vertical-align:middle}
.ranges{display:flex;gap:4px;background:#171a21;padding:4px;border-radius:10px}
.ranges button{font:600 13px var(--f);padding:7px 14px;border-radius:7px;color:var(--dim);transition:color .3s,background .3s}
.ranges button:hover{color:var(--fg)}
.ranges button[aria-pressed=true]{background:var(--fg);color:var(--bg)}
.readout{font:500 13px var(--f);color:var(--dim);display:flex;flex-wrap:wrap;gap:6px 18px;min-height:20px;margin-bottom:10px}
.readout b{font-weight:600;color:var(--fg)}
.legend{display:flex;flex-wrap:wrap;gap:18px;font:500 13px var(--f);color:var(--dim);margin-top:12px}
.legend i{display:inline-block;width:16px;height:2px;border-radius:1px;vertical-align:middle;margin-right:6px}
.chart{height:460px;width:100%}

.stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.stat{padding:28px 24px 30px;border-left:1px solid var(--line);min-height:220px;display:flex;flex-direction:column;justify-content:space-between}
.stat:first-child{border-left:0;padding-left:0}
.stat .num{font:700 40px/1 var(--f);letter-spacing:-.04em;margin-top:12px}
.stat .num small{font-size:15px;font-weight:500;color:var(--dim);margin-left:4px}
.note{font-size:13px;color:var(--dim);margin-top:10px}
.range{position:relative;height:2px;border-radius:1px;background:var(--line);margin-top:28px}
.range .fill{position:absolute;left:0;top:0;height:2px;width:0;background:var(--fg);transition:width 1.6s var(--ease) .6s}
.range .dot{position:absolute;top:-4px;left:0;width:10px;height:10px;background:var(--ac);border-radius:50%;transform:translateX(-50%);transition:left 1.6s var(--ease) .6s;box-shadow:0 0 0 4px rgba(245,185,66,.2)}
.range+.ends{display:flex;justify-content:space-between;font:500 12px var(--f);color:var(--dim);margin-top:10px}
.gauge{width:100%;max-width:180px;margin-top:8px}
.gauge path{fill:none;stroke-width:6;stroke-linecap:round}
.gauge .arc{stroke:var(--ac);stroke-dasharray:100;stroke-dashoffset:100;transition:stroke-dashoffset 1.8s var(--ease) .6s}

.cta{display:flex;align-items:center;justify-content:space-between;width:100%;margin:56px 0 80px;padding:32px 0;border-top:1px solid var(--fg);border-bottom:1px solid var(--fg);font:700 clamp(26px,3.6vw,44px) var(--f);letter-spacing:-.035em;text-align:left;position:relative;overflow:hidden;transition:color .5s var(--ease),padding .6s var(--ease)}
.cta::before{content:'';position:absolute;inset:0;background:var(--ac);transform:translateY(101%);transition:transform .6s var(--ease);z-index:-1}
.cta:hover{color:var(--bg);padding-left:24px;padding-right:24px}
.cta:hover::before{transform:none}
.cta .arw{transition:transform .6s var(--ease)}
.cta:hover .arw{transform:translateX(8px)}
.cta .sub{font:700 12px var(--f);letter-spacing:.06em;display:block;margin-bottom:6px;opacity:.7}

.drawer{position:fixed;inset:0;background:var(--bg);z-index:80;overflow-y:auto;transform:translateY(100%);transition:transform .9s var(--ease);visibility:hidden}
.drawer.open{transform:none;visibility:visible}
.dtop{position:sticky;top:0;background:rgba(15,17,21,.92);backdrop-filter:blur(8px);z-index:2;border-bottom:1px solid var(--line)}
.dtop .wrap{display:flex;justify-content:space-between;align-items:center;padding-top:16px;padding-bottom:16px}
.close{font:600 13px var(--f);border:1px solid var(--line);border-radius:8px;padding:9px 16px;transition:border-color .3s,color .3s}
.close:hover{border-color:var(--ac);color:var(--ac)}
.dgrid{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.dgrid .stat{min-height:150px}
.status{display:inline-block;font:600 13px var(--f);padding:5px 12px;border:1px solid currentColor;border-radius:999px}
.sub-chart{height:240px;width:100%}
.explain{font-size:14px;color:var(--dim);max-width:640px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font:500 14px var(--f);margin-bottom:96px}
th{font:600 13px var(--f);color:var(--dim);text-align:right;padding:12px 8px;border-bottom:1px solid var(--dim)}
td{text-align:right;padding:12px 8px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
tbody tr{opacity:0;transform:translateX(-10px);transition:opacity .6s var(--ease),transform .6s var(--ease),background .2s}
.drawer.open tbody tr{opacity:1;transform:none}
tbody tr:hover{background:rgba(255,255,255,.035)}
.bar-cell{position:relative}
.bar-cell i{position:absolute;right:8px;bottom:4px;height:2px;background:var(--ac);opacity:.55}

.err{padding:120px 0;font:600 15px var(--f);color:var(--up)}
footer{padding:28px 0 40px;border-top:1px solid var(--line);font:500 12px var(--f);color:var(--dim);display:flex;justify-content:space-between;gap:16px}

@media (max-width:900px){
  .wrap{padding:0 16px}
  .hero{grid-template-columns:1fr;padding-top:48px}
  .price{text-align:left}
  #chg{justify-content:flex-start}
  .ohlc,.stats,.dgrid{grid-template-columns:1fr 1fr}
  .cell:nth-child(3){border-left:0;padding-left:0}
  .stat{padding-left:16px}
  .stat:nth-child(odd){border-left:0;padding-left:0}
  .stat:nth-child(n+3){border-top:1px solid var(--line)}
  .chart{height:340px}
  .top{flex-wrap:wrap}
  table{font-size:12px}
  .hide-m{display:none}
}
@media (prefers-reduced-motion:reduce){*,*::before{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="loader"></div>
<div class="grain" aria-hidden="true"></div>

<div class="wrap">
  <header class="top">
    <span>005930 · KOSPI · KRW</span>
    <span id="asof">Loading</span>
    <a href="/samsung" target="_blank" rel="noopener">Raw JSON ↗</a>
  </header>
</div>
<div class="ticker" aria-hidden="true"><div class="track" id="track"></div></div>

<main class="wrap" id="app">
  <section class="hero">
    <div class="reveal" style="--d:0">
      <span class="idx">01 — EQUITY</span>
      <h1>삼성전자</h1>
      <p class="en">Samsung Electronics Co., Ltd.</p>
    </div>
    <div class="price reveal" style="--d:1">
      <div class="lbl">종가</div>
      <div class="big"><span id="price">0</span><small>원</small></div>
      <div id="chg"></div>
    </div>
  </section>
  <div class="rule"></div>
  <section class="ohlc reveal" style="--d:2" id="ohlc"></section>

  <section class="sec reveal" style="--d:3">
    <div class="sechead">
      <h2><span class="idx">02</span>가격의 흐름</h2>
      <div class="ranges" role="group" aria-label="기간 선택">
        <button data-n="21">1M</button><button data-n="63">3M</button><button data-n="126" aria-pressed="true">6M</button><button data-n="252">1Y</button><button data-n="0">ALL</button>
      </div>
    </div>
    <div class="readout" id="readout"></div>
    <div class="chart" id="main"></div>
    <div class="legend"><span><i style="background:#f5b942"></i>MA5</span><span><i style="background:#a78bfa"></i>MA20</span><span><i style="background:#34d399"></i>MA60</span><span><i style="background:#8b929c"></i>MA120</span></div>
  </section>

  <section class="sec reveal" style="--d:4">
    <div class="sechead"><h2><span class="idx">03</span>한눈에 보기</h2></div>
    <div class="stats">
      <div class="stat">
        <div><div class="lbl">52주 범위 내 위치</div><div class="num"><span id="pos">0</span><small>%</small></div></div>
        <div><div class="range"><div class="fill" id="posFill"></div><div class="dot" id="posDot"></div></div><div class="ends"><span id="lo"></span><span id="hi"></span></div></div>
      </div>
      <div class="stat">
        <div class="lbl">RSI (14일)</div>
        <svg class="gauge" viewBox="0 0 100 56" aria-hidden="true"><path d="M6 50 A44 44 0 0 1 94 50" stroke="#262a33"/><path class="arc" id="rsiArc" d="M6 50 A44 44 0 0 1 94 50" pathLength="100"/></svg>
        <div><div class="num" style="margin-top:0"><span id="rsi">0</span></div><div class="note" id="rsiNote"></div></div>
      </div>
      <div class="stat">
        <div><div class="lbl">거래량 / 20일 평균</div><div class="num"><span id="vr">0</span><small>배</small></div></div>
        <div><div class="range"><div class="fill" id="vrFill" style="background:var(--ac)"></div></div><div class="ends"><span>0배</span><span>3배</span></div></div>
      </div>
      <div class="stat">
        <div><div class="lbl">20일 변동성 (연율)</div><div class="num"><span id="vol">0</span><small>%</small></div></div>
        <div class="note">일간 수익률 표준편차 × √252</div>
      </div>
    </div>
  </section>

  <button class="cta reveal" style="--d:5" id="openDetail" aria-controls="detail" aria-expanded="false">
    <span><span class="sub">04 — DEEP DIVE</span>상세보기</span><span class="arw">→</span>
  </button>
</main>

<div class="wrap"><footer><span>데이터 · FinanceDataReader</span><span>투자 판단의 책임은 본인에게 있습니다</span></footer></div>

<div class="drawer" id="detail" role="dialog" aria-modal="true" aria-label="상세 지표">
  <div class="dtop"><div class="wrap"><span class="idx">삼성전자 — 상세 지표</span><button class="close" id="closeDetail">닫기 ✕</button></div></div>
  <div class="wrap">
    <section class="sec">
      <div class="sechead"><h2><span class="idx">A</span>이동평균</h2><span class="status" id="align"></span></div>
      <div class="dgrid" id="maGrid"></div>
    </section>
    <section class="sec">
      <div class="sechead"><h2><span class="idx">B</span>RSI · 상대강도</h2><span class="status" id="rsiStatus"></span></div>
      <p class="explain">최근 14일 상승폭과 하락폭의 비율. 70 이상은 과열, 30 이하는 침체 구간으로 봅니다.</p>
      <div class="sub-chart" id="rsiChart"></div>
    </section>
    <section class="sec">
      <div class="sechead"><h2><span class="idx">C</span>MACD · 추세 모멘텀</h2><span class="status" id="macdStatus"></span></div>
      <p class="explain">12일·26일 지수이동평균의 차이(MACD)와 9일 시그널선. 막대가 0 위로 올라서면 상승 모멘텀입니다.</p>
      <div class="sub-chart" id="macdChart"></div>
    </section>
    <section class="sec">
      <div class="sechead"><h2><span class="idx">D</span>볼린저 밴드</h2><span class="status" id="bbStatus"></span></div>
      <p class="explain">20일 평균 ± 2 표준편차. 밴드 폭이 좁아지면 큰 움직임이 다가온다는 신호로 읽습니다.</p>
      <div class="sub-chart" id="bbChart" style="height:300px"></div>
    </section>
    <section class="sec">
      <div class="sechead"><h2><span class="idx">E</span>최근 30거래일</h2></div>
      <table><thead><tr><th>날짜</th><th class="hide-m">시가</th><th class="hide-m">고가</th><th class="hide-m">저가</th><th>종가</th><th>등락</th><th>거래량</th></tr></thead><tbody id="rows"></tbody></table>
    </section>
  </div>
</div>

<script>
const UP='#f04452',DN='#3d8bfd',AC='#f5b942',FG='#eceef1',BG='#0f1115',DIM='#9aa1ab',LN='rgba(255,255,255,.05)';
const $=s=>document.querySelector(s);
const fmt=(n,d=0)=>n==null?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=n=>(n>0?'+':'')+fmt(n,2)+'%';
const dir=n=>n>=0?'up':'dn';
const line=(rows,k)=>rows.filter(r=>r[k]!=null).map(r=>({time:r.Date,value:r[k]}));
const base=()=>({autoSize:true,
  layout:{background:{type:'solid',color:BG},textColor:DIM,fontFamily:"'Pretendard Variable',Pretendard,sans-serif",fontSize:12},
  grid:{vertLines:{color:LN},horzLines:{color:LN}},
  rightPriceScale:{borderColor:LN},timeScale:{borderColor:LN},
  crosshair:{vertLine:{color:'#5b616b',width:1,style:2,labelBackgroundColor:'#2a2e37'},horzLine:{color:'#5b616b',width:1,style:2,labelBackgroundColor:'#2a2e37'}},
  localization:{priceFormatter:p=>fmt(p,Math.abs(p)<1000?1:0)},  // 원화는 정수, RSI 등 작은 값만 소수 1자리
  handleScroll:{vertTouchDrag:false}});
const plain={priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false};

function countUp(el,to,dec=0,dur=1600){
  const s=performance.now();
  const f=t=>{const p=Math.min((t-s)/dur,1),e=1-Math.pow(1-p,4);el.textContent=fmt(to*e,dec);if(p<1)requestAnimationFrame(f)};
  requestAnimationFrame(f);
}

let D,L,S,main,built=false;

fetch('/samsung').then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(init)
  .catch(e=>{$('#app').innerHTML='<p class="err">데이터를 불러오지 못했습니다 — '+e.message+'</p>';document.body.classList.add('ready')});

function init(j){
  D=j.data;L=D[D.length-1];S=j.summary;
  $('#asof').textContent=j.updated+' 기준';
  const up=L.Change>=0;
  $('#chg').innerHTML=`<span class="${dir(L.Change)}">${up?'▲':'▼'} ${fmt(Math.abs(S.change))}</span><span class="${dir(L.Change)}">${pct(L.Change)}</span>`;
  $('#ohlc').innerHTML=[['시가',L.Open],['고가',L.High],['저가',L.Low],['거래량',L.Volume]]
    .map(([k,v])=>`<div class="cell"><div class="lbl">${k}</div><div class="val">${fmt(v)}</div></div>`).join('');
  const tick=D.slice(-40).reverse().map(r=>`<span>${r.Date.slice(5).replace('-','.')}<b class="${dir(r.Change)}">${pct(r.Change)}</b></span>`).join('');
  $('#track').innerHTML=tick+tick;

  buildMain();
  document.body.classList.add('ready');
  countUp($('#price'),L.Close);

  const pos=(L.Close-S.low_52w)/(S.high_52w-S.low_52w)*100;
  $('#lo').textContent='최저 '+fmt(S.low_52w);$('#hi').textContent='최고 '+fmt(S.high_52w);
  const vr=L.Volume/S.avg_volume_20;
  countUp($('#pos'),pos,1);countUp($('#rsi'),L.RSI14,1);countUp($('#vr'),vr,2);countUp($('#vol'),S.volatility_20,1);
  $('#rsiNote').textContent=rsiText(L.RSI14);
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    $('#posFill').style.width=pos+'%';$('#posDot').style.left=pos+'%';
    $('#rsiArc').style.strokeDashoffset=100-L.RSI14;
    $('#vrFill').style.width=Math.min(vr/3,1)*100+'%';
  }));
}

function rsiText(v){return v>=70?'과매수 구간 — 단기 과열':v<=30?'과매도 구간 — 단기 침체':'중립 구간'}

function readout(r){
  $('#readout').innerHTML=`<span>${r.Date}</span><span>시 <b>${fmt(r.Open)}</b></span><span>고 <b>${fmt(r.High)}</b></span><span>저 <b>${fmt(r.Low)}</b></span><span>종 <b>${fmt(r.Close)}</b></span><span class="${dir(r.Change)}">${pct(r.Change)}</span><span>거래량 <b>${fmt(r.Volume)}</b></span>`;
}

function buildMain(){
  main=LightweightCharts.createChart($('#main'),base());
  const cs=main.addCandlestickSeries({upColor:UP,borderUpColor:UP,wickUpColor:UP,downColor:DN,borderDownColor:DN,wickDownColor:DN});
  cs.setData(D.map(r=>({time:r.Date,open:r.Open,high:r.High,low:r.Low,close:r.Close})));
  [['MA5',AC],['MA20','#a78bfa'],['MA60','#34d399'],['MA120','#8b929c']]
    .forEach(([k,c])=>main.addLineSeries({color:c,lineWidth:1.5,...plain}).setData(line(D,k)));
  const vol=main.addHistogramSeries({priceScaleId:'vol',priceFormat:{type:'volume'},...plain});
  main.priceScale('vol').applyOptions({scaleMargins:{top:.84,bottom:0}});
  vol.setData(D.map(r=>({time:r.Date,value:r.Volume,color:r.Change>=0?'rgba(240,68,82,.4)':'rgba(61,139,253,.4)'})));
  main.subscribeCrosshairMove(p=>readout((p.logical!=null&&D[Math.round(p.logical)])||L));
  readout(L);
  setRange(126);
  document.querySelectorAll('.ranges button').forEach(b=>b.onclick=()=>{
    document.querySelectorAll('.ranges button').forEach(x=>x.setAttribute('aria-pressed',x===b));
    setRange(+b.dataset.n);
  });
}
function setRange(n){n?main.timeScale().setVisibleLogicalRange({from:D.length-n,to:D.length+1}):main.timeScale().fitContent()}

// tone: 'up' | 'dn' | 그 외(중립)
function status(id,text,tone){const el=$(id);el.textContent=text;el.style.color=tone==='up'?UP:tone==='dn'?DN:DIM}

function buildDetail(){
  // A. 이동평균
  const mas=['MA5','MA20','MA60','MA120'];
  $('#maGrid').innerHTML=mas.map(k=>{const v=L[k],d=(L.Close/v-1)*100;
    return `<div class="stat"><div class="lbl">${k.replace('MA','')}일 이동평균</div><div class="num" style="font-size:30px">${fmt(v)}</div><div class="note">종가 대비 <b class="${dir(d)}">${pct(d)}</b></div></div>`}).join('');
  const bull=mas.every((k,i)=>i===0||L[mas[i-1]]>L[k]), bear=mas.every((k,i)=>i===0||L[mas[i-1]]<L[k]);
  status('#align',bull?'정배열 · 상승 추세':bear?'역배열 · 하락 추세':'혼조',bull?'up':bear?'dn':'');

  // B. RSI
  const rc=LightweightCharts.createChart($('#rsiChart'),base());
  const rs=rc.addLineSeries({color:AC,lineWidth:2,priceLineVisible:false});
  rs.setData(line(D,'RSI14'));
  rs.createPriceLine({price:70,color:UP,lineWidth:1,lineStyle:2,axisLabelVisible:true});
  rs.createPriceLine({price:30,color:DN,lineWidth:1,lineStyle:2,axisLabelVisible:true});
  status('#rsiStatus',fmt(L.RSI14,1)+' · '+rsiText(L.RSI14).split(' —')[0],L.RSI14>=70?'up':L.RSI14<=30?'dn':'');

  // C. MACD
  const mc=LightweightCharts.createChart($('#macdChart'),base());
  mc.addHistogramSeries({...plain}).setData(D.filter(r=>r.Hist!=null).map(r=>({time:r.Date,value:r.Hist,color:r.Hist>=0?'rgba(240,68,82,.65)':'rgba(61,139,253,.65)'})));
  mc.addLineSeries({color:FG,lineWidth:1.5,...plain}).setData(line(D,'MACD'));
  mc.addLineSeries({color:AC,lineWidth:1.5,lineStyle:2,...plain}).setData(line(D,'Signal'));
  const P=D[D.length-2], cross=P.Hist<=0&&L.Hist>0?'골든크로스 발생':P.Hist>=0&&L.Hist<0?'데드크로스 발생':L.Hist>0?'상승 모멘텀':'하락 모멘텀';
  status('#macdStatus',cross,dir(L.Hist));

  // D. 볼린저
  const bc=LightweightCharts.createChart($('#bbChart'),base());
  bc.addAreaSeries({lineColor:'transparent',topColor:'rgba(245,185,66,.07)',bottomColor:'rgba(245,185,66,.07)',...plain}).setData(line(D,'BB_Upper'));
  bc.addLineSeries({color:'rgba(245,185,66,.7)',lineWidth:1,...plain}).setData(line(D,'BB_Upper'));
  bc.addLineSeries({color:'rgba(245,185,66,.7)',lineWidth:1,...plain}).setData(line(D,'BB_Lower'));
  bc.addLineSeries({color:'#5b616b',lineWidth:1,lineStyle:2,...plain}).setData(line(D,'MA20'));
  bc.addLineSeries({color:FG,lineWidth:2,priceLineVisible:false}).setData(line(D,'Close'));
  [rc,mc,bc].forEach(c=>c.timeScale().setVisibleLogicalRange({from:D.length-126,to:D.length+1}));
  const pb=(L.Close-L.BB_Lower)/(L.BB_Upper-L.BB_Lower)*100;
  status('#bbStatus','%B '+fmt(pb,0)+(pb>100?' · 상단 돌파':pb<0?' · 하단 이탈':' · 밴드 내'),pb>100?'up':pb<0?'dn':'');

  // E. 테이블
  const last=D.slice(-30).reverse(), vmax=Math.max(...last.map(r=>r.Volume));
  $('#rows').innerHTML=last.map((r,i)=>`<tr style="transition-delay:${300+i*25}ms"><td>${r.Date}</td><td class="hide-m">${fmt(r.Open)}</td><td class="hide-m">${fmt(r.High)}</td><td class="hide-m">${fmt(r.Low)}</td><td>${fmt(r.Close)}</td><td class="${dir(r.Change)}">${pct(r.Change)}</td><td class="bar-cell">${fmt(r.Volume)}<i style="width:${r.Volume/vmax*60}%"></i></td></tr>`).join('');
}

const dr=$('#detail'),ob=$('#openDetail');
function openD(){if(!D)return;if(!built){buildDetail();built=true}
  dr.classList.add('open');ob.setAttribute('aria-expanded','true');document.body.style.overflow='hidden';dr.scrollTop=0;setTimeout(()=>$('#closeDetail').focus(),50)}
function closeD(){dr.classList.remove('open');ob.setAttribute('aria-expanded','false');document.body.style.overflow='';ob.focus()}
ob.onclick=openD;$('#closeDetail').onclick=closeD;
addEventListener('keydown',e=>{if(e.key==='Escape'&&dr.classList.contains('open'))closeD()});
</script>
</body>
</html>
"""
