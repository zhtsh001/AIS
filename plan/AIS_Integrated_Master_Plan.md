# Alpha Intelligence System (AIS) Integrated Master Plan
*Date: 2026-05-21*
*Status: Canonical planning document after V6 consolidation*

---

## 0. 文档定位

本文档整合以下原始规划文件，作为 AIS 后续开发和运营的唯一主计划：

- `AIS_Master_Architecture_V4_Final.md`
- `Alpha_Intelligence_System_Blueprint.md`
- `AIS_MVP_Roadmap.md`
- `AIS_Technical_Deployment_Plan.md`
- `OOP_Refactoring_Plan.md`
- `AIS_Subscription_Flow_Design.md`

这些拆分文档可以作为历史参考，但后续设计更新应优先写入本文档。

---

## 1. 核心定位

AIS 不是新闻聚合器，也不是热点追踪工具。AIS 的核心定位是：

**一个长期维护的高智力密度个人情报系统。**

它的核心资产不是某个推送渠道，而是：

1. 可长期积累、可分层订阅的 Alpha 信源库。
2. 面向非共识、远见和结构性变化的筛选能力。
3. 高密度、低噪音、可持续复用的生成与发布管线。

系统优先级固定为：

```text
信源质量 > 筛选质量 > 输出密度 > 渠道数量 > 自动化规模
```

宁可每天只输出 1 到 3 条真正有价值的信号，也不要为了形成日报而填充低质量内容。

---

## 2. 产品原则

### 2.1 质量优于数量

AIS 不追求覆盖所有新闻，也不追求“今天一定有很多条”。任何输出都必须满足：

- 高认知壁垒。
- 高信息密度。
- 有非显然洞察。
- 能指向未来几个月或几年内的结构性变化。
- 能经得起用户回看，而不是只在当下制造刺激。

明确排除：

- 活动公告。
- 招聘信息。
- 融资通稿。
- 营销稿。
- 常规产品发布。
- 行业套话。
- 追风口式评论。
- 币圈喊单或低质量投机内容。
- 没有二阶洞察的普通产品更新。

### 2.2 Alpha 不是新闻

抓取层可以广，但生成层必须窄。每条内容都必须回答：

> 这条信息为什么可能改变未来结构？

如果只能回答“发生了什么”，它不应进入最终输出。

### 2.3 信源库是长期资产

`sources.yaml` 是 AIS 的核心资产库，不只是抓取配置。每个信源都必须有清晰的领域、主题、标签、优先级和维护理由。

未来用户可以按领域或主题选择订阅范围，因此从现在开始就要保留这套分类结构。

### 2.4 渠道必须解耦

当前主渠道是 Email。Telegram、WhatsApp、微信生态、RSS、Feishu 等都只作为 `Publisher` 扩展口保留。

中国大陆中文用户当前不是优先受众，但未来仍可能接入。架构上必须保证新增大陆渠道时，不需要改 Fetch、Generate、AlphaSignal、Subscriber 的核心逻辑。

---

## 3. 阶段总览

### Phase A: 当前 MVP

目标：跑通稳定、高质量、Email-first 的个人情报系统。

重点：

- 修复 pipeline 稳定性。
- 标准化 `sources.yaml` taxonomy。
- 扩展 AI 开源社区源。
- 跑通 Email daily + weekly。
- 保留 dry-run 审稿流程。

### Phase B: 个人化订阅

目标：让用户按领域和 topic 订阅自己关心的高价值信源切片。

重点：

- `Subscriber` 增加 `domains/topics/min_priority`。
- Orchestrator 按兴趣过滤。
- Email 保持主交互入口。
- 订阅页仍可延后，先支持手动维护。

### Phase C: 订阅产品化

目标：从个人情报系统扩展为轻量订阅产品。

重点：

- 公开订阅页。
- 邮箱确认和退订。
- 免费/付费 tier。
- paid-only 字段。
- RSS 或静态归档。

### Phase D: 渠道扩展

目标：把聊天软件作为交互和轻推送入口，而不是核心状态源。

可能渠道：

