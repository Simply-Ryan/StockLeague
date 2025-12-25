# Phase 3 Integration Guide for Developers

## Overview
This guide explains how to integrate Phase 3 engagement features into the StockLeague application.

---

## ✅ Pre-Integration Checklist

- [x] Database schema migrations created (`phase_3_schema.py`)
- [x] Migration tool created (`migrate_phase_3.py`)
- [x] Service layer implemented (3 services)
- [x] API routes implemented (`engagement_routes.py`)
- [x] Unit tests created (40+ tests)
- [x] Blueprint registered in `app.py`
- [ ] Database migrations applied
- [ ] Frontend components integrated
- [ ] Testing in staging environment

---

## 🔧 Step 1: Apply Database Migrations

### Command
```bash
cd /workspaces/StockLeague
python migrate_phase_3.py --apply
```

### What This Does
1. Creates 5 new database tables
2. Creates 6 performance indexes
3. Sets up foreign key relationships
4. Validates schema integrity

### Verify Migration
```bash
python migrate_phase_3.py --verify
```

### Expected Output
```
✓ Table 'league_activity_log' exists with 7 columns
✓ Table 'league_announcements' exists with 8 columns
✓ Table 'league_system_events' exists with 5 columns
✓ Table 'league_performance_snapshots' exists with 10 columns
✓ Table 'league_analytics' exists with 8 columns
✓ All required tables exist!
```

---

## 🚀 Step 2: Start Application

### Python
```bash
cd /workspaces/StockLeague
python app.py
```

### The Application Will:
1. Import all engagement modules
2. Register the engagement blueprint
3. Initialize database connections
4. Start Flask server on port 5000

### Check Routes Are Registered
```bash
# In Python console
from app import app
print([str(rule) for rule in app.url_map.iter_rules() if 'engagement' in str(rule)])
```

---

## 🧪 Step 3: Test API Endpoints

### Test Activity Feed Endpoint
```bash
curl -X GET "http://localhost:5000/api/engagement/leagues/1/activity-feed"
```

Expected response:
```json
{
  "success": true,
  "activities": [],
  "count": 0,
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

### Test Other Endpoints
```bash
# Get activity stats
curl -X GET "http://localhost:5000/api/engagement/leagues/1/activity-stats"

# Get user metrics
curl -X GET "http://localhost:5000/api/engagement/leagues/1/user/1/metrics"

# Get announcements
curl -X GET "http://localhost:5000/api/engagement/leagues/1/announcements"

# Get league analytics
curl -X GET "http://localhost:5000/api/engagement/leagues/1/analytics"
```

---

## 📝 Step 4: Create Test Activities

### Via Python (Command Line)
```python
from league_activity_feed import LeagueActivityFeed
from database.db_manager import DatabaseManager

db = DatabaseManager()
activity_feed = LeagueActivityFeed(db)

# Log a trade activity
success, activity_id, error = activity_feed.log_trade_activity(
    league_id=1,
    user_id=1,
    username='testuser',
    trade_type='buy',
    symbol='AAPL',
    shares=10,
    price=150.00
)

if success:
    print(f"Activity logged: {activity_id}")
else:
    print(f"Error: {error}")
```

### Via API
```bash
# Use the activity feed endpoint to retrieve activities
curl -X GET "http://localhost:5000/api/engagement/leagues/1/activity-feed?limit=20"
```

---

## 🌐 Step 5: Integrate Frontend

### Include Activity Feed Component
In `league_detail.html`:
```html
{% include "components/league_activity_feed.html" %}
```

With data attribute:
```html
<div data-league-id="{{ league.id }}">
    {% include "components/league_activity_feed.html" %}
