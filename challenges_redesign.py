"""
Challenges System Redesign
==========================
Redesigns challenges to use:
1. Developer-made challenges only
2. Isolated challenge portfolios
3. No interference with league or personal portfolios
"""

# Developer-Made Challenges Configuration
DEVELOPER_CHALLENGES = {
    "first_steps": {
        "name": "First Steps",
        "description": "Make your first trade with any stock",
        "difficulty": "Beginner",
        "duration_days": 7,
        "rules": {
            "min_trades": 1,
            "min_investment": 0,
            "portfolio_value_target": 0,
            "max_portfolio_value": 10000  # Starting value
        },
        "rewards": {
            "cash": 100,
            "achievement": "first_trader",
            "badge": "🚀 First Step"
        },
        "instructions": "Execute your first stock trade to complete this challenge.",
        "order": 1
    },
    "diversification": {
        "name": "Diversification Master",
        "description": "Own stocks from at least 5 different companies",
        "difficulty": "Intermediate",
        "duration_days": 30,
        "rules": {
            "min_unique_stocks": 5,
            "min_portfolio_value": 5000,
            "max_position_percent": 40  # No more than 40% in one stock
        },
        "rewards": {
            "cash": 500,
            "achievement": "diversification_master",
            "badge": "📊 Diversified"
        },
        "instructions": "Build a diversified portfolio with at least 5 different stocks.",
        "order": 2
    },
    "profit_maker": {
        "name": "Profit Maker",
        "description": "Generate $500 in profit within the challenge period",
        "difficulty": "Intermediate",
        "duration_days": 30,
        "rules": {
            "min_profit": 500,
            "min_trades": 5,
            "portfolio_value_target": 10500  # $10,000 starting + $500 profit
        },
        "rewards": {
            "cash": 1000,
            "achievement": "profit_maker",
            "badge": "💰 Profit Maker"
        },
        "instructions": "Increase your challenge portfolio value by at least $500.",
        "order": 3
    },
    "market_timing": {
        "name": "Market Timing Expert",
        "description": "Execute 20 trades with mostly profitable exits",
        "difficulty": "Advanced",
        "duration_days": 30,
        "rules": {
            "min_trades": 20,
            "target_win_rate": 0.60,  # 60% profitable trades
            "min_profit_per_trade": 0
        },
        "rewards": {
            "cash": 2000,
            "achievement": "market_timing_expert",
            "badge": "⏱️ Market Timing"
        },
        "instructions": "Complete 20 trades with at least 60% of them being profitable.",
        "order": 4
    },
    "sector_specialist": {
        "name": "Sector Specialist",
        "description": "Focus 80% of your portfolio on a single sector",
        "difficulty": "Intermediate",
        "duration_days": 30,
        "rules": {
            "min_sector_concentration": 0.80,
            "min_stocks_in_sector": 3,
            "min_portfolio_value": 8000
        },
        "rewards": {
            "cash": 750,
            "achievement": "sector_specialist",
            "badge": "🏭 Specialist"
        },
        "instructions": "Build a portfolio where 80% of value is in one sector (minimum 3 stocks).",
        "order": 5
    }
}

class ChallengePortfolio:
    """
    Manages isolated portfolios for challenges.
    Each challenge participation gets its own portfolio snapshot.
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_challenge_portfolio(self, user_id: int, challenge_id: int) -> int:
        """
        Create a new isolated portfolio for a user participating in a challenge.
        Returns portfolio_id
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Create challenge portfolio with starting cash
        cursor.execute("""
            INSERT INTO challenge_portfolios (user_id, challenge_id, starting_cash, current_cash, created_at)
            VALUES (?, ?, 10000, 10000, CURRENT_TIMESTAMP)
        """, (user_id, challenge_id))
        
        portfolio_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return portfolio_id
    
    def get_challenge_portfolio(self, user_id: int, challenge_id: int):
        """Get or create challenge portfolio"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM challenge_portfolios 
            WHERE user_id = ? AND challenge_id = ?
            LIMIT 1
        """, (user_id, challenge_id))
        
        portfolio = cursor.fetchone()
        conn.close()
        
        if portfolio:
            return dict(portfolio)
        
        # Create if doesn't exist
        portfolio_id = self.create_challenge_portfolio(user_id, challenge_id)
        return self.get_challenge_portfolio(user_id, challenge_id)
    
    def get_challenge_holdings(self, portfolio_id: int):
        """Get all stock holdings in a challenge portfolio"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, SUM(shares) as shares, 
                   AVG(price) as avg_cost,
                   SUM(CASE WHEN type='buy' THEN shares*price ELSE -shares*price END) as total_invested
            FROM challenge_trades
            WHERE portfolio_id = ?
            GROUP BY symbol
            HAVING shares > 0
        """, (portfolio_id,))
        
        holdings = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in holdings]
    
    def record_challenge_trade(self, portfolio_id: int, symbol: str, trade_type: str, 
                               shares: int, price: float):
        """Record a trade in the challenge portfolio"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO challenge_trades 
            (portfolio_id, symbol, type, shares, price, timestamp)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (portfolio_id, symbol, trade_type, shares, price))
        
        conn.commit()
        conn.close()
    
    def calculate_portfolio_value(self, portfolio_id: int, current_prices: dict) -> dict:
        """Calculate total portfolio value and gains/losses"""
        holdings = self.get_challenge_holdings(portfolio_id)
        
        stock_values = {}
        total_invested = 0
        total_current_value = 0
        
        for holding in holdings:
            symbol = holding['symbol']
            shares = holding['shares']
            avg_cost = holding['avg_cost']
            
            current_price = current_prices.get(symbol, avg_cost)
            current_value = shares * current_price
            invested_value = shares * avg_cost
            
            stock_values[symbol] = {
                'shares': shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'current_value': current_value,
                'invested_value': invested_value,
                'gain_loss': current_value - invested_value,
                'gain_loss_percent': ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
            }
            
            total_invested += invested_value
            total_current_value += current_value
        
        # Get challenge portfolio cash
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_cash FROM challenge_portfolios WHERE id = ?", (portfolio_id,))
        result = cursor.fetchone()
        conn.close()
        
        current_cash = result['current_cash'] if result else 0
        
        return {
            'holdings': stock_values,
            'cash': current_cash,
            'total_value': total_current_value + current_cash,
            'total_gain_loss': total_current_value - total_invested,
            'total_invested': total_invested,
            'total_current_value': total_current_value
        }

# Database Schema Updates Required:
"""
-- New table for isolated challenge portfolios
CREATE TABLE IF NOT EXISTS challenge_portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    starting_cash NUMERIC DEFAULT 10000,
    current_cash NUMERIC DEFAULT 10000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, completed, abandoned
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id),
    UNIQUE(user_id, challenge_id)
);

-- Trades within challenge portfolios (isolated from main trading)
CREATE TABLE IF NOT EXISTS challenge_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    type TEXT NOT NULL,  -- buy, sell
    shares INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES challenge_portfolios(id)
);

-- Challenge definitions (developer-created only)
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    difficulty TEXT,  -- Beginner, Intermediate, Advanced
    duration_days INTEGER,
    rules TEXT,  -- JSON
    rewards TEXT,  -- JSON with cash, achievement, badge
    instructions TEXT,
    sort_order INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Challenge completions tracking
CREATE TABLE IF NOT EXISTS challenge_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    portfolio_id INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    final_portfolio_value NUMERIC,
    profit_loss NUMERIC,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id),
    FOREIGN KEY (portfolio_id) REFERENCES challenge_portfolios(id),
    UNIQUE(user_id, challenge_id)
);
"""
