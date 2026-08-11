# Julia 交互实验嵌入 Streamlit 网页的实现方法

本文总结本仓库中“李萨如图形实验智能助教”和“声速测量实验智能助教”已经采用并验证的 Julia 网页嵌入方案。目标是在一个 Streamlit 页面内直接运行 Julia/WGLMakie 交互实验，并在单文件版本中做到目标机器无需预装 Python 或 Julia。

## 1. 核心结论

当前方案不是把 Julia 代码翻译成 JavaScript，也不是让 Streamlit 直接执行 Julia 绘图，而是采用两个本机服务、一个用户入口的结构：

- Python/Streamlit 负责主页、智能问答、导航、进程管理和日志。
- Julia/Bonito/WGLMakie 负责物理计算、响应式状态和 WebGL 图形。
- Julia 在本机回环地址上运行一个内部 HTTP/WebSocket 服务。
- Streamlit 使用自定义 HTML 组件把 Julia 页面嵌入“演示实验”标签页。
- 启动器自动分配端口，普通用户不需要填写或访问 Julia 端口。
- 单文件版把编译后的完整 Julia 应用目录一并装入 PyInstaller 包。

因此，“Julia 无需单独给用户一个端口”应理解为：**端口对用户隐藏并由程序管理，而不是技术上完全取消 Julia 服务端口。**

## 2. 总体架构

```mermaid
flowchart LR
    L["单文件启动器"] -->|"启动子进程并注入环境变量"| S["Streamlit 主应用"]
    S -->|"预热或按需启动"| J["Julia PackageCompiler 运行时"]
    B["Edge / Chrome 浏览器"] -->|"唯一用户入口"| S
    S --> C["components.html 嵌入包装层"]
    C -->|"iframe + HTTP/WebSocket"| J
    J -->|"postMessage: ready / failed"| C
    C -->|"client-log"| H["心跳与浏览器诊断服务"]
    L -->|"关闭浏览器后清理进程树"| S
```

本地默认端口如下，但启动器发现端口被占用时会自动选择空闲端口：

| 项目 | Streamlit 默认端口 | Julia 默认端口 |
|---|---:|---:|
| 李萨如 | 8501 | 9384 |
| 声速 | 8502 | 9385 |

两个服务都只绑定 `127.0.0.1`，不会默认暴露到局域网或公网。

## 3. 完整启动时序

### 3.1 启动器选择端口

`packaging/launcher.py` 分别为 Streamlit 和 Julia 检查首选端口。如果端口已占用，则通过绑定端口 `0` 让操作系统分配空闲端口。

选定端口后，启动器把所有路径和端口写入环境变量，例如：

```text
LISSAJOUS_APP_DIR
LISSAJOUS_JULIA_EXE
LISSAJOUS_JULIA_PROJECT_DIR
LISSAJOUS_STREAMLIT_PORT
LISSAJOUS_WEB_PORT

SOUND_SPEED_APP_DIR
SOUND_SPEED_JULIA_EXE
SOUND_SPEED_JULIA_PROJECT_DIR
SOUND_SPEED_STREAMLIT_PORT
SOUND_SPEED_WEB_PORT
```

这样 Streamlit、Julia、嵌入页面和日志系统始终使用同一组运行时端口，避免在不同文件中写死地址。

### 3.2 启动 Streamlit 子进程

启动器以隐藏窗口方式启动 Streamlit 子进程，并访问：

```text
http://127.0.0.1:<streamlit-port>/_stcore/health
```

只有健康检查返回 HTTP 200 后，启动器才打开浏览器。这个检查只说明 Streamlit 已就绪，不代表 Julia 图形已经完成初始化。

### 3.3 提前预热 Julia

两个 `app.py` 都在主页初始化阶段调用：

```python
@st.cache_resource(show_spinner=False)
def prewarm_julia_runtime():
    try:
        return launch_julia_web_server()
    except Exception:
        return None

prewarm_julia_runtime()
```

它的作用是尽早创建 Julia 子进程，使用户阅读主页或使用问答时，Julia 可以并行完成冷启动。`show_spinner=False` 还能避免 Streamlit 显示突兀的英文函数调用提示。

`launch_julia_web_server()` 只负责发起进程，不等待完整 WebGL 图形生成，因此不会把主页一直阻塞到 Julia 完全加载。

### 3.4 用户进入“演示实验”标签页

