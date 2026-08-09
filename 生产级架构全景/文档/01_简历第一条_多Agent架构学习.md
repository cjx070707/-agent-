# 简历第一条学习文档：多 Agent 架构（主 Agent + Fork 子 Agent）

> 对应简历表述（意译）：多 Agent 架构选型与落地——主 Agent + fork SubAgent，解决单 Agent 上下文爆炸；主 loop 30 轮 / 300s；跨平台并行检索相对串行延迟约降 65%。  
> 原文依据：`globex/03_0`、`03_1`、`11`、`14`；全景讲解：`app/agent/*`；验证脚本：`demos/demo_parallel_fork.py`、`demo_timeout_guard.py`。  
> 用法：面试口述用 §1；啃代码用 §2–3；讲「为什么像生产」用 §4；内化经历用 §5（模拟实习叙事，按「可辩护」写，勿把模拟说成编造数据）。  
> **同步/并发/异步**：全景目标=第3档，简历①深挖仍以并行为主——见 `02_同步_并发_异步定稿.md`（已定稿，学习改动不大）。

---

## 0. 和「全异步」的关系（先读 30 秒）

- 次生产级**目标形态**是第3档全链路异步（`app/api` + `ainvoke` + `wait_for`）。  
- 简历①要拷打的是：**同质 fork + 同轮多 dispatch 并行 + 防失控**；~65% 来自并行，不是来自「写了 async」。  
- 学习优先级：**并行与护栏 ≫ 异步形态（能口述即可）**。不必因定稿 A 重学一整条 async 重构。

---

## 1. 详细面试介绍（建议背框架，用自己的话讲）

### 1.1 30 秒版（开场）

我们做的是跨境购物对话 Agent。用户一句需求往往要同时查多个平台，如果全塞进一个 Agent，会出现三类问题：上下文被中间检索污染、平台检索串行等太久、子链路太深导致主线决策变慢。所以架构上选了**一个主 AgentLoop + 按需 fork 的同质子 AgentLoop**：主 Agent 负责理解、合流、比价精挑和收尾；跨平台检索这类同质、可并行的子任务，用 `dispatch_tool` 派出去，子 Agent 用独立 `thread_id`/checkpoint 跑完，只把压缩后的结果字符串交回主线。主任务有 **30 轮迭代 + 300 秒超时**，并配合 fork 深度、工具循环检测、结果截断做纵深防御。压测口径下，跨平台并行相对串行，端到端延迟大约能降 **六成多（简历写 65%）**。

### 1.2 2–3 分钟版（完整故事）

**业务背景**  
不是「接一个搜索 API 出列表」，而是长链路决策：拆需求 → 品类洞察 → 多平台搜 → 比价 → 到手价 → 按偏好精挑 → 清单。信息源多、步骤多、还要可观察。

**为什么不是异构多 Agent（搜索 Agent / 比价 Agent 各一套）**  
多平台检索本质是**同类型任务**（同一套工具、同一套推理规范，只是 platform 不同）。异构拆分会带来 prompt/工具边界维护成本，且比价、运费本身是合流后的确定性计算，不需要独立「角色 Agent」。我们选的是 **同质 fork**：子 Agent = 主 Agent 的克隆（同 LLM、同 system prompt、同 `FULL_TOOL_SET`），差异只在 State 隔离。

**怎么跑起来**  
主 Agent 每轮 Think → 决定自己调工具还是 `dispatch_tool(demands)`。跨 4 平台时，理想路径是**一轮里发出多个 `dispatch_tool` 的 tool_calls**；LangGraph 的 ToolNode 用带 Context 传播的线程池并发执行，I/O 等待重叠，总耗时≈最慢一路。子 Agent 跑完只返回最终 Observation（字符串；Prompt 约束尽量吐紧凑 JSON）。主 Agent 再调 `PriceCompare` / `ShippingCalc`（**不 fork**）→ `ItemPicker` → `ShoppingSummary`（终结）。

**怎么保证不失控**  
- 30 轮：防「一直调工具不收敛」  
- 300s：防「某步卡死不返回」（与轮次是不同故障模式）  
- fork 深度上限（如 2）：防递归 fork 爆炸  
- 同工具次数限制 + 超长结果截断：防死循环刷工具 / 一次撑爆上下文  

