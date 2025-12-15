# Portfolio Context System - Implementation Summary

## Overview
The portfolio context system allows users to seamlessly switch between their personal portfolio and league portfolios, enabling competition in leagues without affecting their personal trading history.

## Architecture

### Session-Based Context Storage
- Uses `session["portfolio_context"]` to store current active portfolio
- Structure: `{"type": "personal"|"league", "league_id": int|None, "league_name": str|None}`
- Persists across requests within the same user session

### Database Schema

#### League Portfolio Tables
- **league_portfolios**: Stores cash balance for each user in each league
  - `league_id, user_id, cash, created_at, locked_at`
  - Each user gets separate starting cash per league
  
- **league_holdings**: Stores stock positions for each user in each league
  - `league_id, user_id, symbol, shares, avg_cost`
  - Completely separate from personal holdings
  
- **league_transactions**: Records all trades within leagues
  - `league_id, user_id, symbol, shares, price, type, fee, timestamp`
  - Separate transaction history per league

## Implementation Details

### Helper Functions (lines 23-103)

#### `get_active_portfolio_context()`
- Retrieves current portfolio context from session
- Defaults to personal portfolio if not set
- Returns context dictionary

#### `set_portfolio_context(type, league_id, name)`
- Updates session with new portfolio context
- Called when user switches portfolios

#### `get_portfolio_cash(user_id, context)`
- Personal: Returns `users.cash`
- League: Returns `league_portfolios.cash` for specific league

#### `get_portfolio_stocks(user_id, context)`
- Personal: Returns `db.get_user_stocks()`
- League: Returns `db.get_league_holdings()`

#### `validate_portfolio_context(user_id, context)`
- Checks if user can trade in current context
- Validates: league membership, league status (active/inactive)
- Returns (bool, error_msg)

### User Interface

#### Navbar Portfolio Switcher (layout.html lines 171-235)
- Dropdown showing active portfolio
- Visual indicators:
  - Personal: Blue badge with user icon
  - League: Yellow badge with trophy icon
- Lists all user's active leagues
- One-click switching via POST forms
- Active portfolio shows checkmark

#### Trade Page Indicators (buy.html & sell.html)
- Dismissible alert banners at top of page
- Shows "Trading in Personal Portfolio" or "Trading in League: [Name]"
- Clear visual distinction between contexts

### Routes

#### `/portfolio/switch` (POST)
- Accepts form data: `context_type` and optional `league_id`
- Validates league membership before switching
- Updates session and redirects back
- Flash message confirms switch

#### `/buy` and `/sell` (Updated)
- Validate portfolio context before processing trade
- Route to appropriate database tables based on context:
  - Personal: `transactions`, `users.cash`, user holdings
  - League: `league_transactions`, `league_portfolios.cash`, `league_holdings`
- WebSocket updates scoped to active portfolio
- Success messages include context info

#### `/` (Index - Updated)
- Fetches stocks from active portfolio
- Displays cash from active portfolio
- Calculates performance based on league starting_cash if applicable
- Shows correct transaction history per context

### Context Processor (lines 132-146)
- Makes `active_context` available in all templates
- Provides `get_user_leagues()` function to templates
- Runs on every request for logged-in users

## Workflow

### Creating a League
1. User creates league with specified `starting_cash`
2. System auto-creates `league_portfolios` entry for creator
3. Creator gets fresh balance equal to `starting_cash`

### Joining a League
1. User joins via invite code or league ID
2. System creates `league_portfolios` entry with league's `starting_cash`
3. User gets independent portfolio for that league

### Trading in Personal Portfolio (Default)
1. User sees "Personal Portfolio" badge in navbar
2. Buy/sell pages show "Trading in Personal Portfolio" banner
3. Trades update `users.cash` and personal holdings
4. Transaction recorded in `transactions` table

### Trading in League Portfolio
1. User clicks league name in navbar dropdown
2. Context switches to league (flash message confirms)
3. Buy/sell pages show "Trading in League: [League Name]" banner
4. Trades update `league_portfolios.cash` and `league_holdings`
5. Transaction recorded in `league_transactions` table
6. Completely isolated from personal portfolio

## Mistake-Proof Design

### Server-Side Validation
- Every trade validates portfolio context
- Checks league membership and status
- Prevents trading in inactive leagues
- Returns 403 error if context invalid

### Clear Visual Feedback
- Navbar always shows active portfolio
- Trade pages have prominent context indicators
- Flash messages confirm portfolio switches
- No ambiguity about target portfolio

### Separation of Concerns
- No portfolio selection in trade forms
- Context is global application state
- One portfolio active at a time
- Cannot accidentally trade in wrong portfolio

## Future Enhancements

### Potential Additions
- [ ] League portfolio history charts
- [ ] League portfolio snapshots
- [ ] Copy trading within leagues
- [ ] League-specific achievements
- [ ] Portfolio comparison views
- [ ] League leaderboard integration with context

## Testing Checklist

- [ ] Switch to personal portfolio - verify trades update personal tables
- [ ] Switch to league portfolio - verify trades update league tables
- [ ] Create league - verify creator gets starting balance
- [ ] Join league - verify member gets starting balance
- [ ] Trade in league - verify isolation from personal
- [ ] Trade in personal - verify isolation from league
- [ ] Switch portfolios mid-session - verify persistence
- [ ] Try to trade in inactive league - verify rejection
- [ ] Check navbar displays correct active portfolio
- [ ] Verify transaction history shows correct trades per context

## Files Modified

### Core Application
- `app.py` (lines 23-103, 132-146, 625-1180)
  - Helper functions
  - Context processor
  - Index route updates
  - Buy/sell route updates

### Templates
- `templates/layout.html` (lines 171-235)
  - Portfolio switcher dropdown
  
- `templates/buy.html` (lines 6-19)
  - Context indicator banner
  
- `templates/sell.html` (lines 6-19)
  - Context indicator banner

### Database
- No schema changes needed (tables already existed)
- Utilizing existing: `league_portfolios`, `league_holdings`, `league_transactions`

## Configuration
No additional configuration required. System works with existing:
- Flask session management
- SQLite database
- Bootstrap 5 UI components
- Font Awesome icons
