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
- [研究与策略治理](theory/RESEARCH_GOVERNANCE.md)
- [NEMT v4.4 策略规范](strategies/NEMT_V4_4.md)
- [NEMT v5 周级趋势价值](strategies/NEMT_V5_WEEKLY_TREND.md)
- [v4.4 证据摘要](evidence/NEMT_V4_4_2024_2026.md)
- [v5 2025失败实验](evidence/NEMT_V5_2025.md)

## 当前版本状态

| 版本 | 状态 | 结论 |
| --- | --- | --- |
| v4.4 | 已验证研究基线 | 仍是 Emergenzix 默认 NEMT 研究策略 |
| v5-alpha | 未通过 | 数学方向保留，当前模型不得晋级或发送开单信号 |

历史模拟不代表未来收益。本项目不构成投资建议。
