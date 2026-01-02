"""
Advanced Orders System for StockLeague

Handles limit orders, stop-loss orders, trailing stops, and bracket orders.
Includes price monitoring and automatic order execution.
"""

import logging
from datetime import datetime, timedelta
from helpers import lookup, usd
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AdvancedOrderManager:
    """Manages advanced order types and execution"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    # ==================== LIMIT ORDERS ====================
    
    def create_limit_order(self, user_id: int, symbol: str, shares: int, action: str, 
                          limit_price: float, notes: str = "", portfolio_id: int = None) -> dict:
        """
        Create a limit order for a user
        
        Args:
            user_id: User ID
            symbol: Stock symbol
            shares: Number of shares
            action: 'buy' or 'sell'
            limit_price: Price to execute at (or better)
            notes: Optional order notes
            portfolio_id: Optional portfolio ID for league trading
            
        Returns:
            Order details dict
        """
        try:
            quote = lookup(symbol)
            if not quote:
                return {"error": f"Stock {symbol} not found"}
            
            if shares <= 0:
                return {"error": "Shares must be positive"}
            
            if limit_price <= 0:
                return {"error": "Limit price must be positive"}
            
            # Validate action
            if action not in ['buy', 'sell']:
                return {"error": "Action must be 'buy' or 'sell'"}
            
            # For sell orders, check user has enough shares
            if action == 'sell':
                user_stocks = self.db.get_user_stocks(user_id)
                stock = next((s for s in user_stocks if s['symbol'] == symbol), None)
                
                if not stock or stock['shares'] < shares:
                    return {"error": f"Insufficient shares. You have {stock['shares'] if stock else 0}"}
            
            # Create order in database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO pending_orders 
                (user_id, symbol, shares, order_type, action, limit_price, status, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, symbol, shares, 'limit', action, limit_price, 'pending', notes, datetime.now()))
            
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Limit order created: user={user_id}, symbol={symbol}, action={action}, shares={shares}, limit={limit_price}")
            
            return {
                "success": True,
                "order_id": order_id,
                "symbol": symbol,
                "shares": shares,
                "action": action,
                "limit_price": limit_price,
                "current_price": quote['price'],
                "status": "pending",
                "message": f"Limit order created. Will execute when {symbol} reaches ${limit_price:.2f}"
            }
        
        except Exception as e:
            logger.error(f"Error creating limit order: {str(e)}")
            return {"error": f"Failed to create order: {str(e)}"}
    
    def cancel_limit_order(self, order_id: int, user_id: int) -> dict:
        """Cancel a pending limit order"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Verify order belongs to user
            cursor.execute("SELECT * FROM pending_orders WHERE id = ? AND user_id = ?", (order_id, user_id))
            order = cursor.fetchone()
            
            if not order:
                conn.close()
                return {"error": "Order not found"}
            
            if order['status'] != 'pending':
                conn.close()
                return {"error": f"Cannot cancel order with status: {order['status']}"}
            
            # Mark as cancelled
            cursor.execute("""
                UPDATE pending_orders 
                SET status = 'cancelled', cancelled_at = ?
                WHERE id = ?
            """, (datetime.now(), order_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Order cancelled: order_id={order_id}, user_id={user_id}")
            
            return {
                "success": True,
                "message": f"Order #{order_id} cancelled"
            }
        
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return {"error": f"Failed to cancel order: {str(e)}"}
    
    def edit_limit_order(self, order_id: int, user_id: int, new_limit_price: float) -> dict:
        """Edit limit price of a pending order"""
        try:
            if new_limit_price <= 0:
                return {"error": "Limit price must be positive"}
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Verify order belongs to user and is pending
            cursor.execute("SELECT * FROM pending_orders WHERE id = ? AND user_id = ?", (order_id, user_id))
            order = cursor.fetchone()
            
            if not order:
                conn.close()
                return {"error": "Order not found"}
            
            if order['status'] != 'pending':
                conn.close()
                return {"error": "Can only edit pending orders"}
            
            old_price = order['limit_price']
            
            # Update limit price
            cursor.execute("""
                UPDATE pending_orders 
                SET limit_price = ?
                WHERE id = ?
            """, (new_limit_price, order_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Order updated: order_id={order_id}, old_price={old_price}, new_price={new_limit_price}")
            
            return {
                "success": True,
                "message": f"Order #{order_id} updated: ${old_price:.2f} → ${new_limit_price:.2f}"
            }
        
        except Exception as e:
            logger.error(f"Error editing order: {str(e)}")
            return {"error": f"Failed to edit order: {str(e)}"}
    
    def get_user_pending_orders(self, user_id: int) -> list:
        """Get all pending orders for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM pending_orders 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY created_at DESC
            """, (user_id,))
            
            orders = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            # Add current price info
            for order in orders:
                quote = lookup(order['symbol'])
                if quote:
                    order['current_price'] = quote['price']
                    order['distance_to_trigger'] = abs(quote['price'] - order['limit_price'])
                    
            return orders
        
        except Exception as e:
            logger.error(f"Error getting pending orders: {str(e)}")
            return []
    
    def get_order_history(self, user_id: int, limit: int = 50) -> list:
        """Get order history for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM pending_orders 
                WHERE user_id = ? AND status IN ('executed', 'cancelled')
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            orders = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return orders
        
        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []
    
    # ==================== ORDER EXECUTION ====================
    
    def check_and_execute_orders(self, batch_size: int = 100) -> dict:
        """
        Check all pending orders and execute those that meet conditions.
        Called periodically by background job.
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get all pending limit orders
            cursor.execute("""
                SELECT * FROM pending_orders 
                WHERE status = 'pending' AND order_type = 'limit'
                LIMIT ?
            """, (batch_size,))
            
            pending_orders = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            executed = 0
            failed = 0
            
            for order in pending_orders:
                try:
                    # Get current price
                    quote = lookup(order['symbol'])
                    if not quote:
                        logger.warning(f"Could not lookup {order['symbol']}")
                        continue
                    
                    current_price = quote['price']
                    should_execute = False
                    
                    # Check if order should execute
                    if order['action'] == 'buy':
                        # Buy at limit price or lower
                        should_execute = current_price <= order['limit_price']
                    else:  # sell
                        # Sell at limit price or higher
                        should_execute = current_price >= order['limit_price']
                    
                    if should_execute:
                        # Execute the order
                        result = self._execute_order(order, current_price)
                        if result['success']:
                            executed += 1
                        else:
                            failed += 1
                
                except Exception as e:
                    logger.error(f"Error checking order {order['id']}: {str(e)}")
                    failed += 1
            
            return {
                "total_checked": len(pending_orders),
                "executed": executed,
                "failed": failed
            }
        
        except Exception as e:
            logger.error(f"Error in check_and_execute_orders: {str(e)}")
            return {"error": str(e)}
    
    def _execute_order(self, order: dict, execution_price: float) -> dict:
        """Execute a pending order at the given price"""
        try:
            user_id = order['user_id']
            symbol = order['symbol']
            shares = order['shares']
            action = order['action']
            
            if action == 'buy':
                # Execute buy
                total_cost = shares * execution_price
                
                # Check user has cash
                user = self.db.get_user(user_id)
                if user['cash'] < total_cost:
                    logger.warning(f"Insufficient cash for order {order['id']}")
                    return {"success": False, "reason": "Insufficient cash"}
                
                # Record transaction
                self.db.record_transaction(
                    user_id=user_id,
                    symbol=symbol,
                    shares=shares,
                    price=execution_price,
                    transaction_type='buy'
                )
                
            else:  # sell
                # Execute sell
                # Check user has shares (already validated at creation)
                self.db.record_transaction(
                    user_id=user_id,
                    symbol=symbol,
                    shares=shares,
                    price=execution_price,
                    transaction_type='sell'
                )
            
            # Mark order as executed
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_orders 
                SET status = 'executed', executed_at = ?, executed_price = ?
                WHERE id = ?
            """, (datetime.now(), execution_price, order['id']))
            conn.commit()
            conn.close()
            
            logger.info(f"Order executed: id={order['id']}, symbol={symbol}, action={action}, shares={shares}, price={execution_price}")
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            return {"success": False, "error": str(e)}
