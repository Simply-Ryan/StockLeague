# Real-Time WebSocket Trading Features

## Overview
StockLeague now includes comprehensive real-time trading capabilities powered by WebSocket technology. Users experience live updates without page refreshes for stock prices, portfolio values, and trade executions.

## Features Implemented

### 1. Live Stock Price Updates
- **Frequency**: Updates every 30 seconds via background thread
- **Data Provided**:
  - Current price
  - Price change ($ and %)
  - Volume
  - OHLC data (Open, High, Low, Close)
  - Timestamp
- **Auto-subscription**: Automatically subscribes to stocks in user's portfolio
- **Visual Indicators**: 
  - Green dot next to live prices
  - Animated flash effect on price updates
  - "LIVE" badge on portfolio page

### 2. Real-Time Portfolio Updates
- **Triggers**: Emitted immediately after buy/sell transactions
- **Updates**:
  - Total cash balance
  - Total portfolio value
  - Individual stock holdings
- **Visual Effects**:
  - Smooth glow animation on value changes
  - No page refresh required
  - Instant feedback

### 3. Order Execution Notifications
- **Notification Types**:
  - Buy orders (green toast)
  - Sell orders (blue toast)
- **Information Displayed**:
  - Transaction type (Buy/Sell)
  - Symbol and shares
  - Price per share
  - Total transaction amount
  - Timestamp
- **Toast Notifications**: Auto-dismiss after 5 seconds with manual close option

### 4. WebSocket API Endpoints

#### Client → Server Events
- `subscribe_stock`: Subscribe to real-time updates for a symbol
- `unsubscribe_stock`: Unsubscribe from updates
- `get_chart_data`: Request candlestick chart data

#### Server → Client Events
- `stock_update`: Live price and market data
- `portfolio_update`: Portfolio value changes
- `order_executed`: Trade execution notification
- `chart_data`: Historical OHLC data for charts
- `chart_error`: Error fetching chart data

### 5. REST API Endpoints
- `GET /api/portfolio/value`: Get current portfolio value with live prices
  - Returns: cash, total_value, holdings[], timestamp

## Technical Architecture

### Backend Components

#### WebSocket Handlers (`app.py`)
```python
@socketio.on('connect')
- Joins user to personal room (user_{user_id})
- Emits initial portfolio state

@socketio.on('subscribe_stock')
- Adds client to stock room
- Tracks subscription in stock_subscriptions dict

@socketio.on('unsubscribe_stock')
- Removes client from stock room

@socketio.on('get_chart_data')
- Fetches candlestick data via get_chart_data()
- Emits chart_data event
```

#### Background Price Updater
```python
def background_price_updater():
    """Updates stock prices every 30 seconds"""
    - Iterates through stock_subscriptions
    - Calls lookup() for latest quote
    - Emits stock_update with OHLCV data
    - Runs continuously in separate thread
```

#### Trade Routes Enhancement
Both `/buy` and `/sell` routes now emit:
1. `portfolio_update` event with updated cash/value/stocks
2. `order_executed` event with transaction details

### Frontend Components

#### Real-Time JavaScript (`static/js/realtime.js`)
- **Socket Management**: Initializes Socket.IO connection
- **Subscription Tracking**: Maintains subscribedSymbols Set
- **Event Handlers**:
  - `stock_update`: Updates price displays with animations
  - `portfolio_update`: Updates cash and total value
  - `order_executed`: Shows toast notifications
- **Utility Functions**:
  - `formatCurrency()`: USD formatting
  - `formatVolume()`: Human-readable volume (M/K)
  - `animateValueChange()`: CSS animation trigger
  - `showToast()`: Bootstrap toast creator
- **Auto-Subscribe**: DOMContentLoaded listener subscribes to visible stocks

#### CSS Animations (`static/css/styles.css`)
```css
.price-update: Flash effect on price changes
.value-change: Glow effect on value updates
.live-indicator: Pulsing green dot animation
Toast notifications: Backdrop blur and shadows
```

#### Template Updates

**layout.html**
- Includes realtime.js script for logged-in users
- Maintains backwards compatibility with legacy stock updates

**index.html (Portfolio)**
- "LIVE" indicator alert box
- Live badge on performance chart
- ID="portfolio-value" for real-time updates
- Green dots next to stock prices
- data-symbol attributes on price elements

## User Experience

### Before (Traditional)
1. User buys stock
2. Page redirects/reloads
3. Sees updated portfolio after full page load
4. Must manually refresh to see price changes

### After (Real-Time)
1. User buys stock
2. Instant toast notification appears
3. Portfolio value updates immediately (no refresh)
4. Stock prices update automatically every 30 seconds
5. Visual animations highlight changes

## Performance Considerations

### Optimization Strategies
1. **Selective Updates**: Only updates subscribed stocks
2. **Room-Based Broadcasting**: Users only receive relevant updates
3. **Caching**: lookup() function uses 30-second quote cache
4. **Throttling**: Background updater limited to 30-second intervals
5. **Cleanup**: Unsubscribes on page unload

### Scalability
- **Current Load**: Suitable for 100s of concurrent users
- **Bottleneck**: Finnhub API rate limits (60 calls/minute free tier)
- **Solution**: Upgrade to paid Finnhub plan or implement request queuing

