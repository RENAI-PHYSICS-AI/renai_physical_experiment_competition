# 声速测量实验智能助教 Windows 单文件版

在项目电脑上运行：

```powershell
./build_onefile.ps1
```

构建内容包括：

1. 本地 RAG 知识库与 Streamlit 应用；
2. 使用 PackageCompiler 生成的独立 Julia/WGLMakie 运行时；
3. 内置中文字体与 WGLMakie 着色器；
4. 本地 Qwen API 凭据的混淆模块；
5. 浏览器心跳、日志与退出后的进程树清理。

最终文件位于 `dist/single/声速测量实验智能助教_单文件版.exe`。首次运行需要先解压内置资源，因此会比后续启动慢。

日志目录：

```text
%LOCALAPPDATA%\SoundSpeedExperimentTutor\logs
```

API Key 不会以明文文件形式进入 exe，但该方式仅适用于内部测试，不能抵御针对性逆向或运行时内存提取。
