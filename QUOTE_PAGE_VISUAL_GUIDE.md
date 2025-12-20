# Quote Page Trading Interface - Visual Guide

## New Quote Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    STOCK HEADER                             │
│         Symbol  │  Price  │  Change  │  Watch Button        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   TECHNICAL CHART                           │
│                   (TradingView Widget)                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  TRADING INTERFACE (NEW!)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🏆 Trading in League: [League Name]  X                    │
│  (or 👤 Trading in Personal Portfolio  X)                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Trade AAPL          Available Cash: $50,000          │  │
│  │                      Your Holdings: 25 shares         │  │
│  ├────────────┬──────────────┤                           │  │
│  │ 🛒 Buy     │ 💰 Sell      │                           │  │
│  └────────────┴──────────────┤                           │  │
│                                                          │  │
│  [BUY TAB ACTIVE]                                       │  │
│  ┌────────────────────────────────────────────────────┐ │  │
│  │                                                    │ │  │
│  │ # Number of Shares                                │ │  │
│  │ ┌──────────────────────┬───────┐                  │ │  │
│  │ │ [        10        ]  │ Max ↑ │                  │ │  │
│  │ └──────────────────────┴───────┘                  │ │  │
│  │ Max: 111 shares @ $450.00                         │ │  │
│  │                                                    │ │  │
│  │ 📈 Strategy (Optional)                            │ │  │
│  │ ┌──────────────────────────────────┐              │ │  │
│  │ │ [No Strategy           ▼]        │              │ │  │
│  │ └──────────────────────────────────┘              │ │  │
│  │                                                    │ │  │
│  │ 📝 Notes (Optional)                               │ │  │
│  │ ┌──────────────────────────────────┐              │ │  │
│  │ │ Why are you buying?               │              │ │  │
│  │ │                                    │              │ │  │
│  │ └──────────────────────────────────┘              │ │  │
│  │                                                    │ │  │
│  │ ┌─ ORDER SUMMARY ──────────────────────────────┐  │ │  │
│  │ │  Price Per Share    Total Cost    Cash After  │  │ │  │
│  │ │    $450.00          $4,500.00     $45,500.00  │  │ │  │
│  │ └────────────────────────────────────────────────┘  │ │  │
│  │                                                    │ │  │
│  │ ┌──────────────────────────────────────────────┐  │ │  │
│  │ │  🛒 Buy AAPL                                 │  │ │  │
│  │ └──────────────────────────────────────────────┘  │ │  │
│  │                                                    │ │  │
│  └────────────────────────────────────────────────────┘ │  │
│                                                         │  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  NEWS & ARTICLES                            │
└─────────────────────────────────────────────────────────────┘
```

## Tab Switching - Buy to Sell

When user has shares of the stock:

```
Buy Tab                          Sell Tab
[🛒 Buy] [💰 Sell ✓]          [🛒 Buy] [💰 Sell ✓]
  ACTIVE       ENABLED            HIDDEN       ACTIVE

# Buy Form                       # Sell Form
   Price: $450.00                   Price: $450.00
   Max Shares: 111                  You Own: 25 shares
   (based on cash)                  (based on holdings)
```

When user has NO shares of the stock:

```
[🛒 Buy] [💰 Sell ✗]
  Can Trade    Cannot Sell

Sell Tab shows:
⚠️ You don't own any shares of AAPL
   Buy some to get started! [Buy link]
```

## Real-time Calculations

### Buy Form Example:
```
User Input: 10 shares of AAPL at $150.00

Price Per Share: $150.00
    ↓
    × 10 shares
    ↓
Total Cost: $1,500.00
    ↓
USER CASH: $50,000.00
    ↓
    - $1,500.00
    ↓
Cash After: $48,500.00 ✓ (GREEN - Valid)

[Submit Button] → ENABLED
```

### Buy Form - Insufficient Funds:
```
User Input: 500 shares of AAPL at $150.00

Price Per Share: $150.00
    ↓
    × 500 shares
    ↓
Total Cost: $75,000.00 ❌ (RED - Too much!)
    ↓
USER CASH: $50,000.00
    ↓
    - $75,000.00
    ↓
Cash After: -$25,000.00 ❌ (RED - Invalid)

[Submit Button] → DISABLED
```

### Sell Form Example:
```
User Input: 10 shares of AAPL at $150.00

Price Per Share: $150.00
    ↓
    × 10 shares
    ↓
Total Proceeds: $1,500.00
    ↓
USER CASH: $50,000.00
    ↓
    + $1,500.00
    ↓
Cash After: $51,500.00 ✓ (Always valid!)

[Submit Button] → ENABLED
```

## Feature Details

### Max Buttons
- **Max Buy**: Fills shares with: `floor(userCash / stockPrice)`
- **Max Sell**: Fills shares with: `userShares` (all holdings)
- Both update form and calculations immediately

### Order Summary Box
Updates in real-time as user types:
- Shows exact cost/proceeds calculation
- Shows cash balance after transaction
- Color codes for validation feedback
- Always visible for user confirmation

### Form Validation
- **Buy**: Disables submit if total cost > available cash
- **Sell**: Limits input to user's share count (max attribute)
- **Both**: Prevents zero or negative shares

### Portfolio Context
Located above tabs:
- Shows current trading context (Personal or League)
- Shows portfolio name if in league
- Can be dismissed with X button
- Prevents accidental trades in wrong portfolio

## JavaScript Behavior

```javascript
// Core Variables (from server)
STOCK_PRICE = 450.00    // Current market price
USER_CASH = 50000.00    // Available cash
USER_SHARES = 25        // Currently owned shares

// Buy Calculations
updateBuyCalculations() {
    shares = input.value
    totalCost = shares * STOCK_PRICE
    cashAfter = USER_CASH - totalCost
    
    // Disable submit if insufficient funds
    if (cashAfter < 0) {
        submitBtn.disabled = true
    }
}

// Sell Calculations
updateSellCalculations() {
    shares = input.value
    totalProceeds = shares * STOCK_PRICE
    cashAfter = USER_CASH + totalProceeds
    
    // Prevent selling more than owned
    if (shares > USER_SHARES) {
        input.value = USER_SHARES
    }
}

// Event Listeners
- Input change → recalculate
- Max buttons → auto-fill + recalculate
- Tab switch → swap form displays
```

## Mobile Responsive Design

### Desktop (>768px)
- Side-by-side form fields
- Full-width order summary boxes
- Tabs fully visible

### Tablet (576-767px)
- Stacked form fields
- Full-width inputs
- Tabs with scroll if needed

### Mobile (<576px)
- Single column layout
- Full-width buttons
- Scrollable tab content
- Compact alerts

## Comparison: Old vs New

### Old Flow (Separate Pages)
```
Quote Page
    ↓
[Buy Link] ──→ /buy page ──→ Fill form ──→ Submit ──→ Back to Quote
            or
[Sell Link] ──→ /sell page ──→ Fill form ──→ Submit ──→ Back to Quote
```

### New Flow (Unified)
```
Quote Page
├─ [Buy Tab] ──→ Fill form ──→ Submit (stays on page with feedback)
└─ [Sell Tab] ──→ Fill form ──→ Submit (stays on page with feedback)

(No navigation required!)
```

## User Experience Benefits

1. **Speed**: Trade without leaving the page
2. **Visibility**: Always see current price and holdings
3. **Feedback**: Real-time calculations before submit
4. **Safety**: Validation prevents invalid orders
5. **Context**: Always clear which portfolio you're trading in
6. **Efficiency**: Max buttons save calculation time
7. **Clarity**: Order summary box shows exact costs/proceeds

