# Visual Overview - Home/Dashboard Restructure

## Site Map After Restructure

```
StockLeague Web Application
│
├─ Public Routes (No Auth Required)
│  ├─ GET /          → Home Page (Landing)
│  ├─ GET /home      → Home Page (Alias)
│  ├─ GET /login     → Login Form
│  ├─ GET /register  → Registration Form
│  └─ GET /about     → About Page
│
├─ Authenticated Routes (Login Required)
│  ├─ GET /dashboard → Trading Dashboard ⭐ NEW
│  ├─ GET /index     → Redirects to /dashboard (Legacy)
│  ├─ GET /buy       → Buy Stocks
│  ├─ GET /sell      → Sell Stocks
│  ├─ GET /explore   → Explore Stocks
│  ├─ GET /watchlist → Watchlist
│  ├─ GET /leagues   → My Leagues
│  ├─ GET /profile   → User Profile
│  └─ ... (other trading routes)
│
└─ API Routes
   ├─ POST /register
   ├─ POST /login
   ├─ POST /logout
   ├─ POST /buy
   ├─ POST /sell
   └─ ... (other API routes)
```

## Before vs After Comparison

### BEFORE Restructure
```
Route /     →  index()  →  index.html  →  Shows trading dashboard
                                            (Private page served publicly)
```

### AFTER Restructure
```
Route /         →  home()       →  home.html       →  Landing page (Public)
Route /home     →  home_alias() →  home.html       →  Landing page (Public)
Route /dashboard →  dashboard()  →  dashboard.html  →  Dashboard (Private)
Route /index    →  index()      →  Redirect /dashboard (Legacy)
```

## Page Structures

### HOME PAGE (Public)
```
┌─────────────────────────────────────────┐
│         NAVBAR WITH LOGO                │
│  (Logo → /home, Login/Register buttons) │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│                                         │
│          HERO SECTION                   │
│  "Welcome to StockLeague"               │
│  [Get Started Free] [Sign In]           │
│                                         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│                                         │
│  FEATURE GRID (6 CARDS)                 │
│  ┌──┐  ┌──┐  ┌──┐                       │
│  │Pa│  │Le│  │Ra│                       │
│  │pe│  │ag│  │nk│                       │
│  │rt│  │ue│  │ing│                      │
│  └──┘  └──┘  └──┘                       │
│  ┌──┐  ┌──┐  ┌──┐                       │
│  │Al│  │Wa│  │Ma│                       │
│  │er│  │tc│  │rk│                       │
│  │ts│  │hl│  │et│                       │
│  └──┘  └──┘  └──┘                       │
│                                         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│     STATISTICS SECTION                  │
│  1000+ Traders | 500+ Leagues           │
│  $100M+ Volume | 24/7 Data              │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│   HOW IT WORKS (4 STEPS)                │
│  1→ 2→ 3→ 4                             │
│  Create Explore Trade Join              │
│  Account Markets Trading Leagues        │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│         CTA SECTION                     │
│  [Sign Up Now] [Learn More]             │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│         FOOTER                          │
└─────────────────────────────────────────┘
```

