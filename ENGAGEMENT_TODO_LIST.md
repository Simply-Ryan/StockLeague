# 📋 StockLeague Engagement Features - TODO List

## Phase 1: Foundation & Quick Wins (Week 1)
**Estimated Total: 10-13 hours**

### Feature 1: League-Specific Activity Feed
- [ ] Design database schema for activity queries
- [ ] Create `GET /api/league/<id>/activity-feed` endpoint
  - [ ] Query recent league trades
  - [ ] Query league achievements unlocked
  - [ ] Query leaderboard rank changes
  - [ ] Format response with timestamps and user info
- [ ] Create `templates/_league_activity_feed.html` component
  - [ ] Design activity feed UI
  - [ ] Add icons for different activity types
  - [ ] Style for sidebar integration
- [ ] Add JavaScript for real-time updates
  - [ ] Implement polling (5-second intervals)
  - [ ] Add "New activities" badge/refresh
- [ ] Integrate into `league_detail.html`
  - [ ] Add activity feed section
  - [ ] Position on page (right sidebar or below header)
  - [ ] Add styling for theme consistency
- [ ] Database optimization
  - [ ] Add indexes on league_id, timestamps
  - [ ] Test query performance
- [ ] Manual testing
  - [ ] Test with sample data
  - [ ] Verify real-time updates
  - [ ] Test on mobile responsiveness

### Feature 2: League-Specific Performance Metrics
- [ ] Design metrics calculation logic
  - [ ] Portfolio value vs league average
  - [ ] Win rate vs league average
  - [ ] Trade frequency vs league average
  - [ ] Recent rank and trend
- [ ] Create `GET /api/league/<id>/user/<user_id>/metrics` endpoint
  - [ ] Calculate user statistics
  - [ ] Calculate league statistics
  - [ ] Compute comparisons and deltas
- [ ] Create `templates/_league_performance_metrics.html` component
  - [ ] Design metrics card/widget UI
  - [ ] Add visual comparisons (color coding)
  - [ ] Add trend indicators (↑↓→)
- [ ] Add simple performance chart
  - [ ] 7-day or 30-day portfolio trend
  - [ ] Use Chart.js sparkline
- [ ] Integrate into `league_detail.html`
  - [ ] Add metrics card prominently
  - [ ] Position next to leaderboard
- [ ] Caching strategy
  - [ ] Cache metrics for 5 minutes
  - [ ] Invalidate on user trade
  - [ ] Update on demand
- [ ] Testing
  - [ ] Test with multiple users
  - [ ] Verify calculations accuracy
  - [ ] Performance test with large leagues

### Feature 3: League Announcements & System Feed
- [ ] Create database tables
  - [ ] `CREATE TABLE league_announcements`
  - [ ] `CREATE TABLE league_system_events`
  - [ ] Add indexes
- [ ] Create announcement API endpoints
  - [ ] `GET /api/league/<id>/announcements` - List announcements
  - [ ] `POST /league/<id>/announce` - Create (admin only)
  - [ ] `PUT /league/<id>/announce/<announce_id>` - Edit (admin)
  - [ ] `DELETE /league/<id>/announce/<announce_id>` - Delete (admin)
  - [ ] Add permission checks for admin operations
- [ ] Create system event generation
  - [ ] Trigger on user joins league
  - [ ] Trigger on ranking change
  - [ ] Trigger on achievement unlock
  - [ ] Trigger on season milestone
- [ ] Create `templates/_league_announcements.html` component
  - [ ] Design announcements/feed UI
  - [ ] Show pinned announcements first
  - [ ] Show system events below
  - [ ] Add timestamps and author
- [ ] Create admin announcement form
  - [ ] Add to league admin panel
  - [ ] Title and content fields
  - [ ] Pin checkbox
  - [ ] Submit button
- [ ] Integrate into `league_detail.html`
  - [ ] Add announcements section
  - [ ] Real-time update on new announcements
