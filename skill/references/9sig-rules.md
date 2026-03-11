# Phoenix 9Sig™ Strategy Rules

## 1. Initial Allocation ( only initially, this is not maintained )

| | |
|---|---|
| Start | 90% TQQQ / 10% SGOV |

---

## 2. Quarterly Rebalance ( Jan / Apr / Jul / Oct )

| Rule | Detail |
|---|---|
| **Target** | 9% Target = Last quarter TQQQ balance × 1.09 ( updated quarterly ) |
| **If Above** | Sell excess down to 9% target → Move excess to SGOV sleeve |
| **If Below** | Draw funds from SGOV to 9% target |
| **ATH DD** | If TQQQ closing price < 70% of the highest closing price over the last 315 trading days ( ~5 quarters ) → Skip TQQQ SELLS for 126 trading days ( ~2 quarters ) |
| **ATH DD refresh** | The 126-day skip window refreshes daily if condition persists |
| **Floor** | If TQQQ < 60% of portfolio, reset to 60/40 TQQQ/SGOV allocation ( enforced only at quarterly rebalance ) |

---

## 3. Margin Overlay — LEAP Sleeve on MARGIN% × ( TQQQ + SGOV )

| Rule | Detail |
|---|---|
| **Allocation** | MARGIN% NAV sized off shares NAV only ( TQQQ + SGOV ) |
| **Formula** | MARGIN% × ( TQQQ + SGOV ) |
| **Entry** | Buy 500–700 DTE, 80 Delta LEAP |
| **Delta Exit** | Δ ≥ 0.95 |
| **Margin Call** | If Margin Call, TQQQ will be seized first → Top up TQQQ with SGOV on 50/50 damage basis |
| **Close / Roll** | Settle any profits 50/50 into TQQQ & SGOV before rolling |
| **Post Profit** | Re-calculate TQQQ 9% target on current TQQQ value after profit split |

---

## ATH DD Rule — Covered Call Overlay Integration

When the ATH DD condition is active:
- **Do not sell covered calls on TQQQ.** Hold shares fully uncapped to capture the recovery.
- The covered call reminder script auto-detects this condition daily using yesterday's confirmed D1 close vs the 315-day high.
- Resume covered calls only when TQQQ prev close recovers above 70% of the 315-day high.

**Why:** A +$3 covered call premium ( ~$150–$250/contract ) is negligible compared to the potential 50–100% recovery bounce TQQQ can make from a deep drawdown. Capping the recovery is the worst possible time to sell calls.
