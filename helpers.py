import os
import requests
from flask import redirect, render_template, session
from functools import wraps
import random
from datetime import datetime, timedelta
import time

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
    Look up quote for symbol using Finnhub API (free tier: 60 req/min).
    Implements 30-second caching to avoid rate limits.
    
    Args:
        symbol: Stock symbol to look up
        force_refresh: If True, bypass cache and fetch fresh data
    
    Get your free API key at: https://finnhub.io/register
    Set it in .env file as: FINNHUB_API_KEY=your_key_here
    """
    import os
    
    symbol_upper = symbol.upper()
    current_time = time.time()
    
    # Check cache first (unless force refresh requested)
    if not force_refresh and symbol_upper in _quote_cache:
        cached_data, cached_time = _quote_cache[symbol_upper]
        if current_time - cached_time < _CACHE_TTL:
            return cached_data
    
    # Get API key from environment
    api_key = os.environ.get("FINNHUB_API_KEY")
    
    if not api_key:
        print("Warning: FINNHUB_API_KEY not set. Get one free at https://finnhub.io/register")
        print("Add to .env file: FINNHUB_API_KEY=your_key_here")
        return None
    
    try:
        # Get real-time quote from Finnhub
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol_upper}&token={api_key}"
        quote_response = requests.get(quote_url, timeout=5)
        quote_response.raise_for_status()
        quote_data = quote_response.json()
        
        # Check if we got valid data
        current_price = quote_data.get('c')  # Current price
        if current_price is None or current_price == 0:
            print(f"Invalid or no price data for {symbol_upper}")
            return None
        
        # Get company profile for name (also check cache for profile)
        cache_key = f"{symbol_upper}_profile"
        if cache_key in _quote_cache:
            company_name = _quote_cache[cache_key]
        else:
            try:
                profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol_upper}&token={api_key}"
                profile_response = requests.get(profile_url, timeout=5)
                profile_response.raise_for_status()
                profile_data = profile_response.json()
                company_name = profile_data.get('name', symbol_upper)
                # Cache company name permanently (doesn't change)
                _quote_cache[cache_key] = company_name
            except:
                company_name = symbol_upper
                _quote_cache[cache_key] = company_name
        
        result = {
            "symbol": symbol_upper,
            "price": float(current_price),
            "name": company_name,
            "change": quote_data.get('d', 0),  # Daily change
            "change_percent": quote_data.get('dp', 0),  # Daily change percent
            "high": quote_data.get('h', current_price),  # Day high
            "low": quote_data.get('l', current_price),  # Day low
            "open": quote_data.get('o', current_price),  # Day open
            "previous_close": quote_data.get('pc', current_price)  # Previous close
        }
        
        # Store in cache with timestamp
        _quote_cache[symbol_upper] = (result, current_time)
        
        return result
    
    except requests.RequestException as e:
        print(f"API request error for {symbol}: {str(e)}")
        return None
    except (ValueError, KeyError) as e:
        print(f"Data parsing error for {symbol}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error looking up {symbol}: {str(e)}")
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def get_chart_data(symbol, days=30):
    """
    Get historical price data for charts.
    Returns dict with dates and prices for the last N days.
    """
    import os
    from datetime import datetime, timedelta
    
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return None
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Convert to Unix timestamps
        end_timestamp = int(end_date.timestamp())
        start_timestamp = int(start_date.timestamp())
        
        # Get candle data (daily prices)
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol.upper()}&resolution=D&from={start_timestamp}&to={end_timestamp}&token={api_key}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Check if we got valid data
        if data.get('s') != 'ok' or not data.get('c'):
            return None
        
        # Format data for Chart.js
        timestamps = data.get('t', [])
        closes = data.get('c', [])
        
        # Convert timestamps to dates
        dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
        
        return {
            'dates': dates,
            'prices': closes,
            'highs': data.get('h', []),
            'lows': data.get('l', []),
            'opens': data.get('o', []),
            'volumes': data.get('v', [])
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
    """Get recent news for a stock"""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return []
    
    try:
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        end_str = end_date.strftime('%Y-%m-%d')
        start_str = start_date.strftime('%Y-%m-%d')
        
        url = f"https://finnhub.io/api/v1/company-news?symbol={symbol.upper()}&from={start_str}&to={end_str}&token={api_key}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        news_data = response.json()
        
        # Return limited number of articles
        return news_data[:limit] if isinstance(news_data, list) else []
    
    except Exception as e:
        print(f"Error fetching news for {symbol}: {str(e)}")
        return []


def get_market_movers():
    """Get top gaining and losing stocks from major indices"""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return {'gainers': [], 'losers': []}
    
    try:
        # Get S&P 500 constituents (we'll check a subset)
        major_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B',
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'BAC', 'MA', 'DIS', 'NFLX',
            'ADBE', 'CRM', 'PFE', 'CSCO', 'INTC', 'AMD', 'ORCL', 'PYPL'
        ]
        
        movers = []
        for symbol in major_symbols[:20]:  # Limit to avoid API rate limits
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
    Used as fallback when Finnhub API is unavailable or rate limited.
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
    Get OHLCV candlestick data for a stock
    
    Args:
        symbol: Stock symbol
        timeframe: Timeframe (D=daily, W=weekly, M=monthly)
        days: Number of days of historical data
    
    Returns:
        List of candles with format:
        [{time, open, high, low, close, volume}, ...]
    """
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return _generate_mock_candles(symbol, days)
    
    try:
        # Calculate timestamp range
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        # Map timeframe to Finnhub resolution
        resolution_map = {
            'D': 'D',   # Daily
            'W': 'W',   # Weekly
            'M': 'M',   # Monthly
            '60': '60', # 60 minute
            '30': '30', # 30 minute
            '15': '15', # 15 minute
            '5': '5',   # 5 minute
            '1': '1'    # 1 minute
        }
        resolution = resolution_map.get(timeframe, 'D')
        
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol.upper()}&resolution={resolution}&from={start_time}&to={end_time}&token={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('s') != 'ok':
            # Fallback to mock data if API returns error
            return _generate_mock_candles(symbol, days)
        
        # Format data for TradingView charts
        candles = []
        for i in range(len(data['t'])):
            candles.append({
                'time': data['t'][i],
                'open': round(data['o'][i], 2),
                'high': round(data['h'][i], 2),
                'low': round(data['l'][i], 2),
                'close': round(data['c'][i], 2),
                'volume': data['v'][i]
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
    Fetch news from Finnhub API
    
    Args:
        symbol: Stock symbol (None for general market news)
        limit: Maximum number of articles
    
    Returns:
        List of news articles with sentiment
    """
    import os
    import requests
    from datetime import datetime, timedelta
    
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        print("Warning: FINNHUB_API_KEY not set")
        return []
    
    try:
        if symbol:
            # Company news
            url = f"https://finnhub.io/api/v1/company-news"
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            
            params = {
                'symbol': symbol,
                'from': week_ago.strftime('%Y-%m-%d'),
                'to': today.strftime('%Y-%m-%d'),
                'token': api_key
            }
        else:
            # General market news
            url = f"https://finnhub.io/api/v1/news"
            params = {
                'category': 'general',
                'token': api_key
            }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        articles = response.json()
        
        # Process and add sentiment
        processed_articles = []
        for article in articles[:limit]:
            # Analyze sentiment
            headline = article.get('headline', '')
            summary = article.get('summary', '')
            text_to_analyze = f"{headline}. {summary}"
            
            sentiment = analyze_sentiment(text_to_analyze)
            
            processed_articles.append({
                'symbol': symbol,
                'headline': headline,
                'summary': summary,
                'source': article.get('source', 'Unknown'),
                'url': article.get('url', ''),
                'image_url': article.get('image', ''),
                'published_at': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'category': article.get('category', 'general')
            })
        
        return processed_articles
    
    except Exception as e:
        print(f"Error fetching news from Finnhub: {e}")
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
