# API引用器

一个轻量级多厂商 AI 聊天客户端。纯 Python 标准库实现，无第三方依赖。

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## 特点

- **12 家 AI 服务商**：DeepSeek / OpenAI / Kimi / 智谱 GLM / 通义千问 / SiliconFlow / OpenRouter / Groq / Gemini / Claude / Ollama / 自定义
- **联网搜索**：支持 Tavily / Serper / Brave / Bing / SearXNG / DuckDuckGo 六种服务
- **聊天记录**：本地持久化，支持历史会话切换和重命名
- **6 语言界面**：简体中文 / 繁體中文 / 日本語 / 한국어 / English / Русский
- **亮暗主题**：随时切换
- **纯本地运行**：不收集数据、不上传统计
- **零依赖**：仅使用 Python 标准库

## 系统要求

- Windows 10 / 11（64 位）
- Python 3.12+（从源码运行）

## 快速开始

### 方式一：下载 exe 直接使用

到 [Releases](../../releases) 页面下载最新版压缩包，解压后双击 `API引用器Ver3.0.exe`。

首次使用需要配置 API Key：

1. 点工具栏「设置」
2. 「接口与模型」页 → 服务商预设选「DeepSeek」
3. 粘贴你的 API Key
4. 点「测试连接」→ 成功后点「保存」
5. 回主界面开始聊天

详细步骤见压缩包里的 `食用方法.txt`。

### 方式二：从源码运行

```bash
git clone https://github.com/Yukina1918/APIClient.git
cd APIClient
python -m ai_chat
