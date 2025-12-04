# 🏆 StockLeague - Competitive Paper Trading Platform

A **gamified social paper trading platform** where users compete in leagues, challenge friends, and climb leaderboards while learning real trading strategies in a risk-free environment. Built with Python Flask, featuring real-time stock quotes, portfolio management, social features, and competitive game modes.

## 📋 Core Features

### 🎯 Trading Features
- **Paper Trading** - Risk-free stock trading with virtual money
- **Real-time Quotes** - Live stock prices using Finnhub API with WebSocket updates
- **Options Trading** - Trade calls and puts with Black-Scholes pricing
  - Full options chain with multiple expiration dates
  - Greeks calculations (Delta, Gamma, Theta, Vega, Rho)
  - Auto-exercise ITM options at expiration
  - Real-time P&L tracking
- **News & Sentiment Analysis** - AI-powered news aggregation with sentiment scoring
  - Real-time news from Finnhub API
  - VADER sentiment analysis (positive/neutral/negative)
  - Stock-specific news feeds
  - Market sentiment dashboard
  - Personalized news tracking
- **Portfolio Management** - Track your holdings and performance
- **Transaction History** - Complete trade log with timestamps
- **Performance Analytics** - Charts, graphs, and detailed statistics with risk metrics

### 👥 Social Features
- **Friends System** - Add friends, send requests, view friend activity
- **User Profiles** - Customizable profiles with stats and achievements
- **Social Feed** - Share trades, like posts, comment on achievements
- **Direct Messaging** - Chat with friends about trading strategies
- **Following System** - Follow top traders and learn from them

### 🏆 League System
- **Create/Join Leagues** - Compete with friends, colleagues, or classmates
- **Public & Private Leagues** - Open leagues or invite-only competitions
- **League Leaderboards** - Real-time rankings within your league
- **Custom Settings** - Set starting cash, trading restrictions, duration
- **League Chat** - Discuss strategies with league members
- **Season System** - Periodic resets and championship seasons

### 🎮 Game Modes & Challenges
- **Daily Challenges** - New trading challenges every day
- **Speed Trading** - Quick 1-hour competitions
- **Sector Challenges** - Trade specific sectors (tech, healthcare, etc.)
- **1v1 Challenges** - Challenge friends to head-to-head trading
- **Tournaments** - Bracket-style competitions with prizes
- **Special Events** - Market simulations and themed competitions

### 🏅 Achievements & Progression
- **Trading Achievements** - Unlock badges for milestones
- **Social Achievements** - Earn rewards for community engagement
- **Rare Badges** - Special achievements for exceptional performance
- **Leaderboard Rankings** - Climb global and league-specific ranks
- **Profile Customization** - Show off your achievements and style

### 🔔 Notifications
- **Friend Requests** - Get notified of new friend activity
- **League Updates** - Alerts for league ranks and events
- **Challenge Notifications** - New challenges and tournament updates
- **Achievement Unlocks** - Celebrate your milestones
- **Price Alerts** - Custom stock price notifications

### 📊 Analytics & Insights
- **Portfolio Performance** - Track ROI, profit/loss, win rate
- **Comparison Tools** - Compare with friends and benchmarks
- **Trading Patterns** - Analyze your trading style and habits
- **Market Data** - Heat maps, trending stocks, sentiment analysis

### 🎨 Modern UI/UX
- **Responsive Design** - Works perfectly on mobile and desktop
- **Beautiful Gradients** - Modern, eye-catching interface
- **Dark/Light Themes** - Customize your viewing experience
- **Interactive Widgets** - Drag-and-drop dashboard customization
- **Real-time Updates** - Live data without page refreshes

## 🛠️ Tech Stack

### Backend
- **Python 3.8+**
- **Flask** - Web framework
- **SQLite** - Database
- **yfinance** - Stock market data API
- **Flask-Session** - Session management
- **Werkzeug** - Password security

### Frontend
- **HTML5** & **Jinja2** - Templating
- **CSS3** - Custom styling with gradients
- **JavaScript (ES6+)** - Interactive features
- **Bootstrap 5** - Responsive framework
- **Font Awesome** - Icons

## 📁 Project Structure

