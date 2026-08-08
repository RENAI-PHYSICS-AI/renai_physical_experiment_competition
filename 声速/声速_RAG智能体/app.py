from __future__ import annotations

import base64
import json
import os
import random
import subprocess
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import code_runner
from agent import SoundSpeedAgent
from config import INDEX_DIR, JULIA_WEB_URL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from experiment_embed import render_sound_speed_experiment
from retrieval import HybridRetriever
from tools import ensure_julia_web_server, launch_julia_web_server


QUICK_QUESTION_POOL = (
    "回声法测量声速时为什么要使用两倍墙面距离？",
    "双麦克风时间差法如何利用互相关确定传播时延？",
    "示波器相位差法为什么会出现完整周期数不确定？",
    "驻波法如何从相邻波节间距得到声速？",
    "温度、湿度和气流分别怎样影响空气中的声速？",
    "采样率不足会给时间差法带来多大的量化误差？",
    "如何比较四种声速测量方法的精度和适用条件？",
    "Kundt 管实验在声速测量史上有什么意义？",
    "怎样设计一组距离与时间差的线性拟合实验？",
    "水中声速测量与空气中声速测量有哪些差异？",
)

MAX_IMAGE_COUNT = 3
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
CODE_RUNNER_ENABLED = os.getenv("SOUND_SPEED_CODE_RUNNER_ENABLED", "true").lower() in {
    "1", "true", "yes",
}
CODE_RUNNER_OUTPUT_DIR = Path(
    os.getenv(
        "SOUND_SPEED_CODE_OUTPUT_DIR",
        Path(__file__).resolve().parent / "runtime_outputs",
    )
).resolve()


