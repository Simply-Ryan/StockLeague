# Advanced League Features & Enhanced Activity Feed

## 🎯 Overview

This document describes the new advanced league features and enhanced activity feed system for StockLeague.

### Features Implemented

#### 1. **Head-to-Head (H2H) Matchups** ⚔️
Challenge specific league members to 1v1 trading battles with:
- Customizable duration (7, 14, 30 days)
- Equal starting capital
- Real-time tracking of both players' portfolios
- Winner determination based on final portfolio value
- H2H Record tracking (W-L-D statistics)
- H2H Leaderboard showing win rates

#### 2. **Enhanced Activity Feed** 📊
Real-time activity tracking with:
- **Filtering by Category:**
  - Trades
  - Achievements
  - Rankings/Leaderboard changes
  - H2H Challenges
  - Milestones
  - System announcements

- **Priority & Pinning:**
  - Pinnable activities for important events
  - Priority levels for featured activities

- **Better Metadata:**
  - Symbol, shares, prices for trades
  - Achievement details
  - Player mentions
  - Custom metadata support

#### 3. **League Seasons** 🏆
Multi-season support for leagues with:
- Automatic season resets
- Season-specific standings
- Prize pools per season
- Theme customization
- Final rankings recording

#### 4. **Division/Tier System** 🎖️
Competitive tiers within leagues:
- Multiple divisions per league per season
- Automatic ranking by tier
- Division-specific leaderboards
- Tier promotion/demotion logic

#### 5. **League Statistics** 📈
Comprehensive league-wide metrics:
- Member count and activity
- Top performers
- Average portfolio values
- Trading patterns
- Risk metrics

---

## 🗄️ Database Schema

### New Tables

#### H2H Matchups
```sql
h2h_matchups (
  id INTEGER PRIMARY KEY,
  league_id INTEGER,
  challenger_id INTEGER,
  opponent_id INTEGER,
  duration_days INTEGER,
  starting_capital NUMERIC,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  status TEXT ('active', 'completed'),
  challenger_final_value NUMERIC,
  opponent_final_value NUMERIC,
  winner_id INTEGER
)
```

#### H2H Records
```sql
h2h_records (
  league_id INTEGER,
  user_id INTEGER,
  wins INTEGER,
  losses INTEGER,
  draws INTEGER,
  win_rate NUMERIC
)
```

#### League Seasons
```sql
league_seasons (
  id INTEGER PRIMARY KEY,
  league_id INTEGER,
  season_number INTEGER,
  name TEXT,
  status TEXT ('active', 'completed'),
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  prize_pool NUMERIC
)
```

#### Season Standings
```sql
season_standings (
  id INTEGER PRIMARY KEY,
  season_id INTEGER,
  user_id INTEGER,
  final_rank INTEGER,
  final_value NUMERIC,
  badges_earned TEXT
)
```

#### League Divisions
```sql
league_divisions (
  id INTEGER PRIMARY KEY,
  league_id INTEGER,
  season_number INTEGER,
  name TEXT,
  tier_level INTEGER,
  min_score NUMERIC,
  max_score NUMERIC
)
```

#### Enhanced Activity Feed
Enhanced `league_activity_feed` table with:
- `category` - Activity category (trade, achievement, ranking, etc.)
- `priority` - Priority level for sorting
- `is_pinned` - Whether activity is pinned to top
- `mentions_json` - Mentioned player IDs

---

## 🔌 API Endpoints

### H2H Matchup Endpoints

#### Create H2H Matchup
```
POST /api/league/<id>/h2h/create
Content-Type: application/json

{
  "opponent_id": 123,
  "duration_days": 7,
  "starting_capital": 10000
}

Response: { "matchup_id": 42, "status": "created" }
```

