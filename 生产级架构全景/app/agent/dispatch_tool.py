"""
文件：app/agent/dispatch_tool.py
所属模块：★★★ 简历① 多 Agent 架构 —— fork 元工具本体
参考原文：globex/14_extract.md
对照真实代码：globex-agent/app/agent/dispatch_tool.py（已实现，本文件是讲解版）
配套验证脚本：../../demos/demo_parallel_fork.py

【做什么】
这是唯一一个"给模型调用、但不做购物业务"的工具——它的作用是创建一个新的
子 AgentLoop，让子 Agent 独立跑完一整套 Think->Act->Observe，最后把它的
最终回复以字符串形式返回给主 Agent。

【解决的问题】
主 Agent 面对"需要并行 / 需要上下文隔离 / 调用链会变深"的子任务时，需要
一个"派发"的手段——不是自己在当前上下文里硬扛，而是开一个干净的新分支去
处理，处理完只拿回一个精简的结果。`dispatch_tool` 就是这个"派发"动作
本身的实现。

【输入 / 输出契约】
- 输入：`demands: str`，一段自然语言描述的子任务需求（比如"在 amazon 上
  搜旅行三件套，预算300，不要塑料"），不是结构化对象——因为下游子 Agent
  要用它去做 LLM 推理，自然语言比结构化 JSON 更适合直接喂给模型。
- 输出：`str`，子 Agent 最后一条消息的内容。**注意这里是字符串，不是
  Pydantic 对象**——这是文档里明确点出的一个稳定性风险点：如果子任务的
  Prompt 没有严格要求"用紧凑 JSON 文本表达结果"，主 Agent 拿到的可能是一段
  自然语言总结而不是可解析的结构化数据，合流阶段的稳定性完全依赖 Prompt
  约束，而不是类型系统保证。

【和其他文件的连接 / State 怎么传递】
- 调用 `fork_guard.enter_fork()` 进入一层 fork，超限时捕获
  `ForkLimitExceeded` 并返回一段可读的拒绝理由（不是让异常一直往外抛炸掉
  主 Agent 的这一轮工具调用）。
- 延迟导入 `main_agent.build_agent`（写在函数体内部而不是文件顶部），避免
  和 `tool_registry.py` 之间的循环依赖：`main_agent` 需要
  `tool_registry.FULL_TOOL_SET`（里面包含 `dispatch_tool`），而
  `dispatch_tool` 又需要调 `main_agent.build_agent`——如果都在文件顶部
  import，两个模块会互相等对方先加载完，形成死锁式的 ImportError。延迟到
  函数体内部 import，等到真正调用这个工具时两个模块都已经加载完毕，问题
  自然消失。
- 子 Agent 的 `thread_id` 是新生成的 `sub-{uuid8}-d{depth}`，和主 Agent
  的 `thread_id` 完全独立——这是"State 隔离"在代码层面的具体落地：子 Agent
  的 checkpointer 记录会存在一个全新的 key 下，读不到主 Agent 的历史，
  主 Agent 也读不到子 Agent 的中间过程，只能拿到 `dispatch_tool` 返回的
  那一段最终字符串。
- 子 Agent 用的 `recursion_limit` 是 `SUB_AGENT_MAX_ITERATIONS = 12`
  （比主 Agent 的 30 小很多）——子任务应该比主任务更快收敛，给它更小的
  轮次上限也是一种防失控设计。

【技术栈】
- `langchain_core.tools.@tool`：把普通 Python 函数变成模型可调用的工具，
  自动从函数签名和 docstring 生成工具的 JSON Schema（模型看到的"工具说明"
  其实就是这个 docstring 的前几行）。
- `uuid.uuid4()`：生成不会冲突的子任务 `thread_id`。

【关键代码片段（帮助理解，非完整实现）】
```python
@tool
def dispatch_tool(demands: str) -> str:
    try:
        with enter_fork() as depth:
            from app.agent.main_agent import build_agent
            sub_thread_id = f"sub-{uuid4().hex[:8]}-d{depth}"
            result = build_agent().invoke(
                {"messages": [{"role": "user", "content": demands}]},
                config={
                    "configurable": {"thread_id": sub_thread_id},
                    "recursion_limit": SUB_AGENT_MAX_ITERATIONS,
                },
            )
            return str(result["messages"][-1].content)
    except ForkLimitExceeded as exc:
        return f"[dispatch_tool 拒绝]: {exc}。建议主 loop 自己处理或换一种拆分方式。"
```

【面试可能被追问】
- "为什么 fork 出来的是同一个 `build_agent()`，不是专门写一个'子 Agent
  类'？" —— 因为设计上主/子 Agent 本来就应该是同质的：同一份 LLM、同一份
  system prompt、同一份工具集，唯一区别只是 `thread_id`（决定了它的 State
  和谁隔离）和 `recursion_limit`（子任务应该更快收敛）。复用同一个
  `build_agent()` 是"同质"这个架构决策在代码上最直接的体现，如果专门写一个
  子类，反而是在architecture上引入了不必要的异构性。
- "主 Agent 一次 Think 里同时 fork 4 个平台，这 4 次 dispatch_tool 调用
  之间会不会互相看到对方的中间状态？" —— 不会。每次调用都会生成独立的
  `sub_thread_id`（哪怕 depth 相同也会因为 uuid 不同而不同），各自的
  checkpointer 记录完全隔离，唯一共享的是无状态的 `get_llm()` 客户端和只读
  的工具集定义，不存在互相污染的可变状态。
"""
