import sqlite3
from datetime import datetime


class DatabaseManager:
    """Manages all database operations for the stock trading app."""
    def __init__(self, db_path="database/stocks.db"):
        self.db_path = db_path
        self.init_db()
        self.init_chat_table()
        self.init_activity_reactions_table()

    def init_chat_table(self):
        """Initialize chat messages table."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                user_id INTEGER,
                username TEXT NOT NULL,
                message TEXT,
                type TEXT DEFAULT 'text',
                filedata TEXT,
                filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_room ON chat_messages(room, created_at DESC)
        ''')
        conn.commit()
        conn.close()

    def insert_chat_message(self, room, username, message, msg_type='text', filedata=None, filename=None, user_id=None):
        """Insert a new chat message."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages (room, user_id, username, message, type, filedata, filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (room, user_id, username, message, msg_type, filedata, filename))
        conn.commit()
        conn.close()

    def get_chat_history(self, room, limit=100):
        """Get chat history for a room."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, message, type, filedata, filename, created_at FROM chat_messages
            WHERE room = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (room, limit))
        rows = cursor.fetchall()
        conn.close()
        # Return in chronological order
        return [dict(row) for row in reversed(rows)]

    def get_user_conversations(self, user_id):
        """Get list of conversations (direct messages and leagues) for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        conversations = []
        
        # Get friends for direct messages
        cursor.execute('''
            SELECT u.id, u.username
            FROM users u
            JOIN friends f ON (f.friend_id = u.id OR f.user_id = u.id)
            WHERE (f.user_id = ? OR f.friend_id = ?)
            AND f.status = 'accepted'
            AND u.id != ?
        ''', (user_id, user_id, user_id))
        
        friends = cursor.fetchall()
        for friend in friends:
            # Generate consistent room ID (lower ID first)
            room_id = f'dm_{min(user_id, friend[0])}_{max(user_id, friend[0])}'
            conversations.append({
                'type': 'dm',
                'id': room_id,
                'name': friend[1],
                'user_id': friend[0]
            })
        
        # Get league conversations
        cursor.execute('''
            SELECT l.id, l.name
            FROM leagues l
            JOIN league_members lm ON l.id = lm.league_id
            WHERE lm.user_id = ?
            AND l.is_active = 1
            ORDER BY l.name
        ''', (user_id,))
        
        leagues = cursor.fetchall()
        for league in leagues:
            conversations.append({
                'type': 'league',
                'id': f'league_{league[0]}',
                'name': league[1],
                'league_id': league[0]
            })
        
        conn.close()
        return conversations

    def get_portfolio_snapshots(self, user_id, limit=90):
        """Get recent portfolio snapshots for a user (limit N)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT total_value, cash, stocks_json, timestamp
            FROM portfolio_snapshots
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        snapshots = cursor.fetchall()
        conn.close()
        return [dict(row) for row in snapshots]

    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database with required tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ============ CORE TABLES ============
        
        # Create users table (enhanced with profile fields)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                hash TEXT NOT NULL,
                email TEXT,
                cash NUMERIC NOT NULL DEFAULT 10000.00,
                bio TEXT,
                avatar_url TEXT,
                is_public INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price NUMERIC NOT NULL,
                type TEXT NOT NULL,
                strategy TEXT,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Pending orders table for advanced order types
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                order_type TEXT NOT NULL,
                action TEXT NOT NULL,
                limit_price NUMERIC,
                stop_price NUMERIC,
                trailing_percent NUMERIC,
                trailing_amount NUMERIC,
                status TEXT DEFAULT 'pending',
                expiration TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Portfolio snapshots for historical tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_value NUMERIC NOT NULL,
                cash NUMERIC NOT NULL,
                stocks_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                added_price NUMERIC,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, symbol)
            )
        """)
        
        # Price alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                target_price NUMERIC NOT NULL,
                alert_type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # ============ SOCIAL TABLES ============
        
        # Friends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (friend_id) REFERENCES users(id),
                UNIQUE(user_id, friend_id)
            )
        """)
        
        # Social posts/feed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'text',
                related_data TEXT,
                likes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Post comments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Post likes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(post_id, user_id)
            )
        """)
        
        # ============ LEAGUE TABLES ============
        
        # Leagues
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                creator_id INTEGER NOT NULL,
                league_type TEXT DEFAULT 'public',
                starting_cash NUMERIC DEFAULT 10000.00,
                settings_json TEXT,
                invite_code TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                season_start TIMESTAMP,
                season_end TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (creator_id) REFERENCES users(id)
            )
        """)
        
        # League members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_rank INTEGER,
                score NUMERIC DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(league_id, user_id)
            )
        """)
        
        # League chat messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # ============ LEAGUE COMPETITION TABLES ============
        
        # League portfolios - isolated cash balance per league member
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                cash NUMERIC NOT NULL DEFAULT 10000.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                locked_at TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(league_id, user_id)
            )
        """)
        
        # League holdings - stock positions per league member
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL DEFAULT 0,
                avg_cost NUMERIC NOT NULL DEFAULT 0,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(league_id, user_id, symbol)
            )
        """)
        
        # League transactions - trade history per league
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price NUMERIC NOT NULL,
                type TEXT NOT NULL,
                fee NUMERIC DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # League portfolio snapshots - for historical rankings and audits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                total_value NUMERIC NOT NULL,
                cash NUMERIC NOT NULL,
                holdings_json TEXT,
                snapshot_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(league_id, user_id, snapshot_date)
            )
        """)
        
        # ============ GAME MODE TABLES ============
        
        # Challenges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                challenge_type TEXT NOT NULL,
                rules_json TEXT,
                creator_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                reward_json TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(id)
            )
        """)
        
        # Challenge participants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenge_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                score NUMERIC DEFAULT 0,
                rank INTEGER,
                completed INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (challenge_id) REFERENCES challenges(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(challenge_id, user_id)
            )
        """)
        
        # ============ ACHIEVEMENT TABLES ============
        
        # Achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                category TEXT,
                icon TEXT,
                rarity TEXT DEFAULT 'common',
                criteria_json TEXT,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 100,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id),
                UNIQUE(user_id, achievement_id)
            )
        """)
        
        # ============ NOTIFICATION TABLES ============
        
        # Notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT,
                content TEXT,
                related_data TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # ============ LEADERBOARD TABLES ============
        
        # Leaderboard cache (for performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leaderboards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leaderboard_type TEXT NOT NULL,
                period TEXT NOT NULL,
                data_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(leaderboard_type, period)
            )
        """)
        
        # ============ MESSAGING TABLES ============
        
        # Direct messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        """)
        
        # ============ OPTIONS TABLES ============
        
        # Options contracts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strike_price NUMERIC NOT NULL,
                expiration_date DATE NOT NULL,
                option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, strike_price, expiration_date, option_type)
            )
        """)
        
        # User options positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                contracts INTEGER NOT NULL,
                avg_premium NUMERIC NOT NULL,
                position_type TEXT NOT NULL CHECK(position_type IN ('long', 'short')),
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                status TEXT DEFAULT 'open' CHECK(status IN ('open', 'closed', 'expired', 'exercised', 'assigned')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (contract_id) REFERENCES options_contracts(id)
            )
        """)
        
        # Options transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                position_id INTEGER NOT NULL,
                contract_id INTEGER NOT NULL,
                contracts INTEGER NOT NULL,
                premium NUMERIC NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('buy', 'sell', 'exercise', 'expire')),
                total_cost NUMERIC NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (position_id) REFERENCES options_positions(id),
                FOREIGN KEY (contract_id) REFERENCES options_contracts(id)
            )
        """)
        
        # ============ NEWS TABLES ============
        
        # News articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                headline TEXT NOT NULL,
                summary TEXT,
                source TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                image_url TEXT,
                published_at TIMESTAMP NOT NULL,
                sentiment_score NUMERIC,
                sentiment_label TEXT CHECK(sentiment_label IN ('positive', 'neutral', 'negative')),
                category TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(url)
            )
        """)
        
        # User news preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, symbol)
            )
        """)
        
        # ============ SOCIAL TRADING TABLES ============
        
        # Following relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trader_following (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                trader_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (follower_id) REFERENCES users(id),
                FOREIGN KEY (trader_id) REFERENCES users(id),
                UNIQUE(follower_id, trader_id)
            )
        """)
        
        # Copy trading settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS copy_trading (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                trader_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                allocation_percentage NUMERIC DEFAULT 10.0,
                max_trade_amount NUMERIC DEFAULT 1000.0,
                copy_buys INTEGER DEFAULT 1,
                copy_sells INTEGER DEFAULT 1,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stopped_at TIMESTAMP,
                FOREIGN KEY (follower_id) REFERENCES users(id),
                FOREIGN KEY (trader_id) REFERENCES users(id),
                UNIQUE(follower_id, trader_id)
            )
        """)
        
        # Copied trades tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS copied_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                trader_id INTEGER NOT NULL,
                original_transaction_id INTEGER NOT NULL,
                copied_transaction_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price NUMERIC NOT NULL,
                type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (follower_id) REFERENCES users(id),
                FOREIGN KEY (trader_id) REFERENCES users(id),
                FOREIGN KEY (original_transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (copied_transaction_id) REFERENCES transactions(id)
            )
        """)
        
        # Trader statistics table (cached performance metrics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trader_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate NUMERIC DEFAULT 0,
                total_return NUMERIC DEFAULT 0,
                avg_return_per_trade NUMERIC DEFAULT 0,
                risk_score NUMERIC DEFAULT 0,
                sharpe_ratio NUMERIC DEFAULT 0,
                max_drawdown NUMERIC DEFAULT 0,
                followers_count INTEGER DEFAULT 0,
                copiers_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # ============ INDEXES FOR PERFORMANCE ============
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_transactions ON transactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_orders_user ON pending_orders(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_orders_status ON pending_orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_orders_symbol ON pending_orders(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_status ON friends(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_members ON league_members(league_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_user ON league_members(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenges_active ON challenges(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_positions_user ON options_positions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_positions_status ON options_positions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_contracts_symbol ON options_contracts(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_contracts_expiration ON options_contracts(expiration_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_symbol ON news_articles(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader_following_follower ON trader_following(follower_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader_following_trader ON trader_following(trader_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copy_trading_follower ON copy_trading(follower_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copy_trading_trader ON copy_trading(trader_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copy_trading_active ON copy_trading(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader_stats_return ON trader_stats(total_return)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader_stats_win_rate ON trader_stats(win_rate)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots ON portfolio_snapshots(user_id, timestamp)")
        
        # League competition indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_portfolios ON league_portfolios(league_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_holdings ON league_holdings(league_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_holdings_symbol ON league_holdings(league_id, symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_transactions ON league_transactions(league_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_transactions_time ON league_transactions(league_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_snapshots ON league_portfolio_snapshots(league_id, user_id, snapshot_date)")
        
        # ============ MIGRATIONS ============
        # Add strategy and notes columns to transactions if they don't exist
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN strategy TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'dark'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # League competition migrations
        try:
            cursor.execute("ALTER TABLE leagues ADD COLUMN lifecycle_state TEXT DEFAULT 'active'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE leagues ADD COLUMN mode TEXT DEFAULT 'absolute_value'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE leagues ADD COLUMN rules_json TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create index on lifecycle_state column (after migration adds it)
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leagues_state ON leagues(lifecycle_state)")
        except sqlite3.OperationalError:
            pass  # Index or column might not exist yet
        
        conn.commit()
        conn.close()
        
        # Seed default challenges if none exist
        self._seed_default_challenges()
    
    def _seed_default_challenges(self):
        """Create default challenges if none exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if challenges exist
        cursor.execute("SELECT COUNT(*) as count FROM challenges")
        count = cursor.fetchone()['count']
        
        if count == 0:
            import json
            from datetime import datetime, timedelta
            
            # Default challenges
            default_challenges = [
                {
                    'name': 'Profit Rookie',
                    'description': 'Make your first $500 profit! Perfect for beginners.',
                    'challenge_type': 'profit_target',
                    'rules': {'target_profit': 500},
                    'duration_days': 30,
                    'reward': {'cash': 100, 'achievement': 'First Profit', 'badge': '💰'}
                },
                {
                    'name': 'Active Trader',
                    'description': 'Complete 20 trades to master the basics.',
                    'challenge_type': 'trade_volume',
                    'rules': {'target_trades': 20},
                    'duration_days': 14,
                    'reward': {'cash': 150, 'achievement': 'Active Trader', 'badge': '📈'}
                },
                {
                    'name': 'Portfolio Builder',
                    'description': 'Grow your portfolio to $15,000.',
                    'challenge_type': 'portfolio_value',
                    'rules': {'target_value': 15000},
                    'duration_days': 60,
                    'reward': {'cash': 250, 'achievement': 'Portfolio Master', 'badge': '💼'}
                },
                {
                    'name': 'Tech Investor',
                    'description': 'Focus on technology stocks and complete 10 trades.',
                    'challenge_type': 'sector_focus',
                    'rules': {'target_sector': 'Technology', 'min_trades': 10},
                    'duration_days': 21,
                    'reward': {'cash': 200, 'achievement': 'Tech Specialist', 'badge': '💻'}
                },
                {
                    'name': 'Profit Master',
                    'description': 'Advanced challenge: Make $2,500 profit!',
                    'challenge_type': 'profit_target',
                    'rules': {'target_profit': 2500},
                    'duration_days': 45,
                    'reward': {'cash': 500, 'achievement': 'Profit Master', 'badge': '🏆'}
                }
            ]
            
            for challenge in default_challenges:
                start_time = datetime.now()
                end_time = start_time + timedelta(days=challenge['duration_days'])
                
                cursor.execute("""
                    INSERT INTO challenges (name, description, challenge_type, rules_json, 
                                          creator_id, start_time, end_time, reward_json, is_active)
                    VALUES (?, ?, ?, ?, NULL, ?, ?, ?, 1)
                """, (
                    challenge['name'],
                    challenge['description'],
                    challenge['challenge_type'],
                    json.dumps(challenge['rules']),
                    start_time,
                    end_time,
                    json.dumps(challenge['reward'])
                ))
            
            conn.commit()
        
        conn.close()
    
    def create_user(self, username, password_hash):
        """Create a new user and return their ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, password_hash)
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return user_id
    
    def get_user(self, user_id):
        """Get user by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def get_user_by_username(self, username):
        """Get user by username."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def update_cash(self, user_id, new_cash):
        """Update user's cash balance."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            (new_cash, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def record_transaction(self, user_id, symbol, shares, price, transaction_type, strategy=None, notes=None):
        """Record a stock transaction."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, type, strategy, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, symbol, shares, price, transaction_type, strategy, notes)
        )
        txn_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return txn_id
    
    def get_transactions(self, user_id):
        """Get all transactions for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        )
        
        transactions = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in transactions]
    
    def get_user_stocks(self, user_id):
        """Get user's current stock holdings."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, SUM(shares) as shares
            FROM transactions
            WHERE user_id = ?
            GROUP BY symbol
            HAVING SUM(shares) > 0
        """, (user_id,))
        
        stocks = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in stocks]
    
    def get_user_stock(self, user_id, symbol):
        """Get user's holdings of a specific stock."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, SUM(shares) as shares
            FROM transactions
            WHERE user_id = ? AND symbol = ?
            GROUP BY symbol
        """, (user_id, symbol))
        
        stock = cursor.fetchone()
        conn.close()
        
        return dict(stock) if stock else None
    
    # ============ PENDING ORDERS METHODS ============
    
    def create_pending_order(self, user_id, symbol, shares, order_type, action, limit_price=None, stop_price=None, trailing_percent=None, trailing_amount=None, expiration=None, notes=None):
        """Create a new pending order (limit, stop, trailing stop, etc.)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pending_orders 
            (user_id, symbol, shares, order_type, action, limit_price, stop_price, trailing_percent, trailing_amount, expiration, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, symbol, shares, order_type, action, limit_price, stop_price, trailing_percent, trailing_amount, expiration, notes))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return order_id
    
    def get_pending_orders(self, user_id, status='pending'):
        """Get all pending orders for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM pending_orders
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
        """, (user_id, status))
        
        orders = cursor.fetchall()
        conn.close()
        
        return [dict(order) for order in orders]
    
    def get_pending_order(self, order_id):
        """Get a specific pending order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pending_orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        conn.close()
        
        return dict(order) if order else None
    
    def execute_pending_order(self, order_id, execution_price):
        """Mark order as executed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pending_orders
            SET status = 'executed', executed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order_id,))
        
        conn.commit()
        conn.close()
    
    def cancel_pending_order(self, order_id):
        """Cancel a pending order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pending_orders
            SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order_id,))
        
        conn.commit()
        conn.close()
    
    def check_and_execute_orders(self, symbol, current_price):
        """Check all pending orders for a symbol and execute if conditions are met"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all pending orders for this symbol
        cursor.execute("""
            SELECT * FROM pending_orders
            WHERE symbol = ? AND status = 'pending'
        """, (symbol,))
        
        orders = cursor.fetchall()
        executed_orders = []
        
        for order in orders:
            order_dict = dict(order)
            should_execute = False
            
            if order_dict['order_type'] == 'limit':
                # Limit Buy: execute when price <= limit_price
                # Limit Sell: execute when price >= limit_price
                if order_dict['action'] == 'buy' and current_price <= order_dict['limit_price']:
                    should_execute = True
                elif order_dict['action'] == 'sell' and current_price >= order_dict['limit_price']:
                    should_execute = True
            
            elif order_dict['order_type'] == 'stop':
                # Stop Buy: execute when price >= stop_price
                # Stop Sell: execute when price <= stop_price
                if order_dict['action'] == 'buy' and current_price >= order_dict['stop_price']:
                    should_execute = True
                elif order_dict['action'] == 'sell' and current_price <= order_dict['stop_price']:
                    should_execute = True
            
            elif order_dict['order_type'] == 'stop_limit':
                # Stop-Limit: trigger at stop_price, execute at limit_price
                if order_dict['action'] == 'buy' and current_price >= order_dict['stop_price'] and current_price <= order_dict['limit_price']:
                    should_execute = True
                elif order_dict['action'] == 'sell' and current_price <= order_dict['stop_price'] and current_price >= order_dict['limit_price']:
                    should_execute = True
            
            if should_execute:
                executed_orders.append(order_dict)
                self.execute_pending_order(order_dict['id'], current_price)
        
        conn.close()
        return executed_orders
    
    # ============ FRIENDS SYSTEM METHODS ============
    
    def send_friend_request(self, user_id, friend_id):
        """Send a friend request."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending')",
                (user_id, friend_id)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def accept_friend_request(self, user_id, friend_id):
        """Accept a friend request."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Update the existing request
        cursor.execute(
            "UPDATE friends SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
            (friend_id, user_id)
        )
        
        # Create reciprocal friendship
        try:
            cursor.execute(
                "INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'accepted')",
                (user_id, friend_id)
            )
        except sqlite3.IntegrityError:
            pass
        
        conn.commit()
        conn.close()
    
    def decline_friend_request(self, user_id, friend_id):
        """Decline a friend request."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
            (friend_id, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def remove_friend(self, user_id, friend_id):
        """Remove a friend (unfriend)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Remove both directions
        cursor.execute(
            "DELETE FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
            (user_id, friend_id, friend_id, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_friends(self, user_id):
        """Get all accepted friends for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.avatar_url, u.last_active, u.cash
            FROM friends f
            JOIN users u ON f.friend_id = u.id
            WHERE f.user_id = ? AND f.status = 'accepted'
            ORDER BY u.username
        """, (user_id,))
        
        friends = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in friends]
    
    def get_pending_friend_requests(self, user_id):
        """Get pending friend requests for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.avatar_url, f.created_at
            FROM friends f
            JOIN users u ON f.user_id = u.id
            WHERE f.friend_id = ? AND f.status = 'pending'
            ORDER BY f.created_at DESC
        """, (user_id,))
        
        requests = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in requests]
    
    def get_sent_friend_requests(self, user_id):
        """Get friend requests sent by user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.avatar_url, f.created_at
            FROM friends f
            JOIN users u ON f.friend_id = u.id
            WHERE f.user_id = ? AND f.status = 'pending'
            ORDER BY f.created_at DESC
        """, (user_id,))
        
        requests = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in requests]
    
    def are_friends(self, user_id, friend_id):
        """Check if two users are friends."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'accepted'",
            (user_id, friend_id)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def get_friend_requests(self, user_id):
        """Get pending friend requests with full details."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.id, u.id as user_id, u.username, u.avatar_url, f.created_at as timestamp
            FROM friends f
            JOIN users u ON f.user_id = u.id
            WHERE f.friend_id = ? AND f.status = 'pending'
            ORDER BY f.created_at DESC
        """, (user_id,))
        
        requests = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in requests]
    
    def accept_friend_request_by_id(self, request_id):
        """Accept a friend request by its ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get the request details
        cursor.execute("SELECT user_id, friend_id FROM friends WHERE id = ? AND status = 'pending'", (request_id,))
        request = cursor.fetchone()
        
        if request:
            sender_id = request["user_id"]
            receiver_id = request["friend_id"]
            
            # Update the existing request
            cursor.execute(
                "UPDATE friends SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (request_id,)
            )
            
            # Create reciprocal friendship
            try:
                cursor.execute(
                    "INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'accepted')",
                    (receiver_id, sender_id)
                )
            except sqlite3.IntegrityError:
                pass
            
            conn.commit()
        
        conn.close()
    
    def decline_friend_request_by_id(self, request_id):
        """Decline a friend request by its ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM friends WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        
        conn.commit()
        conn.close()
    
    # ============ LEAGUE SYSTEM METHODS ============
    
    def create_league(self, name, description, creator_id, league_type='public', starting_cash=10000.00, settings_json=None):
        """Create a new league."""
        import secrets
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        invite_code = secrets.token_urlsafe(8)
        
        cursor.execute("""
            INSERT INTO leagues (name, description, creator_id, league_type, starting_cash, settings_json, invite_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, creator_id, league_type, starting_cash, settings_json, invite_code))
        
        league_id = cursor.lastrowid
        
        # Auto-join creator as admin
        cursor.execute("""
            INSERT INTO league_members (league_id, user_id, is_admin)
            VALUES (?, ?, 1)
        """, (league_id, creator_id))
        
        conn.commit()
        conn.close()
        
        return league_id, invite_code
    
    def join_league(self, league_id, user_id):
        """Join a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO league_members (league_id, user_id)
                VALUES (?, ?)
            """, (league_id, user_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def leave_league(self, league_id, user_id):
        """Leave a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM league_members WHERE league_id = ? AND user_id = ?",
            (league_id, user_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_user_leagues(self, user_id):
        """Get all leagues a user is a member of."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, lm.current_rank, lm.score, lm.is_admin
            FROM leagues l
            JOIN league_members lm ON l.id = lm.league_id
            WHERE lm.user_id = ? AND l.is_active = 1
            ORDER BY lm.joined_at DESC
        """, (user_id,))
        
        leagues = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in leagues]
    
    def get_league(self, league_id):
        """Get league details."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
        league = cursor.fetchone()
        conn.close()
        
        return dict(league) if league else None
    
    def get_league_by_invite_code(self, invite_code):
        """Get league by invite code."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM leagues WHERE invite_code = ?", (invite_code,))
        league = cursor.fetchone()
        conn.close()
        
        return dict(league) if league else None
    
    def get_league_leaderboard(self, league_id):
        """Get leaderboard for a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.avatar_url, lm.score, lm.current_rank
            FROM league_members lm
            JOIN users u ON lm.user_id = u.id
            WHERE lm.league_id = ?
            ORDER BY lm.score DESC, lm.joined_at ASC
        """, (league_id,))
        
        leaderboard = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in leaderboard]
    
    def update_league_scores(self, league_id):
        """Update scores and ranks for all members in a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all members and their portfolio values
        cursor.execute("""
            SELECT lm.user_id, u.cash
            FROM league_members lm
            JOIN users u ON lm.user_id = u.id
            WHERE lm.league_id = ?
        """, (league_id,))
        
        members = cursor.fetchall()
        
        # Calculate scores (would include stock values in real implementation)
        scores = []
        for member in members:
            user_id = member['user_id']
            # Get total portfolio value
            stocks = self.get_user_stocks(user_id)
            # Note: In real implementation, fetch current prices
            total_value = member['cash']  # + stock values
            scores.append((total_value, user_id))
        
        # Sort by score descending
        scores.sort(reverse=True)
        
        # Update ranks
        for rank, (score, user_id) in enumerate(scores, 1):
            cursor.execute("""
                UPDATE league_members
                SET score = ?, current_rank = ?
                WHERE league_id = ? AND user_id = ?
            """, (score, rank, league_id, user_id))
        
        conn.commit()
        conn.close()
    
    def start_league_season(self, league_id, duration_days=30):
        """Start a new season for a league."""
        from datetime import datetime, timedelta
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        season_end = now + timedelta(days=duration_days)
        
        cursor.execute("""
            UPDATE leagues
            SET season_start = ?, season_end = ?, is_active = 1
            WHERE id = ?
        """, (now, season_end, league_id))
        
        # Reset all member scores
        cursor.execute("""
            UPDATE league_members
            SET score = 0, current_rank = NULL
            WHERE league_id = ?
        """, (league_id,))
        
        conn.commit()
        conn.close()
    
    def end_league_season(self, league_id):
        """End current season and archive winners."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get final rankings
        cursor.execute("""
            SELECT user_id, current_rank, score
            FROM league_members
            WHERE league_id = ?
            ORDER BY current_rank ASC
            LIMIT 10
        """, (league_id,))
        
        winners = cursor.fetchall()
        
        # Mark season as ended
        cursor.execute("""
            UPDATE leagues
            SET is_active = 0
            WHERE id = ?
        """, (league_id,))
        
        # Create notifications for top 3
        league = self.get_league(league_id)
        for winner in winners[:3]:
            if winner['current_rank'] == 1:
                title = "🏆 League Champion!"
                message = f"Congratulations! You won {league['name']}!"
            elif winner['current_rank'] == 2:
                title = "🥈 Second Place!"
                message = f"Great job! You placed 2nd in {league['name']}!"
            elif winner['current_rank'] == 3:
                title = "🥉 Third Place!"
                message = f"Well done! You placed 3rd in {league['name']}!"
            
            self.create_notification(
                winner['user_id'],
                'league_result',
                title,
                message,
                str(league_id)
            )
        
        conn.commit()
        conn.close()
        
        return [dict(w) for w in winners]
    
    # ============ LEAGUE PORTFOLIO METHODS ============
    
    def get_league_portfolio(self, league_id, user_id):
        """Get a user's portfolio within a specific league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM league_portfolios
            WHERE league_id = ? AND user_id = ?
        """, (league_id, user_id))
        
        portfolio = cursor.fetchone()
        conn.close()
        
        return dict(portfolio) if portfolio else None
    
    def create_league_portfolio(self, league_id, user_id, starting_cash):
        """Create a new league portfolio for a user when joining."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO league_portfolios (league_id, user_id, cash)
                VALUES (?, ?, ?)
            """, (league_id, user_id, starting_cash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already exists
        finally:
            conn.close()
    
    def update_league_cash(self, league_id, user_id, new_cash):
        """Update a user's cash balance within a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE league_portfolios
            SET cash = ?
            WHERE league_id = ? AND user_id = ?
        """, (new_cash, league_id, user_id))
        
        conn.commit()
        conn.close()
    
    def get_league_holdings(self, league_id, user_id):
        """Get all stock holdings for a user within a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, shares, avg_cost
            FROM league_holdings
            WHERE league_id = ? AND user_id = ? AND shares > 0
        """, (league_id, user_id))
        
        holdings = cursor.fetchall()
        conn.close()
        
        return [dict(h) for h in holdings]
    
    def get_league_holding(self, league_id, user_id, symbol):
        """Get a specific stock holding within a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, shares, avg_cost
            FROM league_holdings
            WHERE league_id = ? AND user_id = ? AND symbol = ?
        """, (league_id, user_id, symbol))
        
        holding = cursor.fetchone()
        conn.close()
        
        return dict(holding) if holding else None
    
    def update_league_holding(self, league_id, user_id, symbol, shares_delta, price):
        """Update or create a stock holding within a league.
        
        Args:
            league_id: League ID
            user_id: User ID
            symbol: Stock symbol
            shares_delta: Positive for buy, negative for sell
            price: Price per share for this transaction
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current holding
        cursor.execute("""
            SELECT shares, avg_cost FROM league_holdings
            WHERE league_id = ? AND user_id = ? AND symbol = ?
        """, (league_id, user_id, symbol))
        
        existing = cursor.fetchone()
        
        if existing:
            old_shares = existing['shares']
            old_avg = existing['avg_cost']
            new_shares = old_shares + shares_delta
            
            # Calculate new average cost (only on buys)
            if shares_delta > 0:
                total_old_value = old_shares * old_avg
                total_new_value = shares_delta * price
                new_avg = (total_old_value + total_new_value) / new_shares if new_shares > 0 else 0
            else:
                new_avg = old_avg  # Keep avg cost on sells
            
            if new_shares > 0:
                cursor.execute("""
                    UPDATE league_holdings
                    SET shares = ?, avg_cost = ?
                    WHERE league_id = ? AND user_id = ? AND symbol = ?
                """, (new_shares, new_avg, league_id, user_id, symbol))
            else:
                # Remove holding if shares = 0
                cursor.execute("""
                    DELETE FROM league_holdings
                    WHERE league_id = ? AND user_id = ? AND symbol = ?
                """, (league_id, user_id, symbol))
        else:
            # Create new holding
            if shares_delta > 0:
                cursor.execute("""
                    INSERT INTO league_holdings (league_id, user_id, symbol, shares, avg_cost)
                    VALUES (?, ?, ?, ?, ?)
                """, (league_id, user_id, symbol, shares_delta, price))
        
        conn.commit()
        conn.close()
    
    def record_league_transaction(self, league_id, user_id, symbol, shares, price, txn_type, fee=0):
        """Record a transaction within a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO league_transactions (league_id, user_id, symbol, shares, price, type, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (league_id, user_id, symbol, shares, price, txn_type, fee))
        
        txn_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return txn_id
    
    def get_league_transactions(self, league_id, user_id=None, limit=100):
        """Get transactions for a league, optionally filtered by user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT lt.*, u.username
                FROM league_transactions lt
                JOIN users u ON lt.user_id = u.id
                WHERE lt.league_id = ? AND lt.user_id = ?
                ORDER BY lt.timestamp DESC
                LIMIT ?
            """, (league_id, user_id, limit))
        else:
            cursor.execute("""
                SELECT lt.*, u.username
                FROM league_transactions lt
                JOIN users u ON lt.user_id = u.id
                WHERE lt.league_id = ?
                ORDER BY lt.timestamp DESC
                LIMIT ?
            """, (league_id, limit))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return [dict(t) for t in transactions]
    
    def create_league_portfolio_snapshot(self, league_id, user_id, total_value, cash, holdings_json):
        """Create a daily snapshot of a user's league portfolio."""
        from datetime import date
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO league_portfolio_snapshots 
                (league_id, user_id, total_value, cash, holdings_json, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (league_id, user_id, total_value, cash, holdings_json, today))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Snapshot already exists for today
        finally:
            conn.close()
    
    def get_league_portfolio_snapshots(self, league_id, user_id, limit=30):
        """Get historical portfolio snapshots for a user in a league."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM league_portfolio_snapshots
            WHERE league_id = ? AND user_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """, (league_id, user_id, limit))
        
        snapshots = cursor.fetchall()
        conn.close()
        
        return [dict(s) for s in snapshots]
    
    def set_league_lifecycle_state(self, league_id, new_state):
        """Update the lifecycle state of a league.
        
        Valid states: draft, open, locked, active, finished
        """
        valid_states = ['draft', 'open', 'locked', 'active', 'finished']
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}. Must be one of {valid_states}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE leagues
            SET lifecycle_state = ?
            WHERE id = ?
        """, (new_state, league_id))
        
        # Also update is_active for backwards compatibility
        is_active = 1 if new_state in ['open', 'active'] else 0
        cursor.execute("""
            UPDATE leagues SET is_active = ? WHERE id = ?
        """, (is_active, league_id))
        
        conn.commit()
        conn.close()
    
    def get_leagues_by_state(self, state, limit=50):
        """Get leagues by lifecycle state."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, u.username as creator_name,
                   COUNT(lm.id) as member_count
            FROM leagues l
            JOIN users u ON l.creator_id = u.id
            LEFT JOIN league_members lm ON l.id = lm.league_id
            WHERE l.lifecycle_state = ?
            GROUP BY l.id
            ORDER BY l.created_at DESC
            LIMIT ?
        """, (state, limit))
        
        leagues = cursor.fetchall()
        conn.close()
        
        return [dict(l) for l in leagues]
    
    def lock_league_portfolios(self, league_id):
        """Lock all portfolios in a league (when it finishes)."""
        from datetime import datetime
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE league_portfolios
            SET locked_at = ?
            WHERE league_id = ?
        """, (datetime.now(), league_id))
        
        conn.commit()
        conn.close()
    
    def is_league_portfolio_locked(self, league_id, user_id):
        """Check if a user's league portfolio is locked."""
        portfolio = self.get_league_portfolio(league_id, user_id)
        return portfolio and portfolio.get('locked_at') is not None
    
    def calculate_league_portfolio_value(self, league_id, user_id, price_lookup_func):
        """Calculate total portfolio value for a user in a league.
        
        Args:
            league_id: League ID
            user_id: User ID  
            price_lookup_func: Function that takes a symbol and returns current price
        
        Returns:
            Total portfolio value (cash + stocks)
        """
        portfolio = self.get_league_portfolio(league_id, user_id)
        if not portfolio:
            return 0
        
        total = portfolio['cash']
        holdings = self.get_league_holdings(league_id, user_id)
        
        for holding in holdings:
            price = price_lookup_func(holding['symbol'])
            if price:
                total += holding['shares'] * price
        
        return total
    
    def update_league_scores_v2(self, league_id, price_lookup_func):
        """Update scores and ranks for all members using league portfolios.
        
        This version uses league-isolated portfolios instead of global portfolios.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get league to check mode
        league = self.get_league(league_id)
        mode = league.get('mode', 'absolute_value') if league else 'absolute_value'
        starting_cash = league.get('starting_cash', 10000.0) if league else 10000.0
        
        # Get all members
        cursor.execute("""
            SELECT user_id FROM league_members WHERE league_id = ?
        """, (league_id,))
        
        members = cursor.fetchall()
        scores = []
        
        for member in members:
            user_id = member['user_id']
            total_value = self.calculate_league_portfolio_value(league_id, user_id, price_lookup_func)
            
            # Calculate score based on mode
            if mode == 'percentage_return':
                # Percentage return from starting cash
                score = ((total_value - starting_cash) / starting_cash) * 100 if starting_cash > 0 else 0
            else:
                # absolute_value (default) - just use total value
                score = total_value
            
            scores.append((score, total_value, user_id))
        
        # Sort by score descending, then by total_value as tiebreaker
        scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # Update ranks
        for rank, (score, total_value, user_id) in enumerate(scores, 1):
            cursor.execute("""
                UPDATE league_members
                SET score = ?, current_rank = ?
                WHERE league_id = ? AND user_id = ?
            """, (score, rank, league_id, user_id))
        
        conn.commit()
        conn.close()
    
    def get_active_leagues(self, limit=20):
        """Get all active public leagues."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, u.username as creator_name,
                   COUNT(lm.id) as member_count
            FROM leagues l
            JOIN users u ON l.creator_id = u.id
            LEFT JOIN league_members lm ON l.id = lm.league_id
            WHERE l.is_active = 1 AND l.league_type = 'public'
            GROUP BY l.id
            ORDER BY l.created_at DESC
            LIMIT ?
        """, (limit,))
        
        leagues = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in leagues]
    
    def get_league_members(self, league_id):
        """Get all members of a league with their stats."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.avatar_url, u.cash,
                   lm.score, lm.current_rank, lm.is_admin, lm.joined_at
            FROM league_members lm
            JOIN users u ON lm.user_id = u.id
            WHERE lm.league_id = ?
            ORDER BY lm.current_rank ASC NULLS LAST, lm.score DESC
        """, (league_id,))
        
        members = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in members]
    
    # ============ NOTIFICATION METHODS ============
    
    def create_notification(self, user_id, notification_type, title, content, related_data=None):
        """Create a notification for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, title, content, related_data)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, notification_type, title, content, related_data))
        
        conn.commit()
        conn.close()
    
    def get_notifications(self, user_id, unread_only=False, limit=50):
        """Get notifications for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if unread_only:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE user_id = ? AND is_read = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
        
        notifications = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in notifications]
    
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?",
            (notification_id,)
        )
        
        conn.commit()
        conn.close()
    
    def mark_all_notifications_read(self, user_id):
        """Mark all notifications as read for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
    
    # ============ USER PROFILE METHODS ============
    
    def update_user_profile(self, user_id, **kwargs):
        """Update user profile fields."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['bio', 'avatar_url', 'is_public', 'email']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if fields:
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def search_users(self, query, limit=20):
        """Search users by username."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, avatar_url, bio
            FROM users
            WHERE username LIKE ? AND is_public = 1
            ORDER BY username
            LIMIT ?
        """, (f"%{query}%", limit))
        
        users = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in users]
    
    # ============ ACHIEVEMENT METHODS ============
    
    def has_achievement(self, user_id, achievement_key):
        """Check if user has a specific achievement"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ? AND a.name = ?
        """, (user_id, achievement_key))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def award_achievement(self, user_id, achievement_key, title, description):
        """Award an achievement to a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # First, ensure the achievement exists in the master table
            cursor.execute(
                "INSERT OR IGNORE INTO achievements (name, description, category) VALUES (?, ?, ?)",
                (achievement_key, description, 'trading')
            )
            
            # Get the achievement ID
            cursor.execute("SELECT id FROM achievements WHERE name = ?", (achievement_key,))
            achievement_id = cursor.fetchone()[0]
            
            # Award it to the user
            cursor.execute(
                "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                (user_id, achievement_id)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Achievement already awarded
        
        conn.close()
    
    def get_achievements(self, user_id):
        """Get all achievements for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.name, a.description, a.category, a.icon, a.rarity, a.points,
                   ua.unlocked_at, ua.progress
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
        """, (user_id,))
        
        achievements = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in achievements]
    
    # ============ WATCHLIST METHODS ============
    
    def add_to_watchlist(self, user_id, symbol, added_price=None, notes=None):
        """Add a stock to user's watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO watchlist (user_id, symbol, added_price, notes) VALUES (?, ?, ?, ?)",
                (user_id, symbol.upper(), added_price, notes)
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False  # Already in watchlist
        
        conn.close()
        return result
    
    def remove_from_watchlist(self, user_id, symbol):
        """Remove a stock from user's watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
            (user_id, symbol.upper())
        )
        
        conn.commit()
        conn.close()
    
    def get_watchlist(self, user_id):
        """Get user's watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        
        watchlist = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in watchlist]
    
    def is_in_watchlist(self, user_id, symbol):
        """Check if stock is in user's watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND symbol = ?",
            (user_id, symbol.upper())
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    # ============ PORTFOLIO SNAPSHOT METHODS ============
    
    def create_snapshot(self, user_id, total_value, cash, stocks_json=None):
        """Create a portfolio snapshot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO portfolio_snapshots (user_id, total_value, cash, stocks_json) VALUES (?, ?, ?, ?)",
            (user_id, total_value, cash, stocks_json)
        )
        
        conn.commit()
        conn.close()
    
    def get_portfolio_history(self, user_id, days=30):
        """Get portfolio value history for the last N days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_value, cash, timestamp 
            FROM portfolio_snapshots 
            WHERE user_id = ? 
            AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (user_id, days))
        
        history = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in history]
    
    # ============ ACTIVITY FEED METHODS ============
    
    def get_friend_activity(self, user_id, limit=50):
        """Get recent activity from friends (trades and achievements)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get transactions from friends
        cursor.execute("""
            SELECT 
                t.id, t.user_id, u.username, t.symbol, t.shares, t.price, 
                t.type, t.timestamp, 'transaction' as activity_type
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            WHERE t.user_id IN (
                SELECT friend_id FROM friends 
                WHERE user_id = ? AND status = 'accepted'
                UNION
                SELECT user_id FROM friends 
                WHERE friend_id = ? AND status = 'accepted'
            )
            
            UNION ALL
            
            SELECT 
                ua.id, ua.user_id, u.username, NULL as symbol, NULL as shares, 
                NULL as price, a.name as type, ua.unlocked_at as timestamp, 
                'achievement' as activity_type
            FROM user_achievements ua
            JOIN users u ON ua.user_id = u.id
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id IN (
                SELECT friend_id FROM friends 
                WHERE user_id = ? AND status = 'accepted'
                UNION
                SELECT user_id FROM friends 
                WHERE friend_id = ? AND status = 'accepted'
            )
            
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, user_id, user_id, user_id, limit))
        
        activities = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in activities]
    
    # ============ ANALYTICS METHODS ============
    
    def get_trading_stats(self, user_id):
        """Get comprehensive trading statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) as total_trades FROM transactions WHERE user_id = ?", (user_id,))
        total_trades = cursor.fetchone()['total_trades']
        
        # Buy vs Sell count
        cursor.execute("SELECT type, COUNT(*) as count FROM transactions WHERE user_id = ? GROUP BY type", (user_id,))
        trade_types = {row['type']: row['count'] for row in cursor.fetchall()}
        
        # Most traded stock
        cursor.execute("""
            SELECT symbol, COUNT(*) as trade_count 
            FROM transactions 
            WHERE user_id = ? 
            GROUP BY symbol 
            ORDER BY trade_count DESC 
            LIMIT 1
        """, (user_id,))
        most_traded = cursor.fetchone()
        
        # Total volume (shares traded)
        cursor.execute("SELECT SUM(ABS(shares)) as total_volume FROM transactions WHERE user_id = ?", (user_id,))
        total_volume = cursor.fetchone()['total_volume'] or 0
        
        # Average trade size
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
        
        # First trade date
        cursor.execute("SELECT MIN(timestamp) as first_trade FROM transactions WHERE user_id = ?", (user_id,))
        first_trade = cursor.fetchone()['first_trade']
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'buys': trade_types.get('buy', 0),
            'sells': trade_types.get('sell', 0),
            'most_traded_symbol': most_traded['symbol'] if most_traded else None,
            'most_traded_count': most_traded['trade_count'] if most_traded else 0,
            'total_volume': total_volume,
            'avg_trade_size': avg_trade_size,
            'first_trade_date': first_trade
        }
    
    def get_portfolio_breakdown(self, user_id):
        """Get portfolio breakdown by symbol with current values"""
        stocks = self.get_user_stocks(user_id)
        
        breakdown = []
        for stock in stocks:
            breakdown.append({
                'symbol': stock['symbol'],
                'shares': stock['shares']
            })
        
        return breakdown
    
    # ============ PRICE ALERTS METHODS ============
    
    def create_alert(self, user_id, symbol, target_price, alert_type):
        """Create a new price alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO price_alerts (user_id, symbol, target_price, alert_type)
            VALUES (?, ?, ?, ?)
        """, (user_id, symbol.upper(), target_price, alert_type))
        
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        
        return alert_id
    
    def get_user_alerts(self, user_id, status='active'):
        """Get user's price alerts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM price_alerts 
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT * FROM price_alerts 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        alerts = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in alerts]
    
    def delete_alert(self, alert_id, user_id):
        """Delete a price alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM price_alerts 
            WHERE id = ? AND user_id = ?
        """, (alert_id, user_id))
        
        conn.commit()
        conn.close()
    
    def trigger_alert(self, alert_id):
        """Mark an alert as triggered"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE price_alerts 
            SET status = 'triggered', triggered_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (alert_id,))
        
        conn.commit()
        conn.close()
    
    def check_alerts(self, user_id, symbol, current_price):
        """Check if any alerts should be triggered"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM price_alerts 
            WHERE user_id = ? AND symbol = ? AND status = 'active'
        """, (user_id, symbol.upper()))
        
        alerts = cursor.fetchall()
        triggered_alerts = []
        
        for alert in alerts:
            alert_dict = dict(alert)
            if alert_dict['alert_type'] == 'above' and current_price >= alert_dict['target_price']:
                triggered_alerts.append(alert_dict)
                self.trigger_alert(alert_dict['id'])
            elif alert_dict['alert_type'] == 'below' and current_price <= alert_dict['target_price']:
                triggered_alerts.append(alert_dict)
                self.trigger_alert(alert_dict['id'])
        
        conn.close()
        return triggered_alerts
    
    # ============ TRADING STRATEGY METHODS ============
    
    def get_strategies_performance(self, user_id):
        """Get trading performance grouped by strategy"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                strategy,
                COUNT(*) as trade_count,
                SUM(CASE WHEN type = 'buy' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN type = 'sell' THEN 1 ELSE 0 END) as sell_count,
                SUM(ABS(shares * price)) as total_volume
            FROM transactions
            WHERE user_id = ? AND strategy IS NOT NULL
            GROUP BY strategy
            ORDER BY trade_count DESC
        """, (user_id,))
        
        strategies = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in strategies]

    # ============ CHALLENGE MANAGEMENT ============
    
    def create_challenge(self, name, description, challenge_type, rules, creator_id, duration_days, reward):
        """Create a new trading challenge"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        start_time = datetime.now()
        end_time = start_time + timedelta(days=duration_days)
        
        import json
        rules_json = json.dumps(rules)
        reward_json = json.dumps(reward)
        
        cursor.execute("""
            INSERT INTO challenges (name, description, challenge_type, rules_json, 
                                  creator_id, start_time, end_time, reward_json, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (name, description, challenge_type, rules_json, creator_id, start_time, end_time, reward_json))
        
        challenge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return challenge_id
    
    def get_active_challenges(self, limit=50):
        """Get all active challenges"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now()
        
        cursor.execute("""
            SELECT 
                c.*,
                u.username as creator_name,
                COUNT(DISTINCT cp.user_id) as participant_count,
                SUM(CASE WHEN cp.completed = 1 THEN 1 ELSE 0 END) as completed_count
            FROM challenges c
            LEFT JOIN users u ON c.creator_id = u.id
            LEFT JOIN challenge_participants cp ON c.id = cp.challenge_id
            WHERE c.is_active = 1 AND c.end_time > ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (now, limit))
        
        challenges = cursor.fetchall()
        conn.close()
        
        import json
        result = []
        for row in challenges:
            challenge = dict(row)
            challenge['rules'] = json.loads(challenge['rules_json']) if challenge['rules_json'] else {}
            challenge['reward'] = json.loads(challenge['reward_json']) if challenge['reward_json'] else {}
            result.append(challenge)
        
        return result
    
    def get_challenge(self, challenge_id):
        """Get challenge details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.*,
                u.username as creator_name,
                COUNT(DISTINCT cp.user_id) as participant_count
            FROM challenges c
            LEFT JOIN users u ON c.creator_id = u.id
            LEFT JOIN challenge_participants cp ON c.id = cp.challenge_id
            WHERE c.id = ?
            GROUP BY c.id
        """, (challenge_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        import json
        challenge = dict(row)
        challenge['rules'] = json.loads(challenge['rules_json']) if challenge['rules_json'] else {}
        challenge['reward'] = json.loads(challenge['reward_json']) if challenge['reward_json'] else {}
        
        return challenge
    
    def join_challenge(self, challenge_id, user_id):
        """Join a challenge"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO challenge_participants (challenge_id, user_id, score)
                VALUES (?, ?, 0)
            """, (challenge_id, user_id))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def get_user_challenges(self, user_id):
        """Get challenges user is participating in"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.*,
                cp.score,
                cp.rank,
                cp.completed,
                cp.joined_at,
                cp.completed_at,
                u.username as creator_name,
                COUNT(DISTINCT cp2.user_id) as participant_count
            FROM challenge_participants cp
            JOIN challenges c ON cp.challenge_id = c.id
            LEFT JOIN users u ON c.creator_id = u.id
            LEFT JOIN challenge_participants cp2 ON c.id = cp2.challenge_id
            WHERE cp.user_id = ? AND c.is_active = 1
            GROUP BY c.id
            ORDER BY c.end_time ASC
        """, (user_id,))
        
        challenges = cursor.fetchall()
        conn.close()
        
        import json
        result = []
        for row in challenges:
            challenge = dict(row)
            challenge['rules'] = json.loads(challenge['rules_json']) if challenge['rules_json'] else {}
            challenge['reward'] = json.loads(challenge['reward_json']) if challenge['reward_json'] else {}
            result.append(challenge)
        
        return result
    
    def get_challenge_leaderboard(self, challenge_id, limit=100):
        """Get challenge leaderboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cp.*,
                u.username,
                u.display_name,
                u.avatar_url
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.id
            WHERE cp.challenge_id = ?
            ORDER BY cp.score DESC, cp.joined_at ASC
            LIMIT ?
        """, (challenge_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Assign ranks
        leaderboard = []
        for i, row in enumerate(rows, 1):
            entry = dict(row)
            entry['rank'] = i
            leaderboard.append(entry)
        
        return leaderboard
    
    def update_challenge_progress(self, challenge_id, user_id, score):
        """Update user's progress in a challenge"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE challenge_participants 
            SET score = ?
            WHERE challenge_id = ? AND user_id = ?
        """, (score, challenge_id, user_id))
        
        conn.commit()
        conn.close()
    
    def complete_challenge(self, challenge_id, user_id):
        """Mark challenge as completed for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now()
        
        cursor.execute("""
            UPDATE challenge_participants 
            SET completed = 1, completed_at = ?
            WHERE challenge_id = ? AND user_id = ?
        """, (now, challenge_id, user_id))
        
        conn.commit()
        
        # Get challenge reward
        cursor.execute("SELECT reward_json FROM challenges WHERE id = ?", (challenge_id,))
        row = cursor.fetchone()
        
        reward = None
        if row and row['reward_json']:
            import json
            reward = json.loads(row['reward_json'])
        
        conn.close()
        
        return reward
    
    def check_challenge_completion(self, challenge_id, user_id):
        """Check if user has completed challenge requirements"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get challenge rules
        cursor.execute("SELECT challenge_type, rules_json FROM challenges WHERE id = ?", (challenge_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        import json
        challenge_type = row['challenge_type']
        rules = json.loads(row['rules_json']) if row['rules_json'] else {}
        
        # Check completion based on challenge type
        completed = False
        
        if challenge_type == 'profit_target':
            # Check if user reached profit target
            cursor.execute("""
                SELECT cp.score
                FROM challenge_participants cp
                WHERE cp.challenge_id = ? AND cp.user_id = ?
            """, (challenge_id, user_id))
            result = cursor.fetchone()
            target = rules.get('target_profit', 0)
            if result and result['score'] >= target:
                completed = True
        
        elif challenge_type == 'trade_volume':
            # Check if user completed required number of trades
            cursor.execute("""
                SELECT COUNT(*) as trade_count
                FROM transactions t
                JOIN challenge_participants cp ON t.user_id = cp.user_id
                WHERE cp.challenge_id = ? AND t.user_id = ?
                  AND t.timestamp >= cp.joined_at
            """, (challenge_id, user_id))
            result = cursor.fetchone()
            target = rules.get('target_trades', 0)
            if result and result['trade_count'] >= target:
                completed = True
        
        elif challenge_type == 'portfolio_value':
            # Check if user reached portfolio value target
            cursor.execute("""
                SELECT cp.score
                FROM challenge_participants cp
                WHERE cp.challenge_id = ? AND cp.user_id = ?
            """, (challenge_id, user_id))
            result = cursor.fetchone()
            target = rules.get('target_value', 0)
            if result and result['score'] >= target:
                completed = True
        
        conn.close()
        return completed
    
    def end_challenge(self, challenge_id):
        """End a challenge and award rewards to winners"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Mark challenge as inactive
        cursor.execute("UPDATE challenges SET is_active = 0 WHERE id = ?", (challenge_id,))
        
        # Get top performers
        cursor.execute("""
            SELECT user_id, score
            FROM challenge_participants
            WHERE challenge_id = ?
            ORDER BY score DESC
            LIMIT 10
        """, (challenge_id,))
        
        winners = cursor.fetchall()
        
        # Get challenge details for notification
        cursor.execute("SELECT name, reward_json FROM challenges WHERE id = ?", (challenge_id,))
        challenge = cursor.fetchone()
        
        import json
        reward = json.loads(challenge['reward_json']) if challenge['reward_json'] else {}
        
        # Notify top 3 winners
        for i, winner in enumerate(winners[:3], 1):
            rank_names = {1: '1st', 2: '2nd', 3: '3rd'}
            import json
            self.create_notification(
                winner['user_id'],
                'challenge_complete',
                f'Challenge Complete!',
                f'You finished {rank_names[i]} in "{challenge["name"]}"! Score: {winner["score"]:.2f}',
                json.dumps({'challenge_id': challenge_id})
            )
        
        conn.commit()
        conn.close()
        
        return [dict(row) for row in winners]
    
    # ============ OPTIONS METHODS ============
    
    def create_options_contract(self, symbol, strike_price, expiration_date, option_type):
        """Create or get existing options contract"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Try to get existing contract
        cursor.execute("""
            SELECT id FROM options_contracts
            WHERE symbol = ? AND strike_price = ? AND expiration_date = ? AND option_type = ?
        """, (symbol, strike_price, expiration_date, option_type))
        
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing['id']
        
        # Create new contract
        cursor.execute("""
            INSERT INTO options_contracts (symbol, strike_price, expiration_date, option_type)
            VALUES (?, ?, ?, ?)
        """, (symbol, strike_price, expiration_date, option_type))
        
        contract_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return contract_id
    
    def get_options_chain(self, symbol, expiration_date=None):
        """Get all available options for a symbol"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if expiration_date:
            cursor.execute("""
                SELECT * FROM options_contracts
                WHERE symbol = ? AND expiration_date = ?
                ORDER BY strike_price, option_type
            """, (symbol, expiration_date))
        else:
            cursor.execute("""
                SELECT * FROM options_contracts
                WHERE symbol = ?
                ORDER BY expiration_date, strike_price, option_type
            """, (symbol,))
        
        contracts = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in contracts]
    
    def get_available_expiration_dates(self, symbol):
        """Get all available expiration dates for a symbol"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT expiration_date
            FROM options_contracts
            WHERE symbol = ? AND expiration_date >= date('now')
            ORDER BY expiration_date
        """, (symbol,))
        
        dates = cursor.fetchall()
        conn.close()
        
        return [row['expiration_date'] for row in dates]
    
    def buy_option(self, user_id, contract_id, contracts, premium):
        """Buy options contracts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        total_cost = contracts * premium * 100  # Options are priced per share, 100 shares per contract
        
        # Check if user has enough cash
        cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user['cash'] < total_cost:
            conn.close()
            return False, "Insufficient funds"
        
        # Deduct cash
        cursor.execute("""
            UPDATE users SET cash = cash - ? WHERE id = ?
        """, (total_cost, user_id))
        
        # Check if user has existing position for this contract
        cursor.execute("""
            SELECT id, contracts, avg_premium
            FROM options_positions
            WHERE user_id = ? AND contract_id = ? AND status = 'open' AND position_type = 'long'
        """, (user_id, contract_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing position
            total_contracts = existing['contracts'] + contracts
            new_avg_premium = ((existing['avg_premium'] * existing['contracts']) + (premium * contracts)) / total_contracts
            
            cursor.execute("""
                UPDATE options_positions
                SET contracts = ?, avg_premium = ?
                WHERE id = ?
            """, (total_contracts, new_avg_premium, existing['id']))
            
            position_id = existing['id']
        else:
            # Create new position
            cursor.execute("""
                INSERT INTO options_positions (user_id, contract_id, contracts, avg_premium, position_type)
                VALUES (?, ?, ?, ?, 'long')
            """, (user_id, contract_id, contracts, premium))
            
            position_id = cursor.lastrowid
        
        # Record transaction
        cursor.execute("""
            INSERT INTO options_transactions 
            (user_id, position_id, contract_id, contracts, premium, transaction_type, total_cost)
            VALUES (?, ?, ?, ?, ?, 'buy', ?)
        """, (user_id, position_id, contract_id, contracts, premium, total_cost))
        
        conn.commit()
        conn.close()
        
        return True, "Options purchased successfully"
    
    def sell_option(self, user_id, position_id, contracts, premium):
        """Sell options contracts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get position details
        cursor.execute("""
            SELECT * FROM options_positions
            WHERE id = ? AND user_id = ? AND status = 'open'
        """, (position_id, user_id))
        
        position = cursor.fetchone()
        
        if not position:
            conn.close()
            return False, "Position not found"
        
        if position['contracts'] < contracts:
            conn.close()
            return False, "Not enough contracts to sell"
        
        total_proceeds = contracts * premium * 100
        
        # Add cash
        cursor.execute("""
            UPDATE users SET cash = cash + ? WHERE id = ?
        """, (total_proceeds, user_id))
        
        # Update position
        remaining_contracts = position['contracts'] - contracts
        
        if remaining_contracts == 0:
            cursor.execute("""
                UPDATE options_positions
                SET contracts = 0, status = 'closed', closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (position_id,))
        else:
            cursor.execute("""
                UPDATE options_positions
                SET contracts = ?
                WHERE id = ?
            """, (remaining_contracts, position_id))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO options_transactions 
            (user_id, position_id, contract_id, contracts, premium, transaction_type, total_cost)
            VALUES (?, ?, ?, ?, ?, 'sell', ?)
        """, (user_id, position_id, position['contract_id'], contracts, premium, -total_proceeds))
        
        conn.commit()
        conn.close()
        
        return True, "Options sold successfully"
    
    def get_user_options_positions(self, user_id, status='open'):
        """Get user's options positions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                op.*,
                oc.symbol,
                oc.strike_price,
                oc.expiration_date,
                oc.option_type
            FROM options_positions op
            JOIN options_contracts oc ON op.contract_id = oc.id
            WHERE op.user_id = ? AND op.status = ?
            ORDER BY oc.expiration_date, oc.symbol
        """, (user_id, status))
        
        positions = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in positions]
    
    def get_options_transactions(self, user_id, limit=50):
        """Get user's options transaction history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ot.*,
                oc.symbol,
                oc.strike_price,
                oc.expiration_date,
                oc.option_type
            FROM options_transactions ot
            JOIN options_contracts oc ON ot.contract_id = oc.id
            WHERE ot.user_id = ?
            ORDER BY ot.timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in transactions]
    
    def expire_options(self, expiration_date, current_prices):
        """Process options expiration and auto-exercise ITM options"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all contracts expiring today
        cursor.execute("""
            SELECT id, symbol, strike_price, option_type
            FROM options_contracts
            WHERE expiration_date = ?
        """, (expiration_date,))
        
        expiring_contracts = cursor.fetchall()
        processed_count = 0
        
        for contract in expiring_contracts:
            current_price = current_prices.get(contract['symbol'])
            
            if not current_price:
                continue
            
            # Get all open positions for this contract
            cursor.execute("""
                SELECT * FROM options_positions
                WHERE contract_id = ? AND status = 'open'
            """, (contract['id'],))
            
            positions = cursor.fetchall()
            
            for position in positions:
                is_itm = False
                intrinsic_value = 0
                
                # Check if option is in-the-money
                if contract['option_type'] == 'call':
                    is_itm = current_price > contract['strike_price']
                    intrinsic_value = max(0, current_price - contract['strike_price'])
                else:  # put
                    is_itm = current_price < contract['strike_price']
                    intrinsic_value = max(0, contract['strike_price'] - current_price)
                
                if is_itm and intrinsic_value > 0:
                    # Auto-exercise ITM options
                    proceeds = position['contracts'] * intrinsic_value * 100
                    
                    cursor.execute("""
                        UPDATE users SET cash = cash + ? WHERE id = ?
                    """, (proceeds, position['user_id']))
                    
                    cursor.execute("""
                        UPDATE options_positions
                        SET status = 'exercised', closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (position['id'],))
                    
                    # Record exercise transaction
                    cursor.execute("""
                        INSERT INTO options_transactions 
                        (user_id, position_id, contract_id, contracts, premium, transaction_type, total_cost)
                        VALUES (?, ?, ?, ?, ?, 'exercise', ?)
                    """, (position['user_id'], position['id'], contract['id'], 
                          position['contracts'], intrinsic_value, proceeds))
                    
                    # Send notification
                    self.create_notification(
                        position['user_id'],
                        'options_exercise',
                        'Options Exercised',
                        f'{position["contracts"]} {contract["option_type"]} contract(s) for {contract["symbol"]} were auto-exercised. Proceeds: ${proceeds:.2f}',
                        '/options'
                    )
                else:
                    # Expire worthless
                    cursor.execute("""
                        UPDATE options_positions
                        SET status = 'expired', closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (position['id'],))
                    
                    cursor.execute("""
                        INSERT INTO options_transactions 
                        (user_id, position_id, contract_id, contracts, premium, transaction_type, total_cost)
                        VALUES (?, ?, ?, ?, 0, 'expire', 0)
                    """, (position['user_id'], position['id'], contract['id'], position['contracts']))
                
                processed_count += 1
        
        conn.commit()
        conn.close()
        
        return processed_count
    
    # ============ NEWS METHODS ============
    
    def cache_news_article(self, symbol, headline, summary, source, url, image_url, published_at, sentiment_score, sentiment_label, category):
        """Cache a news article with sentiment data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO news_articles 
                (symbol, headline, summary, source, url, image_url, published_at, sentiment_score, sentiment_label, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, headline, summary, source, url, image_url, published_at, sentiment_score, sentiment_label, category))
            
            conn.commit()
            article_id = cursor.lastrowid
        except Exception as e:
            print(f"Error caching article: {e}")
            article_id = None
        finally:
            conn.close()
        
        return article_id
    
    def get_news_by_symbol(self, symbol, limit=20, max_age_hours=24):
        """Get cached news for a specific symbol"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM news_articles
            WHERE symbol = ?
              AND datetime(cached_at) >= datetime('now', '-' || ? || ' hours')
            ORDER BY published_at DESC
            LIMIT ?
        """, (symbol, max_age_hours, limit))
        
        articles = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in articles]
    
    def get_general_news(self, limit=50, max_age_hours=24):
        """Get general market news"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM news_articles
            WHERE symbol IS NULL OR symbol = ''
              AND datetime(cached_at) >= datetime('now', '-' || ? || ' hours')
            ORDER BY published_at DESC
            LIMIT ?
        """, (max_age_hours, limit))
        
        articles = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in articles]
    
    def get_all_news(self, limit=100, max_age_hours=24):
        """Get all news articles (both general and stock-specific)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM news_articles
            WHERE datetime(cached_at) >= datetime('now', '-' || ? || ' hours')
            ORDER BY published_at DESC
            LIMIT ?
        """, (max_age_hours, limit))
        
        articles = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in articles]
    
    def get_sentiment_summary(self, symbol=None):
        """Get sentiment summary for a symbol or overall market"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT 
                    sentiment_label,
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_score
                FROM news_articles
                WHERE symbol = ?
                  AND datetime(cached_at) >= datetime('now', '-24 hours')
                  AND sentiment_label IS NOT NULL
                GROUP BY sentiment_label
            """, (symbol,))
        else:
            cursor.execute("""
                SELECT 
                    sentiment_label,
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_score
                FROM news_articles
                WHERE datetime(cached_at) >= datetime('now', '-24 hours')
                  AND sentiment_label IS NOT NULL
                GROUP BY sentiment_label
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        summary = {
            'positive': {'count': 0, 'avg_score': 0},
            'neutral': {'count': 0, 'avg_score': 0},
            'negative': {'count': 0, 'avg_score': 0}
        }
        
        for row in results:
            label = row['sentiment_label']
            summary[label] = {
                'count': row['count'],
                'avg_score': row['avg_score']
            }
        
        total = sum(s['count'] for s in summary.values())
        if total > 0:
            for label in summary:
                summary[label]['percentage'] = (summary[label]['count'] / total) * 100
        
        return summary
    
    def cleanup_old_news(self, days=7):
        """Delete news articles older than specified days"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM news_articles
            WHERE datetime(cached_at) < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def add_news_preference(self, user_id, symbol):
        """Add a symbol to user's news feed preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO news_preferences (user_id, symbol, enabled)
                VALUES (?, ?, 1)
            """, (user_id, symbol))
            
            conn.commit()
            success = True
        except sqlite3.Error:
            success = False
        finally:
            conn.close()
        
        return success
    
    def remove_news_preference(self, user_id, symbol):
        """Remove a symbol from user's news feed preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM news_preferences
            WHERE user_id = ? AND symbol = ?
        """, (user_id, symbol))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_user_news_preferences(self, user_id):
        """Get user's news feed preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol FROM news_preferences
            WHERE user_id = ? AND enabled = 1
        """, (user_id,))
        
        symbols = [row['symbol'] for row in cursor.fetchall()]
        conn.close()
        
        return symbols
    
    # ============ SOCIAL TRADING METHODS ============
    
    def follow_trader(self, follower_id, trader_id):
        """Follow a trader"""
        if follower_id == trader_id:
            return False, "Cannot follow yourself"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO trader_following (follower_id, trader_id)
                VALUES (?, ?)
            """, (follower_id, trader_id))
            
            conn.commit()
            
            import json
            # Send notification
            self.create_notification(
                trader_id,
                'new_follower',
                'New Follower',
                f'Someone started following your trades!',
                json.dumps({'from_user_id': follower_id})
            )
            
            success = True
            message = "Now following trader"
        except sqlite3.Error:
            success = False
            message = "Already following this trader"
        finally:
            conn.close()
        
        return success, message
    
    def unfollow_trader(self, follower_id, trader_id):
        """Unfollow a trader"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM trader_following
            WHERE follower_id = ? AND trader_id = ?
        """, (follower_id, trader_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_following(self, user_id):
        """Get list of traders a user is following"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.id, u.username, u.avatar_url,
                tf.started_at,
                ts.total_return, ts.win_rate, ts.total_trades
            FROM trader_following tf
            JOIN users u ON tf.trader_id = u.id
            LEFT JOIN trader_stats ts ON u.id = ts.user_id
            WHERE tf.follower_id = ?
            ORDER BY tf.started_at DESC
        """, (user_id,))
        
        following = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in following]
    
    def get_followers(self, trader_id):
        """Get list of users following a trader"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.id, u.username, u.avatar_url,
                tf.started_at
            FROM trader_following tf
            JOIN users u ON tf.follower_id = u.id
            WHERE tf.trader_id = ?
            ORDER BY tf.started_at DESC
        """, (trader_id,))
        
        followers = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in followers]
    
    def is_following(self, follower_id, trader_id):
        """Check if user is following a trader"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM trader_following
            WHERE follower_id = ? AND trader_id = ?
        """, (follower_id, trader_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0
    
    def start_copy_trading(self, follower_id, trader_id, allocation_pct=10, max_trade=1000, copy_buys=True, copy_sells=True):
        """Start copy trading a trader"""
        if follower_id == trader_id:
            return False, "Cannot copy yourself"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO copy_trading 
                (follower_id, trader_id, is_active, allocation_percentage, max_trade_amount, copy_buys, copy_sells)
                VALUES (?, ?, 1, ?, ?, ?, ?)
            """, (follower_id, trader_id, allocation_pct, max_trade, 1 if copy_buys else 0, 1 if copy_sells else 0))
            
            conn.commit()
            
            # Follow them automatically
            self.follow_trader(follower_id, trader_id)
            
            # Send notification
            import json
            self.create_notification(
                trader_id,
                'trade_copy',
                'New Copy Trader',
                f'Someone is now copying your trades!',
                json.dumps({'from_user_id': follower_id})
            )
            
            success = True
            message = "Copy trading activated"
        except Exception as e:
            success = False
            message = f"Error: {str(e)}"
        finally:
            conn.close()
        
        return success, message
    
    def stop_copy_trading(self, follower_id, trader_id):
        """Stop copy trading a trader"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE copy_trading
            SET is_active = 0, stopped_at = CURRENT_TIMESTAMP
            WHERE follower_id = ? AND trader_id = ?
        """, (follower_id, trader_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_copy_trading_settings(self, follower_id, trader_id):
        """Get copy trading settings"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM copy_trading
            WHERE follower_id = ? AND trader_id = ? AND is_active = 1
        """, (follower_id, trader_id))
        
        settings = cursor.fetchone()
        conn.close()
        
        return dict(settings) if settings else None
    
    def get_active_copiers(self, trader_id):
        """Get users actively copying a trader"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ct.*,
                u.username, u.avatar_url
            FROM copy_trading ct
            JOIN users u ON ct.follower_id = u.id
            WHERE ct.trader_id = ? AND ct.is_active = 1
            ORDER BY ct.started_at DESC
        """, (trader_id,))
        
        copiers = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in copiers]
    
    def get_copying(self, follower_id):
        """Get traders a user is copying"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ct.*,
                u.username, u.avatar_url,
                ts.total_return, ts.win_rate
            FROM copy_trading ct
            JOIN users u ON ct.trader_id = u.id
            LEFT JOIN trader_stats ts ON u.id = ts.user_id
            WHERE ct.follower_id = ? AND ct.is_active = 1
            ORDER BY ct.started_at DESC
        """, (follower_id,))
        
        copying = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in copying]
    
    def record_copied_trade(self, follower_id, trader_id, original_txn_id, copied_txn_id, symbol, shares, price, trade_type):
        """Record a copied trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO copied_trades 
            (follower_id, trader_id, original_transaction_id, copied_transaction_id, symbol, shares, price, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (follower_id, trader_id, original_txn_id, copied_txn_id, symbol, shares, price, trade_type))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_copied_trades(self, follower_id, trader_id=None):
        """Get copied trades history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if trader_id:
            cursor.execute("""
                SELECT ct.*, u.username as trader_username
                FROM copied_trades ct
                JOIN users u ON ct.trader_id = u.id
                WHERE ct.follower_id = ? AND ct.trader_id = ?
                ORDER BY ct.timestamp DESC
                LIMIT 50
            """, (follower_id, trader_id))
        else:
            cursor.execute("""
                SELECT ct.*, u.username as trader_username
                FROM copied_trades ct
                JOIN users u ON ct.trader_id = u.id
                WHERE ct.follower_id = ?
                ORDER BY ct.timestamp DESC
                LIMIT 50
            """, (follower_id,))
        
        trades = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in trades]
    
    def update_trader_stats(self, user_id):
        """Update cached trader statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate stats from transactions
        cursor.execute("""
            SELECT COUNT(*) as total_trades
            FROM transactions
            WHERE user_id = ?
        """, (user_id,))
        
        total_trades = cursor.fetchone()['total_trades']
        
        # Get portfolio value and cash
        cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        cash = user['cash']
        
        # Get holdings value
        portfolio = self.get_portfolio_breakdown(user_id)
        from helpers import lookup
        holdings_value = 0
        for holding in portfolio:
            quote = lookup(holding['symbol'])
            if quote:
                holdings_value += holding['shares'] * quote['price']
        
        total_value = cash + holdings_value
        total_return = ((total_value - 10000) / 10000) * 100  # Assuming 10k starting cash
        
        # Win/loss calculation (simplified)
        transactions = self.get_transactions(user_id)
        winning = 0
        losing = 0
        for txn in transactions:
            if txn['type'] == 'sell':
                # Simplified - would need cost basis tracking for accurate calculation
                quote = lookup(txn['symbol'])
                if quote and txn['price'] > quote['price'] * 0.95:  # Rough estimate
                    winning += 1
                else:
                    losing += 1
        
        win_rate = (winning / (winning + losing) * 100) if (winning + losing) > 0 else 0
        
        # Get followers and copiers count
        cursor.execute("SELECT COUNT(*) as count FROM trader_following WHERE trader_id = ?", (user_id,))
        followers_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM copy_trading WHERE trader_id = ? AND is_active = 1", (user_id,))
        copiers_count = cursor.fetchone()['count']
        
        # Update or insert stats
        cursor.execute("""
            INSERT OR REPLACE INTO trader_stats 
            (user_id, total_trades, winning_trades, losing_trades, win_rate, total_return, 
             followers_count, copiers_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, total_trades, winning, losing, win_rate, total_return, followers_count, copiers_count))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_trader_stats(self, user_id):
        """Get trader statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trader_stats WHERE user_id = ?", (user_id,))
        stats = cursor.fetchone()
        
        conn.close()
        
        return dict(stats) if stats else None
    
    def get_top_traders(self, limit=20, order_by='total_return'):
        """Get top performing traders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        valid_orders = ['total_return', 'win_rate', 'total_trades', 'followers_count']
        if order_by not in valid_orders:
            order_by = 'total_return'
        
        cursor.execute(f"""
            SELECT 
                ts.*,
                u.username, u.avatar_url, u.bio
            FROM trader_stats ts
            JOIN users u ON ts.user_id = u.id
            WHERE ts.total_trades >= 5
            ORDER BY ts.{order_by} DESC
            LIMIT ?
        """, (limit,))
        
        traders = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in traders]
    
    # === Activity Reactions ===
    
    def init_activity_reactions_table(self):
        """Initialize activity reactions table for emoji reactions on feed items"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(activity_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_activity_reactions_activity 
            ON activity_reactions(activity_id)
        ''')
        conn.commit()
        conn.close()
    
    def add_activity_reaction(self, activity_id, user_id, emoji):
        """Add or update an emoji reaction to an activity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_reactions (activity_id, user_id, emoji)
            VALUES (?, ?, ?)
            ON CONFLICT(activity_id, user_id) 
            DO UPDATE SET emoji = ?, created_at = CURRENT_TIMESTAMP
        ''', (activity_id, user_id, emoji, emoji))
        conn.commit()
        conn.close()
    
    def remove_activity_reaction(self, activity_id, user_id):
        """Remove a user's reaction from an activity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM activity_reactions 
            WHERE activity_id = ? AND user_id = ?
        ''', (activity_id, user_id))
        conn.commit()
        conn.close()
    
    def get_activity_reactions(self, activity_id):
        """Get all reactions for an activity grouped by emoji"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT emoji, COUNT(*) as count, GROUP_CONCAT(user_id) as user_ids
            FROM activity_reactions
            WHERE activity_id = ?
            GROUP BY emoji
            ORDER BY count DESC
        ''', (activity_id,))
        
        reactions = cursor.fetchall()
        conn.close()
        
        result = []
        for row in reactions:
            result.append({
                'emoji': row[0],
                'count': row[1],
                'user_ids': [int(uid) for uid in row[2].split(',') if uid]
            })
        return result
    
    def get_user_activity_reaction(self, activity_id, user_id):
        """Get a specific user's reaction to an activity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT emoji FROM activity_reactions
            WHERE activity_id = ? AND user_id = ?
        ''', (activity_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
