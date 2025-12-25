"""
Email Notifications System for StockLeague

Provides event-driven email notifications for:
- League invites and member actions
- Trading activity alerts
- Achievement unlocks
- Portfolio milestones
- League announcements
- Challenge completions

Uses Flask-Mail with template-based emails.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import sqlite3

logger = logging.getLogger(__name__)


class NotificationEvent(Enum):
    """Event types that trigger notifications."""
    # League events
    LEAGUE_INVITE = "league_invite"
    LEAGUE_INVITE_ACCEPTED = "league_invite_accepted"
    LEAGUE_INVITE_DECLINED = "league_invite_declined"
    LEAGUE_CREATED = "league_created"
    LEAGUE_MEMBER_JOINED = "league_member_joined"
    LEAGUE_MEMBER_LEFT = "league_member_left"
    LEAGUE_DISBANDED = "league_disbanded"
    
    # Trading events
    TRADE_EXECUTED = "trade_executed"
    TRADE_ALERT = "trade_alert"
    HIGH_VOLUME_TRADE = "high_volume_trade"
    
    # Achievement events
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    MILESTONE_REACHED = "milestone_reached"
    RANK_CHANGED = "rank_changed"
    
    # Portfolio events
    PORTFOLIO_MILESTONE = "portfolio_milestone"
    PORTFOLIO_LOSS_ALERT = "portfolio_loss_alert"
    DIVIDEND_RECEIVED = "dividend_received"
    
    # Challenge events
    CHALLENGE_STARTED = "challenge_started"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_FAILED = "challenge_failed"
    
    # Announcement events
    LEAGUE_ANNOUNCEMENT = "league_announcement"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    
    # Admin events
    ADMIN_ALERT = "admin_alert"
    FRAUD_DETECTED = "fraud_detected"


@dataclass
class EmailTemplate:
    """Email template with subject and content."""
    event: NotificationEvent
    subject: str
    html_template: str
    text_template: str
    variables: List[str]


class EmailTemplateManager:
    """Manages email templates for different notification types."""
    
    def __init__(self):
        """Initialize email templates."""
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[NotificationEvent, EmailTemplate]:
        """Load all email templates."""
        return {
            NotificationEvent.LEAGUE_INVITE: EmailTemplate(
                event=NotificationEvent.LEAGUE_INVITE,
                subject="You're invited to join {{ league_name }} on StockLeague!",
                html_template=self._league_invite_html(),
                text_template=self._league_invite_text(),
                variables=["username", "league_name", "invited_by", "invite_code", "expires_at"]
            ),
            NotificationEvent.LEAGUE_INVITE_ACCEPTED: EmailTemplate(
                event=NotificationEvent.LEAGUE_INVITE_ACCEPTED,
                subject="{{ user_name }} accepted your invite to {{ league_name }}",
                html_template=self._league_invite_accepted_html(),
                text_template=self._league_invite_accepted_text(),
                variables=["user_name", "league_name", "league_id"]
            ),
            NotificationEvent.ACHIEVEMENT_UNLOCKED: EmailTemplate(
                event=NotificationEvent.ACHIEVEMENT_UNLOCKED,
                subject="🏆 Achievement Unlocked: {{ achievement_name }}",
                html_template=self._achievement_unlocked_html(),
                text_template=self._achievement_unlocked_text(),
                variables=["username", "achievement_name", "description", "reward"]
            ),
            NotificationEvent.MILESTONE_REACHED: EmailTemplate(
                event=NotificationEvent.MILESTONE_REACHED,
                subject="🎉 Milestone Reached: {{ milestone_name }}",
                html_template=self._milestone_reached_html(),
                text_template=self._milestone_reached_text(),
                variables=["username", "milestone_name", "league_name", "value"]
            ),
            NotificationEvent.RANK_CHANGED: EmailTemplate(
                event=NotificationEvent.RANK_CHANGED,
                subject="📊 Your rank changed in {{ league_name }}",
                html_template=self._rank_changed_html(),
                text_template=self._rank_changed_text(),
                variables=["username", "league_name", "old_rank", "new_rank", "portfolio_value"]
            ),
            NotificationEvent.PORTFOLIO_MILESTONE: EmailTemplate(
                event=NotificationEvent.PORTFOLIO_MILESTONE,
                subject="💰 Milestone Alert: {{ event_text }}",
                html_template=self._portfolio_milestone_html(),
                text_template=self._portfolio_milestone_text(),
                variables=["username", "event_text", "portfolio_value", "league_name", "date"]
            ),
            NotificationEvent.LEAGUE_ANNOUNCEMENT: EmailTemplate(
                event=NotificationEvent.LEAGUE_ANNOUNCEMENT,
                subject="📢 Announcement from {{ league_name }}: {{ title }}",
                html_template=self._league_announcement_html(),
                text_template=self._league_announcement_text(),
                variables=["username", "league_name", "title", "message", "posted_by"]
            ),
            NotificationEvent.TRADE_EXECUTED: EmailTemplate(
                event=NotificationEvent.TRADE_EXECUTED,
                subject="Trade Confirmation: {{ action }} {{ shares }} shares of {{ symbol }}",
                html_template=self._trade_executed_html(),
                text_template=self._trade_executed_text(),
                variables=["username", "action", "shares", "symbol", "price", "total", "league_name", "timestamp"]
            ),
        }
    
    def _league_invite_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0066cc;">You're Invited to Join StockLeague!</h2>
                    <p>Hi {{ username }},</p>
                    <p><strong>{{ invited_by }}</strong> invited you to join the league:</p>
                    <h3 style="color: #0066cc;">{{ league_name }}</h3>
                    <p style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                        <strong>Invite Code:</strong> <code style="font-size: 16px; letter-spacing: 2px;">{{ invite_code }}</code>
                    </p>
                    <p><strong>This invite expires:</strong> {{ expires_at }}</p>
                    <p>
                        <a href="https://stockleague.app/join?code={{ invite_code }}" 
                           style="background: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Accept Invite
                        </a>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">
                        If you didn't expect this invite, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _league_invite_text(self) -> str:
        return """
