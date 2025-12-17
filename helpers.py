import os
import requests
from flask import redirect, render_template, session
from functools import wraps
import random
from datetime import datetime, timedelta
import time
import difflib
from typing import List
from utils import POPULAR_SYMBOLS

# Simple cache for stock quotes (30 second TTL to avoid rate limits)
_quote_cache = {}
_CACHE_TTL = 30  # seconds


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def lookup(symbol, force_refresh=False):
    """
    Look up quote for symbol using Yahoo Finance API.
    Implements 30-second caching to improve performance.
    
    Args:
        symbol: Stock symbol to look up
        force_refresh: If True, bypass cache and fetch fresh data
    
    Yahoo Finance is free and requires no API key.
    """
    import yfinance as yf
    
    symbol_upper = symbol.upper()
    current_time = time.time()
    
    # Check cache first (unless force refresh requested)
    if not force_refresh and symbol_upper in _quote_cache:
        cached_data, cached_time = _quote_cache[symbol_upper]
        if current_time - cached_time < _CACHE_TTL:
            return cached_data
    
    try:
        # Get stock data from Yahoo Finance
        ticker = yf.Ticker(symbol_upper)
        
        # Try to get current price from fast_info first (faster)
        try:
            fast_info = ticker.fast_info
            current_price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
            previous_close = fast_info.get('previousClose', current_price)
        except:
            # Fallback to info if fast_info fails
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose', current_price)
        
        if current_price is None or current_price == 0:
            print(f"Invalid or no price data for {symbol_upper}")
            return None
        
        # Get detailed info for name (only if needed)
        try:
            info = ticker.info
            name = info.get('longName') or info.get('shortName', symbol_upper)
            day_high = info.get('dayHigh', current_price)
            day_low = info.get('dayLow', current_price)
            day_open = info.get('open', current_price)
        except:
            name = symbol_upper
            day_high = current_price
            day_low = current_price
            day_open = current_price
        
        # Calculate change
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close > 0 else 0
        
        result = {
            "symbol": symbol_upper,
            "price": float(current_price),
            "name": name,
            "change": float(change),
            "change_percent": float(change_percent),
            "high": float(day_high),
            "low": float(day_low),
            "open": float(day_open),
            "previous_close": float(previous_close)
        }
        
        # Store in cache with timestamp
        _quote_cache[symbol_upper] = (result, current_time)
        
        return result
    
    except Exception as e:
        print(f"Error looking up {symbol}: {str(e)}")
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def get_chart_data(symbol, days=30):
    """
    Get historical price data for charts using Yahoo Finance.
    Returns dict with dates and prices for the last N days.
    """
    import yfinance as yf
    from datetime import datetime, timedelta
    
    try:
        ticker = yf.Ticker(symbol.upper())
        
        # Get historical data
        period_map = {
            7: '7d',
            30: '1mo',
            90: '3mo',
            180: '6mo',
            365: '1y'
        }
        
        # Find closest period or default to exact days
        period = period_map.get(days, f'{days}d')
        hist = ticker.history(period=period)
        
        if hist.empty:
            print(f"No chart data available for {symbol}")
            return None
        
        # Format data for Chart.js
        dates = [date.strftime('%Y-%m-%d') for date in hist.index]
        
        return {
            'dates': dates,
            'prices': hist['Close'].tolist(),
            'highs': hist['High'].tolist(),
            'lows': hist['Low'].tolist(),
            'opens': hist['Open'].tolist(),
            'volumes': hist['Volume'].tolist()
        }
    
    except Exception as e:
        print(f"Error fetching chart data for {symbol}: {str(e)}")
        return None


def get_popular_stocks():
    """Get quotes for popular stocks to display on homepage"""
    popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'SPY']
    
    stocks = []
    for symbol in popular_symbols:
        quote = lookup(symbol)
        if quote:
            stocks.append(quote)
    
    return stocks


def get_stock_news(symbol, limit=5):
    """Get recent news for a stock using Yahoo Finance"""
    import yfinance as yf
    
    try:
        ticker = yf.Ticker(symbol.upper())
        news = ticker.news
        
        if not news:
            return []
        
        # Format news to match expected structure
        formatted_news = []
        for article in news[:limit]:
            formatted_news.append({
                'headline': article.get('title', ''),
                'summary': article.get('summary', ''),
                'url': article.get('link', ''),
                'source': article.get('publisher', 'Yahoo Finance'),
                'datetime': article.get('providerPublishTime', int(time.time()))
            })
        
        return formatted_news
    
    except Exception as e:
        print(f"Error fetching news for {symbol}: {str(e)}")
        return []