### DASHBOARD PAGE (Private - Authenticated Only)
```
┌─────────────────────────────────────────┐
│  NAVBAR WITH DASHBOARD ICON             │
│  (Logo → /home, Dashboard → /dashboard) │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Dashboard | [Buy Stocks] [Explore]     │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  ⚠️  League Portfolio Mode / Personal   │
│  Description of current portfolio ctx   │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  ● LIVE UPDATES                         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  PERFORMANCE CARDS (4 COLUMNS)          │
│  ┌──────────┐ ┌──────────┐             │
│  │Total:   │ │Cash:     │             │
│  │$50,000  │ │$5,000    │             │
│  └──────────┘ └──────────┘             │
│  ┌──────────┐ ┌──────────┐             │
│  │Stocks:  │ │Change:   │             │
│  │$45,000  │ │+$500 1%↑ │             │
│  └──────────┘ └──────────┘             │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  QUICK ACTIONS (4 GRID)                 │
│  [Buy] [Sell] [Watchlist] [Leagues]     │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  PORTFOLIO CHART (30 DAYS)              │
│    │                                    │
│  $ │    ╱╲       ╱╲                     │
│    │   ╱  ╲     ╱  ╲╱                   │
│    │  ╱    ╲   ╱                        │
│    │ ╱      ╲ ╱                         │
│    │                                    │
│    └────────────────────────────────────│
│      Day1  Day2  ... Day30              │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  YOUR HOLDINGS | [Add Stocks]           │
│  ┌──────────────────────────────────┐  │
│  │ Symbol | Shares | Price | Value  │  │
│  ├──────────────────────────────────┤  │
│  │ AAPL   │   10   │ $170  │ $1700  │  │
│  │ MSFT   │   5    │ $300  │ $1500  │  │
│  │ GOOGL  │   2    │ $140  │ $280   │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  RECENT TRANSACTIONS | [View All]       │
│  ┌──────────────────────────────────┐  │
│  │ Date | Symbol | Type | Shares    │  │
│  ├──────────────────────────────────┤  │
│  │ Today│ AAPL   │ Buy  │ 10        │  │
│  │ Today│ MSFT   │ Sell │ 3         │  │
│  │ Yest │ GOOGL  │ Buy  │ 2         │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│         FOOTER                          │
└─────────────────────────────────────────┘
```

## User Flow Diagrams

### New User Journey
```
┌──────────┐
│ Visit /  │
└─────┬────┘
      │
      ↓
┌──────────────────────────┐
│  Home Page Loads         │
│  ✓ Hero Section          │
│  ✓ Features             │
│  ✓ Stats               │
│  ✓ CTA Buttons         │
└─────┬────────────────────┘
      │
      ├──→ Click "Get Started Free"
      │    ↓
      │  ┌──────────────┐
      │  │ /register    │
      │  └──────┬───────┘
      │         ↓
      │    [Fill Form]
      │         ↓
      │    [POST /register]
      │         ↓
      │    ┌──────────────┐
      │    │ /dashboard   │ ← Redirected after login
      │    └──────────────┘
      │
      └──→ Click "Sign In"
           ↓
        ┌──────────────┐
        │ /login       │
        └──────┬───────┘
               ↓
          [Fill Form]
               ↓
          [POST /login]
               ↓
          ┌──────────────┐
          │ /dashboard   │ ← Redirected after login
          └──────────────┘
```

### Returning User Journey
```
┌──────────┐
│ Visit /  │
└─────┬────┘
      │
      ↓
┌──────────────────────────┐
│  Home Page Loads         │
│  ✓ Same layout          │
│  ✓ "Go to Dashboard" btn │
│  ✓ Navigation links      │
└─────┬────────────────────┘
      │
      ├──→ Click "Go to Dashboard"
      │    ↓
      │  @login_required check
      │    ↓
      │  ┌──────────────┐
      │  │ /dashboard   │ ← Authenticated
      │  └──────────────┘
      │
      └──→ Click Dashboard Icon (navbar)
           ↓
        @login_required check
           ↓
        ┌──────────────┐
        │ /dashboard   │ ← Authenticated
        └──────────────┘
```

## Navigation Topology

```
                         ┌─── All Other Routes
                         │    (Trade, Leagues, etc)
                         │
    ┌─────────────────┐  │
    │   NAVBAR        │──┤
    │                 │  │
    │ [Logo] [Links]  │  │
    └────────┬────────┘  │
             │           │
      Logo "/" Route     │
             │           │
      ┌──────┴─────┐     │
      │             │     │
      ↓             ↓     │
   /home      /dashboard  │
    │             │       │
    │ Public       │ Private
    │ Auth: NO     │ Auth: YES
    │             │
    │         @login_required
    │             │
    ↓             ↓
 home()      dashboard()
    │             │
    ↓             ↓
 home.html  dashboard.html
    │             │
    ↓             ↓
Landing Page  Trading Dashboard
```

