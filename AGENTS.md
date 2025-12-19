# AGENTS.md

This file provides authoritative guidance for AI coding agents (e.g., OpenAI Codex and similar systems) when working with code in this repository.

## Project Overview

vibe-quant is a Binance USDT-Margined perpetual futures position executor designed for **Hedge Mode reduce-only closing**. It uses ccxt + WebSocket to execute small-lot position exits with minimal market impact through execution mode rotation (maker → aggressive limit).

**Key constraints:**

- All orders must be `reduceOnly=True`
- Hedge mode requires `positionSide=LONG/SHORT`
- Target latency: < 200ms end-to-end

## Architecture

### Core Modules
- **ConfigManager**: Global defaults + per-symbol overrides, optional hot reload
- **ExchangeAdapter** (ccxt): Markets/positions/balance fetch, order placement/cancellation
- **WSClient**: Subscribes to trade + best bid/ask streams
- **SignalEngine**: Exit condition evaluation, sliding window returns, multiplier calculation
- **ExecutionEngine**: Per-side state machine, mode rotation, order management
- **RiskManager**: Liquidation distance fallback, stale data protection, rate limiting
- **Logger**: Daily rotating logs
- **Notifier**: Telegram notifications

### Execution Mode Rotation
Per `symbol + positionSide`, maintains state machine: `IDLE → PLACE → WAIT → (FILLED|TIMEOUT) → CANCEL → COOLDOWN → IDLE`

Two execution modes:
1. **MAKER_ONLY**: Post-only limit (GTX), timeout cancel
2. **AGGRESSIVE_LIMIT**: Limit closer to execution direction, no post-only

### Signal Conditions
- LONG exit: `last_trade > prev_trade && best_bid >= last_trade` OR bid improvement
- SHORT exit: `last_trade < prev_trade && best_ask <= last_trade` OR ask improvement
- Acceleration: Sliding window return triggers larger position slices

### Quantity Calculation
`final_mult = base_mult × roi_mult × accel_mult` (capped by `max_mult` and `max_order_notional`)

Completion: Position is done when remaining quantity rounds to 0 via `stepSize` or is below `minQty`.

## Configuration

YAML-based with global defaults and per-symbol overrides. Key sections:
- `global.execution`: TTL, cooldown, mode rotation thresholds, pricing strategy
- `global.accel`: Sliding window acceleration tiers
- `global.roi`: ROI-based multiplier tiers
- `global.risk`: Liquidation distance thresholds
- `global.rate_limit`: Orders/cancels per second limits
- `symbols.<SYMBOL>`: Per-symbol overrides

## Tech Stack (Planned)

- **Language**: Python 3.11+
- **Async**: asyncio
- **Exchange**: ccxt (REST) + binance-futures-connector or websocket-client (WS)
- **Config**: PyYAML + pydantic
- **Logging**: loguru
- **Notifications**: python-telegram-bot
- **Testing**: pytest + pytest-asyncio

## Markdown 编写规范

编写 `.md` 文件时，注意 GitHub 渲染规则：

- **换行**：单个换行符不会渲染为换行。使用 `<br>` 标签换行（行尾两个空格容易被编辑器自动删除），或用空行分隔段落。


# IMPORTANT:
# emphasize modularity (multiple files) and discourage a monolith (one giant file).
# Always read memory-bank/architecture.md before writing any code. Include entire database schema.
# Always read memory-bank/design-document.md before writing any code.
# After adding a major feature or completing a milestone, update memory-bank/architecture.md with any new architectural insights (including an explanation of each file's role), and record what was done in memory-bank/progress.md for future developers.
# 先讨论，不明白的地方反问我，先不着急编码
