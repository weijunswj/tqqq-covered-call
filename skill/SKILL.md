---
name: tqqq-covered-call
description: TQQQ covered call income strategy with daily Telegram reminder automation. Use when the user asks about selling covered calls on TQQQ, setting up a daily pre-market options reminder, and managing roll/pause decisions with VIX, ADX, and macro-event filters.
---

# TQQQ Covered Call Strategy

## Strategy Overview

Sell **OTM covered calls** on TQQQ every week to generate income. The strategy only works in **range-bound markets** — pause immediately when the market trends.

| Parameter | Value |
|---|---|
| Strike | Default: current price + $3 ( OTM ); if VIX 22–25: +$3.5 ( OTM ) |
| DTE | Default: closest weekly expiry to 7 DTE |
| DTE exception | If VIX < 16 and 7 DTE +$3 OTM mid premium < $0.20, use closest expiry to 14 DTE |
| Cycle | Weekly |
| Roll | Once at market open if ITM → new strike per VIX rule, same selected expiry |
| Max rolls/cycle | 3 — then let it ride to expiry |
| Close | DTE 0 at open |

---

## Entry Conditions ( ALL must be true )

- VIX between 15–25.
- ADX ( 14 ) < 25 — range-bound, no strong trend.

---

## Pause / Skip Conditions

| Trigger | Threshold | Action |
|---|---|---|
| ADX trending | ADX > 25 | Pause new entries |
| VIX elevated | VIX > 25 | Pause new entries |
| VIX extreme | VIX ≥ 40 | Close existing call + sit out |
| FOMC / Fed event | Today | Skip open |
| CPI / PCE / NFP | Today | Skip open |
| Big tech earnings before open | MSFT, AAPL, NVDA, GOOGL, GOOG, META, AMZN, TSLA, AMD, AVGO, NFLX, QCOM | Skip open |
| VIX too low | VIX < 15 | Skip — premium too thin |

---

## Resume Conditions

| Pause Reason | Resume When |
|---|---|
| Bull run / ADX > 25 | TQQQ pulls back ≥ 5% from recent high |
| VIX 25–40 | VIX drops below 22 for 2 consecutive days |
| VIX ≥ 40 | VIX drops below 25 for 2 consecutive days |
| FOMC / macro event | Next trading day |
| Earnings at open | Next trading day |

---

## Roll Decision Rules

1. Check at market open only ( once per day ).
2. If call is ITM → buy back + sell new call at strike per VIX rule ( +$3 default, +$3.5 at VIX 22–25 ), same selected weekly expiry.
3. If 3+ rolls already done this cycle → let it ride, no more rolls.
4. If net roll cost > original premium collected → close the call, don't roll.

---

## Pre-Event Close Warning

**Day before FOMC or big tech earnings ( before open ):**
- If your strike is within ±$2 of current price → close the call at open today.
- If strike > current price + $2 → let it ride, event risk already priced in.

---

## Existing Position on Pause Day

| Trigger | Call is Deep OTM ( > $2 away ) | Call is Near ATM / ITM |
|---|---|---|
| FOMC / CPI / NFP today | Hold, let decay | Close before event |
| Earnings before open | Hold | Close pre-market |
| VIX 25–40 | Hold, let decay | Roll once then hold |
| VIX ≥ 40 | Close | Close |
---

## 9Sig Status ( Display Only )

Still compute and display:
- ATH DD status.
- TQQQ prev close as % of 315-day high.

This section is **informational only** and does not affect proceed/pause/close decisions.

---

## Daily Reminder Script

A fully automated daily Telegram reminder lives at:
```
/home/ubuntu/tqqq_reminder/send_reminder.py
```

**Auto-checks:** TQQQ prev daily close ( D1 chart ), VIX, ADX ( 14 ), 9Sig status ( 315d lookback, display-only ), ForexFactory events ( FOMC / CPI / NFP / holidays ), Nasdaq earnings API ( big tech before open, today + tomorrow ).

**Output:** Telegram message with today's call, exact strike, selected weekly DTE, roll instructions, pre-event close warning, 9Sig status, and pause day counter.

**Schedule:** GitHub Actions handles scheduling ( Mon–Fri, 8:30pm SGT during EDT / 9:30pm SGT during EST ).

### Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather), get the bot token.
2. Send the bot any message to register your chat ID.
3. Update `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` at the top of `send_reminder.py`.
4. Configure and maintain the GitHub Actions workflow schedule.

### ADX Calculation Notes

Uses proper Wilder smoothing with SMA seed. Requires `range=2y&interval=1d` daily data for stable output. Valid range: 0–100. Below 20 = range-bound. Above 25 = trending.
