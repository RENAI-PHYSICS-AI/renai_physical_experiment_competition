# AGENTS.md — 仁爱物理竞赛仓库 AI Agent 工作指南

> 适用对象：Codex / Qwen 等 AI Agent。开始任何修改前，请先阅读本文件、`PROJECT_STATUS.md` 与 `README.md`。
> 维护要求：仓库结构、命令或约定发生变化时，请同步更新本文件。

## 1. 项目简介与目标

- 本仓库是 **2026 年第十二届全国大学生物理实验竞赛（创新）自选题 2** 的参赛作品；竞赛通知原文见根目录 `2026年第十二届全国大学生物理实验竞赛 (创新)第一轮通知.pdf`。
- 包含两个相互独立、可平行运行的虚拟实验教学系统：
  - **李萨如图形实验智能助教**（`李萨如/`）：Streamlit 端口 `8501`，内嵌 Julia WebGL 可视化端口 `9384`；
  - **声速测量实验智能助教**（`声速/`）：Streamlit 端口 `8502`，内嵌 Julia WebGL 可视化端口 `9385`。
- 核心能力：RAG 检索增强问答、实验教学、Julia WebGL（WGLMakie）可视化嵌入、受限 Python 代码运行、实验数据 CSV 导出、离线单文件 EXE 打包与安装器。

## 2. 技术栈

- **Python 3.12**（`uv` 管理虚拟环境），Web 框架 **Streamlit**（`>=1.40, <2`）。
- **RAG 与科学计算**：requests、ddgs（在线检索）、PyMuPDF（PDF 解析）、numpy / scipy / scikit-learn / joblib、matplotlib / pillow；可选 sentence-transformers 本地 embedding（`requirements-embedding.txt`）。
- **可视化**：Julia 1.10 + WGLMakie，各自独立 `Project.toml` 环境。
- **LLM**：默认阿里云 token-plan 端点，模型 `qwen3.7-plus`（以各 `config.py` 为准），可用环境变量 `*_LLM_BASE_URL` / `*_LLM_MODEL` / `*_API_KEY` 覆盖。
- **打包**：PyInstaller（Python launcher）+ Julia PackageCompiler；李萨如另有 Inno Setup 安装器。
- **测试**：Python `unittest`（契约 + 单元）；Julia Web 路由/资源冒烟。
- **大文件**：Git LFS，规则见 `.gitattributes`：`*.exe *.pdf *.pptx *.ppt *.mp4 *.zip`。

## 3. 项目目录结构

```text
仁爱物理竞赛/
├─ README.md                          # 项目总说明（安装/运行/测试/打包/安全边界，权威）
├─ AGENTS.md                          # 本文件：AI Agent 工作指南
├─ PROJECT_STATUS.md                  # 项目进展快照
├─ packaging_offline_smoke.py         # 打包产物离线冒烟测试（单文件）
├─ Julia与Python对比.md / Julia嵌入网页实现方法.md / 配音视频录制与字幕添加方法.md
├─ 2026年第十二届全国大学生物理实验竞赛 (创新)第一轮通知.pdf
├─ .imgvenv/                          # 镜像/资源用虚拟环境（勿动）
├─ 李萨如/
│  ├─ 李萨如_RAG智能体/                # Streamlit 应用主体
│  │  ├─ app.py                       # 应用入口（streamlit run app.py）
│  │  ├─ config.py                    # LISSAJOUS_* 前缀环境变量配置
│  │  ├─ code_runner.py               # 受限 Python 执行器（AST 黑名单）
│  │  ├─ experiment_embed.py          # Julia WebGL 嵌入、加载状态与慢加载消息
│  │  ├─ ingest.py                    # RAG 语料入库（生成 data/index/manifest.json）
│  │  ├─ start_agent.ps1              # 一键启动脚本
│  │  ├─ requirements.txt / requirements-embedding.txt
│  │  ├─ data/                        # 语料与索引产物（勿手改）
│  │  ├─ tests/                       # unittest 测试（含 test_wgl_readiness.py）
│  │  └─ packaging/                   # launcher.py / build_onefile.ps1 / build_installer.ps1 / dist/（gitignore）
│  ├─ 李萨如图形可视化实验说明/
│  │  └─ 实验一至四_Julia综合可视化方案/  # Project.toml + web.jl（端口 9384，四个实验路由 + CSV 导出）
│  └─ 设计报告/                        # TeX/PDF/bib/assets/答辩PPT/讲稿/srt/mp4/自动配音版
└─ 声速/
   ├─ 声速_RAG智能体/                  # 与李萨如对称结构，SOUND_SPEED_* 前缀，端口 8502
   ├─ 声速测量可视化实验说明/
   │  └─ 声速四种方法_Julia综合可视化方案/web/  # web.jl（端口 9385）
   └─ 设计报告/
```

## 4. 开发环境

