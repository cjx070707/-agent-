"""
文件：app/agent/tool_registry.py
所属模块：★★★ 简历① 多 Agent 架构 —— 工具集注册表
参考原文：globex/09_Globex项目重点提取.md、globex/14_extract.md
对照真实代码：globex-agent/app/agent/tool_registry.py（已实现，本文件是讲解版）

【做什么】
把 9 个业务工具 + 1 个 fork 元工具（`dispatch_tool`）收拢成一个列表
`FULL_TOOL_SET`，给 `main_agent.py` 的 `create_agent(tools=...)` 用。

【解决的问题】
- 工具从哪里来、给谁用，需要一个唯一的"清单"，不能让每个调用方各自 import
  一堆工具函数、自己拼列表——那样容易漏工具、容易两处清单不一致。
- 更重要的是：**主 Agent 和子 Agent 用的是同一个 `FULL_TOOL_SET`**，这正是
  "同质子 Agent"的字面体现——子 Agent 不是拿到一个"阉割版"工具集，是完整
  的复制品，包括它自己也能再调 `dispatch_tool` 继续 fork（受 `fork_guard`
  深度上限保护）。

【输入 / 输出】
- 无输入，是一个模块级常量列表。
- 输出：`FULL_TOOL_SET: list`，10 个 `@tool` 装饰过的可调用对象。

【和其他文件的连接 / State 怎么传递】
- 依赖：`app/tools/*.py` 的 9 个业务工具 + `app/agent/dispatch_tool.py`。
- 被 `main_agent.py` 消费：`create_agent(tools=FULL_TOOL_SET, ...)`。
- 还留着一个 `PHASE_ONE_TOOLS = [item_search, price_compare]` 常量——这是
  项目早期"两工具最小 AgentLoop"阶段的产物，现在的正式组装已经不用它了，
  是开发过程中留下的历史痕迹，不是 bug，但如果读代码时看到要能分清"这是
  历史遗留，不是当前架构的一部分"。

【技术栈】
- 纯 Python list，没有额外框架依赖——工具注册在 LangChain 里就是"把
  `@tool` 函数放进一个 list"这么简单，复杂度都在工具本身和 Agent 组装上。

【关键代码片段（帮助理解，非完整实现）】
```python
FULL_TOOL_SET = [
    planner,
    item_search,
    price_compare,
    shipping_calc,
    category_insight,
    item_picker,
    shopping_summary,
    chat_fallback,
    web_search,
    dispatch_tool,
]
```

【面试可能被追问】
- "9 个业务工具 + dispatch_tool，一共是几个工具？" —— 10 个可调用对象，
  但概念上要分清楚：`dispatch_tool` 是"fork 元工具"，不算进"9 个业务工具"
  的计数里，它自己不做任何购物业务，只负责创建子 Agent 并转发结果。这是
  文档里明确强调过的边界，容易被面试官拿来试探你是不是真的理解架构，还是
  背了个"9"这个数字。
"""
