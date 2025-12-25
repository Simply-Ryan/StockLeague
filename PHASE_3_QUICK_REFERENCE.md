# Phase 3: Quick Reference Guide

## 🚀 Quick Start

### 1. Apply Database Schema
```bash
cd /workspaces/StockLeague
python migrate_phase_3.py --apply
```

### 2. Test the APIs
```bash
# Get activity feed
curl http://localhost:5000/api/engagement/leagues/1/activity-feed

# Get user metrics
curl http://localhost:5000/api/engagement/leagues/1/user/1/metrics

# Get announcements
curl http://localhost:5000/api/engagement/leagues/1/announcements
```

### 3. Run Tests
```bash
python -m pytest tests/test_engagement_features.py -v
```

---

## 📁 Files Created/Modified

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| `engagement_routes.py` | API | 870 | Flask routes for engagement features |
| `league_activity_feed.py` | Service | 420 | Activity feed management |
| `league_performance_metrics.py` | Service | 600 | Performance calculations |
| `league_announcements.py` | Service | 480 | Announcements management |
| `phase_3_schema.py` | Database | 220 | Schema migrations |
| `migrate_phase_3.py` | Tool | 320 | Migration utilities |
| `tests/test_engagement_features.py` | Tests | 680 | Unit tests (40+) |
| `app.py` | Modified | 4 lines | Blueprint registration |

---

## 🔗 API Endpoints

### Activity Feed
- `GET /api/engagement/leagues/<id>/activity-feed` - Get activities
- `GET /api/engagement/leagues/<id>/activity-stats` - Get stats

### Metrics
- `GET /api/engagement/leagues/<id>/user/<id>/metrics` - User metrics

### Announcements
- `GET /api/engagement/leagues/<id>/announcements` - Get announcements
- `POST /api/engagement/leagues/<id>/announcements` - Create announcement

### Analytics
- `GET /api/engagement/leagues/<id>/compare/<id>/<id>` - Compare players
- `GET /api/engagement/leagues/<id>/analytics` - League analytics

### Notifications
- `GET /api/engagement/notifications` - Get notifications
- `POST /api/engagement/notifications/<id>/read` - Mark as read
- `POST /api/engagement/notifications/read-all` - Mark all as read

---

## 💻 Code Examples

### Log Activity
```python
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

### Get Metrics
```python
from league_performance_metrics import LeaguePerformanceMetrics

metrics_service = LeaguePerformanceMetrics()
success, metrics, error = metrics_service.get_user_league_metrics(
    league_id=1,
    user_id=1
)
print(f"Portfolio: ${metrics['portfolio_value']}")
print(f"Rank: {metrics['rank']}")
print(f"Win Rate: {metrics['win_rate']}")
```

### Create Announcement
```python
from league_announcements import LeagueAnnouncements

announcements_service = LeagueAnnouncements()
success, announcement_id, error = announcements_service.create_announcement(
    league_id=1,
    title='Important Update',
    content='New rules effective tomorrow',
    author_id=1,
    author_username='admin'
)
```

---

## 🗂️ Database Tables

### league_activity_log
Stores all league member activities (trades, achievements, rankings, joins)
- **Columns**: id, league_id, user_id, activity_type, description, metadata, created_at
- **Index**: (league_id, created_at DESC)

### league_announcements
League announcements and updates
- **Columns**: id, league_id, author_id, title, content, pinned, created_at, updated_at
- **Index**: (league_id, pinned DESC, created_at DESC)

### league_system_events
Important league events
- **Columns**: id, league_id, event_type, description, user_id, created_at
- **Index**: (league_id, created_at DESC)

### league_performance_snapshots
Daily performance snapshots for metrics history
- **Columns**: id, league_id, user_id, snapshot_date, portfolio_value, daily_pl, total_pl, win_rate, trade_count, created_at
- **Unique**: (league_id, user_id, snapshot_date)

### league_analytics
League-wide analytics summaries
- **Columns**: id, league_id, analytics_date, total_volume, total_trades, average_portfolio, most_traded_stock, average_win_rate, created_at
- **Unique**: (league_id, analytics_date)

---

## 🧪 Test Examples

```bash
# Run all tests
python -m pytest tests/test_engagement_features.py -v

