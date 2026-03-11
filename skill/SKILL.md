---
name: tqqq-covered-call
description: TQQQ covered call income strategy with daily Telegram reminder automation. Use when the user asks about selling covered calls on TQQQ, setting up a daily pre-market options reminder, managing roll decisions, pause/resume conditions, or integrating the Phoenix 9Sig ATH DD rule with a covered call overlay.
---

# TQQQ Covered Call Strategy

## Strategy Overview

Sell **+$3 OTM covered calls** on TQQQ every 2 weeks to generate income. The strategy only works in **range-bound markets** — pause immediately when the market trends.

| Parameter | Value |
|---|---|
| Strike | Current price + $3 ( OTM ) |
| DTE | Closest expiry to 14 days |
| Cycle | Bi-weekly |
| Roll | Once at market open if ITM → new +$3 OTM, same DTE |
| Max rolls/cycle | 3 — then let it ride to expiry |
| Close | DTE 0 at open |

---

## Entry Conditions ( ALL must be true )

- VIX between 15–25
- ADX ( 14 ) < 20 — range-bound, no strong trend
- TQQQ prev daily close > 70% of its 315-day high ( 9Sig ATH DD rule )

---

## Pause / Skip Conditions

| Trigger | Threshold | Action |
|---|---|---|
| ADX trending | ADX > 25 | Pause new entries |
| VIX elevated | VIX > 25 | Pause new entries |
| VIX extreme | VIX ≥ 40 | Close existing call + sit out |
| ATH DD triggered | TQQQ prev close < 70% of 315d high | Hard skip — hold shares uncapped |
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
| ATH DD triggered | TQQQ prev close recovers above 70% of 315d high |
| FOMC / macro event | Next trading day |
| Earnings at open | Next trading day |

---

## Roll Decision Rules

1. Check at market open only ( once per day ).
2. If call is ITM → buy back + sell new +$3 OTM call, closest to 14d DTE.
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
| ATH DD triggered | Close | Close |

---

## 9Sig ATH DD Rule ( Phoenix 9Sig Integration )

Uses **yesterday's confirmed daily close** ( not intraday price ):

> If TQQQ prev daily close < 70% of the highest daily close over the last 315 trading days → skip selling covered calls.

The 315-day lookback window refreshes daily. Resume only when prev close recovers above 70% threshold. Rationale: a +$3 premium is irrelevant vs a potential 50–100% bounce after a crash — hold shares uncapped.

---

## Daily Reminder Script

A fully automated daily Telegram reminder lives at:
```
/home/ubuntu/tqqq_reminder/send_reminder.py
```

**Auto-checks:** TQQQ prev daily close ( D1 chart ), VIX, ADX ( 14 ), ATH DD status ( 315d lookback ), ForexFactory events ( FOMC / CPI / NFP / holidays ), Nasdaq earnings API ( big tech before open, today + tomorrow ).

**Output:** Telegram message with today's call, exact strike, roll instructions, pre-event close warning, 9Sig ATH DD status, and pause day counter.

**Schedule:** Mon–Fri, 8:30pm SGT ( EDT ) / 9:30pm SGT ( EST ).

### Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather), get the bot token.
2. Send the bot any message to register your chat ID.
3. Update `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` at the top of `send_reminder.py`.
4. Schedule via Manus scheduler or system cron.

### ADX Calculation Notes

Uses proper Wilder smoothing with SMA seed. Requires `range=2y&interval=1d` daily data for stable output. Valid range: 0–100. Below 20 = range-bound. Above 25 = trending.