**你负责什么（面试角色定位）**  
参与主/子组装与 `dispatch_tool`、防失控参数与 Prompt 约束、并行 vs 串行延迟对比、合流稳定性与回归用例；不声称从零写了 LangGraph 调度内核。

### 1.3 高频追问速答

| 问题 | 答法要点 |
|---|---|
| 同质 vs 异构？ | 同质=克隆自己；异构=不同角色/工具。多平台搜适合同质。 |
| 何时 fork？ | 能并行 / 要隔离上下文 / 子链路深（≥3 步）。比价运费不 fork。 |
| 子 Agent 返回什么？ | 字符串 Observation，不是 Pydantic；结构化靠 Prompt，这是已知风险点。 |
| 65% 怎么来的？ | 固定跨平台 query；对比「禁用并行 fork（串行）」与「一轮多 tool_calls 并行」；串行≈各平台耗时和，并行≈max；我们本地用 sleep 模拟 I/O 得到约 66.7%，与 65% 同量级。 |
| 只靠 30 轮够吗？ | 不够；还要深度、超时、循环、截断，纵深防御。 |
| ContextVar 干嘛？ | 跨调用链记 fork 深度；并发下必须用会 `copy_context` 的执行器，否则子线程深度全丢成 0。 |
| Agent 还是 workflow？ | 下一步工具由 LLM 运行时选；中途可改策略（如塑料款过多再调 CategoryInsight），不是写死顺序。 |

### 1.4 口述禁忌（你以前踩过的坑）

- 不要说「并行返回结构化参数」——说「返回压缩后的字符串结果，Prompt 要求 JSON」。  
- 不要只提 30 轮不提 300s 和四件套。  
- 不要说「我写了框架内部的线程池」——说「利用框架对同轮多 tool_calls 的并发执行」。  
- 数字说得出测量方法；72%/22% 等其他条另论，本条聚焦 30/300/65%。

---

## 2. 架构学习（把图装进脑子）

### 2.1 要解决的三个瓶颈（原文 03-0）

1. **上下文污染**：子任务大量中间页（政策、评论）灌进主 messages，主线变钝。  
2. **串行等待**：四平台顺序搜，耗时≈求和。  
3. **调用链过深**：搜→规格→评论→物流… 主历史膨胀。

对策：主 loop **按需** fork 同质子 loop，子任务独立跑，主线只收最终结果。

### 2.2 运行时结构

```text
用户 query
  → run_agent(thread_id=主会话)
  → 主 AgentLoop（FULL_TOOL_SET + Checkpointer）
        │
        ├─ 自己调：Planner / CategoryInsight / PriceCompare / …
        │
        └─ dispatch_tool(demands) × N（同轮可并发）
              → enter_fork() 深度+1
              → build_agent().invoke(thread_id=sub-xxx, recursion_limit=12)
              → 子 Agent 独立 Think/Act/Observe
              → return str(最后一条消息)
        │
        → 合流 → 比价/运费/精挑 → ShoppingSummary → 结束
```

### 2.3 状态怎么隔离

| 概念 | 含义 |
|---|---|
| State | 主要是 messages（对话与工具 Observation） |
| Checkpointer | 按 `thread_id` 存取 State；主/子不同 key → 互不污染 |
| 同质 | 同一个 `build_agent()` 单例 + 同一份工具定义；**不是**新建另一套 Agent 类 |
| ContextVar | 请求级/调用链级透明传参（fork 深度；API 层还有 thread_id） |

关键直觉：**隔离靠 thread_id，不靠「再建一个异构 Agent 类」。**

### 2.4 和固定 Workflow 的本质区别（原文 03-1）

| | 固定 Plan-and-Execute | 本项目 AgentLoop |
|---|---|---|
| 下一步 | Python/计划写死 | LLM 根据 Observation 再决定 |
| 中途翻车 | 仍按原 plan 跑完 | 可改工具、改 query、再 fork |
| 可证伪检验 | — | 塑料款过多是否会调 CategoryInsight 改策略 |

面试金句：我们要的是**运行时编排**，不是套了 LLM 壳的流水线。

### 2.5 收敛与边界

- `ShoppingSummary`：终结工具，之后不应再开检索。  
- `PriceCompare` / `ShippingCalc`：确定性计算，主 Agent 直接调。  
- `dispatch_tool`：元工具，不做购物业务，不计入「九工具」。

