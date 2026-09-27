# Alpha Intelligence System (AIS) MVP Roadmap v3
*Date: 2026-05-21*

---

## MVP 目标

当前 MVP 不再追求多渠道覆盖，也不再以企微或 Telegram 作为核心闭环。

新目标：

> 跑通一个稳定、高质量、Email-first 的个人情报系统。

验收重点：

- 信源分层清晰。
- 抓取稳定。
- 生成高密度。
- Email daily + weekly 可用。
- dry-run 审稿流程可靠。
- 架构为未来兴趣订阅和聊天渠道留口子。

---

## Phase 1: Pipeline 稳定性修复

- [ ] 修复 `fetch.py:is_source_due` 的北京时间判断 bug。
- [ ] 修复 `GithubTrendingFeed` 调用不存在的 `save_item` 问题。
- [ ] 确认 `pipeline.py fetch/generate/publish-daily/publish-weekly` 四个入口都可独立运行。
- [ ] 检查 launchd plist 全部调用 `pipeline.py`，并保持四任务解耦。
- [ ] 保证 dry-run 不触发真实网络发送。
- [ ] 保证 `pytest` 全绿。

验收命令：

```bash
./venv/bin/python -m pytest -q
./venv/bin/python pipeline.py publish-daily --dry-run
```

---

## Phase 2: 信源 Taxonomy 标准化

- [ ] 为所有 active source 补齐 `domain`。
- [ ] 为所有 active source 补齐 `topics`。
- [ ] 为所有 active source 补齐 `tags`。
- [ ] 为所有 active source 补齐 `priority`。
- [ ] 为所有 active source 增加 `quality_floor`。
- [ ] 为所有 active source 增加 `audience`。
- [ ] 增加 sources schema 检查测试。

目标结构：

```yaml
domain: "AI"
topics: ["open_source_ai", "agents"]
tags: ["github", "builders", "tools"]
priority: 5
quality_floor: 8.0
audience: ["personal", "future_paid"]
```

验收标准：

- `sources.yaml` 能支持未来用户按领域和主题订阅。
- Fetch 写入 raw item 时保留 source metadata。

---

## Phase 3: AI 开源社区源扩展

第一批只做低维护成本源：

- [ ] Hugging Face Daily Papers。
- [ ] r/LocalLLaMA。
- [ ] GitHub AI Trending / new-star repos。

接入原则：

- 优先 RSS、公开 API、稳定 HTML。
- 不做登录态。
- 不引入重型爬虫。
- 每个新源都必须有清晰维护理由。

验收标准：

- 新源能进入 `data/raw/YYYY-MM-DD/`。
- 新源能更新 `data/index/url_index.json`。
- 新源输出字段与现有源一致。

---

## Phase 4: Email Daily + Weekly 真实运行

- [ ] 配置 `RESEND_API_KEY`。
- [ ] 配置 `AIS_EMAIL_FROM`。
- [ ] 手动添加个人 Email subscriber。
- [ ] 添加 daily subscriber 记录。
- [ ] 添加 weekly subscriber 记录。
- [ ] 跑 daily dry-run 并人工审稿。
- [ ] 跑 weekly dry-run 并人工审稿。
- [ ] 真实发送一封 daily 到个人邮箱。
- [ ] 真实发送一封 weekly 到个人邮箱。

验收标准：

- Email HTML 可读。
- 中英双语展示正常。
- unsubscribe footer 存在。
- deliveries 幂等表正常写入。
- daily 和 weekly 不互相误发。

---

## Phase 5: 用户兴趣订阅准备

- [ ] `Subscriber` 预留 `domains/topics/min_priority`。
- [ ] Orchestrator 按 subscriber 兴趣过滤 signals。
- [ ] Email 仍为主交互入口。
- [ ] WhatsApp、Telegram、微信生态仅保留 Publisher 扩展点。
- [ ] 公开订阅页作为后续项目，不进入当前 MVP。

未来 subscriber 偏好：

```python
domains: list[str] = []
topics: list[str] = []
min_priority: int = 3
```

规则：

- 空 `domains/topics` 表示接收全部。
- 非空时按兴趣过滤。
- 当前先手动维护，不做公开用户界面。

---

## 质量红线

以下内容不允许进入最终输出：

- 活动公告。
- 招聘。
- 营销稿。
- 套路化趋势文。
- 纯融资新闻。
- 投机喊单。
- 没有远见推演的常规产品更新。

宁可少发，不可凑数。

---

## 当前不做

- 企业微信上线。
- 公开订阅网站。
- 支付系统。
- X/Twitter 高维护爬虫。
- Farcaster 登录态抓取。
- 多渠道同时扩张。

---

*Roadmap updated for Email-first personal intelligence MVP.*
