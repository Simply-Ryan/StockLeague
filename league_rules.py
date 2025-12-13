"""
League Rule Engine - Trade Validation and Rule Enforcement

This module provides rule-based validation for league trades.
Rules are configured per league and enforced at trade execution time.

Usage:
    engine = LeagueRuleEngine(rules_config)
    is_valid, error = engine.validate_order(order_data, portfolio, current_price)
    fee = engine.apply_fees(trade_value)
"""

from typing import Dict, List, Tuple, Optional, Any
import json


# Default rules configuration
DEFAULT_RULES = {
    'starting_cash': 10000.0,
    'max_positions': None,           # None = unlimited
    'max_position_value': None,      # Max $ value per position
    'max_position_percent': None,    # Max % of portfolio per position
    'transaction_fee_percent': 0,    # Trading fee as percentage
    'transaction_fee_flat': 0,       # Flat fee per trade
    'allow_shorting': False,
    'max_leverage': 1.0,             # 1.0 = no leverage (margin)
    'min_trade_value': 0,            # Minimum trade size
    'max_trade_value': None,         # Maximum trade size
    'allowed_sectors': None,         # None = all sectors
    'allowed_symbols': None,         # None = all symbols
    'blocked_symbols': None,         # Symbols that cannot be traded
    'trading_hours_only': False,     # Enforce trading hours (future)
    'max_daily_trades': None,        # Max trades per day
}


