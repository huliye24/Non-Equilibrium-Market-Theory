# ASDE — 独立参考原型

理论：[动态情景穷举与自适应决策](../../theory/ADAPTIVE_SCENARIO_DECISION.md)。本目录只定义**有限情景、概率输入验证、候选仓位穷举、成本与最坏情景损失约束**，无网络、无交易所连接、无实盘权限。80k/76k/85k BTC 是示意价，1/3 权重完全人为设定，不是训练结果。

运行演示：`python experiments/reference/asde.py`

测试命令：`python -m unittest discover -s experiments/reference -p 'test_*.py'`

这是教学参考模型，不是历史回测或策略验证；未建立时序状态训练、滚动验证、账户保证金、跨资产相关性或概率校准。后续开发应在 Emergenzix 仓库内完成，并保留实验预注册和证据等级。