- WhatsApp。
- Telegram。
- 微信生态。
- RSS。
- Feishu。

原则：

- 只新增 Publisher / Renderer / inbound handler。
- 不改 Fetch、Generate、AlphaSignal、Source taxonomy。

---

## 4. Source Taxonomy

### 4.1 一级领域 `domain`

建议标准域：

- `AI`
- `Web3`
- `Biotech`
- `HardTech`
- `Cyber`
- `Macro`
- `Science`
- `TechBiz`

### 4.2 二级主题 `topics`

一个信源可以属于多个 topic。示例：

- AI: `frontier_models`, `agents`, `alignment`, `open_source_ai`, `ai_infra`, `robotics`
- Web3: `ethereum`, `zk`, `mev`, `protocol_research`, `crypto_markets`
- Biotech: `synthetic_biology`, `drug_discovery`, `clinical_trials`, `ai_for_science`
- HardTech: `semiconductors`, `space`, `materials`, `energy`, `quantum`
- Cyber: `zero_day`, `exploit_research`, `supply_chain_security`

### 4.3 三级标签 `tags`

用于更细粒度筛选和解释，例如：

- `papers`
- `builders`
- `github`
- `deep-dive`
- `policy`
- `preprint`
- `infra`
- `security`
- `open-source`

### 4.4 Source 元数据模板

```yaml
id: "rss_huggingface_daily_papers"
name: "Hugging Face Daily Papers"
type: "rss"
url: "..."
domain: "AI"
topics: ["open_source_ai", "frontier_models"]
tags: ["papers", "builders", "open-source"]
priority: 5
quality_floor: 8.0
audience: ["personal", "future_paid"]
language: "en"
frequency_hint: "daily"
active: true
description: "AI 开源社区人工初筛后的高价值论文入口。"
```

### 4.5 第一批新增源

第一批只做低维护成本的 AI 开源社区源：

- Hugging Face Daily Papers。
- r/LocalLLaMA。
- GitHub AI Trending / new-star repos。

接入原则：

- 优先 RSS、公开 API、稳定 HTML。
- 不做登录态。
- 不引入重型爬虫。
- 每个新源都必须有清晰维护理由。

---

## 5. Pipeline Architecture

### 5.1 Fetch

统一入口：

```bash
python pipeline.py fetch
```

职责：

- 读取 `sources.yaml`。
- 按 `frequency_hint` 判断是否抓取。
- 调用对应 ingestor。
- 将原始内容写入 `data/raw/YYYY-MM-DD/`。
- 维护 `data/index/url_index.json`。

抓取结果必须携带：

```text
source_id, source, title, summary, url, published,
domain, topics, tags, priority, quality_floor, language
```

近期修复：

- 修复 `fetch.py:is_source_due` 的北京时间判断 bug。
- 修复 `GithubTrendingFeed` 调用不存在的 `save_item` 问题。
- 确认 `pipeline.py fetch` 可独立运行。

### 5.2 Raw Storage

Raw 数据保留策略：

- 默认保留 30 天。
- 默认容量上限 100MB。
- 跨天重复出现保留，用于观察信号复现频率。
- 同一天同 URL 可聚合计数。
- 全局 URL 索引写入 `data/index/url_index.json`。

### 5.3 Generate

统一入口：

```bash
python pipeline.py generate
```

职责：

- 读取最近 raw 候选。
- 本地过滤明显非 Alpha 内容。
- 按 `priority desc + quality_floor desc + last_fetched_at desc` 排序。
- 调用 Gemini 评分。
- 达到阈值后生成 5 模块 AlphaSignal。
- 输出 `.json` 作为 canonical artifact，`.md` 仅作为人工检查副本。

生成质量门：

- Source gate: 信源优先级和维护理由。
- Candidate gate: 本地规则过滤活动、营销、招聘、通稿。
- LLM gate: score 和 `quality_floor`。
- Publish gate: compliance 和重复发送保护。

### 5.4 Publish

统一入口：

```bash
python pipeline.py publish-daily --scheduled
python pipeline.py publish-weekly --scheduled
```