# Run specific test class
python -m pytest tests/test_engagement_features.py::TestLeagueActivityFeed -v

# Run with coverage report
python -m pytest tests/test_engagement_features.py --cov=league_activity_feed --cov=league_performance_metrics --cov=league_announcements

# Run specific test
python -m pytest tests/test_engagement_features.py::TestLeagueActivityFeed::test_log_trade_activity -v
```

---

## 🔧 Migration Commands

```bash
# Apply migrations
python migrate_phase_3.py --apply

# Verify schema created correctly
python migrate_phase_3.py --verify

# Print detailed schema info
python migrate_phase_3.py --info

# Rollback (use with caution!)
python migrate_phase_3.py --rollback
```

---

## 📊 Activity Types

- `trade_buy` - User bought stock
- `trade_sell` - User sold stock
- `ranking_change` - User's rank changed
- `achievement_unlocked` - User unlocked achievement
- `member_joined` - New member joined league
- `system_event` - System event (season start, etc.)

---

## 🔒 Permission Model

| Operation | Required Role | Notes |
|-----------|---------------|-------|
| Log Activity | Any league member | Automatic for trades/achievements |
| Create Announcement | Admin/Owner | Can pin announcements |
| Edit Announcement | Author/Admin | Author or league admin |
| Delete Announcement | Author/Admin | Author or league admin |
| Pin Announcement | Admin/Owner | Admin/owner only |
| Get Metrics | Any league member | Compare any member |
| Get Analytics | Any league member | League-wide view |

---

## ⚡ Performance Tips

1. **Paginate Activity Feeds**: Always use limit/offset (max 100 per page)
2. **Cache Metrics**: Performance snapshots can be cached hourly
3. **Index Usage**: Queries automatically use indexes on league_id + created_at
4. **Activity Cleanup**: Use `cleanup_old_activities()` to archive old data

---

## 🐛 Troubleshooting

### Migration Fails
```bash
# Verify database connection
sqlite3 database/stocks.db ".tables"

# Check existing tables
python migrate_phase_3.py --verify

# Get detailed info
python migrate_phase_3.py --info
```

### API Returns 404
- Ensure league_id exists in database
- Verify user is league member
- Check activity feed is not filtered out

### Slow Queries
- Verify indexes exist: `python migrate_phase_3.py --info`
- Check row counts in activity_log table
- Consider archiving old activities

---

## 📝 Logging

Logs are generated for:
- Activity logging operations
- Announcement CRUD operations
- Metrics calculations
- System events
- Migration operations

Enable debug logging:
```python
import logging
logging.getLogger('league_metrics').setLevel(logging.DEBUG)
logging.getLogger('league_announcements').setLevel(logging.DEBUG)
logging.getLogger('engagement_routes').setLevel(logging.DEBUG)
```

---

## 🔗 Related Files

- Engagement routes: `engagement_routes.py`
- Activity feed service: `league_activity_feed.py`
- Metrics service: `league_performance_metrics.py`
- Announcements service: `league_announcements.py`
- Database schema: `phase_3_schema.py`
- Migration tool: `migrate_phase_3.py`
- Tests: `tests/test_engagement_features.py`
- UI Component: `templates/components/league_activity_feed.html`

---

## 📞 Common Tasks

### Get Last 20 Activities
```python
activity_feed = LeagueActivityFeed()
success, activities, error = activity_feed.get_league_activity_feed(
    league_id=1,
    limit=20,
    offset=0
)
```

### Calculate Risk Metrics
```python
metrics = LeaguePerformanceMetrics()
success, risk, error = metrics.calculate_risk_metrics(
    league_id=1,
    user_id=1
)
print(f"Portfolio Concentration: {risk['portfolio_concentration']}")
print(f"Volatility: {risk['profit_volatility']}")
```

### Get All Announcements
```python
announcements = LeagueAnnouncements()
success, ann_list, error = announcements.get_league_announcements(
    league_id=1,
    limit=100
)
# Pinned announcements appear first
```

### Get Most Active Users
```python
activity_feed = LeagueActivityFeed()
success, stats, error = activity_feed.get_recent_activity_stats(
    league_id=1,
    hours=24
)
# Returns top users, activity breakdown, etc.
```

---

Version: 1.0  
Last Updated: January 2025  
Status: ✅ Ready for Production
