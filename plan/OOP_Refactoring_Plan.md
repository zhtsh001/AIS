# AIS 面向对象与模块化重构方案 v3
*Date: 2026-05-21*

---

## 1. 重构目标

当前代码已经完成 Publisher、Renderer、Subscriber、AlphaSignal 的初步解耦。下一阶段重构重点不是为了抽象而抽象，而是支持三个长期能力：

1. 分层 Alpha 信源库。
2. 按领域和 topic 的个性化订阅。
3. Email 主渠道稳定运行，同时保留未来聊天渠道扩展。

---

## 2. 数据模型演进

### 2.1 AlphaSignal

现有 `AlphaSignal` 已能表达内容主体和多语言 bodies。下一步应增加或标准化信源分类字段：

```python
domain: str
topics: list[str]
tags: list[str]
priority: int
```

用途：

- 发布时按用户兴趣过滤。
- 周报按领域分组。
- 未来做信源质量仪表盘。
- 未来做 paid tier 差异化。

### 2.2 Subscriber

现有 `Subscriber` 已有 channel、address、langs、tier、cadence。下一步预留兴趣偏好：

```python
domains: list[str] = []
topics: list[str] = []
min_priority: int = 3
```

规则：

- 空 `domains/topics` 表示接收全部。
- 非空则按交集过滤。
- `min_priority` 用于过滤低优先级源。
- 个人阶段可以先不暴露 UI，只在 CLI 或数据库里维护。

---

## 3. Source 与 Ingestor 抽象

当前 `sources.yaml` 已经承担资产库角色，但 ingestor 层仍偏脚本式。下一阶段建议引入轻量 SourceSpec 概念。

### SourceSpec

来自 `sources.yaml` 的结构化对象：

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

### Ingestor 契约

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

这比新增深层继承更重要。

---

## 4. Publisher 架构

当前主线：

- `EmailPublisher`
- `HTMLRenderer`

保留接口：

- `TelegramPublisher`
- `RSSPublisher`
- `WeChatPublisher`
- `WhatsAppPublisher`
- `FeishuPublisher`

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

---

## 5. Orchestrator 重构方向

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

其中 interest filter 应基于：

- `signal.domain in subscriber.domains`
- `signal.topics` 与 `subscriber.topics` 有交集
- `signal.priority >= subscriber.min_priority`

空兴趣字段表示不过滤。

---

## 6. 质量门模块

建议把质量门从 prompt 里部分抽出来：

- Source gate: 信源优先级和维护理由。
- Candidate gate: 本地规则过滤活动、营销、招聘、通稿。
- LLM gate: score 和 quality_floor。
- Publish gate: compliance 和重复发送保护。

未来可以有独立 `processors/quality.py`，但第一阶段不强求。

---

## 7. 当前不做的重构

暂不做：

- 大型框架化 Ingestor 基类。
- 公开订阅 Web 服务。
- 支付系统。
- 企业微信恢复。
- 多渠道同步上线。

这些都会增加复杂度，但不会立刻提高个人情报系统质量。

---

## 8. 验收标准

- `AlphaSignal` 能携带 source taxonomy。
- `Subscriber` 能表达兴趣偏好。
- Orchestrator 能按 cadence 和兴趣过滤。
- Email Publisher 仍然是主线。
- WhatsApp、微信生态和 Telegram 可作为未来 Publisher 接入，不污染核心管线。

---

*Refactoring plan updated for source taxonomy and Email-first operation.*