---

## 3. 代码文件学习（详细，按依赖顺序）

对照路径（二选一即可，职责一致）：

- 讲解版：`生产级架构全景/app/agent/`  
- 可运行复刻：`globex-agent/app/agent/`（以你本机为准）

建议阅读顺序：`llm` → `prompts` → `tool_registry` → `fork_guard` → `middleware` → `dispatch_tool` → `main_agent`。

---

### 3.1 `llm.py` —— 统一模型入口

**做什么**  
`get_llm()` 返回进程内单例 `ChatOpenAI`（OpenAI 兼容协议，如 DeepSeek）。配置来自环境变量。

**为什么重要**  
主/子共用同一客户端对象；无状态 HTTP，并发 invoke 安全。换模型只改 `.env`，不改业务。

**学习检查**  
- 为什么用 `lru_cache` 而不是 import 时全局 new？→ 延迟初始化，避免 env 未加载就炸。  
- 主子共用实例会不会串请求？→ 不会，每次 invoke 独立。

---

### 3.2 `prompts.py` —— Prompt 加载

**做什么**  
从 YAML 读 system prompt；支持 `long_term_preferences` 占位（给记忆模块预留）。

**和本条的关系**  
Prompt 里必须写清：何时 `dispatch_tool`、子任务尽量一层 fork、超时/拒绝后换思路、Summary 后收敛。多 Agent 行为一半在代码护栏，一半在 Prompt。

**学习检查**  
打开 `prompts.yml`，找到 fork 相关规则；能口述「模型为什么知道要并行 fork」。

---

### 3.3 `tool_registry.py` —— 工具清单

**做什么**  
`FULL_TOOL_SET` = 九业务工具 + `dispatch_tool`。

**关键点**  
主/子注册**同一份** list → 同质的代码证据。数工具时要说「10 个可调用对象，其中 1 个是 fork 元工具」。

**学习检查**  
指出哪一行把 `dispatch_tool` 注册进去；解释为何子 Agent 也能看到它（所以需要深度护栏）。

---

### 3.4 `fork_guard.py` —— fork 深度护栏

**做什么**  
`ContextVar` 记当前深度；`enter_fork()` 超限抛 `ForkLimitExceeded`；`finally` 里 `reset`。

**为什么用 ContextVar**  
嵌套 + 并发调用链上不能靠全局 int；也不能给每一层都手动传 depth（易漏）。

**并发陷阱（必学）**  
标准 `ThreadPoolExecutor` 新线程拿不到父线程 ContextVar → 深度全是 0 → 护栏失效。  
LangChain `ContextThreadPoolExecutor` 在 map/submit 前 `copy_context()` → 子线程看到正确深度。  
验证：跑 `demos/demo_parallel_fork.py` Part 2。

**学习检查**  
手画：主 fork 一层 → 子再 dispatch → 第二层 → 第三层被拒，返回什么给主 loop。

---

### 3.5 `middleware.py` —— 工具层防失控

**做什么**  
1. `truncate_long_tool_result`：结果超长截断并提示缩窄查询。  
2. `ToolCallLimitMiddleware`：同工具单次 run 次数上限，`exit_behavior="continue"`（拦工具不杀整次 run）。

**和 30 轮的关系**  
30 轮管「整图递归」；middleware 管「细粒度刷工具 / 单次炸弹结果」。

**学习检查**  
说明与原文「滑动窗口 LoopDetector」的差异（若实现是整次 run 硬计数）：有意简化，更严更简单。

---

### 3.6 `dispatch_tool.py` —— fork 本体（本条核心文件）

**做什么**  
`@tool` 包装：`demands: str` → fork 子 Agent → `str` 结果。

**必懂实现细节**

| 点 | 原因 |
|---|---|
| 函数内延迟 import `build_agent` | 打破与 `tool_registry` 的循环依赖 |
| `sub-{uuid}-d{depth}` | 独立 checkpoint key |
| `recursion_limit` 更小（如 12） | 子任务应更快收敛 |
| `ForkLimitExceeded` → 字符串拒绝 | 异常转 Observation，主 loop 可换策略 |
| 返回 `str(...)` | Tool 契约；合流稳定性依赖 Prompt |