当前主 Publisher：

- Email HTML。

保留扩展口：

- Telegram。
- WhatsApp。
- WeChat / 企业微信 / 公众号。
- RSS。
- Feishu。

发布层职责：

- 按 cycle 选择 daily 或 weekly 信号。
- 按 Subscriber 的 `cadence/domains/topics/tier/confirmed/active` 过滤。
- 按语言需求触发翻译缓存。
- 渲染到对应渠道。
- 写入 deliveries 表，保证幂等。

---

## 6. Data Models

### 6.1 AlphaSignal

未来应稳定承载：

```python
id: str
source_url: str
source_lang: str
source: str
title: str
score: float
domain: str
topics: list[str]
tags: list[str]
priority: int
tier: str
bodies: dict[str, str]
paid_only_fields: dict[str, str]
```

用途：

- 发布时按用户兴趣过滤。
- 周报按领域分组。
- 未来做信源质量仪表盘。
- 未来做 paid tier 差异化。

### 6.2 Subscriber

当前已有：

```python
id: str
channel: str
address: str
langs: list[str]
tier: str
active: bool
confirmed: bool
delivery_hour: int
timezone: str
cadence: str
```

未来兴趣订阅字段：

```python
domains: list[str] = []
topics: list[str] = []
min_priority: int = 3
```

规则：

- 空 `domains/topics` 表示接收全部。
- 非空时按兴趣过滤。
- daily 和 weekly 可以用不同 subscriber 记录区分。
- 当前先手动维护个人 Email subscriber，不急于做公开订阅页。

---

## 7. Subscriber Flow

### 7.1 当前阶段

当前不做公开订阅页。

当前方式：

- 手动添加个人 Email subscriber。
- 通过 CLI 设置 `langs/cadence/timezone/delivery_hour`。
- daily 和 weekly 用不同 subscriber 记录区分。

示例：

```bash
./venv/bin/python scripts/add_subscriber.py \
  --id em:tristan:daily \
  --channel email \
  --address you@example.com \
  --langs zh,en \
  --tz Asia/Shanghai \
  --hour 8 \
  --cadence daily \
  --confirmed
```

weekly 另建一条：

```bash
./venv/bin/python scripts/add_subscriber.py \
  --id em:tristan:weekly \
  --channel email \
  --address you@example.com \
  --langs zh,en \
  --tz Asia/Shanghai \
  --hour 20 \
  --cadence weekly \
  --confirmed
```

### 7.2 未来订阅页

未来订阅页应允许用户选择：

- Email 地址。
- 输出语言：中文、英文或中英双语。
- 接收频率：daily 或 weekly。
- 接收时间。
- 时区。
- 感兴趣的 domains。
- 感兴趣的 topics。
- 最低信源优先级。

