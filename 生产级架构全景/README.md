# Globex 生产级架构全景（理解性学习用，不要求能跑通）

## 这是什么

这不是一个可运行的工程项目，是一份"贴着完整文件树"的学习材料。骨架参照
`globex/`（原始文档第 01-15 章）描述的**完整目标架构**——1 个主 AgentLoop
+ N 个同质子 AgentLoop + 9 个业务工具 + 5 类基础设施——而不是只参照
`globex-agent/` 目前实际写到的进度（那个项目目前还没做到 Cache Breakpoint、
长期记忆、三塔召回）。

每个文件内部主要是**结构化说明文字**：做什么、解决什么问题、输入输出契约、
和其他文件怎么连接、用了什么技术栈，偶尔配几行关键代码帮助理解。目的是让你
不用来回切文档和代码，对着一个文件就能把这块讲清楚。

## 简历四条 —— 对应文件位置

| 简历条目 | 对应目录 | 学习状态 | 真实代码是否存在 |
|---|---|---|---|
| ① 多 Agent 架构（主+Fork子Agent） | `app/agent/` | ✅ 已精讲，含实测数据 | ✅ `globex-agent/app/agent/` 已实现 |
| ② Cache Breakpoint 上下文压缩 | `app/compress/` | ✅ 学习稿+日程+demo | 讲解版已升级（非复刻仓） |
| ③ 长期记忆 Store | `app/memory/` | ✅ 学习稿+日程+demo | 讲解版已升级 |
| ④ 三塔向量召回 | `app/recall/towers.py` `app/recall/ann.py` | ✅ 学习稿+日程+demo | 讲解版已升级 |

标 ✅ 的四条均已有学习稿；背景板目录仍只做一两句话说明。

## 深度图例

- **★★★ 完整讲解**：`app/agent/` 全部 7 个文件。每个文件包含：做什么 /
  解决的问题 / 输入输出契约 / 和其他文件的连接（State 怎么传递） / 技术栈 /
  关键代码片段 / 面试可能追问的点。
- **背景板（一两句话）**：`app/api/` `app/tools/` `app/recall/`（除三塔部分）
  `app/eval/` `app/prompt/` `app/utils/` 以及 `pipelines/` `scripts/`
  `data/` `frontend/` `tests/` `docker/`。这些文件存在的目的是让你看到
  "一个完整生产级项目大概长什么样"，不是简历重点，不深挖。
- **简历②③④讲解版**：`app/compress/` `app/memory/` `app/recall/towers.py`
  `app/recall/ann.py`——已升级为与简历重点同级的完整讲解格式。
- **次生产级补丁**：`app/ops/`——原文档未覆盖的灰度运营壳（讲解为主，
  不是可运行配置中心）。详见 `文档/原文档与次生产级差别.md`。

## 目录全景

```text
生产级架构全景/
├── README.md                      本文件
├── 文档/                          理解入口与架构讨论
│   ├── 00_项目地图.md              ★ 先读：链条 / 工具 / 评测 / 数据来源
│   ├── 02_同步_并发_异步定稿.md    ★ 全景=第3档；学习仍以并行为先
│   ├── 简历第一条_多Agent架构/     ★ 简历①全套（学习稿 + 实习日程）
│   ├── 简历第二条_CacheBreakpoint/ ★ 简历②（01 学习 + 03 日程 + demo）
│   ├── 简历第三条_长期记忆Store/  ★ 简历③（01+03+demo）
│   ├── 简历第四条_三塔向量召回/   ★ 简历④（01+03+demo）
│   ├── 次生产级灰度模拟可行性评估.md
│   └── 原文档与次生产级差别.md
├── demos/                         可实际运行的验证脚本（理解用，非正式工程）
│   ├── demo_parallel_fork.py       验证"为什么并行能降延迟 65%"
│   ├── demo_timeout_guard.py       验证"线程池超时 vs asyncio.wait_for 真取消"
│   ├── demo_cache_breakpoint.py    盲目压缩 vs Cache-Aware（指纹模拟 cache）
│   ├── demo_memory_store.py        跨会话写入 → read_relevant 注入
│   └── demo_tri_tower_recall.py    同义/双通道/跨语言/后过滤红线
└── app/
    ├── ops/        ★ 次生产级补丁（原文档无）：灰度开关/指标/回滚/放量故事线
    │   ├── flags.py
    │   ├── metrics.py
    │   ├── rollback.py
    │   └── rollout.md
    ├── agent/      ★★★ 简历① 主/子 AgentLoop、fork、防失控
    │   ├── llm.py
    │   ├── prompts.py
    │   ├── tool_registry.py
    │   ├── dispatch_tool.py
    │   ├── fork_guard.py
    │   ├── middleware.py
    │   └── main_agent.py
    ├── api/        背景板 FastAPI + WebSocket + AGUI 事件
    │   ├── context.py
    │   ├── events.py
    │   ├── monitor.py
    │   ├── connection.py
    │   └── server.py
    ├── tools/      背景板 9 个业务工具（真实代码已在 globex-agent 实现）
    │   ├── planner.py
    │   ├── chat_fallback.py
    │   ├── web_search.py
    │   ├── category_insight.py
    │   ├── item_search.py
    │   ├── item_picker.py
    │   ├── price_compare.py
    │   ├── shipping_calc.py
    │   └── shopping_summary.py
    ├── recall/
    │   ├── towers.py     ★★★ 简历④ Query/User 在线编码 + 融合
    │   ├── ann.py         ★★★ 简历④ Faiss ANN + 后过滤红线
    │   ├── category_kb.py 背景板
    │   ├── reranker.py    背景板
    │   ├── fx.py          背景板
    │   ├── duty.py        背景板
    │   └── shipping.py    背景板
    ├── memory/      ★★★ 简历③
    │   ├── schemas.py
    │   ├── store.py            抽象接口 PreferenceStore
    │   ├── in_memory_store.py  本地内存实现
    │   └── vector_store.py     向量/OpenSearch 实现
    ├── compress/    ★★★ 简历②
    │   ├── breakpoint.py
    │   └── compressor.py
    ├── eval/        背景板
    │   ├── schemas.py
    │   ├── rubric.py
    │   ├── judge.py
    │   └── trace_logger.py
    ├── prompt/      背景板
    │   └── prompts.yml
    └── utils/       背景板
        ├── path_utils.py
        └── thread_ctx.py
```

