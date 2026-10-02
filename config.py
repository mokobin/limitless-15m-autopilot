import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    CDP_URL: str = os.getenv("CDP_URL", "http://127.0.0.1:9223")
    MARKET_URL: str = os.getenv("MARKET_URL", "https://limitless.exchange/markets/eth-15min-price")
    PROFILE_URL: str = os.getenv("PROFILE_URL", "https://limitless.exchange/profile")
    WALLET_RECEIVER: str = os.getenv("WALLET_RECEIVER", "")
    
    # Strategy settings
    MIN_CENTS_PRICE: float = float(os.getenv("MIN_CENTS_PRICE", "20.0"))
    MAX_CENTS_PRICE: float = float(os.getenv("MAX_CENTS_PRICE", "70.0"))
    ORDER_AMOUNT_USD: float = float(os.getenv("ORDER_AMOUNT_USD", "1.0"))
    
    # Timing & Sync
    BASE_UTC_HOUR: int = int(os.getenv("BASE_UTC_HOUR", "12"))
    BASE_UTC_MIN: int = int(os.getenv("BASE_UTC_MIN", "0"))
    BASE_ROUND_NUM: int = int(os.getenv("BASE_ROUND_NUM", "11"))

settings = Settings()
