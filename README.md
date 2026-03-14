# TQQQ Covered Call Daily Reminder

Automated daily pre-market Telegram reminder for a TQQQ covered call income strategy. It checks market conditions each morning and tells you whether to proceed, pause, skip, or close.

---

## What It Does

Runs Mon–Fri before US market open. Fetches live data, evaluates conditions, and sends a Telegram message with:

- **Today's call** — PROCEED / PAUSE / SKIP / CLOSE & SIT OUT.
- **Exact strike to use** ( dynamic +$3 / +$3.5 OTM rule ).
- **Selected expiry / DTE rule** ( weekly 7 DTE default, with low-vol exception ).
- **Roll instructions** if you have an open position.
- **Pre-event close warning** if FOMC or big tech earnings are tomorrow.
- **9Sig status** — ATH DD status and % of 315d high ( display-only ).
- **Pause day counter** — current streak + all-time total.

---

## Checks Performed

| Check | Source |
|---|---|
| TQQQ prev daily close ( D1 ) | Yahoo Finance |
| VIX level | Yahoo Finance |
| ADX ( 14 ) — trend strength | Yahoo Finance ( computed ) |
| 9Sig status ( ATH DD + % of 315d high ) | Yahoo Finance ( computed ) |
| FOMC / Fed events | ForexFactory JSON API |
| CPI / PCE / NFP today | ForexFactory JSON API |
| US market holidays | ForexFactory JSON API |
| Big tech earnings before open ( today + tomorrow ) | Nasdaq earnings API |

**Big tech watchlist:** MSFT, AAPL, NVDA, GOOGL, GOOG, META, AMZN, TSLA, AMD, AVGO, NFLX, QCOM.

---

## Strategy Rules ( Quick Reference )

| Parameter | Value |
|---|---|
| Strike | Default: +$3 OTM ( current price + $3 ); if VIX 22–25: +$3.5 OTM |
| DTE | Default: closest weekly expiry to 7 DTE |
| DTE exception | If VIX < 16 **and** 7 DTE +$3 OTM mid premium < $0.20, use closest expiry to 14 DTE |
| Cycle | Weekly |
| Roll | Once at open if ITM → new strike per VIX rule, same selected expiry |
| Max rolls/cycle | 3 — then let it ride |
| Close | DTE 0 at open |

**Proceed when:** VIX 15–25 · ADX < 25.

**Pause when:** ADX > 25 · VIX > 25 · FOMC/CPI/NFP day · earnings at open.

**Close existing call:** VIX ≥ 40.

**Pre-event:** Close call if within $2 of strike, day before FOMC / earnings.

> 9Sig ATH DD status is still displayed for context, but does not drive proceed/pause/close decisions.

---

## Setup

### 1. Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` and follow the steps.
3. Copy the bot token ( format: `123456789:ABCdef...` ).
4. Send your new bot any message ( e.g. `hi` ) to register your chat ID.

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

### 3. Install dependencies

```bash
pip install requests pytz python-dotenv
```

### 4. Test run

Normal send:

```bash
python send_reminder.py
```

Dry-run ( builds and prints message but does not send to Telegram ):

```bash
DRY_RUN=1 python send_reminder.py
```

### 5. Schedule ( GitHub Actions )

A workflow is included at `.github/workflows/daily-reminder.yml`.

Credential sources ( either works ):
- **Recommended:** repo **Secrets** ( `TELEGRAM_TOKEN`, `TELEGRAM_CHAT` ).
- **Also supported:** repo **Variables** with the same names.

Path in GitHub UI:
- **Settings → Secrets and variables → Actions**.

Then run via:
- Scheduled cron ( two UTC cron expressions covering both DST UTC hours ), or
- **Actions → TQQQ Covered Call Reminder → Run workflow**.

**Temporary 10pm test without touching `main`:**
1. Create a branch ( e.g. `test-10pm` ).
2. Open **Actions → TQQQ Covered Call Reminder → Run workflow**.
3. Choose branch `test-10pm` in the **Use workflow from** selector.
4. Click **Run workflow** at 10:00pm.

> Note: GitHub `schedule` uses the workflow file from the default branch only, so branch-only scheduled cron is not supported.

GitHub Actions cron is UTC-only ( no America/New_York timezone setting ), so the workflow uses two cron expressions ( one per UTC hour ) plus an ET-time guard; it executes only when local ET time is within **08:30–08:59 America/New_York** ( to tolerate delayed runner starts ).

If you do **not** see `TQQQ Covered Call Reminder` in Actions:
1. Open a PR that includes `.github/workflows/daily-reminder.yml`.
2. Merge that PR into your default branch ( `master` / `main` ).
3. Ensure Actions are enabled for the repo / org.
4. Refresh Actions page.

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

The script auto-updates this file daily. Delete or reset to `{}` to clear state.

---

## Files

```text
tqqq-covered-call/
├── send_reminder.py          ← Main script.
├── state.json                ← Auto-managed pause state.
├── README.md                 ← This file.
└── skill/
    ├── SKILL.md              ← Strategy skill.
    └── references/
        └── 9sig-rules.md     ← Full Phoenix 9Sig™ strategy rules.
```