## File Structure Changes

```
StockLeague/
│
├── app.py
│   ├─ REMOVED:  @app.route("/") @login_required def index()
│   ├─ ADDED:    @app.route("/") def home()
│   ├─ ADDED:    @app.route("/home") def home_alias()
│   ├─ ADDED:    @app.route("/dashboard") @login_required def dashboard()
│   └─ ADDED:    @app.route("/index") @login_required def index() [redirect]
│
├── templates/
│   ├─ layout.html [MODIFIED]
│   │  ├─ Changed navbar brand href: "/" → "/home"
│   │  ├─ Changed nav link: "/" → "/dashboard"
│   │  ├─ Changed icon: fa-home → fa-chart-pie
│   │  └─ Changed text: "Portfolio" → "Dashboard"
│   │
│   ├─ home.html [NEW ✨]
│   │  ├─ Landing page (public)
│   │  ├─ 430+ lines
│   │  ├─ Hero, features, stats, how-it-works, CTA
│   │  └─ Responsive design
│   │
│   ├─ dashboard.html [NEW ✨]
│   │  ├─ Trading dashboard (private)
│   │  ├─ 390+ lines
│   │  ├─ Stats, chart, holdings, transactions
│   │  └─ Responsive design
│   │
│   ├─ index.html [DEPRECATED]
│   │  └─ Now serves as /index redirect to /dashboard
│   │
│   └─ ... (other templates unchanged)
│
└── ... (other files unchanged)
```

## Color & Icon Usage

### Home Page Icons
```
🏠 Home (in browser/navbar context)
📈 StockLeague brand icon (Chart Line)
🎯 Feature icons (varies by feature)
⭐ Navigation elements
```

### Dashboard Page Icons
```
📊 Dashboard icon (Chart Pie) in navbar
💰 Wallet icon in context alerts
⚡ Live badge indicator
📈 Portfolio chart with visual data
💾 Transaction history icon
🎁 Quick action icons
```

### Navbar Icons
```
Before:  🏠 (Home icon)     → points to / (dashboard)
After:   📊 (Chart-Pie)    → points to /dashboard

Brand:   📈 (Chart-Line)   → points to /home (was /, now home)
```

## Color Scheme

### Home Page
- Primary gradient background
- Feature cards with hover effects
- Accent colors for statistics
- CTA buttons in primary colors

### Dashboard Page
- Stat cards with highlight border
- Context alert with warning/primary gradient
- Green for positive gains, red for losses
- Chart with primary color line
- Neutral grays for tables

### Consistent Across Both
- Bootstrap primary color theme
- Dark navbar with white text
- Responsive container widths
- Font Awesome icon library
- Smooth transitions (0.3s ease)

## Responsive Breakpoints

### Mobile (< 768px)
- Single column layouts
- Hamburger menu navbar
- Stacked stat cards
- Full-width buttons
- Smaller font sizes

### Tablet (768px - 1024px)
- 2-column grids
- Expanded navbar
- Adjusted spacing
- Medium font sizes

### Desktop (> 1024px)
- Multi-column grids (3-4 columns)
- Full horizontal navbar
- Maximum spacing
- Larger font sizes

## Performance Metrics

| Metric | Home Page | Dashboard |
|--------|-----------|-----------|
| Static HTML | Yes | No |
| DB Queries | 0 | 5-10 |
| API Calls | 0 | ~20 (price lookups) |
| Load Time | Fast | Medium |
| Cache-able | Yes | Partial |
| Data Refresh | N/A | Real-time |

## Accessibility Features

- Semantic HTML structure
- ARIA labels on interactive elements
- Color contrast ratios meet WCAG standards
- Keyboard navigation support
- Screen reader friendly
- Alt text for icons/images
- Form labels properly associated
- Focus states visible on buttons

---

This visual overview helps understand the complete restructure at a glance!
