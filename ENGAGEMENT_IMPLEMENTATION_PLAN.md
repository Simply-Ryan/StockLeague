# StockLeague Engagement Features - Implementation Plan

## Selected Features Overview

This document outlines the 7 engagement features selected for implementation, prioritized by dependency and impact.

---

## 📋 Feature List & Details

### Feature 1: League-Specific Activity Feed
**Status**: Planning  
**Dependency**: None  
**Effort**: 3-4 hours  
**Impact**: High - Real-time engagement

**What**:
- Display league member activities in league context
- Filter/scope of existing /feed to show only league activities
- Show recent trades, achievements, ranking changes within league
- Auto-scroll or "New activities" badge
- Real-time updates via WebSocket

**Components**:
- New route: `/api/league/<id>/activity-feed` - Returns JSON of recent activities
- New template section: `league_detail.html` - Activity feed sidebar
- JavaScript: Poll or WebSocket for live updates
- Database: Query trades, achievements, leaderboard changes in league context

**Success Criteria**:
- ✅ Shows 10+ recent activities
- ✅ Updates in real-time or within 5 seconds
- ✅ Shows user avatars and action type with icons
- ✅ Timestamps and activity descriptions

---

### Feature 2: League-Specific Performance Metrics
**Status**: Planning  
**Dependency**: Feature 1 (database queries)  
**Effort**: 3-4 hours  
**Impact**: High - Personalization

**What**:
- Display user's performance vs. league average
- Personal stats widget on league page
- Weekly/monthly P&L in league context
- Win rate, trade frequency, best trades
- Personal rank position with trend indicator

**Components**:
- New route: `/api/league/<id>/user/<user_id>/metrics` - Personal metrics
- New template section: `league_detail.html` - User performance card
- Database calculations: Compare user stats to league average
- Chart.js: Simple sparkline for performance trend

**Metrics to Display**:
- Your portfolio value vs. league average
- Your win rate vs. league average
- Your trade frequency vs. league average
- Your current rank and trend (↑↓→)
- Weekly P&L and monthly P&L
- Best performing stock in your portfolio

**Success Criteria**:
- ✅ Shows 5+ key metrics
- ✅ Color-coded comparisons (green = above average)
- ✅ Updates after each trade
- ✅ Shows historical trend

---

### Feature 3: League Announcements & System Feed
**Status**: Planning  
**Dependency**: None  
**Effort**: 4-5 hours  
**Impact**: Medium - Communication & engagement

**What**:
- Admin-only announcement posting
- System-generated events feed (ranking changes, milestones)
- Pinned announcements at top
- Announcement history
- Auto-generated milestone notifications

**Components**:
- New table: `league_announcements` - Admin posts
- New table: `league_system_events` - Auto-generated events
- New route: `/api/league/<id>/announcements` - Get announcements
- New route: `POST /league/<id>/announce` - Admin create announcement
- New template section: `league_detail.html` - Announcements card
- Backend job: Generate system events for milestones

**Announcement Types**:
- Admin posts (editable, deletable)
- System events: "Player X joined", "Ranking changed", "Season milestone", "Achievement unlocked"
- Pinned important messages

**Success Criteria**:
- ✅ Admins can post announcements
- ✅ System auto-generates milestone events
- ✅ Announcements appear in real-time
- ✅ Announcements have edit/delete for admin
- ✅ Shows creation date and admin name

---

### Feature 4: Side-by-Side Player Comparison
**Status**: Planning  
**Dependency**: Feature 2 (metrics calculation)  
**Effort**: 3-4 hours  
**Impact**: High - Competitive engagement

**What**:
- Modal/page to compare your stats with any league member
- Side-by-side portfolio metrics
- Strategy comparison
- Win rate and performance comparison
- Achievement comparison

**Components**:
- New route: `/api/league/<id>/compare/<user1_id>/<user2_id>` - Comparison data
- New template: `league_comparison_modal.html` - Comparison display
- JavaScript: Click on any player → Opens comparison
- Database: Aggregate stats for comparison