class LeagueRuleEngine:
    """
    Rule engine for enforcing league-level trading constraints.
    
    Rules can be configured per league and are checked before
    executing any trade within that league.
    """
    
    def __init__(self, rules_config: Optional[Dict[str, Any]] = None):
        """
        Initialize rule engine with configuration.
        
        Args:
            rules_config: Dict of rules to apply. Missing keys use defaults.
        """
        self.rules = {**DEFAULT_RULES}
        if rules_config:
            self.rules.update(rules_config)
    
    @classmethod
    def from_json(cls, rules_json: Optional[str]) -> 'LeagueRuleEngine':
        """
        Create rule engine from JSON string.
        
        Args:
            rules_json: JSON string of rules, or None for defaults
            
        Returns:
            LeagueRuleEngine instance
        """
        if not rules_json:
            return cls()
        
        try:
            config = json.loads(rules_json)
            return cls(config)
        except (json.JSONDecodeError, TypeError):
            return cls()
    
    def to_json(self) -> str:
        """Serialize current rules to JSON."""
        return json.dumps(self.rules)
    
    def validate_order(self, symbol: str, shares: int, price: float,
                       trade_type: str, portfolio: Dict,
                       current_holdings: List[Dict],
                       daily_trade_count: int = 0) -> Tuple[bool, str]:
        """
        Validate a trade order against all rules.
        
        Args:
            symbol: Stock symbol
            shares: Number of shares
            price: Price per share
            trade_type: 'buy' or 'sell'
            portfolio: Dict with 'cash' key
            current_holdings: List of holdings dicts with 'symbol', 'shares', 'avg_cost'
            daily_trade_count: Number of trades already made today
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if shares <= 0:
            return False, "Shares must be positive"
        
        if price <= 0:
            return False, "Price must be positive"
        
        trade_value = shares * price
        
        # Check blocked symbols
        blocked = self.rules.get('blocked_symbols')
        if blocked and symbol.upper() in [s.upper() for s in blocked]:
            return False, f"{symbol} is blocked from trading in this league"
        
        # Check allowed symbols
        allowed = self.rules.get('allowed_symbols')
        if allowed and symbol.upper() not in [s.upper() for s in allowed]:
            return False, f"{symbol} is not in the allowed list for this league"
        
        # Check min trade value
        min_trade = self.rules.get('min_trade_value', 0)
        if trade_value < min_trade:
            return False, f"Minimum trade value is ${min_trade:,.2f}"
        
        # Check max trade value
        max_trade = self.rules.get('max_trade_value')
        if max_trade and trade_value > max_trade:
            return False, f"Maximum trade value is ${max_trade:,.2f}"
        
        # Check max daily trades
        max_daily = self.rules.get('max_daily_trades')
        if max_daily and daily_trade_count >= max_daily:
            return False, f"Maximum {max_daily} trades per day reached"
        
        if trade_type == 'buy':
            return self._validate_buy(symbol, shares, price, portfolio, current_holdings)
        elif trade_type == 'sell':
            return self._validate_sell(symbol, shares, price, portfolio, current_holdings)
        else:
            return False, f"Invalid trade type: {trade_type}"
    
    def _validate_buy(self, symbol: str, shares: int, price: float,
                      portfolio: Dict, current_holdings: List[Dict]) -> Tuple[bool, str]:
        """Validate a buy order."""
        trade_value = shares * price
        total_cost = trade_value + self.calculate_fee(trade_value)
        cash = portfolio.get('cash', 0)
        
        # Check sufficient funds
        if total_cost > cash:
            return False, f"Insufficient funds. Need ${total_cost:,.2f}, have ${cash:,.2f}"
        
        # Check max positions
        max_positions = self.rules.get('max_positions')
        if max_positions:
            current_symbols = {h['symbol'] for h in current_holdings if h.get('shares', 0) > 0}
            if symbol not in current_symbols and len(current_symbols) >= max_positions:
                return False, f"Maximum {max_positions} positions allowed"
        
        # Check max position value
        max_pos_value = self.rules.get('max_position_value')
        if max_pos_value:
            current_holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_value = (current_holding['shares'] * price) if current_holding else 0
            new_value = current_value + trade_value
            if new_value > max_pos_value:
                return False, f"Position would exceed max value of ${max_pos_value:,.2f}"
        
        # Check max position percent
        max_pos_pct = self.rules.get('max_position_percent')
        if max_pos_pct:
            # Calculate total portfolio value
            portfolio_value = cash
            for h in current_holdings:
                hval = h.get('shares', 0) * price  # Simplified - using current price
                portfolio_value += hval
            
            current_holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_value = (current_holding['shares'] * price) if current_holding else 0
            new_value = current_value + trade_value
            
            if portfolio_value > 0:
                position_pct = (new_value / portfolio_value) * 100
                if position_pct > max_pos_pct:
                    return False, f"Position would exceed {max_pos_pct}% of portfolio"
        
        return True, ""
    
    def _validate_sell(self, symbol: str, shares: int, price: float,
                       portfolio: Dict, current_holdings: List[Dict]) -> Tuple[bool, str]:
        """Validate a sell order."""
        holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
        current_shares = holding.get('shares', 0) if holding else 0
        
        # Check if shorting
        if shares > current_shares:
            if not self.rules.get('allow_shorting', False):
                return False, "Short selling is not allowed in this league"
            
            # If shorting allowed, check leverage limits
            # (Future implementation for margin trading)
        
        return True, ""
    
    def calculate_fee(self, trade_value: float) -> float:
        """
        Calculate total transaction fee.
        
        Args:
            trade_value: Value of the trade (shares * price)
            
        Returns:
            Total fee amount
        """
        flat_fee = self.rules.get('transaction_fee_flat', 0)
        pct_fee = self.rules.get('transaction_fee_percent', 0)
        
        return flat_fee + (trade_value * pct_fee / 100)
    
    def can_short(self) -> bool:
        """Check if shorting is allowed."""
        return self.rules.get('allow_shorting', False)
    
    def max_leverage(self) -> float:
        """Get maximum leverage ratio."""
        return self.rules.get('max_leverage', 1.0)
    
    def get_starting_cash(self) -> float:
        """Get starting cash for this league."""
        return self.rules.get('starting_cash', 10000.0)
    
    def get_allowed_symbols(self) -> Optional[List[str]]:
        """Get list of allowed symbols, or None for all."""
        return self.rules.get('allowed_symbols')
    
    def get_blocked_symbols(self) -> Optional[List[str]]:
        """Get list of blocked symbols, or None for none."""
        return self.rules.get('blocked_symbols')
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """
        Get a human-readable summary of active rules.
        
        Returns:
            Dict with rule names and their current values
        """
        summary = {}
        
        if self.rules.get('max_positions'):
            summary['Max Positions'] = self.rules['max_positions']
        
        if self.rules.get('max_position_value'):
            summary['Max Position Value'] = f"${self.rules['max_position_value']:,.2f}"
        
        if self.rules.get('max_position_percent'):
            summary['Max Position %'] = f"{self.rules['max_position_percent']}%"
        
        if self.rules.get('transaction_fee_percent') or self.rules.get('transaction_fee_flat'):
            fee_parts = []
            if self.rules.get('transaction_fee_percent'):
                fee_parts.append(f"{self.rules['transaction_fee_percent']}%")
            if self.rules.get('transaction_fee_flat'):
                fee_parts.append(f"${self.rules['transaction_fee_flat']:.2f}")
            summary['Trading Fees'] = " + ".join(fee_parts)
        
        if self.rules.get('allow_shorting'):
            summary['Short Selling'] = 'Allowed'
        
        if self.rules.get('allowed_symbols'):
            summary['Allowed Stocks'] = f"{len(self.rules['allowed_symbols'])} specific symbols"
        
        if self.rules.get('blocked_symbols'):
            summary['Blocked Stocks'] = f"{len(self.rules['blocked_symbols'])} symbols"
        
        if self.rules.get('max_daily_trades'):
            summary['Max Daily Trades'] = self.rules['max_daily_trades']
        
        if self.rules.get('min_trade_value'):
            summary['Min Trade Value'] = f"${self.rules['min_trade_value']:,.2f}"
        
        if self.rules.get('max_trade_value'):
            summary['Max Trade Value'] = f"${self.rules['max_trade_value']:,.2f}"
        
        return summary


def get_default_rules() -> Dict[str, Any]:
    """Get a copy of the default rules configuration."""
    return {**DEFAULT_RULES}


def create_sector_restricted_rules(sectors: List[str], 
                                   starting_cash: float = 10000.0) -> Dict[str, Any]:
    """
    Helper to create rules for sector-restricted leagues.
    
    Args:
        sectors: List of allowed sector names
        starting_cash: Starting cash amount
        
    Returns:
        Rules configuration dict
    """
    return {
        'starting_cash': starting_cash,
        'allowed_sectors': sectors,
    }


def create_limited_capital_rules(max_positions: int = 10,
                                 max_position_percent: float = 25,
                                 fee_percent: float = 0.1,
                                 starting_cash: float = 10000.0) -> Dict[str, Any]:
    """
    Helper to create rules for limited capital mode.
    
    Args:
        max_positions: Maximum number of different stocks
        max_position_percent: Maximum % of portfolio per position
        fee_percent: Trading fee percentage
        starting_cash: Starting cash amount
        
    Returns:
        Rules configuration dict
    """
    return {
        'starting_cash': starting_cash,
        'max_positions': max_positions,
        'max_position_percent': max_position_percent,
        'transaction_fee_percent': fee_percent,
    }


def create_symbol_restricted_rules(symbols: List[str],
                                   starting_cash: float = 10000.0) -> Dict[str, Any]:
    """
    Helper to create rules for symbol-restricted leagues (e.g., S&P 500 only).
    
    Args:
        symbols: List of allowed stock symbols
        starting_cash: Starting cash amount
        
    Returns:
        Rules configuration dict
    """
    return {
        'starting_cash': starting_cash,
        'allowed_symbols': [s.upper() for s in symbols],
    }
