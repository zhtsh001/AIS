# AIS 恢复报告

恢复日期：2026-09-27。项目已恢复到 `/Users/tristan/Desktop/AIS`。

## 恢复范围

- 从本机 Codex 会话提取了 57 份代码、配置和文档，另补提取 plaintext renderer 原文。
- plan 目录包含整合版规划文档及原 6 份规划文档。
- sources.yaml 包含 24 个信源，其中 23 个 active。
- 核心 fetch、generate、pipeline、数据模型、SQLite store、邮件 publisher、orchestrator 已恢复。
- manifest.json 记录历史来源、提取时间、文件哈希，以及补丁匹配失败等线索。`complete_evidence` 仅表示读取到文件尾或存在 Add File 正文，不代表已证实为丢失前最新版本。

## 重建与修复

以下内容为本次新写，不能视作原文件的逐字恢复：

- publishers/renderers/base.py：渲染器接口。
- publishers/renderers/html.py：兼容原邮件接口的 HTML 渲染器。
- publishers/telegram.py：简化的 Telegram transport，未联网验收。
- subscribers/tokens.py：随机订阅 token。
- utils/config.py 中的 load_sources：缺失的信源加载函数。
- requirements.txt、requirements-recovered.lock.txt、.env.example 和 tests/test_recovery.py。

已修复历史代码中 datetime.timedelta 调用错误、GitHub 入库调用不存在的 save_item、归档 Subscriber 使用旧 lang 参数的问题。

## 验证

- 所有恢复/重建的 Python 文件通过 AST 语法检查。
- fetch、generate、publishers.orchestrator 导入成功。
- pipeline.py --help 正常。
- 6 项新建离线测试通过：信源库 ID 唯一性、时间判断、token、UTF-8 消息保留、双语 HTML 转义、邮件 dry-run 禁止发送、本地归档兼容性（部分合并在同一测试中）。
- 已安装核心依赖并记录当前版本；这些不是原始依赖版本。

## 尚未恢复或验证

- 原 tests 测试集、Git 历史、订阅数据库、已发送记录、raw/generated 历史内容没有恢复。
- .env 旧密钥未恢复；只有空白示例配置。
- 旧企微回调相关源码为历史恢复资料，Flask/wechatpy 等旧渠道依赖未安装。
- 未执行真实抓取、模型调用或消息发送，未安装或启动任何定时任务。
- 历史文档与历史实现不完全一致，尤其 taxonomy、订阅偏好及 daily/weekly 调度。恢复不表示所有规划已实现。
- 恢复出的 weekly 信源频率逻辑仍沿用历史简化实现，上线前需要单独审查。

## 使用

在 ais_engine 目录运行：

```sh
venv/bin/python -m unittest discover -s tests -v
venv/bin/python pipeline.py --help
```

恢复快照 recovery/AIS_recovered_2026-09-27.zip 包含代码与 plan，不含 venv、日志、运行数据和凭据。同盘备份只用于方便搬运，不能代替异地备份。
