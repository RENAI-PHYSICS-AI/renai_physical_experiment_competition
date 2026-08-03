from __future__ import annotations

import json
import os

import streamlit.components.v1 as components


def render_sound_speed_experiment(julia_url: str, height: int = 930) -> None:
    heartbeat_url = os.getenv("SOUND_SPEED_HEARTBEAT_URL", "").strip()
    client_log_url = (
        heartbeat_url[:-10] + "/client-log"
        if heartbeat_url.endswith("/heartbeat")
        else heartbeat_url + "/client-log"
        if heartbeat_url
        else ""
    )
    settings = json.dumps(
        {"url": julia_url, "clientLogUrl": client_log_url},
        ensure_ascii=False,
    )
    html = _HTML.replace("__SETTINGS__", settings)
    components.html(html, height=height, scrolling=False)


_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * { box-sizing:border-box; }
  html,body { margin:0; overflow:hidden; background:transparent; font-family:system-ui,"Microsoft YaHei",sans-serif; }
  .stage { position:relative; width:100%; height:910px; overflow:hidden; background:#0b0f14; border-radius:6px; }
  iframe { display:block; width:100%; height:100%; border:0; background:#0b0f14; }
  .loading { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
    flex-direction:column; gap:14px; color:#d4dde7; background:#0b0f14; transition:opacity .2s ease; }
  .loading.hidden { opacity:0; pointer-events:none; }
  .spinner { width:42px; height:42px; border-radius:50%; border:5px solid rgba(255,255,255,.15);
    border-top-color:#27b3a2; animation:spin 1s linear infinite; }
  .title { font-size:18px; font-weight:700; letter-spacing:0; }
  .detail { max-width:620px; color:#91a3b5; font-size:14px; line-height:1.6; text-align:center; letter-spacing:0; }
  .error { color:#ff8e8e; }
  @keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
<main class="stage">
  <iframe id="julia" title="声速四种方法综合可视化实验"></iframe>
  <div class="loading" id="loading">
    <div class="spinner"></div>
    <div class="title" id="title">正在初始化 Julia 交互实验</div>
    <div class="detail" id="detail">首次运行需要加载 Bonito 与 WGLMakie，请稍等。</div>
  </div>
</main>
<script>
(() => {
  const settings = __SETTINGS__;
  const frame = document.getElementById('julia');
  const loading = document.getElementById('loading');
  const title = document.getElementById('title');
  const detail = document.getElementById('detail');
  const clientLog = (type, message = '') => {
    if (!settings.clientLogUrl) return;
    const body = JSON.stringify({
      type,
      url: settings.url,
      detail: String(message),
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });
    fetch(settings.clientLogUrl, {method:'POST', mode:'no-cors', cache:'no-store', body}).catch(() => {});
  };
  const timeout = window.setTimeout(() => {
    title.textContent = '实验加载时间较长';
    detail.textContent = '请检查 Julia 服务窗口或 web_stdout.log；刷新页面可重新连接。';
    detail.classList.add('error');
    clientLog('wrapper-timeout', 'WGL ready message was not received after 70 seconds');
  }, 70000);
  clientLog('wrapper-start', 'opening Julia iframe');
  frame.src = settings.url + (settings.url.includes('?') ? '&' : '?') + 'attempt=' + Date.now();
  frame.addEventListener('load', () => clientLog('iframe-load', frame.src));
  frame.addEventListener('error', () => clientLog('iframe-error', frame.src));
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || !event.data) return;
    if (event.data.type === 'sound-speed-wgl-ready') {
      window.clearTimeout(timeout);
      clientLog('wgl-ready', event.data.detail || '');
      loading.classList.add('hidden');
    }
    if (event.data.type === 'sound-speed-wgl-failed') {
      window.clearTimeout(timeout);
      clientLog('wgl-failed', event.data.detail || '');
      title.textContent = 'Julia 实验初始化失败';
      detail.textContent = event.data.detail || '请查看 web_stdout.log。';
      detail.classList.add('error');
    }
  });
  window.addEventListener('error', event => clientLog('wrapper-error', `${event.message} ${event.filename}:${event.lineno}`));
  window.addEventListener('unhandledrejection', event => clientLog('wrapper-unhandledrejection', event.reason || ''));
})()
</script>
</body>
</html>
"""
