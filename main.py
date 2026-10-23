#!/usr/bin/env python3
# Master Engine v100.0 — Omnipresent Global Trading Engine for Hadi
# Fully compatible with FxPro pricing ($500 Account / 1% Risk Engine)

import requests
import time
import threading
import statistics
from datetime import datetime

SYMBOL = "BTCUSDT"
BINANCE_BASES = ["https://data-api.binance.vision", "https://api.binance.com"]
TOKEN = "8862704494:AAGfQvIC04YAV2OAuwHWo1KqnxgS80ikraw"
CHAT_ID = "@HadiTradingLive"

CAPITAL_USD = 500.0
RISK_PCT = 1.0
RISK_REWARD = 2.0
COOLDOWN_SECONDS = 300

session = requests.Session()
last_signal_time = 0.0

def local_time():
    return datetime.now().astimezone().strftime("%H:%M:%S")

def send_telegram(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False

def get_klines(interval, limit=100):
    for base in BINANCE_BASES:
        try:
            r = session.get(f"{base}/api/v3/klines", params={"symbol": SYMBOL, "interval": interval, "limit": limit}, timeout=8)
            r.raise_for_status()
            rows = r.json()[:-1]
            return [{
                "open": float(x[1]),
                "high": float(x[2]),
                "low": float(x[3]),
                "close": float(x[4]),
                "volume": float(x[5])
            } for x in rows]
        except Exception:
            continue
    return []

def get_price():
    for base in BINANCE_BASES:
        try:
            r = session.get(f"{base}/api/v3/trades", params={"symbol": SYMBOL, "limit": 1}, timeout=5)
            r.raise_for_status()
            return float(r.json()[-1]["price"])
        except Exception:
            continue
    return None

def ema(values, period):
    if len(values) < period:
        return None
    val = sum(values[:period]) / period
    alpha = 2.0 / (period + 1)
    for v in values[period:]:
        val = alpha * v + (1.0 - alpha) * val
    return val

def rsi(values, period=14):
    if len(values) < period + 1:
        return 50.0
    deltas = [values[i] - values[i-1] for i in range(1, len(values))]
    gains = [max(x, 0.0) for x in deltas[-period:]]
    losses = [max(-x, 0.0) for x in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))

def evaluate_omnipresent_grid():
    global last_signal_time
    price = get_price()
    if not price:
        return

    c1m = get_klines("1m", 50)
    c5m = get_klines("5m", 50)
    c15m = get_klines("15m", 50)
    c1h = get_klines("1h", 100)
    c4h = get_klines("4h", 100)

    if not c1m or not c5m or not c15m or not c1h or not c4h:
        return

    closes_1h = [x["close"] for x in c1h]
    closes_4h = [x["close"] for x in c4h]

    ema9_1h, ema21_1h = ema(closes_1h, 9), ema(closes_1h, 21)
    ema9_4h, ema21_4h = ema(closes_4h, 9), ema(closes_4h, 21)

    rsi_15m = rsi([x["close"] for x in c15m])
    rsi_1h = rsi(closes_1h)

    # حساب مصفوفة القوة
    bullish_score = 0
    bearish_score = 0

    if ema9_1h and ema21_1h and ema9_1h > ema21_1h: bullish_score += 25
    if ema9_4h and ema21_4h and ema9_4h > ema21_4h: bullish_score += 25
    if 50.0 <= rsi_1h <= 68.0: bullish_score += 25
    if rsi_15m > 52.0: bullish_score += 25

    if ema9_1h and ema21_1h and ema9_1h < ema21_1h: bearish_score += 25
    if ema9_4h and ema21_4h and ema9_4h < ema21_4h: bearish_score += 25
    if 32.0 <= rsi_1h <= 50.0: bearish_score += 25
    if rsi_15m < 48.0: bearish_score += 25

    current_time = time.monotonic()

    if (bullish_score >= 75 or bearish_score >= 75) and (current_time - last_signal_time >= COOLDOWN_SECONDS):
        side = "BUY" if bullish_score >= 75 else "SELL"
        title = "🟢 [إشارة القنص العالمية — BUY]" if side == "BUY" else "🔴 [إشارة القنص العالمية — SELL]"

        atr_val = price * 0.004
        if side == "BUY":
            sl = price - (1.5 * atr_val)
            tp = price + (RISK_REWARD * (price - sl))
        else:
            sl = price + (1.5 * atr_val)
            tp = price - (RISK_REWARD * (sl - price))

