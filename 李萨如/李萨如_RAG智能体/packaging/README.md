# Windows 安装版构建

该目录用于生成“李萨如图形实验智能助教”的 Windows x64 安装程序。

## 构建

在项目电脑上运行：

```powershell
./build_installer.ps1
```

构建过程会：

1. 从本地 `.streamlit/secrets.toml` 读取 API Key，并生成不入库的混淆模块。
2. 使用 PackageCompiler 生成独立的 Julia/WGLMakie 应用。
3. 使用 PyInstaller 生成包含知识库、Julia 主实验和兼容实验的便携目录。
4. 使用 Inno Setup 生成当前用户安装包。

Julia、PyInstaller 和 Inno Setup 的中间产物会放到短英文暂存路径，避免中文路径兼容性和 Windows 路径长度问题；最终输出位于 `dist/installer/`。安装版默认使用 Julia/WGLMakie 交互实验；若目标浏览器未在 12 秒内完成 WebGL 会话，会自动切换到稳定渲染，同时保留手动兼容模式。

API Key 不会以明文文件形式进入安装包，但这种方式仅适合内部测试，不能抵御针对性逆向或运行时内存提取。
