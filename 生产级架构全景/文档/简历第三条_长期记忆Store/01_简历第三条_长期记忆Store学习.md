# 简历第三条学习文档：长期记忆 Store

> 对应简历：Redis/Postgres（持久化后端）+ 偏好抽取 + 软衰减；跨会话复用；命中约 72%。  
> 原文：`globex/06_extract.md`。**72% 原文无表——本全景定为可辩护自拟口径（见 §5）。**  
> 配套：`03` 日程、`app/memory/*`、`demos/demo_memory_store.py`。

---

## 0. 已定决策（过面试标准）

| 项 | 决定 |
|---|---|
| 体例 | 与①②相同：01 + 03 + 代码讲解 + 无 API demo |
| 与②边界 | Breakpoint=会话内 token；Store=跨会话结构化偏好 |
| 72% | **自拟**：「当 query 需要某类偏好时，该偏好被 `read_relevant` 注入成功」的比例；面试主动说明非原文表、可复述测法 |
| 后端说法 | 接口 `PreferenceStore`；开发内存；次生产级 Redis/Postgres（可再演进 OpenSearch） |
| 抽取 | Reflect 阶段从对话抽出条目（规则/关键词起步，可升级 NLU/LLM） |
| 学习深度 | 读写时机、read_relevant、黑名单优先、软衰减、和①②分工——够用；不上分布式锁细节深水 |

---

## 1. 面试介绍

### 1.1 30 秒

跨会话不能靠把聊天记录越存越长。我们把「不要塑料」一类偏好抽成结构化条目进 Preference Store，会话结束可以压缩历史；新会话开始用 `read_relevant` 只取与当前 query 最相关的几条注入 system prompt。带软衰减和黑名单加权。持久化叙事用 Redis/Postgres。相关偏好注入命中我们压测口径大约 72%。

### 1.2 2～3 分钟

**问题**：Breakpoint 会丢掉旧消息；用户却希望下次还记得材质黑名单。  
**存什么**：`PreferenceEntry`（preference / history / blacklist），不是 raw log。  
**写**：Reflect 阶段 `maybe_write`（关键词/规则抽取）。  
**读**：`run_agent` 开头 `read_relevant(top_k≈5)`，避免 50 条全注入。  
**排序**：相关度 × 置信度 × 时间衰减 + 黑名单加权。  
**后端**：抽象接口，换存储不换 Agent 时机。  
**评估**：注入是否发生、下游是否遵守（约束遗漏）；72% 是注入成功率类口径。

### 1.3 追问速答

| 问 | 答 |
|---|---|
| 和 Breakpoint？ | 会话内压缩 vs 跨会话持久偏好；互补 |
| 为何不 read 全量？ | token 膨胀、噪声；相关 Top-K |
| 软衰减？ | 降旧偏好权重，不轻易删；黑名单衰减慢 |
| 72%？ | 自拟注入命中率；说明样本与定义，不谎称原文 |
| Redis 还是 PG？ | 都可；关键是接口与读写时机，简历写组合表示生产持久化 |

### 1.4 禁忌

- 不要说「我们把全部聊天存 Redis 当记忆」。  
- 不要把 72% 说成原文官方表。  
- 不要和 Prompt Cache 搅成一个模块。

---

## 2. 机制图

```text
会话1: 用户说不要塑料
  → Reflect 抽取 → Store.write(blacklist)
  → 历史可被 Breakpoint 压缩/丢弃

会话2: query=洗漱包
  → read_relevant → 注入 system prompt
  → ItemPicker / 主 Agent 守约束
```

---

## 3. 代码文件

| 文件 | 作用 |
|---|---|
| `schemas.py` | PreferenceEntry |
| `store.py` | 抽象接口 |
| `in_memory_store.py` | 本地跑通 |
| `vector_store.py` | 向量/混合相关读 + 黑名单策略叙事 |
| `prompts.py`（agent） | `long_term_preferences` 注入口 |

Demo：`python3 生产级架构全景/demos/demo_memory_store.py`

---

## 4. 次生产级

- 持久化、相关读取、衰减、黑名单优先——原文要求的生产补齐项。  
- 灰度：可关 `ENABLE_MEMORY_INJECT`（ops）；误伤过度过滤时停注入、保留写入。  
- 多实例：Store 必须进程外共享（呼应①里 InMemorySaver 的同类问题）。

---

## 5. 72% 口径（背这个）

**定义**：在「当前 query 与某条硬偏好（如材质黑名单）语义相关」的评测子集上，`read_relevant` 结果中**包含该偏好**的比例。  

**怎么测**：固定 N 条跨会话 case（先写偏好，再换 session 用相关 query 读）；统计命中。叙事约 72%。  

**面试补一句**：这是组内离线评测口径，不是公开论文数字；机制比数字更重要。

---

## 6. 作弊条

```text
跨会话偏好 → 结构化 Store，不存整段聊天
写 Reflect；读 run 开头 read_relevant(top_k)
分：相关度×置信度×衰减 + 黑名单加权
后端：接口稳定；Redis/PG 持久化
和②互补；72% = 注入命中自拟口径
```
