# 📋 SPRINT 6.1 PLAN: ADVANCED ORDER TYPES

**Duration**: Week 1-2 (10 working days)  
**Total Effort**: 45 hours  
**Start Date**: January 2, 2026  
**End Date**: January 15, 2026  

---

## 🎯 SPRINT OVERVIEW

### Goal
Implement a complete advanced order system allowing users to create limit orders, stop-loss orders, trailing stops, and bracket orders with automatic execution and monitoring.

### Business Value
- **User Retention**: Advanced traders stay longer with professional features
- **Competitive Advantage**: Match features of real brokerages
- **Revenue Potential**: Premium tier can require advanced orders (Phase 7)
- **Trading Sophistication**: Enable more strategic, risk-managed trading

### Team Allocation
- **1 Developer**: 45 hours = 1 full sprint (5.5 days of work per week)
- **Recommended**: 2 developers to allow parallel work on tasks

---

## ✅ ACCEPTANCE CRITERIA BY TASK

### Task 6.1.1: Limit Orders (15 hours)
**Owner**: Developer A  
**Timeline**: Day 1-3

**Acceptance Criteria**:
- [ ] Limit buy/sell order form UI on `/trade` page
- [ ] Form includes: symbol, quantity, limit price, notes, order type selector
- [ ] Database stores limit orders in `pending_orders` table
- [ ] Order status tracked: pending → executed → completed
- [ ] Background job checks prices and executes when reached
- [ ] Email notification sent when limit order executes
- [ ] Cancel limit order functionality works
- [ ] User can view all pending limit orders
- [ ] Order history shows completed limit orders with execution price
- [ ] Edge case: Skip gaps (price jumps over limit) handled gracefully
- [ ] Validation: prevent invalid inputs (negative, zero, etc.)
- [ ] Mobile responsive design

**Definition of Done**:
- Code reviewed and merged to master
- All tests passing
- UI tested on desktop and mobile
- Documentation updated

---

### Task 6.1.2: Stop-Loss & Trailing Stop Orders (15 hours)
**Owner**: Developer B (or A after 6.1.1)  
**Timeline**: Day 2-5

