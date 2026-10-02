"""
Limitless Exchange Web3 Automation Engine via Playwright CDP
Controls the browser session with zero private key handling on disk (Privy / Smart Account session).
"""
import asyncio
import re
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page, Browser

class LimitlessClient:
    def __init__(self, page: Page, market_url: str):
        self.page = page
        self.market_url = market_url

    async def sync_portfolio(self) -> Dict[str, Any]:
        """
        Navigates or triggers the Portfolio view to extract:
        - Real Available & Total Balance
        - Live Positions count & details
        - Auto-claims any settled winning positions
        """
        # Trigger Portfolio SPA view
        await self.page.evaluate("""() => {
            const p = Array.from(document.querySelectorAll("a, button, div, p, span"))
                          .find(e => e.innerText && e.innerText.trim() === "Portfolio");
            if (p) p.click();
        }""")
        await self.page.wait_for_timeout(3000)

        # 1. Check for Claimable winnings and click Claim
        claimed = False
        claim_res = await self.page.evaluate("""() => {
            const btn = Array.from(document.querySelectorAll("button"))
                             .find(b => b.innerText && b.innerText.trim() === "Claim" && b.offsetWidth > 0);
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }""")

        if claim_res:
            claimed = True
            await self.page.wait_for_timeout(3500)
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)
            # Re-sync portfolio view
            await self.page.evaluate("""() => {
                const p = Array.from(document.querySelectorAll("a, button, div, p, span"))
                              .find(e => e.innerText && e.innerText.trim() === "Portfolio");
                if (p) p.click();
            }""")
            await self.page.wait_for_timeout(2000)

        # 2. Extract Available Cash
        balance_txt = await self.page.evaluate("""() => {
            const divs = Array.from(document.querySelectorAll("div, section, p"));
            for (let el of divs) {
                if (el.innerText && el.innerText.startsWith("Total Balance$")) {
                    const m = el.innerText.match(/Total Balance\\$([0-9.]+)/);
                    if (m) return "$" + m[1];
                }
            }
            const header = document.querySelector("header") || document.body;
            const mNav = header.innerText.match(/\\$([0-9]+\\.[0-9]{2})/);
            if (mNav) return "$" + mNav[1];
            return "$0.00";
        }""")

        # 3. Check Live Positions Count
        pos_count = await self.page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button"));
            const posBtn = btns.find(b => b.innerText && b.innerText.trim().startsWith("Positions"));
            if (!posBtn) return 0;
            const txt = posBtn.innerText.replace(/\\s+/g, " ").trim();
            const m = txt.match(/Positions\\s+(\\d+)/);
            return m ? parseInt(m[1]) : 0;
        }""")

        # 4. Extract active position side if holding
        active_pos_side = None
        if pos_count > 0:
            active_pos_side = await self.page.evaluate("""() => {
                const row = Array.from(document.querySelectorAll("tr, [role=\\"row\\"]"))
                                 .find(r => r.innerText && r.innerText.includes("ETH Up or Down"));
                if (row) {
                    const text = row.innerText.replace(/\\s+/g, " ").trim();
                    if (text.includes("Up")) return "BUY UP";
                    if (text.includes("Down")) return "BUY DOWN";
                    return text.slice(0, 30);
                }
                return null;
            }""")

        return {
            "balance": balance_txt,
            "positions_count": pos_count,
            "active_pos_side": active_pos_side,
            "claimed_new_winnings": claimed
        }

    async def get_market_metrics(self) -> Dict[str, Any]:
        """
        Navigates to the 15-minute ETH market and extracts:
        - Target Price to beat
        - Live odds (Up cents / Down cents)
        - Current time window
        """
        await self.page.goto(self.market_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        info = await self.page.evaluate("""() => {
            const pTarget = Array.from(document.querySelectorAll("p"))
                                 .find(p => p.previousElementSibling && 
                                            p.previousElementSibling.innerText && 
                                            p.previousElementSibling.innerText.includes("Target"));
            const pCurrent = Array.from(document.querySelectorAll("p"))
                                  .find(p => p.previousElementSibling && 
                                             p.previousElementSibling.innerText && 
                                             p.previousElementSibling.innerText.includes("Current"));
            
            const btns = Array.from(document.querySelectorAll("button"))
                              .filter(b => b.offsetWidth > 0 && b.offsetHeight > 0);
            const upBtn = btns.find(b => b.innerText && b.innerText.includes("Up") && b.innerText.includes("¢"));
            const downBtn = btns.find(b => b.innerText && b.innerText.includes("Down") && b.innerText.includes("¢"));
            
            return {
                targetText: pTarget ? pTarget.innerText.trim() : null,
                currentText: pCurrent ? pCurrent.innerText.replace(/\\n/g, " ").trim() : null,
                upOdds: upBtn ? upBtn.innerText.replace(/\\s+/g, " ").trim() : null,
                downOdds: downBtn ? downBtn.innerText.replace(/\\s+/g, " ").trim() : null
            };
        }""")

        target_price = None
        if info.get("targetText"):
            m = re.search(r'\$([0-9,]+\.[0-9]+)', info["targetText"])
            if m:
                target_price = float(m.group(1).replace(',', ''))

        return {
            "target_price": target_price,
            "target_raw": info.get("targetText"),
            "up_odds": info.get("upOdds"),
            "down_odds": info.get("downOdds")
        }

    async def execute_trade(self, decision: str = "UP") -> Tuple[bool, str]:
        """
        Executes binary prediction order with 3-phase verification:
        1. Select side (Up/Down) with live cents odds
        2. Click 'Set to $1' preset
        3. Click 'Buy Up' / 'Buy Down' execution button
        """
        # 1. Select side
        side_clicked = await self.page.evaluate("""(side) => {
            const btns = Array.from(document.querySelectorAll("button"))
                              .filter(b => b.offsetWidth > 0 && b.offsetHeight > 0);
            const targetBtn = btns.find(b => b.innerText && 
                                             b.innerText.includes(side === 'UP' ? 'Up' : 'Down') && 
                                             b.innerText.includes('¢'));
            if (targetBtn) {
                targetBtn.click();
                return targetBtn.innerText.replace(/\\s+/g, " ").trim();
            }
            return null;
        }""", decision)

        if not side_clicked:
            return False, f"Could not find or select {decision} outcome odds."

        await self.page.wait_for_timeout(1000)

        # 2. Click 'Set to $1'
        set1_clicked = await self.page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button")).filter(b => b.offsetWidth > 0);
            const s = btns.find(b => b.innerText && b.innerText.includes("Set to $1"));
            if (s) {
                s.click();
                return true;
            }
            return false;
        }""")

        if not set1_clicked:
            return False, "Could not find 'Set to $1' amount button."

        await self.page.wait_for_timeout(1200)

        # 3. Click Submit 'Buy Up' / 'Buy Down'
        submit_clicked = await self.page.evaluate("""(side) => {
            const btns = Array.from(document.querySelectorAll("button")).filter(b => b.offsetWidth > 0);
            const expected = side === 'UP' ? 'Buy Up' : 'Buy Down';
            const b = btns.find(btn => btn.innerText && btn.innerText.trim().startsWith(expected));
            if (b) {
                b.click();
                return b.innerText.trim();
            }
            return null;
        }""", decision)

        if not submit_clicked:
            return False, f"Submit order button for {decision} did not trigger."

        # Wait for on-chain sponsorship & close share popup
        await self.page.wait_for_timeout(5000)
        try:
            await self.page.mouse.click(50, 50)
        except Exception:
            pass

        return True, f"Successfully executed {submit_clicked} ({side_clicked})"

    async def withdraw_all_usdc(self, recipient_address: str) -> Tuple[bool, str]:
        """
        Withdraws full available USDC balance to an on-chain Base recipient address.
        """
        # Open dropdown via header balance
        await self.page.evaluate("""() => {
            const header = document.querySelector("header") || document.body;
            const el = Array.from(header.querySelectorAll("button, div, a"))
                            .find(e => e.innerText && e.innerText.includes("$"));
            if (el) el.click();
        }""")
        await self.page.wait_for_timeout(1000)

        # Click Withdraw
        await self.page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll("button, [role=\\"menuitem\\"], a, div"));
            const wd = btns.find(b => b.innerText && b.innerText.trim() === "Withdraw");
            if (wd) wd.click();
        }""")
        await self.page.wait_for_timeout(2000)

        # Fill lowercase recipient address
        addr_inp = self.page.locator("input[placeholder*=\"0x000\"]").first
        await addr_inp.click()
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")
        await addr_inp.fill(recipient_address.lower())
        await self.page.wait_for_timeout(500)

        # Click Max amount button
        max_btn = self.page.locator("button:has-text(\"Max\")").first
        await max_btn.click()
        await self.page.wait_for_timeout(1000)

        # Confirm Withdraw button
        wd_btn = self.page.locator("button.chakra-button").filter(has_text="Withdraw").last
        if await wd_btn.is_disabled():
            return False, "Withdraw button is disabled (check balance or address validity)."

        await wd_btn.click()
        await self.page.wait_for_timeout(5000)
        return True, f"Withdrawal submitted to {recipient_address}"
