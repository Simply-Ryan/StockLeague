"""
Quick test script to verify Yahoo Finance API integration
"""
import sys
sys.path.insert(0, '.')

from helpers import lookup, get_chart_data, get_stock_news

def test_lookup():
    """Test lookup function"""
    print("Testing lookup function...")
    quote = lookup("AAPL")
    if quote:
        print(f"✓ Symbol: {quote['symbol']}")
        print(f"✓ Name: {quote['name']}")
        print(f"✓ Price: ${quote['price']:.2f}")
        print(f"✓ Change: {quote['change']:.2f} ({quote['change_percent']:.2f}%)")
        return True
    else:
        print("✗ Failed to get quote")
        return False

def test_chart_data():
    """Test get_chart_data function"""
    print("\nTesting get_chart_data function...")
    data = get_chart_data("AAPL", days=7)
    if data and data.get('dates') and data.get('prices'):
        print(f"✓ Got {len(data['dates'])} days of data")
        print(f"✓ Latest date: {data['dates'][-1]}")
        print(f"✓ Latest price: ${data['prices'][-1]:.2f}")
        return True
    else:
        print("✗ Failed to get chart data")
        return False

def test_news():
    """Test get_stock_news function"""
    print("\nTesting get_stock_news function...")
    news = get_stock_news("AAPL", limit=3)
    if news:
        print(f"✓ Got {len(news)} news articles")
        for i, article in enumerate(news, 1):
            print(f"  {i}. {article['headline'][:60]}...")
        return True
    else:
        print("✗ Failed to get news")
        return False

if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("Yahoo Finance API Integration Test")
    print("=" * 60)
    
    results = []
    results.append(test_lookup())
    time.sleep(2)  # Brief delay between tests
    results.append(test_chart_data())
    time.sleep(2)
    results.append(test_news())
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    sys.exit(0 if all(results) else 1)