进入实验页后，Streamlit 再调用 `ensure_julia_web_server()`。该函数执行以下检查：

1. 如果 Julia 端口已经监听，立即返回。
2. 如果已有 Julia 子进程仍在运行，继续等待，不重复启动。
3. 如果没有进程，则创建新的 Julia 子进程。
4. 每 0.5 秒检查一次 TCP 监听状态。
5. 若子进程提前退出，提示用户查看 `julia_web.log`。
6. 超过限定时间仍未监听，则报告启动超时。

当前超时设置为：

- 李萨如：75 秒。
- 声速：90 秒。

### 3.5 嵌入 Julia 页面

确认 Julia 已监听后，Streamlit 使用 `streamlit.components.v1.html()` 写入自定义 HTML。包装层内部再创建一个指向 Julia 地址的 `iframe`：

```html
<iframe id="julia" title="Julia 交互实验"></iframe>
<script>
  frame.src = settings.juliaUrl + "?attempt=" + Date.now();
</script>
```

`attempt=<时间戳>` 用来避免浏览器把前一次失败或未完整加载的页面缓存下来。

这里实际上形成了两层嵌入：

```text
Streamlit 页面
└─ Streamlit components.html 组件 iframe
   └─ Julia/Bonito 页面 iframe
```

之所以不直接使用最简单的 `components.iframe()`，是因为当前包装层还承担加载遮罩、超时提示、WebGL 就绪信号和浏览器端诊断日志等职责。

## 4. Julia 端如何提供网页实验

### 4.1 激活 WGLMakie

Julia 入口先加载便携资源，再激活 WGLMakie：

```julia
load_packaged_wgl_shaders!()
WGLMakie.activate!(; use_html_widgets = true)
configure_theme!()  # 李萨如；声速在构图阶段配置字体
```

WGLMakie 把 Makie 图形转换为浏览器 WebGL 内容；Bonito 管理 HTML DOM、响应式状态以及浏览器与 Julia 之间的 WebSocket 通信。

### 4.2 创建 Bonito 服务

核心结构如下：

```julia
host = get(ENV, "..._WEB_HOST", "127.0.0.1")
port = parse(Int, get(ENV, "..._WEB_PORT", "9384"))
browser_host = get(ENV, "..._WEB_BROWSER_HOST", "127.0.0.1")

server = Bonito.Server(
    host,
    port;
    proxy_url = "http://$(browser_host):$(port)",
)

Bonito.route!(server, "/" => app())
wait(server)
```

`proxy_url` 必须表示浏览器真正能够访问的 Julia 地址。Bonito 会据此生成页面资源和 WebSocket 地址。如果这里仍指向错误端口，即使 TCP 服务已经启动，WGLMakie 也可能停在加载状态。

### 4.3 两个项目的路由方式

李萨如把四个实验设置为四条独立路由：

```text
/phase       相位差
/amplitude   振幅比
/ratio       有理频率比
/detune      频率失谐
```

Streamlit 根据分段控件的选择，把对应路由传给嵌入包装层。每个路由创建独立的 `Bonito.App`。

声速只使用根路由 `/`。回声法、双麦克风时间差法、示波器相位差法和驻波法在同一个 WGLMakie 应用内部切换。

## 5. 为什么要做两级就绪检查

Julia 网页实验的“就绪”至少有两个层级。

### 5.1 第一级：TCP 服务已经监听

Python 使用：

```python
with socket.create_connection((host, port), timeout=0.8):
    return True
```

这里故意不反复请求 Bonito 根页面。首次生成 WGLMakie 页面代价很高，用短超时 HTTP 请求探测根页面容易出现以下问题：

- 服务其实正常，但页面构造超过 HTTP 探测超时，被误判为失败。
- 多次探测会重复给单个 Julia 服务施加昂贵请求。
- 探测请求抢占初始化资源，使真正的浏览器请求更慢。

因此 TCP 连通只表示“Julia 已接受连接”，适合作为进程层就绪信号。

### 5.2 第二级：WebGL 画布真正完成初始化

Bonito 页面中的 JavaScript 持续检查：

```javascript
const canvas = document.querySelector("canvas");
const spinner = document.querySelector(".wglmakie-spinner");

if (canvas && !spinnerVisible) {
  window.parent.postMessage({type: "...-wgl-ready"}, "*");
}
```

