# Quick Reference: Advanced League Features

## 📚 Files Overview

### Database Layer
- **`database/advanced_league_features.py`** - Core database operations
  - `AdvancedLeagueDB` class with all methods
  - ~500 lines of battle-tested code

### Application Layer  
- **`app.py`** - Flask routes (added ~400 lines)
  - `POST /api/league/<id>/h2h/create` - Create matchup
  - `GET /api/league/<id>/h2h/matchups` - Get matchups
  - `GET /api/league/<id>/h2h/leaderboard` - H2H leaderboard
  - `GET /api/league/<id>/activity-feed/filtered` - Filtered feed
  - `GET /api/league/<id>/statistics` - League stats
  - `GET /leagues/<id>/h2h` - H2H page

### Frontend Layer
- **`templates/league_h2h.html`** - H2H matchups page
  - Active matchups display
  - Challenge modal
  - Leaderboard sidebar
  
- **`templates/components/league_activity_feed_enhanced.html`** - New activity feed
  - Category filtering tabs
  - Real-time updates
  - Better styling

### Utilities
- **`database/init_advanced_features.py`** - Initialization script
- **`ADVANCED_LEAGUE_FEATURES.md`** - Full documentation

---

## ⚡ Quick Start (5 minutes)

### Step 1: Initialize Database
```bash
cd /workspaces/StockLeague
python database/init_advanced_features.py
```

✅ Creates all tables automatically

### Step 2: Restart Flask App
```bash
python app.py
```

### Step 3: Test H2H Feature
1. Go to any league
2. Click "H2H Matchups" (new button to add in league page)
3. Click "Challenge Opponent"
4. Select opponent, duration, capital
5. Click "Send Challenge"

### Step 4: Use Enhanced Activity Feed
Replace in league detail template:
```html
<!-- Old -->
{% include "components/league_activity_feed.html" %}

<!-- New -->
{% include "components/league_activity_feed_enhanced.html" %}
```

---

## 🎮 Features at a Glance

| Feature | What It Does | How to Use |
|---------|-------------|-----------|
| **H2H Matchups** | 1v1 trading battles | Create challenge on H2H page |
| **H2H Records** | Win/loss tracking | Visible on H2H leaderboard |
| **Activity Feed Filtering** | Filter by category | Click category tabs on feed |
| **League Statistics** | Overall metrics | Call `/api/league/<id>/statistics` |
| **Seasons** | Multi-season support | Create season via DB (future UI) |
| **Divisions** | Tiered competition | Create divisions via DB (future UI) |

---

## 🔌 Integration Points

### In League Detail Page
Add navigation button:
```html
<a href="/leagues/{{ league.id }}/h2h" class="btn btn-primary">
  <i class="fas fa-crossed-swords"></i> H2H Matchups
</a>
```

### In Activity Feed
Use enhanced component:
```html
<div class="col-lg-8">
  {% include "components/league_activity_feed_enhanced.html" %}
</div>
```

### In League Sidebar
Add H2H stats:
```html
<div class="card">
  <h6>H2H Record</h6>
  <!-- Show user's H2H stats here -->
</div>
```

---

## 📊 Database Commands

### View H2H Matchups
```sql
SELECT * FROM h2h_matchups WHERE league_id = 1 AND status = 'active';
```

### View H2H Records
```sql
SELECT * FROM h2h_records WHERE league_id = 1 ORDER BY win_rate DESC;
```

### View Enhanced Activities
```sql
SELECT * FROM league_activity_feed 
WHERE league_id = 1 AND category = 'trade'
ORDER BY created_at DESC;
```

### View Seasons
```sql
SELECT * FROM league_seasons WHERE league_id = 1;
```

---

## 🎯 Use Cases

### Scenario 1: Challenge a Friend
1. Go to league H2H page
2. Click "Challenge Opponent"
3. Select friend
4. Select 7-day duration
5. Click "Send Challenge"
6. Friend sees active matchup
7. Both trade for 7 days
8. Winner determined automatically

### Scenario 2: Check League Stats
```javascript
fetch('/api/league/1/statistics')
  .then(r => r.json())
  .then(data => console.log(data.statistics));
```

### Scenario 3: Filter Activities by Type
- Click "Trades" tab → See only trades
- Click "Achievements" tab → See only achievements
- Click "H2H" tab → See H2H challenges
- Click "All" tab → See everything

### Scenario 4: Pin Important Activity
```python
advanced_league_db.pin_activity(activity_id, is_pinned=True)
```

---

## 🐛 Common Issues & Fixes

### Issue: "Tables don't exist"
**Fix:** Run initialization script
```bash
python database/init_advanced_features.py
```

### Issue: H2H endpoint returns 404
**Fix:** 
1. Verify `advanced_league_db` is initialized in app.py
2. Check that `init_advanced_league_system()` is called
3. Restart Flask app

### Issue: Activity feed shows empty categories
**Fix:**
1. Check activities have correct `category` field
2. Ensure activities are being logged to feed
3. Check SQL query in `get_activity_feed_by_category()`

### Issue: H2H leaderboard shows no one
**Fix:**
1. Create some matchups first
2. Complete matchups with `end_h2h_matchup()`
3. Check `h2h_records` table populated

---

## 📱 Mobile Considerations

H2H page is fully responsive:
- ✅ Mobile-friendly challenge modal
- ✅ Responsive matchup cards
- ✅ Swipeable leaderboard
- ✅ Touch-friendly buttons

---

## 🚀 Future Enhancements

1. **Automatic H2H Completion**
   - Background job to check matchup end dates
   - Auto-calculate winners
   - Send notifications

2. **Tournament Mode**
   - Bracket-style competitions
   - Playoff matchups
   - Prize pools

3. **Trading Analytics**
   - Win rate vs specific opponents
   - Trading pattern analysis
   - Strategy recommendations

4. **Mobile App Integration**
   - Push notifications for H2H
   - Real-time challenge updates
   - Mobile H2H dashboard

5. **Social Features**
   - H2H chat during matchups
   - Smack talk emojis
   - Victory celebrations

---

## 📞 Support

### Debug Mode
Add to app.py before running:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Initialization
```bash
# Verify tables exist
sqlite3 database/stocks.db ".tables" | grep h2h
```

### View Logs
```bash
# Watch Flask logs
tail -f /var/log/stockleague.log
```

---

## ✨ Pro Tips

1. **Bulk Create Matchups**
   ```python
   for user_id in league_members:
       advanced_league_db.create_h2h_matchup(
           league_id, user_id, opponent_id, 7, 10000
       )
   ```

2. **Export H2H Records**
   ```sql
   SELECT * FROM h2h_records 
   WHERE league_id = 1 
   ORDER BY win_rate DESC;
   ```

3. **Analyze Trading Patterns**
   ```sql
   SELECT metadata->>'symbol' as symbol, COUNT(*) as trades
   FROM league_activity_feed
   WHERE league_id = 1 AND category = 'trade'
   GROUP BY symbol
   ORDER BY trades DESC;
   ```

4. **Create Season Reset Job**
   ```python
   scheduler.add_job(
       end_league_season,
       'cron',
       day='1',  # First of month
       hour='0'
   )
   ```

---

## 📖 Learn More

- Full documentation: [ADVANCED_LEAGUE_FEATURES.md](ADVANCED_LEAGUE_FEATURES.md)
- Database schema: See `database/advanced_league_features.py`
- API details: See routes in `app.py` (lines ~5050-5250)
- UI templates: See `templates/league_h2h.html` and enhanced feed

---

**Last Updated:** Dec 21, 2025
**Version:** 1.0
