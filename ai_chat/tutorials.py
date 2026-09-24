# ai_chat/tutorials.py
"""教程正文（中文完整版 + 英文简版，其他语言 fallback 到英文）。"""
from __future__ import annotations

TUTORIALS: dict[str, dict[str, str]] = {

    "tut.api.body": {
        "zh_CN": """【第一步：拿到 API Key】

· OpenAI
  https://platform.openai.com/api-keys
  登录 → Create new secret key → 复制 sk- 开头的密钥。

· DeepSeek（国内直连、价格低）
  https://platform.deepseek.com/api_keys
  登录 → 创建 API Key → 立刻复制（只显示一次）。

· 智谱 GLM
  https://open.bigmodel.cn/usercenter/apikeys

· Kimi（月之暗面）
  https://platform.moonshot.cn/console/api-keys

· 通义千问（阿里云百炼）
  https://bailian.console.aliyun.com/

· OpenRouter（一个 Key 调用多家模型）
  https://openrouter.ai/keys


【第二步：在本软件里配置】

1. 打开「聊天」页，点顶部「聊天设置」按钮。
2. 在「API 选项」里选一个「服务商预设」，
   地址和常用模型会自动填好。
3. 把 API Key 粘贴进去（可点「显示」核对）。
4. 需要的话调整温度（0~2，越大越随机）和超时时间。
5. 点「测试连接」，弹出成功提示就说明通了。
6. 点「保存」。


【常用地址速查】

OpenAI        https://api.openai.com/v1
DeepSeek      https://api.deepseek.com/v1
Kimi          https://api.moonshot.cn/v1
智谱 GLM       https://open.bigmodel.cn/api/paas/v4
通义千问       https://dashscope.aliyuncs.com/compatible-mode/v1
SiliconFlow   https://api.siliconflow.cn/v1
OpenRouter    https://openrouter.ai/api/v1
Groq          https://api.groq.com/openai/v1
Gemini        https://generativelanguage.googleapis.com/v1beta/openai
Ollama（本地）  http://localhost:11434/v1


【想用没列出来的服务商？】

只要它兼容 OpenAI 的 /chat/completions 接口，
就选「自定义 / 其他兼容接口」，手动填地址、Key 和模型名即可。


【需要代理时】

在聊天设置 → API 选项 的「代理」里填写，例如
  http://127.0.0.1:7890
留空表示直连。""",

        "en": """STEP 1 — Get an API key

· OpenAI       https://platform.openai.com/api-keys
· DeepSeek     https://platform.deepseek.com/api_keys
· Zhipu GLM    https://open.bigmodel.cn/usercenter/apikeys
· Kimi         https://platform.moonshot.cn/console/api-keys
· Qwen         https://bailian.console.aliyun.com/
· OpenRouter   https://openrouter.ai/keys


STEP 2 — Configure this app

1. Open the Chat page and click "Chat settings".
2. Pick a provider preset in "API options".
3. Paste your API key.
4. Adjust temperature (0–2) and timeout if needed.
5. Click "Test connection".
6. Click "Save".


ENDPOINT CHEAT SHEET

OpenAI        https://api.openai.com/v1
DeepSeek      https://api.deepseek.com/v1
Kimi          https://api.moonshot.cn/v1
Zhipu GLM     https://open.bigmodel.cn/api/paas/v4
Qwen          https://dashscope.aliyuncs.com/compatible-mode/v1
OpenRouter    https://openrouter.ai/api/v1
Groq          https://api.groq.com/openai/v1
Ollama (local) http://localhost:11434/v1


BEHIND A PROXY?

Fill in the Proxy field, e.g. http://127.0.0.1:7890.""",
    },

    "tut.search.body": {
        "zh_CN": """【原理】

AI 模型本身不能上网。「联网搜索」实际上是本软件在替它上网：

  你的问题
    → 软件调用搜索服务，取回网页标题 + 摘要 + 链接
    → 把这些资料拼进提示词
    → 再发给 AI
    → AI 结合资料给出答案，并用 [1] [2] 标注来源


【最省事：DuckDuckGo（完全免费、不用注册）】

聊天设置 → 联网搜索选项 → 搜索服务选 DuckDuckGo
不用填任何 Key，回到主界面勾选工具栏的「联网搜索」即可。

优点：零配置。
缺点：结果质量一般，国内偶尔被限流。


【推荐：Tavily（专为 AI 设计，有免费额度）】

1. 打开 https://tavily.com 注册账号。
2. 在控制台复制以 tvly- 开头的 API Key。
3. 本软件：聊天设置 → 联网搜索选项 → 服务选 Tavily → 粘贴 Key。
4. 点「保存」，回主界面勾选「联网搜索」。


【其他可选服务】

Serper      https://serper.dev            谷歌结果，注册送免费额度
Brave       https://brave.com/search/api  每月 2000 次免费
Bing        https://portal.azure.com      Azure 的 Bing Search 资源
SearXNG     自建实例，无需 Key


【注意事项】

· 联网会多花几秒，回答更慢是正常的。
· 搜索服务是第三方，请不要在问题里写敏感隐私信息。
· 检索到的内容由搜索引擎决定，请自行判断可信度。""",

        "en": """HOW IT WORKS

The model itself cannot browse the web. "Web search" means this app
does the browsing on its behalf:

  your question
    → the app calls a search service and gets titles, snippets, URLs
    → those results are injected into the prompt
    → the prompt is sent to the model
    → the model answers, citing sources as [1] [2]


EASIEST — DuckDuckGo (free, no sign-up)

Chat settings → Web search → pick DuckDuckGo. No key required.


RECOMMENDED — Tavily (built for AI, free tier)

1. Sign up at https://tavily.com
2. Copy the API key that starts with tvly-.
3. Chat settings → Web search → provider Tavily → paste the key.
4. Save, then tick "Web search" on the main screen.


OTHER PROVIDERS

Serper      https://serper.dev
Brave       https://brave.com/search/api
Bing        https://portal.azure.com
SearXNG     self-hosted, no key needed""",
    },

    "tut.agent.body": {
        "zh_CN": """【它能做什么】

开启「本地办公」后，AI 不再只是聊天，它可以通过工具（Function Calling）：
  · 列出 / 读取 / 写入 / 删除你指定文件夹里的文件
  · 运行白名单内的命令（如 python 脚本）
AI 在云端负责思考与决定动作，本软件在你的电脑上真正执行。


【前提】

  · 所用模型必须支持 Function Calling（DeepSeek、Qwen、gpt-4o、豆包等都支持）。
  · 需要已配置好可用的 API。


【配置步骤】

1. 打开「聊天」页 → 点「聊天设置」→ 找到「本地办公（Agent）」。
2. 勾选「启用本地办公」。
3. 点「浏览」，选择一个专门的办公文件夹（建议新建一个空文件夹，
   例如 D:\\AI_Workspace，不要直接选 C 盘或重要资料目录）。
4. 按需勾选：
     · 文件工具（列 / 读 / 写 / 删）
     · 受限命令工具（白名单）
5. 若启用命令工具，在「命令白名单」里填写允许的程序，逗号分隔，
   例如：python, py, dir, type, where
6. 建议保持「写 / 删 / 执行命令前需要我确认」勾选。
7. 点「保存」。回到聊天页，状态栏会出现「本地办公」字样。


【路径是怎么被「强制锁死」的】

  · AI 的所有文件路径都会被解析到办公文件夹内。
  · 绝对路径、..\\.. 穿越、符号链接、Windows 盘符跳转 → 一律拒绝。
  · 这是代码层面的硬限制，不靠 AI 自觉，无法被提示词绕过。


【命令权限：向管理员（你）申请】

当 AI 想运行一个不在白名单里的程序时，会弹出申请框：
  · 「是」    永久加入白名单并保存
  · 「否」    仅允许这一次
  · 「取消」 拒绝
注意：路径越界属于硬限制，不会提供放行；可申请的只有命令权限。


【会话文件夹结构】

每个话题保存为 data/chat/<年月日>-<时分>_<24位随机数>/，里面按类型分目录：
  chat/<id>.txt   聊天正文
  txt/ json/ py/ java/ html/ js/ css/ md/ ...   各类产出，按需创建
  screenshots/    AI 眼睛的截图
AI 用 write_file 写入的文件，会在真实办公目录里产生，
同时在会话文件夹对应类型目录留一份归档。


【安全建议】

  · 办公目录务必专用、空目录起步，不要放重要文件。
  · 保持「执行前确认」，留意弹窗里的具体动作。
  · 需要更强隔离：可新建一个非管理员 Windows 账户只用于本软件，
    或把整套环境放进虚拟机（可快照、一键还原）。
  · 长时间挂机跑 Agent 会持续消耗 API 额度，注意用量。""",

        "en": """WHAT IT DOES

With Local work enabled, the AI can (via Function Calling):
  · list / read / write / delete files inside a folder you choose
  · run whitelisted commands (e.g. python scripts)
The model plans in the cloud; this app executes on your computer.


REQUIREMENTS

  · A model that supports Function Calling (DeepSeek, Qwen, gpt-4o, Doubao…).
  · A working API key.


SETUP

1. Chat page → Chat settings → "Local work (Agent)".
2. Tick "Enable local work".
3. Click Browse and pick a dedicated folder (e.g. D:\\AI_Workspace;
   never pick C:\\ or a folder with important data).
4. Enable file tools and/or the restricted shell.
5. If using the shell, list allowed programs in the whitelist,
   e.g. python, py, dir, type, where
6. Keep "Ask me before write/delete/run" ticked.
7. Save. The status bar shows "Local work".


HARD PATH LOCK

  · Every path is resolved inside the workspace.
  · Absolute paths, .. traversal, symlinks and drive jumps are rejected.
  · This is enforced in code, not by the model's cooperation.


COMMAND PERMISSIONS

When the AI wants a program not on the whitelist, a prompt appears:
  · Yes = add permanently · No = allow once · Cancel = deny
Path escapes are hard-blocked and can never be approved;
only command permissions can be requested.


SESSION FOLDERS

Each topic is data/chat/<date>-<time>_<24 random chars>/ with subfolders:
  chat/<id>.txt, plus txt/ json/ py/ java/ html/ js/ css/ md/ ... and screenshots/.
Files written via write_file appear in the real workspace and are also
archived in the matching session subfolder.


SAFETY

Use a dedicated empty folder, keep confirmations on, and for stronger
isolation use a non-admin Windows account or a virtual machine. Long
autonomous runs keep consuming API quota.""",
    },

    "tut.vision.body": {
        "zh_CN": """【它是什么】

「AI 眼睛」让 AI 真正“看见”画面：把整屏截图或本地图片，
以图像形式发送给多模态模型。
注意：这是真实图像理解，不是 OCR 文字提取。


【前提】

必须使用支持图片输入的多模态模型，例如：
  gpt-4o / gpt-4.1、qwen-vl / qwen-plus、gemini、
  doubao-vision、claude、glm-4v 等。
纯文本模型（如部分 deepseek-chat）无法看图。


【使用步骤】

1. 在「聊天」页工具栏点「👁 AI 眼睛」。
2. 选择：
     · 「立即截屏并附带」：截取当前整个屏幕
     · 「选择本地图片附带」：从电脑选 png/jpg/jpeg/gif/bmp/webp
3. 可以重复添加多张，状态栏会显示“📷 已附 N 张”。
4. 在输入框正常输入你的问题（例如“帮我看看这个界面哪里有问题”），
   点发送，图片和文字会一起发给模型。
5. 想取消：点 AI 眼睛 → 「清除已附图片」。


【截图保存在哪】

附带的图片会保存到当前会话文件夹的 screenshots/ 目录，方便回看。


【隐私与安全】

  · 截图和图片会被上传到模型服务商的服务器处理，
    请勿包含密码、隐私、敏感信息。
  · 截屏前可以先最小化无关窗口。


【Linux 截屏后端】

  · Wayland：需要 grim
  · X11：scrot / maim / ImageMagick(import) / gnome-screenshot
    若都没有会提示截屏失败，请安装其中一个。
  · Windows 与 macOS 无需额外安装。""",

        "en": """WHAT IT IS

AI Eyes lets the model actually see: it sends a full screenshot or a
local image to a multimodal model. This is real image understanding,
not OCR text extraction.


REQUIREMENTS

A multimodal model that accepts images: gpt-4o / gpt-4.1, qwen-vl /
qwen-plus, gemini, doubao-vision, claude, glm-4v, etc. Text-only
models cannot see images.


HOW TO USE

1. Click "👁 AI Eyes" in the Chat toolbar.
2. Choose "Capture screen now" or "Attach a local image"
   (png/jpg/jpeg/gif/bmp/webp).
3. Add multiple images; the status bar shows how many are attached.
4. Type your question (e.g. "What is wrong with this UI?") and send;
   images and text go together.
5. Use "Clear attached images" to cancel.


WHERE SCREENSHOTS ARE SAVED

Attached images are stored in the session folder under screenshots/.


PRIVACY

Screenshots and images are uploaded to the model provider. Do not
include passwords or sensitive information.


LINUX CAPTURE BACKENDS

Wayland: grim. X11: scrot / maim / ImageMagick import / gnome-screenshot.
Windows and macOS need nothing extra.""",
    },

    "tut.faq.body": {
        "zh_CN": """Q：提示 HTTP 401 / Unauthorized？
A：API Key 填错了或已失效。重新复制一次，注意不要带上空格。

Q：提示 HTTP 404 / 模型不存在？
A：模型名写错了，或者这个账号没开通该模型。

Q：提示 HTTP 429？
A：请求太频繁或额度用尽，等一会儿再试。

Q：提示「请求超时」？
A：网络不通，或需要走代理。在聊天设置的「代理」里填写。

Q：一直不出字？
A：部分推理模型首字很慢，把超时时间调大到 300 秒试试。

Q：回答里有很多 ** 星号？
A：聊天设置 → 聊天优化 → 把「Markdown 精简」调成「标准」或「强力」。

Q：怎么彻底关闭联网搜索？
A：取消勾选工具栏的「联网搜索」即可。

Q：数据保存在哪里？
A：全部在程序同目录的 data/ 文件夹里：
   · data/config.json            界面与模型偏好
   · data/keys.json              你的 API Key
   · data/chat/<日期>_<随机数>/  每个话题一个文件夹，
     内含 chat / txt / json / py / java / html 等分类目录

Q：会不会读取我的本地文件？
A：默认不会，只发送你输入的文字。只有你手动开启「本地办公」并选择
   办公目录后，AI 才能读写该目录内的文件，且路径被强制锁死。

Q：想换语言怎么办？
A：设置页的「语言」区块里切换，或菜单栏「语言」。

Q：怎么新建 / 切换聊天记录？
A：主界面右上角的「📋 聊天记录」下拉可以查看历史并切换。
   点「新建会话」或者菜单「会话 → 新建会话」开始新话题。

Q：聊天记录保存多少条上下文？
A：聊天设置 →「上下文读取条数」默认 20。
   每次请求只携带最近 N 条消息，越多越贵。""",

        "en": """Q: HTTP 401 / Unauthorized
A: Wrong or expired API key. Copy it again with no stray spaces.

Q: HTTP 404 / model not found
A: Misspelled model name, or your account has no access to it.

Q: HTTP 429
A: Too many requests or quota exhausted. Wait and retry.

Q: "Request timed out"
A: Network issue or you need a proxy.

Q: Nothing appears at all
A: Reasoning models can be slow to emit the first token.
   Try raising the timeout to 300 s.

Q: My answers are full of ** asterisks
A: Chat settings → Chat polish → set "Markdown cleanup" to Normal or Strong.

Q: How do I turn web search off completely?
A: Untick "Web search" in the toolbar.

Q: Where is my data stored?
A: All under data/ next to the program:
   · data/config.json
   · data/keys.json
   · data/chat/<date>_<random>/  one folder per topic, containing
     chat / txt / json / py / java / html subfolders

Q: Does it read my local files?
A: Not by default — it only sends the text you type. It can read and
   write files only after you enable Local work and pick a workspace,
   and all paths are hard-locked inside that folder.

Q: How do I change the language?
A: Use the Language section on the Settings page.

Q: How do I start a new chat or switch history?
A: Use the "📋 History" dropdown on the top-right.

Q: How many context messages are sent?
A: Chat settings → "Context messages", default 20.""",
    },
}