- Windows 10/11 x64 + PowerShell（本仓库脚本均为 PowerShell）。
- `uv`（Python 环境/包管理）、Python 3.12、Julia 1.10、支持 WebGL 的浏览器（Chrome/Edge）。
- Git + **Git LFS**：克隆后必须执行 `git lfs install` 与 `git lfs pull`，否则大文件只是指针文件。
- 网络：Julia 依赖安装、在线检索（ddgs）与 LLM 调用需要网络；离线环境使用打包好的 EXE。

## 5. 安装与启动命令

李萨如首次运行需先初始化 Julia 可视化环境（在 `李萨如/李萨如_RAG智能体/` 目录执行）：

```powershell
julia --startup-file=no --project="..\李萨如图形可视化实验说明\实验一至四_Julia综合可视化方案" -e "using Pkg; Pkg.instantiate(); Pkg.precompile()"
```

启动（在各自项目 `*_RAG智能体/` 目录执行）：

```powershell
.\start_agent.ps1
```

`start_agent.ps1` 行为：uv 创建 `.venv`（Python 3.12）→ `uv pip install -r requirements.txt` → 若 `data/index/manifest.json` 缺失则先运行 `ingest.py` → `streamlit run app.py`（声速另传 `--server.port 8502` 并自动初始化其 Julia web 工程）。

## 6. 构建命令

在各自项目 `packaging/` 目录执行：

```powershell
.\build_onefile.ps1     # 先运行测试，再 Julia PackageCompiler + PyInstaller，输出 dist/single/
.\build_installer.ps1   # 仅李萨如：Inno Setup 安装器，输出 dist/installer/（含 12s WebGL 超时回退）
```

`packaging/dist/` 已 gitignore：**EXE 不提交到仓库**，发布走线下分发，`README.md` 记录其尺寸与 SHA-256。

## 7. 测试命令

在各自项目 `*_RAG智能体/` 目录执行：

```powershell
& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v
```

- 正式验收口径（`README.md` 记录，2026-08-13）：李萨如 25/25 测试 + Julia 5 路由/6 资源冒烟；声速 24/24 测试 + 1 路由/2 资源冒烟。
- 打包产物离线冒烟：根目录 `packaging_offline_smoke.py`。

## 8. 代码风格和约定

- 目录、文档与提交信息使用中文；代码标识符与注释使用英文。
- 配置集中在各项目 `config.py`；环境变量前缀：李萨如 `LISSAJOUS_*`、声速 `SOUND_SPEED_*`（Julia 端口 `*_WEB_PORT`、LLM `*_LLM_BASE_URL` / `*_LLM_MODEL` / `*_API_KEY`、CSV 导出目录 `*_EXPORT_DIR`）。
- 两个子项目保持结构与命名对称（app.py / config.py / code_runner.py / experiment_embed.py / ingest.py / start_agent.ps1 / packaging/ / tests/）。
- PyInstaller launcher（`packaging/launcher.py`）负责双进程编排、端口回退（李萨如 Streamlit 18501-18550 / Julia 19384-19433 / 心跳 19850-19899；声速 Streamlit 28502-28551 / Julia 29385-29434 / 心跳 29850-29899）与内嵌混淆密钥 `_embedded_secret`。
- 提交信息为简短中文描述（参考 `06903c5 更新最终版` 等既有历史）。

## 9. 修改代码时必须遵守的规则

1. **安全边界**：`code_runner.py` 是 AST 黑名单 + 库白名单（仅 matplotlib/numpy/scipy/PIL）的受限执行器，拒绝文件/网络/进程/环境变量/Streamlit-secrets 访问，带超时与独立 `runtime_outputs/run_<uuid>` 输出目录；不得放宽该策略，且要理解它**不是 OS 级沙箱**。
2. **本机绑定**：Julia Web 服务仅绑定 `127.0.0.1`；改动端口须同步修改 config、embed、launcher、测试与文档。
3. **功能开关**：受限执行可用 `LISSAJOUS_CODE_RUNNER_ENABLED=false` / `SOUND_SPEED_CODE_RUNNER_ENABLED=false` 关闭；新增开关遵循既有前缀命名。
4. **WGL 就绪契约**：Julia 侧初始化超过慢阈值发送 `lissajous-wgl-slow` / `sound-speed-wgl-slow` 消息（阈值两侧不同：李萨如 45s（`45000` ms）/ 声速 60s（`60000` ms）），wrapper 侧处理并在 iframe 加载后超过约定时间未收到 ready 时记 `wrapper-slow` 日志（李萨如 60s / 声速 70s）；不要重新引入已移除的 `wrapper-timeout` 硬超时报错路径（契约断言见 `tests/test_wgl_readiness.py`）。
5. **CSV 导出契约**：四个实验路由均提供持久化 CSV 导出（Julia 侧原子写入，函数名两侧不同：李萨如 `write_experiment_csv_atomic`、声速 `write_csv_atomic`，均配合 `unique_export_path` 生成唯一导出文件名），导出目录读环境变量 `LISSAJOUS_EXPORT_DIR` / `SOUND_SPEED_EXPORT_DIR`。
6. **对称修改**：李萨如与声速的同类改动应同步两侧，除非任务明确只针对其一。
7. **测试同步**：改动 app / embed / runner / launcher / web.jl 必须同步 `tests/` 并全绿。
8. **日志位置**：运行日志写入 `%LOCALAPPDATA%\LissajousExperimentTutor\logs` 与 `%LOCALAPPDATA%\SoundSpeedExperimentTutor\logs`，不要写进仓库。
9. **大文件意识**：新增 `*.exe *.pdf *.pptx *.mp4 *.zip` 等类型会经 LFS，提交前确认必要。
10. **不擅自提交**：未经用户明确要求并确认范围，不执行 `git commit` / `git push`。
11. **文档同步**：改动仓库结构、命令、端口、约定或工作重点时，同步更新 `AGENTS.md`、`PROJECT_STATUS.md`（含“更新时间”与“最近一次工作停在哪里”）与 `README.md`，保持文档与代码一致；本次新增的两份文档本身也须随进展维护。

