#!/usr/bin/env python3
"""
TQQQ Covered Call Daily Pre-Market Reminder
Sends a Telegram message before US market open with all automated checks.

Data sources:
  - TQQQ / VIX             : Yahoo Finance (D1 daily chart closes)
  - ADX(14) / ATH DD       : Yahoo Finance (computed from 2y daily data)
  - FOMC / CPI / NFP       : ForexFactory JSON calendar
  - Big Tech Earnings      : Nasdaq Earnings API

Configuration:
  Copy .env.example to .env and fill in your Telegram credentials.
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from dotenv import load_dotenv

# ── Load config from .env ──────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
    print("ERROR: TELEGRAM_TOKEN and TELEGRAM_CHAT must be set in .env", file=sys.stderr)
    sys.exit(1)

# ── Constants ──────────────────────────────────────────────────────────────────
ET         = pytz.timezone("America/New_York")
SGT        = pytz.timezone("Asia/Singapore")
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
STATE_FILE = Path(__file__).parent / "state.json"

# ForexFactory high-impact USD event keywords
FOMC_KEYWORDS  = ["fomc", "federal reserve", "fed rate", "interest rate decision",
                  "monetary policy", "powell", "fed chair"]
MACRO_KEYWORDS = ["cpi", "core cpi", "pce", "core pce", "nfp", "non-farm",
                  "unemployment rate", "gdp", "retail sales"]

# Top Nasdaq-100 constituents that meaningfully move TQQQ
BIG_TECH = {
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
    "GOOGL": "Alphabet",
    "GOOG":  "Alphabet",
    "META":  "Meta",
    "AMZN":  "Amazon",
    "TSLA":  "Tesla",
    "AMD":   "AMD",
    "NFLX":  "Netflix",
    "QCOM":  "Qualcomm",
    "AVGO":  "Broadcom",
}


# ── State Management ───────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load pause state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "paused":           False,
        "reason":           None,
        "since":            None,
        "days_paused":      0,
        "resume_cond":      None,
        "total_days_paused": 0,
        "last_run_date":    None,
    }


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def update_state(action: str, pause_until: str | None, tqqq: dict, vix: float | None) -> tuple[dict, str]:
    """
    Update pause state based on today's action.
    Returns ( state, status_change_msg ).
    status_change_msg is non-empty only on state transitions ( paused ↔ resumed ).
    Same-day guard: if already ran today, skip counter increments to prevent double-counting.
    """
    state      = load_state()
    today_str  = str(datetime.now(ET).date())
    change_msg = ""
    already_ran_today = state.get("last_run_date") == today_str

    is_pause  = any(x in action for x in ["⏸️ PAUSE", "⏸️ SKIP", "🛑 CLOSE", "🛑 SKIP", "🏖️ MARKET", "⚠️ CAUTION"])
    is_proceed = "✅ PROCEED" in action

    if is_pause:
        if not state["paused"]:
            state.update({
                "paused":      True,
                "reason":      action,
                "since":       today_str,
                "days_paused": 1,
                "resume_cond": pause_until or "Check conditions manually.",
            })
            if not already_ran_today:
                state["total_days_paused"] = state.get("total_days_paused", 0) + 1
            change_msg = f"⏸️ PAUSE STARTED today. Reason: {action}"
        else:
            if not already_ran_today:
                state["days_paused"]       = state.get("days_paused", 1) + 1
                state["total_days_paused"] = state.get("total_days_paused", 0) + 1
            state["reason"]            = action
            state["resume_cond"]       = pause_until or state.get("resume_cond", "")

    elif is_proceed and state["paused"]:
        days = state.get("days_paused", 0)
        change_msg = (
            f"✅ RESUMING today after {days} day(s) paused. "
            f"( {state.get('reason', '')} ) — conditions now clear."
        )
        state.update({
            "paused":      False,
            "reason":      None,
            "since":       None,
            "days_paused": 0,
            "resume_cond": None,
        })

    state["last_run_date"] = today_str
    save_state(state)
    return state, change_msg


# ── Data Fetchers ──────────────────────────────────────────────────────────────

def get_tqqq_data() -> dict:
    """
    Fetch TQQQ daily closes from Yahoo Finance D1 chart.
    Returns prev close, 10-day return. No intraday / meta prices used.
    """
    try:
        url    = "https://query1.finance.yahoo.com/v8/finance/chart/TQQQ?interval=1d&range=20d"
        r      = requests.get(url, headers=HEADERS, timeout=10)
        closes = [c for c in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
        price      = closes[-1]
        prev       = closes[-2] if len(closes) >= 2 else None
        change_pct = ((price - prev) / prev * 100) if prev else 0
        ten_day    = ((closes[-1] - closes[-11]) / closes[-11] * 100) if len(closes) >= 11 else None
        return {
            "price":          round(price, 2),
            "change_pct":     round(change_pct, 2),
            "ten_day_return": round(ten_day, 1) if ten_day is not None else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_vix() -> float | None:
    """Fetch latest VIX level from Yahoo Finance."""
    try:
        url  = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=2d"
        r    = requests.get(url, headers=HEADERS, timeout=10)
        meta = r.json()["chart"]["result"][0]["meta"]
        return round(meta.get("regularMarketPrice"), 2)
    except Exception:
        return None


def get_adx_and_ath_dd() -> dict:
    """
    Fetch 2 years of TQQQ daily OHLC and compute:
      - ADX ( 14 )  : trend strength. >25 = trending, <20 = range-bound.
      - ATH DD      : True if yesterday's confirmed daily close < 70% of the
                      highest confirmed daily close over the last 315 trading days.
                      ( Phoenix 9Sig rule — uses D1 closes only, never intraday. )
    """
    try:
        url  = "https://query1.finance.yahoo.com/v8/finance/chart/TQQQ?interval=1d&range=2y"
        r    = requests.get(url, headers=HEADERS, timeout=15)
        q    = r.json()["chart"]["result"][0]["indicators"]["quote"][0]
        highs  = [h for h in q["high"]  if h]
        lows   = [l for l in q["low"]   if l]
        closes = [c for c in q["close"] if c]

        # Use yesterday's confirmed daily close ( script runs before US market open )
        prev_close = closes[-1]
        closes_315 = closes[-315:] if len(closes) >= 315 else closes
        ath_high   = max(closes_315)
        pct_of_ath = round((prev_close / ath_high) * 100, 1)
        ath_dd     = pct_of_ath < 70.0

        # ADX ( 14 ) — Wilder smoothing with SMA seed
        n = 14
        if len(closes) < n * 2:
            return {
                "adx":                None,
                "ath_high_315":       round(ath_high, 2),
                "ath_dd_triggered":   ath_dd,
                "current_pct_of_ath": pct_of_ath,
                "prev_close":         round(prev_close, 2),
            }

        tr_list, pdm_list, ndm_list = [], [], []
        for i in range(1, len(closes)):
            h, l, pc  = highs[i], lows[i], closes[i - 1]
            ph, pl    = highs[i - 1], lows[i - 1]
            tr        = max(h - l, abs(h - pc), abs(l - pc))
            up_move   = h - ph
            down_move = pl - l
            tr_list.append(tr)
            pdm_list.append(up_move   if (up_move > down_move and up_move > 0)   else 0)
            ndm_list.append(down_move if (down_move > up_move and down_move > 0) else 0)

        def wilder_smooth(data: list, period: int) -> list:
            """Wilder smoothing seeded with SMA of first `period` values."""
            if len(data) < period:
                return []
            seed = sum(data[:period]) / period * period  # ATR seed = sum, not avg
            out  = [seed]
            for v in data[period:]:
                out.append(out[-1] - out[-1] / period + v)
            return out

        atr_s = wilder_smooth(tr_list,  n)
        pdm_s = wilder_smooth(pdm_list, n)
        ndm_s = wilder_smooth(ndm_list, n)

        dx_list = []
        for i in range(min(len(atr_s), len(pdm_s), len(ndm_s))):
            pdi = (pdm_s[i] / atr_s[i] * 100) if atr_s[i] else 0
            ndi = (ndm_s[i] / atr_s[i] * 100) if atr_s[i] else 0
            dx  = (abs(pdi - ndi) / (pdi + ndi) * 100) if (pdi + ndi) else 0
            dx_list.append(dx)

        adx = None
        if len(dx_list) >= n:
            adx_val = sum(dx_list[:n]) / n
            for dx in dx_list[n:]:
                adx_val = (adx_val * (n - 1) + dx) / n
            adx = round(adx_val, 1)

        return {
            "adx":                adx,
            "ath_high_315":       round(ath_high, 2),
            "ath_dd_triggered":   ath_dd,
            "current_pct_of_ath": pct_of_ath,
            "prev_close":         round(prev_close, 2),
        }
    except Exception as e:
        return {"error": str(e)}


def get_forexfactory_events() -> tuple[list, list, list]:
    """
    Fetch ForexFactory this-week JSON calendar.
    Returns ( fomc_events, macro_events, usd_holidays ).
      - fomc_events  : FOMC / Fed events today or tomorrow
      - macro_events : CPI / PCE / NFP events today
      - usd_holidays : USD market holidays today
    """
    today_et    = datetime.now(ET).date()
    tomorrow_et = today_et + timedelta(days=1)
    fomc, macro, holidays = [], [], []

    try:
        url    = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        events = requests.get(url, headers=HEADERS, timeout=10).json()

        for e in events:
            try:
                ev_dt    = datetime.fromisoformat(e["date"]).astimezone(ET)
                ev_date  = ev_dt.date()
                ev_time  = ev_dt.strftime("%H:%M ET")
                title    = e.get("title", "").lower()
                country  = e.get("country", "")
                impact   = e.get("impact", "")

                if country != "USD":
                    continue

                if impact == "Holiday" and ev_date == today_et:
                    holidays.append({"title": e["title"], "date": str(ev_date)})

                if impact == "High" and ev_date in (today_et, tomorrow_et):
                    if any(kw in title for kw in FOMC_KEYWORDS):
                        fomc.append({
                            "title": e["title"],
                            "date":  str(ev_date),
                            "time":  ev_time,
                            "when":  "TODAY" if ev_date == today_et else "TOMORROW",
                        })

                if impact == "High" and ev_date == today_et:
                    if any(kw in title for kw in MACRO_KEYWORDS):
                        macro.append({"title": e["title"], "time": ev_time})

            except Exception:
                continue

    except Exception as e:
        return [], [], []

    return fomc, macro, holidays


def get_big_tech_earnings() -> tuple[list, list]:
    """
    Check Nasdaq earnings calendar for Nasdaq-100 heavyweights.
    Returns ( today_earnings, tmrw_earnings ) — before-open events only.
      - today_earnings : before open TODAY ( gap risk at open )
      - tmrw_earnings  : before open TOMORROW ( pre-event close warning )
    """
    today_et    = datetime.now(ET).date()
    tomorrow_et = today_et + timedelta(days=1)
    today_res, tmrw_res = [], []

    hdrs = {
        "User-Agent": "Mozilla/5.0",
        "Accept":     "application/json, text/plain, */*",
        "Origin":     "https://www.nasdaq.com",
        "Referer":    "https://www.nasdaq.com/",
    }

    for check_date, result_list in [(today_et, today_res), (tomorrow_et, tmrw_res)]:
        try:
            url  = f"https://api.nasdaq.com/api/calendar/earnings?date={check_date}"
            rows = requests.get(url, headers=hdrs, timeout=10).json().get("data", {}).get("rows") or []
            for row in rows:
                sym = row.get("symbol", "")
                if sym in BIG_TECH and "before" in row.get("time", "").lower():
                    result_list.append({"symbol": sym, "name": BIG_TECH[sym]})
        except Exception:
            pass

    return today_res, tmrw_res


# ── Decision Logic ─────────────────────────────────────────────────────────────

def evaluate_status(
    tqqq: dict,
    vix: float | None,
    fomc_events: list,
    macro_events: list,
    usd_holidays: list,
    earnings: list,
    tmrw_earnings: list,
    adx_data: dict,
) -> tuple[str, list, str | None]:
    """
    Evaluate all checks and return ( action, flags, pause_until ).
    Priority: ATH DD > VIX extreme > macro events > earnings > VIX elevated > ADX.
    """
    flags       = []
    action      = "✅ PROCEED"
    pause_until = None

    # Market holiday — hard stop, no further checks needed
    if usd_holidays:
        for h in usd_holidays:
            flags.append(f"🏖️ US MARKET HOLIDAY: {h['title']}")
        return "🏖️ MARKET HOLIDAY — NO ACTION", flags, "Resume next trading day."

    # FOMC today / tomorrow
    fomc_today = [e for e in fomc_events if e["when"] == "TODAY"]
    fomc_tmrw  = [e for e in fomc_events if e["when"] == "TOMORROW"]
    if fomc_today:
        for e in fomc_today:
            flags.append(f"🔴 FOMC/FED TODAY at {e['time']}: {e['title']}")
        action      = "⏸️ SKIP — FOMC TODAY"
        pause_until = "Resume tomorrow if no follow-on Fed events."
    elif fomc_tmrw:
        for e in fomc_tmrw:
            flags.append(f"🟡 FOMC TOMORROW at {e['time']}: {e['title']} → If call within $2 of strike, close at open today.")
        if action == "✅ PROCEED":
            action      = "⚠️ CAUTION — FOMC TOMORROW"
            pause_until = "Skip today too if you want to avoid pre-FOMC vol."

    # Macro data today ( CPI / PCE / NFP )
    if macro_events:
        for e in macro_events:
            flags.append(f"🔴 {e['title']} at {e['time']}")
        action      = "⏸️ SKIP — MACRO DATA TODAY"
        pause_until = "Resume tomorrow once data reaction settles."

    # Big tech earnings before open today
    if earnings:
        syms = ", ".join(e["symbol"] for e in earnings)
        flags.append(f"🔴 EARNINGS BEFORE OPEN: {syms}")
        if action == "✅ PROCEED":
            action      = "⏸️ SKIP — EARNINGS AT OPEN"
            pause_until = "Resume tomorrow after gap settles."

    # Big tech earnings before open tomorrow — pre-event close warning
    if tmrw_earnings:
        syms = ", ".join(e["symbol"] for e in tmrw_earnings)
        flags.append(f"🟡 EARNINGS TOMORROW PRE-OPEN: {syms} → If call within $2 of strike, close at open today.")

    # VIX checks
    if vix is not None:
        if vix >= 40:
            flags.append(f"🔴 VIX = {vix} ( ≥40 ) — extreme vol")
            action      = "🛑 CLOSE & SIT OUT"
            pause_until = "Resume when VIX drops below 25 for 2 consecutive days."
        elif vix > 25:
            flags.append(f"🔴 VIX = {vix} ( >25 ) — above sweet spot")
            if action == "✅ PROCEED":
                action      = "⏸️ PAUSE — HIGH VIX"
                pause_until = "Resume when VIX drops back into 15–25 range."
        elif vix < 15:
            flags.append(f"🟡 VIX = {vix} ( <15 ) — too calm, premium too thin")
            if action == "✅ PROCEED":
                action      = "⏸️ SKIP — LOW VIX"
                pause_until = "Resume when VIX rises back above 15."

    # ATH DD check ( Phoenix 9Sig rule )
    if adx_data and "error" not in adx_data:
        if adx_data.get("ath_dd_triggered"):
            pct = adx_data.get("current_pct_of_ath", 0)
            ath = adx_data.get("ath_high_315", 0)
            flags.append(f"🔴 ATH DD TRIGGERED: TQQQ at {pct}% of 315d high ( ${ath} ) — deep drawdown")
            action      = "🛑 SKIP — ATH DD WINDOW"
            pause_until = "Resume when TQQQ closes above 70% of its 315d high. Skip window refreshes daily."
        elif adx_data.get("current_pct_of_ath") is not None:
            pct = adx_data["current_pct_of_ath"]
            if pct < 80:
                flags.append(f"🟡 TQQQ at {pct}% of 315d high ( approaching ATH DD zone at 70% )")

    # ADX trend strength check
    if adx_data and "error" not in adx_data and adx_data.get("adx") is not None:
        adx = adx_data["adx"]
        if adx > 25:
            flags.append(f"🔴 ADX = {adx} ( >25 ) — trending market, covered calls risky")
            if action == "✅ PROCEED":
                action      = "⏸️ PAUSE — TRENDING ( ADX )"
                pause_until = "Resume when ADX drops below 20 ( range-bound market )."
        elif adx > 20:
            flags.append(f"🟡 ADX = {adx} ( 20–25 ) — watch, approaching trend zone")

    # TQQQ 10-day return — secondary early-warning signal
    if "error" not in tqqq and tqqq.get("ten_day_return") is not None:
        r10 = tqqq["ten_day_return"]
        if r10 >= 15:
            flags.append(f"🟡 TQQQ 10-day return = +{r10}% ( strong run, watch ADX )")

    if not flags:
        flags.append("All checks clear. ✅")

    return action, flags, pause_until


# ── Message Builder ────────────────────────────────────────────────────────────

def build_message(
    tqqq: dict,
    vix: float | None,
    fomc_events: list,
    macro_events: list,
    usd_holidays: list,
    earnings: list,
    action: str,
    flags: list,
    pause_until: str | None = None,
    state: dict | None = None,
    status_change_msg: str = "",
    adx_data: dict | None = None,
) -> tuple[str, str]:
    """Build the Telegram message subject and body."""
    date_str = datetime.now(SGT).strftime("%a, %d %b %Y")
    subject  = f"[TQQQ CC] {date_str} | {action}"

    # Strike calculation
    if "error" not in tqqq and tqqq.get("price"):
        price = tqqq["price"]
        # Widen strike on high-risk days
        if any("EARNINGS" in f and "🔴" in f for f in flags):
            offset, strike_note = 5, "(widened to +$5 — earnings at open)"
        elif vix and vix >= 30:
            offset, strike_note = 5, "(widened to +$5 — high VIX)"
        else:
            offset, strike_note = 3, "(normal +$3)"
        exact_strike = f"${round(price + offset)}"
    else:
        exact_strike = "N/A"
        strike_note  = ""

    # Flags block — suppress the all-clear line
    real_flags = [f for f in flags if "clear" not in f.lower()]
    flags_text = ("\n".join(f"  {f}" for f in real_flags) + "\n") if real_flags else ""
    pause_text = (f"  RESUME: {pause_until}\n") if pause_until else ""
    reasons_block = f"WHY\n{flags_text}{pause_text}\n" if real_flags else ""

    # Pause tracker / status change block
    pause_tracker = ""
    if state and state.get("paused"):
        days  = state.get("days_paused", 1)
        since = state.get("since", "unknown")
        cond  = state.get("resume_cond", "")
        pause_tracker = f"PAUSE TRACKER\n  Paused since: {since} ( {days} day(s) )\n  Resume when: {cond}\n\n"
    elif status_change_msg:
        pause_tracker = f"STATUS CHANGE\n  {status_change_msg}\n\n"

    # Existing position close guidance
    close_guidance = ""
    if "CLOSE" in action or "SIT OUT" in action:
        if "ATH DD" in action:
            close_guidance = "*EXISTING POSITION:*\n  Close your call at open today. ATH DD window active — hold shares uncapped.\n\n"
        elif vix and vix >= 40:
            close_guidance = "*EXISTING POSITION:*\n  Close your call at open today. VIX ≥40 — reversal risk too high.\n\n"
    elif any("TOMORROW" in f for f in real_flags) and tqqq.get("price"):
        lo = round(tqqq["price"] - 2)
        hi = round(tqqq["price"] + 2)
        close_guidance = (
            f"*EXISTING POSITION:*\n"
            f"  Event tomorrow — if your strike is ${lo}–${hi}, close at open today.\n"
            f"  If strike > ${hi}, let it ride.\n\n"
        )

    # 9Sig status block
    if adx_data and "error" not in adx_data:
        pct        = adx_data.get("current_pct_of_ath", "N/A")
        ath_high   = adx_data.get("ath_high_315", "N/A")
        prev_close = adx_data.get("prev_close", "N/A")
        dd_status  = "🔴 IN ATH DD WINDOW" if adx_data.get("ath_dd_triggered") else "🟢 NOT in ATH DD window"
        sig9_block = (
            f"*9SIG STATUS*\n"
            f"  ATH DD: {dd_status}\n"
            f"  TQQQ prev close: ${prev_close}  ( {pct}% of 315d high ${ath_high} )\n"
        )
    else:
        sig9_block = "*9SIG STATUS*\n  ATH DD: data unavailable\n"

    # Pause day counter
    cur_days   = state.get("days_paused", 0) if state and state.get("paused") else 0
    total_days = state.get("total_days_paused", 0) if state else 0
    pause_line = f"  Pause days: {cur_days} current / {total_days} total ( all-time )\n"

    div  = "─" * 35
    body = (
        f"{div}\n"
        f"*TODAY'S CALL:  {action}*\n"
        f"{div}\n"
        f"{reasons_block}"
        f"{close_guidance}"
        f"{pause_tracker}"
        f"*STRIKE TO USE:*  {exact_strike}  ( {strike_note} )\n"
        f"*DTE:* closest expiry to 14d\n"
        f"\n"
        f"*IF ROLLING:*\n"
        f"  ITM → roll to {exact_strike}, same closest-14-DTE expiry\n"
        f"  3+ rolls already → let it ride, no more rolls\n"
        f"  Net roll cost > original premium collected → close the call, don't roll\n"
        f"\n"
        f"{div}\n"
        f"*STRATEGY (ref)*\n"
        f"  Entry      +$3 OTM | closest to 14d DTE | bi-weekly\n"
        f"  Roll       Once at open if ITM → new +$3 OTM, same DTE | max 3 rolls/cycle\n"
        f"  Close      DTE 0 at open\n"
        f"  Proceed    VIX 15–25 | ADX <20 | TQQQ >70% of 315d high\n"
        f"  Pause      ADX >25 | VIX >25 | FOMC/CPI/NFP day | earnings at open\n"
        f"  Close CC   VIX ≥40 | ATH DD triggered\n"
        f"  Pre-event  Close call if within $2 of strike, day before FOMC/earnings\n"
        f"\n"
        f"{sig9_block}"
        f"{pause_line}"
        f"{div}"
    )

    return subject, body


# ── Telegram Delivery ──────────────────────────────────────────────────────────

def send_telegram(subject: str, body: str) -> None:
    """Send Telegram message with Markdown bold formatting. Falls back to plain text on parse error."""
    text = f"*{subject}*\n\n{body}"
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "Markdown"}, timeout=15).json()

    if not resp.get("ok"):
        # Fallback: strip markdown and retry plain
        plain = requests.post(url, json={"chat_id": TELEGRAM_CHAT, "text": text.replace("*", "")}, timeout=15).json()
        if not plain.get("ok"):
            print(f"Telegram error: {plain}", file=sys.stderr)
            sys.exit(1)
        print(f"  Sent OK ( plain fallback, message_id: {plain['result']['message_id']} )")
    else:
        print(f"  Sent OK ( message_id: {resp['result']['message_id']} )")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[{datetime.now(SGT).strftime('%Y-%m-%d %H:%M SGT')}] Running TQQQ pre-market reminder...")

    tqqq                     = get_tqqq_data()
    vix                      = get_vix()
    adx_data                 = get_adx_and_ath_dd()
    fomc, macro, holidays    = get_forexfactory_events()
    earnings, tmrw_earnings  = get_big_tech_earnings()

    action, flags, pause_until = evaluate_status(
        tqqq, vix, fomc, macro, holidays, earnings, tmrw_earnings, adx_data
    )
    state, change_msg = update_state(action, pause_until, tqqq, vix)

    # Debug output
    print(f"  TQQQ      : {tqqq}")
    print(f"  VIX       : {vix}")
    print(f"  ADX/ATH   : {adx_data}")
    print(f"  FOMC      : {fomc}")
    print(f"  Macro     : {macro}")
    print(f"  Holidays  : {holidays}")
    print(f"  Earnings  : today={earnings}  tomorrow={tmrw_earnings}")
    print(f"  Decision  : {action}")
    print(f"  State     : {state}")
    if change_msg:
        print(f"  Change    : {change_msg}")

    subject, body = build_message(
        tqqq, vix, fomc, macro, holidays, earnings,
        action, flags, pause_until, state, change_msg, adx_data
    )

    print(f"  Subject   : {subject}")
    print("  Sending Telegram message...")
    send_telegram(subject, body)
    print("  Done. ✅")
