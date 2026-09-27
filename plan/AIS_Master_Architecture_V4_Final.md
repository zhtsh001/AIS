# Alpha Intelligence System (AIS) 总纲与架构白皮书 (V6)
*Drafted for Tristan*
*Date: 2026-05-21 (V6 revision: personal intelligence system + Email-first architecture)*

---

## 一、核心定位

AIS 不是新闻聚合器，也不是热点追踪工具。AIS 的核心定位是：

**一个长期维护的高智力密度个人情报系统。**

它的核心资产不是某个推送渠道，而是：

1. 可长期积累、可分层订阅的 Alpha 信源库。
2. 面向非共识、远见和结构性变化的筛选能力。
3. 高密度、低噪音、可持续复用的生成与发布管线。

系统优先级固定为：

`信源质量 > 筛选质量 > 输出密度 > 渠道数量 > 自动化规模`

宁可每天只输出 1 到 3 条真正有价值的信号，也不要为了形成日报而填充低质量内容。

---

## 二、产品原则

### 1. 质量优于数量

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

### 2. Alpha 不是新闻

抓取层可以广，但生成层必须窄。每条内容都必须回答：

> 这条信息为什么可能改变未来结构？

如果只能回答“发生了什么”，它不应进入最终输出。

### 3. 信源库是长期核心资产

`sources.yaml` 是 AIS 的核心资产库，不只是抓取配置。每个信源都必须有清晰的领域、主题、标签、优先级和维护理由。

未来用户可以按领域或主题选择订阅范围，因此从现在开始就要保留这套分类结构。

### 4. 渠道必须解耦

当前主渠道是 Email。Telegram、WhatsApp、微信生态、RSS、Feishu 等都只作为 `Publisher` 扩展口保留。

中国大陆中文用户当前不是优先受众，但未来仍可能接入。架构上必须保证新增大陆渠道时，不需要改 Fetch、Generate、AlphaSignal、Subscriber 的核心逻辑。

---

## 三、信源库分层结构

### 1. 一级领域 `domain`

建议标准域：

- `AI`
- `Web3`
- `Biotech`
- `HardTech`
- `Cyber`
- `Macro`
- `Science`
- `TechBiz`

### 2. 二级主题 `topics`

一个信源可以属于多个 topic。示例：

- AI: `frontier_models`, `agents`, `alignment`, `open_source_ai`, `ai_infra`, `robotics`
- Web3: `ethereum`, `zk`, `mev`, `protocol_research`, `crypto_markets`
- Biotech: `synthetic_biology`, `drug_discovery`, `clinical_trials`, `ai_for_science`
- HardTech: `semiconductors`, `space`, `materials`, `energy`, `quantum`
- Cyber: `zero_day`, `exploit_research`, `supply_chain_security`

### 3. 三级标签 `tags`

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

### 4. Source 元数据模板

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

---

## 四、系统管线

### 1. Fetch

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

### 2. Generate

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

### 3. Publish

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

## 五、数据模型方向

### AlphaSignal

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

### Subscriber

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

## 六、发布策略

### 当前主线

- Email 为主。
- 默认中英双语。
- 每日北京时间 08:08 发送 daily digest。
- 每周北京时间周五 20:08 发送 weekly review。
- 真实发送前必须先 dry-run 到 `test_outputs/`。

### 未来渠道

聊天软件只作为交互和轻推送入口，不承载核心业务逻辑。新增渠道时，只新增 `Publisher` 和必要 `Renderer`，不改核心管线。

中国大陆中文用户未来可通过 Email、微信生态、公众号或其他合规渠道接入，但不再把任何单一中文 IM 平台作为系统基础设施。

---

## 七、近期路线

### v0.1 当前主线

- 修复现有 pipeline 稳定性。
- 标准化 `sources.yaml` taxonomy。
- 扩展 AI 开源社区信源。
- 跑通 Email daily + weekly。
- 保留 dry-run 审稿流程。

### v0.2

- Subscriber 兴趣订阅字段。
- 更完整的订阅偏好管理。
- RSS 或静态归档。
- 付费 tier 与 paid-only 字段策略。

### v0.3

- WhatsApp / 微信生态等聊天渠道 PoC。
- 大陆中文用户渠道评估。
- 更完整的信源质量仪表盘。

---

## 八、验收标准

- 计划文档与代码方向一致。
- Email 是当前主渠道。
- 信源库是长期核心资产。
- 输出质量优先级高于数量。
- 未来大陆中文用户和聊天软件渠道可接入，但不绑死当前架构。
- 后续开发可以按本文件拆任务。

---

*Document updated for V6: Email-first personal intelligence architecture.*
