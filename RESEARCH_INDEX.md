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
| [2022 冻结窗口 E1–E5](experiments/reports/20261026-2022-frozen-battery.md) | 2022 全年五组实验，六窗口汇总（100 USDT → 102.57） | PREREGISTERED（部分污染）；下跌市仅 +2.57% |
| [勘误 01](experiments/reports/ERRATUM-01-2026-ytd-ci.md) | 2026 YTD 报告的 CI 措辞错误与计数更正 | 勘误；不改变任何数值与判定 |
| [S-003.W 2022 探索性](experiments/reports/20261026-s003w-2022-exploratory.md) | 小资金周级确认单变量消融（100 USDT → 105.35） | EXPLORATORY；周级确认是唯一改善项 |
| [S-003.W 2022 复现记录](experiments/reports/REPRO-20261026-s003w-2022.md) | 全新目录两次独立运行的逐字节复现 | 复现通过；不改变证据等级 |
| [S-003.1 2023 账本](experiments/reports/20261026-s0031-2023-ledger.md) | 滚动权益 + 分批记账（100 → 140.89 / 124.98） | EXPLORATORY；复利 +2.81，分批 -15.92 |
| [S-003.1 2025 账本 + arm C](experiments/reports/20261026-s0031-2025-ledger.md) | 滚动权益/分批/平衡止损（100 → 93.67 / 96.92） | EXPLORATORY；全部亏损年 |
| [S-003.1 2023+2024 五格](experiments/reports/20261026-s0031-2023-2024-five-cell.md) | 含 arm C 的三年矩阵；每年最优配置都不同 | EXPLORATORY；无稳定最优配置 |
| [ETHUSDT 2024 跨资产五格](experiments/reports/20261026-ethusdt-2024-five-cell.md) | 参数冻结自 BTC，首次换资产（100 → 117.13） | PREREGISTERED；首个删最大赢家仍为正的窗口 |
| [2022 @10k BTC+ETH](experiments/reports/20261026-2022-10k-btc-eth.md) | 下跌年 + 1 万本金；ETH 每格优于 BTC | EXPLORATORY；规模比例校验通过 |
| [PR#72 周级 UP-UP 闸门评估](experiments/reports/20261026-pr72-weekly-upup.md) | 8 组合 × 6 格；闸门 2/8 胜；ETH 四年全正 | EXPLORATORY；闸门不采纳 |
| [风险预算 1%–10% 敏感性](experiments/reports/20261026-risk-sweep-1-to-10.md) | 单笔 5% 可达年 +182%；连亏 15 笔是硬约束 | EXPLORATORY；高风险档不可实盘 |
| [10 币横截面 2022–2025](experiments/reports/20261026-cross-section-10-symbols.md) | 8 币首次；33,307 笔；24/40 资产-年份为正 | PREREGISTERED；压线通过 |
| [为什么收益低：逐笔诊断](experiments/reports/20261026-why-low-return-diagnosis.md) | 699 笔；止损后 76% 继续走；放宽止损无效 | EXPLORATORY；结构性约束 |
| [概率论上限分析](experiments/reports/20261026-mathematics-of-low-return.md) | 凯利最优 3.5%，理论上限 +14.6%/年；10% 风险理论为负 | EXPLORATORY；边际 t≈2.3 |
| [低频/加仓/对冲三臂 + 长空不对称](experiments/reports/20261026-lowfreq-pyramid-hedge.md) | 只做多把凯利上限从 14.7% 提到 46.5% | EXPLORATORY；空单零边际 |
| [按收益排序的最优可行配置](experiments/reports/20261026-return-maximizing-config.md) | 只做多 2% 风险 3 仓并行：年化 +90.1% | EXPLORATORY；单一路径 |
| [S-004 臂 A 结果](experiments/reports/20261026-s004-arm-a-result.md) | 稀疏过滤杀掉 0/7 最大赢家，H0 未拒绝 | EXPLORATORY；A 臂否定 |
| [S-004.A.2 事件级 A/B](experiments/reports/20261026-s004-a2-ab-study.md) | 2,356 候选；top1% 赢家 0/24；总收益为原策略 1/244 | EXPLORATORY；过滤器否决 |
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