外层嵌入包装收到 `postMessage` 后才隐藏加载遮罩。

这比监听 `iframe.onload` 更可靠，因为 `load` 事件只说明 HTML 框架已经载入，不能证明 WebSocket、着色器、WebGL 上下文和 Makie 场景已经就绪。

当前浏览器端超时为：

| 项目 | Julia 页面内部检查 | Streamlit 包装层提示 |
|---|---:|---:|
| 李萨如 | 45 秒 | 60 秒 |
| 声速 | 60 秒 | 70 秒 |

声速构图和初始数据计算更重，因此预留了更长时间。

## 6. 错误诊断与日志

### 6.1 服务端日志

Julia 的标准输出与标准错误被合并写入持久日志：

```text
%LOCALAPPDATA%/LissajousExperimentTutor/logs/julia_web.log
%LOCALAPPDATA%/SoundSpeedExperimentTutor/logs/julia_web.log
```

开发模式下，如果没有设置日志目录，则写入 Julia 项目目录的 `web_stdout.log`。

### 6.2 浏览器端日志

嵌入包装层会记录以下事件：

```text
wrapper-start
iframe-load
iframe-error
wgl-ready
wgl-failed
wrapper-timeout
wrapper-error
wrapper-unhandledrejection
```

这些事件发送到启动器创建的临时心跳服务，再写入浏览器诊断日志。这样可以区分：

- Julia 进程没有启动。
- 端口已经监听，但页面尚未构造完成。
- iframe 已加载，但 WebGL 不可用。
- WebSocket、脚本或浏览器硬件加速发生错误。

李萨如页面还会主动探测 `webgl2` 或 `webgl1`，失败时在页面底部显示浏览器、地址和 WebGL 状态。

## 7. 开发环境与单文件环境的差别

### 7.1 开发环境

开发时由系统 Julia 执行源文件：

```text
julia --project=<Julia项目目录> web.jl --no-instantiate
```

依赖应当提前通过 `Pkg.instantiate()` 安装，用户启动程序时不再在线下载依赖。

### 7.2 单文件环境

单文件版本先使用 PackageCompiler 生成独立 Julia 应用：

```julia
create_app(
    SOURCE_DIR,
    OUTPUT_DIR;
    executables = ["SoundSpeedWebRuntime" => "julia_main"],
    force = true,
    incremental = true,
    include_lazy_artifacts = true,
)
```

李萨如对应 `LissajousWebRuntime.exe`，声速对应 `SoundSpeedWebRuntime.exe`。包装模块的 `julia_main()` 调用同一个 `main()`，并把异常写到标准错误。

当前 PackageCompiler 源项目约束为 Julia 1.10、Bonito 4.2 和 WGLMakie 0.13。升级这些组件时应重新执行冷启动、WebSocket、着色器资源和无开发环境机器测试，而不能只确认编译成功。

PackageCompiler 的产物不是一个可以脱离目录单独复制的 EXE，而是一棵完整运行时目录，例如：

```text
julia_app/
├─ bin/
│  ├─ LissajousWebRuntime.exe 或 SoundSpeedWebRuntime.exe
│  └─ 其他运行时文件
├─ lib/
│  ├─ sys.dll
│  └─ Julia 及依赖库
└─ share/
   ├─ 内置中文字体
   └─ WGLMakie 着色器资源
```

`sys.dll` 是 PackageCompiler 运行时的一部分，不能只保留主 EXE，也不应从其他 Julia 版本手工替换。正确做法是始终保存和打包完整的 `julia_app` 目录。

### 7.3 便携资源处理

WGLMakie 在运行时仍会读取着色器源文件。若只生成 sysimage，里面可能保留构建机器的 Julia depot 路径，换电脑后便会找不到资源。

当前构建脚本会：

1. 复制 `NotoSansCJKsc-Regular.otf` 和字体许可证。
2. 复制 WGLMakie `assets` 目录。
3. 在运行时根据 `Sys.BINDIR` 定位这些相对资源。
4. 把着色器内容重新写入 `WGLMakie.ALL_SHADERS`。

这一步解决了中文字体缺失、旧 artifact 路径失效和构建机绝对路径泄漏等问题。

### 7.4 再封装进 PyInstaller

PyInstaller 的 spec 文件把以下内容写入最终单文件：

