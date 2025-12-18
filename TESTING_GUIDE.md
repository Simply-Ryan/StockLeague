# Quick Navigation Testing Guide

## URL Routes Reference

### Public Routes (No Login Required)
- `http://localhost:5000/` → **Home Page** (Landing page)
- `http://localhost:5000/home` → **Home Page** (Alias)

### Private Routes (Login Required)
- `http://localhost:5000/dashboard` → **Dashboard** (Trading portfolio)
- `http://localhost:5000/index` → **Redirects to Dashboard** (Backwards compatibility)

## Navbar Navigation

### Unauthenticated User
- **Logo** (StockLeague): Routes to `/home`
- Navbar shows: Login/Register buttons

### Authenticated User
- **Logo** (StockLeague): Routes to `/home`
- **Dashboard Icon** (chart-pie): Routes to `/dashboard`
- **Navbar Brand**: Routes to `/home`
- Other nav items available (Trade dropdown, Leagues, etc.)

## Testing Checklist

### Home Page Tests
- [ ] Visit `/` → Home page loads with hero section
- [ ] Visit `/home` → Same home page loads
- [ ] Check "Get Started Free" button (unauthenticated) works
- [ ] Check "Go to Dashboard" button (authenticated) routes to `/dashboard`
- [ ] Verify all feature cards display correctly
- [ ] Check responsive design on mobile (use browser dev tools)
- [ ] Verify hero image/gradient loads

### Dashboard Page Tests
- [ ] Visit `/dashboard` (logged in) → Dashboard loads
- [ ] Verify portfolio stats display (Total Value, Cash, Holdings, Today's Change)
- [ ] Check holdings table shows your stocks with prices and gain/loss
- [ ] Verify transaction history displays recent trades
- [ ] Check portfolio performance chart renders (if history exists)
- [ ] Test empty states (no holdings, no transactions)
- [ ] Verify quick action buttons work (Buy, Sell, Watchlist, Leagues)
- [ ] Check "Add Stocks" button in holdings section

### Navigation Tests
- [ ] Click navbar brand (StockLeague) → Routes to `/home`
- [ ] Click dashboard icon in navbar → Routes to `/dashboard`
- [ ] Click "Buy Stocks" button → Routes to `/buy`
- [ ] Click "Explore" button → Routes to `/explore`
- [ ] Test on mobile navbar (hamburger menu)

### Authentication Tests
- [ ] Visit `/dashboard` without login → Redirects to `/login`
- [ ] Visit `/index` without login → Redirects to `/login`
- [ ] After login, verify session works correctly
- [ ] Logout and verify redirects to login

### Visual/UX Tests
- [ ] Check color scheme consistency
- [ ] Verify hover effects on buttons
- [ ] Check spacing and alignment on all screen sizes
- [ ] Verify icon visibility and clarity
- [ ] Check text readability and contrast
- [ ] Test on dark/light theme modes (if available)

## Browser Console Checks
After visiting pages, open browser DevTools (F12) and check:
- [ ] No JavaScript errors in console
- [ ] No network errors (404s, 500s)
- [ ] Chart renders without errors (if portfolio history exists)
- [ ] Responsive design adjusts correctly on resize

## Common Issues & Fixes

### Home Page Not Loading
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check Flask app is running
- Verify `/home` and `/` routes are in app.py

### Dashboard Not Loading After Login
- Clear browser cache
- Verify `@login_required` decorator is working
- Check session cookie is set (should see in DevTools Storage)
- Verify portfolio data query works (check Flask logs)

### Navbar Not Showing Dashboard Icon
- Clear browser cache
- Verify layout.html changes (brand href, icon, text)
- Check user is logged in (navbar shows dashboard link only when authenticated)

### Chart Not Rendering
- Check portfolio history exists (at least 2 data points)
- Verify Chart.js library loads from CDN
- Check browser console for JavaScript errors
- Verify `portfolio_dates` and `portfolio_values` are passed to template

## Quick Start Commands

```bash
# In project directory
cd /workspaces/codespaces-blank/StockLeague

# Activate virtual environment
source venv/bin/activate

# Run Flask app
python app.py

# Or with Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run

# App runs on http://localhost:5000
```

## Key Files Modified
1. `app.py` - Added home(), home_alias(), dashboard() routes; updated index() to redirect
2. `templates/layout.html` - Updated navbar brand href and dashboard link
3. `templates/home.html` - Created new landing page (public route)
4. `templates/dashboard.html` - Created new dashboard page (private route)

## Reference Variables in Dashboard Template

Access these variables in `dashboard.html`:
```jinja
{{ stocks }}              - List of stock holdings
{{ cash | usd }}         - Formatted cash balance
{{ grand_total | usd }}  - Total portfolio value
{{ total_value | usd }}  - Stock holdings value
{{ total_gain_loss | usd }} - Dollar gain/loss
{{ total_percent_change }}  - Percent change
{{ transactions }}       - List of recent trades
{{ portfolio_history }}  - Historical data for chart
{{ active_context }}     - Current portfolio context
```

## Performance Optimization Notes
- Dashboard caches popular stocks query
- Uses real-time price lookups only when needed
- Chart data (portfolio_dates/values) pre-calculated in backend
- Watchlist queries optimized to count only
