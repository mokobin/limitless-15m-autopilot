"""
Feed data provider for real-time crypto price and momentum (Binance Spot API)
"""
import json
import urllib.request
from typing import Tuple, Optional

def get_binance_metrics(symbol: str = "ETHUSDT") -> Tuple[Optional[float], float, float]:
    """
    Fetches real-time price, RSI(14), and 5-min momentum from Binance spot.
    Returns: (current_price, rsi, momentum)
    """
    try:
        url_ticker = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        req = urllib.request.Request(url_ticker, headers={"User-Agent": "Mozilla/5.0"})
        price = float(json.loads(urllib.request.urlopen(req, timeout=10).read())["price"])
        
        url_klines = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=15"
        req_k = urllib.request.Request(url_klines, headers={"User-Agent": "Mozilla/5.0"})
        klines = json.loads(urllib.request.urlopen(req_k, timeout=10).read())
        closes = [float(x[4]) for x in klines]
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_g = sum(gains) / len(deltas) if gains else 0
        avg_l = sum(losses) / len(deltas) if losses else 1e-9
        rs = avg_g / avg_l
        rsi = 100 - (100 / (1 + rs))
        
        momentum = closes[-1] - closes[-5]
        return price, rsi, momentum
    except Exception as e:
        return None, 50.0, 0.0
