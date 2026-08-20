# PROJECT_STATUS.md — 仁爱物理竞赛项目当前状态

> 更新时间：2026-08-20 ｜ 分支：`main`，HEAD `06903c5 更新最终版`，工作树含未提交改动
> 本文件是项目进展快照，每次工作会话后应同步更新；仓库操作规范见 `AGENTS.md`。

## 1. 当前项目目标

面向第十二届全国大学生物理实验竞赛（创新）自选题，构建两套并行的离线智能助教：

- 李萨如图形实验智能助教（`李萨如/李萨如_RAG智能体`，默认端口 `8501` / `9384`）
- 声速测量实验智能助教（`声速/声速_RAG智能体`，默认端口 `8502` / `9385`）

提供实验原理问答（RAG 检索）、Julia/WGLMakie WebGL 交互可视化、数据处理与 CSV 导出、受限 Python 运行等能力，最终以离线单文件 EXE 交付。

当前阶段目标：“WGL 就绪体验 + CSV 导出持久化 + 启动器加固”增强的代码、契约测试与协作文档已完成；2026-08-20 又完成两套 Qwen 凭据更新、单文件重构建和冻结态离线冒烟，并修正声速报告队员人数与页脚编号 13 的大面积空白。

## 2. 当前总体状态

- 两个项目核心功能已完成，并于 2026-08-13 通过正式验收（当时李萨如 Python 测试 25/25、声速 24/24，Julia 端冒烟通过）。
- 本次 WIP 增强（WGL 就绪 UX + CSV 导出持久化 + 启动器端口池/日志加固）代码与测试已完成，**2026-08-18 完整回归全绿：李萨如 33/33 OK（约 2.8s）、声速 32/32 OK（约 2.0s）**；此前失败的 `test_named_job_child_attaches_before_descendants` 已修复。
- 2026-08-20 更新两套竞赛单文件版的 Qwen 访问凭据：最小在线鉴权返回正常；李萨如 33/33、声速 32/32 测试通过；两套冻结态离线冒烟与内嵌凭据一致性检查通过。正式 EXE 已重建，大小和 SHA-256 已同步到 README 与两份设计报告。
- 声速报告已按四位成员修正贡献表，并将“校内平台与本竞赛专题模块的关系”表提前到 4.2 节首段之后，填补页脚编号 13 的大块空白且保持表格正常字号。
- launcher.log ack 覆盖 bug 已修复（启动器日志调用全部改走 `safe_write_log`，详见第 6 节）。
- 一批改动未提交：21 个修改文件 + 4 个未跟踪文件（`AGENTS.md`、`PROJECT_STATUS.md`、两个项目各一份新增 `tests/test_wgl_readiness.py`），详见第 4 节。
- 2026-08-18 完成“文档与代码”一致性核对，修正 `AGENTS.md` / `PROJECT_STATUS.md` 中与代码不符的表述（CSV 原子写函数名、WGL 慢阈值、加载动画归属），并补齐第 4 节遗漏的两个文件。
- `packaging/dist/` 下的 EXE 产物被 gitignore，不入库；`*.exe *.pdf *.pptx *.ppt *.mp4 *.zip` 走 Git LFS（见 `.gitattributes`）。
- LaTeX 中间产物（`.aux`/`.bbl`/`.log`/`.out`/`.toc`）未入库（已核实），仅跟踪 tex 源文件与最终成品。

## 3. 已完成事项