#### Get User's H2H Matchups
```
GET /api/league/<id>/h2h/matchups?status=active

Response: {
  "matchups": [
    {
      "id": 42,
      "challenger_id": 1,
      "opponent_id": 2,
      "opponent_name": "Alice",
      "duration_days": 7,
      "status": "active",
      "started_at": "2025-12-21T10:00:00",
      "is_challenger": true
    }
  ]
}
```

#### Get H2H Leaderboard
```
GET /api/league/<id>/h2h/leaderboard?limit=50

Response: {
  "leaderboard": [
    {
      "user_id": 1,
      "username": "TopPlayer",
      "wins": 15,
      "losses": 3,
      "draws": 1,
      "total_matchups": 19,
      "win_rate": 78.95
    }
  ]
}
```

### Activity Feed Endpoints

#### Get Filtered Activity Feed
```
GET /api/league/<id>/activity-feed/filtered?category=trade&limit=20&offset=0

Response: {
  "activities": [
    {
      "id": 101,
      "user_id": 1,
      "username": "Player1",
      "activity_type": "trade",
      "title": "Bought 10 shares of AAPL",
      "description": "Purchased at $150.25",
      "category": "trade",
      "priority": 0,
      "is_pinned": false,
      "metadata": {
        "symbol": "AAPL",
        "action": "BUY",
        "shares": 10,
        "price": 150.25
      },
      "created_at": "2025-12-21T10:30:00"
    }
  ],
  "category": "trade"
}
```

### Statistics Endpoints

#### Get League Statistics
```
GET /api/league/<id>/statistics

Response: {
  "statistics": {
    "member_count": 25,
    "activity_count": 342,
    "top_trader": {
      "user_id": 1,
      "username": "TopTrader",
      "score": 45000
    },
    "avg_portfolio_value": 12500.50
  }
}
```

---

## 🎨 UI Components

### H2H Matchups Page
**Route:** `GET /leagues/<id>/h2h`

Features:
- Active matchups display with vs. visualizations
- Real-time portfolio value tracking
- Completed matchups history
- H2H Leaderboard sidebar
- Challenge opponent modal

### Enhanced Activity Feed Component
**Template:** `templates/components/league_activity_feed_enhanced.html`

Features:
- Category-based filtering tabs
- Real-time activity updates
- Load more pagination
- Responsive design
- Activity detail cards

---

## 🚀 Getting Started

### 1. Initialize Database Tables

```bash
cd /workspaces/StockLeague
python database/init_advanced_features.py
```

This will create all necessary tables and print a confirmation.

### 2. Update League Detail Page

Add H2H button to league navigation:

```html
<a href="/leagues/{{ league.id }}/h2h" class="btn btn-primary">
  <i class="fas fa-crossed-swords"></i> H2H Matchups
</a>
```

### 3. Use Enhanced Activity Feed

Replace the old activity feed component with the new one:

```html
{% include "components/league_activity_feed_enhanced.html" %}
```

---

## 💻 Developer Guide

### Creating H2H Matchups Programmatically

```python
from database.advanced_league_features import AdvancedLeagueDB

advanced_league_db = AdvancedLeagueDB(db)

# Create matchup
matchup_id = advanced_league_db.create_h2h_matchup(
    league_id=5,
    challenger_id=10,
    opponent_id=20,
    duration_days=7,
    starting_capital=10000
)

# End matchup
advanced_league_db.end_h2h_matchup(
    matchup_id=matchup_id,
    challenger_final=11500,
    opponent_final=10800
)
```

### Adding Categorized Activities

```python
# Add activity with category
activity_id = advanced_league_db.add_categorized_activity(
    league_id=5,
    activity_type='trade',
    title='John bought 10 shares of AAPL',
    description='Purchased at $150.25',
    user_id=10,
    category='trade',
    priority=0,
    metadata={
        'symbol': 'AAPL',
        'shares': 10,
        'price': 150.25
    }
)

# Pin important activity
advanced_league_db.pin_activity(activity_id, is_pinned=True)
```

### Getting League Statistics

