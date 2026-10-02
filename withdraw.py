#!/usr/bin/env python3
"""
Withdrawal CLI Utility
Instantly transfers remaining USDC balance from Limitless Exchange to your Base EVM wallet.
"""
import asyncio
import sys
from playwright.async_api import async_playwright
from config import settings
from limitless_client import LimitlessClient

async def main():
    recipient = settings.WALLET_RECEIVER
    if len(sys.argv) > 1:
        recipient = sys.argv[1].strip()

    if not recipient or not recipient.startswith("0x") or len(recipient) != 42:
        print("Usage: python3 withdraw.py <0xRecipientEVMAddress>")
        sys.exit(1)

    print(f"🚀 Initiating full withdrawal to: {recipient} on Base network...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(settings.CDP_URL)
        except Exception as e:
            print(f"Error connecting to CDP: {e}")
            return

        pages = [pg for pg in browser.contexts[0].pages if "limitless.exchange" in pg.url and not pg.url.startswith("blob:")]
        if not pages:
            print("No Limitless tab open.")
            return

        client = LimitlessClient(pages[0], settings.MARKET_URL)
        success, msg = await client.withdraw_all_usdc(recipient)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ Failed: {msg}")

if __name__ == "__main__":
    asyncio.run(main())