def search_tickers(query, limit=8):
    """Search Yahoo Finance for symbols/company names similar to query.

    Uses Yahoo's public search endpoint to return a small list of matching
    symbols with their display names. Returns list of dicts: {symbol, name}.
    """
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {
            'q': query,
            'lang': 'en-US',
            'region': 'US',
            'quotesCount': limit,
            'newsCount': 0
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get('quotes', [])[:limit]:
            # Only include equities/ETFs for quoting
            qtype = item.get('quoteType', '').upper()
            if qtype not in ('EQUITY', 'ETF', 'MUTUALFUND'):
                # include some common types but skip collections like 'INDEX' if not relevant
                pass

            symbol = item.get('symbol')
            name = item.get('longname') or item.get('shortname') or item.get('name') or item.get('quoteSourceName') or symbol
            if symbol:
                results.append({'symbol': symbol, 'name': name})

        return results
    except Exception as e:
        print(f"Error searching tickers for '{query}': {e}")
        # If the remote search fails (rate limit or network issue), fall back
        # to a small local search over popular symbols using fuzzy matching.
        try:
            return _local_search_tickers(query, limit)
        except Exception as ex:
            print(f"Local fallback search failed: {ex}")
            return []


_symbol_name_cache = {}


def _ensure_symbol_name(symbol: str) -> str:
    """Ensure we have a display name for symbol; cache it."""
    sym = symbol.upper()
    if sym in _symbol_name_cache:
        return _symbol_name_cache[sym]
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        info = t.info
        name = info.get('longName') or info.get('shortName') or sym
    except Exception:
        name = sym
    _symbol_name_cache[sym] = name
    return name


def _local_search_tickers(query: str, limit: int = 8) -> List[dict]:
    """Fallback search: check popular symbols and fuzzy-match company names."""
    q = (query or '').strip().lower()
    candidates = []

    # Pre-seed popular symbols (ensure names cached)
    for sym in POPULAR_SYMBOLS:
        name = _ensure_symbol_name(sym)
        candidates.append({'symbol': sym, 'name': name})

    # First, direct substring matches on symbol or name
    results = []
    for item in candidates:
        if len(results) >= limit:
            break
        if q in item['symbol'].lower() or q in item['name'].lower():
            results.append(item)

    if len(results) >= limit:
        return results[:limit]

    # If not enough, use difflib on company names
    names = [c['name'] for c in candidates]
    close = difflib.get_close_matches(query, names, n=limit)
    for cname in close:
        for c in candidates:
            if c['name'] == cname and c not in results:
                results.append(c)
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return results[:limit]


def get_market_movers():
    """Get top gaining and losing stocks from major indices"""
    try:
        # Get S&P 500 constituents (we'll check a subset)
        major_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B',
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'BAC', 'MA', 'DIS', 'NFLX',
            'ADBE', 'CRM', 'PFE', 'CSCO', 'INTC', 'AMD', 'ORCL', 'PYPL'
        ]
        
        movers = []
        for symbol in major_symbols[:20]:  # Process subset to balance performance
            quote = lookup(symbol)
            if quote and 'change_percent' in quote:
                movers.append({
                    'symbol': symbol,
                    'name': quote.get('name', symbol),
                    'price': quote['price'],
                    'change': quote.get('change', 0),
                    'change_percent': quote['change_percent']
                })
        
        # Sort by change_percent
        movers.sort(key=lambda x: x['change_percent'], reverse=True)
        
        # Get top 5 gainers and losers
        gainers = movers[:5]
        losers = movers[-5:]
        losers.reverse()  # Show worst losers first
        
        return {
            'gainers': gainers,
            'losers': losers
        }
    
    except Exception as e:
        print(f"Error fetching market movers: {str(e)}")
        return {'gainers': [], 'losers': []}