**并行从哪来**  
本文件**一次调用只跑一个子 Agent**。并行来自：主模型**同轮多个** `dispatch_tool` tool_calls + 框架并发调度。

**学习检查**  
- 读 docstring：三个适用场景是否与 03-0 三件事一致。  
- 用 `scripts/try_dispatch_fork.py`（若有）看真实 LLM 是否 fork；**不 fork 直接串行 item_search 也可能合理**——v1 不确定性要心里有数。

---

### 3.7 `main_agent.py` —— 组装入口

**做什么**  
`build_agent()`：`create_agent(model, tools, system_prompt, checkpointer, middleware)`，`lru_cache` 单例。  
`run_agent(query, thread_id)`：带 `recursion_limit=30` 调用。

**必懂**  
- Agent 必须单例 + 共享 Checkpointer，否则每次新建等于失忆。  
- 主/子隔离 = 不同 `thread_id`，不是两个 Agent 对象。  
- **300s 超时**：定稿落在第3档——`asyncio.wait_for(ainvoke)` 真取消；与「同轮多 tool 并发降延迟」是两件事。线程池「放弃等待但后台仍跑」≠真取消（见 `demos/demo_timeout_guard.py`）。

**学习检查**  
从 `run_agent` 画到 `dispatch_tool` 再画回 `build_agent` 的调用环，标出单例与 thread_id。

---

### 3.8 建议动手验证清单

```bash
# 在 globex-agent 环境中
uv run python ../简历内容学习与面试准备/生产级架构全景/demos/demo_parallel_fork.py
uv run python ../简历内容学习与面试准备/生产级架构全景/demos/demo_timeout_guard.py
uv run pytest tests/test_fork_guard.py tests/test_dispatch_tool.py tests/test_middleware.py -q
# 有密钥时
uv run python scripts/try_dispatch_fork.py
```

你应能解释每个命令在验证什么假设。

---

## 4. 为什么这是「接近生产级 / 次生产级」

不是「已经上了 eBay 全量生产」，而是：**具备生产级 Agent 编排应有的关键属性**。

| 生产级关注点 | 本条如何体现 | 仍缺什么（诚实） |
|---|---|---|
| 故障隔离 | 子任务独立 thread/checkpoint，中间噪声不进主线 | 多 worker 下 InMemorySaver 要换 Redis/PG |
| 延迟可控 | 同轮多 fork 并发；可测串并行差 | 需线上直方图与告警 |
| 成本/上下文可控 | 只回最终结果；结果截断；后续接 Cache Breakpoint | 压缩是另一简历条 |
| 安全收敛 | 轮次+超时+深度+循环限制 | 异步超时与 cancel 要接 API 层 |
| 可观测 | AGUI fork/tool 事件（全链路） | 任务级四轴在 `ops/` 补丁 |
| 可回滚放量 | 概念上可关并行 fork flag | 原文弱，见 `app/ops/` |

**面试一句**  
「生产级不是堆微服务，而是：动态编排有上限、并发有收益可证、失败可降级可观测。我们这条主+同质 fork 就是按这个标准落地的。」

---

## 5. 模拟实习：我在这条上真实会经历什么

> 以下按「悉尼站 AI Agent 开发实习」叙事组织，任务粒度贴近真实协作。  
> **纪律**：机制与数字测量方法要能讲清；公司内部真实数据用「我们组压测口径」表述；不要声称无法核实的人名业绩。

### 5.1 你在组里的角色

- **Title**：AI Agent Development Intern  
- **直接对口**：Agent 平台 / 购物 Agent 业务一组（导师 = Staff/高级工程师）  
- **本条 ownership**：主/子 Agent 编排与防失控、跨平台并行路径、相关单测与压测对比、Prompt 中 fork 规则迭代  
- **不对口**：四平台采买合同、三塔训练（协作消费）、前端像素（只约定 AGUI 事件）

### 5.2 入职第一周：读链路 + 画图（导师任务）

**导师原话（模拟）**  
「先别写代码。把主 Agent 从用户点发送到 ShoppingSummary 的路径画出来，标清哪里会 fork、哪里绝对不能 fork，周五给我讲。」

