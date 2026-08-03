# 声速测量实验智能助教

本地项目使用 `声速/ref` 中的经典文献和 `声速测量可视化实验说明` 中的实验报告构建 RAG 知识库，并提供声速四种测量方法的 Julia/WGLMakie 网页实验。

## 功能

- 本地文献 TF-IDF + BM25 混合检索；
- Qwen 兼容接口的流式回答与联网搜索补充；
- 在聊天输入框中直接粘贴波形、示波器截图和实验装置照片；
- 回声法、双麦克风时间差法、示波器相位差法、驻波法综合演示；
- 回答流自动滚动，界面仅显示主题模式选择。

## 启动

需要本机安装 `uv`、Julia 1.10 和现代 Edge/Chrome。首次启动会创建 Python 环境、构建知识库并安装 Julia 依赖：

```powershell
cd 声速/声速_RAG智能体
./start_agent.ps1
```

随后访问：

```text
http://127.0.0.1:8502
```

## 模型配置

可通过环境变量配置兼容 OpenAI Chat Completions 的接口：

```powershell
$env:SOUND_SPEED_LLM_BASE_URL="https://example.com/v1/chat/completions"
$env:SOUND_SPEED_LLM_MODEL="model-name"
$env:SOUND_SPEED_LLM_API_KEY="your-key"
./start_agent.ps1
```

也可复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml` 后填写本地密钥。密钥文件已被 `.gitignore` 排除。

## 单独操作

```powershell
# 重建文献索引
./build_index.ps1

# Julia 模型自检
julia --project=../声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web `
  ../声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl --self-test

# Python 测试
./.venv/Scripts/python.exe -m unittest discover -s tests -v
```
