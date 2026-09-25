# AI Chat / APIClient v5.2

> 基于 **PyQt6** 的多模型 AI 桌面聊天客户端，兼容任意 OpenAI 协议接口，支持联网搜索、本地办公 Agent、图灵识别（多模态视觉）、亮暗双主题与彩色 Emoji。

## 📋 程序介绍

AI Chat 是一个桌面端大模型聊天工具，面向想要一个干净、可自托管、数据完全本地的 AI 客户端的用户。

- 🔌 **多模型兼容**：任意 OpenAI 兼容接口（DeepSeek、豆包、通义千问、Kimi、OpenRouter、OpenAI 等），可编辑下拉框选择模型，也支持手动输入
- 🎨 **现代 UI**：PyQt6 原生控件，亮色 / 暗色主题一键点击切换；彩色 Emoji 跟随 Windows 系统（Win10 / Win11 自动使用 Segoe UI Emoji）
- 🌐 **联网搜索**：内置 Tavily / SearXNG / Bing / Brave / DuckDuckGo 等搜索服务，回答自动标注来源
- 🛡️ **本地办公 Agent**：代码硬锁工作目录，文件读写 / Shell 命令默认关闭，未知命令弹窗申请权限
- 👁️ **图灵识别**：粘贴截图或本地图片，以真实图像发给多模态模型；图片在聊天区显示预览，并持久化到会话目录
- 📊 **Markdown 渲染**：代码块独立区块（一键复制）、Markdown 表格渲染成真正的表格
- 💾 **数据本地**：所有配置 / Key / 聊天记录都在程序目录的 `data/` 下，不上传任何无关信息
- 📦 **开箱即用**：已打包为单文件 exe，自带 Python 运行环境，双击即用

> ⚠️ 本地文件 / 命令执行功能**默认关闭**，需手动开启；安全防护依靠代码硬校验，请勿把重要私人目录设为工作目录。

## 🚀 快速开始

**方式一：直接运行 exe（推荐）**
```
dist\AIClient5.2.exe
```

**方式二：源码运行（需要 Python 3.10+）**
```bash
pip install PyQt6
python run.py
# 或
python -m ai_chat
```

首次启动后在「聊天设置」里选择服务商预设、填入 API Key 即可开始对话。

## 📂 数据存储

```
data/
  config.json            界面与模型偏好
  keys.json              API Key
  chat/
    {会话id}/
      {会话id}.txt       聊天记录（自定义文本格式）
      images/            该会话的图片
      artifacts/         Agent 产出的文件
```
