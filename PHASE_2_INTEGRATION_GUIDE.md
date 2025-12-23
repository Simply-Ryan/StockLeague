# Phase 2 Implementation Quick Reference

## Quick Start - Backend Integration Checklist

### Portfolio Analytics Dashboard Integration

#### 1. Create API Endpoint
```python
@app.route('/api/portfolio/analytics', methods=['GET'])
@login_required
def get_portfolio_analytics():
    """Return comprehensive portfolio analytics data"""
    user = get_current_user()
    
    # Calculate metrics
    portfolio_value = db.get_portfolio_value(user.id)
    total_return = db.calculate_total_return(user.id)
    sharpe_ratio = calculate_sharpe_ratio(user.id)
    win_rate = db.calculate_win_rate(user.id)
    
    # Get holdings
    stocks = db.get_user_stocks(user.id)
    
    # Get historical data
    portfolio_history = db.get_portfolio_history(user.id, days=365)
    
    return jsonify({
        'portfolio_value': portfolio_value,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'avg_trade_size': calculate_avg_trade_size(user.id),
        'trading_days': count_trading_days(user.id),
        'stocks': stocks,
        'portfolio_history': portfolio_history,
        'sector_data': get_sector_breakdown(user.id),
    })
```

#### 2. Route to Template
```python
@app.route('/portfolio/analytics', methods=['GET'])
@login_required
def portfolio_analytics():
    """Display enhanced portfolio analytics dashboard"""
    data = get_portfolio_analytics()  # Call API endpoint
    return render_template('portfolio_analytics_enhanced.html', **data)
```

#### 3. Add Database Methods (if not exists)
```python
class DatabaseManager:
    def get_portfolio_history(self, user_id, days=365):
        """Get daily portfolio values for the past N days"""
        query = """
        SELECT date(created_at) as date, portfolio_value
        FROM portfolio_history
        WHERE user_id = ? AND created_at > date('now', '-' || ? || ' days')
        GROUP BY date(created_at)
        ORDER BY date ASC
        """
        return self.fetch_all(query, (user_id, days))
    
    def get_sector_breakdown(self, user_id):
        """Get portfolio breakdown by sector"""
        # Implement sector grouping logic
        pass
```

---

### League Management UI Integration

#### 1. Create League Member API
```python
@app.route('/api/leagues/<int:league_id>/members', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_league_members(league_id):
    """Manage league members"""
    user = get_current_user()
    league = db.get_league(league_id)
    
    # Verify user is owner/admin
    if not is_league_admin(user.id, league_id):
        return {'error': 'Unauthorized'}, 403
    
    if request.method == 'GET':
        members = db.get_league_members(league_id)
        return jsonify(members)
    
    elif request.method == 'POST':
        action = request.json.get('action')
        member_id = request.json.get('member_id')
        
        if action == 'promote':
            db.update_member_role(league_id, member_id, 'admin')
        elif action == 'demote':
            db.update_member_role(league_id, member_id, 'member')
        elif action == 'remove':
            db.remove_league_member(league_id, member_id)
        
        return {'success': True}
```

#### 2. Create Invite Code API
```python
@app.route('/api/leagues/<int:league_id>/invite-code', methods=['GET', 'POST'])
@login_required
def manage_invite_code(league_id):
    """Get or regenerate league invite code"""
    user = get_current_user()
    
    if not is_league_admin(user.id, league_id):
        return {'error': 'Unauthorized'}, 403
    
    if request.method == 'GET':
        code = db.get_league_invite_code(league_id)
        return jsonify({
            'code': code,
            'share_url': f"https://stockleague.com/join/{code}"
        })
    
    elif request.method == 'POST':
        new_code = generate_invite_code()
        db.update_league_invite_code(league_id, new_code)
        return jsonify({'code': new_code})
```

