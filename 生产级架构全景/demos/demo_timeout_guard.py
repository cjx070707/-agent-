"""
模块①任务 4：给主 AgentLoop 加超时保护 —— 灰度上线前必须补的可靠性任务。

背景：
你自己的 globex-agent/app/agent/main_agent.py 目前只有 30 轮的
`recursion_limit`，没有实现文档（globex/14_extract.md）里配套的
300 秒超时保护。这不是漏写，是有真实的架构依赖：文档里的超时保护是
`asyncio.wait_for(main_agent.ainvoke(...), timeout=300)`，
必须跑在异步的 FastAPI 请求处理器里；而你现在的代码全是同步 `.invoke()`，
异步层还没搭（阶段 2 Task 7 还没做），这个超时暂时没地方挂——这是一个
架构依赖关系，不是随便漏掉的。

这个脚本对比两种"给一个可能挂住的调用加超时"的方案，让你亲眼看到它们的
真实区别：

方案 A（线程池超时，能配合现在的同步代码，但有隐患）：
把 .invoke() 丢进一个线程池，主线程只等 N 秒，超时就不再等，直接返回。
问题：被丢弃的那个线程并不会被真的杀死，它会在后台一直跑到自己结束，
浪费 CPU/网络资源，且如果它最终修改了共享状态（比如写日志、写数据库），
主线程完全不知道——这是一个真实的资源泄漏隐患。

方案 B（asyncio.wait_for 真取消，原文用的方案，需要异步调用链）：
用 asyncio.wait_for 包裹一个 async 协程，超时后会真正把这个协程 cancel 掉
（在下一个 await 点抛 CancelledError），协程内部能捕获这个信号做清理。

运行：
    cd globex-agent
    uv run python "../简历内容学习与面试准备/生产级架构全景/demos/demo_timeout_guard.py"
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError


HANGING_SUB_AGENT_DURATION = 3.0
TIMEOUT_SEC = 1.0


# ---- 方案 A：线程池超时 ----


def fake_sync_agent_invoke() -> str:
    print("  [线程内] 子任务开始执行……")
    time.sleep(HANGING_SUB_AGENT_DURATION)
    print("  [线程内] 子任务执行完毕（此时主线程可能早就不等了）")
    return "done"


def run_with_thread_timeout() -> None:
    print("=== 方案 A：ThreadPoolExecutor + future.result(timeout=...) ===")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fake_sync_agent_invoke)
        try:
            result = future.result(timeout=TIMEOUT_SEC)
            print(f"  主线程收到结果: {result}")
        except FutureTimeoutError:
            elapsed = time.perf_counter() - start
            print(f"  主线程等了 {elapsed:.1f}s 后放弃等待，返回超时错误给用户")
            print("  注意：被丢弃的线程仍在后台运行，几秒后会自己悄悄跑完——")
            print("  继续观察 2 秒，你会看到它自己打印'执行完毕'：")
    time.sleep(HANGING_SUB_AGENT_DURATION)


# ---- 方案 B：asyncio.wait_for 真取消 ----


async def fake_async_agent_ainvoke() -> str:
    try:
        print("  [协程内] 子任务开始执行……")
        await asyncio.sleep(HANGING_SUB_AGENT_DURATION)
        print("  [协程内] 子任务执行完毕")
        return "done"
    except asyncio.CancelledError:
        print("  [协程内] 收到取消信号！执行清理逻辑（比如释放连接、写取消日志），然后真正退出")
        raise


async def run_with_asyncio_timeout() -> None:
    print("=== 方案 B：asyncio.wait_for(..., timeout=...) ===")
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(fake_async_agent_ainvoke(), timeout=TIMEOUT_SEC)
        print(f"  收到结果: {result}")
    except asyncio.TimeoutError:
        elapsed = time.perf_counter() - start
        print(f"  {elapsed:.1f}s 超时，协程已被真正取消，之后不会再打印'执行完毕'")


if __name__ == "__main__":
    run_with_thread_timeout()
    print()
    asyncio.run(run_with_asyncio_timeout())
    print("\n(等待 2 秒，确认方案 B 不会再有输出，方案 A 之前已经打印过'执行完毕')")
    time.sleep(2)
    print("结束。")