**Acceptance Criteria**:
- [ ] Stop-loss order UI with price input
- [ ] Trailing stop order UI with percentage input
- [ ] Stop orders trigger when price falls below stop price
- [ ] Trailing stops follow price and sell if it drops X%
- [ ] Cancel stop order functionality
- [ ] View pending stop orders with current status
- [ ] Test scenario: gap down (price skips stop level)
- [ ] Test scenario: trailing stop recalculates on new highs
- [ ] Order history shows stop orders correctly
- [ ] Notifications on stop order execution
- [ ] Orders linked to user positions (can't sell more than owned)

**Definition of Done**:
- Code reviewed and merged
- All tests passing
- Tested with real price data (IEX API)
- Documentation complete

---

### Task 6.1.3: Bracket Orders (10 hours)
**Owner**: Developer A or B  
**Timeline**: Day 5-7

**Acceptance Criteria**:
- [ ] Bracket order UI shows entry, stop-loss, and take-profit setup
- [ ] All three orders linked via bracket_id
- [ ] Canceling entry cancels both exit orders
- [ ] Executing stop-loss cancels take-profit automatically
- [ ] Executing take-profit cancels stop-loss automatically
- [ ] Visual representation showing all three orders
- [ ] Order history shows bracket as single entry
- [ ] Test: Complex bracket scenarios
- [ ] Notifications for all bracket components

**Definition of Done**:
- Code reviewed
- All tests passing
- UI/UX validated

---

### Task 6.1.4: Order Management Dashboard (5 hours)
**Owner**: Developer B  
**Timeline**: Day 7-8

**Acceptance Criteria**:
- [ ] New `/orders` page showing all orders
- [ ] View pending orders with current status
- [ ] View completed order history
- [ ] Cancel button for pending orders (with confirmation)
- [ ] Edit pending order (modify limit/stop price)
- [ ] Statistics: success rate, fill rate, average fill time
- [ ] Filter by: order type, status, symbol, date range
- [ ] Sort by: date, symbol, price, status
- [ ] Mobile responsive
- [ ] Search functionality

**Definition of Done**:
- Page responsive and fast
- All features working
- Tested on mobile

---

## 📊 DETAILED TASK BREAKDOWN

### Task 6.1.1: Limit Orders (15 hours)

#### Phase 1: Design & Planning (1 hour)
- [ ] Sketch UI mockup for limit order form
- [ ] Design database interactions
- [ ] Plan background job approach (cron vs scheduler)
- [ ] Design price check logic

**Output**: Design document with wireframes

#### Phase 2: Database Schema (1 hour)
- [ ] Verify `pending_orders` table has all needed fields
- [ ] Add indexes on (user_id, symbol, status) for query performance
- [ ] Create migration script if needed
- [ ] Test schema with sample inserts

**Files to Modify**:
- `database/db_manager.py` - Add methods for order CRUD

**Methods Needed**:
```python
def create_limit_order(user_id, symbol, shares, action, limit_price, notes)
def get_pending_orders(user_id, order_type=None)
def get_order_by_id(order_id)
def cancel_order(order_id)
def execute_order(order_id, execution_price)
def update_order_price(order_id, new_price)
```

#### Phase 3: Backend API Routes (6 hours)
- [ ] `POST /api/orders/create` - Create limit order
  - Validate: user has account, symbol exists, shares valid
  - Store in pending_orders table
  - Return order details
  
- [ ] `GET /api/orders` - Get user's orders
  - Filters: pending, executed, all
  - Returns JSON array
  
- [ ] `POST /api/orders/<id>/cancel` - Cancel order
  - Check user owns order
  - Update status to 'cancelled'
  
- [ ] `POST /api/orders/<id>/execute` - Manual execution (for testing)
  - Check conditions met
  - Execute trade
  - Update order status

**Files to Create/Modify**:
- `app.py` - Add routes above

#### Phase 4: Frontend UI (5 hours)
- [ ] Add "Limit Order" tab to `/trade` page buy/sell tabs
- [ ] Form fields:
  - Number of shares (auto-filled from current form)
  - Limit price (user input)
  - Order notes (optional)
  - "Place Limit Order" button
  
- [ ] Live calculations:
  - Show what price will trigger execution
  - If buy: "Will buy {shares} @ ${limit_price} or better"
  - If sell: "Will sell {shares} @ ${limit_price} or better"
  
- [ ] Order confirmation modal
- [ ] Success/error messaging

**Files to Modify**:
- `templates/trade.html` - Add limit order tab and form
- `static/js/app.js` - Add form handling

#### Phase 5: Background Job (2 hours)
- [ ] Create price monitoring job
  - Runs every minute (or via scheduled task)
  - Checks all pending limit orders
  - Gets current price via IEX API
  - Executes order if conditions met
  
- [ ] Create execution logic
  - Execute buy order if current_price ≤ limit_price
  - Execute sell order if current_price ≥ limit_price
  - Handle gap scenarios gracefully
  
- [ ] Error handling
  - Retry failed executions
  - Log all actions

**Files to Modify**:
- `advanced_orders.py` - Add execution logic
- `app.py` - Add background job (or create scheduler.py)

**New File Options**:
- `jobs/price_monitor.py` - Runs every minute
- `scheduler.py` - Celery/APScheduler setup

#### Phase 6: Testing & Edge Cases (1 hour)
- [ ] Test: Create limit order
- [ ] Test: Order executes at correct price
- [ ] Test: Order executes on exact price match
- [ ] Test: Gap scenario (price jumps over limit)
  - Should execute at market price, not gap over it
- [ ] Test: Cancel pending order
- [ ] Test: Email notification sent

---

### Task 6.1.2: Stop-Loss & Trailing Stop Orders (15 hours)

#### Phase 1: Design (1 hour)
- [ ] Design trailing stop logic
  - How to track "high water mark"
  - When to update high water mark
  - When to trigger stop
- [ ] UI mockups for both order types
- [ ] Document difference from limit orders

**Output**: Design document with state diagrams

#### Phase 2: Stop-Loss Orders (5 hours)
- [ ] Add UI to `/trade` page
  - "Stop-Loss Order" tab
  - Input: stop price
  - Show calculation: "Will sell all shares if price falls below ${stop_price}"
  
- [ ] Backend API: same as limit orders
  - Reuse existing `/api/orders/create` if possible
  - Differentiate by order_type field
  
- [ ] Execution logic in background job
  - Execute sell if current_price ≤ stop_price
  - Test gap down scenario (price drops below stop, no execution at stop price)
  
- [ ] Testing
  - Price reaches stop → executes
  - Price skips over stop → still executes at market
  - No execution if price stays above

#### Phase 3: Trailing Stop Orders (6 hours)
- [ ] UI: percentage input (e.g., 5% trailing stop)
  - Calculate: "Will sell if price drops 5% from high"
  - Show current high: "$95.50"
  - Show trigger price: "$90.73" (95.50 * 0.95)
  
- [ ] Database tracking
  - Store: trailing_percent, highest_price_since_creation
  - Update highest_price daily in background job
  
- [ ] Execution logic
  - Monitor price against (highest_price * (1 - trailing_percent))
  - Update highest_price when new high reached
  - Execute when threshold crossed
  
- [ ] Edge cases
  - Multiple price updates same day
  - Weekend/gap scenarios
  - Historical high tracking

#### Phase 4: Integration & Testing (3 hours)
- [ ] Combine stop-loss and trailing in single order form
- [ ] Test both types
- [ ] Test transitions (stop-loss → execute vs. → trailing)
- [ ] Performance test (many pending orders)

---

### Task 6.1.3: Bracket Orders (10 hours)

#### Phase 1: Design (1 hour)
- [ ] Design bracket UI showing 3 orders
- [ ] Design linking/coordination logic
- [ ] Document state transitions

#### Phase 2: Database & Backend (4 hours)
- [ ] Add bracket_id field to pending_orders
- [ ] Create logic to link orders
- [ ] Implement cancellation cascade
  - Entry cancelled → cancel both exits
  - Exit executed → cancel other exit
  
- [ ] API endpoints:
  - `POST /api/orders/bracket/create` - Create all 3
  - `POST /api/orders/bracket/<id>/cancel` - Cancel all

#### Phase 3: UI & Frontend (4 hours)
- [ ] Create bracket order form
  - Entry price (buy or sell)
  - Take-profit price
  - Stop-loss price
  - Display: "Bracket: {entry} / {stop} / {profit}"
  
- [ ] Visual display
  - Show all 3 orders linked
  - Color code: entry, profit, loss
  - Show status of each
  
- [ ] Integration with existing order flow

#### Phase 4: Testing (1 hour)
- [ ] Create bracket successfully
- [ ] Cancel entry cancels exits
- [ ] Execute one exit cancels other
- [ ] Visual feedback

---

### Task 6.1.4: Order Management Dashboard (5 hours)

#### Phase 1: Design & Template (1 hour)
- [ ] Create `templates/orders.html`
- [ ] Design layout: pending + history sections
- [ ] Plan filtering/sorting

#### Phase 2: Backend Routes (2 hours)
- [ ] `GET /orders` - render dashboard
- [ ] `GET /api/orders/statistics` - get stats (success rate, etc.)
- [ ] `/api/orders/search` - search/filter orders

#### Phase 3: Frontend Features (1.5 hours)
- [ ] Display pending orders table
- [ ] Display order history table
- [ ] Cancel button with confirmation modal
- [ ] Edit pending order modal
- [ ] Statistics cards

#### Phase 4: Polish & Testing (0.5 hours)
- [ ] Responsive design
- [ ] Performance (lazy load history)
- [ ] Test all features

---

## 🏗️ ARCHITECTURE & INTEGRATION

### Database Schema (Already Exists)
```
pending_orders table:
- id: auto-increment
- user_id: FK to users
- symbol: stock symbol
- shares: quantity
- order_type: 'limit', 'stop', 'trailing_stop', 'bracket'
- action: 'buy' or 'sell'
- limit_price: for limit orders
- stop_price: for stop orders
- trailing_percent: for trailing stops
- trailing_amount: calculated amount
- status: 'pending', 'executed', 'cancelled'
- notes: user notes
- created_at, executed_at, cancelled_at
- expiration: optional expiration date
- bracket_id: for linked bracket orders
```

### Background Job Flow
```
1. Every minute (or on schedule):
   - Get all pending orders
   - For each order:
     - Get current price via IEX API
     - Check execution condition
     - If condition met:
       - Execute trade (deduct from portfolio)
       - Send email notification
       - Update order status
       - Update portfolio history
```

### Price Execution Logic
```
LIMIT BUY:
  Execute if current_price ≤ limit_price
  Execute at limit_price (or better)

LIMIT SELL:
  Execute if current_price ≥ limit_price
  Execute at limit_price (or better)

STOP-LOSS SELL:
  Execute if current_price ≤ stop_price
  Execute at market price (may be worse than stop)

TRAILING STOP:
  Track highest_price_since_creation
  Update daily/on new highs
  Execute if current_price ≤ (highest_price * (1 - trailing_percent))
```

---

## 📋 FILES TO CREATE/MODIFY

### Files to Create
- [ ] `templates/orders.html` - Order management dashboard
- [ ] `templates/order_modal.html` (optional) - Reusable order modals
- [ ] `jobs/price_monitor.py` (if needed) - Background job

### Files to Modify
- [ ] `database/db_manager.py` - Add order CRUD methods
- [ ] `advanced_orders.py` - Expand with execution logic
- [ ] `app.py` - Add order routes and background job
- [ ] `templates/trade.html` - Add order tabs
- [ ] `static/js/app.js` - Order form handling
- [ ] `static/css/styles.css` - Order UI styling

### Existing Infrastructure
- ✅ `pending_orders` table exists
- ✅ `advanced_orders.py` partially complete
- ✅ IEX API integration exists (via `helpers.lookup()`)

---

## 🧪 TESTING STRATEGY

### Unit Tests
```python
# Test limit order execution
def test_limit_buy_executes_at_target():
    # Setup: order with limit_price=100
    # Execute: price reaches 99.50
    # Assert: order executes
    
def test_limit_sell_executes_at_target():
    # Setup: order with limit_price=100
    # Execute: price reaches 100.50
    # Assert: order executes

def test_trailing_stop_updates_high():
    # Setup: trailing stop 5% with high=$100
    # Execute: price goes to $105, then $98
    # Assert: high updates to $105, triggers at $99.75
```

### Integration Tests
```python
def test_bracket_order_full_flow():
    # Create bracket order
    # Verify all 3 orders created
    # Execute entry
    # Verify exits linked
    # Execute exit
    # Verify other exit cancelled

def test_order_email_notification():
    # Create order
    # Trigger execution
    # Assert email sent to user
```

### Manual Testing Checklist
- [ ] Create limit buy order in UI
- [ ] Create limit sell order in UI
- [ ] Create stop-loss order in UI
- [ ] Create trailing stop in UI
- [ ] Create bracket order in UI
- [ ] Cancel order from dashboard
- [ ] Edit pending order price
- [ ] View order history
- [ ] Test on mobile
- [ ] Verify emails sent

### Edge Case Testing
- [ ] Gap up scenario (price jumps over limit)
- [ ] Gap down scenario (price drops below stop)
- [ ] Multiple orders same symbol
- [ ] User with multiple portfolios
- [ ] Insufficient funds scenario
- [ ] Order expires without execution
- [ ] Network error during execution

---

## 📅 DAILY BREAKDOWN

### Day 1-2 (Friday-Monday)
**Task**: 6.1.1 Limit Orders - Design & Database
- [ ] 0.5 hrs: Review existing code
- [ ] 1 hr: Design database interactions
- [ ] 1 hr: Update db_manager.py with order methods
- [ ] 0.5 hrs: Test database queries

### Day 2-3 (Tuesday-Wednesday)
**Task**: 6.1.1 Limit Orders - Backend APIs
- [ ] 2 hrs: Create `/api/orders/create` endpoint
- [ ] 2 hrs: Create `/api/orders` GET endpoint
- [ ] 2 hrs: Create cancel/execute endpoints
- [ ] 1 hr: Test all endpoints

### Day 3-4 (Wednesday-Thursday)
**Task**: 6.1.1 Limit Orders - Frontend & UI
- [ ] 1.5 hrs: Add limit order tab to trade.html
- [ ] 1.5 hrs: Create form with live calculations
- [ ] 1.5 hrs: Add JavaScript form handling
- [ ] 0.5 hrs: Test form submission

### Day 4-5 (Thursday-Friday)
**Task**: 6.1.1 & 6.1.2 - Background Jobs & Testing
- [ ] 2 hrs: Create price monitoring job
- [ ] 2 hrs: Implement order execution logic
- [ ] 1 hr: Test various price scenarios
- [ ] 1 hr: Deploy and monitor

### Day 5-6 (Friday-Monday)
**Task**: 6.1.2 Stop-Loss & Trailing Stop
- [ ] 2 hrs: Design and plan trailing stop logic
- [ ] 2 hrs: Add stop-loss UI and backend
- [ ] 2 hrs: Add trailing stop UI and logic
- [ ] 1 hr: Test both scenarios

### Day 6-7 (Monday-Tuesday)
**Task**: 6.1.2 Continued & 6.1.3 Bracket
- [ ] 1 hr: Finish trailing stop testing
- [ ] 2 hrs: Design bracket order system
- [ ] 2 hrs: Implement bracket APIs
- [ ] 1 hr: Create bracket UI

### Day 7-8 (Tuesday-Wednesday)
**Task**: 6.1.3 Bracket & 6.1.4 Dashboard
- [ ] 1 hr: Finish bracket testing
- [ ] 1 hr: Create orders.html dashboard
- [ ] 1.5 hrs: Add pending/history tables
- [ ] 1.5 hrs: Add filters, search, statistics
- [ ] 0.5 hrs: Mobile responsive testing

### Day 8-10 (Wednesday-Friday)
**Task**: Integration, Testing & Polish
- [ ] 2 hrs: Integration testing
- [ ] 2 hrs: Edge case testing
- [ ] 1 hr: Performance optimization
- [ ] 1 hr: Documentation
- [ ] 1 hr: Code review and merge

---

## 🎯 SUCCESS METRICS

### Feature Completeness
- [ ] All 4 order types working
- [ ] 95%+ test coverage
- [ ] All acceptance criteria met
- [ ] No critical bugs

### Performance
- [ ] Order creation: <500ms
- [ ] Price checking: <1s per 100 orders
- [ ] Dashboard loads: <2s
- [ ] Mobile responsive: all devices

### User Experience
- [ ] Forms intuitive and clear
- [ ] Error messages helpful
- [ ] Mobile-friendly
- [ ] Email notifications working

### Code Quality
- [ ] Code reviewed by peer
- [ ] Proper error handling
- [ ] Database indexes optimized
- [ ] Documentation complete

---

## 🔗 DEPENDENCIES & BLOCKERS

### Internal Dependencies
- Phase 5 complete (mobile optimization) ✅
- IEX API integration ✅
- Database connection working ✅

### External Dependencies
- Email service (sendgrid, AWS SES) for notifications
- Scheduler (APScheduler, Celery) for background jobs

### Potential Blockers
1. **Price data accuracy**: IEX API latency
2. **Database performance**: Many pending orders
3. **Email delivery**: Service reliability
4. **Timezone handling**: User timezones for job scheduling

---

## 📞 COMMUNICATION PLAN

### Daily Standup
- 15 minutes each morning
- Report: What done yesterday, what doing today, blockers
- Sync on any blockers immediately

### Code Review
- All PRs reviewed before merge
- Minimum 1 approval required
- Address feedback same day

### Deployment
- Merge to staging first
- Test for 24 hours
- Deploy to production
- Monitor for errors

---

## 📚 REFERENCE DOCUMENTATION

### Related Files
- `DETAILED_IMPLEMENTATION_ROADMAP_PHASES_5_10.md` - Full technical specs
- `advanced_orders.py` - Existing implementation (350 lines)
- `database/db_manager.py` - Database methods

### API Reference
- IEX API docs: https://iexcloud.io/docs/
- Flask-APScheduler: https://flask-apscheduler.readthedocs.io/
- Email service: Check existing setup

### Example Implementation Patterns
- Look at `/buy` and `/sell` routes for similar transaction logic
- Look at background jobs for scheduling pattern

---

## ✨ NICE-TO-HAVE FEATURES (If Time)

1. **Order Templates**: Save order setups for quick reuse
2. **Alert Sounds**: Notify user with sound when order executes
3. **Mobile App Notifications**: Push notifications (Phase 5 PWA)
4. **Advanced Analytics**: Charts of order history, success rates
5. **One-Click Orders**: Pre-filled bracket templates
6. **Order Simulator**: Test orders without executing

---

## 📝 SIGN-OFF

**Sprint Owner**: [To be assigned]  
**Sprint Goals Approved**: [ ]  
**Estimated Hours**: 45 hours  
**Expected Completion**: January 15, 2026  

**Created**: January 1, 2026  
**Last Updated**: January 1, 2026  
**Status**: Ready to Start ✅

---

## 🚀 NEXT STEPS

1. Assign developers to tasks
2. Set up daily standup
3. Create GitHub issues for each task
4. Start with Task 6.1.1 on Day 1
5. Update this document daily with progress

**Ready to build! 💪**
