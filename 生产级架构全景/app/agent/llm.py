"""
文件：app/agent/llm.py
所属模块：★★★ 简历① 多 Agent 架构 —— LLM 统一入口
参考原文：globex/10_基础模块与模型配置_核心提取.md
对照真实代码：globex-agent/app/agent/llm.py（已实现，本文件是讲解版）

【做什么】
封装"如何创建一个大模型客户端对象"，是主 Agent 和所有同质子 Agent 共用的
唯一 LLM 入口。谁想要一个能调用的模型实例，都调 get_llm()，不自己 new
ChatOpenAI。

【解决的问题】
如果每个模块各自 new 一个模型客户端：
1. 模型参数（api_key / base_url / model 名）散落在各处，换模型、换厂商要
   改很多文件。
2. 每次调用都新建一次 HTTP 客户端连接池，浪费资源。
用一层单例包装，保证整个进程只创建一次模型客户端，主/子 Agent 复用同一份。

【输入 / 输出】
- 输入：无参数，配置从 .env 读（OPENAI_API_KEY / OPENAI_BASE_URL / LLM_MAIN）。
- 输出：一个 ChatOpenAI 实例——LangChain 标准 Runnable，支持 .invoke() /
  .stream() / .bind_tools()。

【和其他文件的连接 / State 怎么传递】
- 被 `main_agent.py` 的 `build_agent()` 调用，作为
  `create_agent(model=get_llm(), ...)` 的模型参数。
- 主 Agent 和 `dispatch_tool` fork 出来的子 Agent 都调用同一个
  `build_agent()`，天然共用同一个 `get_llm()` 单例——这是"主/子 Agent
  同质"的技术基础之一：他们不只是工具集一样，连底层模型客户端对象都是
  同一个。
- 本文件不持有任何请求级状态（没有 thread_id、没有对话历史），是纯粹的
  "无状态工厂"，State 隔离的责任在 `main_agent.py` 的 checkpointer，
  不在这里。

【技术栈】
- `python-dotenv`：加载 `.env`。
- `langchain_openai.ChatOpenAI`：OpenAI 兼容协议的模型客户端（这里接的是
  DeepSeek 的 OpenAI-compatible 接口，属于"版本适配"类偏差，不影响架构，
  换成任意 OpenAI 兼容厂商只需要改 `.env`）。
- `functools.lru_cache(maxsize=1)`：最简单的单例实现，延迟到第一次调用才
  真正创建对象。

【关键代码片段（帮助理解，非完整实现）】
```python
@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    settings = get_model_settings()
    return ChatOpenAI(
        model=settings["model"],
        api_key=settings["api_key"],
        base_url=settings["base_url"],
    )
```

【面试可能被追问】
- "为什么用 lru_cache 不用模块级全局变量？"
  效果类似，但 lru_cache 是延迟初始化——第一次真正调用才创建；全局变量在
  模块 import 那一刻就执行，如果 `.env` 还没加载好会直接报错，lru_cache
  版本更安全，也方便测试时 mock。
- "主子 Agent 共用一个模型客户端对象，并发调用安全吗？"
  安全。ChatOpenAI 底层是无状态的 HTTP 客户端，每次 `.invoke()` 是一次独立
  请求，不持有跨请求的可变状态，多线程/多协程共用同一个客户端实例没问题——
  这也是为什么模块①里验证过的"4 个 dispatch_tool 并发跑"敢放心共用同一个
  `get_llm()` 单例。
"""