- [ ] Testing
  - [ ] Test admin posting
  - [ ] Test system event generation
  - [ ] Test permission enforcement
  - [ ] Test display formatting

---

## Phase 2: Enhancement & Integration (Week 2)
**Estimated Total: 7-10 hours**

### Feature 4: Side-by-Side Player Comparison
- [ ] Create comparison data endpoint
  - [ ] `GET /api/league/<id>/compare/<user1_id>/<user2_id>`
  - [ ] Gather portfolio metrics
  - [ ] Gather strategy metrics
  - [ ] Gather achievement data
  - [ ] Format for side-by-side display
- [ ] Create `templates/league_comparison.html` modal/page
  - [ ] Design two-column comparison layout
  - [ ] Add visual indicators (↑↓=)
  - [ ] Color code comparisons (green better, red worse)
  - [ ] Show 8+ comparison metrics
- [ ] Add JavaScript integration
  - [ ] Click player name to open comparison
  - [ ] Click in leaderboard row to compare
  - [ ] Add "Compare with me" quick action
- [ ] Modal styling
  - [ ] Responsive design for mobile
  - [ ] Smooth open/close animation
- [ ] Testing
  - [ ] Test different player pairs
  - [ ] Verify calculations
  - [ ] Test on mobile

### Feature 5: League Chat Integration on Page
- [ ] Analyze existing chat implementation at `/chat`
  - [ ] Understand Socket.IO integration
  - [ ] Review message schema
  - [ ] Identify reusable components
- [ ] Create `templates/_league_chat_sidebar.html` partial
  - [ ] Design compact chat sidebar
  - [ ] Show last 5-10 messages
  - [ ] Add message input form
  - [ ] Display user avatars
- [ ] Integrate Socket.IO chat logic
  - [ ] Connect to league chat room
  - [ ] Send/receive messages in real-time
  - [ ] Update message count
- [ ] Add to `league_detail.html`
  - [ ] Position as right sidebar
  - [ ] Add unread message badge
  - [ ] Add "Expand chat" button
- [ ] Responsive design
  - [ ] Mobile: Convert sidebar to modal
  - [ ] Add scroll for long conversations
- [ ] Testing
  - [ ] Test message sending/receiving
  - [ ] Test real-time updates
  - [ ] Test with multiple users

### Feature 6: Extended League Notifications
- [ ] Design league notification types
  - [ ] `league_overtaken` - User rank decreased
  - [ ] `league_achievement` - Achievement unlocked in league
  - [ ] `league_milestone` - Portfolio value milestone
  - [ ] `league_ranking_change` - Rank change notification
  - [ ] `league_announcement` - New admin announcement
- [ ] Create background job for ranking changes
  - [ ] Run every trade or every 5 minutes
  - [ ] Detect when user overtaken
  - [ ] Create notification if changed
- [ ] Extend existing notification system
  - [ ] Add league context to notifications
  - [ ] Include league name in message
  - [ ] Add link to league page
- [ ] Implement notification logic
  - [ ] Detect achievement in league context
  - [ ] Detect milestone in league context
  - [ ] Link announcement to notification
- [ ] Update notifications display
  - [ ] Show league context in notifications page
  - [ ] Add league-specific filtering
  - [ ] Show quick links to league
- [ ] Testing
  - [ ] Test overtaken notification
  - [ ] Test achievement notification
  - [ ] Test milestone detection
  - [ ] Verify no duplicate notifications

---

## Phase 3: Deep Analytics (Week 3)
**Estimated Total: 5-6 hours**

### Feature 7: League Analytics Dashboard
- [ ] Design analytics calculations
  - [ ] Portfolio value distribution
  - [ ] Win rate distribution
  - [ ] Trading pattern analysis
  - [ ] Risk metrics aggregation
  - [ ] Predictive insights
