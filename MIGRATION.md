# NEMT 研究资料迁移记录

## 目的
将 NEMT-Simulator2 的理论、方法和策略规范提取到本仓库，不将历史网站、API、Electron、部署脚本、下单程序或交易所密钥一起迁移。

## 来源与可追溯性
- 来源仓库：[NEMT-Simulator2](https://github.com/huliye24/NEMT-Simulator2)
- 来源整理分支：[research-only-export-20261026](https://github.com/huliye24/NEMT-Simulator2/tree/research-only-export-20261026)
- 整理快照提交：`ce537c2c3d4589dfc81984277f4893e815bc39a7`
- 旧仓库原始基线：`8582b66f3bff4b2aa6d2433399c6d3c4452761c9`
- 新仓库导入前基线：`fc604adb7c9dcb012ec88e8ea26e49f73ccb0340`
- 迁移日期：2026-10-26

## 迁移说明
- 原整理快照中共有 66 个文件，其中 63 个新增研究或许可证文档被逐项按文件内容复制到本仓库；
- 已有的 `README.md` 与 `LICENSE` **不覆盖**，现有 v4.4/v5 策略及证据文件保持不变；
- `MIGRATION.md` 根据实际目标仓库重写，并新增 `RESEARCH_INDEX.md`；
- 旧仓库 Git 历史、远端分支、提交父指针 **没有被合并或复制进来**；
- 各原始文献在迁移时不修改正文，新增的策略候选与研究治理文档来自去代码整理版。

## 重要分类
- `theory/book/chapters/`：NEMT 理论整合版书稿（含系统工程的概念性章节，非软件）
- `experiments/preregistration/`：实验计划、先决条件、门控标准
- `experiments/reports/`：已有报告文本；并不代表本次迁移已重跑或独立复核
- `strategies/candidates/`：研究假设，不能与版本化已验证策略等同
- `archive/legacy/`：过时或仅供历史参考的材料
- `governance/`：研究与来源追踪制度

## 后续工作
1. 审阅书稿内部断链、术语冲突、图像和旧软件工程描述；
2. 将预注册与已完成实验的结果、代码/数据指纹、验证状态逐项核对；
3. 避免将探索性研究或历史策略池中示例仓位写成有效交易建议；
4. 在 Emergenzix 以稳定研究版本 ID 与 Git 提交引用理论，而非从此仓库拉取可执行代码；
5. 安全审计历史旧仓库中可能出现的凭据；任何旧凭据风险不得通过复制仓库历史扩散。

## 版权
本仓库根目录保留 GPL-3.0 许可证，迁移文件中有关历史 Apache-2.0 及第三方贡献的说明存于 `LICENSES/` 和 `governance/LEGACY_LICENSE_POLICY.md`。复制文件或变更目录不自动改变第三方版权。
