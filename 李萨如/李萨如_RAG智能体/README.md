# 李萨如图形实验智能助教

## 项目内容

本项目使用 `李萨如/ref` 中的文献和 `李萨如图形可视化实验说明` 中的实验文档构建本地知识库。当前功能包括：

- PDF 分页提取、文本清洗和重叠切块；
- Melde 1860 扫描专篇的德文 OCR 与可搜索文字层；
- 文献名、页码、年份、语言和主题元数据；
- 字符级 TF-IDF 向量与 BM25 混合检索；
- 本地文献检索与联网搜索相结合的智能问答；
- Qwen Token Plan（北京区）流式回答，生成内容实时显示；
- 支持在聊天框中直接粘贴李萨如轨迹、示波器截图和实验装置照片进行视觉分析；
- 文献与网页结果仅作为内部依据，不在默认回答中展示来源列表；
- 无语言模型时的离线检索回答；
- 频率比、闭合周期、相位和轨迹形状计算；
- 在网页内直接展示四个独立的 Julia/WGLMakie 可视化实验；
- 可选的多语言稠密语义向量。

## 启动

双击 `start_agent.bat`，或在 PowerShell 中运行：

```powershell
.\start_agent.ps1
```

脚本会自动创建 `.venv`、安装依赖、在缺少索引时构建知识库，然后启动：

```text
http://127.0.0.1:8501
```

## 手动构建索引

```powershell
.\build_index.ps1
```

重新生成 Melde 1860 专篇 OCR（卷内印刷页 513–537，PDF 第 544–568 页）：

```powershell
.venv\Scripts\python.exe ocr_melde.py
```

基础索引完全离线。需要增加稠密语义向量时：

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-embedding.txt
.venv\Scripts\python.exe build_dense_index.py
```

## 模型配置

默认连接 Qwen Token Plan 北京区的 OpenAI-compatible 接口：

```text
https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions
```

API Key 保存在本机 `.streamlit/secrets.toml`，也可以通过环境变量配置：

```powershell
$env:LISSAJOUS_LLM_BASE_URL="https://api.example.com/v1/chat/completions"
$env:LISSAJOUS_LLM_MODEL="model-name"
$env:LISSAJOUS_LLM_API_KEY="your-key"
```

未连接模型时，智能体仍可完成检索、页码引用、参数计算和 Julia 实验启动。

“演示实验”包含四个独立页面：`相位差`、`振幅比`、`有理频率比`和`频率失谐`。
应用会自动启动本机 Bonito 服务并嵌入页面，默认地址为：

```text
http://127.0.0.1:9384
```

## 测试

```powershell
.venv\Scripts\python.exe tests\test_core.py
```

评估问题位于 `tests/evaluation_questions.json`，覆盖相位、频率比、历史、机械摆、示波器和 MEMS 扫描。

## 知识库状态

扫描质量不足的页面会记录在 `data/index/extraction_report.json`，不会生成虚假文本。Melde 1860 第二部分已从年鉴扫描卷中单独提取，并建立逐页德文 OCR 文字层；知识库使用该 25 页专篇，不索引其余无关卷页。
