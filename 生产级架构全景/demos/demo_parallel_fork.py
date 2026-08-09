"""
模块①核心机制模拟：多 Agent Fork 为什么能让跨平台检索并行提速。

背景（对应 globex/14_extract.md + 你自己写的
globex-agent/app/agent/dispatch_tool.py、fork_guard.py）：

主 Agent 的 LLM 在一轮 Think 里，如果同时对 4 个平台调用 dispatch_tool，
会在一条 AIMessage 里产出 4 个 tool_calls。LangGraph 的 ToolNode 内部
（langgraph/prebuilt/tool_node.py 的 _func）用
`ContextThreadPoolExecutor.map()` 把这 4 个 tool_calls 丢进线程池并发跑，
不是一个个 await 排队执行。

这个脚本不跑真实 LLM（省钱、省时间、结果确定），只还原两件事：

1. 4 个"耗时 I/O 任务"（用 sleep 模拟等 HTTP/LLM 响应），串行 vs 线程池
   并发，时间差有多大——对应简历里"并行检索延迟降低 65%"这句话背后的
   真实机制。
2. 为什么 fork_guard.py 必须依赖 LangChain 的 ContextThreadPoolExecutor，
   不能用 Python 标准库的 ThreadPoolExecutor——因为 fork_guard 用
   ContextVar 记录"当前 fork 深度"，而标准 ThreadPoolExecutor 起新线程时
   不会自动带着调用方的 ContextVar 值过去（新线程会看到默认值），
   ContextThreadPoolExecutor 在 submit/map 时显式 `copy_context()` 后
   在子线程里 `context.run(...)`，才能让子线程"继承"父线程当时的
   fork_depth。

运行方式（要用 globex-agent 的虚拟环境，因为需要 langchain_core）：

    cd "globex-agent 项目目录"
    uv run python "简历内容学习与面试准备/生产级架构全景/demos/demo_parallel_fork.py 的绝对路径"
"""

import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar

from langchain_core.runnables.config import ContextThreadPoolExecutor

# 模拟 4 个平台的检索耗时（网络 I/O，用 sleep 模拟等待 HTTP/LLM 响应的时间）
PLATFORM_LATENCY_SEC = {
    "amazon": 3.0,
    "shopee": 2.0,
    "aliexpress": 2.5,
    "ebay": 1.5,
}


def search_platform(platform: str) -> str:
    time.sleep(PLATFORM_LATENCY_SEC[platform])
    return f"{platform} 返回 3 个候选"


def run_serial() -> float:
    start = time.perf_counter()
    for platform in PLATFORM_LATENCY_SEC:
        search_platform(platform)
    return time.perf_counter() - start


def run_parallel() -> float:
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(search_platform, PLATFORM_LATENCY_SEC))
    return time.perf_counter() - start


# ---- Part 2：验证 ContextVar 在线程池里会不会"丢深度" ----

fork_depth: ContextVar[int] = ContextVar("fork_depth", default=0)


def report_depth(_: str) -> int:
    return fork_depth.get()


def run_with_plain_executor() -> list[int]:
    token = fork_depth.set(1)  # 模拟主 loop 已经进入第 1 层 fork
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            return list(executor.map(report_depth, PLATFORM_LATENCY_SEC))
    finally:
        fork_depth.reset(token)


def run_with_context_executor() -> list[int]:
    token = fork_depth.set(1)
    try:
        with ContextThreadPoolExecutor(max_workers=4) as executor:
            return list(executor.map(report_depth, PLATFORM_LATENCY_SEC))
    finally:
        fork_depth.reset(token)


if __name__ == "__main__":
    serial_time = run_serial()
    parallel_time = run_parallel()
    reduction = (serial_time - parallel_time) / serial_time * 100

    print("=== Part 1：串行 vs 并行耗时对比 ===")
    print(f"串行总耗时: {serial_time:.2f}s")
    print(f"并行(线程池)总耗时: {parallel_time:.2f}s")
    print(f"延迟降低: {reduction:.1f}%")
    print()

    print("=== Part 2：普通 ThreadPoolExecutor 会不会丢 ContextVar ===")
    print(
        f"普通 ThreadPoolExecutor 里子线程看到的 fork_depth: "
        f"{run_with_plain_executor()}  <- 期望是 1，实际很可能全是 0"
    )
    print(
        f"ContextThreadPoolExecutor 里子线程看到的 fork_depth: "
        f"{run_with_context_executor()}  <- 应该全是 1"
    )
