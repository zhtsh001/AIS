# AIS 订阅与精细化交付设计方案 v2
*Date: 2026-05-21*

---

## 1. 当前定位

本文件描述未来订阅系统设计，不是当前 MVP 必须完成项。

当前阶段：

- 用户交互主入口保持 Email。
- Subscriber 先手动维护。
- 不做公开订阅页。
- 不做支付。
- 不做聊天软件交互。

设计目标是保证未来扩展时，不需要推翻现有 pipeline。

---

## 2. 未来用户体验

未来订阅页应允许用户选择：

- Email 地址。
- 输出语言：中文、英文或中英双语。
- 接收频率：daily 或 weekly。
- 接收时间。
- 时区。
- 感兴趣的 domains。
- 感兴趣的 topics。
- 最低信源优先级。

用户最终不是订阅“全部 AIS”，而是订阅自己关心的高价值信源切片。

---

## 3. 订阅偏好模型

在现有 `Subscriber` 基础上增加：

```python
domains: list[str] = []
topics: list[str] = []
min_priority: int = 3
```

含义：

- `domains=[]`: 接收全部领域。
- `topics=[]`: 接收全部主题。
- `min_priority=3`: 只接收 priority 大于等于 3 的信号。

示例：

```python
Subscriber(
    id="em:user:daily",
    channel="email",
    address="user@example.com",
    langs=["zh", "en"],
    cadence="daily",
    domains=["AI", "HardTech"],
    topics=["open_source_ai", "agents", "semiconductors"],
    min_priority=4,
    confirmed=True,
)
```

---

## 4. 分发过滤规则

发布时按以下顺序过滤：

1. `active=True`。
2. `confirmed=True`。
3. `cadence` 匹配当前 publish cycle。
4. `tier` 匹配信号可见性。
5. `domain` 命中 subscriber domains，空列表则不过滤。
6. `topics` 与 subscriber topics 有交集，空列表则不过滤。
7. `priority >= min_priority`。
8. `deliveries` 表确认未发送过。

这些逻辑属于 orchestrator，不属于 Publisher。

---

## 5. Email 交互主线

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

---

## 6. 未来订阅页

未来可新增 `subscribe_server.py`，但不进入当前 MVP。

建议端点：

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

## 7. 聊天软件口子

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

---

## 8. 大陆中文用户准备

大陆中文用户当前不是优先方向，但未来仍可能接入。

准备方式：

- 保持中文输出能力。
- 保持 Email 可作为基础渠道。
- 保留 WeChat/公众号/企业微信/其他中文渠道 Publisher 口子。
- 不把任何单一平台作为核心依赖。
- 避免把大陆渠道逻辑写进生成层或信源层。

---

## 9. 当前不做

- 公开订阅页。
- 支付系统。
- WhatsApp bot。
- 微信回调服务。
- 用户偏好 UI。
- 自动化大陆渠道接入。

---

## 10. 验收标准

未来实现本设计时，应满足：

- 用户可以按领域和 topic 订阅。
- Email 仍是主交互入口。
- daily 和 weekly 可以独立订阅。
- 中英双语正常工作。
- 聊天软件可以作为扩展入口，但不影响核心系统。
- 大陆中文用户可以通过新增 Publisher 接入。

---

*Subscription design updated for Email-first and interest-based delivery.*