```
StockLeague/
├── app.py                      # Main Flask application
├── helpers.py                  # Helper functions (lookup, usd, apology)
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
│
├── database/
│   ├── db_manager.py          # Database operations manager
│   └── stocks.db              # SQLite database (auto-generated)
│
├── templates/                  # Jinja2 HTML templates
│   ├── layout.html            # Base template
│   ├── index.html             # Portfolio dashboard
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── buy.html               # Buy stocks
│   ├── sell.html              # Sell stocks
│   ├── quote.html             # Get stock quote
│   ├── quoted.html            # Display quote result
│   ├── history.html           # Transaction history
│   ├── add_cash.html          # Add cash to account
│   └── apology.html           # Error page
│
├── static/
│   ├── css/
│   │   └── styles.css         # Custom CSS styles
│   ├── js/
│   │   └── app.js             # JavaScript functionality
│   └── images/                # Image assets
│
└── flask_session/             # Session files (auto-generated)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git (optional)

### Installation

1. **Clone or navigate to the project directory**
   ```powershell
   cd C:\Programming\Visual_Studio_Code\WebApps\StockLeague
   ```

2. **Create a virtual environment (recommended)**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set up environment variables (optional)**
   
   For Alpha Vantage API (alternative to yfinance):
   ```powershell
   $env:ALPHA_VANTAGE_API_KEY="your_api_key_here"
   ```

5. **Initialize the database**
   
   The database will be automatically created when you first run the app.

### Running the Application

1. **Start the Flask development server**
   ```powershell
   python app.py
   ```

2. **Open your browser and navigate to**
   ```
   http://127.0.0.1:5000
   ```

3. **Register a new account**
   - Click "Register" in the navigation
   - Create a username and password
   - You'll start with $10,000 in cash!

## 📖 Usage Guide

### Getting Stock Quotes
1. Navigate to "Quote" in the menu
2. Enter a stock symbol (e.g., AAPL, GOOGL, TSLA)
3. View real-time price information

### Buying Stocks
1. Go to "Buy" from the navigation
2. Enter the stock symbol
3. Specify number of shares
4. Confirm purchase (if you have sufficient funds)

### Selling Stocks
1. Click "Sell" in the menu
2. Select a stock from your portfolio
3. Enter number of shares to sell
4. Confirm the sale

### Viewing Portfolio
- Your main dashboard shows all holdings
- See current prices and total values
- Track your cash balance and grand total

### Transaction History
- View all buy and sell transactions
- See prices, dates, and transaction types
- Track your trading activity

### Adding Cash
- Click "Add Cash" to deposit funds
- Enter amount or use quick buttons
- Increase your buying power

## 🔐 Security Features

- **Password Hashing**: All passwords are hashed using Werkzeug's security functions
- **Session Management**: Secure session handling with Flask-Session
- **CSRF Protection**: Built-in Flask security features
- **Input Validation**: Server-side and client-side validation
- **SQL Injection Prevention**: Parameterized queries with SQLite

## 🎨 Customization

### Changing the Starting Cash Balance
Edit `database/db_manager.py`:
```python
cash NUMERIC NOT NULL DEFAULT 10000.00  # Change this value
```

### Modifying Colors and Themes
Edit `static/css/styles.css`:
```css
:root {
    --primary-color: #2c3e50;    /* Adjust colors here */
    --success-color: #27ae60;
    /* ... */
}
```

### Adding New Stock Data Sources
Edit `helpers.py` to add alternative APIs or data sources.

## 🐛 Troubleshooting

### Common Issues

**Issue**: "Module not found" errors
- **Solution**: Make sure all dependencies are installed: `pip install -r requirements.txt`

**Issue**: Stock prices not loading
- **Solution**: Check your internet connection. yfinance requires internet access for real-time data.

**Issue**: Database errors
- **Solution**: Delete `database/stocks.db` and restart the app to recreate the database.

**Issue**: Session errors
- **Solution**: Clear the `flask_session/` folder and restart the application.

## 🚀 Production Deployment

For production deployment:

1. **Set Flask environment variables**
   ```powershell
   $env:FLASK_ENV="production"
   ```

2. **Use a production server (Gunicorn on Linux, waitress on Windows)**
   ```powershell
   pip install waitress
   waitress-serve --port=8000 app:app
   ```

3. **Set up a reverse proxy (Nginx or Apache)**

4. **Enable HTTPS** with SSL certificates

5. **Set up a proper database** (PostgreSQL or MySQL for production)

## 🤝 Contributing

Feel free to fork this project and submit pull requests for improvements!

### Ideas for Enhancement
- Add stock charts and graphs
- Implement watchlists
- Add email notifications
- Create portfolio analytics
- Add social trading features
- Implement stop-loss orders
- Add cryptocurrency support

## 📝 License

This project is open source and available for educational purposes.

## 👨‍💻 Author

Built with ❤️ using Flask, Python, and Bootstrap

## 🙏 Acknowledgments

- **Yahoo Finance** for stock data via yfinance
- **Bootstrap** for the responsive framework
- **Font Awesome** for icons
- **Flask** community for excellent documentation

## 📞 Support

For issues or questions, please check the troubleshooting section or open an issue on the repository.

---

**Happy Trading! 📈💰**
