# TQQQ Covered Call Daily Reminder

Automated daily pre-market Telegram reminder for a TQQQ +$3 OTM covered call income strategy. Checks market conditions every morning and tells you exactly what to do — proceed, pause, skip, or close.

---

## What It Does

Runs Mon–Fri before US market open. Fetches live data, evaluates conditions, and sends a Telegram message with:

- **Today's call** — PROCEED / PAUSE / SKIP / CLOSE & SIT OUT
- **Exact strike to use** ( auto-widens to +$5 on high-risk days )
- **Roll instructions** if you have an open position
- **Pre-event close warning** if FOMC or big tech earnings are tomorrow
- **9Sig ATH DD status** — whether you're in the Phoenix 9Sig drawdown skip window
- **Pause day counter** — current streak + all-time total

---

## Checks Performed

| Check | Source |
|---|---|
| TQQQ prev daily close ( D1 ) | Yahoo Finance |
| VIX level | Yahoo Finance |
| ADX ( 14 ) — trend strength | Yahoo Finance ( computed ) |
| ATH DD — TQQQ vs 315-day high | Yahoo Finance ( computed ) |
| FOMC / Fed events | ForexFactory JSON API |
| CPI / PCE / NFP today | ForexFactory JSON API |
| US market holidays | ForexFactory JSON API |
| Big tech earnings before open ( today + tomorrow ) | Nasdaq earnings API |

**Big tech watchlist:** MSFT, AAPL, NVDA, GOOGL, GOOG, META, AMZN, TSLA, AMD, AVGO, NFLX, QCOM

---

## Strategy Rules ( Quick Reference )

| Parameter | Value |
|---|---|
| Strike | +$3 OTM ( current price + $3 ) |
| DTE | Closest expiry to 14 days |
| Cycle | Bi-weekly |
| Roll | Once at open if ITM → new +$3 OTM, same DTE |
| Max rolls/cycle | 3 — then let it ride |
| Close | DTE 0 at open |

**Proceed when:** VIX 15–25 · ADX < 20 · TQQQ > 70% of 315d high

**Pause when:** ADX > 25 · VIX > 25 · FOMC/CPI/NFP day · earnings at open

**Close existing call:** VIX ≥ 40 · ATH DD triggered

**Pre-event:** Close call if within $2 of strike, day before FOMC/earnings

For full strategy rationale and 9Sig integration rules, see [`skill/references/9sig-rules.md`](skill/references/9sig-rules.md).

---

## Setup

### 1. Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` and follow the steps.
3. Copy the bot token ( format: `123456789:ABCdef...` ).
4. Send your new bot any message ( e.g. "hi" ) to register your chat ID.

### 2. Configure the Script

Edit the top of `send_reminder.py`:

```python
TELEGRAM_TOKEN = "your_bot_token_here"
TELEGRAM_CHAT  = "your_chat_id_here"   # fetch via getUpdates if unsure
```

To fetch your chat ID automatically:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

### 3. Install Dependencies

```bash
pip install requests pytz
```

### 4. Test Run

```bash
python send_reminder.py
```

### 5. Schedule ( Manus Scheduler )

The script is pre-scheduled via Manus at:
- **8:30pm SGT** Mon–Fri during EDT ( Mar–Nov )
- **9:30pm SGT** Mon–Fri during EST ( Nov–Mar )

To run via system cron instead ( SGT = UTC+8 ):
```
# EDT season: 8:30pm SGT = 12:30 UTC
30 12 * * 1-5 /usr/bin/python3 /path/to/send_reminder.py

# EST season: 9:30pm SGT = 13:30 UTC
30 13 * * 1-5 /usr/bin/python3 /path/to/send_reminder.py
```

---

## State Tracking

Pause state is persisted in `state.json`:

```json
{
  "paused": false,
  "reason": null,
  "since": null,
  "days_paused": 0,
  "resume_cond": null,
  "total_days_paused": 0
}
```

The script auto-updates this file daily — no manual intervention needed. Delete or reset to `{}` to clear state.

---

## Files

```
tqqq-covered-call/
├── send_reminder.py          ← main script
├── state.json                ← auto-managed pause state
├── README.md                 ← this file
└── skill/
    ├── SKILL.md              ← Manus skill for strategy reasoning
    └── references/
        └── 9sig-rules.md     ← full Phoenix 9Sig™ strategy rules
```
