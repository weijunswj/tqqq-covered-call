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

### 2. Configure environment variables

Create a local `.env` file:

```bash
cp .env.example .env
```

Then set:

```env
TELEGRAM_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT=123456789
```

To fetch your chat ID automatically:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

### 3. Install Dependencies

```bash
pip install requests pytz python-dotenv
```

### 4. Test Run

Normal send:
```bash
python send_reminder.py
```

Dry-run (builds and prints message but does not send to Telegram):
```bash
DRY_RUN=1 python send_reminder.py
```

### 5. Schedule

#### Option A: GitHub Actions (optional)
A workflow is included at `.github/workflows/daily-reminder.yml`.

Credential sources (either works):
- **Recommended:** repo **Secrets** (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT`)
- **Also supported:** repo **Variables** with the same names

Path in GitHub UI:
- **Settings → Secrets and variables → Actions**

Then run via:
- scheduled cron (already configured for both EDT/EST windows), or
- **Actions → TQQQ Covered Call Reminder → Run workflow**.

If you do **not** see `TQQQ Covered Call Reminder` in Actions:
1. Open a PR that includes `.github/workflows/daily-reminder.yml`.
2. Merge that PR into your default branch (`master`/`main`).
3. Ensure Actions are enabled for the repo/org.
4. Refresh Actions page; the workflow should appear in the left sidebar.

#### Option B: Manus / Local scheduler
The script can also run via Manus / cron (no GitHub required).

For non-GitHub usage, configure credentials in your runtime environment:
- Local machine: create `.env` from `.env.example`.
- Manus/cron/server: set environment variables `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` in the scheduler/job config.

Cron example (SGT = UTC+8):
```
# EDT season: 8:30pm SGT = 12:30 UTC
30 12 * * 1-5 /usr/bin/python3 /path/to/send_reminder.py

# EST season: 9:30pm SGT = 13:30 UTC
30 13 * * 1-5 /usr/bin/python3 /path/to/send_reminder.py
```


### Scheduler conflict note


How to avoid scheduler conflicts (Manus vs GitHub):
1. Pick one primary scheduler.
2. If using Manus only, disable GitHub schedule by removing the `schedule:` block in `.github/workflows/daily-reminder.yml` (keep `workflow_dispatch` for manual runs if wanted).
3. If using GitHub only, disable the Manus job in Manus scheduler UI.
4. Verify only one run source is active to avoid duplicate Telegram messages.

If both Manus scheduler and GitHub Actions schedule are enabled, the script may run twice and send duplicate messages.
Use **one scheduler only**:
- Keep Manus as primary: disable/remove the `schedule` block in `.github/workflows/daily-reminder.yml` and keep `workflow_dispatch` for manual runs.
- Keep GitHub Actions as primary: disable Manus schedule.

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
