"""
文件：app/tools/shipping_calc.py ｜ 背景板（非简历重点，真实代码已在 globex-agent 实现）

估算关税、运费和到手价，同样是确定性计算，不 fork。和 price_compare 一起
构成"候选合流后"的两个纯计算工具，职责边界很清楚：谁都不反向调用 item_search
补数据，需要的字段必须由上游透传。
"""
