"""
文件：app/tools/shopping_summary.py ｜ 背景板（非简历重点，真实代码已在 globex-agent 实现）

生成最终购物清单和选购理由，是 Agent 的收敛出口——调用它之后主 Agent 应该
停止继续调用其他工具，这是"Agent 需要明确终止条件"的具体体现。
"""