def _generate_mock_candles(symbol, days=90):
    """
    Generate realistic mock candlestick data based on current stock price.
    Used as fallback when Yahoo Finance API is unavailable.
    """
    # Get current price
    quote = lookup(symbol)
    if not quote:
        return []
    
    current_price = quote['price']
    candles = []
    
    # Start from 'days' ago and generate data up to today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Initial price (simulate historical starting point ~10% lower on average)
    price = current_price * (0.85 + random.random() * 0.25)  # Between 85-110% of current
    
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday=0, Friday=4
            # Random daily movement (between -3% and +3%)
            daily_change = (random.random() - 0.5) * 0.06
            
            # Trend towards current price (stronger as we get closer to today)
            days_remaining = (end_date - current_date).days
            if days_remaining > 0:
                trend_factor = 0.05 * (1 - days_remaining / days)
                price_target = current_price
                trend = (price_target - price) / price * trend_factor
                daily_change += trend
            
            # Calculate OHLC
            open_price = price
            close_price = price * (1 + daily_change)
            
            # High/Low with some randomness
            volatility = random.random() * 0.02  # 0-2% intraday range
            high_price = max(open_price, close_price) * (1 + volatility)
            low_price = min(open_price, close_price) * (1 - volatility)
            
            # Volume (random between 500k and 50M)
            volume = int(random.random() * 49500000 + 500000)
            
            candles.append({
                'time': int(current_date.timestamp()),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            price = close_price
        
        current_date += timedelta(days=1)
    
    return candles


def get_candlestick_data(symbol, timeframe='D', days=90):
    """
    Get OHLCV candlestick data for a stock using Yahoo Finance
    
    Args:
        symbol: Stock symbol
        timeframe: Timeframe (D=daily, W=weekly, M=monthly)
        days: Number of days of historical data
    
    Returns:
        List of candles with format:
        [{time, open, high, low, close, volume}, ...]
    """
    import yfinance as yf
    
    try:
        ticker = yf.Ticker(symbol.upper())
        
        # Map timeframe to yfinance interval
        interval_map = {
            'D': '1d',   # Daily
            'W': '1wk',  # Weekly
            'M': '1mo',  # Monthly
            '60': '60m', # 60 minute
            '30': '30m', # 30 minute
            '15': '15m', # 15 minute
            '5': '5m',   # 5 minute
            '1': '1m'    # 1 minute
        }
        interval = interval_map.get(timeframe, '1d')
        
        # For intraday data, limit to recent days
        if timeframe in ['60', '30', '15', '5', '1']:
            days = min(days, 7)  # Max 7 days for intraday
        
        # Get historical data
        hist = ticker.history(period=f'{days}d', interval=interval)
        
        if hist.empty:
            return _generate_mock_candles(symbol, days)
        
        # Format data for TradingView charts
        candles = []
        for date, row in hist.iterrows():
            candles.append({
                'time': int(date.timestamp()),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        
        return candles
    
    except Exception as e:
        print(f"Error fetching candlestick data for {symbol}: {str(e)}")
        # Fallback to mock data on error
        return _generate_mock_candles(symbol, days)


def calculate_sma(prices, period=20):
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return []
    
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(None)
        else:
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(round(avg, 2))
    return sma


def calculate_ema(prices, period=20):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return []
    
    multiplier = 2 / (period + 1)
    ema = []
    
    # Start with SMA for first value
    sma = sum(prices[:period]) / period
    ema.append(round(sma, 2))
    
    # Calculate EMA for rest
    for i in range(period, len(prices)):
        ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(round(ema_value, 2))
    
    # Pad beginning with None
    return [None] * (period - 1) + ema


def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return []
    
    gains = []
    losses = []
    
    # Calculate gains and losses
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    
    # Calculate RSI
    rsi = [None] * period
    
    # First RSI uses simple average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        rsi.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi.append(round(100 - (100 / (1 + rs)), 2))
    
    # Subsequent RSI uses smoothed average
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(round(100 - (100 / (1 + rs)), 2))
    
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow:
        return {'macd': [], 'signal': [], 'histogram': []}
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # Calculate MACD line
    macd_line = []
    for i in range(len(prices)):
        if ema_fast[i] is None or ema_slow[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(round(ema_fast[i] - ema_slow[i], 2))
    
    # Calculate signal line (EMA of MACD)
    macd_values = [x for x in macd_line if x is not None]
    signal_ema = calculate_ema(macd_values, signal)
    
    # Pad signal line
    signal_line = [None] * (len(macd_line) - len(signal_ema)) + signal_ema
    
    # Calculate histogram
    histogram = []
    for i in range(len(macd_line)):
        if macd_line[i] is None or signal_line[i] is None:
            histogram.append(None)
        else:
            histogram.append(round(macd_line[i] - signal_line[i], 2))
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return {'upper': [], 'middle': [], 'lower': []}
    
    middle = calculate_sma(prices, period)
    upper = []
    lower = []
    
    for i in range(len(prices)):
        if i < period - 1:
            upper.append(None)
            lower.append(None)
        else:
            # Calculate standard deviation
            slice_data = prices[i - period + 1:i + 1]
            mean = sum(slice_data) / period
            variance = sum((x - mean) ** 2 for x in slice_data) / period
            std = variance ** 0.5
            
            upper.append(round(middle[i] + (std_dev * std), 2))
            lower.append(round(middle[i] - (std_dev * std), 2))
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }


def get_technical_indicators(symbol, timeframe='D', days=90):
    """Get candlestick data with technical indicators"""
    candles = get_candlestick_data(symbol, timeframe, days)
    
    if not candles:
        return None
    
    # Extract close prices for indicator calculation
    close_prices = [c['close'] for c in candles]
    timestamps = [c['time'] for c in candles]
    
    # Calculate all indicators
    sma_20 = calculate_sma(close_prices, 20)
    sma_50 = calculate_sma(close_prices, 50)
    ema_20 = calculate_ema(close_prices, 20)
    rsi = calculate_rsi(close_prices, 14)
    macd = calculate_macd(close_prices, 12, 26, 9)
    bollinger = calculate_bollinger_bands(close_prices, 20, 2)
    
    # Format indicators with timestamps
    indicators = {
        'candles': candles,
        'sma_20': [{'time': timestamps[i], 'value': sma_20[i]} for i in range(len(sma_20)) if sma_20[i] is not None],
        'sma_50': [{'time': timestamps[i], 'value': sma_50[i]} for i in range(len(sma_50)) if sma_50[i] is not None],
        'ema_20': [{'time': timestamps[i], 'value': ema_20[i]} for i in range(len(ema_20)) if ema_20[i] is not None],
        'rsi': [{'time': timestamps[i], 'value': rsi[i]} for i in range(len(rsi)) if rsi[i] is not None],
        'macd': {
            'macd': [{'time': timestamps[i], 'value': macd['macd'][i]} for i in range(len(macd['macd'])) if macd['macd'][i] is not None],
            'signal': [{'time': timestamps[i], 'value': macd['signal'][i]} for i in range(len(macd['signal'])) if macd['signal'][i] is not None],
            'histogram': [{'time': timestamps[i], 'value': macd['histogram'][i]} for i in range(len(macd['histogram'])) if macd['histogram'][i] is not None]
        },
        'bollinger': {
            'upper': [{'time': timestamps[i], 'value': bollinger['upper'][i]} for i in range(len(bollinger['upper'])) if bollinger['upper'][i] is not None],
            'middle': [{'time': timestamps[i], 'value': bollinger['middle'][i]} for i in range(len(bollinger['middle'])) if bollinger['middle'][i] is not None],
            'lower': [{'time': timestamps[i], 'value': bollinger['lower'][i]} for i in range(len(bollinger['lower'])) if bollinger['lower'][i] is not None]
        }
    }
    
    return indicators


def calculate_portfolio_analytics(user_id, db):
    """
    Calculate comprehensive portfolio analytics including risk metrics,
    performance stats, and diversification analysis.
    """
    from datetime import datetime, timedelta
    import math
    
    # Get user data
    user = db.get_user(user_id)
    stocks = db.get_user_stocks(user_id)
    transactions = db.get_transactions(user_id)
    
    # Initialize analytics dict
    analytics = {
        'total_value': user['cash'],
        'cash': user['cash'],
        'stocks_value': 0,
        'total_invested': 0,
        'total_return': 0,
        'return_percentage': 0,
        'holdings': [],
        'sector_allocation': {},
        'risk_metrics': {},
        'performance_metrics': {},
        'diversification': {}
    }
    
    # Calculate current portfolio value and holdings
    sector_map = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'META': 'Technology',
        'AMZN': 'Consumer', 'TSLA': 'Automotive', 'NVDA': 'Technology', 'AMD': 'Technology',
        'JPM': 'Finance', 'BAC': 'Finance', 'GS': 'Finance', 'V': 'Finance',
        'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'WMT': 'Consumer', 'HD': 'Consumer', 'MCD': 'Consumer'
    }
    
    for stock in stocks:
        quote = lookup(stock['symbol'])
        if quote:
            current_value = stock['shares'] * quote['price']
            analytics['stocks_value'] += current_value
            analytics['total_value'] += current_value
            
            # Calculate cost basis for this holding
            cost_basis = 0
            shares_counted = 0
            for txn in transactions:
                if txn['symbol'] == stock['symbol'] and txn['type'] == 'buy':
                    shares_to_count = min(stock['shares'] - shares_counted, txn['shares'])
                    cost_basis += shares_to_count * txn['price']
                    shares_counted += shares_to_count
                    if shares_counted >= stock['shares']:
                        break
            
            gain_loss = current_value - cost_basis
            gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
            
            holding = {
                'symbol': stock['symbol'],
                'shares': stock['shares'],
                'avg_price': cost_basis / stock['shares'] if stock['shares'] > 0 else 0,
                'current_price': quote['price'],
                'current_value': current_value,
                'cost_basis': cost_basis,
                'gain_loss': gain_loss,
                'gain_loss_pct': gain_loss_pct,
                'portfolio_weight': 0  # Will calculate after total is known
            }
            analytics['holdings'].append(holding)
            
            # Sector allocation
            sector = sector_map.get(stock['symbol'], 'Other')
            analytics['sector_allocation'][sector] = analytics['sector_allocation'].get(sector, 0) + current_value
    
    # Calculate portfolio weights
    for holding in analytics['holdings']:
        holding['portfolio_weight'] = (holding['current_value'] / analytics['total_value'] * 100) if analytics['total_value'] > 0 else 0
    
    # Sort holdings by value
    analytics['holdings'].sort(key=lambda x: x['current_value'], reverse=True)
    
    # Calculate total return
    total_invested = 10000  # Starting cash
    for txn in transactions:
        if txn['type'] == 'buy':
            total_invested += txn['shares'] * txn['price']
    
    analytics['total_invested'] = total_invested
    analytics['total_return'] = analytics['total_value'] - total_invested
    analytics['return_percentage'] = (analytics['total_return'] / total_invested * 100) if total_invested > 0 else 0
    
    # Calculate daily returns for risk metrics
    snapshots = db.get_portfolio_snapshots(user_id, limit=90)
    # Benchmark: S&P 500 (simulate with SPY)
    spy_history = []
    for snap in snapshots:
        quote = lookup('SPY')
        if quote:
            spy_history.append(quote['price'])
    if len(snapshots) >= 2:
        daily_returns = []
        spy_returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1]['total_value']
            curr_value = snapshots[i]['total_value']
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
            if len(spy_history) == len(snapshots):
                prev_spy = spy_history[i-1]
                curr_spy = spy_history[i]
                if prev_spy > 0:
                    spy_return = (curr_spy - prev_spy) / prev_spy
                    spy_returns.append(spy_return)
        if daily_returns:
            # Volatility (standard deviation of returns)
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            volatility = math.sqrt(variance) * math.sqrt(252)  # Annualized
            # Downside deviation (only negative returns)
            downside_returns = [r for r in daily_returns if r < 0]
            downside_dev = math.sqrt(sum((r) ** 2 for r in downside_returns) / len(downside_returns)) * math.sqrt(252) if downside_returns else 0
            # Sortino Ratio (risk-free rate 2%)
            risk_free_rate = 0.02
            annualized_return = mean_return * 252
            sortino_ratio = (annualized_return - risk_free_rate) / downside_dev if downside_dev > 0 else 0
            # Sharpe Ratio
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
            # Beta (vs SPY)
            beta = 1.0
            if spy_returns and len(spy_returns) == len(daily_returns):
                cov = sum((daily_returns[i] - mean_return) * (spy_returns[i] - (sum(spy_returns)/len(spy_returns))) for i in range(len(daily_returns))) / len(daily_returns)
                spy_var = sum((r - (sum(spy_returns)/len(spy_returns))) ** 2 for r in spy_returns) / len(spy_returns)
                beta = cov / spy_var if spy_var > 0 else 1.0
            # Maximum Drawdown
            peak = snapshots[0]['total_value']
            max_drawdown = 0
            for snapshot in snapshots:
                if snapshot['total_value'] > peak:
                    peak = snapshot['total_value']
                drawdown = (peak - snapshot['total_value']) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            analytics['risk_metrics'] = {
                'volatility': volatility * 100,  # As percentage
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'downside_deviation': downside_dev * 100,
                'max_drawdown': max_drawdown * 100,  # As percentage
                'beta': beta,
                'var_95': sorted(daily_returns)[int(len(daily_returns) * 0.05)] * 100 if daily_returns else 0  # Value at Risk
            }
            # Benchmark comparison
            analytics['benchmark'] = {
                'spy_total_return': ((spy_history[-1] - spy_history[0]) / spy_history[0] * 100) if spy_history else 0,
                'spy_volatility': (math.sqrt(sum((r - (sum(spy_returns)/len(spy_returns))) ** 2 for r in spy_returns) / len(spy_returns)) * math.sqrt(252) * 100) if spy_returns else 0
            }
    
    # Performance metrics
    winning_trades = sum(1 for txn in transactions if txn['type'] == 'sell' and txn.get('profit', 0) > 0)
    losing_trades = sum(1 for txn in transactions if txn['type'] == 'sell' and txn.get('profit', 0) < 0)
    total_trades = winning_trades + losing_trades
    
    analytics['performance_metrics'] = {
        'total_trades': len(transactions),
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
        'avg_gain': sum(txn.get('profit', 0) for txn in transactions if txn.get('profit', 0) > 0) / winning_trades if winning_trades > 0 else 0,
        'avg_loss': sum(txn.get('profit', 0) for txn in transactions if txn.get('profit', 0) < 0) / losing_trades if losing_trades > 0 else 0
    }
    
    # Diversification metrics
    analytics['diversification'] = {
        'num_holdings': len(stocks),
        'num_sectors': len(analytics['sector_allocation']),
        'concentration': analytics['holdings'][0]['portfolio_weight'] if analytics['holdings'] else 0,  # Top holding %
        'herfindahl_index': sum((h['portfolio_weight'] / 100) ** 2 for h in analytics['holdings'])  # Lower is more diversified
    }
    
    # Convert sector allocation to percentages
    sector_allocation_pct = {}
    for sector, value in analytics['sector_allocation'].items():
        sector_allocation_pct[sector] = (value / analytics['total_value'] * 100) if analytics['total_value'] > 0 else 0
    analytics['sector_allocation'] = sector_allocation_pct
    
    return analytics


def calculate_portfolio_performance_history(user_id, db, days=30):
    """Get historical portfolio performance data for charting"""
    from datetime import datetime, timedelta
    
    snapshots = db.get_portfolio_snapshots(user_id, limit=days)
    
    if not snapshots:
        return []
    
    # Format for Chart.js
    performance_data = []
    for snapshot in reversed(snapshots):  # Oldest first
        performance_data.append({
            'date': snapshot['timestamp'].split(' ')[0] if isinstance(snapshot['timestamp'], str) else snapshot['timestamp'],
            'value': snapshot['total_value']
        })
    
    return performance_data


# ============ OPTIONS PRICING & GREEKS ============

import math
from scipy.stats import norm

def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    """
    Calculate Black-Scholes option price
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Volatility (annual)
        option_type: 'call' or 'put'
    
    Returns:
        Option price
    """
    if T <= 0:
        # Expired option - intrinsic value only
        if option_type == 'call':
            return max(0, S - K)
        else:
            return max(0, K - S)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return max(0, price)


def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho)
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (annual)
        sigma: Volatility (annual)
        option_type: 'call' or 'put'
    
    Returns:
        Dictionary with all Greeks
    """
    if T <= 0:
        return {
            'delta': 0,
            'gamma': 0,
            'theta': 0,
            'vega': 0,
            'rho': 0
        }
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1
    
    # Gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    
    # Theta
    if option_type == 'call':
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) 
                 - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) 
                 + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
    
    # Vega (same for calls and puts)
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100  # Divided by 100 for 1% change
    
    # Rho
    if option_type == 'call':
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
    else:
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 4),
        'theta': round(theta, 4),
        'vega': round(vega, 4),
        'rho': round(rho, 4)
    }


def get_option_price_and_greeks(symbol, strike, expiration_date, option_type, current_price=None):
    """
    Get option price and Greeks for a specific contract
    
    Args:
        symbol: Stock symbol
        strike: Strike price
        expiration_date: Expiration date (YYYY-MM-DD)
        option_type: 'call' or 'put'
        current_price: Current stock price (will lookup if not provided)
    
    Returns:
        Dictionary with price and Greeks
    """
    # Get current stock price if not provided
    if current_price is None:
        quote = lookup(symbol)
        if not quote:
            return None
        current_price = quote['price']
    
    # Calculate time to expiration
    from datetime import datetime
    exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
    current_date = datetime.now()
    days_to_expiration = (exp_date - current_date).days
    time_to_expiration = max(0, days_to_expiration / 365.0)  # Convert to years
    
    # Use simplified assumptions for paper trading
    risk_free_rate = 0.045  # 4.5% (current approximate risk-free rate)
    volatility = 0.30  # 30% annual volatility (can be enhanced with historical calculation)
    
    # Calculate price and Greeks
    price = black_scholes_price(current_price, strike, time_to_expiration, 
                                risk_free_rate, volatility, option_type)
    greeks = calculate_greeks(current_price, strike, time_to_expiration, 
                              risk_free_rate, volatility, option_type)
    
    # Calculate intrinsic and extrinsic value
    if option_type == 'call':
        intrinsic_value = max(0, current_price - strike)
    else:
        intrinsic_value = max(0, strike - current_price)
    
    extrinsic_value = max(0, price - intrinsic_value)
    
    return {
        'price': round(price, 2),
        'greeks': greeks,
        'intrinsic_value': round(intrinsic_value, 2),
        'extrinsic_value': round(extrinsic_value, 2),
        'days_to_expiration': days_to_expiration,
        'time_to_expiration': round(time_to_expiration, 4),
        'in_the_money': intrinsic_value > 0
    }


# ============ NEWS & SENTIMENT ANALYSIS ============

def analyze_sentiment(text):
    """
    Analyze sentiment of text using VADER
    
    Args:
        text: Text to analyze (headline or article)
    
    Returns:
        Dictionary with sentiment score and label
    """
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        
        # Compound score: -1 (most negative) to +1 (most positive)
        compound = scores['compound']
        
        # Classify sentiment
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'score': round(compound, 4),
            'label': label,
            'positive': scores['pos'],
            'neutral': scores['neu'],
            'negative': scores['neg']
        }
    except ImportError:
        # Fallback if VADER not installed
        return {
            'score': 0,
            'label': 'neutral',
            'positive': 0,
            'neutral': 1,
            'negative': 0
        }


def fetch_news_finnhub(symbol=None, limit=50):
    """
    Fetch news using Yahoo Finance API
    
    Args:
        symbol: Stock symbol (None for general market news)
        limit: Maximum number of articles
    
    Returns:
        List of news articles with sentiment
    """
    import yfinance as yf
    from datetime import datetime
    
    try:
        if symbol:
            # Company news from Yahoo Finance
            ticker = yf.Ticker(symbol)
            articles = ticker.news
        else:
            # For general market news, use a major index like S&P 500
            ticker = yf.Ticker("^GSPC")
            articles = ticker.news
        
        if not articles:
            return []
        
        # Process and add sentiment
        processed_articles = []
        for article in articles[:limit]:
            # Analyze sentiment
            headline = article.get('title', '')
            summary = article.get('summary', '')
            text_to_analyze = f"{headline}. {summary}"
            
            sentiment = analyze_sentiment(text_to_analyze)
            
            # Convert timestamp to readable format
            timestamp = article.get('providerPublishTime', int(time.time()))
            published_at = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            processed_articles.append({
                'symbol': symbol,
                'headline': headline,
                'summary': summary,
                'source': article.get('publisher', 'Yahoo Finance'),
                'url': article.get('link', ''),
                'image_url': article.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '') if article.get('thumbnail') else '',
                'published_at': published_at,
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'category': 'general'
            })
        
        return processed_articles
    
    except Exception as e:
        print(f"Error fetching news from Yahoo Finance: {e}")
        return []


def get_cached_or_fetch_news(symbol, db, force_refresh=False):
    """
    Get news from cache or fetch fresh if needed
    
    Args:
        symbol: Stock symbol (None for general news)
        db: Database manager instance
        force_refresh: Force fetch from API
    
    Returns:
        List of news articles
    """
    # Check cache first (unless force refresh)
    if not force_refresh:
        if symbol:
            cached = db.get_news_by_symbol(symbol, limit=20, max_age_hours=2)
        else:
            cached = db.get_general_news(limit=50, max_age_hours=2)
        
        if cached:
            return cached
    
    # Fetch fresh news
    articles = fetch_news_finnhub(symbol, limit=50)
    
    # Cache the articles
    for article in articles:
        db.cache_news_article(
            article['symbol'],
            article['headline'],
            article['summary'],
            article['source'],
            article['url'],
            article['image_url'],
            article['published_at'],
            article['sentiment_score'],
            article['sentiment_label'],
            article['category']
        )
    
    return articles


def calculate_portfolio_analytics(user_id, db):
    """
    Calculate comprehensive portfolio analytics including risk metrics
    """
    import numpy as np
    from collections import defaultdict
    
    # Get user data
    user = db.get_user(user_id)
    cash = user['cash']
    
    # Get holdings
    holdings = db.get_user_stocks(user_id)
    
    # Initialize analytics
    total_value = cash
    positions = []
    sector_allocation = defaultdict(float)
    
    # Map sectors (simplified - in production use real sector data)
    sector_map = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'AMZN': 'Consumer Cyclical',
        'TSLA': 'Automotive', 'NVDA': 'Technology', 'META': 'Technology', 'JPM': 'Financial',
        'JNJ': 'Healthcare', 'V': 'Financial', 'PG': 'Consumer Defensive', 'UNH': 'Healthcare',
        'HD': 'Consumer Cyclical', 'BAC': 'Financial', 'MA': 'Financial', 'DIS': 'Communication',
        'NFLX': 'Communication', 'ADBE': 'Technology', 'CRM': 'Technology', 'PFE': 'Healthcare',
        'CSCO': 'Technology', 'INTC': 'Technology', 'AMD': 'Technology', 'ORCL': 'Technology'
    }
    
    for holding in holdings:
        quote = lookup(holding['symbol'])
        if quote:
            current_value = quote['price'] * holding['shares']
            total_value += current_value
            
            cost_basis = holding.get('avg_cost', quote['price']) * holding['shares']
            profit_loss = current_value - cost_basis
            profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
            
            sector = sector_map.get(holding['symbol'], 'Other')
            sector_allocation[sector] += current_value
            
            positions.append({
                'symbol': holding['symbol'],
                'shares': holding['shares'],
                'current_price': quote['price'],
                'current_value': current_value,
                'cost_basis': cost_basis,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'weight': 0,  # Will calculate after we know total
                'sector': sector
            })
    
    # Calculate position weights
    for pos in positions:
        pos['weight'] = (pos['current_value'] / total_value * 100) if total_value > 0 else 0
    
    # Get historical data for risk metrics
    snapshots = db.get_portfolio_snapshots(user_id, limit=90)
    
    # Calculate returns
    daily_returns = []
    if len(snapshots) > 1:
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i]['total_value']
            curr_value = snapshots[i-1]['total_value']
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
    
    # Risk Metrics
    volatility = 0
    sharpe_ratio = 0
    max_drawdown = 0
    
    if daily_returns:
        returns_array = np.array(daily_returns)
        volatility = np.std(returns_array) * np.sqrt(252) * 100  # Annualized
        
        mean_return = np.mean(returns_array)
        if volatility > 0:
            risk_free_rate = 0.04 / 252  # 4% annual risk-free rate
            sharpe_ratio = (mean_return - risk_free_rate) / np.std(returns_array) * np.sqrt(252)
        
        # Calculate max drawdown
        cumulative = [10000]  # Starting value
        for ret in daily_returns:
            cumulative.append(cumulative[-1] * (1 + ret))
        
        peak = cumulative[0]
        max_dd = 0
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        max_drawdown = max_dd * 100
    
    # Calculate Beta (vs SPY as benchmark)
    beta = 1.0
    correlation = 0.0
    try:
        if len(daily_returns) > 20:
            # Get SPY returns for same period
            spy_returns = []
            for i in range(len(daily_returns)):
                # Simplified - use random market return for demo
                # In production, fetch actual SPY historical data
                spy_returns.append(random.uniform(-0.02, 0.02))
            
            if len(spy_returns) == len(daily_returns):
                portfolio_returns = np.array(daily_returns)
                market_returns = np.array(spy_returns)
                
                covariance = np.cov(portfolio_returns, market_returns)[0][1]
                market_variance = np.var(market_returns)
                
                if market_variance > 0:
                    beta = covariance / market_variance
                
                correlation = np.corrcoef(portfolio_returns, market_returns)[0][1]
    except Exception:
        pass
    
    # Diversification score (0-100)
    diversification_score = 0
    if positions:
        # Score based on number of positions and weight distribution
        num_positions = len(positions)
        max_weight = max([p['weight'] for p in positions]) if positions else 100
        
        position_score = min(num_positions * 10, 50)  # Max 50 for 5+ positions
        concentration_score = max(0, 50 - max_weight)  # Penalize high concentration
        diversification_score = position_score + concentration_score
    
    # Total return
    starting_cash = 10000  # Default starting cash
    total_return = total_value - starting_cash
    total_return_pct = (total_return / starting_cash * 100) if starting_cash > 0 else 0
    
    # Sector allocation percentages
    sector_pct = {}
    for sector, value in sector_allocation.items():
        sector_pct[sector] = (value / total_value * 100) if total_value > 0 else 0
    
    return {
        'total_value': total_value,
        'cash': cash,
        'invested_value': total_value - cash,
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        'num_positions': len(positions),
        'positions': positions,
        'sector_allocation': sector_pct,
        'risk_metrics': {
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'beta': beta,
            'max_drawdown': max_drawdown,
            'correlation': correlation,
            'diversification_score': diversification_score
        },
        'benchmark': {
            'spy_total_return': 12.5,  # Mock data
            'spy_volatility': 18.2,
            'alpha': (total_return_pct - 12.5) if total_return_pct else 0
        }
    }


def calculate_portfolio_performance_history(user_id, db, days=90):
    """Get portfolio performance history for charting"""
    snapshots = db.get_portfolio_snapshots(user_id, limit=days)
    
    history = []
    for snapshot in reversed(snapshots):
        history.append({
            'date': snapshot['timestamp'],
            'total_value': snapshot['total_value'],
            'cash': snapshot['cash']
        })
    
    return history