- 两套 Streamlit + Julia 双进程助教与统一启动器 `packaging/launcher.py`（端口回退、心跳、内嵌 API key）。
- 启动器端口池分离重构（本次 WIP）：李萨如回退端口 Streamlit `18501–18550` / Julia `19384–19433` / 心跳 `19850–19899`；声速回退端口 Streamlit `28502–28551` / Julia `29385–29434` / 心跳 `29850–29899`；由 `select_service_ports()` / `configured_port()` 统一选择，两项目互不冲突。
- `EXPORT_DIR_ENV` + `export_dir()` 回退链：CSV 导出目录可用环境变量 `LISSAJOUS_EXPORT_DIR` / `SOUND_SPEED_EXPORT_DIR` 配置（本次 WIP）。
- `safe_write_log` 修复（本次 WIP）：启动器全部直接日志调用改走 `safe_write_log`（写失败不抛异常、不覆盖已有内容），修复 NamedJob 成功路径 ack 被 PermissionError 覆盖的 bug（见第 6 节）；浏览器启动参数亦有加固。
- Julia 可视化服务 `web.jl`（WGLMakie/Bonito，每项目 4 个实验路由）。
- 受限 Python 执行器 `code_runner.py`（AST 黑名单，仅放行 matplotlib/numpy/scipy/PIL；两个项目各自独立迁移完成）。
- CSV 原子写导出（两项目 `web.jl`，4 条路由全覆盖；函数名两侧不同：李萨如 `write_experiment_csv_atomic`、声速 `write_csv_atomic`，均配合 `unique_export_path` 生成唯一导出文件名）。
- WGL 就绪机制（本次 WIP）：Julia 端初始化超过慢阈值发送 `lissajous-wgl-slow` / `sound-speed-wgl-slow` 消息（阈值两侧不同：李萨如 45 秒 / 声速 60 秒）；包装层 `experiment_embed.py` 在 iframe 加载后超过约定时间未收到 ready 记录 `wrapper-slow`（李萨如 60 秒 / 声速 70 秒）；移除了旧的硬超时；保留加载动画、canvas 隐藏与 300ms 轮询（`.wglmakie-spinner` 样式与 canvas `visibility: hidden !important` 位于 web.jl 页面侧：李萨如含自定义 CSS，声速仅 JS 探测；包装层自有遮罩使用 `.loading`/`.spinner`）。
- 契约测试 `tests/test_wgl_readiness.py`（两项目各一份，新增未提交）：校验慢初始化可恢复与 4 条路由的 CSV 持久化。
- PyInstaller 单文件打包链路（`packaging/build_onefile.ps1`；李萨如另有 `build_installer.ps1` 安装包脚本与 `build_julia_portable.ps1`），Julia 端 `build_julia_app.jl`（PackageCompiler）。
- 离线冒烟脚本 `packaging_offline_smoke.py`（仓库根目录）。
- 设计报告（tex 源、PDF、答辩 PPT、10 分钟讲稿、字幕与自动配音素材，LFS 管理）。
- 正式验收（2026-08-13，见第 2 节）；EXE 体积与 SHA-256 记录在 `README.md`。
- 仓库缓存清理约 293MB、保留全部最终交付物（前次会话记录）。
- 本次会话新增 `AGENTS.md` 与 `PROJECT_STATUS.md`（未提交），并于 2026-08-18 重跑两项目完整回归确认全绿（33/33、32/32）。

## 4. 当前正在进行的工作（WIP，未提交）

主题：WGL 就绪 UX + CSV 导出持久化 + 启动器加固。改动分布（21 个修改 + 2 个新增测试）：

- `李萨如/李萨如_RAG智能体` 与 `声速/声速_RAG智能体`（各 5 个文件）：
  - `app.py`：接入 CSV 导出目录环境变量（`LISSAJOUS_EXPORT_DIR` / `SOUND_SPEED_EXPORT_DIR`）；
  - `experiment_embed.py`：处理新的 slow 消息类型、iframe 加载后超过约定时间未收到 ready 记录 `wrapper-slow` 日志（李萨如 60 秒 / 声速 70 秒），移除旧 `wrapper-timeout` 硬超时逻辑；包装层自有加载遮罩使用 `.loading`/`.spinner`（`.wglmakie-spinner` 样式与 canvas `visibility: hidden !important` 在 web.jl 页面侧）；
  - `packaging/launcher.py`：端口池分离（`STREAMLIT_FALLBACK_PORTS` / `JULIA_FALLBACK_PORTS` / `HEARTBEAT_PORTS`）、`EXPORT_DIR_ENV` / `export_dir()` 回退链、`safe_write_log` 修复、浏览器加固参数；
  - `tests/test_launcher_lifecycle.py`：适配性更新（含 NamedJob attach 顺序契约测试）；
  - 新增 `tests/test_wgl_readiness.py`（读取源码文本做契约校验）；
  - 第 5 个修改文件两侧不同：李萨如为 `packaging/packagecompiler_source/Project.toml`（新增 `Dates` 标准库依赖），声速为 `assets/sound_speed_header.png`（头图资源）。
- Julia 侧：
  - `李萨如/李萨如图形可视化实验说明/实验一至四_Julia综合可视化方案/web.jl` 与 `Project.toml`；
  - `声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl`；
  - 慢阈值两侧不同：李萨如 45000ms / 声速 60000ms（`slowSent` 去重）；原子写函数名亦不同：李萨如 `write_experiment_csv_atomic` / 声速 `write_csv_atomic`。
- 设计报告（两项目）：tex/PDF/配图素材有同步改动（是否与本次 WIP 直接关联待确认）。
- 仓库根：新增 `AGENTS.md`、`PROJECT_STATUS.md`（本次会话，未提交）。

