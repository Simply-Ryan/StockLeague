import requests
from flask import redirect, render_template, session
from functools import wraps
import random


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


def lookup(symbol):
    """
    Look up quote for symbol using Finnhub API (free tier: 60 req/min).
    Get your free API key at: https://finnhub.io/register
    Set it in .env file as: FINNHUB_API_KEY=your_key_here
    """
    import os
    
    # Get API key from environment
    api_key = os.environ.get("FINNHUB_API_KEY")
    
    if not api_key:
        print("Warning: FINNHUB_API_KEY not set. Get one free at https://finnhub.io/register")
        print("Add to .env file: FINNHUB_API_KEY=your_key_here")
        return None
    
    try:
        symbol_upper = symbol.upper()
        
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
        
        # Get company profile for name
        try:
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol_upper}&token={api_key}"
            profile_response = requests.get(profile_url, timeout=5)
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            company_name = profile_data.get('name', symbol_upper)
        except:
            company_name = symbol_upper
        
        return {
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