## Browser Compatibility
- **WebSocket Support**: All modern browsers (Chrome, Firefox, Safari, Edge)
- **Fallback**: Socket.IO automatically falls back to polling if WebSocket unavailable
- **Minimum Versions**: Chrome 16+, Firefox 11+, Safari 7+, Edge 12+

## Configuration

### WebSocket Settings (app.py)
```python
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    logger=True,
    engineio_logger=True
)
```

### Update Frequency
Change background updater interval in `app.py`:
```python
def background_price_updater():
    while True:
        time.sleep(30)  # Change this value (seconds)
```

## Testing Checklist

### Manual Testing
- [ ] Buy stock → See toast notification
- [ ] Buy stock → Portfolio value updates without refresh
- [ ] Sell stock → See toast notification
- [ ] Sell stock → Cash balance updates immediately
- [ ] Open portfolio → Prices update every 30 seconds
- [ ] Price update → Animated flash effect
- [ ] Multiple tabs → All tabs receive updates
- [ ] Disconnect WiFi → Reconnect → Updates resume

### Automated Testing (Future)
- Unit tests for WebSocket handlers
- Integration tests for buy/sell emissions
- Load testing for concurrent users

## Troubleshooting

### Issue: Updates not appearing
**Solutions**:
1. Check browser console for connection errors
2. Verify Socket.IO script loaded: `https://cdn.socket.io/4.7.2/socket.io.min.js`
3. Check Flask logs for "Client connected" messages
4. Ensure `socketio.run()` used instead of `app.run()`

### Issue: Duplicate subscriptions
**Solutions**:
1. Clear localStorage: `localStorage.clear()`
2. Check subscribedSymbols Set in console: `window.realtimeTrading.subscribedSymbols`
3. Manually unsubscribe: `window.realtimeTrading.unsubscribeFromStock('AAPL')`

### Issue: High server load
**Solutions**:
1. Increase update interval (30s → 60s)
2. Limit max subscriptions per user
3. Implement user-based rate limiting
4. Use Redis for session storage and pub/sub

## Future Enhancements

### Planned Features
1. **Live Candlestick Charts**: Real-time chart updates with Chart.js financial plugin
2. **Order Book Display**: Live bid/ask spreads
3. **Trade Alerts**: Customizable price alerts with push notifications
4. **Multi-Symbol Charts**: Compare multiple stocks in real-time
5. **Voice Assistant**: Trade execution via voice commands
6. **Mobile App**: Native iOS/Android with persistent WebSocket connections

### Advanced Features
1. **Level 2 Data**: Market depth and order flow
2. **Options Chain**: Real-time options pricing
3. **News Feed**: Live financial news with sentiment analysis
4. **Backtesting**: Test strategies with historical data streaming
5. **Paper Trading Mode**: Practice with simulated real-time data

## Security Considerations

### Current Implementation
- User-specific rooms prevent cross-user data leakage
- @login_required decorator on all sensitive endpoints
- Input validation on symbol subscriptions
- Room-based authorization (users can only join own room)

### Additional Recommendations
1. Rate limiting on WebSocket events (prevent spam)
2. Max subscriptions per user (prevent resource exhaustion)
3. CSRF tokens on REST endpoints
4. WSS (WebSocket Secure) in production with SSL certificate
5. Content Security Policy headers

## Deployment Notes

### Production Checklist
- [ ] Set `cors_allowed_origins` to specific domain (not "*")
- [ ] Enable WebSocket compression
- [ ] Use Redis for Socket.IO adapter (multi-server support)
- [ ] Configure Nginx proxy with WebSocket support
- [ ] Enable eventlet/gevent worker pool
- [ ] Set up monitoring for WebSocket connections
- [ ] Configure load balancer sticky sessions

### Nginx Configuration
```nginx
location / {
    proxy_pass http://localhost:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

## Code Examples

### Subscribe to Stock on Page Load
```javascript
document.addEventListener('DOMContentLoaded', function() {
    window.realtimeTrading.subscribeToStock('AAPL');
});
```

### Manually Emit Portfolio Update (Backend)
```python
socketio.emit('portfolio_update', {
    'cash': user["cash"],
    'total_value': portfolio_value,
    'stocks': [{'symbol': s["symbol"], 'shares': s["shares"]} for s in stocks]
}, room=f'user_{user_id}')
```

### Custom Toast Notification (Frontend)
```javascript
showToast(`
    <div class="toast align-items-center text-white bg-success border-0">
        <div class="toast-body">Trade executed successfully!</div>
    </div>
`);
```

## Maintenance

### Monitoring Metrics
- Active WebSocket connections
- Messages per second
- Average message latency
- Error rate
- Memory usage per connection

### Log Files
- Flask logs: Connection/disconnection events
- Socket.IO logs: Event emissions and room joins
- Error logs: Failed subscriptions and API errors

## Conclusion
The real-time WebSocket trading features provide a modern, responsive user experience that eliminates the need for manual page refreshes. Users receive instant feedback on trades and continuously updated market data, creating a professional trading platform feel.

**Status**: ✅ Fully Implemented
**Version**: 1.0
**Last Updated**: 2024
