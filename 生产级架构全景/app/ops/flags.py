"""
文件：app/ops/flags.py ｜ ★ 次生产级补丁（原文档无此模块）
说明依据：生产级架构全景/文档/原文档与次生产级差别.md §4

【做什么】
定义「能力级」开关与（讲解用的）流量百分比，让部署代码和放量行为解耦。
灰度时优先拨这里的配置，而不是紧急改业务代码。

【解决的问题】
原文档有组件内降级（如 Reranker 超时跳过精排），但没有「整能力放量控制」。
没有 flag 时，每次行为变更都等于一次发布；有 flag 时，可以先暗发布再放量，
出事时 kill switch 关回安全行为。

【建议覆盖的能力开关（讲解清单，不是可运行配置中心）】
- ENABLE_FORK_PARALLEL：跨平台是否允许一次多路 dispatch_tool
- ENABLE_CACHE_BREAKPOINT：是否启用上下文断点压缩
- ENABLE_THREE_TOWER：item_search 是否走三塔+ANN（关则退回简化检索叙事）
- ENABLE_MEMORY_INJECT：新会话是否注入长期记忆
- GLOBAL_KILL_SWITCH：总闸，打开则只保留最保守路径（例如单 Agent、无 fork）

【和其他文件的连接】
- 被 main_agent / dispatch_tool / item_search / compress / memory 在「决策是否启用
  某能力」时概念上读取（讲解级；本全景不要求真接配置中心）。
- 与 rollback.py 配合：回滚矩阵的动作通常是「把某个 flag 置 false / 降流量」。

【技术栈（次生产级常见选型，原文未指定）】
环境变量、远程配置中心、或专用 feature-flag 服务。理解阶段记住职责即可：
「放量控制是运营配置，不是业务工具」。

【面试怎么说】
「这层不是 Globex 原文章节里的模块，是我们为模拟灰度补的 ops；原文的降级
在召回/工具内部，我们的 flag 管的是能力是否对多少用户打开。」
"""
