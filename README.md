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
- **Pre-market gap protection** ( pauses new entries if gap-up exceeds threshold ).
- **9Sig status** — ATH DD status and % of 315d high ( display-only ).
- **Pause day counter** — current streak + all-time total.

---

## Data Source Audit

All core decision logic uses **confirmed daily closes** from Yahoo Finance D1 bars. No intraday prices are used for ADX, ATH DD, or strike calculation. The only live data point is the pre-market gap check, which is intentionally live.

| Data Point | Source | Uses Yesterday Close? |
|---|---|---|
| **TQQQ price** ( for strike calc ) | Yahoo Finance D1 chart | ✅ Yes |
| **ATH DD** ( 315d high check ) | Yahoo Finance D1 chart | ✅ Yes |
| **ADX ( 14 )** | Yahoo Finance D1 chart | ✅ Yes |
| **VIX** | Yahoo Finance quote | ✅ Yes ( `regularMarketPrice` = prev close pre-market ) |
| **Pre-market gap** | Yahoo Finance quote | ✅ Intentionally live |

---

## Strategy Rules ( Quick Reference )

| Parameter | Value |
|---|---|
| Strike | Default: +$3 OTM ( current price + $3 ); if VIX 18–22: +$3.5 OTM |
| DTE | Default: closest weekly expiry to 7 DTE |
| DTE exception | If VIX < 16 **and** 7 DTE +$3 OTM mid premium < $0.20, use closest expiry to 14 DTE |
| Cycle | Weekly |
| Roll | Once at open if ITM → new strike per VIX rule, same selected expiry |
| Max rolls/cycle | 3 — then let it ride |
| Close | DTE 0 at open |

**Proceed when:** VIX 15–22 · ADX < 25 and not rising sharply.

**Pause when:** ADX > 25, or ADX rises by >3 day-over-day · VIX < 15 or > 22 · TQQQ pre-market gap-up > 4% · FOMC/CPI/NFP day · earnings at open today or tomorrow.

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Test run

```bash
python send_reminder.py

# Dry-run ( prints message, no send )
DRY_RUN=1 python send_reminder.py
```

### 5. Schedule

#### ⚠️ GitHub Actions Scheduler Warning

The GitHub Actions `schedule` trigger is **not reliable** for time-sensitive tasks. It is [officially documented as best-effort](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule) and can be delayed by 5–60+ minutes, or sometimes not fire at all, especially on repos with low activity. For a daily trading reminder, this is a significant risk.

To mitigate this, the workflow's ET-time guard has been widened to **08:30–10:00 ET** (a 90-minute window) to tolerate most delays. However, for guaranteed execution, a more reliable scheduler is recommended.

#### Recommended Schedulers

| Option | Reliability | Setup |
|---|---|---|
| **Manus Scheduler** | ✅ High | `manus schedule` CLI | 
| **Render.com Cron Job** | ✅ High | Free tier available | 
| **Railway Cron** | ✅ High | Free tier available |
| **GitHub Actions `schedule`** | ⚠️ Low ( best-effort ) | Included in repo |

To use an external scheduler, trigger the workflow via `workflow_dispatch`:

```bash
# Example: trigger via gh CLI
gh workflow run daily-reminder.yml --repo <owner>/<repo>
```

#### GitHub Actions Setup ( if used )

1. Add `TELEGRAM_TOKEN` and `TELEGRAM_CHAT` as repo **Secrets** under **Settings → Secrets and variables → Actions**.
2. The workflow will now run on its schedule or can be triggered manually via **Actions → TQQQ Covered Call Reminder → Run workflow**.

### 6. State persistence — BOT_STATE_TOKEN ( required )

Bot state ( pause counters, ATH DD tracking ) is saved across runs via a GitHub Actions Variable called `BOT_STATE_JSON`. The default `GITHUB_TOKEN` does **not** have write access to repo Variables, so you need a fine-grained PAT:

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. Set **Resource owner** to your account, **Repository access** to this repo only.
4. Under **Permissions → Repository permissions**, set **Variables** to **Read and write**.
5. Generate and copy the token.
6. Add it as a repo Secret: **Settings → Secrets and variables → Actions → New repository secret**, name it `BOT_STATE_TOKEN`.

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
```