**Comparison Metrics**:
- Portfolio value and % change
- Win rate and recent streak
- Trade frequency and average return per trade
- Best and worst performing stocks
- Achievements earned
- Risk metrics (volatility, max drawdown)

**Success Criteria**:
- ✅ Click any leaderboard player to compare
- ✅ Shows 8+ metrics side-by-side
- ✅ Visual indicators for who's ahead (↑ ↓ =)
- ✅ Color-coded comparison (green = better, red = worse)

---

### Feature 5: League Chat Integration on League Page
**Status**: Planning  
**Dependency**: Existing /chat infrastructure  
**Effort**: 2-3 hours  
**Impact**: Medium - Community retention

**What**:
- Embed league chat sidebar on league page
- Quick access to league discussion
- Show recent messages
- Post new messages without leaving page
- Unread message count badge

**Components**:
- Modify `league_detail.html` - Add chat sidebar
- Reuse existing Socket.IO chat logic
- New template partial: `_league_chat_sidebar.html`
- JavaScript: Real-time message updates with Socket.IO

**Chat Features**:
- Show 5-10 recent messages
- Quick message input
- Unread badge on league menu
- Click to expand full chat modal
- Show user avatars with messages

**Success Criteria**:
- ✅ Chat appears on league page
- ✅ Real-time message sending/receiving
- ✅ Shows recent messages on page load
- ✅ Unread count badge

---

### Feature 6: Extended League Notifications
**Status**: Planning  
**Dependency**: Feature 2 (ranking tracking)  
**Effort**: 2-3 hours  
**Impact**: Medium - Engagement loops

**What**:
- Extend existing notifications with league-specific alerts
- Alert when overtaken in leaderboard
- Achievement unlocked in league
- Friend trades in league
- Milestone reached (e.g., $15,000 portfolio)
- System announcements in notifications

**Components**:
- Modify existing `/notifications` system
- Add new notification types: `league_overtaken`, `league_achievement`, `league_milestone`, `league_announcement`
- Backend job: Compare rankings periodically, create notifications
- Database: Link notifications to leagues

**Notification Types**:
- "You've been overtaken by [Player] (now #3)"
- "[Player] unlocked [Achievement] in [League]"
- "You've reached $15,000 in [League]!"
- "New announcement in [League]"
- "Your friend [Player] bought AAPL in [League]"

**Success Criteria**:
- ✅ Notifications appear in real-time
- ✅ Shows in notifications center with league context
- ✅ Includes league name and relevant context
- ✅ Links to league page for action

---

### Feature 7: League Analytics Dashboard
**Status**: Planning  
**Dependency**: Feature 2 (calculations)  
**Effort**: 5-6 hours  
**Impact**: High - Strategic depth

**What**:
- Deep analytics view for league
- League-wide statistics and trends
- Performance distributions
- Trading pattern analysis
- Predictive insights

**Components**:
- New route: `/league/<id>/analytics` - Analytics page
- New route: `/api/league/<id>/analytics` - Analytics data
- New template: `league_analytics.html` - Dashboard
- Backend calculations: Aggregate league statistics
- Charts: Chart.js for visualizations

**Analytics Sections**:

1. **League Overview**:
   - Total members and active traders
   - Average portfolio value
   - Total capital deployed
   - League age (days)

2. **Performance Metrics**:
   - Portfolio value distribution (histogram)
   - Win rate distribution
   - Average daily return
   - Top and bottom performers

3. **Trading Patterns**:
   - Most traded stocks in league
   - Average trades per member
   - Peak trading hours
   - Trading frequency distribution

4. **Risk Analysis**:
   - Average volatility
   - Max drawdown distribution
   - Risk-reward ratio by member
   - Portfolio correlation

5. **Competitive Insight**:
   - Predicted winners based on current performance
   - Catch-up potential (distance to leader)
   - Win rate by trading style
   - Best performing strategies

6. **Leaderboards**:
   - By total return
   - By daily return
   - By consistency (lowest volatility)
   - By risk-adjusted return (Sharpe ratio)

**Success Criteria**:
- ✅ Shows 5+ chart visualizations
- ✅ League average baselines
- ✅ Real-time data updates
- ✅ Downloadable as PDF/CSV
- ✅ Performance comparisons

