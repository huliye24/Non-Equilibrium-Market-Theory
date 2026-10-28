# Non-Equilibrium Market Theory (NEMT)

本仓库是 NEMT 的理论与策略规范源，不是交易软件仓库。

NEMT 研究市场从相对稳定状态进入临界、趋势扩张与衰减状态时的信息结构，
并尝试把这些状态写成可证伪、可复现实验的数学假设。

## 仓库边界

| 本仓库负责 | Emergenzix 负责 |
| --- | --- |
| NEMT 概念、符号和数学假设 | 软件、API、前端与数据库 |
| 策略规则与版本规范 | 可执行策略适配器与回测引擎 |
| 风险原则与评价方法 | EC2、S3、Batch、CloudWatch部署 |
| 实验结论与失败记录 | PAPER工作流和Telegram机器人 |

可执行实现位于 [Emergenzix](https://github.com/huliye24/emergenzix)。本仓库
不保存交易所密钥、机器人令牌、云端配置、原始行情、容器镜像或真实订单
能力。理论结果不能自动授权实盘交易。

## 内容

- [NEMT 核心理论](theory/CORE_THEORY.md)
- [动态情景穷举与自适应决策（ASDE）](theory/ADAPTIVE_SCENARIO_DECISION.md) — 未验证研究提案与离线参考算法
- [研究与策略治理](theory/RESEARCH_GOVERNANCE.md)
- [NEMT v4.4 策略规范](strategies/NEMT_V4_4.md)
- [NEMT v5 周级趋势价值](strategies/NEMT_V5_WEEKLY_TREND.md)
- [v4.4 证据摘要](evidence/NEMT_V4_4_2024_2026.md)
- [v5 2025失败实验](evidence/NEMT_V5_2025.md)

## 研究文库与历史材料（2026-10-26 迁入）

原 NEMT-Simulator2 中的研究资料现已按**文献快照**分类整理，不携带旧软件源码或旧仓库提交历史：

- [完整理论书稿（29个章节文件）](theory/book/chapters/00-title.md)：《非平衡市场与宏观趋势调度理论》的研究稿；
- [理论原则](theory/principles/)：风险优先、策略生命周期假设；
- [核心数学实验预注册](experiments/preregistration/core-math-20261017/README.md)：无量纲化、相位变化、经济参数识别；
- [后续实验预注册](experiments/preregistration/follow-up-20261017/README.md)：数值稳定性、稳健观测量、BTC 样本外检验；
- [实验报告（历史原稿）](experiments/reports/README.md)：**此次迁移未重新运行或独立复核原始数据**；
- [候选策略研究](strategies/candidates/S-001-market-regimes.md)：与现有 v4.4、v5 正式版本文档分开；
- [历史档案](archive/legacy/README.md)：仅存档，不代表当前已获验证；
- [研究规范](governance/RESEARCH_PROTOCOL.md)：假设、预注册、失败证据与样本外判断；
- [研究资料目录](RESEARCH_INDEX.md)与[迁移溯源](MIGRATION.md)。

**证据分级提醒：**现有 v4.4 的“已验证研究基线”仅代表其文档规定的历史测试范围，不代表已通过实盘准入，也不等于数学理论被证实。历史实验报告和 v5-alpha 失败记录均保留原始范围与局限。

## 当前版本状态

| 版本 | 状态 | 结论 |
| --- | --- | --- |
| v4.4 | 已验证研究基线 | 仍是 Emergenzix 默认 NEMT 研究策略 |
| v5-alpha | 未通过 | 数学方向保留，当前模型不得晋级或发送开单信号 |

历史模拟不代表未来收益。本项目不构成投资建议。