**你怎么完成**  
1. 读 03-0 / 14 / 项目地图 §2–4。  
2. 画一张序列图：主 Think → 4×dispatch → 子 ItemSearch → 合流 → 比价 → Summary。  
3. 列出反例：PriceCompare 若被模型 fork 了会怎样（浪费、隔离无意义）。  
4. 周五口述 + 指出「同质」三个相同、一个不同（thread_id）。

**验收**  
导师追问「子 Agent 有没有更少的工具？」答错会被打回重读 03-0。

**你学到的素养**  
先对齐架构边界，再写代码；能画图才能改图。

---

### 5.3 任务 A：补齐 / 加固 `dispatch_tool` + 独立 thread（2 周）

**背景问题（你会撞上）**  
- v0 主 Agent 自己 for 循环调四次 `item_search`：慢，且中间 Candidate 全进主上下文。  
- 有人提「做四个平台专家 Agent」：导师否决——同质任务不值得异构。  

**任务**  
实现/完善 `dispatch_tool`：独立 `thread_id`、子 `recursion_limit`、异常变 Observation；注册进 `FULL_TOOL_SET`；Prompt 增加并行 fork 指引。

**怎么做**  
1. 写失败测试：子 thread_id ≠ 主；深度超限返回拒绝字符串而非进程崩溃。  
2. 最小实现 + 延迟 import 解决循环依赖（第一次 ImportError 要会查栈）。  
3. 本地用静态 ItemSearch mock，不烧钱打四平台。  

**怎么测**  
- 单测：`fork_guard`、dispatch 拒绝路径。  
- 手工：`try_dispatch_fork.py` 看是否出现多个 dispatch；记录「LLM 未 fork」的 case，区分 bug vs 策略选择。  

**复盘会说的话**  
「并行不是 dispatch 函数内部 asyncio.gather 四平台，而是模型同轮多 tool_calls；我们要优化 Prompt 与可观测性，而不是在工具里写死四路。」

---

### 5.4 任务 B：防失控四件套落地（导师：上线门槛）

**导师原话（模拟）**  
「动态 Agent 没有护栏不能灰度。深度、超时、循环、截断按 14 章补齐，给出默认参数和理由。」

**你会遇到的问题**  
1. **子 Agent 递归 fork**：同质工具集含 dispatch → 曾孙爆炸 → CPU/账单飙。→ `MAX_FORK_DEPTH=2`。  
2. **模型死循环搜同一词**：轮次耗尽仍无清单。→ 同工具 run_limit + Prompt「换策略」。  
3. **一次返回几千候选**：上下文爆、Cache 前缀被毁（为后条压缩埋坑）。→ 截断 + 提示缩 top_k。  
4. **只有 recursion_limit、任务挂死**：某 LLM 请求挂起。→ 设计 300s；发现同步 invoke 难真取消 → 记技术债：等 FastAPI 异步层用 `wait_for(ainvoke)`；用 demo 向导师证明线程池超时会泄漏后台工作。  

**怎么测**  
- 单测构造超深 fork、超长 ToolMessage、超限工具名。  
- 混沌：mock 子 Agent sleep > 超时，断言主侧收到超时 Observation/错误事件，且（异步方案下）协程被取消。  

**学习**  
生产素养 = **先假设模型会作恶/会笨**，用确定性工程约束概率行为。

---

### 5.5 任务 C：并行收益量化（对应简历 65%）

**导师原话（模拟）**  
「口头说快没有用。给我一张表：串行 vs 并行，P50，样本量和 query。」

**怎么做**  
1. 固定 query：「旅行三件套，预算 300，amazon+shopee+aliexpress+ebay」。  
2. 两组：  
   - A：强制串行（或 Prompt 禁多 dispatch / 实验开关关并行）。  
   - B：允许同轮多 dispatch。  
3. 每组跑 N 次（如 10），记端到端墙钟时间；同时记是否真出现 ≥2 个并行 dispatch（否则数据无效）。  
4. 汇报：均值/方差、延迟降低百分比、失败率（超时、未 Summary）。  

**本地认知实验**  
`demo_parallel_fork.py`：用 sleep 模拟平台延迟，得到 ~66.7%，用来**理解公式**；对导师汇报时要说明：线上应用真实 LLM+工具耗时复测，65% 是业务压测口径。

**坑**  
- LLM 经常不并行 → 优化 Prompt、加 few-shot、或临时在编排层对「多平台」显式扇出（产品要拍板是否削弱 Agent 动态性）。  
- 并行后 token 成本上升（多份子 Agent 系统前缀）→ 与「延迟收益」写进权衡，不是免费午餐。