## 10. 不要随意修改的文件/目录

- `*/data/index/`：RAG 索引产物，由 `ingest.py` 重新生成。
- `*/packaging/dist/`：构建产物（gitignore），勿手工编辑。
- `.gitattributes` / `.gitignore`：LFS 与忽略规则，改动需用户确认。
- `2026年第十二届全国大学生物理实验竞赛 (创新)第一轮通知.pdf`：竞赛原始通知。
- `设计报告/` 下的 PDF：必须与对应 `.tex` 同步重新编译后替换，不能单独修改。
- `*/tests/evaluation_questions.json`：评测题目数据，改动影响评测口径。
- `.venv/` / `.imgvenv/`：虚拟环境目录。
- `ref/`（如存在）：第三方参考资料，有版权约束。

## 11. Git 工作流

- 单分支 `main`；远端 `origin` = `git@github.com:RENAI-PHYSICS-AI/renai_physical_experiment_competition.git`（GitHub 组织 RENAI-PHYSICS-AI）。
- 提交流程：`git status` 确认改动范围 → 排除 `.venv/`、`packaging/dist/`、临时文件 → 中文提交信息 → 用户确认后推送。
- 必须可用 Git LFS；只读 git 命令若因 LFS smudge/clean 报错，可临时附加参数 `-c filter.lfs.smudge=cat -c filter.lfs.clean=cat -c filter.lfs.process= -c filter.lfs.required=false`。
- 隐私与安全：学生数据、密钥等敏感信息不得入库；代码中的密钥是混淆而非加密。
- 配置好 origin ≠ 已推送；任何推送以用户确认为准。

## 12. 常见问题

- **拉下来的大文件只有几行指针文本**：未安装 Git LFS 或未执行 `git lfs pull`。
- **启动失败/端口冲突**：`8501/8502/9384/9385` 被占用；EXE launcher 会自动尝试回退端口池，开发模式需手动释放端口。
- **Julia 依赖安装失败**：网络或上游镜像异常（已知案例：Deno artifact 404 阻断李萨如 Julia 自检）；重试或等上游恢复；声速自检不受该问题影响。
- **EXE 启动失败**：旧 `.venv` 里打包的 launcher 不可靠，务必干净环境重新执行 `build_onefile.ps1`。
- **WebGL 页面加载慢/白屏**：WGLMakie 首次加载慢，现有 spinner + 慢加载消息（Julia 侧李萨如 45s / 声速 60s；wrapper 侧李萨如 60s / 声速 70s）+ 安装器 12s 超时回退兜底；属体验缓解而非根治。
- **策略测试通过 ≠ 验收通过**：`code_runner` 的策略检查只覆盖语法/策略层，完整验收需 unittest + 真实执行 + EXE 重建 + 启动冒烟。

## 13. AI Agent 开始工作前应检查什么

1. 阅读 `README.md`、本文件与 `PROJECT_STATUS.md`（重点看“当前正在进行的工作”和“下一步建议”）。
2. `git status` 与 `git log -1`：确认当前分支与未提交改动（本仓库常有 WIP 改动，避免混淆或误提交）。
3. 确认改动目标属于哪个子项目（李萨如 / 声速 / 根目录文档），以及是否需要对另一侧做对称同步。
4. 检查 `.venv/` 是否存在（决定测试命令能否直接执行）。
5. 涉及 Julia 时确认对应 `Project.toml` 环境已 instantiate。
6. 涉及大文件时确认 Git LFS 已安装。

## 14. 完成修改后必须进行的验证

1. 受影响项目跑全量测试：`& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v`，必须全绿（含 `test_wgl_readiness.py`）。
2. 启动冒烟：`.\start_agent.ps1` → 页面可打开、问答可用、Julia 可视化嵌入可加载、CSV 导出正常（如涉及）。
3. 改动 Julia 工程时：启动 `web.jl` 并按 `README.md` 口径做路由/资源冒烟。
4. 改动打包链路时：重新执行 `build_onefile.ps1`，再跑根目录 `packaging_offline_smoke.py` 离线冒烟。
5. `git status` 复查改动范围，确认无 `.venv/`、`dist/`、临时文件等误报。
6. 向用户报告已完成与未完成的验证（如“EXE 未重建”“未推送”）；不得把未验证内容描述为已完成。
