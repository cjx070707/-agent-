"""
文件：app/agent/main_agent.py
所属模块：★★★ 简历① 多 Agent 架构 —— 主 AgentLoop 组装入口
参考原文：globex/14_extract.md
对照真实代码：globex-agent/app/agent/main_agent.py（已实现，本文件是讲解版）
配套验证脚本：../../demos/demo_timeout_guard.py

【做什么】
这是把前面几个文件（llm / prompts / tool_registry / middleware）拼装成
一个真正能跑的 AgentLoop 的地方。`build_agent()` 组装一次、进程内缓存单例；
`run_agent()` 是给外部（比如未来的 FastAPI 层）调用的统一入口。

【解决的问题】
Agent 的各个组成部分（模型、Prompt、工具、中间件、Checkpointer、收敛限制）
分散在不同文件里各自负责一件事，必须有一个地方把它们"组装"起来，否则没人
知道"一个完整可用的 Agent 到底由哪些部分构成"。这个文件就是那个组装点，
也是理解整条架构最好的入口——看这一个文件基本能知道其余文件都在为它做什么。

【输入 / 输出契约】
- `build_agent()`：无输入，输出一个 LangGraph 编译好的 Runnable（同时具备
  `.invoke()` 方法）。
- `run_agent(query: str, thread_id: str)`：输入用户原始 query 和会话
  `thread_id`，输出 Agent 最后一条消息的字符串内容。

【和其他文件的连接 / State 怎么传递】
- `build_agent()` 用 `@lru_cache(maxsize=1)` 缓存，保证**进程内只有一个
  Agent 实例，配一个共享的 `InMemorySaver()`**——这一点很关键：如果每次
  调用都新建一个 Agent（同时新建一个新的 `InMemorySaver`），`thread_id`
  隔离机制会失效，因为每次拿到的都是全新的、空的 checkpoint 存储，"记住
  上一轮对话"这件事根本不会发生。必须是"Agent 对象本身只造一次，
  `thread_id` 只是这个共享 Checkpointer 里的一个 key"，State 隔离才有意义。
- `thread_id` 是整条 State 隔离机制的核心："谁的对话历史"完全由传入的
  `thread_id` 决定：主 Agent 用用户会话自己的 `thread_id`；`dispatch_tool`
  fork 出来的子 Agent 用独立生成的 `sub-*` `thread_id`——**它们调的是
  同一个 `build_agent()`、共享同一个 `InMemorySaver`，只是传了不同的
  `thread_id`，checkpointer 内部会按 key 分桶存取，天然做到隔离**，不需要
  为子 Agent 专门造一个不同的 Agent 对象或不同的存储后端。
- `recursion_limit=MAIN_AGENT_RECURSION_LIMIT`（30）通过
  `config={"configurable": {...}, "recursion_limit": ...}` 传给
  `.invoke()`，这是 LangGraph 框架级的收敛保护，超过这个轮数会直接抛
  `GraphRecursionError`，不需要自己写计数器。

【技术栈】
- `langchain.agents.create_agent`：官方当前推荐的 Agent 组装 API（原文
  用的是已弃用的 `create_react_agent`，这里是版本适配，AgentLoop 本身仍然
  由 LangGraph 执行，行为等价）。
- `langgraph.checkpoint.memory.InMemorySaver`：最简单的 Checkpointer 实现，
  按 `thread_id` 存/取对话历史，进程重启会丢失（生产级应该换成 Redis/
  Postgres 后端，这是阶段 5"工程化收尾"要补的事，目前是有意的教学简化）。

【关键代码片段（帮助理解，非完整实现）】
```python
MAIN_AGENT_RECURSION_LIMIT = 30

@lru_cache(maxsize=1)
def build_agent():
    tool_names = [tool.name for tool in FULL_TOOL_SET]
    return create_agent(
        model=get_llm(),
        tools=FULL_TOOL_SET,
        system_prompt=get_system_prompt(),
        checkpointer=InMemorySaver(),
        middleware=[truncate_long_tool_result, *build_tool_call_limit_middlewares(tool_names)],
    )

def run_agent(query: str, thread_id: str) -> str:
    result = build_agent().invoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": thread_id}, "recursion_limit": MAIN_AGENT_RECURSION_LIMIT},
    )
    return str(result["messages"][-1].content)
```

【一个已知、且有明确原因的真实缺口——300 秒超时保护尚未实现】
原文档配套的保护是 `MAIN_AGENT_MAX_ITERATIONS=30` **+**
`MAIN_AGENT_TIMEOUT_SEC=300`，两者防的故障模式不同（30 轮防"逻辑打转不
收敛"，300s 防"某一步卡死不返回"）。当前代码只做了前者。原因不是遗漏，是
真实的架构依赖：原文写法是
`asyncio.wait_for(main_agent.ainvoke(...), timeout=300)`，要求整条调用链
是异步的，而现在全是同步 `.invoke()`，异步 FastAPI 层还没搭（属于阶段 2
Task 7，尚未开始）。详细的技术选型对比（线程池超时 vs asyncio.wait_for
真取消，两者的真实区别）见 `../../demos/demo_timeout_guard.py`，跑一遍能
亲眼看到"线程池超时不是真取消，后台线程会自己跑完"这个关键差异。

【面试可能被追问】
- "为什么用进程内缓存单例，不是每次请求新建 Agent？" —— 见上面"连接"
  部分：因为 `InMemorySaver` 必须是同一个实例才能让不同 `thread_id` 之间
  真正做到"各自独立、又能各自持久化多轮历史"，新建 Agent 等于新建存储，
  等于每次都是"失忆"的全新会话。
- "InMemorySaver 在多进程部署（比如开了 4 个 worker 进程）下会有什么问题？"
  —— 会出问题：`InMemorySaver` 的数据只存在单个进程的内存里，同一个
  `thread_id` 的后续请求如果被负载均衡分到另一个 worker 进程，那个进程的
  `InMemorySaver` 里根本没有这个 `thread_id` 的历史，等于会话丢失。生产级
  必须换成 Redis/Postgres 这类进程外共享存储，这也是文档里"阶段 5 长期记忆
  持久化"要解决的问题之一。
"""
