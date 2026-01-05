# Portfolio Chart Fix - Analysis & Implementation Plan

## Problem Diagnosis

**Status**: Portfolio Performance Chart in `/dashboard` is broken

### Root Cause Analysis

1. **Chart Data Dependency**
   - Chart displays in `templates/dashboard.html` lines 460-694
   - Requires `portfolio_history`, `portfolio_dates`, `portfolio_values` to be passed from Flask route
   - Route: `/dashboard` (lines 1620-1715 in `app.py`)

2. **Data Flow**
   ```
   app.py route /dashboard
   ├─ Calls: db.get_portfolio_history(user_id, days=30)
   ├─ Database: portfolio_snapshots table
   ├─ Processing: Extract dates and values from snapshots
   └─ Template: render with portfolio_dates, portfolio_values
   ```

3. **Likely Issues**
   - Empty `portfolio_snapshots` table (no snapshots exist)
   - Chart data never being populated (snapshots never created)
   - Chart rendering despite empty data (condition check fails)
   - Theme color contrast not adapting properly

### Current Code Flow

**Dashboard Route** (`app.py` line 1620):
```python
portfolio_history = db.get_portfolio_history(user_id, days=30)
portfolio_dates = []
portfolio_values = []
if portfolio_history:
    for entry in portfolio_history:
        timestamp = entry.get("timestamp", "")
        date_str = timestamp.split()[0] if timestamp else ""
        portfolio_dates.append(date_str)
        portfolio_values.append(entry.get("total_value", 0))
```

**Template Check** (`templates/dashboard.html` line 461):
```html
{% if portfolio_history and portfolio_history|length > 1 %}
    <!-- Show chart -->
{% endif %}
```

**Chart Initialization** (`templates/dashboard.html` line 587-690):
- Gets CSS variables for theme colors
- Uses `--primary-color`, `--text-secondary`, `--bg-primary`
- Creates Chart.js line chart with portfolio values

## Solution Strategy

### Phase 1: Ensure Portfolio Snapshots Are Created
**Problem**: Empty portfolio_snapshots table = no chart data
**Solution**: Create snapshots on trading events and periodically

1. **Hook into Trading Operations**
   - After each successful trade (buy/sell)
   - Create snapshot via `db.create_snapshot(user_id, total_value, cash, stocks_json)`

2. **Create Initial Snapshots** (Backfill)
   - When user logs in, check if they have any snapshots
   - If not, create initial snapshot with current portfolio value
   - Generate historical snapshots (simulate last 30 days)

3. **Fix** in `app.py` buy/sell routes:
   ```python
   # After successful trade
   from datetime import datetime, timedelta
   import json
   
   # Calculate total portfolio value
   total_value = cash + sum(stock['price'] * stock['shares'] for stock in stocks)
   
   # Create snapshot
   stocks_json = json.dumps([{'symbol': s['symbol'], 'shares': s['shares']} for s in stocks])
   db.create_snapshot(user_id, total_value, cash, stocks_json)
   ```

### Phase 2: Fix Theme Color Contrast
**Problem**: Chart colors might not contrast well with theme background

**Solution**:
1. Ensure CSS variables are defined in layout.html
2. Add fallback colors if variables not found
3. Test both light and dark themes
4. Fix grid line color (currently 8% opacity on light theme might be hard to see)

**Code Fix** in `templates/dashboard.html`:
```javascript
// Get computed style for color - handle both light/dark themes
const computedStyle = getComputedStyle(document.documentElement);
const primaryColor = computedStyle.getPropertyValue('--primary-color').trim() || '#1976d2';
const textSecondary = computedStyle.getPropertyValue('--text-secondary').trim() || '#666';

// IMPROVED: Better grid colors based on theme
const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark' 
                    || document.body.classList.contains('dark-theme');
const gridColor = isDarkTheme ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
```

### Phase 3: Ensure Data Loading and Display
**Problem**: Chart might render but show empty/incomplete data

**Solution**:
1. Add debug logging to check data is being passed
2. Ensure dates and values arrays are non-empty
3. Add error handling for missing snapshots
4. Show helpful message if no chart data available

**Code Addition**:
```javascript
console.log('Portfolio Chart Debug:', {
    history: portfolio_history,
    datesCount: dates.length,
    valuesCount: values.length
});

if (dates.length === 0 || values.length === 0) {
    console.warn('No portfolio history data to display');
    chartCanvas.parentElement.innerHTML = 
        '<div class="alert alert-info">Not enough data to display chart. Trade some stocks!</div>';
    return;
}
```

## Implementation Steps

### Step 1: Create `create_snapshot()` method in DatabaseManager (if not exists)
Check `database/db_manager.py` for existing `create_snapshot()` method.
If missing, add:
```python
def create_snapshot(self, user_id, total_value, cash, stocks_json):
    """Create a portfolio snapshot for historical tracking"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO portfolio_snapshots (user_id, total_value, cash, stocks_json, timestamp)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (user_id, total_value, cash, stocks_json))
    conn.commit()
    conn.close()
```

### Step 2: Hook Snapshot Creation into Buy/Sell Routes
- Modify `buy()` route (line 1748+)
- Modify `sell()` route (line ~2000+)
- After successful trade: create snapshot

### Step 3: Add Backfill Logic
- In dashboard route, if no snapshots exist:
  - Create initial snapshot
  - Generate synthetic historical data for chart display

### Step 4: Fix Theme Color Handling
- Update chart initialization script in `templates/dashboard.html`
- Test with both light and dark themes
- Ensure grid lines, text, and borders are visible

### Step 5: Add Error Handling & Logging
- Add console logs for debugging
- Show helpful messages if data is missing
- Test on multiple devices/browsers

## Files to Modify

1. **database/db_manager.py**
   - Ensure `create_snapshot()` method exists
   - Ensure `get_portfolio_history()` returns correct data

2. **app.py**
   - `/dashboard` route (line 1620)
   - `/buy` route (line 1748)
   - `/sell` route (line ~2000)
   - Add snapshot creation after successful trades

3. **templates/dashboard.html**
   - Lines 460-694 (chart HTML and JS)
   - Fix theme color handling
   - Add error state display
   - Add debug logging

## Testing Checklist

- [ ] Chart displays when user has portfolio snapshots
- [ ] Chart shows correct dates (30-day history)
- [ ] Chart shows correct values (total portfolio value over time)
- [ ] Colors work in light theme
- [ ] Colors work in dark theme
- [ ] Chart responsive on mobile
- [ ] Grid lines visible and not distracting
- [ ] No console errors
- [ ] Graceful fallback when no data available
- [ ] Performance acceptable (< 1s load time)

## Success Criteria

✅ Chart displays portfolio performance for last 30 days
✅ Colors adapt to theme (light/dark)
✅ Grid lines are visible but subtle
✅ Works on desktop and mobile
✅ No console errors
✅ Shows helpful message if no data
✅ Performance: < 1 second to render
✅ All data points display correctly

---

**Status**: Ready for implementation
**Effort**: 2-3 hours (diagnosis + fix + testing)
**Priority**: HIGH (user-facing feature)