st.set_page_config(
    page_title="声速测量实验智能助教",
    page_icon="∿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def install_launcher_heartbeat() -> None:
    heartbeat_url = os.getenv("SOUND_SPEED_HEARTBEAT_URL", "").strip()
    if not heartbeat_url:
        return
    encoded_url = json.dumps(heartbeat_url)
    components.html(
        f"""
        <script>
        (() => {{
            const host = window.parent;
            const url = {encoded_url};
            const closedUrl = url.endsWith("/heartbeat")
                ? url.slice(0, -10) + "/closed"
                : url + "/closed";
            if (host.__soundSpeedHeartbeatTimer) {{
                host.clearInterval(host.__soundSpeedHeartbeatTimer);
            }}
            if (host.__soundSpeedCloseHandler) {{
                host.removeEventListener("pagehide", host.__soundSpeedCloseHandler);
            }}
            const pulse = () => host.fetch(url, {{mode: "no-cors", cache: "no-store"}}).catch(() => {{}});
            const close = () => {{
                try {{ host.navigator.sendBeacon(closedUrl, "closed"); }} catch (_) {{}}
            }};
            pulse();
            host.__soundSpeedHeartbeatTimer = host.setInterval(pulse, 3000);
            host.__soundSpeedCloseHandler = close;
            host.addEventListener("pagehide", close);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


install_launcher_heartbeat()


@st.cache_resource(show_spinner=False)
def prewarm_julia_runtime() -> object | None:
    """Start Julia while the user reads the home page."""
    try:
        return launch_julia_web_server()
    except Exception:
        return None


prewarm_julia_runtime()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1180px;}
    .app-hero {
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(260px, .75fr);
        align-items: center;
        gap: 2rem;
        min-height: 230px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.25rem;
        overflow: hidden;
        color: #f7fbff;
        background: #15365b;
        border: 1px solid #2e526f;
        border-radius: 8px;
    }
    .app-hero__kicker {
        margin: 0 0 .65rem;
        color: #73d7cf;
        font-size: .95rem;
        font-weight: 700;
        letter-spacing: 0;
    }
    .app-hero h1 {
        margin: 0;
        color: #ffffff;
        font-size: 2.55rem;
        line-height: 1.18;
        font-weight: 800;
        letter-spacing: 0;
    }
    .app-hero__subtitle {
        max-width: 38rem;
        margin: .9rem 0 0;
        color: #c9d7e4;
        font-size: 1.05rem;
        line-height: 1.7;
        letter-spacing: 0;
    }
    .app-hero__visual {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 170px;
    }
    .app-hero__visual img {
        display: block;
        width: 100%;
        max-width: 420px;
        height: auto;
        aspect-ratio: 2 / 1;
        object-fit: contain;
    }
    .app-lede {
        margin: 0 0 1.25rem;
        padding: .15rem .15rem .15rem 1rem;
        color: inherit;
        border-left: 3px solid #ff7063;
        font-size: 1.02rem;
        line-height: 1.75;
        letter-spacing: 0;
    }
    .chat-guide {
        padding: .65rem .25rem 1.1rem;
    }
    .chat-guide__title {
        margin: 0 0 .4rem;
        font-size: 1.12rem;
        font-weight: 750;
        letter-spacing: 0;
    }
    .chat-guide__summary {
        margin: 0;
        color: #9aa6b2;
        line-height: 1.7;
        letter-spacing: 0;
    }
    .chat-guide ul {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .65rem 1.5rem;
        margin: .9rem 0 0;
        padding-left: 1.15rem;
    }
    .chat-guide li {
        padding-left: .15rem;
        line-height: 1.55;
        letter-spacing: 0;
    }
    .chat-guide li::marker {color: #46c8bf;}
    .image-hint {
        margin: -.35rem 0 .85rem;
        color: #9aa6b2;
        font-size: .9rem;
        line-height: 1.55;
        letter-spacing: 0;
    }
    [data-testid="stChatInput"] [data-testid="stChatInputFileUploadButton"],
    [data-testid="stChatInput"] button[aria-label="Attach files"],
    [data-testid="stChatInput"] button[aria-label="Upload files"],
    [data-testid="stChatInput"] button[aria-label="上传文件"] {
        display: none !important;
    }
    .st-key-quick_questions {padding-bottom: 1rem;}
    .st-key-quick_questions [data-testid="stButton"] button {
        min-height: 3.5rem;
        border-radius: 6px;
        white-space: normal;
        line-height: 1.45;
        font-weight: 600;
        letter-spacing: 0;
    }
    .st-key-quick_questions .st-key-refresh_questions [data-testid="stButton"] button {
        min-height: 2.5rem;
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: .75rem;
        border-bottom: 1px solid rgba(128, 128, 128, .35);
    }
    [data-testid="stTabs"] [data-testid="stTab"] {
        min-width: 9rem;
        min-height: 3.25rem;
        padding: .75rem 1.25rem;
        border: 1px solid rgba(128, 128, 128, .35);
        border-bottom: 0;
        border-radius: 6px 6px 0 0;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0;
    }
    [data-testid="stTabs"] [data-testid="stTab"] p {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0;
    }
    [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
        color: #ff4b4b;
        background: rgba(255, 75, 75, .12);
        border-color: rgba(255, 75, 75, .7);
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {height: 3px;}
    [data-testid="stMainMenuDivider"],
    [data-testid="stMainMenuItem-print"],
    [data-testid="stMainMenuItem-recordScreencast"],
    [data-testid="stMainMenuList"] + div {display: none !important;}
    @media (max-width: 720px) {
        .block-container {padding-top: 1rem; padding-left: 1rem; padding-right: 1rem;}
        .app-hero {
            grid-template-columns: 1fr;
            gap: .75rem;
            min-height: 0;
            padding: 1.35rem;
        }
        .app-hero h1 {font-size: 2rem;}
        .app-hero__subtitle {font-size: .98rem;}
        .app-hero__visual {min-height: 110px; max-height: 145px;}
        .app-hero__visual img {max-width: 360px;}
        .chat-guide ul {grid-template-columns: 1fr; gap: .45rem;}
        [data-testid="stTabs"] [role="tablist"] {gap: .5rem;}
        [data-testid="stTabs"] [data-testid="stTab"] {
            flex: 1 1 0;
            min-width: 0;
            padding: .65rem .75rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_retriever(manifest_stamp: float) -> HybridRetriever:
    del manifest_stamp
    return HybridRetriever()


def current_retriever() -> HybridRetriever | None:
    manifest = INDEX_DIR / "manifest.json"
    if not manifest.exists():
        return None
    return load_retriever(manifest.stat().st_mtime)


def set_stream_autoscroll(enabled: bool) -> None:
    if enabled:
        script = """
        <script>
        (() => {
            const host = window.parent;
            const doc = host.document;
            const previous = host.__soundSpeedStreamScroll;
            if (previous) {
                previous.observer.disconnect();
                if (previous.timer) host.clearTimeout(previous.timer);
            }

            const state = { observer: null, timer: null };
            const scrollToLatest = () => {
                state.timer = null;
                const root = doc.querySelector('[data-testid="stMain"]')
                    || doc.scrollingElement
                    || doc.documentElement;
                if (root) root.scrollTo({ top: root.scrollHeight, behavior: "auto" });
            };
            const scheduleScroll = () => {
                if (state.timer) return;
                state.timer = host.setTimeout(scrollToLatest, 80);
            };
            state.observer = new host.MutationObserver(scheduleScroll);
            const target = doc.body || doc.documentElement;
            if (!target) return;
            state.observer.observe(target, {
                childList: true,
                subtree: true,
                characterData: true,
            });
            host.__soundSpeedStreamScroll = state;
            scheduleScroll();
        })();
        </script>
        """
    else:
        script = """
        <script>
        (() => {
            const host = window.parent;
            const state = host.__soundSpeedStreamScroll;
            if (!state) return;
            state.observer.disconnect();
            if (state.timer) host.clearTimeout(state.timer);
            const doc = host.document;
            const root = doc.querySelector('[data-testid="stMain"]')
                || doc.scrollingElement
                || doc.documentElement;
            if (root) root.scrollTo({ top: root.scrollHeight, behavior: "auto" });
            delete host.__soundSpeedStreamScroll;
        })();
        </script>
        """
    components.html(script, height=0, width=0)


def enable_clipboard_image_paste() -> None:
    script = """
    <script>
    (() => {
        const host = window.parent;
        const doc = host.document;
        if (host.__soundSpeedPasteHandler) {
            doc.removeEventListener("paste", host.__soundSpeedPasteHandler, true);
        }

        const handler = (event) => {
            const chatInput = event.target.closest?.('[data-testid="stChatInput"]');
            if (!chatInput || !event.clipboardData) return;

            const images = Array.from(event.clipboardData.items || [])
                .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
                .map((item) => item.getAsFile())
                .filter(Boolean)
                .slice(0, 3);
            if (!images.length) return;

            const fileInput = chatInput.querySelector('input[type="file"]')
                || doc.querySelector('[data-testid="stChatInput"] input[type="file"]');
            if (!fileInput) return;

            const transfer = new host.DataTransfer();
            images.forEach((file, index) => {
                const extension = (file.type.split("/")[1] || "png").replace("jpeg", "jpg");
                const namedFile = file.name && file.name !== "image.png"
                    ? file
                    : new host.File([file], `clipboard-${Date.now()}-${index + 1}.${extension}`, {
                        type: file.type,
                    });
                transfer.items.add(namedFile);
            });
            fileInput.files = transfer.files;
            fileInput.dispatchEvent(new host.Event("change", { bubbles: true }));
            event.preventDefault();
        };

        host.__soundSpeedPasteHandler = handler;
        doc.addEventListener("paste", handler, true);
    })();
    </script>
    """
    components.html(script, height=0, width=0)


def prepare_images(uploaded_files: list) -> list[dict]:
    prepared = []
    for uploaded_file in uploaded_files[:MAX_IMAGE_COUNT]:
        mime_type = uploaded_file.type or ""
        if mime_type not in ALLOWED_IMAGE_TYPES:
            continue
        data = uploaded_file.getvalue()
        encoded = base64.b64encode(data).decode("ascii")
        prepared.append(
            {
                "name": uploaded_file.name,
                "data": data,
                "data_url": f"data:{mime_type};base64,{encoded}",
            }
        )
    return prepared


def render_chat_message(message: dict) -> None:
    images = message.get("images") or []
    if images:
        st.image(
            [image["data"] for image in images],
            caption=[image["name"] for image in images],
            width=260,
        )
    if message.get("content"):
        st.markdown(message["content"])


def render_python_code_runner(content: str, key_prefix: str) -> None:
    """Offer opt-in execution for Python blocks after applying the local blacklist."""
    if not CODE_RUNNER_ENABLED:
        return
    blocks = code_runner.extract_python_blocks(content)
    if not blocks:
        return

    with st.expander("运行回答中的 Python 可视化代码", expanded=False):
        st.caption(
            "执行前会检查受限模块、文件/进程操作和敏感配置访问；"
            "每次运行使用独立输出目录，并受超时限制。请仍只运行你信任的代码。"
        )
        selected = 0
        if len(blocks) > 1:
            selected = st.selectbox(
                "选择代码块",
                options=list(range(len(blocks))),
                format_func=lambda index: f"代码块 {index + 1}",
                key=f"{key_prefix}_code_select",
            )
        timeout = st.slider(
            "超时时间（秒）",
            min_value=5,
            max_value=180,
            value=90,
            key=f"{key_prefix}_timeout",
            help="动画导出通常需要更长时间。",
        )
        if not st.button("运行并显示结果", key=f"{key_prefix}_run_code"):
            return

        code_runner.cleanup_old_runs(CODE_RUNNER_OUTPUT_DIR)
        run_status = st.status("正在隔离目录中运行……", expanded=False)
        try:
            result = code_runner.run_python_block(
                blocks[selected], CODE_RUNNER_OUTPUT_DIR, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            run_status.update(label="计算超时，进程已停止", state="error")
            st.error(f"代码运行超过 {timeout} 秒，已停止。")
            return
        except Exception as exc:
            run_status.update(label="代码运行失败", state="error")
            st.error(f"代码运行失败：{exc}")
            return

        if result.get("blocked"):
            run_status.update(label="代码已被安全策略阻止", state="error")
            st.error(result.get("block_reason", "代码未通过安全检查。"))
            return

        run_status.update(label="代码运行完成", state="complete")
        if result.get("stdout"):
            st.code(result["stdout"], language="text")
            if result.get("stdout_truncated"):
                st.info("标准输出较长，页面仅显示末尾 20,000 个字符。")
        if result.get("stderr"):
            st.code(result["stderr"], language="text")
            if result.get("stderr_truncated"):
                st.info("错误输出较长，页面仅显示末尾 20,000 个字符。")
        if result.get("returncode") != 0:
            st.error(f"Python 进程退出码：{result.get('returncode')}")

        visuals = result.get("visuals") or []
        if not visuals:
            st.info("代码已运行，但没有捕获到 GIF、PNG、JPG、MP4 或 WebM 输出。")
        for path in visuals:
            if path.lower().endswith((".mp4", ".webm")):
                st.video(path)
            else:
                st.image(path, use_container_width=True)


try:
    secret_base_url = st.secrets.get("llm_base_url", LLM_BASE_URL)
    secret_model = st.secrets.get("llm_model", LLM_MODEL)
    secret_api_key = st.secrets.get("llm_api_key", LLM_API_KEY)
except Exception:
    secret_base_url = LLM_BASE_URL
    secret_model = LLM_MODEL
    secret_api_key = LLM_API_KEY

retriever = current_retriever()
top_k = 6
language = None
topic_filter = None
base_url = secret_base_url
model = secret_model
api_key = secret_api_key

header_image = Path(__file__).resolve().parent / "assets" / "sound_speed_header.png"
header_image_data = base64.b64encode(header_image.read_bytes()).decode("ascii")
st.markdown(
    f"""
    <section class="app-hero">
        <div>
            <p class="app-hero__kicker">SPEED OF SOUND · ACOUSTICS LAB</p>
            <h1>声速测量实验智能助教</h1>
            <p class="app-hero__subtitle">传播时间 · 相位比较 · 驻波共振 · 可视化实验</p>
        </div>
        <div class="app-hero__visual">
            <img src="data:image/png;base64,{header_image_data}" alt="音叉振动与纵向声波传播示意图">
        </div>
    </section>
    <p class="app-lede">从传播时间、相位和波长出发，比较不同测量方法，并把公式、波形与真实实验条件连接起来。</p>
    """,
    unsafe_allow_html=True,
)
demo_tab, chat_tab = st.tabs(["演示实验", "智能问答"])

with chat_tab:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "quick_questions" not in st.session_state:
        st.session_state.quick_questions = random.sample(QUICK_QUESTION_POOL, 3)
    quick_question = None
    if not st.session_state.messages:
        st.markdown(
            """
            <section class="chat-guide">
                <p class="chat-guide__title">围绕声波传播、测量与实验展开</p>
                <p class="chat-guide__summary">从理论声速到实验波形，逐步连接测量原理、数据处理与误差分析。</p>
                <ul>
                    <li>回声与双麦克风时间差</li>
                    <li>示波器相位比较与驻波共振</li>
                    <li>环境修正、误差来源与改进方法</li>
                </ul>
            </section>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="quick_questions"):
            quick_title, refresh_action = st.columns([5, 1], vertical_alignment="center")
            with quick_title:
                st.markdown("**快速提问**")
            with refresh_action:
                if st.button(
                    "换一组",
                    icon=":material/refresh:",
                    key="refresh_questions",
                    use_container_width=True,
                ):
                    st.session_state.quick_questions = random.sample(QUICK_QUESTION_POOL, 3)
                    st.rerun()
            quick_columns = st.columns(3)
            for index, prompt in enumerate(st.session_state.quick_questions):
                with quick_columns[index]:
                    if st.button(prompt, key=f"quick_question_{index}", use_container_width=True):
                        quick_question = prompt
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            render_chat_message(message)
            if message["role"] == "assistant":
                render_python_code_runner(message.get("content", ""), f"message_{message_index}")

    st.markdown(
        '<p class="image-hint">点击聊天框后，可按 Ctrl+V 直接粘贴声波波形、示波器截图或实验装置照片。</p>',
        unsafe_allow_html=True,
    )
    enable_clipboard_image_paste()
    submission = st.chat_input(
        "询问声速理论、文献或实验问题",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp"],
        max_upload_size=10,
    )
    typed_question = ""
    uploaded_files = []
    if submission:
        if isinstance(submission, str):
            typed_question = submission
        else:
            typed_question = submission.text
            uploaded_files = list(submission.files)
    images = prepare_images(uploaded_files)
    question = quick_question or typed_question.strip()
    if images and not question:
        question = "请分析这些图片，并结合声速测量实验说明其中的物理现象。"
    if question:
        user_message = {
            "role": "user",
            "content": question,
            "images": images,
            "image_urls": [image["data_url"] for image in images],
        }
        st.session_state.messages.append(user_message)
        with st.chat_message("user"):
            render_chat_message(user_message)
        with st.chat_message("assistant"):
            if not retriever:
                st.warning("知识库暂不可用，请先运行 build_index.ps1。")
            else:
                with st.status("正在检索本地文献并联网搜索...", expanded=False) as thinking:
                    agent = SoundSpeedAgent(
                        retriever,
                        base_url=base_url,
                        model=model,
                        api_key=api_key,
                    )
                    prepared = agent.prepare(
                        question,
                        history=st.session_state.messages[:-1],
                        top_k=top_k,
                        language=language,
                        topic=topic_filter,
                        image_urls=user_message["image_urls"],
                    )
                    thinking.update(label="知识检索完成", state="complete")
                set_stream_autoscroll(True)
                try:
                    with st.spinner("正在生成回答..."):
                        answer = st.write_stream(agent.stream(prepared))
                finally:
                    set_stream_autoscroll(False)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )
                render_python_code_runner(
                    answer, f"message_{len(st.session_state.messages) - 1}"
                )

with demo_tab:
    try:
        with st.spinner("正在启动 Julia 可视化实验..."):
            ensure_julia_web_server()
        render_sound_speed_experiment(JULIA_WEB_URL)
    except Exception as exc:
        st.error(f"Julia 实验启动失败：{exc}")