Hi {{ username }},

{{ invited_by }} invited you to join {{ league_name }} on StockLeague!

Invite Code: {{ invite_code }}
Expires: {{ expires_at }}

Visit: https://stockleague.app/join?code={{ invite_code }}

If you didn't expect this invite, you can safely ignore this email.
        """
    
    def _league_invite_accepted_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0066cc;">✓ Invite Accepted!</h2>
                    <p>Great news! <strong>{{ user_name }}</strong> accepted your invite to join {{ league_name }}.</p>
                    <p style="background: #f0fff0; padding: 15px; border-radius: 5px; border-left: 4px solid #22c55e;">
                        The league now has {{ member_count }} members.
                    </p>
                    <p>
                        <a href="https://stockleague.app/league/{{ league_id }}" 
                           style="background: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            View League
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _league_invite_accepted_text(self) -> str:
        return """
Great news! {{ user_name }} accepted your invite to {{ league_name }}.

The league now has {{ member_count }} members.

View League: https://stockleague.app/league/{{ league_id }}
        """
    
    def _achievement_unlocked_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #d4a574;">🏆 Achievement Unlocked!</h2>
                    <p>Congratulations, {{ username }}!</p>
                    <p style="background: #fff8dc; padding: 15px; border-radius: 5px; border-left: 4px solid #d4a574;">
                        <strong>{{ achievement_name }}</strong><br>
                        {{ description }}
                    </p>
                    <p><strong>Reward:</strong> {{ reward }}</p>
                </div>
            </body>
        </html>
        """
    
    def _achievement_unlocked_text(self) -> str:
        return """
🏆 Achievement Unlocked!

Congratulations, {{ username }}!

{{ achievement_name }}
{{ description }}

Reward: {{ reward }}
        """
    
    def _milestone_reached_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #22c55e;">🎉 Milestone Reached!</h2>
                    <p>Excellent progress, {{ username }}!</p>
                    <p style="background: #f0fff0; padding: 15px; border-radius: 5px; border-left: 4px solid #22c55e;">
                        <strong>{{ milestone_name }}</strong> in {{ league_name }}<br>
                        Milestone: {{ value }}
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _milestone_reached_text(self) -> str:
        return """
🎉 Milestone Reached!

Excellent progress, {{ username }}!

{{ milestone_name }} in {{ league_name }}
Milestone: {{ value }}
        """
    
    def _rank_changed_html(self) -> str:
        direction = "📈 Up" if "{{ old_rank }}" > "{{ new_rank }}" else "📉 Down"
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #3b82f6;">📊 Rank Update</h2>
                    <p>Hi {{ username }},</p>
                    <p>Your rank in <strong>{{ league_name }}</strong> has changed:</p>
                    <p style="background: #f0f4ff; padding: 15px; border-radius: 5px; border-left: 4px solid #3b82f6;">
                        <strong>#{{ old_rank }}</strong> → <strong>#{{ new_rank }}</strong><br>
                        Portfolio Value: {{ portfolio_value }}
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _rank_changed_text(self) -> str:
        return """
📊 Rank Update

Hi {{ username }},

Your rank in {{ league_name }} has changed:
#{{ old_rank }} → #{{ new_rank }}
Portfolio Value: {{ portfolio_value }}
        """
    
    def _portfolio_milestone_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #ec4899;">💰 Portfolio Milestone</h2>
                    <p>{{ username }}, great news!</p>
                    <p style="background: #fdf2f8; padding: 15px; border-radius: 5px; border-left: 4px solid #ec4899;">
                        <strong>{{ event_text }}</strong><br>
                        Current Value: {{ portfolio_value }}<br>
                        League: {{ league_name }}<br>
                        Date: {{ date }}
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _portfolio_milestone_text(self) -> str:
        return """
💰 Portfolio Milestone

{{ username }}, great news!

{{ event_text }}
Current Value: {{ portfolio_value }}
League: {{ league_name }}
Date: {{ date }}
        """
    
    def _league_announcement_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #f59e0b;">📢 League Announcement</h2>
                    <p>Hi {{ username }},</p>
                    <p><strong>{{ league_name }}</strong> has a new announcement:</p>
                    <h3>{{ title }}</h3>
                    <div style="background: #fef3c7; padding: 15px; border-radius: 5px; border-left: 4px solid #f59e0b;">
                        {{ message }}
                    </div>
                    <p style="color: #999; font-size: 12px; margin-top: 10px;">
                        Posted by: {{ posted_by }}
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _league_announcement_text(self) -> str:
        return """
📢 League Announcement

Hi {{ username }},

{{ league_name }} has a new announcement:

{{ title }}

{{ message }}

Posted by: {{ posted_by }}
        """
    
    def _trade_executed_html(self) -> str:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0066cc;">✓ Trade Confirmed</h2>
                    <p>Hi {{ username }},</p>
                    <p>Your trade in <strong>{{ league_name }}</strong> has been executed:</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                        <tr style="background: #f5f5f5;">
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Action:</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{{ action }}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Symbol:</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{{ symbol }}</td>
                        </tr>
                        <tr style="background: #f5f5f5;">
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Shares:</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{{ shares }}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Price:</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{{ price }}</td>
                        </tr>
                        <tr style="background: #f0fff0;">
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total:</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{{ total }}</strong></td>
                        </tr>
                    </table>
                    <p style="color: #999; font-size: 12px;">
                        Executed: {{ timestamp }}
                    </p>
                </div>
            </body>
        </html>
        """
    
    def _trade_executed_text(self) -> str:
        return """