```text
app.py
assets/
data/
prompts/
完整 julia_app/
Streamlit、Matplotlib 等 Python 运行时
```

启动后 PyInstaller 解包到 `_MEIPASS` 临时目录。`launcher.py` 使用：

```python
Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
```

找到解包根目录，再设置 Julia EXE 和项目目录。因此目标机器不需要安装 Python、Julia、WGLMakie 或 Bonito。

构建时使用较短的 ASCII 路径，可以降低 OneDrive 路径、中文目录、路径长度和构建工具兼容性带来的风险。

## 8. 当前采用的是 Julia-only 嵌入

李萨如的 `experiment_embed.py` 仍保留一个 `render_hybrid_experiment()` 实验性函数，它可以在 Julia 加载失败时切换到纯 JavaScript 备用实验。

当前正式页面没有调用该函数，而是调用：

```python
render_julia_experiment(...)
```

因此正式实现是 Julia-only：

- 不会在 Julia 与 JavaScript 实验之间自动切换。
- 物理模型、数组、导出和交互状态都以 Julia 为唯一来源。
- 加载失败时显示诊断信息，而不是悄悄换成另一套计算实现。

声速项目同样只有 Julia 实验页面，没有混合回退。

## 9. 进程生命周期

单文件启动器维护一个本地心跳服务，并监控浏览器是否仍连接 Streamlit。浏览器关闭或长时间失去心跳后，启动器会：

1. 停止心跳服务器。
2. 终止 Streamlit 子进程。
3. 递归终止由 Streamlit 启动的 Julia 子进程。
4. 释放 Streamlit 和 Julia 端口。

Julia 进程使用 `CREATE_NO_WINDOW`，避免 Windows 弹出额外控制台窗口；日志仍会写入持久目录。

## 10. 曾出现问题及对应经验

### 10.1 不要用昂贵页面作为短周期健康检查

错误做法：每隔几百毫秒对 `/` 发起 HTTP 请求，并用很短的 HTTP 超时判断 Julia 是否成功。

正确做法：进程层使用 TCP 监听检查；浏览器层使用 canvas、spinner 与 `postMessage` 判断完整就绪。

### 10.2 不要把 `iframe.onload` 当作图形已就绪

Bonito 外壳、WebSocket、WebGL 场景和着色器不是同时完成。必须等待页面主动发出 `wgl-ready`。

### 10.3 不要要求用户管理 Julia 端口

启动器统一选择端口，再通过环境变量传给 Python、Julia 和 iframe。用户只访问 Streamlit 地址。

### 10.4 不要在最终用户机器上执行 `Pkg.instantiate()`

依赖解析、下载和 artifact 安装应发生在构建阶段。最终运行使用 PackageCompiler 应用和 `--no-instantiate`，避免网络、注册表和旧 artifact 下载失败。

### 10.5 不要只复制 Runtime.exe 或 sys.dll

PackageCompiler 应用依赖完整的 `bin`、`lib`、`share` 和 artifact 目录。手工拼接来自不同构建的 DLL 很容易出现 ABI 或资源路径不一致。

### 10.6 不要只延长一个超时

需要区分：

- Streamlit 启动超时。
- Julia TCP 监听超时。
- Bonito/WGLMakie 页面初始化超时。
- 外层包装提示超时。

盲目把所有超时加大，只会延迟报错，不能解决端口、WebSocket、WebGL 或资源缺失问题。

### 10.7 浏览器硬件加速是 WGLMakie 的运行条件

如果浏览器无法创建 WebGL 上下文，Julia 服务即使完全正常也无法显示图形。应优先使用程序自动打开的 Edge 或 Chrome，并启用硬件加速。

## 11. 本机部署与服务器部署的边界

当前单文件方案假定浏览器、Streamlit 和 Julia 位于同一台 Windows 机器，因此 Julia 地址可以使用 `127.0.0.1:<port>`。

如果部署到学校服务器，学生浏览器中的 `127.0.0.1` 指向学生自己的电脑，不能直接访问服务器上的 Julia。服务器部署必须增加反向代理，例如：

```text
https://physics.example.edu/agent/        -> Streamlit
https://physics.example.edu/julia-liss/   -> 李萨如 Bonito 服务
https://physics.example.edu/julia-sound/  -> 声速 Bonito 服务
```

反向代理还必须支持 WebSocket Upgrade，并同步设置：