---

## 🎯 Implementation Order & Dependencies

```
Phase 1 (Week 1) - Foundation & Quick Wins
├── Feature 1: League Activity Feed (3-4 hrs)
├── Feature 2: League Performance Metrics (3-4 hrs)
└── Feature 3: Announcements & System Feed (4-5 hrs)
   Total: 10-13 hours

Phase 2 (Week 2) - Enhancement & Integration
├── Feature 4: Player Comparison (3-4 hrs)
├── Feature 5: Chat Integration (2-3 hrs)
└── Feature 6: Extended Notifications (2-3 hrs)
   Total: 7-10 hours

Phase 3 (Week 3) - Deep Analytics
└── Feature 7: League Analytics Dashboard (5-6 hrs)
   Total: 5-6 hours
```

---

## 📊 Database Changes Required

### New Tables

```sql
CREATE TABLE league_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER NOT NULL,
    admin_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    is_pinned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (admin_id) REFERENCES users(id)
);

CREATE TABLE league_system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_id INTEGER,
    target_id INTEGER,
    data_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (actor_id) REFERENCES users(id),
    FOREIGN KEY (target_id) REFERENCES users(id)
);
```

### New Notification Types

```python
LEAGUE_NOTIFICATIONS = {
    'league_overtaken': 'You were overtaken by {player_name} in {league_name}',
    'league_achievement': '{player_name} unlocked {achievement} in {league_name}',
    'league_milestone': 'You reached {milestone} in {league_name}',
    'league_announcement': 'New announcement in {league_name}',
    'league_ranking_change': 'You moved to #{new_rank} in {league_name}',
}
```

---

## 🔄 API Endpoints Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/league/<id>/activity-feed` | GET | Get recent league activities | Required |
| `/api/league/<id>/user/<user_id>/metrics` | GET | Get user metrics in league | Required |
| `/api/league/<id>/announcements` | GET | Get league announcements | Required |
| `POST /league/<id>/announce` | POST | Create announcement (admin only) | Admin |
| `PUT /league/<id>/announce/<announce_id>` | PUT | Edit announcement (admin) | Admin |
| `DELETE /league/<id>/announce/<announce_id>` | DELETE | Delete announcement (admin) | Admin |
| `/api/league/<id>/compare/<user1>/<user2>` | GET | Compare two users | Required |
| `/api/league/<id>/analytics` | GET | Get league analytics | Required |

---

## 📝 Template Changes

### Files to Create
- `templates/_league_activity_feed.html` - Activity feed component
- `templates/_league_performance_metrics.html` - Performance card
- `templates/_league_announcements.html` - Announcements section
- `templates/_league_chat_sidebar.html` - Chat integration
- `templates/league_comparison.html` - Comparison modal
- `templates/league_analytics.html` - Analytics dashboard

### Files to Modify
- `templates/league_detail.html` - Add activity feed, metrics, announcements, chat
- `templates/dashboard.html` - Add league-specific context
- `templates/notifications.html` - Update to show league notifications

---

## 🛠️ Implementation Checklist

### Phase 1: Foundation

#### Feature 1: League Activity Feed
- [ ] Create `GET /api/league/<id>/activity-feed` endpoint
- [ ] Query recent trades, achievements, ranking changes
- [ ] Create `_league_activity_feed.html` template
- [ ] Add JavaScript for real-time updates (polling or Socket.IO)
- [ ] Add activity feed section to league_detail.html
- [ ] Test with sample data
- [ ] Optimize queries with indexing

#### Feature 2: League Performance Metrics
- [ ] Create `GET /api/league/<id>/user/<user_id>/metrics` endpoint
- [ ] Calculate user metrics vs league averages
- [ ] Create `_league_performance_metrics.html` template
- [ ] Add metrics section to league_detail.html
- [ ] Create simple chart for performance trend
- [ ] Test with multiple users
- [ ] Cache metrics to reduce DB load

