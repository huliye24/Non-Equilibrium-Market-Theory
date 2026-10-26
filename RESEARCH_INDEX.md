# NEMT Research Library — 研究资料目录

NEMT 的定位是**可证伪的金融市场理论与版本化交易策略规范**；代码实现由 [Emergenzix](https://github.com/huliye24/emergenzix) 承担。当前仓库分为两类材料。

## A. 当前研究基线（导入前即存在）
| 资料 | 用途 | 状态 |
| --- | --- | --- |
| [核心理论](theory/CORE_THEORY.md) | ψ、S、临界状态与可证伪框架 | 活跃研究 |
| [策略 v4.4](strategies/NEMT_V4_4.md) | 版本化交易策略规范 | 历史验证研究基线；不代表实盘验证 |
| [v4.4 证据](evidence/NEMT_V4_4_2024_2026.md) | 2024–2026 的已报告验证 | 受原文约束，需核对运行证据 |
| [v4.4 样本外证据 2022-06~10](evidence/NEMT_V4_4_2022_06_10.md) | 原始标定区间之外的探索性回测 | EXPLORATORY；路由退化，不晋级 |
| [v4.4 2022 样本外实验报告](experiments/reports/20261026-nemt-v44-2022-oos.md) | 78 次月度回测的完整记录、复现步骤与指纹 | EXPLORATORY |
| [策略 v5-alpha](strategies/NEMT_V5_WEEKLY_TREND.md) | 周级趋势策略假说 | 未通过 |
| [v5.2.2 慢速系统消融](experiments/reports/20261026-v522-slow-system-ablation.md) | 55 日独立臂 A/B 消融（2025） | EXPLORATORY；改善但仍为负 |
| [v5.2.6 NEMT 增量信息](experiments/reports/20261026-v526-incremental-information.md) | 全突破事件账本，含被拒反事实（2025） | EXPLORATORY；Delta_R>0 但两组均为负 |
| [2023 冻结窗口 E1–E5](experiments/reports/20261026-2023-frozen-battery.md) | 2023 全年五组实验，跨年度对照 | PREREGISTERED；收益与增量符号均翻转 |
| [2021 冻结窗口 E1–E5](experiments/reports/20261026-2021-frozen-battery.md) | 2021 全年五组实验，三年度对照 | PREREGISTERED；门槛在该年未发生作用 |
| [2024 冻结窗口 E1–E5](experiments/reports/20261026-2024-frozen-battery.md) | 2024 全年五组实验，四年度汇总 | PREREGISTERED（部分污染）；门槛从未显示正增量 |
| [2026 年初至今 E1–E5](experiments/reports/20261026-2026-ytd-frozen-battery.md) | 2026-01 至 2026-10-25 五组实验，五窗口汇总 | PREREGISTERED（未完成年度）；中位 R 五年恒定 |
| [勘误 01](experiments/reports/ERRATUM-01-2026-ytd-ci.md) | 2026 YTD 报告的 CI 措辞错误与计数更正 | 勘误；不改变任何数值与判定 |
| [v5 失败实验](evidence/NEMT_V5_2025.md) | 2025 年全年研究观察 | FAIL，必须保留 |
| [研究治理](theory/RESEARCH_GOVERNANCE.md) | 版本、成本、风控与权限 | 规范 |

## B. 从旧 NEMT-Simulator2 整理来的研究遗产
| 资料 | 用途 | 解释边界 |
| --- | --- | --- |
| [理论书稿](theory/book/chapters/00-title.md) | 长篇理论论述及宏观—微观框架 | 历史作者原稿，非新验证 |
| [风险与生命周期原则](theory/principles/) | 研究原则、可检验生命周期假说 | 研究构想 |
| [数学建模备忘](theory/notes/) | 术语与指标备忘 | 参数需重新冻结 |
| [三项核心数学实验](experiments/preregistration/core-math-20261017/README.md) | 数学一致性、相变与经济映射 | 原预注册方案 |
| [后续数值/样本外实验](experiments/preregistration/follow-up-20261017/README.md) | 数值稳定、观测量、BTC OOS | 原预注册方案 |
| [历史实验报告](experiments/reports/README.md) | 研究结论原文 | 迁移时未验证 |
| [市场状态策略候选 S-001](strategies/candidates/S-001-market-regimes.md) | 可证伪的状态切换问题 | CONJECTURE |
| [研究档案](archive/legacy/README.md) | 过往分析与原有策略池 | 历史记录，不视为批准规则 |

## 方法
先冻结假设 → 执行实验 → 保存正负证据 → 检查因果性、样本外、成本与误差 → 人工评审 → 再决定是否作为 Emergenzix 的策略研究输入。

**理论标签不是市场真值，回测指标不是未来收益保证，文献中的仓位示例不是实际交易建议。**

迁移溯源见 [MIGRATION.md](MIGRATION.md)。
