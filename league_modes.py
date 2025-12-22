"""
League Competition Modes - Pluggable Strategy Pattern

This module implements different competition modes for stock trading leagues.
Each mode defines its own scoring formula, trade validation, and instrument rules.

Usage:
    mode = get_league_mode('percentage_return')
    score = mode.calculate_score(portfolio_value, starting_cash, trades)
    is_valid, error = mode.validate_trade(trade, portfolio, current_holdings)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any


# League mode identifiers
MODE_ABSOLUTE_VALUE = 'absolute_value'
MODE_PERCENTAGE_RETURN = 'percentage_return'
MODE_LIMITED_CAPITAL = 'limited_capital'


class LeagueMode(ABC):
    """
    Abstract base class for league competition modes.
    
    Each concrete mode must implement:
    - calculate_score: How to calculate a member's score
    - validate_trade: Whether a trade is allowed under this mode's rules
    - get_tiebreaker_key: How to break ties in rankings
    """
    
    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        """
        Initialize the mode with optional custom rules.
        
        Args:
            rules: Dict of mode-specific rules that override defaults
        """
        self.rules = rules or {}
        self._apply_default_rules()
    
    @abstractmethod
    def _apply_default_rules(self) -> None:
        """Apply default rules for this mode. Subclasses must implement."""
        pass
    
    @abstractmethod
    def calculate_score(self, portfolio_value: float, starting_cash: float, 
                        trades: List[Dict] = None, snapshots: List[Dict] = None) -> float:
        """
        Calculate the competition score for a league member.
        
        Args:
            portfolio_value: Current total portfolio value (cash + stocks)
            starting_cash: The starting cash amount for this league
            trades: List of trade records for this member (optional)
            snapshots: List of portfolio snapshots for risk calculations (optional)
            
        Returns:
            The member's score for ranking purposes
        """
        pass
    
    @abstractmethod
    def validate_trade(self, symbol: str, shares: int, price: float, 
                       trade_type: str, portfolio: Dict, 
                       current_holdings: List[Dict]) -> Tuple[bool, str]:
        """
        Validate whether a trade is allowed under this mode's rules.
        
        Args:
            symbol: Stock symbol
            shares: Number of shares
            price: Price per share
            trade_type: 'buy' or 'sell'
            portfolio: Current portfolio dict with 'cash' key
            current_holdings: List of current holdings dicts
            
        Returns:
            Tuple of (is_valid, error_message)
            error_message is empty string if valid
        """
        pass
    
    @abstractmethod
    def get_tiebreaker_key(self, member_data: Dict) -> Tuple:
        """
        Generate a tiebreaker key for ranking members with equal scores.
        
        Args:
            member_data: Dict with member info including score, total_value, etc.
            
        Returns:
            Tuple that can be used for secondary sorting
        """
        pass
    
    def get_description(self) -> str:
        """Return a human-readable description of this mode."""
        return "Standard trading competition"
    
    def get_allowed_symbols(self) -> Optional[List[str]]:
        """
        Return list of allowed symbols, or None for all symbols.
        Override in subclasses that restrict symbols.
        """
        return None
    
    def get_allowed_sectors(self) -> Optional[List[str]]:
        """
        Return list of allowed sectors, or None for all sectors.
        Override in subclasses that restrict sectors.
        """
        return None
    
    def apply_fee(self, trade_value: float) -> float:
        """
        Calculate transaction fee for a trade.
        
        Args:
            trade_value: Total value of the trade (shares * price)
            
        Returns:
            Fee amount
        """
        fee_percent = self.rules.get('transaction_fee_percent', 0)
        return trade_value * (fee_percent / 100)


class AbsoluteValueMode(LeagueMode):
    """
    Default mode: Score = total portfolio value.
    
    Simple and straightforward - whoever has the most money wins.
    Good for beginners and casual competitions.
    """
    
    def _apply_default_rules(self) -> None:
        defaults = {
            'transaction_fee_percent': 0,
            'max_positions': None,
            'max_position_value': None,
            'allow_shorting': False,
        }
        for key, value in defaults.items():
            if key not in self.rules:
                self.rules[key] = value
    
    def calculate_score(self, portfolio_value: float, starting_cash: float,
                        trades: List[Dict] = None, snapshots: List[Dict] = None) -> float:
        return portfolio_value
    
    def validate_trade(self, symbol: str, shares: int, price: float,
                       trade_type: str, portfolio: Dict,
                       current_holdings: List[Dict]) -> Tuple[bool, str]:
        # Check if shorting is attempted when not allowed
        if trade_type == 'sell':
            holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_shares = holding['shares'] if holding else 0
            if shares > current_shares and not self.rules.get('allow_shorting', False):
                return False, "Short selling is not allowed in this league"
        
        # Check if buy is affordable
        if trade_type == 'buy':
            total_cost = shares * price + self.apply_fee(shares * price)
            if total_cost > portfolio.get('cash', 0):
                return False, "Insufficient funds"
        
        return True, ""
    
    def get_tiebreaker_key(self, member_data: Dict) -> Tuple:
        # Tiebreaker: earlier join date wins
        return (member_data.get('joined_at', ''),)
    
    def get_description(self) -> str:
        return "Absolute Value: Ranked by total portfolio value"


class PercentageReturnMode(LeagueMode):
    """
    Score = percentage return from starting cash.
    
    Formula: ((current_value - starting_cash) / starting_cash) * 100
    
    This mode levels the playing field - a $100 profit on $1000 is the same
    score as a $10,000 profit on $100,000.
    """
    
    def _apply_default_rules(self) -> None:
        defaults = {
            'transaction_fee_percent': 0,
            'max_positions': None,
            'allow_shorting': False,
        }
        for key, value in defaults.items():
            if key not in self.rules:
                self.rules[key] = value
    
    def calculate_score(self, portfolio_value: float, starting_cash: float,
                        trades: List[Dict] = None, snapshots: List[Dict] = None) -> float:
        if starting_cash <= 0:
            return 0
        return ((portfolio_value - starting_cash) / starting_cash) * 100
    
    def validate_trade(self, symbol: str, shares: int, price: float,
                       trade_type: str, portfolio: Dict,
                       current_holdings: List[Dict]) -> Tuple[bool, str]:
        # Same validation as AbsoluteValue
        if trade_type == 'sell':
            holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_shares = holding['shares'] if holding else 0
            if shares > current_shares and not self.rules.get('allow_shorting', False):
                return False, "Short selling is not allowed"
        
        if trade_type == 'buy':
            total_cost = shares * price + self.apply_fee(shares * price)
            if total_cost > portfolio.get('cash', 0):
                return False, "Insufficient funds"
        
        return True, ""
    
    def get_tiebreaker_key(self, member_data: Dict) -> Tuple:
        # Tiebreaker: higher absolute value, then earlier join
        return (member_data.get('total_value', 0), member_data.get('joined_at', ''))
    
    def get_description(self) -> str:
        return "Percentage Return: Ranked by % gain from starting cash"



class LimitedCapitalMode(LeagueMode):
    """
    Mode with position limits and capital constraints.
    
    Rules can include:
    - max_positions: Maximum number of different stocks
    - max_position_value: Maximum value per position
    - max_position_percent: Maximum % of portfolio per position
    """
    
    def _apply_default_rules(self) -> None:
        defaults = {
            'transaction_fee_percent': 0.1,  # 0.1% fee by default
            'max_positions': 10,
            'max_position_value': None,  # e.g., 2000 = max $2000 per stock
            'max_position_percent': 25,  # Max 25% of portfolio in one stock
            'allow_shorting': False,
        }
        for key, value in defaults.items():
            if key not in self.rules:
                self.rules[key] = value
    
    def calculate_score(self, portfolio_value: float, starting_cash: float,
                        trades: List[Dict] = None, snapshots: List[Dict] = None) -> float:
        # Use percentage return for scoring
        if starting_cash <= 0:
            return 0
        return ((portfolio_value - starting_cash) / starting_cash) * 100
    
    def validate_trade(self, symbol: str, shares: int, price: float,
                       trade_type: str, portfolio: Dict,
                       current_holdings: List[Dict]) -> Tuple[bool, str]:
        if trade_type == 'sell':
            holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_shares = holding['shares'] if holding else 0
            if shares > current_shares and not self.rules.get('allow_shorting', False):
                return False, "Cannot sell more shares than you own"
            return True, ""
        
        # Buy validation
        trade_value = shares * price
        fee = self.apply_fee(trade_value)
        total_cost = trade_value + fee
        
        if total_cost > portfolio.get('cash', 0):
            return False, "Insufficient funds"
        
        # Check max positions
        max_positions = self.rules.get('max_positions')
        if max_positions:
            current_symbols = {h['symbol'] for h in current_holdings if h['shares'] > 0}
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
        max_pos_percent = self.rules.get('max_position_percent')
        if max_pos_percent:
            # Calculate total portfolio value including this trade
            portfolio_value = portfolio.get('cash', 0)
            for h in current_holdings:
                portfolio_value += h['shares'] * price  # Simplified - using current price for all
            
            current_holding = next((h for h in current_holdings if h['symbol'] == symbol), None)
            current_value = (current_holding['shares'] * price) if current_holding else 0
            new_value = current_value + trade_value
            
            if portfolio_value > 0:
                position_percent = (new_value / portfolio_value) * 100
                if position_percent > max_pos_percent:
                    return False, f"Position would exceed {max_pos_percent}% of portfolio"
        
        return True, ""
    
    def get_tiebreaker_key(self, member_data: Dict) -> Tuple:
        return (member_data.get('total_value', 0),)
    
    def get_description(self) -> str:
        desc = "Limited Capital: "
        parts = []
        if self.rules.get('max_positions'):
            parts.append(f"max {self.rules['max_positions']} positions")
        if self.rules.get('max_position_percent'):
            parts.append(f"max {self.rules['max_position_percent']}% per stock")
        if self.rules.get('transaction_fee_percent'):
            parts.append(f"{self.rules['transaction_fee_percent']}% fee")
        return desc + ", ".join(parts) if parts else desc + "position limits apply"



# Mode registry for easy lookup
MODE_REGISTRY = {
    MODE_ABSOLUTE_VALUE: AbsoluteValueMode,
    MODE_PERCENTAGE_RETURN: PercentageReturnMode,
    MODE_LIMITED_CAPITAL: LimitedCapitalMode,
}


def get_league_mode(mode_name: str, rules: Optional[Dict] = None) -> LeagueMode:
    """
    Factory function to get a league mode instance.
    
    Args:
        mode_name: One of the MODE_* constants
        rules: Optional dict of custom rules for this mode
        
    Returns:
        LeagueMode instance
        
    Raises:
        ValueError if mode_name is not recognized
    """
    mode_class = MODE_REGISTRY.get(mode_name)
    if not mode_class:
        # Default to absolute value
        mode_class = AbsoluteValueMode
    return mode_class(rules)


def get_available_modes() -> List[Dict[str, str]]:
    """
    Get list of available modes with their descriptions.
    
    Returns:
        List of dicts with 'id' and 'name' and 'description' keys
    """
    return [
        {
            'id': MODE_ABSOLUTE_VALUE,
            'name': 'Absolute Value',
            'description': 'Ranked by total portfolio value - simple and straightforward'
        },
        {
            'id': MODE_PERCENTAGE_RETURN,
            'name': 'Percentage Return',
            'description': 'Ranked by % gain from starting cash - levels the playing field'
        },
        {
            'id': MODE_LIMITED_CAPITAL,
            'name': 'Limited Capital',
            'description': 'Position limits and trading fees - tests discipline'
        },
    ]
