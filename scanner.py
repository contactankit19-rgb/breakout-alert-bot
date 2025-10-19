from breakout import check_breakout, send_to_all, exchange

def run_scan():
    send_to_all("✅ 4H breakout scanner with scoring is live!")
    tickers = exchange.fetch_tickers()
    volume_data = {
        symbol: tickers[symbol]['quoteVolume']
        for symbol in tickers
        if '/USDT' in symbol and 'quoteVolume' in tickers[symbol]
    }
    top_100 = sorted(volume_data.items(), key=lambda x: x[1], reverse=True)[:100]
    symbols = [symbol for symbol, volume in top_100]

    for symbol in symbols:
        check_breakout(symbol)

if __name__ == '__main__':
    run_scan()
