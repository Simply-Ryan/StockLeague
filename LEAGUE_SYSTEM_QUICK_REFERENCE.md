# League System - Quick Reference Guide

**Quick links to key documentation and code**

---

## 📚 Documentation Files

| Document | Purpose | Best For |
|----------|---------|----------|
| [LEAGUE_SYSTEM_COMPLETE_DOCUMENTATION.md](LEAGUE_SYSTEM_COMPLETE_DOCUMENTATION.md) | Complete reference | Architects, new devs, deep understanding |
| [LEAGUE_SYSTEM_IMPROVEMENTS.md](LEAGUE_SYSTEM_IMPROVEMENTS.md) | Fixes implemented | QA, code reviewers, DevOps |
| [LEAGUE_SYSTEM_REVIEW_SUMMARY.md](LEAGUE_SYSTEM_REVIEW_SUMMARY.md) | Executive summary | Quick overview, project status |
| This file | Quick reference | Developers needing quick lookup |

---

## 🗄️ Database Tables

### Core League Tables
- **leagues** - Main league configuration
- **league_members** - Who is in each league
- **league_portfolios** - Cash balance per user per league
- **league_holdings** - Stock positions per user per league
- **league_transactions** - Trade history
- **league_activity_feed** - Event log
- **league_seasons** - Multi-season support
- **league_member_stats** - Performance metrics

---

## 🔑 Key Methods

### League Management
```python
league_id, code = db.create_league(name, description, creator_id, ...)
success = db.join_league(league_id, user_id)
db.leave_league(league_id, user_id)  # Handles ownership transfer & auto-delete
leagues = db.get_user_leagues(user_id)
league = db.get_league(league_id)
league = db.get_league_by_invite_code(invite_code)
```

### Membership
```python
members = db.get_league_members(league_id)
count = db.get_league_member_count(league_id)
db.remove_league_member(league_id, user_id)
db.set_league_member_admin(league_id, user_id, is_admin=True)
```

### Portfolio Management
```python
portfolio = db.get_league_portfolio(league_id, user_id)
db.create_league_portfolio(league_id, user_id, starting_cash)
holdings = db.get_league_holdings(league_id, user_id)
holding = db.get_league_holding(league_id, user_id, symbol)
db.update_league_holding(league_id, user_id, symbol, shares_delta, price)
db.update_league_cash(league_id, user_id, new_cash)
value = db.calculate_league_portfolio_value(league_id, user_id, price_lookup_func)
```

### Trading
```python
is_valid, error = db.validate_league_trade(league_id, user_id, symbol, action, shares, price)
db.record_league_transaction(league_id, user_id, symbol, shares, price, type, fee)
```

### Scoring & Ranking
```python
db.update_league_scores(league_id)  # Old version
db.update_league_scores_v2(league_id, price_lookup_func)  # New version
leaderboard = db.get_league_leaderboard(league_id)
```

### Seasons
```python
db.start_league_season(league_id, duration_days=30)
db.end_league_season(league_id)
```

### Activity
```python
activity_id = db.add_league_activity(league_id, activity_type, title, description, user_id, metadata)
activities = db.get_league_activity_feed(league_id, limit=20, offset=0)
```

---

## 🛣️ Flask Routes

### League Pages
- `GET /leagues` - List all leagues
- `GET /leagues/<id>` - View league details
- `GET /leagues/<id>/preview` - JSON preview

### League Management
- `GET/POST /leagues/create` - Create new league
- `POST /leagues/join` - Join a league
- `POST /leagues/<id>/leave` - Leave league

### Trading
- `GET/POST /leagues/<id>/trade` - Trade stocks

### Admin
- `POST /leagues/<id>/end` - End season
- `POST /leagues/<id>/restart` - Start new season
- `POST /leagues/<id>/activate` - Activate league

### API
- `GET /api/leagues/<id>/activity` - Activity feed JSON
- `POST /leagues/<id>/track_view` - Analytics

---

## ⚙️ What's New (Fixed)

### Fix 1: Portfolio Value with Missing Prices
**What**: If stock price unavailable, now uses cost basis instead of ignoring position  
**Where**: `calculate_league_portfolio_value()` line 1745  
**Why**: Prevents artificially low portfolio values

