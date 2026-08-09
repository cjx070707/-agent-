"""
文件：app/agent/prompts.py
所属模块：★★★ 简历① 多 Agent 架构 —— Prompt 加载与拼装
参考原文：globex/10_基础模块与模型配置_核心提取.md
对照真实代码：globex-agent/app/agent/prompts.py（已实现，本文件是讲解版）

【做什么】
从 YAML 配置文件读 system prompt 模板，并把"长期偏好"这段文字插进模板里，
返回给 `main_agent.py` 组装 Agent 用。

【解决的问题】
Prompt 是这类 Agent 项目里改动最频繁的东西（调策略基本等于改 Prompt），
如果把大段 Prompt 文本硬编码在 Python 代码里，每次调整都要动代码、重新走
代码审查。拆成 YAML 文件，Prompt 本身可以单独迭代、单独 diff，不污染业务
代码。

【输入 / 输出】
- 输入：`long_term_preferences: str`，一段"该用户的长期偏好摘要文字"，
  默认空字符串。
- 输出：拼装好的完整 system prompt 字符串。

【和其他文件的连接 / State 怎么传递 —— 这是一个值得注意的连接点】
- 被 `main_agent.py` 的 `build_agent()` 调用：
  `create_agent(system_prompt=get_system_prompt(), ...)`。
- **`long_term_preferences` 这个参数是简历①和简历③（长期记忆）之间预留的
  连接缝**：真实生产版本里，主 Agent 启动前应该先从 `app/memory/store.py`
  读出这个用户的偏好摘要，传进 `get_system_prompt(long_term_preferences=...)`，
  这样"上次说过不要塑料"才能在新会话里自动生效。当前 `globex-agent` 代码里
  这个参数存在，但调用处永远传的是空字符串（因为长期记忆 Store 还没实现）——
  **这是一个"接口已经预留、实现还没跟上"的真实工程状态**，面试时可以精准
  指出这一点，显得你真正读过代码而不是背文档。
- 用 `lru_cache` 缓存 YAML 解析结果，避免每次调用都重新读文件、重新
  `yaml.safe_load`。

【技术栈】
- `pyyaml`：解析 `app/prompt/prompts.yml`。
- `pathlib.Path`：用 `__file__` 相对定位配置文件路径，不依赖当前工作目录，
  避免"在哪个目录下启动程序，相对路径就找不到文件"的常见坑。
- `str.format()`：模板变量替换（不是 Jinja2，因为模板简单，没必要引入更重的
  模板引擎）。

【关键代码片段（帮助理解，非完整实现）】
```python
@lru_cache(maxsize=1)
def _load_prompts() -> dict:
    with PROMPT_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def get_system_prompt(long_term_preferences: str = "") -> str:
    template = _load_prompts()["system_prompt"]
    return template.format(
        long_term_preferences=long_term_preferences or "（暂无沉淀偏好）"
    )
```

【面试可能被追问】
- "长期记忆和 Prompt 具体怎么接起来？" —— 见上面"连接点"那段，这正是简历
  ③要讲的"prompt injector"角色：Store 读出偏好 -> 格式化成一段摘要文字
  -> 作为参数传给 `get_system_prompt`，注入到 system prompt 最前面（这样
  还有一个好处：只要这段文字在多轮对话里保持不变，就不会破坏 Cache
  Breakpoint 的 Prompt Cache 前缀——这是简历①②③三个模块在设计上互相牵制
  的一个具体例子）。
"""