#### Feature 3: Announcements & System Feed
- [ ] Create `league_announcements` table
- [ ] Create `league_system_events` table
- [ ] Create `GET /api/league/<id>/announcements` endpoint
- [ ] Create `POST /league/<id>/announce` endpoint (admin)
- [ ] Create announcement CRUD operations
- [ ] Create `_league_announcements.html` template
- [ ] Add system event generation for milestones
- [ ] Add announcements section to league_detail.html
- [ ] Test admin announcement posting
- [ ] Test auto-generated system events

### Phase 2: Enhancement

#### Feature 4: Player Comparison
- [ ] Create `/api/league/<id>/compare/<user1>/<user2>` endpoint
- [ ] Build comparison data structure
- [ ] Create `league_comparison.html` modal template
- [ ] Add JavaScript to open comparison from leaderboard
- [ ] Style comparison for side-by-side view
- [ ] Test with different player pairs

#### Feature 5: Chat Integration
- [ ] Identify existing chat implementation in `/chat`
- [ ] Create `_league_chat_sidebar.html` template partial
- [ ] Reuse Socket.IO chat logic
- [ ] Add chat sidebar to league_detail.html
- [ ] Add unread message badge
- [ ] Test real-time message updates
- [ ] Test on mobile (responsive chat)

#### Feature 6: Extended Notifications
- [ ] Add league notification types to system
- [ ] Create background job for ranking change detection
- [ ] Implement "overtaken" notification logic
- [ ] Add notification creation for achievements
- [ ] Add notification creation for milestones
- [ ] Extend notifications page to show league context
- [ ] Test notification delivery

### Phase 3: Analytics

#### Feature 7: League Analytics Dashboard
- [ ] Create `/league/<id>/analytics` route
- [ ] Create `/api/league/<id>/analytics` endpoint
- [ ] Implement analytics calculations:
  - [ ] Portfolio distribution
  - [ ] Trading pattern analysis
  - [ ] Win rate analysis
  - [ ] Risk metrics
  - [ ] Predictive insights
- [ ] Create `league_analytics.html` template
- [ ] Add Chart.js visualizations
- [ ] Create 5+ different chart types
- [ ] Add filter/timeframe controls
- [ ] Test performance with large datasets
- [ ] Optimize queries and caching

---

## 📈 Success Metrics

**Phase 1 Complete**:
- ✅ Activity feed showing real-time activities
- ✅ Performance metrics displayed for each user
- ✅ Announcements system working
- ✅ Baseline engagement metrics collected

**Phase 2 Complete**:
- ✅ Player comparison accessible from leaderboard
- ✅ Chat integrated and real-time
- ✅ Notifications extended with league context
- ✅ User session time on league page increases

**Phase 3 Complete**:
- ✅ Analytics dashboard fully functional
- ✅ 5+ different data visualizations
- ✅ Strategic insights available to users
- ✅ Leaderboards extended to multiple dimensions

**Overall Goals**:
- 🎯 Average time on league page: 5+ minutes
- 🎯 Daily return visits to leagues: 3x baseline
- 🎯 Chat messages in leagues: 10+ per day
- 🎯 Feature adoption: 80%+ of users

---

## 📚 Technical Notes

### Reusing Existing Infrastructure
- Socket.IO: Already integrated for real-time updates
- Chat system: Existing at `/chat`, can integrate
- Notifications: System exists, extend with league types
- Database: Strong foundation, add new tables as needed
- Charts: Use Chart.js (lightweight)

### Performance Considerations
- Cache league statistics (refresh every 5 mins)
- Index queries on `league_id`, `user_id`, timestamps
- Paginate activity feeds (20 items per page)
- Lazy load analytics charts
- Use database views for complex aggregations

### Mobile Responsiveness
- Activity feed: Vertical scrolling
- Metrics: Stack on mobile
- Chat: Sidebar converts to modal on mobile
- Analytics: Responsive charts with Chart.js
- Comparison: Stack columns on small screens

---

## 🚀 Next Steps

1. **Review & Approve Plan** - Get stakeholder sign-off on features and schedule
2. **Setup Development Branch** - Create feature branches for each phase
3. **Begin Phase 1** - Start with Activity Feed implementation
4. **Daily Progress Updates** - Track completion of checklist items
5. **User Testing** - Gather feedback after Phase 1

