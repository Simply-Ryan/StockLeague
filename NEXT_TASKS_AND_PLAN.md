# 🚀 StockLeague - Next Tasks & Development Plan (January 5, 2026)

## 📊 Current Status
- **Phases Completed**: 1-5 (Core trading, leagues, engagement, WebSocket, mobile/PWA)
- **Current Issues**: 6 known problems, 4 nice-to-have improvements
- **Architecture**: Solid (Flask + SQLite + WebSocket + performance monitoring)
- **Copilot Instructions**: ✅ Updated and comprehensive

---

## 🎯 PRIORITY 1: Critical Issues (This Week)

These are blocking issues that hurt user experience:

### 1.1 Portfolio Performance Chart Broken (HIGH PRIORITY)
**File**: `/dashboard` route, likely `templates/dashboard.html`  
**Problem**: Chart not rendering correctly  
**Impact**: Users can't see portfolio performance  
**Effort**: 2-3 hours

**Steps to Fix**:
1. Check if Chart.js library is loading correctly
2. Verify data being passed to chart template
3. Test theme compatibility (dark/light themes)
4. Fix contrast issues with background
5. Add error handling for missing data
6. Test on multiple browsers

**Acceptance Criteria**:
- [ ] Chart displays portfolio performance with correct colors
- [ ] Respects user's current theme (dark/light)
- [ ] Works on desktop and mobile
- [ ] Handles empty/missing data gracefully

---

### 1.2 Remove/Replace Challenges System (HIGH PRIORITY)
**Files**: Dropdown menu, routes, templates, database  
**Problem**: Challenges are duplicate of achievements  
**Impact**: Confusing UX, unused feature  
**Effort**: 3-4 hours

**Steps to Fix**:
1. Identify all references to challenges in codebase
2. Remove from navigation/dropdown menus
3. Verify no active routes depend on it
4. Remove from database (soft delete or full removal)
5. Update frontend templates
6. Test all links still work

**Search for**:
```bash
grep -r "challenge" app.py templates/ --include="*.html" --include="*.py"
grep -r "/challenges" app.py --include="*.py"
grep -r "challenges_system" . --include="*.py"
```

**Acceptance Criteria**:
- [ ] No "challenges" in navigation menu
- [ ] No broken links to challenges
- [ ] Achievements system remains untouched
- [ ] Database cleaned up (old challenge data)

---

### 1.3 Fix News Display (News Always Shows Placeholders) (MEDIUM PRIORITY)
**Files**: `/news` route, `templates/news.html`, `helpers.py`  
**Problem**: News never displays real content, always shows "0.00" scores  
**Impact**: News feature is completely broken  
**Effort**: 2-3 hours

**Steps to Fix**:
1. Debug `fetch_news_finnhub()` or `get_stock_news()` in helpers.py
2. Check Finnhub API key configuration
3. Verify news cache is being populated
4. Test API response manually
5. Add error logging to diagnose failures
6. Update templates to display real news vs placeholders

**Acceptance Criteria**:
- [ ] News displays real headlines from Finnhub API
- [ ] Sentiment scores show actual values (not 0.00)
- [ ] Images display if available
- [ ] Handles API failures gracefully

---

## 🎯 PRIORITY 2: Important Features (Week 2-3)

These are feature improvements that enhance UX:

### 2.1 Fix /chat Backend & Frontend (MEDIUM PRIORITY)
**Files**: `app.py` (/chat routes), `templates/chat.html`, WebSocket handlers  
**Problem**: Needs functionality review, remove call button, polish UI  
**Impact**: Chat is partially functional, needs refinement  
**Effort**: 4-5 hours

**Steps**:
1. Review chat backend routes for bugs
2. Remove video call button from UI
3. Test message history loading
4. Ensure WebSocket events work correctly
5. Test with multiple users simultaneously
6. Polish theme support (dark/light)
7. Test on mobile

**Acceptance Criteria**:
- [ ] Message sending/receiving works
- [ ] Message history loads correctly
- [ ] No console errors
- [ ] Works on desktop and mobile
- [ ] Call button removed

---

### 2.2 Fix Activity Feed Display Logic (MEDIUM PRIORITY)
**Files**: `league_activity_feed.py`, `/feed` route, `templates/feed.html`  
**Problem**: Should show own activity + friends' activity, currently incomplete  
**Impact**: Users can't see full social context  
**Effort**: 3-4 hours

**Steps**:
1. Verify database query for activity feed
2. Ensure own activities are included
3. Ensure friend activities are included
4. Test pagination/loading
5. Verify timestamps and formatting
6. Add filtering options

**Acceptance Criteria**:
- [ ] Shows user's own activities
- [ ] Shows friends' activities
- [ ] Activities appear in chronological order
- [ ] Pagination works correctly

---

### 2.3 Optimize /explore Page Performance (COMPLEX)
**Files**: `/explore` route, templates, helpers.py  
**Problem**: Page loads extremely slowly (stock search/discovery)  
**Impact**: Users abandon page, bad experience  
**Effort**: 6-8 hours (complex optimization)

**Likely Causes**:
- Multiple API calls without caching
- Inefficient database queries
- Loading too much data at once
- Missing indexes
- No pagination

**Steps**:
1. Profile the page load time (Chrome DevTools)
2. Identify slowest operations
3. Check if API calls are being cached
4. Implement pagination for stock lists
5. Optimize database queries
6. Add database indexes if needed
7. Consider Redis caching for popular stocks

**Acceptance Criteria**:
- [ ] Page loads in < 2 seconds
- [ ] Responsive as user types/scrolls
- [ ] Pagination works for large lists

---