#### 3. Route to Template
```python
@app.route('/leagues/<int:league_id>/manage', methods=['GET'])
@login_required
def league_management(league_id):
    """Display league management interface"""
    user = get_current_user()
    league = db.get_league(league_id)
    members = db.get_league_members(league_id)
    is_owner = league.creator_id == user.id
    
    return render_template('league_management.html',
        league=league,
        members=members,
        is_owner=is_owner,
        league_id=league_id
    )
```

---

### Achievement System Integration

#### 1. Create Achievement API
```python
@app.route('/api/achievements', methods=['GET'])
@login_required
def get_achievements():
    """Get all achievements with user progress"""
    user = get_current_user()
    
    achievements = db.get_all_achievements()
    user_progress = db.get_user_achievements(user.id)
    
    # Organize by category
    by_category = {
        'trading': [],
        'wealth': [],
        'league': [],
        'special': []
    }
    
    for achievement in achievements:
        category = achievement['category']
        progress = user_progress.get(achievement['id'], {})
        
        achievement['unlocked'] = progress.get('unlocked', False)
        achievement['unlocked_date'] = progress.get('unlocked_date')
        achievement['current_progress'] = progress.get('current_progress', 0)
        
        by_category[category].append(achievement)
    
    return jsonify(by_category)
```

#### 2. Achievement Leaderboard API
```python
@app.route('/api/achievements/leaderboard', methods=['GET'])
def get_achievement_leaderboard():
    """Get top users by achievement count"""
    query = """
    SELECT u.id, u.username, u.bio, COUNT(ua.id) as achievement_count
    FROM users u
    LEFT JOIN user_achievements ua ON u.id = ua.user_id AND ua.unlocked = 1
    GROUP BY u.id
    ORDER BY achievement_count DESC
    LIMIT 10
    """
    results = db.fetch_all(query)
    return jsonify(results)
```

#### 3. Route to Template
```python
@app.route('/achievements', methods=['GET'])
@login_required
def achievements():
    """Display achievements dashboard"""
    user = get_current_user()
    
    # Get achievement data
    achievements_by_cat = request_api('/api/achievements')
    leaderboard = request_api('/api/achievements/leaderboard')
    
    # Count achievements
    unlocked_count = sum(1 for cat_ach in achievements_by_cat.values() 
                         for ach in cat_ach if ach.get('unlocked'))
    
    return render_template('achievements_enhanced.html',
        trading_achievements=achievements_by_cat['trading'],
        wealth_achievements=achievements_by_cat['wealth'],
        league_achievements=achievements_by_cat['league'],
        special_achievements=achievements_by_cat['special'],
        total_unlocked=unlocked_count,
        total_achievements=sum(len(v) for v in achievements_by_cat.values()),
        achievement_leaderboard=leaderboard,
        trading_achievement_count=len([a for a in achievements_by_cat['trading'] if a.get('unlocked')]),
        wealth_achievement_count=len([a for a in achievements_by_cat['wealth'] if a.get('unlocked')]),
        league_achievement_count=len([a for a in achievements_by_cat['league'] if a.get('unlocked')]),
        special_achievement_count=len([a for a in achievements_by_cat['special'] if a.get('unlocked')]),
    )
```

---

## Database Schema Updates

### Add Portfolio History Tracking
```sql
CREATE TABLE IF NOT EXISTS portfolio_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    portfolio_value REAL NOT NULL,
    cash_balance REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX idx_portfolio_history_user_date 
    ON portfolio_history(user_id, created_at);
```

### Add Achievement System
```sql
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,  -- trading, wealth, league, special
    icon TEXT,
    reward_points INTEGER DEFAULT 0,
    reward_badge TEXT,
    required_progress INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    unlocked BOOLEAN DEFAULT 0,
    current_progress INTEGER DEFAULT 0,
    unlocked_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(achievement_id) REFERENCES achievements(id)
);
```

### Add League Member Roles
```sql
ALTER TABLE league_members ADD COLUMN role TEXT DEFAULT 'member';
-- Values: 'owner', 'admin', 'member'

CREATE INDEX idx_league_members_role 
    ON league_members(league_id, role);
```

---

## Navigation Updates

