<div align="center">

# API 引用器 · AI Chat

**纯 Python 标准库打造的多厂商 AI 聊天客户端**

零依赖 · 单文件运行 · 数据全本地 · 6 语言 · 亮暗主题

[![Python](https://img.shields.io/badge/Python-3.14.7%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![tkinter](https://img.shields.io/badge/UI-tkinter-FF6F00)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)
[![Platform](https://img.shields.io/badge/Platform-Windows%208.1%2B%20%7C%20macOS%20%7C%20Linux-lightgrey)](#)

</div>

---

## ✨ 简介

**API 引用器**（内部代号 `AI Chat`）是一个使用 **Python 3.14 + tkinter 原生控件** 编写的桌面 AI 聊天客户端。

- 🚫 **零第三方依赖** —— 只用 `tkinter` / `urllib` / `json` / `threading`
- 🎨 **完全自绘 UI** —— 不用 ttk 皮肤，亮暗主题递归刷新，颜色精确控制
- 🔐 **数据全本地** —— 唯一网络请求都直接发往你自己填的 API 地址
- 🌐 **12 家 AI 服务商 + 7 种搜索服务** —— 预设 + 自定义，全兼容 OpenAI 协议
- 🗂️ **四个页签** —— 聊天 / 设置 / 线索 / 关于
- 🌍 **6 语言** —— 简体中文、繁體中文、日本語、한국어、English、Русский

---

## 🚀 快速开始

### 方式一：直接运行 exe（Windows）

1. 从 [Releases](../../releases) 下载最新的压缩包，解压后启动 `API引用器Ver4.0.exe`
2. 双击运行 —— 首次启动约 3~5 秒
3. 若杀毒软件拦截，选择「允许运行」（PyInstaller 打包的 Python 程序常被误判）

### 方式二：从源码运行

```bash
git clone https://github.com/Yukina1918/APIClient.git
cd APIClient
python -m ai_chat
