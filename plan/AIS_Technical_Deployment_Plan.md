# Alpha Intelligence System (AIS) 技术架构与部署方案 v2
*Date: 2026-05-21*

---

## 1. 部署目标

当前部署目标是稳定运行个人情报系统：

- Mac mini 本地常驻。
- launchd 定时调度。
- SQLite 本地状态。
- Email Publisher 作为主发布渠道。
- dry-run 本地审稿作为上线保护。

企业微信不再是正式上线路径。微信生态可以在未来作为独立 Publisher 重新评估。

---

## 2. 运行环境

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

---

## 3. 核心命令

统一入口：

```bash
./venv/bin/python pipeline.py fetch
./venv/bin/python pipeline.py generate
./venv/bin/python pipeline.py publish-daily --dry-run
./venv/bin/python pipeline.py publish-weekly --dry-run
```

真实定时入口：

```bash
./venv/bin/python pipeline.py publish-daily --scheduled
./venv/bin/python pipeline.py publish-weekly --scheduled
```

---

## 4. launchd 调度

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

## 5. 环境变量

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

---

## 6. 数据目录

```text
data/raw/             # 原始抓取结果
data/index/           # URL 全局索引
data/generated/       # AlphaSignal JSON + 人工检查 md
data/translations/    # 按需翻译缓存
data/run_stats/       # 每轮运行统计
data/subscribers.db   # 订阅者与 deliveries 幂等表
test_outputs/         # dry-run 和本地报告
```

Raw 数据保留策略：

- 默认保留 30 天。
- 默认容量上限 100MB。
- 跨天重复出现保留，用于观察信号复现频率。

---

## 7. 上线流程

### 1. 本地检查

```bash
./venv/bin/python -m pytest -q
```

### 2. 跑抓取和生成

```bash
./venv/bin/python pipeline.py fetch
./venv/bin/python pipeline.py generate
```

### 3. dry-run 审稿

```bash
./venv/bin/python pipeline.py publish-daily --dry-run
./venv/bin/python pipeline.py publish-weekly --dry-run
```

检查：

- 内容是否高密度。
- 是否有低质量追风内容。
- 中英双语是否正常。
- Email HTML 是否可读。

### 4. 添加个人 subscriber

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

### 5. 真实试发

先手动运行 publish，不启用 launchd 发布任务。确认成功后再安装/启动 daily 和 weekly plist。

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 邮件进垃圾箱 | 配 SPF/DKIM/DMARC，先发个人邮箱测试 |
| 内容质量下降 | 提高 `quality_floor`，强化 prompt，宁可少发 |
| LLM 成本上升 | 限制 `max_items_per_cycle`，翻译缓存复用 |
| 信源噪音增加 | 按 `priority` 和 `topics` 分层，不让低质源抢队列 |
| 渠道变化 | Publisher 插件化，核心管线不依赖渠道 |

---

## 9. 当前不部署

- 企业微信。
- 公开订阅网站。
- 支付 webhook。
- WhatsApp 常驻服务。
- 微信生态回调服务。

这些均为未来可选扩展，不进入当前上线清单。

---

*Deployment plan updated for Email-first AIS operations.*