### Update Main Navigation Template
Add links to new features:
```html
<!-- In templates/layout.html nav section -->
<li class="nav-item">
    <a class="nav-link" href="/portfolio/analytics">
        <i class="fas fa-chart-line"></i> Analytics
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="/achievements">
        <i class="fas fa-trophy"></i> Achievements
    </a>
</li>
```

### Add League Management Link
```html
<!-- In league detail template -->
{% if is_owner or is_admin %}
<a href="/leagues/{{ league.id }}/manage" class="btn btn-primary">
    <i class="fas fa-cog"></i> Manage League
</a>
{% endif %}
```

---

## Testing Checklist

### Portfolio Analytics Tests
- [ ] API endpoint returns correct metrics
- [ ] Chart data is properly formatted
- [ ] Holdings table displays correct values
- [ ] Filter buttons work correctly
- [ ] Export to CSV/PDF functionality works
- [ ] Mobile responsive design verified

### League Management Tests
- [ ] Only owners/admins can access management
- [ ] Member promote/demote/remove functions work
- [ ] Invite code generates and can be copied
- [ ] Invite code regeneration works
- [ ] Settings changes save correctly
- [ ] Mobile responsive member cards

### Achievement Tests
- [ ] Achievements display with correct progress
- [ ] Filter buttons work (All/Unlocked/Locked)
- [ ] Leaderboard displays correctly
- [ ] Achievement icons and descriptions show
- [ ] Progress bars animate properly
- [ ] Unlock dates display correctly

---

## Performance Optimization Tips

1. **Cache portfolio calculations** (TTL: 10 minutes)
   ```python
   @cache.cached(timeout=600)
   def calculate_portfolio_metrics(user_id):
       # Expensive calculations here
   ```

2. **Optimize achievement queries** - Use single query with JOINs
3. **Paginate leaderboard** - Load 10 at a time, lazy load on scroll
4. **Cache achievement definitions** - Load once at startup

---

## Deployment Checklist

Before deploying Phase 2 features:
- [ ] All APIs return proper status codes (200, 400, 403, 404, 500)
- [ ] Error messages are user-friendly
- [ ] Database migrations run successfully
- [ ] New tables indexed for performance
- [ ] Test coverage > 80% for new code
- [ ] Security review completed (SQL injection, XSS, CSRF)
- [ ] Browser compatibility tested (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness verified
- [ ] Performance: API response time < 200ms
- [ ] Rate limiting implemented for new endpoints

---

## Common Issues & Solutions

### Issue: Portfolio chart not loading
**Solution**: Check if Chart.js CDN is accessible; verify data format is valid JSON array

### Issue: Invite code not regenerating
**Solution**: Ensure database transaction commits; check permissions middleware

### Issue: Achievement progress not updating
**Solution**: Verify trigger logic when trades complete; check progress calculation logic

### Issue: Leaderboard loading slowly
**Solution**: Add database index on achievement_count; implement pagination

---

## Quick Commands for Testing

### Test Portfolio Analytics Endpoint
```bash
curl -X GET http://localhost:5000/api/portfolio/analytics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test League Management
```bash
curl -X GET http://localhost:5000/api/leagues/1/members \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Achievements
```bash
curl -X GET http://localhost:5000/api/achievements \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Integration Timeline

- **Week 1**: Backend API development
- **Week 2**: Database schema updates and testing
- **Week 3**: Frontend integration and styling
- **Week 4**: Performance optimization and QA
- **Week 5**: Deployment and monitoring

---

## Support & Next Steps

After Phase 2 deployment:
1. Monitor API performance metrics
2. Gather user feedback on new features
3. Plan Phase 3 feature development
4. Schedule scaling infrastructure upgrades

For questions or issues during integration, refer to:
- [PHASE_2_COMPLETION_SUMMARY.md](PHASE_2_COMPLETION_SUMMARY.md)
- [PHASE_3_ROADMAP.md](PHASE_3_ROADMAP.md)
- Template files in `/templates/`
