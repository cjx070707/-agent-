"""
文件：app/agent/fork_guard.py
所属模块：★★★ 简历① 多 Agent 架构 —— fork 深度护栏
参考原文：globex/14_extract.md 第 4.2 节"fork 防失控四件套"
对照真实代码：globex-agent/app/agent/fork_guard.py（已实现，本文件是讲解版）
配套验证脚本：../../demos/demo_parallel_fork.py（Part 2）

【做什么】
用一个"当前 fork 深度"计数器，限制子 Agent 内部还能不能再调用
`dispatch_tool` 继续往下 fork。超过上限（2 层）就拒绝，返回一个可读的
错误信息，而不是让程序无限递归下去直到爆栈。

【解决的问题】
主/子 Agent 是同质的、共享完整工具集（包括 `dispatch_tool` 自己），意味着
子 Agent 理论上可以在自己内部再 fork 出孙子 Agent，孙子还能再 fork
曾孙……如果没有硬限制，一次异常的模型决策就可能导致递归 fork 爆炸，
瞬间打满线程池、耗尽 API 配额。`fork_guard` 是这条"动态能力"的确定性刹车。

【输入 / 输出】
- `enter_fork()`：一个上下文管理器（`@contextmanager`），进入时深度 +1，
  超过上限抛 `ForkLimitExceeded`；退出时（无论成功还是异常）自动把深度
  恢复到进入前的值。
- `current_fork_depth()`：读当前深度，用于日志/监控埋点。

【和其他文件的连接 / State 怎么传递 —— 本文件最值得讲的地方】
- 被 `dispatch_tool.py` 包裹调用：`with enter_fork() as depth: ...`。
- 用 `contextvars.ContextVar` 存深度值，不是模块级普通变量，也不是显式
  参数传递。选它的原因：Agent 的调用链是"嵌套 + 并发"的（主 Agent 一次
  Think 可能同时 fork 4 个子 Agent，子 Agent 内部又可能再 fork），普通全局
  变量在并发场景下会被多个分支互相污染，而 `ContextVar` 天然按"调用链"隔离
  ——前提是负责调度的执行器要正确把调用方当时的 context "复制"给每个并发
  分支，而不是让分支共享同一个可变引用，也不是让分支从零开始。
- **这个前提在这里成立，是因为 LangGraph 的 `ToolNode` 底层用的是 LangChain
  自己实现的 `ContextThreadPoolExecutor`，不是 Python 标准库原生的
  `ThreadPoolExecutor`。** 标准库线程池开新线程时不会自动带着调用方的
  `ContextVar` 值过去（新线程会看到默认值 0），`ContextThreadPoolExecutor`
  在分发任务前显式 `copy_context()`，让每个并发分支拿到父级 context 在
  fork 那一刻的快照，分支内部的修改（`+1`）只影响自己的 context 副本，不会
  互相串。这一点在 `demo_parallel_fork.py` 的 Part 2 里有实测验证：
  ```text
  普通 ThreadPoolExecutor:        [0, 0, 0, 0]   <- 丢了
  ContextThreadPoolExecutor:      [1, 1, 1, 1]   <- 对的
  ```

【技术栈】
- `contextvars.ContextVar`：跨调用链透明传递的上下文变量。
- `contextlib.contextmanager`：把"进入+退出自动恢复"的模式写成简洁的
  `with` 语句，异常安全（`finally` 里 `reset`，即使中途抛异常深度也不会
  错乱）。

【关键代码片段（帮助理解，非完整实现）】
```python
_fork_depth: ContextVar[int] = ContextVar("globex_fork_depth", default=0)
MAX_FORK_DEPTH = 2

@contextmanager
def enter_fork():
    cur = _fork_depth.get()
    if cur >= MAX_FORK_DEPTH:
        raise ForkLimitExceeded(f"fork 深度超过上限 {MAX_FORK_DEPTH}")
    token = _fork_depth.set(cur + 1)
    try:
        yield cur + 1
    finally:
        _fork_depth.reset(token)
```

【面试可能被追问】
- "为什么限制是 2 层，不是 1 层或者 3 层？" —— 1 层太死板，连"主 Agent fork
  子 Agent 去做一次跨平台搜索，子任务内部再拆一次子步骤"这种合理场景都不
  允许；层数太深又失去了限制的意义，实际就是在"允许一次合理的二级拆分"
  和"防止失控"之间取一个工程上可接受的折中值，不是靠公式算出来的，是根据
  业务场景（跨平台检索最多两级：主 Agent -> 平台级子 Agent，不需要更深）
  拍定的。
- "如果不用 ContextVar，用参数显式传 depth 会有什么问题？" —— 功能上等价，
  但要求 `dispatch_tool` 之外的每一层调用函数都显式接收和转发 `depth`
  参数，任何一层忘了传就会漏掉限制；`ContextVar` 的好处正是不需要修改中间
  每一层函数签名，是"横切关注点"（cross-cutting concern）的标准解法。
"""