## 5. 尚未完成事项

- 提交范围确认与提交：21 个修改文件 + 2 个新增测试 + `AGENTS.md` / `PROJECT_STATUS.md`；提交前确认不含学生数据与明文密钥（敏感数据规则见 `AGENTS.md`）。
- Julia 端冒烟（本次未跑）：李萨如 5 路由/6 资源、声速 1 路由/2 资源；以及根目录 `packaging_offline_smoke.py`。
- 两套正式单文件 EXE 已于 2026-08-20 重建并通过冻结态离线冒烟；如需重新发布李萨如安装器，仍须另行重建 installer。
- `README.md` 是否补充 CSV 导出说明（导出目录环境变量、原子写行为）：待确认。
- 设计报告/答辩材料是否补充本次 WGL 就绪机制说明：待确认。
- 新提交推送到远端需用户明确确认（当前 `main` 与 `origin/main` 同步于 `06903c5`，尚未产生新提交）。

## 6. 当前已知 Bug 与限制

- launcher.log PermissionError / ack 覆盖 bug（本次已修复）：症状为 `test_named_job_child_attaches_before_descendants` 失败；原因是 `packaging/launcher.py` 的 NamedJob 成功路径裸调 `write_log`，日志文件被占用时抛 PermissionError，把已写入的 `ok:<pid>` ack 覆盖为 `error:...`，导致父进程误判子进程 attach；修复为全部日志调用改走 `safe_write_log`（失败不抛异常、不覆盖）。PermissionError 的根因（文件锁来源：残留实例/杀毒软件/OneDrive 同步等）待确认。
- WebGL（WGLMakie/Bonito）首屏加载在部分环境很慢：目前只能用慢提示 + 加载动画缓解，无法根治（本次 WIP 正是针对该问题的体验改进）。
- Deno 产物镜像 404 且 GitHub 下载超时：李萨如 Julia 自检被阻塞，只能记录为外部依赖阻塞、待网络/镜像恢复后重跑；声速自检通过（前次会话记录）。
- 受限 Python 执行器是 AST 策略级检查，不是 OS 沙箱；“policy 检查通过”不等于安全保证。
- 内嵌 API key 只是混淆（`_embedded_secret.py`），不是加密。
- 旧的 `.venv` 启动器会失败，需重建环境后重新打包（前次会话记录）。
- 服务仅监听 `127.0.0.1`（设计约束，不对外暴露）。

## 7. 已经尝试但失败的方法

- 启动器成功路径直接裸调 `write_log`：在日志文件被锁环境抛 PermissionError 并覆盖 ack，导致契约测试失败；已改为 `safe_write_log`（本次会话）。
- 复用旧 `.venv` 启动器直接运行：失败，结论是重建环境、重新打包（前次会话记录）。
- 依赖 Deno 产物的自检流程：镜像 404/下载超时导致李萨如自检失败，未解决，只能记为外部阻塞（前次会话记录）。
- PowerShell 递归清理命令：受环境限制无法执行，改用有界深度的 Python 脚本完成清理（前次会话记录）。
- 旧的包装层硬超时（45/70 秒 `wrapper-timeout` 报错）：加载最终成功时仍会误报错误、体验差，本次 WIP 改为可恢复的 slow 消息机制。

## 8. 重要架构决策以及为什么这么决定

- Streamlit（Python）+ Julia 双进程、端口分离（李萨如 `8501`/`9384`，声速 `8502`/`9385`）并为两项目配置各自独立的回退端口段：WGLMakie 生态适合物理可视化，Streamlit 交互页面开发快；端口回退避免赛场/教室环境端口冲突；端口池分离避免两项目同时运行时互相占用。
- AST 黑名单受限 Python 执行器：竞赛机离线、无法依赖 OS 沙箱；同时在 README 明确这不是安全边界。
- PyInstaller + PackageCompiler 单文件 EXE：竞赛要求离线一键运行；EXE 属可复现构建产物，`packaging/dist/` 不入 Git。
- 两项目独立目录、独立打包入口（各自 `build_onefile.ps1`）：选题并行、互不依赖，降低耦合与打包风险；不轻易抽取公共核心。
- Git LFS 管理大文件、LaTeX 中间产物不入库：保持仓库干净且可复现。
- CSV 原子写 + 导出目录环境变量可配：避免导出写坏，便于评委/教师自定义导出位置。
- 慢加载消息替代硬超时（Julia 端阈值李萨如 45s / 声速 60s；包装层 `wrapper-slow` 李萨如 60s / 声速 70s）：慢初始化是“可恢复状态”，不应被当作失败处理。
- 关键日志路径统一走 `safe_write_log`：日志是副作用，不应因写日志失败而影响主流程，更不能覆盖已有的关键记录（如 NamedJob ack）。