`pipelines/`、`scripts/`、`data/`、`frontend/`、`tests/`、`docker/` 原文档
只到目录级别、没有具体到文件名，所以只在各自目录下放一份 README 说明用途，
不虚构文件名。

## 内容来源纪律（2026-08-09 补充）

审计发现过一次问题：`app/memory/injector.py` 曾经被写成一个独立文件，但
原文档（`globex/06_extract.md`）里并没有这个文件，"读偏好注入 prompt"
在原文里是 `main_agent.py` 内部的一个调用动作，不是单独文件——这个错误的
根源是参考了 `globex-replica-docs/Globex项目复刻方案.md`（我们自己复刻
项目定的目录基线）而不是原文档本身。已改正（见 `app/memory/` 现在的
4 个文件）。

**之后的规则**：本目录任何文件结构、文件名、职责描述，都必须能追溯到
`globex/` 下某一章节的具体内容，不以 `globex-replica-docs/` 或
`globex-agent/` 已有的设计决定作为架构依据——那两者只用来核对"复刻代码
目前实现到什么程度"这类事实性问题，不作为"原方案应该是什么样"的依据。

各目录的原文依据（已核对）：

| 目录 | 原文依据 |
|---|---|
| `app/agent/` | `globex/14_extract.md` 第 31-44 行工程文件结构 |
| `app/tools/` | `globex/14_extract.md` 第 45-54 行 + 第 09-15 章各工具专章 |
| `app/api/` | `globex/07_extract.md`（events/context/connection/monitor/server）+ `globex/15_extract.md`（server/connection/monitor/context 定稿） |
| `app/recall/`（towers/ann） | `globex/11item_search_fork_reproduction.md` |
| `app/recall/`（category_kb/reranker） | `globex/13_category_insight_rag_复刻提取.md` + `globex/13-1_rag_hybrid_rerank_eval_复刻提取.md` |
| `app/recall/`（fx/duty/shipping） | `globex/12_price_compare_shipping_calc_复刻提取.md` |
| `app/memory/` | `globex/06_extract.md`（schemas/store/in_memory_store/vector_store） |
| `app/compress/` | `globex/14_extract.md` 第 55-57 行（定稿简化版；第5章早期为 `app/context/`，全景跟第14章定稿） |
| `app/ops/` | **非原文档**；次生产级灰度补丁，见 `文档/原文档与次生产级差别.md` |

## 怎么用这份材料

0. **先读** `文档/00_项目地图.md`——整条 Agent 链、工具联动、评测、数据来源。
1. 读 `文档/02_同步_并发_异步定稿.md`——目标第3档；并行 vs 异步；学习优先级。
2. 简历①：`文档/简历第一条_多Agent架构/`；简历②设计：`文档/简历第二条_CacheBreakpoint/`。
3. 再读差别文档与灰度评估，分清「原文内核」和「ops 补丁」。
4. 看本 README 建立文件树与简历四条落点；代码讲解在 `app/`。
5. 需要眼见为实（如并行提速），去 `demos/` 跑脚本。
6. 学习对错记录在仓库根目录 `00_学习进度与复盘笔记.md`。
