import ccxt
import pandas as pd
from telegram import Bot
import os

# === CONFIG ===
TELEGRAM_TOKEN = '8446122011:AAF01V-OwF0OLnR3rgVv8jcJiVrHz_IfQV8'
TIMEFRAME = '4h'
LIMIT = 100
VOLUME_THRESHOLD = 30000000  # $30M
CHAT_IDS_FILE = 'chat_ids.txt'

# === INIT ===
exchange = ccxt.binance()
bot = Bot(token=TELEGRAM_TOKEN)

# === TELEGRAM SUBSCRIPTION LOGIC ===
def load_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE):
        return []
    with open(CHAT_IDS_FILE, 'r') as f:
        return f.read().splitlines()

def save_chat_ids(chat_ids):
    with open(CHAT_IDS_FILE, 'w') as f:
        f.write('\n'.join(chat_ids))

def send_to_all(message):
    for chat_id in load_chat_ids():
        try:
            bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"⚠️ Failed to send to {chat_id}: {e}")

# === SCANNER LOGIC ===
def fetch_ohlcv(symbol):
    data = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_breakout(symbol):
    try:
        score = 0
        ticker = exchange.fetch_ticker(symbol)
        volume_usd = ticker['quoteVolume']
        if volume_usd > VOLUME_THRESHOLD:
            score += 1
        else:
            print(f"❌ {symbol} — Volume ${volume_usd:,.0f} < $30M")

        df = fetch_ohlcv(symbol)
        close = df['close']
        open_ = df['open']
        high = df['high']
        low = df['low']

        # EMA logic
        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()
        if close.iloc[-1] > ema9.iloc[-1] > ema21.iloc[-1]:
            score += 1

        # RSI logic
        rsi = calculate_rsi(close)
        if rsi.iloc[-1] > 50:
            score += 1

        # MACD crossover
        macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal_line = macd_line.ewm(span=9).mean()
        if macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
            score += 1

        # Candle body strength
        body = abs(close.iloc[-1] - open_.iloc[-1])
        range_ = high.iloc[-1] - low.iloc[-1]
        if range_ > 0 and body / range_ > 0.5:
            score += 1

        # Final decision
        if score >= 4:
            print(f"✅ {symbol} scored {score}/5 — sending alert")
            message = (
                f"🚀 Breakout Alert (4H): {symbol}\n"
                f"Score: {score}/5\n"
                f"Volume: ${volume_usd:,.0f}\n"
                f"RSI: {rsi.iloc[-1]:.2f}\n"
                f"EMA9 > EMA21: ✅\n"
                f"MACD crossover: ✅\n"
                f"Candle strength: ✅"
            )
            send_to_all(message)
        else:
            print(f"🔍 {symbol} scored {score}/5 — skipped")

    except Exception as e:
        print(f"⚠️ Error with {symbol}: {e}")