- [ ] Create analytics API endpoint
  - [ ] `GET /api/league/<id>/analytics`
  - [ ] Return comprehensive analytics data
  - [ ] Include historical data if available
- [ ] Build analytics page
  - [ ] `GET /league/<id>/analytics`
  - [ ] Render `league_analytics.html`
- [ ] Create `templates/league_analytics.html`
  - [ ] Design dashboard layout
  - [ ] Add 5+ chart sections
  - [ ] Add statistics tables
  - [ ] Add filter controls
- [ ] Implement visualizations
  - [ ] Portfolio value distribution (histogram)
  - [ ] Win rate distribution (histogram)
  - [ ] Most traded stocks (bar chart)
  - [ ] Performance trend (line chart)
  - [ ] Risk metrics (scatter plot)
  - [ ] Top performers (leaderboard)
- [ ] Add filters and controls
  - [ ] Time range selector
  - [ ] User type filter
  - [ ] Metric selector
- [ ] Performance optimization
  - [ ] Cache analytics (refresh every 10 mins)
  - [ ] Use database views for aggregations
  - [ ] Lazy load charts
  - [ ] Paginate large data sets
- [ ] Testing
  - [ ] Test with large datasets
  - [ ] Verify calculation accuracy
  - [ ] Performance test (loading time)
  - [ ] Test responsiveness on mobile

---

## Additional Tasks

### Database Setup
- [ ] Review and create migration for new tables
- [ ] Add indexes for performance
- [ ] Test migrations on clean database

### Documentation
- [ ] Update API documentation
- [ ] Add endpoint descriptions to Swagger/OpenAPI
- [ ] Document notification types
- [ ] Add user guide for new features

### Testing & QA
- [ ] Create test data fixtures
- [ ] Write integration tests
- [ ] User acceptance testing
- [ ] Performance testing
- [ ] Mobile responsiveness testing
- [ ] Browser compatibility testing

### Deployment
- [ ] Create deployment checklist
- [ ] Run migrations on production
- [ ] Monitor performance metrics
- [ ] Gather user feedback

---

## Dependencies & Notes

### Existing Infrastructure Used
- ✅ Socket.IO (real-time)
- ✅ Existing chat system at `/chat`
- ✅ Existing notifications system
- ✅ Chart.js available
- ✅ Bootstrap for styling

### Database Changes
- Need to create `league_announcements` table
- Need to create `league_system_events` table
- Add indexes on frequently queried columns

### API Routes
- 12 new API endpoints total
- 7 new page routes
- Maintain REST conventions

### Breaking Changes
- None - all new features, no modifications to existing

---

## Progress Tracking

### Phase 1 Checklist
**Total Tasks**: 35  
**Completed**: 0  
**In Progress**: 0  
**Blocked**: 0  

### Phase 2 Checklist
**Total Tasks**: 25  
**Completed**: 0  
**In Progress**: 0  
**Blocked**: 0  

### Phase 3 Checklist
**Total Tasks**: 20  
**Completed**: 0  
**In Progress**: 0  
**Blocked**: 0  

---

## Risk Assessment

| Feature | Risk | Mitigation |
|---------|------|-----------|
| Activity Feed | High volume of queries | Add caching, limit to 50 items |
| Real-time Updates | Socket.IO connection issues | Implement polling fallback |
| Chat Integration | Duplicate/conflicting code | Refactor existing chat module |
| Analytics | Performance with large data | Use database views, pagination |
| Notifications | Spam notifications | Implement frequency limits |

---

## Timeline Estimate

- **Phase 1**: 3-4 days (10-13 hours)
- **Phase 2**: 2-3 days (7-10 hours)
- **Phase 3**: 1-2 days (5-6 hours)
- **Testing & Deployment**: 1-2 days
- **Total**: 1-2 weeks for full implementation

---

## Approval & Sign-Off

- [ ] Product Manager Approval
- [ ] Tech Lead Review
- [ ] Design Review
- [ ] Ready to Begin Phase 1
