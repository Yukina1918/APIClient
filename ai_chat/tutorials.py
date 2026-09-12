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
   · data/config.json       界面与模型偏好
   · data/keys.json         你的 API Key
   · data/chat/chat_*.txt   聊天记录

Q：会不会读取我的本地文件？
A：不会。本软件只发送你在输入框里写的文字。

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
   · data/chat/chat_*.txt

Q: Does it read my local files?
A: No. It only sends the text you type.

Q: How do I change the language?
A: Use the Language section on the Settings page.

Q: How do I start a new chat or switch history?
A: Use the "📋 History" dropdown on the top-right.

Q: How many context messages are sent?
A: Chat settings → "Context messages", default 20.""",
    },
}