---

### 5.6 任务 D：合流稳定性（字符串 Observation 翻车）

**线上/联调问题（模拟）**  
主 Agent 有时把子 Agent 散文总结当 JSON 解析失败，比价吃不到 Candidate。

**任务**  
1. Prompt：子任务输出 schema（platform、candidates、truncated）。  
2. 主侧：解析失败则降级为「带原文再调一次 ItemPicker/重试」或请求子任务重跑。  
3. 评测：P1 增加「跨平台结果可解析率」。  

**素养**  
Agent 系统的契约常常是 **Prompt 契约 + 尽力解析**，不如 Pydantic 硬；要在评测里盯，而不是假设模型永远听话。

---

### 5.7 任务 E：灰度前 checklist（与 ops 衔接）

**领导/PM（模拟）**  
「并行 fork 先 5% 用户。超时率或 P0 升高就关。」

**你要交付**  
- flag：`ENABLE_FORK_PARALLEL`（讲解见 `app/ops/flags.py`）。  
- 指标：任务耗时、fork 次数、超时率、未收敛率。  
- 回滚：关并行 → 退回主 Agent 串行工具调用（慢但稳）。  

**你的站会更新模板**  
「本周：并行路径回归 12 条全绿；压测 N=10，P50 从 Xs→Ys（-Z%）；已知 LLM 不扇出比例 A%，下周改 Prompt vB。」

---

### 5.8 一周学习节奏（可照做）

| 日 | 做什么 |
|---|---|
| 一 | 重读本文件 §1–2，闭卷画架构图 |
| 二 | 精读 `dispatch_tool` + `fork_guard`，跑两个 demo |
| 三 | 精读 `main_agent` + `middleware`，写 5 条「若去掉 X 会怎样」 |
| 四 | 口述 3 分钟版给同学/录音；对照 §1.4 禁忌改 |
| 五 | 模拟导师拷问：65%、ContextVar、同质、300s、为何不 fork 比价 |
| 六 | 读 03-1 Agent vs workflow，准备一个现场例子 |
| 日 | 把新坑记进 `00_学习进度与复盘笔记.md` |

---

### 5.9 「实习收获」自我鉴定（打勾才算真懂）

- [ ] 能闭卷画出主/子/dispatch/Checkpointer 关系  
- [ ] 能解释并行发生在「同轮多 tool_calls」而非 dispatch 内部写死四平台  
- [ ] 能说明 ContextVar + ContextThreadPoolExecutor 为什么绑在一起  
- [ ] 能区分 30 轮 vs 300s vs 深度 vs 循环限制  
- [ ] 能描述一次串并行压测怎么设计  
- [ ] 能举一个「LLM 动态改策略」的例子证明是 Agent  
- [ ] 能诚实说出：异步超时、多实例 Checkpointer、字符串合流仍是风险点  

---

## 6. 推荐阅读路径（原文）

1. `globex/03_0_extract.md` — 为何 fork、同质定义、三件事  
2. `globex/03_1_extract.md` — AgentLoop vs PAE  
3. `globex/11item_search_fork_reproduction.md` — ItemSearch 与四路 fork  
4. `globex/14_extract.md` — 组装与防失控定稿（agent 七文件）  
5. 全景 `app/agent/*.py` 讲解头注释  
6. `文档/00_项目地图.md` §2–4 — 放回整链  

---

## 7. 一页纸作弊条（临上面试）

```text
问题：单 Agent 污染 + 串行慢 + 链路深
方案：主 AgentLoop + 同质 fork（dispatch_tool）
同质：同模型/同 Prompt/同工具；异：thread_id + checkpoint
并行：同轮多 dispatch → 框架线程池 → 耗时≈max → ~65%
护栏：30轮 + 300s + 深度2 + 循环限制 + 截断
不 fork：PriceCompare / ShippingCalc
终结：ShoppingSummary
我做：编排、护栏、Prompt、压测对比、合流稳定性
不加分装腔：我写了调度器内核 / 返回的是结构化 RPC
```

---

*本文随学习更新；与复盘笔记冲突时，以你最新跑通的代码与压测为准，并回写数字口径。*
