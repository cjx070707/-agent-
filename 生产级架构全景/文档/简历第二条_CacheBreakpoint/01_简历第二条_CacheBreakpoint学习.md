# 简历第二条学习文档：Cache Breakpoint 上下文压缩

> 对应简历：边界压缩（早期稳定 + 近轮可压）；10+ 轮压在约 30k token；Prompt Cache 命中约 80%。  
> 原文：`globex/05_extract.md`（定稿）。接入主 loop 叙事见 14 章；**压缩只动断点后**（你已确认）。  
> 配套：`03_…实习日程模拟.md`、`app/compress/*`、`demos/demo_cache_breakpoint.py`。  
> 粗讲确认：乱压改前缀→命中掉；断点在最近 K 轮工具前；线前 cache、线后压；一步结束后再算再压。

---

## 1. 详细面试介绍

### 1.1 30 秒版

购物 Agent 多轮工具调用后上下文会爆。乱摘要会改掉本应稳定的历史前缀，Prompt Cache 命中崩掉，综合成本反而更高。我们用 Cache Breakpoint 画盖章线：线前一字不动保缓存，线后才截断/摘要；挂在 Agent 每步结束后做。目标是长对话仍可控（约 10+ 轮压在 30k 量级），命中率稳住在约 80%（相对盲目压缩的约 15%）。

### 1.2 2～3 分钟版

**痛点**：`item_search`、多路 fork 结果、多轮比价会把 messages 堆到上万～数万 token。  
**冲突**：Prompt Cache 要求前缀完全一致；压缩若动到前缀 → miss。原文对比：不压命中高但贵；盲目压命中约 15%；Cache-Aware 命中约 80% 且综合成本最低。  
**做法**：用最近 K 次工具调用定位断点——最近轮最不稳定放线后；线前封存。只压缩线后。每步结束后重算断点再压。  
**配套**：工具侧先控体积（L0 截断）；评估不只看 token，还看任务成功和约束遗漏（别摘要掉「不要塑料」）。  
**和 fork / Store**：fork 少往主线倒脏数据；Breakpoint 收拾主线历史；Store 是跨会话偏好，不是会话内压缩。

### 1.3 高频追问

| 问 | 答 |
|---|---|
| 乱压缩为何更亏？ | 前缀被改 → cache miss → 每轮重算大前缀，省的 tip 不够赔的 |
| 断点怎么画？ | 最近 K 个工具消息中最早那个下标；线前稳、线后压 |
| 为何最近轮放线后？ | 最爱变，拿去当缓存前缀会频繁失效 |
| 何时触发？ | Agent 一步结束后观察历史，再 compute + compress |
| 和工具截断区别？ | 截断=单次结果；Breakpoint=多轮历史治理 |
| 和 Store？ | 会话内 token vs 跨会话偏好 |
| 80%/30k？ | 80% 来自原文 Cache-Aware 表；30k 是长对话目标水位，靠线后压+L0 |

### 1.4 口述禁忌

- 不要说「我们压缩整段历史省钱」——要说「只压断点后」。  
- 不要把 14 章「压断点前」示例当标准。  
- 不要只报压缩率不报命中率/约束遗漏。  
- 「断电」是口误，说 **断点 / Breakpoint**。

---

## 2. 机制（你已对齐的版本，写干净）

```text
一步 Agent 结束
  → 看 messages
  → compute_breakpoint(keep_recent=K)
  → 线前：不动（保 Prompt Cache 前缀）
  → 线后：截断/摘要（省 token，保留约束）
  → 进入下一轮
```

你的复述微调：

1. 乱压缩把**线前本该不变的部分改成会变的** → 命中率**变小**（不是「cache 小时」别的意思）。  
2. 断点画在「最近 K 轮工具调用」那段的**起点前**（线前 cache，线后压）——对。  
3. 触发：一步结束后**观察历史并执行压缩**（不止观察）。——对，补全「算断点 + 只压后面」。

---

## 3. 代码文件学习

### 3.1 `app/compress/breakpoint.py`

`compute_breakpoint(messages, keep_recent=3) -> idx`  
`messages[:idx]` 稳定；`messages[idx:]` 可压。

### 3.2 `app/compress/compressor.py`

`compress_after_breakpoint`：前缀原样 + 后缀 shrink。  
红线：禁止修改前缀。

### 3.3 挂到主 loop（叙事）

每步后 hook：`post_step_compress` 一类——先 bp 再 compress。  
目标形态仍在全景第3档异步链上，但本条学习不要求先改整仓 async。

### 3.4 Demo（必跑）

```bash
python3 生产级架构全景/demos/demo_cache_breakpoint.py
```

应看到：盲目压缩 → 稳定前缀指纹 **变了**；Cache-Aware → 指纹 **不变**，总字符下降。

---

## 4. 为什么算次生产级

| 点 | 体现 |
|---|---|
| 成本/延迟 | 保 cache + 控 token，不是傻压 |
| 正确性 | 约束遗漏、任务成功率进评估 |
| 与编排一体 | 挂在 AgentLoop 步进后，不是旁路脚本 |
| 可灰度 | 概念上可关 `ENABLE_CACHE_BREAKPOINT`（ops） |

诚实边界：厂商 cache API 细节（显式 cache_control vs 自动前缀）知差异即可；自学用指纹不变模拟「命中」。

---

## 5. 数字口径

| 说法 | 依据 |
|---|---|
| 命中 ~80% | 05 表 Cache-Aware；对比盲目 ~15%、原文亦有 15%→80%+ |
| 综合成本约 -35% | 05 口径原文 |
| ~30k / 10+ 轮 | 目标水位；机制=线后压+L0，不是魔法常数 |

---

## 6. 推荐阅读

1. `globex/05_extract.md` §2–5、§11  
2. 本夹 `03` 实习日程  
3. `demos/demo_cache_breakpoint.py`  
4. 项目地图里与①、③的边界  

---

## 7. 一页纸作弊条

```text
问题：多轮上下文膨胀；乱压打穿 Prompt Cache
方案：Cache Breakpoint 盖章线
线前：不动（cache）；线后：压（省 token）
划法：最近 K 个工具调用起点
时机：Agent 一步结束后
评估：命中率 + 约束遗漏 + 任务成功，不单看压缩率
和 fork：隔离脏数据 vs 治理主线历史
和 Store：会话内 vs 跨会话
数字：~80% 命中；~30k 水位
```