## 🎯 PRIORITY 3: Polish & UI Improvements (Week 3-4)

### 3.1 Fix Theme Contrast Issues in Analytics
**Problem**: Charts and text have poor contrast with light/dark themes  
**Impact**: Hard to read analytics  
**Effort**: 2-3 hours

**Steps**:
1. Review all chart colors (Chart.js themes)
2. Test on both dark and light themes
3. Add info icons explaining chart types
4. Ensure text is readable on all backgrounds

---

### 3.2 Revamp League Details Page
**Problem**: First section needs redesign  
**Impact**: Users confused by layout  
**Effort**: 3-4 hours

**Steps**:
1. Review current layout
2. Redesign for clarity and UX
3. Test on mobile/desktop
4. Get feedback if possible

---

### 3.3 Polish Notifications System
**Problem**: UI needs improvements, backend needs review  
**Impact**: Notifications feel incomplete  
**Effort**: 3-4 hours

**Steps**:
1. Review notification types and triggers
2. Improve dropdown UI
3. Test notification page
4. Ensure all notifications appear correctly

---

### 3.4 Verify Font Awesome Icons
**Problem**: Many icons don't load (typos or missing icons)  
**Impact**: Visual inconsistency  
**Effort**: 1-2 hours

**Steps**:
1. Check Font Awesome version being used
2. Search for all FA icon references
3. Verify icon names are correct
4. Replace invalid icons with correct ones

---

## 📈 PRIORITY 4: Next Phase (Phase 6 - Advanced Trading)

After completing Priority 1-3, start Phase 6:

### 4.1 Implement Advanced Order Types
**Files**: `advanced_orders.py` (already exists but needs implementation)  
**Features**:
- Limit orders (buy/sell at specific price)
- Stop-loss orders (sell if price drops)
- Trailing stop orders (follow price, stop at loss)
- Bracket orders (stop + target profit)

**Estimated Effort**: 20-25 hours across 2-3 weeks

**Steps**:
1. Create order management UI
2. Implement order execution logic
3. Create order dashboard
4. Add notifications for order fills
5. Test with various price movements

**See**: `DETAILED_IMPLEMENTATION_ROADMAP_PHASES_5_10.md` for full specification

---

### 4.2 Division Leagues System
**Features**:
- Tier-based divisions (Bronze, Silver, Gold, etc.)
- Promotion/demotion
- Division-specific prizes

**Estimated Effort**: 15-20 hours

---

### 4.3 Tournament System Enhancements
**Features**:
- Bracket-style tournaments
- Automatic seeding
- Real-time tournament updates
- Prize allocation

**Estimated Effort**: 20-25 hours

---

## 📚 Recommended Reading Before Starting

Before diving into fixes, read these for context:

1. **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - Known problems summary
2. **[KNOWN_ISSUES_PERSONAL.md](KNOWN_ISSUES_PERSONAL.md)** - Personal notes on issues
3. **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - AI coding patterns
4. **[PHASE_2_PROGRESS_SUMMARY.md](PHASE_2_PROGRESS_SUMMARY.md)** - Design patterns
5. **[DETAILED_IMPLEMENTATION_ROADMAP_PHASES_5_10.md](DETAILED_IMPLEMENTATION_ROADMAP_PHASES_5_10.md)** - Phase 6 specs

---

## 🛠️ Development Workflow

### For Each Task:

1. **Read** the issue description carefully
2. **Understand** the current code (use grep to find all references)
3. **Identify** root cause (add console.log/print debugging)
4. **Fix** following existing patterns in codebase
5. **Test** on multiple browsers/devices
6. **Document** what changed and why
7. **Commit** with clear message

### Commands:

```bash
# Find all references to a feature
grep -r "feature_name" . --include="*.py" --include="*.html" --include="*.js"

# Check for errors in Python files
python -m py_compile app.py database/db_manager.py

# Run existing tests
cd /workspaces/StockLeague
python -m pytest tests/ -v

# Start the app to test
python app.py

# Check database status
python check_db.py
```

---

## 📋 Recommended Task Order

### Week 1 (Priority 1 - Critical Fixes)
- **Day 1**: Portfolio chart fix + remove challenges
- **Day 2**: News display fix + initial testing
- **Day 3**: Chat system review and fixes
- **Day 4**: Activity feed fixes
- **Day 5**: Testing and bug fixes

### Week 2 (Priority 2 - Performance & Polish)
- **Day 1**: Explore page optimization (diagnose)
- **Day 2-4**: Explore page optimization (fix)
- **Day 5**: Theme contrast fixes in analytics

### Week 3 (Priority 3 - UI Polish)
- **Day 1-2**: League details page revamp
- **Day 3**: Notifications polish
- **Day 4**: Font Awesome icon verification
- **Day 5**: General polish and cleanup

### Week 4+ (Phase 6 - Advanced Trading)
- Start limit orders implementation
- Build order dashboard
- Test with multiple concurrent orders

---

## 📊 Success Metrics

After completing this plan:
- ✅ No critical bugs in KNOWN_ISSUES.md
- ✅ All pages load efficiently (< 3 seconds)
- ✅ Features work on desktop and mobile
- ✅ Theme support (dark/light) consistent
- ✅ Ready to start Phase 6

---

## 🔗 Key Files to Have Open

Keep these files open for reference:
- [app.py](app.py) - Main routes
- [database/db_manager.py](database/db_manager.py) - Database operations
- [helpers.py](helpers.py) - Utility functions
- [error_handlers.py](error_handlers.py) - Error patterns
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md) - Problem list

---

**Ready to start? Pick Priority 1.1 (Portfolio Chart) and let's go!**

Generated: January 5, 2026  
Status: Ready for implementation
