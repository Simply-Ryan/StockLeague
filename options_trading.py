"""
Complete Options Trading System for StockLeague
Implements options buying, selling, expiration, and portfolio management
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class OptionType(Enum):
    """Option contract type"""
    CALL = "call"
    PUT = "put"


class OptionStatus(Enum):
    """Status of an option position"""
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"
    EXERCISED = "exercised"


class OptionPosition:
    """Represents a single option position"""
    
    def __init__(self, position_id, user_id, league_id, symbol, option_type, strike_price,
                 expiration_date, quantity, premium_paid, status='open', opened_at=None,
                 closed_at=None, closing_premium=None, closing_reason=None):
        self.position_id = position_id
        self.user_id = user_id
        self.league_id = league_id
        self.symbol = symbol
        self.option_type = option_type
        self.strike_price = strike_price
        self.expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d') if isinstance(expiration_date, str) else expiration_date
        self.quantity = quantity
        self.premium_paid = premium_paid
        self.status = status
        self.opened_at = opened_at or datetime.now()
        self.closed_at = closed_at
        self.closing_premium = closing_premium
        self.closing_reason = closing_reason
    
    @property
    def total_cost(self) -> float:
        """Total cost of position (premium * quantity * 100 for contracts)"""
        return self.premium_paid * self.quantity * 100
    
    @property
    def is_expired(self) -> bool:
        """Check if option has expired"""
        return datetime.now() > self.expiration_date
    
    @property
    def days_to_expiration(self) -> int:
        """Days until expiration"""
        return (self.expiration_date - datetime.now()).days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'position_id': self.position_id,
            'user_id': self.user_id,
            'league_id': self.league_id,
            'symbol': self.symbol,
            'option_type': self.option_type,
            'strike_price': self.strike_price,
            'expiration_date': self.expiration_date.strftime('%Y-%m-%d'),
            'quantity': self.quantity,
            'premium_paid': self.premium_paid,
            'total_cost': self.total_cost,
            'status': self.status,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at,
            'closing_premium': self.closing_premium,
            'closing_reason': self.closing_reason,
            'days_to_expiration': self.days_to_expiration,
            'is_expired': self.is_expired
        }


class OptionsGreeks:
    """Container for Greeks calculations"""
    
    def __init__(self, delta=0, gamma=0, theta=0, vega=0, rho=0):
        self.delta = delta
        self.gamma = gamma
        self.theta = theta
        self.vega = vega
        self.rho = rho
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'delta': round(self.delta, 4),
            'gamma': round(self.gamma, 4),
            'theta': round(self.theta, 4),
            'vega': round(self.vega, 4),
            'rho': round(self.rho, 4)
        }


class OptionsPricingEngine:
    """Calculates option pricing using Black-Scholes model"""
    
    # Pricing constants
    RISK_FREE_RATE = 0.045  # 4.5% annual risk-free rate
    DEFAULT_VOLATILITY = 0.30  # 30% default volatility
    MIN_VOLATILITY = 0.05
    MAX_VOLATILITY = 2.0
    
    @staticmethod
    def black_scholes(spot_price: float, strike_price: float, time_to_expiration: float,
                     risk_free_rate: float, volatility: float, option_type: str) -> float:
        """
        Calculate Black-Scholes option price.
        
        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiration: Time to expiration in years
            risk_free_rate: Annual risk-free interest rate
            volatility: Annual volatility (sigma)
            option_type: 'call' or 'put'
            
        Returns:
            Option price
        """
        if time_to_expiration <= 0:
            # Expired - intrinsic value only
            if option_type == 'call':
                return max(0, spot_price - strike_price)
            else:
                return max(0, strike_price - spot_price)
        
        # Clamp volatility to reasonable range
        volatility = max(OptionsPricingEngine.MIN_VOLATILITY, 
                        min(volatility, OptionsPricingEngine.MAX_VOLATILITY))
        
        from scipy.stats import norm
        
        d1 = (math.log(spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiration) / \
             (volatility * math.sqrt(time_to_expiration))
        
        d2 = d1 - volatility * math.sqrt(time_to_expiration)
        
        if option_type == 'call':
            price = (spot_price * norm.cdf(d1) - 
                    strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2))
        else:  # put
            price = (strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2) - 
                    spot_price * norm.cdf(-d1))
        
        return max(0, price)
    
    @staticmethod
    def calculate_greeks(spot_price: float, strike_price: float, time_to_expiration: float,
                        risk_free_rate: float, volatility: float, option_type: str) -> OptionsGreeks:
        """
        Calculate option Greeks.
        
        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiration: Time to expiration in years
            risk_free_rate: Annual risk-free interest rate
            volatility: Annual volatility (sigma)
            option_type: 'call' or 'put'
            
        Returns:
            OptionsGreeks object
        """
        if time_to_expiration <= 0:
            return OptionsGreeks(0, 0, 0, 0, 0)
        
        volatility = max(OptionsPricingEngine.MIN_VOLATILITY,
                        min(volatility, OptionsPricingEngine.MAX_VOLATILITY))
        
        from scipy.stats import norm
        
        d1 = (math.log(spot_price / strike_price) +
              (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiration) / \
             (volatility * math.sqrt(time_to_expiration))
        
        d2 = d1 - volatility * math.sqrt(time_to_expiration)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (spot_price * volatility * math.sqrt(time_to_expiration))
        
        # Theta (per day)
        if option_type == 'call':
            theta = (-(spot_price * norm.pdf(d1) * volatility) / (2 * math.sqrt(time_to_expiration)) -
                    risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2)) / 365
        else:
            theta = (-(spot_price * norm.pdf(d1) * volatility) / (2 * math.sqrt(time_to_expiration)) +
                    risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2)) / 365
        
        # Vega (per 1% change in volatility)
        vega = spot_price * norm.pdf(d1) * math.sqrt(time_to_expiration) / 100
        
        # Rho (per 1% change in interest rates)
        if option_type == 'call':
            rho = strike_price * time_to_expiration * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(d2) / 100
        else:
            rho = -strike_price * time_to_expiration * math.exp(-risk_free_rate * time_to_expiration) * norm.cdf(-d2) / 100
        
        return OptionsGreeks(delta, gamma, theta, vega, rho)


class OptionsPortfolioManager:
    """Manages options positions and portfolio"""
    
    def __init__(self, db, pricing_engine=None):
        """
        Initialize options portfolio manager.
        
        Args:
            db: DatabaseManager instance
            pricing_engine: OptionsPricingEngine (will create default if not provided)
        """
        self.db = db
        self.pricing_engine = pricing_engine or OptionsPricingEngine()
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create options tables if they don't exist"""
        cursor = self.db.get_connection().cursor()
        
        # Options contracts (available contracts)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strike_price REAL NOT NULL,
                expiration_date DATE NOT NULL,
                option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, strike_price, expiration_date, option_type)
            )
        ''')
        
        # User options positions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_options_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                league_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                premium_paid REAL NOT NULL,
                status TEXT DEFAULT 'open' CHECK(status IN ('open', 'closed', 'expired', 'exercised')),
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                closing_premium REAL,
                closing_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (contract_id) REFERENCES options_contracts(id)
            )
        ''')
        
        # Options price history (for tracking price changes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES options_contracts(id)
            )
        ''')
        
        # Options portfolio statistics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_portfolio_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                league_id INTEGER NOT NULL,
                total_premium_paid REAL DEFAULT 0,
                total_premium_received REAL DEFAULT 0,
                total_realized_profit REAL DEFAULT 0,
                total_positions INTEGER DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, league_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (league_id) REFERENCES leagues(id)
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_positions_user ON user_options_positions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_positions_league ON user_options_positions(league_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_positions_status ON user_options_positions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_contract ON options_contracts(symbol, expiration_date)')
        
        self.db.get_connection().commit()
        logger.info("Options portfolio tables verified/created")
    
    def buy_option(self, user_id: int, league_id: int, symbol: str, strike_price: float,
                  expiration_date: str, option_type: str, quantity: int, current_price: float) -> Tuple[bool, str, Optional[int]]:
        """
        Buy an options contract.
        
        Args:
            user_id: User ID
            league_id: League ID
            symbol: Stock symbol
            strike_price: Strike price
            expiration_date: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            quantity: Number of contracts
            current_price: Current stock price
            
        Returns:
            (success, message, position_id)
        """
        try:
            # Validate inputs
            if quantity <= 0:
                return False, "Quantity must be positive", None
            
            if strike_price <= 0:
                return False, "Strike price must be positive", None
            
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            if exp_date <= datetime.now():
                return False, "Expiration date must be in the future", None
            
            # Calculate option price
            time_to_expiration = (exp_date - datetime.now()).days / 365.0
            option_price = self.pricing_engine.black_scholes(
                current_price, strike_price, time_to_expiration,
                OptionsPricingEngine.RISK_FREE_RATE,
                OptionsPricingEngine.DEFAULT_VOLATILITY,
                option_type
            )
            
            total_cost = option_price * quantity * 100  # Options contracts are 100 shares
            
            # Check if user has sufficient cash
            portfolio = self.db.get_portfolio(user_id, league_id)
            if portfolio.get('cash', 0) < total_cost:
                return False, f"Insufficient cash. Need ${total_cost:.2f}, have ${portfolio.get('cash', 0):.2f}", None
            
            # Create contract if it doesn't exist
            contract_id = self.db.create_options_contract(symbol, strike_price, expiration_date, option_type)
            
            # Create position
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_options_positions 
                (user_id, league_id, contract_id, quantity, premium_paid, status)
                VALUES (?, ?, ?, ?, ?, 'open')
            ''', (user_id, league_id, contract_id, quantity, option_price))
            
            position_id = cursor.lastrowid
            
            # Deduct cash from portfolio
            self.db.update_portfolio(user_id, league_id, cash_delta=-total_cost)
            
            # Update portfolio stats
            self._update_portfolio_stats(user_id, league_id)
            
            conn.commit()
            conn.close()
            
            logger.info(f"User {user_id} bought {quantity} {option_type} contracts {symbol} {strike_price} @ ${option_price}")
            return True, f"Bought {quantity} {option_type} contract(s) at ${option_price:.2f} each", position_id
            
        except Exception as e:
            logger.error(f"Error buying option: {e}")
            return False, f"Error buying option: {str(e)}", None
    
    def sell_option(self, user_id: int, league_id: int, position_id: int, current_price: float) -> Tuple[bool, str, Optional[float]]:
        """
        Sell an options position.
        
        Args:
            user_id: User ID
            league_id: League ID
            position_id: Position ID to close
            current_price: Current stock price
            
        Returns:
            (success, message, profit_loss)
        """
        try:
            # Get position
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT up.*, oc.symbol, oc.strike_price, oc.expiration_date, oc.option_type
                FROM user_options_positions up
                JOIN options_contracts oc ON up.contract_id = oc.id
                WHERE up.id = ? AND up.user_id = ? AND up.league_id = ?
            ''', (position_id, user_id, league_id))
            
            position = cursor.fetchone()
            if not position:
                return False, "Position not found", None
            
            if position['status'] != 'open':
                return False, f"Position is already {position['status']}", None
            
            # Calculate current option price
            exp_date = datetime.strptime(position['expiration_date'], '%Y-%m-%d')
            time_to_expiration = max(0, (exp_date - datetime.now()).days / 365.0)
            
            closing_price = self.pricing_engine.black_scholes(
                current_price, position['strike_price'], time_to_expiration,
                OptionsPricingEngine.RISK_FREE_RATE,
                OptionsPricingEngine.DEFAULT_VOLATILITY,
                position['option_type']
            )
            
            # Calculate P&L
            premium_paid = position['premium_paid'] * position['quantity'] * 100
            premium_received = closing_price * position['quantity'] * 100
            profit_loss = premium_received - premium_paid
            
            # Update position
            cursor.execute('''
                UPDATE user_options_positions
                SET status = 'closed', closed_at = ?, closing_premium = ?, closing_reason = 'sold'
                WHERE id = ?
            ''', (datetime.now(), closing_price, position_id))
            
            # Add cash back to portfolio
            self.db.update_portfolio(user_id, league_id, cash_delta=premium_received)
            
            # Update portfolio stats
            self._update_portfolio_stats(user_id, league_id)
            
            conn.commit()
            conn.close()
            
            logger.info(f"User {user_id} sold position {position_id} for P&L: ${profit_loss:.2f}")
            return True, f"Position closed. Profit/Loss: ${profit_loss:.2f}", profit_loss
            
        except Exception as e:
            logger.error(f"Error selling option: {e}")
            return False, f"Error selling option: {str(e)}", None
    
    def get_user_positions(self, user_id: int, league_id: int, status: str = 'open') -> List[Dict[str, Any]]:
        """Get user's options positions"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT up.*, oc.symbol, oc.strike_price, oc.expiration_date, oc.option_type
                FROM user_options_positions up
                JOIN options_contracts oc ON up.contract_id = oc.id
                WHERE up.user_id = ? AND up.league_id = ? AND up.status = ?
                ORDER BY up.opened_at DESC
            ''', (user_id, league_id, status))
            
            positions = cursor.fetchall()
            conn.close()
            
            return [dict(p) for p in positions]
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_portfolio_stats(self, user_id: int, league_id: int) -> Dict[str, Any]:
        """Get options portfolio statistics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM options_portfolio_stats
                WHERE user_id = ? AND league_id = ?
            ''', (user_id, league_id))
            
            stats = cursor.fetchone()
            conn.close()
            
            if stats:
                return dict(stats)
            else:
                return {
                    'user_id': user_id,
                    'league_id': league_id,
                    'total_premium_paid': 0,
                    'total_premium_received': 0,
                    'total_realized_profit': 0,
                    'total_positions': 0,
                    'open_positions': 0
                }
            
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {}
    
    def _update_portfolio_stats(self, user_id: int, league_id: int):
        """Update options portfolio statistics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get stats
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open
                FROM user_options_positions
                WHERE user_id = ? AND league_id = ?
            ''', (user_id, league_id))
            
            counts = cursor.fetchone()
            
            # Update or insert stats
            cursor.execute('''
                INSERT INTO options_portfolio_stats 
                (user_id, league_id, total_positions, open_positions)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, league_id) DO UPDATE SET
                    total_positions = ?,
                    open_positions = ?,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, league_id, counts['total'], counts['open'],
                  counts['total'], counts['open']))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def expire_positions(self) -> Tuple[int, List[str]]:
        """
        Check and process expired options contracts.
        
        Returns:
            (count_expired, messages)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Find expired positions
            cursor.execute('''
                SELECT up.*, oc.symbol, oc.strike_price, oc.expiration_date, oc.option_type
                FROM user_options_positions up
                JOIN options_contracts oc ON up.contract_id = oc.id
                WHERE up.status = 'open' AND oc.expiration_date < date('now')
            ''')
            
            expired_positions = cursor.fetchall()
            messages = []
            
            for position in expired_positions:
                # Calculate intrinsic value at expiration
                if position['option_type'] == 'call':
                    intrinsic = max(0, position['strike_price'] - position['strike_price'])
                else:
                    intrinsic = max(0, position['strike_price'] - position['strike_price'])
                
                # Update position status
                cursor.execute('''
                    UPDATE user_options_positions
                    SET status = 'expired', closed_at = ?
                    WHERE id = ?
                ''', (datetime.now(), position['id']))
                
                msg = f"Position expired: {position['symbol']} {position['option_type']} @ {position['strike_price']}"
                messages.append(msg)
                logger.info(msg)
            
            conn.commit()
            conn.close()
            
            return len(expired_positions), messages
            
        except Exception as e:
            logger.error(f"Error processing expirations: {e}")
            return 0, []
