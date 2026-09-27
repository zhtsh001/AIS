# Alpha Intelligence System (AIS) 商业与技术总体蓝图 (v5)
*Date: 2026-05-21*

---

## 1. 系统定位

AIS 的目标是帮助用户持续获得少量但极高价值的前沿信号。它不是新闻摘要，不是信息流，也不是热点雷达。

核心承诺：

> 用长期维护的 Alpha 信源库和高门槛筛选机制，交付高智力密度、非共识、有远见的情报。

系统默认服务对象是个人高强度信息消费者，尤其是希望长期跟踪 AI、开源、硬科技、Web3、Cyber、Biotech 等前沿领域的人。

---

## 2. 内容标准

### 2.1 必须具备

- 非显然性：不是公开新闻标题的复述。
- 结构性：能指向技术、产业、资本、生态或社会结构变化。
- 前瞻性：能推演未来几个月或几年内可能发生的变化。
- 高密度：每句话都应携带信息，不做情绪填充。
- 可复盘：几周后回看仍能解释为什么当时值得关注。

### 2.2 明确排除

- 行活式行业评论。
- 套路化“趋势解读”。
- 追热点的短期兴奋。
- 活动、会议、招聘、纯融资。
- 营销稿和 PR 稿。
- 币圈喊单和投机性内容。
- 没有二阶洞察的“新产品上线”。

质量规则：

> 宁可空，也不凑数。

---

## 3. 信源资产库

AIS 的长期护城河来自 `sources.yaml`。每个信源都应被当作资产管理，而不是 URL 列表。

每个信源至少包含：

```yaml
id: "rss_example"
name: "Example Source"
type: "rss"
url: "https://example.com/feed"
domain: "AI"
topics: ["open_source_ai", "agents"]
tags: ["builders", "deep-dive"]
priority: 5
quality_floor: 8.0
audience: ["personal", "future_paid"]
language: "en"
frequency_hint: "daily"
active: true
description: "为什么这个信源值得长期维护。"
```

分层结构：

- `domain`: 一级领域。
- `topics`: 二级兴趣主题。
- `tags`: 细粒度解释和过滤。
- `priority`: 信源优先级。
- `quality_floor`: 该信源进入生成的最低评分要求。

这套结构未来直接服务用户兴趣订阅。

---

## 4. 产品形态

### 4.1 当前阶段

当前产品是个人情报系统：

- 主交互入口：Email。
- 输出语言：中英双语。
- 频率：每日 + 每周。
- 订阅管理：先手动维护个人 subscriber。
- 发送前保留 dry-run 审稿。

### 4.2 未来阶段

未来可以扩展为订阅产品：

- 用户选择感兴趣的 `domains/topics`。
- 免费与付费 tier 分层。
- paid 用户获得更完整来源、深度推演和更高频推送。
- 大陆中文用户可通过独立 Publisher 接入。
- WhatsApp、Telegram、微信生态可作为交互或轻推送入口。

---

## 5. 技术架构

核心管线：

```text
sources.yaml
  -> fetch / ingestors
  -> raw_storage + url_index
  -> generate / score + 5-module AlphaSignal
  -> i18n translation cache
  -> publishers.orchestrator
  -> Email Publisher / future channel Publishers
```

核心原则：

- Fetch 不关心渠道。
- Generate 不关心订阅者。
- Publisher 不关心信源抓取。
- Subscriber 偏好只在发布编排层生效。

这样未来增加 WhatsApp、微信生态或 RSS，不会影响信源库和生成层。

---

## 6. 当前优先路线

1. 修复现有 pipeline 稳定性。
2. 标准化 `sources.yaml` 的 `domain/topics/tags/priority/quality_floor`。
3. 扩展 AI 开源社区源：
   - Hugging Face Daily Papers。
   - r/LocalLLaMA。
   - GitHub AI Trending / new-star repos。
4. 跑通 Email daily + weekly。
5. 增加 subscriber 兴趣过滤。

---

## 7. 非目标

当前阶段不做：

- 企业微信正式上线。
- 公开订阅网站。
- 支付系统。
- 大规模多渠道分发。
- 登录态爬虫。
- X/Twitter 或 Farcaster 这类高维护成本源。

这些都可以在基础系统稳定后作为后续模块接入。

---

## 8. 成功标准

AIS 成功不是因为每天发很多，而是因为：

- 用户愿意认真读每一条。
- 输出能持续提前暴露未来变化。
- 信源库能越维护越值钱。
- 渠道变化不会伤到核心系统。

---

*Blueprint updated for Email-first personal intelligence architecture.*
