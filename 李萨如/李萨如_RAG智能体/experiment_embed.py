from __future__ import annotations

import base64
import json
import os

import streamlit.components.v1 as components


EXPERIMENTS = {
    "相位差": {
        "mode": "phase",
        "summary": "保持两方向频率相同，观察相位差如何把直线连续变为椭圆或圆。",
        "controls": [
            ("amplitude", "共同振幅 A", 0.2, 2.0, 0.05, 1.0),
            ("frequency", "共同频率 f / Hz", 0.5, 5.0, 0.1, 1.0),
            ("phase", "相位差 φ / °", 0, 360, 1, 60),
        ],
    },
    "振幅比": {
        "mode": "amplitude",
        "summary": "保持频率相同，改变两个正交振动的振幅，比较轨迹长短轴与振幅比。",
        "controls": [
            ("ax", "X 振幅 Ax", 0.2, 2.0, 0.05, 1.0),
            ("ay", "Y 振幅 Ay", 0.2, 2.0, 0.05, 1.5),
            ("phase", "相位差 φ / °", 0, 180, 1, 90),
        ],
    },
    "有理频率比": {
        "mode": "ratio",
        "summary": "调节整数频率比，观察轨迹闭合、波瓣数量与共同周期之间的关系。",
        "controls": [
            ("fx", "X 频率 fx / Hz", 1, 8, 1, 2),
            ("fy", "Y 频率 fy / Hz", 1, 8, 1, 3),
            ("phase", "相位差 φ / °", 0, 180, 1, 30),
        ],
    },
    "频率失谐": {
        "mode": "detune",
        "summary": "让两个频率略有差异，观察相位缓慢漂移和轨迹不再稳定闭合的过程。",
        "controls": [
            ("fx", "基准频率 fx / Hz", 1.0, 6.0, 0.05, 3.0),
            ("fy", "失谐频率 fy / Hz", 1.0, 6.0, 0.01, 3.08),
            ("phase", "初相位 φ / °", 0, 180, 1, 20),
        ],
    },
}


def experiment_html(name: str) -> str:
    config = EXPERIMENTS[name]
    payload = json.dumps(config, ensure_ascii=False)
    return _HTML.replace("__CONFIG__", payload)


def render_experiment(name: str, height: int = 820) -> None:
    components.html(
        experiment_html(name),
        height=height,
        scrolling=False,
    )


def render_julia_experiment(name: str, julia_url: str, route: str, height: int = 820) -> None:
    heartbeat_url = os.getenv("LISSAJOUS_HEARTBEAT_URL", "").strip()
    client_log_url = (
        heartbeat_url[:-10] + "/client-log"
        if heartbeat_url.endswith("/heartbeat")
        else heartbeat_url + "/client-log"
        if heartbeat_url
        else ""
    )
    settings = json.dumps(
        {
            "juliaUrl": f"{julia_url}{route}",
            "title": name,
            "clientLogUrl": client_log_url,
        },
        ensure_ascii=False,
    )
    components.html(
        _JULIA_ONLY_HTML.replace("__SETTINGS__", settings),
        height=height,
        scrolling=False,
    )


def render_hybrid_experiment(
    name: str,
    julia_url: str,
    route: str,
    height: int = 820,
    timeout_seconds: float = 12.0,
) -> None:
    fallback = base64.b64encode(experiment_html(name).encode("utf-8")).decode("ascii")
    settings = json.dumps(
        {
            "juliaUrl": f"{julia_url}{route}",
            "fallbackHtml": fallback,
            "timeoutMs": max(3000, round(timeout_seconds * 1000)),
        }
    )
    components.html(
        _HYBRID_HTML.replace("__SETTINGS__", settings),
        height=height,
        scrolling=False,
    )