- Bonito `proxy_url`。
- iframe 的浏览器可见地址。
- CSP `frame-src`。
- 登录鉴权和访问控制。
- HTTPS 下的 `wss://` WebSocket。
- 将当前面向本机的 `postMessage(..., "*")` 改为校验明确的父页面 origin。

不能直接把无鉴权的 Bonito 端口绑定到 `0.0.0.0` 暴露给公网。

## 12. 建议验收清单

### 12.1 Julia 运行时

- `Runtime.exe --self-test` 能完成物理模型与界面构造自检。
- `sys.dll`、Julia 动态库、字体和 WGLMakie 着色器均存在。
- 运行时没有引用构建机器的绝对 depot 路径。

### 12.2 启动与端口

- 默认端口空闲时正常启动。
- 默认端口被占用时可以自动换端口。
- Streamlit 健康检查返回 200。
- Julia TCP 监听成功。
- 关闭浏览器后进程和端口全部释放。

### 12.3 页面交互

- 首次冷启动时加载遮罩正常显示。
- 收到 `wgl-ready` 后遮罩消失。
- 李萨如四条路由均可打开和切换。
- 声速四种方法可以在同一应用内切换。
- 滑块、按钮、播放、重置和导出功能正常。
- 刷新页面后可以重新建立 Bonito/WebSocket 会话。

### 12.4 无开发环境机器

- 在未安装 Python 和 Julia 的干净 Windows 机器上测试。
- 测试普通用户权限、中文路径和离线网络。
- 测试不同 Windows 缩放比例和浏览器硬件加速设置。
- 验证日志可定位启动失败、WebGL 失败和加载超时。

## 13. 主要代码位置

| 功能 | 李萨如 | 声速 |
|---|---|---|
| Streamlit 页面与预热 | `李萨如/李萨如_RAG智能体/app.py` | `声速/声速_RAG智能体/app.py` |
| Julia 进程启动与就绪检查 | `李萨如/李萨如_RAG智能体/tools.py` | `声速/声速_RAG智能体/tools.py` |
| iframe 包装与 ready 消息 | `李萨如/李萨如_RAG智能体/experiment_embed.py` | `声速/声速_RAG智能体/experiment_embed.py` |
| 路径和端口配置 | `李萨如/李萨如_RAG智能体/config.py` | `声速/声速_RAG智能体/config.py` |
| Julia/Bonito/WGLMakie 页面 | `李萨如/李萨如图形可视化实验说明/实验一至四_Julia综合可视化方案/web.jl` | `声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl` |
| 单文件启动与进程监管 | `李萨如/李萨如_RAG智能体/packaging/launcher.py` | `声速/声速_RAG智能体/packaging/launcher.py` |
| PackageCompiler 构建 | `李萨如/李萨如_RAG智能体/packaging/build_julia_app.jl` | `声速/声速_RAG智能体/packaging/build_julia_app.jl` |
| Julia 可执行入口 | `.../packagecompiler_source/src/LissajousWebRuntime.jl` | `.../packagecompiler_source/src/SoundSpeedWebRuntime.jl` |
| PyInstaller 单文件封装 | `.../packaging/lissajous_onefile.spec` | `.../packaging/sound_speed_onefile.spec` |

## 14. 可复用的最小实现顺序

将这一方案迁移到新的 Julia 实验时，建议按以下顺序实施：

1. 在 Julia 中把物理实验封装为 `Bonito.App`。
2. 用 `Bonito.Server` 和明确路由在 `127.0.0.1` 启动服务。
3. 在 Julia 页面中加入 WebGL 完成检测和 `postMessage`。
4. 在 Python 中实现子进程启动、日志和 TCP 就绪检查。
5. 在 Streamlit 中加入带加载遮罩的 iframe 包装层。
6. 通过启动器统一分配 Streamlit 和 Julia 端口。
7. 先完成开发环境的冷启动、刷新和路由测试。
8. 使用 PackageCompiler 生成完整 Julia 应用目录。
9. 显式复制字体、WGLMakie 着色器和运行时资源。
10. 将完整 `julia_app` 目录交给 PyInstaller 封装。
11. 在没有 Python、Julia 和网络的干净机器上做最终验收。

这套方案的核心不是 iframe 本身，而是把**进程管理、端口一致性、两级就绪检查、WebSocket 地址、便携资源和生命周期清理**作为一个整体实现。