</div>
```

### JavaScript Integration
```html
<script>
document.addEventListener('DOMContentLoaded', function() {
    const leagueId = document.querySelector('[data-league-id]').getAttribute('data-league-id');
    
    // Load initial activities
    fetch(`/api/engagement/leagues/${leagueId}/activity-feed?limit=20`)
        .then(response => response.json())
        .then(data => {
            console.log('Activities:', data.activities);
            // Render activities to DOM
        });
});
</script>
```

---

## 📊 Step 6: Connect Business Logic

### Log Activities on Trade
In your trade execution code:
```python
from league_activity_feed import LeagueActivityFeed

def execute_trade(user_id, league_id, symbol, shares, price, trade_type):
    # Execute trade...
    
    # Log activity
    activity_feed = LeagueActivityFeed()
    activity_feed.log_trade_activity(
        league_id=league_id,
        user_id=user_id,
        username=get_username(user_id),
        trade_type=trade_type,
        symbol=symbol,
        shares=shares,
        price=price
    )
```

### Log Achievement Unlocks
```python
def unlock_achievement(league_id, user_id, achievement_name):
    from league_activity_feed import LeagueActivityFeed
    
    activity_feed = LeagueActivityFeed()
    activity_feed.log_achievement_unlocked(
        league_id=league_id,
        user_id=user_id,
        username=get_username(user_id),
        achievement_name=achievement_name,
        achievement_description=f"Unlocked: {achievement_name}"
    )
```

### Log Ranking Changes
```python
def update_league_rankings(league_id):
    from league_activity_feed import LeagueActivityFeed
    
    activity_feed = LeagueActivityFeed()
    
    # Get old rankings, calculate new rankings...
    
    for user_id in league_members:
        if old_rank[user_id] != new_rank[user_id]:
            activity_feed.log_ranking_change(
                league_id=league_id,
                user_id=user_id,
                username=get_username(user_id),
                old_rank=old_rank[user_id],
                new_rank=new_rank[user_id]
            )
```

---

## 🎯 Step 7: Display Metrics Dashboard

### In League Dashboard Template
```html
<div class="metrics-section">
    <h3>Top Performers</h3>
    <div id="performance-metrics">
        <!-- Populated by JavaScript -->
    </div>
</div>

<script>
fetch(`/api/engagement/leagues/{{ league.id }}/analytics?days=30`)
    .then(response => response.json())
    .then(data => {
        document.getElementById('performance-metrics').innerHTML = `
            <p>Total Volume: $${data.analytics.total_volume}</p>
            <p>Avg Win Rate: ${(data.analytics.average_win_rate * 100).toFixed(1)}%</p>
            <p>Most Traded: ${data.analytics.most_traded_stock}</p>
        `;
    });
</script>
```

---

## 🔔 Step 8: Setup Notifications

### Log System Events
```python
from league_announcements import LeagueAnnouncements

announcements = LeagueAnnouncements()
announcements.log_system_event(
    league_id=league_id,
    event_type='season_started',
    description='New trading season has begun!',
    user_id=None  # System event, no specific user
)
```

### Create Announcements
```python
# Admin creates important announcement
announcements.create_announcement(
    league_id=league_id,
    title='Important: Rules Update',
    content='All members must review the new trading rules.',
    author_id=admin_user_id,
    author_username='league_admin',
    pinned=True  # Pin to top
)
```

---

## 🚨 Step 9: Error Handling

### Handle API Errors
```python
from error_handling import ValidationError, AuthorizationError

try:
    success, metrics, error = metrics_service.get_user_league_metrics(
        league_id=1,
        user_id=1
    )
    
    if not success:
        logger.error(f"Metrics error: {error}")
        # Handle error gracefully
        raise ValidationError(error)
        
except AuthorizationError as e:
    # User not authorized
    return apology("You don't have permission to view this", 403)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return apology("An error occurred", 500)
```

---

## 📈 Step 10: Monitor Performance

### Query Performance Monitoring
```python
import time
from league_performance_metrics import LeaguePerformanceMetrics

metrics_service = LeaguePerformanceMetrics()