_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root { color-scheme: light dark; --bg:#0b0e13; --panel:#12171e; --line:#2d3540;
    --text:#f2f4f7; --muted:#9aa4b2; --x:#2ec7e6; --y:#ef5a7d; --gold:#ffb83d;
    --green:#58d18b; --accent:#ff4b55; }
  * { box-sizing:border-box; }
  html,body { margin:0; background:transparent; color:var(--text); font:15px/1.45 system-ui,
    "Microsoft YaHei",sans-serif; letter-spacing:0; overflow:hidden; }
  .lab { height:800px; padding:18px; background:var(--bg); border:1px solid #252c35;
    border-radius:8px; display:grid; grid-template-rows:auto minmax(0,1fr) auto auto; gap:14px; }
  header { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; }
  h2 { margin:0; font-size:24px; }
  header p { margin:4px 0 0; color:var(--muted); }
  .status { color:var(--green); white-space:nowrap; font-weight:650; }
  .plots { min-height:0; display:grid; grid-template-columns:1.15fr 1fr 1fr; gap:10px; }
  .plot { min-width:0; background:var(--panel); border:1px solid #242c35; border-radius:6px;
    padding:10px; display:grid; grid-template-rows:auto minmax(0,1fr); }
  .plot h3 { margin:0 0 4px; text-align:center; font-size:15px; font-weight:650; }
  canvas { width:100%; height:100%; min-height:270px; display:block; }
  .controls { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
  .control { min-width:0; background:var(--panel); border:1px solid #242c35; border-radius:6px; padding:10px 12px; }
  .control label { display:flex; justify-content:space-between; gap:8px; color:var(--muted); }
  .control output { color:var(--text); font-variant-numeric:tabular-nums; }
  input[type=range] { width:100%; accent-color:var(--accent); }
  .footer { display:grid; grid-template-columns:auto 1fr; gap:16px; align-items:center; }
  .actions { display:flex; gap:8px; }
  button { height:38px; padding:0 18px; border:1px solid #38414d; border-radius:6px;
    background:#202630; color:var(--text); font:inherit; cursor:pointer; }
  button.primary { background:var(--accent); border-color:var(--accent); color:white; }
  .metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }
  .metric { border-left:2px solid var(--gold); padding-left:10px; min-width:0; }
  .metric span { color:var(--muted); display:block; font-size:12px; }
  .metric strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    font-size:15px; font-variant-numeric:tabular-nums; }
  @media (max-width:900px) {
    .lab { height:800px; }
    .plots { grid-template-columns:1fr 1fr; }
    .plot:last-child { display:none; }
    .metrics { grid-template-columns:1fr 1fr; }
  }
</style>
</head>
<body>
<main class="lab">
  <header><div><h2 id="title"></h2><p id="summary"></p></div><div class="status">实时运行</div></header>
  <section class="plots">
    <div class="plot"><h3>X、Y 方向时域波形</h3><canvas id="wave"></canvas></div>
    <div class="plot"><h3>李萨如轨迹</h3><canvas id="trajectory"></canvas></div>
    <div class="plot"><h3 id="auxTitle">参数扫描</h3><canvas id="auxiliary"></canvas></div>
  </section>
  <section class="controls" id="controls"></section>
  <footer class="footer">
    <div class="actions"><button class="primary" id="play">暂停</button><button id="reset">重置</button></div>
    <div class="metrics" id="metrics"></div>
  </footer>
</main>
<script>
(() => {
  const cfg = __CONFIG__;
  const defaults = Object.fromEntries(cfg.controls.map(c => [c[0], c[5]]));
  const values = {...defaults};
  let playing = true, clock = 0, previous = performance.now();
  const $ = id => document.getElementById(id);
  $('title').textContent = ({phase:'相位差',amplitude:'振幅比',ratio:'有理频率比',detune:'频率失谐'})[cfg.mode];
  $('summary').textContent = cfg.summary;
  const controls = $('controls');
  cfg.controls.forEach(([key,label,min,max,step,start]) => {
    const box=document.createElement('div'); box.className='control';
    box.innerHTML=`<label><span>${label}</span><output id="o-${key}"></output></label>`+
      `<input id="i-${key}" type="range" min="${min}" max="${max}" step="${step}" value="${start}">`;
    controls.appendChild(box);
    const input=$(`i-${key}`), output=$(`o-${key}`);
    const update=()=>{ values[key]=Number(input.value); output.value=Number(input.value).toFixed(step<0.1?2:step<1?1:0); };
    input.addEventListener('input',update); update();
  });

  const canvases=['wave','trajectory','auxiliary'].map($);
  function context(canvas) {
    const ratio=Math.min(devicePixelRatio||1,2), rect=canvas.getBoundingClientRect();
    const width=Math.max(240,Math.round(rect.width*ratio)), height=Math.max(220,Math.round(rect.height*ratio));
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    const ctx=canvas.getContext('2d'); ctx.setTransform(ratio,0,0,ratio,0,0);
    return {ctx,w:width/ratio,h:height/ratio};
  }
  function frame(canvas, xLabel='', yLabel='') {
    const {ctx,w,h}=context(canvas), pad={l:42,r:14,t:12,b:32};
    ctx.clearRect(0,0,w,h); ctx.fillStyle='#12171e';ctx.fillRect(0,0,w,h);
    ctx.strokeStyle='#252d37';ctx.lineWidth=1;
    for(let i=0;i<=4;i++){const x=pad.l+(w-pad.l-pad.r)*i/4;ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();}
    for(let i=0;i<=4;i++){const y=pad.t+(h-pad.t-pad.b)*i/4;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();}
    ctx.fillStyle='#9aa4b2';ctx.font='12px system-ui';ctx.textAlign='center';ctx.fillText(xLabel,(pad.l+w-pad.r)/2,h-8);
    ctx.save();ctx.translate(12,(pad.t+h-pad.b)/2);ctx.rotate(-Math.PI/2);ctx.fillText(yLabel,0,0);ctx.restore();
    return {ctx,w,h,pad,x0:pad.l,y0:pad.t,pw:w-pad.l-pad.r,ph:h-pad.t-pad.b};
  }
  function poly(plot, points, color, width=2.2) {
    const {ctx}=plot; if(!points.length)return; ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=width;
    points.forEach((p,i)=>{const x=plot.x0+p[0]*plot.pw,y=plot.y0+(1-p[1])*plot.ph;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
  }
  function dot(plot,p,color,r=5){const x=plot.x0+p[0]*plot.pw,y=plot.y0+(1-p[1])*plot.ph;plot.ctx.beginPath();plot.ctx.fillStyle=color;plot.ctx.arc(x,y,r,0,Math.PI*2);plot.ctx.fill();}
  const normalize=(v,lo,hi)=>(v-lo)/(hi-lo);
  const gcd=(a,b)=>b?gcd(b,a%b):a;

  function current() {
    let ax=1,ay=1,fx=1,fy=1,phase=(values.phase||0)*Math.PI/180;
    if(cfg.mode==='phase'){ax=ay=values.amplitude;fx=fy=values.frequency;}
    if(cfg.mode==='amplitude'){ax=values.ax;ay=values.ay;}
    if(cfg.mode==='ratio'){fx=values.fx;fy=values.fy;}
    if(cfg.mode==='detune'){fx=values.fx;fy=values.fy;}
    return {ax,ay,fx,fy,phase};
  }
  function drawWave(p) {
    const plot=frame($('wave'),'归一化时间','位移'), maxA=Math.max(p.ax,p.ay)*1.15;
    const xs=[],ys=[]; for(let i=0;i<=320;i++){const u=i/320,t=u*2;
      xs.push([u,normalize(p.ax*Math.sin(2*Math.PI*p.fx*t),-maxA,maxA)]);
      ys.push([u,normalize(p.ay*Math.sin(2*Math.PI*p.fy*t+p.phase),-maxA,maxA)]);}
    poly(plot,xs,'#2ec7e6');poly(plot,ys,'#ef5a7d');
    const u=(clock%4)/4, t=u*2;
    dot(plot,[u,normalize(p.ax*Math.sin(2*Math.PI*p.fx*t),-maxA,maxA)],'#2ec7e6');
    dot(plot,[u,normalize(p.ay*Math.sin(2*Math.PI*p.fy*t+p.phase),-maxA,maxA)],'#ef5a7d');
  }
  function drawTrajectory(p) {
    const plot=frame($('trajectory'),'x','y'), maxA=Math.max(p.ax,p.ay)*1.12, points=[];
    const span=cfg.mode==='detune'?Math.min(18,4+clock):Math.max(1,1/gcd(Math.round(p.fx),Math.round(p.fy)));
    const samples=700; for(let i=0;i<=samples;i++){const t=span*i/samples;
      points.push([normalize(p.ax*Math.sin(2*Math.PI*p.fx*t),-maxA,maxA),normalize(p.ay*Math.sin(2*Math.PI*p.fy*t+p.phase),-maxA,maxA)]);}
    poly(plot,points,'rgba(255,255,255,.22)',1.4);
    const upto=Math.max(2,Math.floor((clock%4)/4*samples));poly(plot,points.slice(0,upto),'#ffb83d',3);
    dot(plot,points[upto-1]||points[0],'#ef5a7d',6);
  }
  function drawAux(p) {
    const plot=frame($('auxiliary'),cfg.mode==='detune'?'时间':'扫描参数',cfg.mode==='detune'?'相位漂移':'归一化指标');
    const points=[];
    if(cfg.mode==='phase'){
      $('auxTitle').textContent='相位扫描与椭圆半轴比';
      for(let i=0;i<=360;i++){const q=i*Math.PI/180;points.push([i/360,Math.min(1,Math.abs(Math.sin(q))/(1+Math.abs(Math.cos(q))))]);}
      poly(plot,points,'#58d18b');dot(plot,[values.phase/360,Math.min(1,Math.abs(Math.sin(p.phase))/(1+Math.abs(Math.cos(p.phase))))],'#ffb83d');
    } else if(cfg.mode==='amplitude'){
      $('auxTitle').textContent='振幅比与轨迹尺度';
      for(let i=0;i<=200;i++){const r=.1+1.9*i/200;points.push([i/200,Math.min(r,1/r)]);}
      poly(plot,points,'#58d18b');const r=p.ay/p.ax;dot(plot,[Math.max(0,Math.min(1,(r-.1)/1.9)),Math.min(r,1/r)],'#ffb83d');
    } else if(cfg.mode==='ratio'){
      $('auxTitle').textContent='频率比与共同周期';
      for(let i=1;i<=8;i++)points.push([(i-1)/7,1/gcd(i,Math.round(p.fy))]);
      poly(plot,points,'#58d18b');dot(plot,[(p.fx-1)/7,1/gcd(Math.round(p.fx),Math.round(p.fy))],'#ffb83d');
    } else {
      $('auxTitle').textContent='相对相位漂移'; const df=p.fy-p.fx;
      for(let i=0;i<=300;i++){const t=20*i/300;points.push([i/300,(Math.sin(2*Math.PI*df*t+p.phase)+1)/2]);}
      poly(plot,points,'#58d18b');const u=(clock%20)/20;dot(plot,[u,(Math.sin(2*Math.PI*df*(clock%20)+p.phase)+1)/2],'#ffb83d');
    }
  }
  function metrics(p) {
    const ratio=p.fx/p.fy, d=Math.abs(p.fy-p.fx), g=gcd(Math.round(p.fx),Math.round(p.fy));
    const rotation=Math.abs(Math.sin(p.phase))<.001?'往复运动':Math.sin(p.phase)>0?'顺时针':'逆时针';
    let items=[['频率比',`${p.fx.toFixed(2)} : ${p.fy.toFixed(2)}`],['振幅比',`${p.ax.toFixed(2)} : ${p.ay.toFixed(2)}`],['运动方向',rotation],['运行时间',`${clock.toFixed(1)} s`]];
    if(cfg.mode==='ratio')items=[['最简频率比',`${Math.round(p.fx/g)} : ${Math.round(p.fy/g)}`],['共同周期',`${(1/g).toFixed(3)} s`],['X 波瓣参考',String(Math.round(p.fy/g))],['Y 波瓣参考',String(Math.round(p.fx/g))]];
    if(cfg.mode==='detune')items=[['失谐量 Δf',`${d.toFixed(2)} Hz`],['拍频',`${d.toFixed(2)} Hz`],['相位漂移',`${(360*d*clock%360).toFixed(1)}°`],['闭合判断',d<.001?'稳定闭合':'观察窗内漂移']];
    $('metrics').innerHTML=items.map(([a,b])=>`<div class="metric"><span>${a}</span><strong title="${b}">${b}</strong></div>`).join('');
  }
  function draw(){const p=current();drawWave(p);drawTrajectory(p);drawAux(p);metrics(p);}
  function animate(now){const dt=Math.min(.05,(now-previous)/1000);previous=now;if(playing)clock+=dt;draw();requestAnimationFrame(animate);}
  $('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'暂停':'播放';};
  $('reset').onclick=()=>{clock=0;playing=true;$('play').textContent='暂停';cfg.controls.forEach(c=>{$(`i-${c[0]}`).value=c[5];$(`i-${c[0]}`).dispatchEvent(new Event('input'));});};
  new ResizeObserver(draw).observe(document.body);requestAnimationFrame(animate);
})();
</script>
</body>
</html>
"""


_JULIA_ONLY_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { box-sizing:border-box; }
  html,body { margin:0; background:transparent; overflow:hidden; font-family:system-ui,"Microsoft YaHei",sans-serif; }
  .stage { position:relative; width:100%; height:800px; overflow:hidden; background:#0b0f14; border-radius:6px; }
  iframe { display:block; width:100%; height:100%; border:0; background:#0b0f14; }
  .loading {
    position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column;
    gap:14px; pointer-events:none; color:#cbd5e1; background:#0b0f14; transition:opacity .25s ease;
  }
  .loading.hidden { opacity:0; }
  .spinner {
    width:42px; height:42px; border-radius:50%; border:5px solid rgba(255,255,255,.16);
    border-top-color:#ff4b55; animation:spin 1s linear infinite;
  }
  .text { font-size:18px; font-weight:650; letter-spacing:0; }
  .hint { max-width:580px; color:#93a4b7; font-size:14px; line-height:1.6; text-align:center; letter-spacing:0; }
  @keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
<main class="stage">
  <iframe id="julia" title="Julia 交互实验"></iframe>
  <div class="loading" id="loading">
    <div class="spinner"></div>
    <div class="text">正在初始化 Julia 交互图形</div>
    <div class="hint">首次启动需要解包并加载 Julia/WGLMakie 组件，请稍等。</div>
  </div>
</main>
<script>
(() => {
  const settings = __SETTINGS__;
  const frame = document.getElementById('julia');
  const loading = document.getElementById('loading');
  function clientLog(type, detail) {
    if (!settings.clientLogUrl) return;
    const body = JSON.stringify({
      type,
      title: settings.title,
      url: settings.juliaUrl,
      detail: String(detail || ''),
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });
    fetch(settings.clientLogUrl, {method:'POST', mode:'no-cors', cache:'no-store', body}).catch(() => {});
  }
  clientLog('wrapper-start', 'opening Julia iframe');
  frame.src = settings.juliaUrl + (settings.juliaUrl.includes('?') ? '&' : '?') + 'attempt=' + Date.now();
  frame.addEventListener('load', () => clientLog('iframe-load', frame.src));
  frame.addEventListener('error', () => clientLog('iframe-error', frame.src));
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || !event.data) return;
    if (event.data.type === 'lissajous-wgl-ready') {
      clientLog('wgl-ready', event.data.detail || '');
      loading.classList.add('hidden');
    }
    if (event.data.type === 'lissajous-wgl-failed') {
      clientLog('wgl-failed', event.data.detail || '');
    }
  });
  window.addEventListener('error', event => clientLog('wrapper-error', `${event.message} ${event.filename}:${event.lineno}`));
  window.addEventListener('unhandledrejection', event => clientLog('wrapper-unhandledrejection', event.reason || ''));
  setTimeout(() => {
    if (!loading.classList.contains('hidden')) clientLog('wrapper-timeout', 'WGL ready message was not received after 60 seconds');
  }, 60000);
})();
</script>
</body>
</html>
"""


_HYBRID_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { box-sizing:border-box; }
  html,body { margin:0; background:transparent; overflow:hidden; font-family:system-ui,"Microsoft YaHei",sans-serif; }
  .stage { position:relative; width:100%; height:800px; overflow:hidden; background:#0b0f14; border-radius:6px; }
  iframe { display:block; width:100%; height:100%; border:0; background:#0b0f14; }
  iframe[hidden] { display:none; }
  .mode-note { position:absolute; right:14px; bottom:14px; z-index:4; display:none; align-items:center;
    gap:10px; padding:8px 10px; color:#d7dee8; background:rgba(23,29,38,.94); border:1px solid #38414d;
    border-radius:6px; box-shadow:0 4px 18px rgba(0,0,0,.25); font-size:13px; }
  .mode-note.visible { display:flex; }
  button { height:30px; padding:0 10px; border:1px solid #4a5665; border-radius:5px; color:#f5f7fa;
    background:#252d38; font:inherit; cursor:pointer; }
</style>
</head>
<body>
<main class="stage">
  <iframe id="julia" title="Julia 交互实验"></iframe>
  <iframe id="fallback" title="稳定渲染实验" hidden></iframe>
  <div class="mode-note" id="modeNote"><span>当前浏览器已自动启用稳定模式</span><button id="retry">重试 Julia</button></div>
</main>
<script>
(() => {
  const settings = __SETTINGS__;
  const juliaFrame = document.getElementById('julia');
  const fallbackFrame = document.getElementById('fallback');
  const modeNote = document.getElementById('modeNote');
  let timer = 0;
  let fallbackLoaded = false;

  function armTimeout() {
    clearTimeout(timer);
    timer = setTimeout(showFallback, settings.timeoutMs);
  }
  function showJulia() {
    clearTimeout(timer);
    fallbackFrame.hidden = true;
    juliaFrame.hidden = false;
    modeNote.classList.remove('visible');
  }
  function showFallback() {
    clearTimeout(timer);
    if (!fallbackLoaded) {
      fallbackFrame.srcdoc = new TextDecoder().decode(Uint8Array.from(atob(settings.fallbackHtml), c => c.charCodeAt(0)));
      fallbackLoaded = true;
    }
    fallbackFrame.hidden = false;
    juliaFrame.hidden = true;
    juliaFrame.src = 'about:blank';
    modeNote.classList.add('visible');
  }
  function startJulia() {
    const probe = document.createElement('canvas');
    let webgl2 = null;
    try {
      webgl2 = probe.getContext('webgl2');
    } catch (_) {}
    if (!webgl2) {
      showFallback();
      return;
    }
    showJulia();
    juliaFrame.src = settings.juliaUrl + (settings.juliaUrl.includes('?') ? '&' : '?') + 'attempt=' + Date.now();
    armTimeout();
  }
  window.addEventListener('message', event => {
    if (event.source !== juliaFrame.contentWindow || !event.data) return;
    if (event.data.type === 'lissajous-wgl-ready') showJulia();
    if (event.data.type === 'lissajous-wgl-failed') showFallback();
  });
  juliaFrame.addEventListener('error', showFallback);
  document.getElementById('retry').addEventListener('click', startJulia);
  startJulia();
})();
</script>
</body>
</html>
"""
