import sqlite3
from datetime import datetime


class DatabaseManager:
    """Manages all database operations for the stock trading app."""
    
    def __init__(self, db_path="database/stocks.db"):
        self.db_path = db_path
        self.init_db()
    
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
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        # ============ INDEXES FOR PERFORMANCE ============
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_transactions ON transactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_status ON friends(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_members ON league_members(league_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league_user ON league_members(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenges_active ON challenges(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots ON portfolio_snapshots(user_id, timestamp)")
        
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
    
    def record_transaction(self, user_id, symbol, shares, price, transaction_type):
        """Record a stock transaction."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, type) VALUES (?, ?, ?, ?, ?)",
            (user_id, symbol, shares, price, transaction_type)
        )
        
        conn.commit()
        conn.close()
    
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
            SELECT u.id, u.username, u.avatar_url, u.last_active
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
    
    def get_notifications(self, user_id, unread_only=False):
        """Get notifications for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if unread_only:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE user_id = ? AND is_read = 0
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
        
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
        
        cursor.execute(
            "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_key = ?",
            (user_id, achievement_key)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def award_achievement(self, user_id, achievement_key, title, description):
        """Award an achievement to a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO achievements (user_id, achievement_key, title, description) VALUES (?, ?, ?, ?)",
                (user_id, achievement_key, title, description)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Achievement already exists
        
        conn.close()
    
    def get_achievements(self, user_id):
        """Get all achievements for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM achievements WHERE user_id = ? ORDER BY earned_at DESC",
            (user_id,)
        )
        
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
                SELECT 
                    CASE 
                        WHEN user1_id = ? THEN user2_id 
                        ELSE user1_id 
                    END
                FROM friends
                WHERE (user1_id = ? OR user2_id = ?)
                AND status = 'accepted'
            )
            
            UNION ALL
            
            SELECT 
                ua.id, ua.user_id, u.username, NULL as symbol, NULL as shares, 
                NULL as price, ua.title as type, ua.earned_at as timestamp, 
                'achievement' as activity_type
            FROM user_achievements ua
            JOIN users u ON ua.user_id = u.id
            WHERE ua.user_id IN (
                SELECT 
                    CASE 
                        WHEN user1_id = ? THEN user2_id 
                        ELSE user1_id 
                    END
                FROM friends
                WHERE (user1_id = ? OR user2_id = ?)
                AND status = 'accepted'
            )
            
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, user_id, user_id, user_id, user_id, user_id, limit))
        
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
