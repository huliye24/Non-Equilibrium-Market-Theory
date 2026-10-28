# ASDE — 独立参考原型

理论：[动态情景穷举与自适应决策](../../theory/ADAPTIVE_SCENARIO_DECISION.md)。本目录只定义**有限情景、概率输入验证、候选仓位穷举、成本与最坏情景损失约束**，无网络、无交易所连接、无实盘权限。80k/76k/85k BTC 是示意价，1/3 权重完全人为设定，不是训练结果。

运行演示：`python experiments/reference/asde.py`

测试命令：`python -m unittest discover -s experiments/reference -p 'test_*.py'`

`asde_walk_forward.py` 进一步提供严格点时的滚动样本外研究接口：

- 显式预注册起始时间、train / validation / test、市场、成本、结果指标和研究等级；特征只读取决策时点之前的数据；
- 趋势、波动、流动性离散状态，样本支持不足时强制 no-trade；
- 训练/滚动历史内估计情景权重，并在留出期报告多分类 Brier 分数；
- 每期只执行第一步并重新规划，保存候选动作、拒绝理由、权益、回撤与尾部损失；
- 同窗运行空仓、买入持有、固定趋势基准，以及无状态、无滚动、均匀概率、成本翻倍消融；失败结果不会被过滤；
- 通过 `AuditedLedger` 协议注入 Emergenzix 已审计账户/保证金/清算账本。本仓库不复制账本，也不自行授予 PAPER/LIVE 权限。

调用方必须为每个运行提供全新的账本适配器（`ledger_factory`）。测试中的 `ConservationLedger` 仅是验证接口调用的测试替身，不是生产账本。

完整测试：`python -m unittest discover -s experiments/reference -p 'test_*.py'`

## 右侧突破入场状态机

`right_side_entry_state.py` 实现只读取已完成 K 线的研究状态机：

`BREAKOUT_CANDIDATE → STABILIZING → RETEST_HELD → REACCELERATION`

它禁止突破后直接追入；只有回踩守住并再次放量加速后，下一根 K 线开盘才具备研究层入场资格。保护止损锚定回踩低点下方，不设固定止盈。实现不连接交易所、订单或生产信号。

预注册与后续三项实验见 [`../preregistration/right-side-entry-state-001.md`](../preregistration/right-side-entry-state-001.md)。

这是教学与研究参考模型，不是策略验证；概率可能失准，有限压力情景可能遗漏尾部事件，结构变化可能使历史频率失效。跨年度/跨币种复核使用 `run_frozen_battery`：除市场和起始时间外，参数变化会被拒绝，所有数据集结果（包括失败结果）都会保留。