未来端点：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/` | 订阅表单 |
| POST | `/subscribe` | 创建 pending subscriber |
| GET | `/confirm` | 邮箱确认 |
| GET | `/unsubscribe` | 退订 |
| GET | `/preferences` | 修改偏好 |
| GET | `/healthz` | 健康检查 |

订阅页只写 subscriber store，不触碰 fetch/generate/publish 核心逻辑。

---

## 8. Publishing And Channels

### 8.1 Email 主线

Email 是当前和未来订阅系统的主交互入口。

Email 负责：

- 发送 daily digest。
- 发送 weekly review。
- 发送确认订阅邮件。
- 发送退订链接。
- 发送偏好修改链接。

每封邮件 footer 应包含：

- unsubscribe 链接。
- preferences 链接。
- 说明这是 AIS 自动邮件。

当前 MVP 可以只保留 unsubscribe 的数据结构，不实现公开端点。

### 8.2 聊天软件口子

WhatsApp、Telegram、微信生态等未来可以作为：

- 轻推送渠道。
- 用户问答入口。
- 偏好修改入口。
- 订阅确认辅助入口。

但聊天软件不应成为核心状态源。核心状态仍在 SQLite subscriber store。

未来新增聊天渠道时，只新增：

- Channel-specific Publisher。
- Channel-specific inbound handler。
- Subscriber address 绑定逻辑。

不改 AlphaSignal、Source taxonomy、Generate pipeline。

### 8.3 大陆中文用户准备

大陆中文用户当前不是优先方向，但未来仍可能接入。

准备方式：

- 保持中文输出能力。
- 保持 Email 可作为基础渠道。
- 保留 WeChat/公众号/企业微信/其他中文渠道 Publisher 口子。
- 不把任何单一平台作为核心依赖。
- 避免把大陆渠道逻辑写进生成层或信源层。

---

## 9. Deployment Plan

### 9.1 运行环境

主环境：

- macOS。
- Python virtualenv: `venv/`。
- launchd。
- SQLite。
- 本地文件系统存储 raw/generated/translations/run_stats。

可选未来环境：

- 海外 VPS。
- Cloudflare Tunnel。
- 静态归档站。
- 订阅偏好服务。

当前不要求上云。

### 9.2 环境变量

当前主线必需：

```env
GEMINI_API_KEY=...
RESEND_API_KEY=...
AIS_EMAIL_FROM=AIS <pulse@example.com>
```

SMTP fallback：

```env
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
```

可选未来渠道：

```env
TELEGRAM_BOT_TOKEN=...
WHATSAPP_...
WECHAT_...
```

原则：

- 密钥只放 `.env`。
- `config.yaml` 只放非敏感业务配置。
- 不把任何渠道密钥写入 plan 文档或代码。

### 9.3 数据目录

```text
data/raw/             # 原始抓取结果
data/index/           # URL 全局索引
data/generated/       # AlphaSignal JSON + 人工检查 md
data/translations/    # 按需翻译缓存
data/run_stats/       # 每轮运行统计
data/subscribers.db   # 订阅者与 deliveries 幂等表
test_outputs/         # dry-run 和本地报告
```

### 9.4 launchd 调度

保留四任务解耦：

| 任务 | 命令 | 频率 |
|---|---|---|
| Fetch | `pipeline.py fetch` | 每小时 `:05` |
| Generate | `pipeline.py generate` | 每 2 小时 `:20` |
| Daily Publish | `pipeline.py publish-daily --scheduled` | 每 5 分钟 tick，脚本内守卫北京时间 08:08 |
| Weekly Publish | `pipeline.py publish-weekly --scheduled` | 每 5 分钟 tick，脚本内守卫北京时间周五 20:08 |

调度原则：

- 抓取、生成、发布互不调用。
- 发布只读取已有 generated signals。
- dry-run 不发送真实邮件。
- scheduled 模式必须有时间窗口和幂等保护。

---

## 10. Implementation Roadmap

### Phase 1: Pipeline 稳定性修复

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

### Phase 2: 信源 Taxonomy 标准化

- [ ] 为所有 active source 补齐 `domain`。
- [ ] 为所有 active source 补齐 `topics`。
- [ ] 为所有 active source 补齐 `tags`。
- [ ] 为所有 active source 补齐 `priority`。
- [ ] 为所有 active source 增加 `quality_floor`。
- [ ] 为所有 active source 增加 `audience`。
- [ ] 增加 sources schema 检查测试。

验收标准：

- `sources.yaml` 能支持未来用户按领域和主题订阅。
- Fetch 写入 raw item 时保留 source metadata。

### Phase 3: AI 开源社区源扩展

- [ ] Hugging Face Daily Papers。
- [ ] r/LocalLLaMA。
- [ ] GitHub AI Trending / new-star repos。

验收标准：

- 新源能进入 `data/raw/YYYY-MM-DD/`。
- 新源能更新 `data/index/url_index.json`。
- 新源输出字段与现有源一致。

### Phase 4: Email Daily + Weekly 真实运行

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

### Phase 5: 用户兴趣订阅准备

- [ ] `Subscriber` 预留 `domains/topics/min_priority`。
- [ ] Orchestrator 按 subscriber 兴趣过滤 signals。
- [ ] Email 仍为主交互入口。
- [ ] WhatsApp、Telegram、微信生态仅保留 Publisher 扩展点。
- [ ] 公开订阅页作为后续项目，不进入当前 MVP。

---

## 11. OOP And Module Boundaries

### 11.1 Source 与 Ingestor

当前 `sources.yaml` 已经承担资产库角色，但 ingestor 层仍偏脚本式。下一阶段建议引入轻量 SourceSpec 概念。

SourceSpec 来自 `sources.yaml`：

```python
id: str
name: str
type: str
url: str
domain: str
topics: list[str]
tags: list[str]
priority: int
quality_floor: float
language: str
frequency_hint: str
active: bool
```

无需一开始做复杂基类，先约定所有 ingestor 输出统一 raw item：

```python
{
  "source_id": "...",
  "source": "...",
  "title": "...",
  "summary": "...",
  "url": "...",
  "published": "...",
  "domain": "...",
  "topics": [...],
  "tags": [...],
  "priority": 5,
  "quality_floor": 8.0,
  "language": "en"
}
```

### 11.2 Publisher 契约

新增渠道规则：

1. 新增 `publishers/<channel>.py`。
2. 复用或新增 renderer。
3. 在 orchestrator 的 publisher factory 注册。
4. `Subscriber.channel` 增加对应 literal。
5. 加 dry-run 测试和失败测试。

原则：

- Publisher 不负责选内容。
- Renderer 不负责判断用户资格。
- Orchestrator 负责过滤、翻译、幂等和分发。

### 11.3 Orchestrator 分层

下一步应明确分层：

1. Load signals。
2. Dedup。
3. Compliance。
4. Subscriber filter。
5. Interest filter。
6. Tier filter。
7. Translation ensure。
8. Render。
9. Transport。
10. Delivery record。

Interest filter 规则：

- `signal.domain in subscriber.domains`
- `signal.topics` 与 `subscriber.topics` 有交集
- `signal.priority >= subscriber.min_priority`

空兴趣字段表示不过滤。

---

## 12. 上线流程

### 12.1 本地检查

```bash
./venv/bin/python -m pytest -q
```

### 12.2 跑抓取和生成

```bash
./venv/bin/python pipeline.py fetch
./venv/bin/python pipeline.py generate
```

### 12.3 dry-run 审稿

```bash
./venv/bin/python pipeline.py publish-daily --dry-run
./venv/bin/python pipeline.py publish-weekly --dry-run
```

检查：

- 内容是否高密度。
- 是否有低质量追风内容。
- 中英双语是否正常。
- Email HTML 是否可读。

### 12.4 真实试发

先手动运行 publish，不启用 launchd 发布任务。确认成功后再安装/启动 daily 和 weekly plist。

---

## 13. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 邮件进垃圾箱 | 配 SPF/DKIM/DMARC，先发个人邮箱测试 |
| 内容质量下降 | 提高 `quality_floor`，强化 prompt，宁可少发 |
| LLM 成本上升 | 限制 `max_items_per_cycle`，翻译缓存复用 |
| 信源噪音增加 | 按 `priority` 和 `topics` 分层，不让低质源抢队列 |
| 渠道变化 | Publisher 插件化，核心管线不依赖渠道 |

---

## 14. 当前不做

当前阶段不做：

- 企业微信正式上线。
- 公开订阅网站。
- 支付系统。
- WhatsApp bot。
- 微信回调服务。
- X/Twitter 高维护爬虫。
- Farcaster 登录态抓取。
- 多渠道同时扩张。

这些都会增加复杂度，但不会立刻提高个人情报系统质量。

---

## 15. 总验收标准

本阶段完成时应满足：

- `pytest` 全绿。
- Email 是当前主渠道。
- `sources.yaml` 具备分层 taxonomy。
- 信源元数据进入 raw item 和 AlphaSignal。
- 生成层按质量门筛选，宁缺毋滥。
- dry-run 可审稿。
- daily 和 weekly 可分别发送到个人邮箱。
- 未来大陆中文用户和聊天软件渠道可接入，但不绑死当前架构。

---

*This document is the canonical AIS planning file from 2026-05-21 onward.*
