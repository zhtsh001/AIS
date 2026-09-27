# Alpha Intelligence System (AIS)

高信息密度的个人情报系统。维护分层 Alpha 信源库，通过独立的抓取、生成和发布流程筛选内容，当前架构以 Email 为主渠道，保留其他 Publisher 扩展接口。

## 当前状态

本仓库是 2026-09-27 从开发历史恢复的版本，部分缺失模块已重新实现。核心模块可导入，6 项离线恢复测试通过；尚未完成真实抓取、Gemini 生成、邮件发送的端到端联调。定时任务未启动。

当前信源配置包含 24 个信源，其中 23 个启用。规划文档描述了目标架构，不代表所有功能已实现。

## 目录

- `plan/`：需求、架构和阶段规划，以 `AIS_Integrated_Master_Plan.md` 为主。
- `ais_engine/sources.yaml`：信源资产库。
- `ais_engine/config.yaml`：非敏感业务参数。
- `ais_engine/pipeline.py`：统一命令入口。
- `ais_engine/ingestors/`、`generators/`：采集、存储及模型调用。
- `ais_engine/publishers/`、`subscribers/`、`i18n/`：发布、订阅状态及翻译。
- `ais_engine/tests/`：本次恢复新增的离线测试。
- `ais_engine/recovery/RECOVERY_REPORT.md`：恢复范围、重建模块及限制。

## 本地准备

推荐使用 Python 3.14（恢复验证环境）。

```sh
cd ais_engine
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements-recovered.lock.txt
python -m unittest discover -s tests -v
python pipeline.py --help
```

`requirements.txt` 是依赖范围；`requirements-recovered.lock.txt` 记录恢复验证时安装的版本，并非丢失前的原始版本。

## 配置与运行

按 `.env.example` 在本地配置 `.env`。生成需要 `GEMINI_API_KEY`；邮件发送需要 `RESEND_API_KEY`、`AIS_EMAIL_FROM`，或 SMTP 配置。密钥、订阅数据库、运行数据不进入 Git。

四个阶段分别执行，命令之间不自动串联：

```sh
python pipeline.py fetch
python pipeline.py generate
python pipeline.py publish-daily --dry-run
python pipeline.py publish-weekly --dry-run
```

前两条命令会访问真实信源或调用模型，可能产生 API 费用。发布前需要配置订阅者并完成手动审稿。恢复验证只覆盖离线测试，未证明完整 pipeline 已可上线。

`--dry-run` 用于本地预览；真实发送须单独配置和验证。`scripts/launchd/` 是历史调度模板，包含原机器绝对路径，部署前需要审查路径、频率和幂等逻辑。

## 历史组件

企微测试脚本、回调服务器、旧发布入口和 `scripts/update_*.sh` 作为历史代码保留。它们不是当前 Email 上线流程，不能当作通用部署脚本直接运行；旧渠道依赖也未纳入核心依赖。

## 后续重点

1. 验证真实抓取、生成及邮件 dry-run 流程。
2. 完善 source taxonomy 与元数据传递。
3. 审查跨日去重、数据保留和 daily/weekly 调度语义。
4. 完成邮件试发后再配置定时任务。

参见 [统一规划](plan/AIS_Integrated_Master_Plan.md) 和 [恢复报告](ais_engine/recovery/RECOVERY_REPORT.md)。
