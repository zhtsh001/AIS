# AIS Scheduler Setup (LaunchAgents)

The four launchd plists in `scripts/launchd/` invoke the unified
`pipeline.py` CLI:

| Plist | Command | Cadence |
|---|---|---|
| `ai.ais.fetch.raw.plist` | `pipeline.py fetch` | every hour at `:05` |
| `ai.ais.generate.alpha.plist` | `pipeline.py generate` | every 2 hours at `:20` |
| `ai.ais.push.daily.plist` | `pipeline.py publish-daily --scheduled` | every 5 min; runs once inside BJ 08:08-08:12 |
| `ai.ais.push.weekly.plist` | `pipeline.py publish-weekly --scheduled` | every 5 min; runs once Fri BJ 20:08-20:12 |

The `--scheduled` flag tells the orchestrator to honor the BJ time window
and the once-per-day idempotency guard (`utils/schedule_guard.py`).

## Install

```bash
cp /Users/tristan/Desktop/AIS/ais_engine/scripts/launchd/ai.ais.fetch.raw.plist ~/Library/LaunchAgents/
cp /Users/tristan/Desktop/AIS/ais_engine/scripts/launchd/ai.ais.generate.alpha.plist ~/Library/LaunchAgents/
cp /Users/tristan/Desktop/AIS/ais_engine/scripts/launchd/ai.ais.push.daily.plist ~/Library/LaunchAgents/
cp /Users/tristan/Desktop/AIS/ais_engine/scripts/launchd/ai.ais.push.weekly.plist ~/Library/LaunchAgents/
```

## Start

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.ais.fetch.raw.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.ais.generate.alpha.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.ais.push.daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.ais.push.weekly.plist
```

## Stop

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.ais.fetch.raw.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.ais.generate.alpha.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.ais.push.daily.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.ais.push.weekly.plist
```

## Manual dry run

Useful when you want to verify what *would* be sent without hitting any
real channel — the orchestrator builds the batches and archives a plaintext
copy to `test_outputs/` so you can review:

```bash
python pipeline.py publish-daily --dry-run
python pipeline.py publish-weekly --dry-run
```

## Outbound enablement

A publisher is enabled when:
1. `config.yaml:publishers.<channel>.enabled` is `true`, AND
2. the required env vars (e.g. `TELEGRAM_BOT_TOKEN` for Telegram,
   `RESEND_API_KEY` + `AIS_EMAIL_FROM` for Email) are present.

If either is missing, the orchestrator logs a warning and falls through to
the local-archive path so cron still produces a usable digest in
`test_outputs/`.

## Deprecated: WeChat Push Safety Switch

The old `WECHAT_PUSH_ENABLED=1` toggle is gone along with the WeCom code
(see `_deprecated/`). Channel-level enablement is now per-Publisher in
`config.yaml`.