✓ Trade Confirmed

Hi {{ username }},

Your trade in {{ league_name }} has been executed:

Action: {{ action }}
Symbol: {{ symbol }}
Shares: {{ shares }}
Price: {{ price }}
Total: {{ total }}

Executed: {{ timestamp }}
        """
    
    def get_template(self, event: NotificationEvent) -> Optional[EmailTemplate]:
        """Get email template for an event."""
        return self.templates.get(event)


class NotificationPreferences:
    """Manages user notification preferences."""
    
    def __init__(self, db):
        """Initialize with database connection."""
        self.db = db
        self._ensure_preferences_table()
    
    def _ensure_preferences_table(self):
        """Create preferences table if needed."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    frequency TEXT DEFAULT 'immediate',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, event_type),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            self.db.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating preferences table: {e}")
    
    def get_user_preferences(self, user_id: int) -> Dict[str, bool]:
        """Get notification preferences for a user."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT event_type, enabled FROM notification_preferences
                WHERE user_id = ?
            """, (user_id,))
            prefs = {row[0]: bool(row[1]) for row in cursor.fetchall()}
            
            # Provide defaults for missing events
            for event in NotificationEvent:
                if event.value not in prefs:
                    prefs[event.value] = True
            
            return prefs
        except sqlite3.Error as e:
            logger.error(f"Error getting preferences: {e}")
            return {}
    
    def set_preference(self, user_id: int, event_type: str, enabled: bool) -> bool:
        """Set preference for an event type."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO notification_preferences
                (user_id, event_type, enabled, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, event_type, int(enabled)))
            self.db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting preference: {e}")
            return False
    
    def should_send_notification(self, user_id: int, event: NotificationEvent) -> bool:
        """Check if notification should be sent for this event."""
        prefs = self.get_user_preferences(user_id)
        return prefs.get(event.value, True)


class NotificationQueue:
    """In-memory queue for pending notifications."""
    
    def __init__(self, db):
        """Initialize notification queue."""
        self.db = db
        self._ensure_queue_table()
    
    def _ensure_queue_table(self):
        """Create notification queue table."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_queue (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    html_body TEXT NOT NULL,
                    text_body TEXT NOT NULL,
                    variables TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            self.db.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating queue table: {e}")
    
    def enqueue(self, user_id: int, event: NotificationEvent, 
                subject: str, html_body: str, text_body: str,
                variables: Optional[Dict] = None) -> bool:
        """Add notification to queue."""
        try:
            import json
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO notification_queue
                (user_id, event_type, subject, html_body, text_body, variables)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, event.value, subject, html_body, text_body, 
                  json.dumps(variables) if variables else None))
            self.db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error enqueueing notification: {e}")
            return False
    
    def get_pending(self, limit: int = 100) -> List[Tuple]:
        """Get pending notifications from queue."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT id, user_id, subject, html_body, text_body
                FROM notification_queue
                WHERE status = 'pending' AND attempts < 3
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting pending notifications: {e}")
            return []
    
    def mark_sent(self, notification_id: int) -> bool:
        """Mark notification as sent."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE notification_queue
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (notification_id,))
            self.db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking notification as sent: {e}")
            return False
    
    def mark_failed(self, notification_id: int, error: str) -> bool:
        """Mark notification as failed."""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE notification_queue
                SET status = 'failed', attempts = attempts + 1, last_error = ?
                WHERE id = ?
            """, (error, notification_id))
            self.db.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking notification as failed: {e}")
            return False


class EmailNotificationService:
    """Main email notification service."""
    
    def __init__(self, mail, db):
        """Initialize email notification service.
        
        Args:
            mail: Flask-Mail Mail instance
            db: Database connection
        """
        self.mail = mail
        self.db = db
        self.template_manager = EmailTemplateManager()
        self.preferences = NotificationPreferences(db)
        self.queue = NotificationQueue(db)
    
    def send_league_invite(self, user_email: str, username: str, 
                          league_name: str, invited_by: str,
                          invite_code: str, expires_at: str) -> bool:
        """Send league invite email."""
        if not self.preferences.should_send_notification(0, NotificationEvent.LEAGUE_INVITE):
            return True
        
        template = self.template_manager.get_template(NotificationEvent.LEAGUE_INVITE)
        if not template:
            return False
        
        variables = {
            'username': username,
            'league_name': league_name,
            'invited_by': invited_by,
            'invite_code': invite_code,
            'expires_at': expires_at
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def send_achievement_unlocked(self, user_email: str, username: str,
                                 achievement_name: str, description: str,
                                 reward: str) -> bool:
        """Send achievement unlocked email."""
        template = self.template_manager.get_template(NotificationEvent.ACHIEVEMENT_UNLOCKED)
        if not template:
            return False
        
        variables = {
            'username': username,
            'achievement_name': achievement_name,
            'description': description,
            'reward': reward
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def send_milestone_reached(self, user_email: str, username: str,
                              milestone_name: str, league_name: str,
                              value: str) -> bool:
        """Send milestone reached email."""
        template = self.template_manager.get_template(NotificationEvent.MILESTONE_REACHED)
        if not template:
            return False
        
        variables = {
            'username': username,
            'milestone_name': milestone_name,
            'league_name': league_name,
            'value': value
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def send_rank_changed(self, user_email: str, username: str,
                         league_name: str, old_rank: int, new_rank: int,
                         portfolio_value: str) -> bool:
        """Send rank changed notification."""
        template = self.template_manager.get_template(NotificationEvent.RANK_CHANGED)
        if not template:
            return False
        
        variables = {
            'username': username,
            'league_name': league_name,
            'old_rank': old_rank,
            'new_rank': new_rank,
            'portfolio_value': portfolio_value
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def send_trade_confirmation(self, user_email: str, username: str,
                               action: str, shares: float, symbol: str,
                               price: str, total: str, league_name: str,
                               timestamp: str) -> bool:
        """Send trade confirmation email."""
        template = self.template_manager.get_template(NotificationEvent.TRADE_EXECUTED)
        if not template:
            return False
        
        variables = {
            'username': username,
            'action': action,
            'shares': shares,
            'symbol': symbol,
            'price': price,
            'total': total,
            'league_name': league_name,
            'timestamp': timestamp
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def send_league_announcement(self, user_email: str, username: str,
                                league_name: str, title: str,
                                message: str, posted_by: str) -> bool:
        """Send league announcement email."""
        template = self.template_manager.get_template(NotificationEvent.LEAGUE_ANNOUNCEMENT)
        if not template:
            return False
        
        variables = {
            'username': username,
            'league_name': league_name,
            'title': title,
            'message': message,
            'posted_by': posted_by
        }
        
        return self._send_email(
            to=user_email,
            subject=self._render_template(template.subject, variables),
            html=self._render_template(template.html_template, variables),
            text=self._render_template(template.text_template, variables)
        )
    
    def _send_email(self, to: str, subject: str, html: str, text: str) -> bool:
        """Send email through Flask-Mail."""
        try:
            from flask_mail import Message
            msg = Message(
                subject=subject,
                recipients=[to],
                html=html,
                body=text
            )
            self.mail.send(msg)
            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error sending email to {to}: {e}")
            return False
    
    @staticmethod
    def _render_template(template_str: str, variables: Dict) -> str:
        """Render template with variables."""
        result = template_str
        for key, value in variables.items():
            result = result.replace("{{ " + key + " }}", str(value))
        return result