## 9. 当前关键文件

李萨如线：
- `李萨如/李萨如_RAG智能体/app.py` — Streamlit 主应用
- `李萨如/李萨如_RAG智能体/experiment_embed.py` — Julia 可视化 iframe 包装层
- `李萨如/李萨如_RAG智能体/packaging/launcher.py` — 启动器（端口池/心跳/NamedJob/safe_write_log）
- `李萨如/李萨如图形可视化实验说明/实验一至四_Julia综合可视化方案/web.jl` — Julia 可视化服务
- `李萨如/李萨如_RAG智能体/tests/` — 测试套件（共 33 个测试，含新增 `test_wgl_readiness.py`）
- `李萨如/李萨如_RAG智能体/packaging/build_onefile.ps1`、`build_installer.ps1` — 打包脚本

声速线（结构对称）：
- `声速/声速_RAG智能体/app.py`、`experiment_embed.py`、`packaging/launcher.py`
- `声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl`
- `声速/声速_RAG智能体/tests/`（共 32 个测试）、`声速/声速_RAG智能体/packaging/build_onefile.ps1`

仓库根：
- `README.md` — 使用说明与验收记录
- `packaging_offline_smoke.py` — 离线冒烟脚本
- `AGENTS.md`、`PROJECT_STATUS.md` — AI 协作文档（本次会话新增，未提交）

## 10. 当前环境配置

- Windows 10/11 x64，PowerShell；当前工作区 `D:\OneDrive\文档\我的文件\git\TJRAC\仁爱物理竞赛`
- Python 3.12（uv 管理，各项目独立 `.venv`），Julia 1.10
- 浏览器需支持 WebGL（WGLMakie 渲染）
- 测试命令（在各项目目录下执行；unittest 结果输出在 stderr，PowerShell 中捕获需追加 `2>&1`）：`& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v 2>&1`
- 日志目录：`%LOCALAPPDATA%\LissajousExperimentTutor\logs`、`%LOCALAPPDATA%\SoundSpeedExperimentTutor\logs`
- Git 远端：`git@github.com:RENAI-PHYSICS-AI/renai_physical_experiment_competition.git`（`main` 分支）；大文件走 Git LFS，git 命令如需绕过 LFS smudge 可追加 `-c filter.lfs.smudge=cat -c filter.lfs.clean=cat -c filter.lfs.process= -c filter.lfs.required=false`
- 回归基线（2026-08-18）：李萨如 33/33 OK、声速 32/32 OK

## 11. 下一步建议

1. 确认提交范围（确认不含学生数据与明文密钥）后，提交 21 个修改文件 + 2 个新增测试 + `AGENTS.md` / `PROJECT_STATUS.md`；是否推送 `origin/main` 由用户确认。
2. 运行 Julia 端冒烟（李萨如至少覆盖 5 路由/6 资源、声速 1 路由/2 资源）与根目录 `packaging_offline_smoke.py`。
3. 若准备公开分发，先在模型服务商侧撤销旧凭据，并确认只分发 2026-08-20 重建后的两个单文件 EXE；李萨如 installer 若继续提供，也需同步重建。
4. 视需要补充 README 的 CSV 导出说明和设计报告中的 WGL 就绪机制说明。
5. 关注 Deno 产物镜像/网络恢复后重跑李萨如 Julia 自检。

## 12. 最近一次工作停在哪里

- 本次 WIP（WGL 就绪 UX + CSV 导出持久化 + 启动器加固）的代码、契约测试与 `AGENTS.md` / `PROJECT_STATUS.md` 均已完成，未提交、未推送。
- 2026-08-18 重跑完整回归确认全绿：李萨如 33/33 OK、声速 32/32 OK；此前失败的 `test_named_job_child_attaches_before_descendants` 已通过 `safe_write_log` 修复。
- 2026-08-20 已完成两套密钥更新、33/33 与 32/32 测试、单文件重构建、冻结态离线冒烟、内嵌凭据一致性检查，以及两份报告/README 的版本指纹同步；未重建李萨如 installer，未提交、未推送。
- 2026-08-18 完成“文档与代码”一致性核对并应用上述修正；核对仅修改文档，未改动代码与测试。
