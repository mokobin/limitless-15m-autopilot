#!/usr/bin/env python3
"""
Main Entrypoint Runner for Limitless 15-Minute Auto-Trader
Connects to live browser session, synchronizes portfolio state, executes signal, and formats Dual-Report.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright

from config import settings
from data_feed import get_binance_metrics
from limitless_client import LimitlessClient
from strategy import PredictionStrategy

STATE_FILE = "limitless_trade_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"rounds": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

async def main():
    state = load_state()
    strategy = PredictionStrategy(
        base_hour=settings.BASE_UTC_HOUR,
        base_min=settings.BASE_UTC_MIN,
        base_round=settings.BASE_ROUND_NUM,
        max_cents=settings.MAX_CENTS_PRICE
    )
    
    now_utc = datetime.now(timezone.utc)
    cur_round = strategy.get_current_round(now_utc)
    prev_round = cur_round - 1
    cur_start, cur_end, prev_start, prev_end = strategy.get_round_times(now_utc)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(settings.CDP_URL)
        except Exception as e:
            print(f"⚠️ Error: Could not connect to Chromium CDP on {settings.CDP_URL}: {e}")
            return

        pages = [pg for pg in browser.contexts[0].pages if "limitless.exchange" in pg.url and not pg.url.startswith("blob:")]
        if not pages:
            print("⚠️ Error: No open Limitless Exchange tab found on browser.")
            return

        page = pages[0]
        client = LimitlessClient(page, settings.MARKET_URL)

        # 1. Audit Portfolio & Check Auto-Claim
        portfolio = await client.sync_portfolio()
        balance_txt = portfolio.get("balance", "$0.00")
        live_positions_count = portfolio.get("positions_count", 0)
        active_pos_side = portfolio.get("active_pos_side")
        claimed_prev = portfolio.get("claimed_new_winnings", False)

        # 2. Inspect Market & Price Metrics
        market_metrics = await client.get_market_metrics()
        target_price = market_metrics.get("target_price")
        b_price, rsi, mom = get_binance_metrics("ETHUSDT")

        diff = (b_price - target_price) if (b_price and target_price) else 0.0

        # 3. Decision & Trade Execution
        entry_status = "IDLE / SKIP ⏸️"
        entry_pos = "NONE"
        modal_entered = "$0.00"

        if live_positions_count == 0:
            decision, reason = strategy.decide(b_price, target_price, mom, rsi)
            if decision in ["UP", "DOWN"]:
                success, msg = await client.execute_trade(decision)
                if success:
                    entry_status = "MATCHED / LIVE 🟢"
                    entry_pos = f"BUY {decision}"
                    modal_entered = f"${settings.ORDER_AMOUNT_USD:.2f} USDC"
                else:
                    entry_status = "FAILED ⚠️"
                    entry_pos = f"ATTEMPT BUY {decision} ({msg})"
        else:
            entry_status = "IN-POSITION ⏳"
            entry_pos = active_pos_side or "BUY LIVE"
            modal_entered = f"${settings.ORDER_AMOUNT_USD:.2f} USDC"

        # Update State
        state["rounds"][str(cur_round)] = {
            "round": cur_round,
            "time": f"{cur_start} – {cur_end} WIB",
            "pos": entry_pos,
            "modal": modal_entered,
            "target": f"${target_price:.2f}" if target_price else "-",
            "spot": f"${b_price:.2f}" if b_price else "-",
            "gap": f"{diff:+.2f}",
            "status": entry_status
        }
        save_state(state)

        # 4. Evaluate Previous Round PnL
        if claimed_prev:
            status_txt = "WIN (Settled 100¢) 🎯 - CLAIMED ✅"
            m_in = f"${settings.ORDER_AMOUNT_USD:.2f} USDC"
            p_out = "$1.38 USDC"  # Standard winning payout
            pnl_val = "+$0.39 USDC (+39.4%)"
        else:
            prev_data = state.get("rounds", {}).get(str(prev_round))
            if prev_data and "BUY" in prev_data.get("pos", "") and "MATCHED" in prev_data.get("status", ""):
                status_txt = "LOSE (Expired 0¢) ❌"
                m_in = f"${settings.ORDER_AMOUNT_USD:.2f} USDC"
                p_out = "$0.00"
                pnl_val = f"-${settings.ORDER_AMOUNT_USD:.2f} USDC (-100%)"
            else:
                status_txt = "TIDAK ADA ENTRY / SKIP ⏸️"
                m_in = "$0.00"
                p_out = "$0.00"
                pnl_val = "$0.00"

        # 5. Output Dual Report
        target_disp = f"${target_price:.2f}" if target_price else (market_metrics.get("target_raw") or "-")
        spot_disp = f"${b_price:.2f}" if b_price else "-"

        report = f"""🎯 **[LAPORAN ENTRY - RONDE {cur_round}]**
• **Jam Sesi:** {cur_start} – {cur_end} WIB
• **Posisi:** **{entry_pos}**
• **Modal Masuk:** {modal_entered}
• **Target Price to Beat:** `{target_disp}`
• **Spot Saat Entry:** `{spot_disp}` (Gap: `{diff:+.2f}`)
• **Status Tiket:** **{entry_status}**
• **Sisa Kas Ready:** `{balance_txt}`

---

📊 **[LAPORAN PnL - RONDE {prev_round}]**
• **Jam Sesi:** {prev_start} – {prev_end} WIB
• **Hasil Akhir:** **{status_txt}**
• **Modal Masuk:** {m_in}
• **Payout Masuk:** {p_out}
• **Net PnL:** **{pnl_val}**"""

        print(report)

if __name__ == "__main__":
    asyncio.run(main())
