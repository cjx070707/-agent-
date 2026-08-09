"""
文件：app/agent/middleware.py
所属模块：★★★ 简历① 多 Agent 架构 —— 防失控中间件
参考原文：globex/14_extract.md 第 4.2 节"fork 防失控四件套"
对照真实代码：globex-agent/app/agent/middleware.py（已实现，本文件是讲解版）

【做什么】
两件独立的防护，都是通过 LangChain 的 middleware 机制挂到 Agent 执行流程
里，不需要改工具本身的代码：
1. `truncate_long_tool_result`：任何工具的返回结果超过 16000 字符，自动
   截断并附带提示（建议模型缩窄查询参数）。
2. `build_tool_call_limit_middlewares`：给每个业务工具各配一个限流器，
   同一次 run 里同一个工具最多调 4 次，超限后拦截这次调用但不终止整个
   Agent 运行。

【解决的问题】
30 轮迭代上限、fork 深度上限，防的是"整体不收敛"和"递归失控"，但还有两种
更细粒度的失控模式它们防不住：
- 单个工具一次性返回超长结果（比如某个平台一次返回了几百个商品），瞬间把
  一大段无意义的原始数据塞进 Agent 的对话历史，挤占后续 Think 的有效上下文。
- 模型陷入"反复调同一个工具、参数几乎不变"的死循环（比如反复搜同一个词，
  因为它没意识到已经搜过了）——这种情况下 30 轮很快就会被无意义地耗尽，
  但每一轮单独看"好像都在做事"，不容易靠轮次上限直接发现。
这两个中间件是对前两层护栏的补充，四层放在一起才是文档说的"纵深防御"。

【输入 / 输出】
- `truncate_long_tool_result`：包裹一个工具调用，输入输出都是
  `ToolMessage`，超长时把 `.content` 换成截断版。
- `build_tool_call_limit_middlewares(tool_names)`：输入工具名列表，输出
  一组 `ToolCallLimitMiddleware` 实例。

【和其他文件的连接 / State 怎么传递】
- 都在 `main_agent.py` 的 `build_agent()` 里通过
  `create_agent(middleware=[...])` 挂进去，成为 Agent 执行图上"工具调用"
  这一步前后自动触发的钩子，业务工具本身完全不知道自己被包了一层。
- 和 `fork_guard.py` 是同一层级的"防失控设施"，但作用范围不同：
  `fork_guard` 管的是"要不要允许开一个新的子 Agent 分支"，`middleware`
  管的是"单个 Agent（无论主还是子）内部的工具调用行为是否健康"。

【技术栈】
- `langchain.agents.middleware.ToolCallLimitMiddleware`：框架自带的调用
  计数限流器，`exit_behavior="continue"` 表示超限只拦这一个工具，不杀掉
  整条 Agent 运行（呼应原文 LoopDetector"提示换策略而不是直接杀死流程"的
  设计意图）。
- `langchain.agents.middleware.wrap_tool_call`：装饰器式的工具调用拦截点，
  能拿到调用前后的完整上下文（request/handler），比"改工具函数本身"更
  通用——同一个装饰器可以套在任意工具上，不用每个工具各写一份截断逻辑。

【关键代码片段（帮助理解，非完整实现）】
```python
MAX_SAME_TOOL_CALLS_PER_RUN = 4
MAX_TOOL_RESULT_CHARS = 16000

@wrap_tool_call
def truncate_long_tool_result(request, handler):
    result = handler(request)
    if len(result.content) <= MAX_TOOL_RESULT_CHARS:
        return result
    truncated = result.content[: MAX_TOOL_RESULT_CHARS - 200] + "\n\n[已截断]"
    return result.model_copy(update={"content": truncated})

def build_tool_call_limit_middlewares(tool_names):
    return [
        ToolCallLimitMiddleware(tool_name=name, run_limit=4, exit_behavior="continue")
        for name in tool_names
    ]
```

【面试可能被追问】
- "16000 字符这个阈值怎么定的？" —— 代码注释里写了换算逻辑："约等于原文
  4000 token * 4 字符/token 的粗略换算"。这是一个真实的工程简化：中文/英文
  混合文本很难用字符数精确估算 token 数，4 字符≈1 token 是英文场景的粗略
  经验值，中文场景通常 1-2 字符≈1 token，所以这个换算在中文占比高的场景下
  会偏保守（更容易提前截断）——这是一个可以主动指出的"已知局限"，比硬答
  "刚好算出来的"更有说服力。
- "和原文的差异在哪？" —— 原文的重复调用检测是"滑动窗口"（最近 6 次里同一
  工具出现 4 次就触发），这里简化成"整次 run 硬计数上限"（同一工具总共不超
  4 次）。滑动窗口更宽松（允许"先密集调用后冷却"的正常模式），硬计数更严格
  也更简单——这是有意识的工程简化，不是理解错了原文。
"""