### Fix 2: Comprehensive Cascade Deletes
**What**: When last member leaves, ALL related data is deleted properly  
**Where**: `leave_league()` lines 1234-1269  
**Why**: Prevents orphaned database records

### Fix 3: Trade Validation Method
**What**: New `validate_league_trade()` method for centralized validation  
**Where**: `database/db_manager.py` lines 1773-1813  
**Why**: Cleaner code, consistent error handling

### Fix 4: Better Error Messages
**What**: Error messages now include specific values  
**Old**: "Insufficient funds"  
**New**: "Insufficient funds. Have $1,000.00, need $15,025.00"  
**Why**: Users know exactly what's wrong

### Fix 5: Member Count Helper
**What**: New `get_league_member_count()` method  
**Where**: `database/db_manager.py` lines 1142-1155  
**Why**: Simplifies code, enables future features

---

## 🧪 Testing Essentials

### Critical Paths to Test
1. Create league → Join → Trade → Leave
2. Leave as owner → Ownership transfer
3. Leave as last member → Auto-delete
4. Insufficient funds error
5. Portfolio value with missing price

### Quick Test Command
```bash
python -m pytest tests/test_leagues.py -v
```

---

## 📋 Common Scenarios

### User Joins League
```python
league = db.get_league(league_id)
success = db.join_league(league_id, user_id)
if success:
    db.create_league_portfolio(league_id, user_id, league['starting_cash'])
    flash("Successfully joined league!")
```

### User Buys Stock
```python
is_valid, error = db.validate_league_trade(league_id, user_id, "AAPL", "BUY", 100, 150.25)
if not is_valid:
    return apology(error, 400)

cost = 100 * 150.25
portfolio = db.get_league_portfolio(league_id, user_id)
db.update_league_cash(league_id, user_id, portfolio['cash'] - cost)
db.update_league_holding(league_id, user_id, "AAPL", 100, 150.25)
db.update_league_scores_v2(league_id, lookup)
```

### User Leaves League
```python
db.leave_league(league_id, user_id)
league = db.get_league(league_id)
if league is None:
    flash("League was deleted (no members remaining)")
else:
    flash("You have left the league")
```

---

## 🚀 Performance Tips

1. **Cache price lookups** - Don't call lookup() multiple times per request
2. **Batch updates** - Update multiple scores in single transaction
3. **Index queries** - Add indexes for frequently queried columns
4. **Lazy load** - Only fetch data you need in the view

---

## 🔍 Debugging Tips

### Check League Status
```python
league = db.get_league(league_id)
print(f"Active: {league['is_active']}")
print(f"Members: {db.get_league_member_count(league_id)}")
print(f"Creator: {league['creator_id']}")
```

### Check Portfolio
```python
portfolio = db.get_league_portfolio(league_id, user_id)
print(f"Cash: ${portfolio['cash']}")
holdings = db.get_league_holdings(league_id, user_id)
print(f"Holdings: {holdings}")
```

### Check Activity
```python
activities = db.get_league_activity_feed(league_id, limit=5)
for activity in activities:
    print(f"{activity['title']} - {activity['created_at']}")
```

---

## ⚠️ Common Pitfalls

❌ **Don't**: Forget to create portfolio when user joins
✅ **Do**: Call `create_league_portfolio()` in join handler

❌ **Don't**: Only check cash before BUY, ignore shares before SELL
✅ **Do**: Use `validate_league_trade()` for complete validation

❌ **Don't**: Update portfolio cash without updating league_holdings
✅ **Do**: Always update both together (use transaction)

❌ **Don't**: Call `lookup()` multiple times in loop
✅ **Do**: Cache results or batch queries

❌ **Don't**: Forget to update scores after trade
✅ **Do**: Call `update_league_scores_v2()` after every trade

---

## 📞 Need Help?

### Architecture Questions
→ See LEAGUE_SYSTEM_COMPLETE_DOCUMENTATION.md

### Implementation Details
→ See LEAGUE_SYSTEM_IMPROVEMENTS.md

### Testing & QA
→ See LEAGUE_SYSTEM_IMPROVEMENTS.md Testing section

### Quick Examples
→ See "Common Scenarios" section above

---

## Version Info

- **Last Updated**: December 19, 2025
- **Documentation Version**: 1.0
- **All Fixes**: Implemented and Ready
- **Status**: Ready for Production