start = time.time()
success, breakdown, error = metrics_service.get_league_performance_breakdown(league_id=1)
elapsed = time.time() - start

if elapsed > 0.5:  # Alert if slow
    logger.warning(f"Slow query: league_breakdown took {elapsed:.2f}s")
```

### Database Size Monitoring
```python
import sqlite3
import os

db_size = os.path.getsize('database/stocks.db') / (1024 * 1024)  # MB
conn = sqlite3.connect('database/stocks.db')
cursor = conn.cursor()

# Check activity log size
cursor.execute('SELECT COUNT(*) FROM league_activity_log')
activity_count = cursor.fetchone()[0]

print(f"Database: {db_size:.1f} MB")
print(f"Activities: {activity_count:,}")
```

---

## 🔄 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing: `pytest tests/test_engagement_features.py`
- [ ] Database backed up
- [ ] Staging environment tested
- [ ] API documentation reviewed
- [ ] Performance tested with real data

### Deployment Steps
```bash
# 1. Backup database
cp database/stocks.db database/stocks.db.backup

# 2. Apply migrations
python migrate_phase_3.py --apply

# 3. Verify schema
python migrate_phase_3.py --verify

# 4. Run tests
pytest tests/test_engagement_features.py -v

# 5. Start application
python app.py
```

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Check API response times
- [ ] Verify activity feed working
- [ ] Test announcements creation
- [ ] Monitor database size growth

---

## 🆘 Troubleshooting

### Issue: Tables Not Created
```bash
python migrate_phase_3.py --info
# Check if tables are listed
# If not, run: python migrate_phase_3.py --apply
```

### Issue: API Returns 500 Error
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check app logs for the specific error
# Common issues:
# - Database not migrated
# - User not league member
# - Activity type not recognized
```

### Issue: Slow Performance
```bash
# Check for missing indexes
python migrate_phase_3.py --info

# Archive old activities
python -c "
from league_activity_feed import LeagueActivityFeed
from datetime import datetime, timedelta

activity_feed = LeagueActivityFeed()
cutoff_date = datetime.now() - timedelta(days=90)
activity_feed.cleanup_old_activities(cutoff_date)
"
```

---

## 📚 Additional Resources

- **API Documentation**: See docstrings in `engagement_routes.py`
- **Service Documentation**: See docstrings in service files
- **Database Schema**: See `phase_3_schema.py`
- **Tests**: See `tests/test_engagement_features.py`
- **Quick Reference**: See `PHASE_3_QUICK_REFERENCE.md`

---

## 🎓 Example: Complete Integration

### 1. Apply Schema
```bash
python migrate_phase_3.py --apply
```

### 2. Log Activity from Trade
```python
# In your trade execution function
from league_activity_feed import LeagueActivityFeed

activity_feed = LeagueActivityFeed()
success, activity_id, error = activity_feed.log_trade_activity(
    league_id=1,
    user_id=1,
    username='trader1',
    trade_type='buy',
    symbol='AAPL',
    shares=10,
    price=150.00
)
```

### 3. Display Feed in Template
```html
<div data-league-id="1">
    {% include "components/league_activity_feed.html" %}
</div>
```

### 4. Create Dashboard Widget
```javascript
// Get metrics and display
fetch('/api/engagement/leagues/1/user/1/metrics')
    .then(r => r.json())
    .then(data => {
        document.getElementById('metrics').innerHTML = `
            Rank: ${data.metrics.rank}
            Win Rate: ${(data.metrics.win_rate * 100).toFixed(1)}%
        `;
    });
```

---

## 📞 Support

For questions or issues:
1. Check `PHASE_3_IMPLEMENTATION_COMPLETE.md` for detailed info
2. Review test cases in `tests/test_engagement_features.py`
3. Check API docstrings in `engagement_routes.py`
4. Review service docstrings in individual service files

---

**Status**: Ready for Production Integration  
**Version**: 1.0  
**Last Updated**: January 2025