```python
stats = advanced_league_db.get_league_statistics(league_id=5)
print(stats)
# Output:
# {
#   'member_count': 25,
#   'activity_count': 342,
#   'top_trader': {...},
#   'avg_portfolio_value': 12500.50
# }
```

---

## 📱 Frontend Usage

### Creating H2H Challenge via JavaScript

```javascript
async function challengeOpponent(leagueId, opponentId) {
  const response = await fetch(`/api/league/${leagueId}/h2h/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      opponent_id: opponentId,
      duration_days: 7,
      starting_capital: 10000
    })
  });
  
  const data = await response.json();
  console.log('Matchup created:', data.matchup_id);
}
```

### Displaying H2H Leaderboard

```javascript
async function displayH2HLeaderboard(leagueId) {
  const response = await fetch(`/api/league/${leagueId}/h2h/leaderboard`);
  const data = await response.json();
  
  data.leaderboard.forEach((record, index) => {
    console.log(`#${index + 1}: ${record.username} - ${record.win_rate}% WR`);
  });
}
```

### Filtering Activity Feed

```javascript
async function getTradeActivities(leagueId) {
  const response = await fetch(
    `/api/league/${leagueId}/activity-feed/filtered?category=trade&limit=20`
  );
  const data = await response.json();
  return data.activities;
}
```

---

## 🧪 Testing

### Test H2H Matchup Creation

```bash
# Create test matchup
curl -X POST http://localhost:5000/api/league/1/h2h/create \
  -H "Content-Type: application/json" \
  -d '{
    "opponent_id": 2,
    "duration_days": 7,
    "starting_capital": 10000
  }'
```

### Test Activity Feed Filtering

```bash
# Get trade activities
curl http://localhost:5000/api/league/1/activity-feed/filtered?category=trade&limit=10
```

### Test League Statistics

```bash
# Get league stats
curl http://localhost:5000/api/league/1/statistics
```

---

## 🔒 Security Considerations

- All endpoints require login (`@login_required`)
- League membership verified before returning data
- Admin-only operations protected (future: season creation, etc.)
- Input validation on all parameters
- SQL injection prevention via parameterized queries

---

## 📊 Performance Optimization

- **Indexes:** Created on:
  - `h2h_matchups(league_id, status)`
  - `h2h_records(league_id, win_rate DESC)`
  - `league_activity_feed(league_id, category, created_at DESC)`

- **Caching:** Statistics can be cached for 5-minute intervals

- **Pagination:** Activity feed uses offset-limit pagination (max 100 items)

---

## 🐛 Troubleshooting

### Tables Not Created
```bash
# Re-run initialization
python database/init_advanced_features.py
```

### H2H Matchup Returns 404
- Verify league exists: `SELECT * FROM leagues WHERE id = ?`
- Verify both players are league members
- Check opponent_id is valid user

### Activity Feed Empty
- Check activities exist in DB: `SELECT COUNT(*) FROM league_activity_feed WHERE league_id = ?`
- Verify `category` column exists on `league_activity_feed` table

---

## 🚀 Next Steps

1. **Automated H2H Matchup Completion**
   - Add background job to auto-complete matchups after duration expires
   - Calculate final portfolio values

2. **H2H Notifications**
   - Notify opponent when challenged
   - Notify winner when matchup completes

3. **Division Promotions**
   - Auto-promote/demote players based on score
   - Season reset logic

4. **Analytics Dashboard**
   - Visualize league trends over time
   - Player performance comparisons

5. **Mobile Optimization**
   - Touch-friendly H2H interface
   - Push notifications for matchups

---

## 📝 Version History

- **v1.0** (Dec 21, 2025) - Initial release
  - H2H Matchups
  - Enhanced Activity Feed
  - League Seasons
  - Division System
  - League Statistics

---

## 👥 Support

For issues or questions about advanced league features, create an issue on the repository or contact the development team.
