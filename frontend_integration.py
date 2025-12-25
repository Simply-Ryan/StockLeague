"""
Frontend Integration - Activity Feed Component Manager
Handles integration of engagement features into HTML templates
"""

import os
from pathlib import Path

def get_activity_feed_widget():
    """Get the HTML widget for activity feed display"""
    return '''<!-- League Activity Feed Widget -->
<div class="engagement-container">
    <div class="activity-feed-panel">
        <h3>
            <i class="fas fa-chart-line"></i> League Activity
            <span class="refresh-btn" onclick="refreshActivityFeed()">
                <i class="fas fa-sync-alt"></i>
            </span>
        </h3>
        
        <div id="activity-feed" class="activity-list">
            <div class="loading">Loading activities...</div>
        </div>
        
        <div class="feed-controls">
            <select id="activity-filter" onchange="filterActivities(this.value)">
                <option value="">All Activities</option>
                <option value="trade_buy">Buy Trades</option>
                <option value="trade_sell">Sell Trades</option>
                <option value="ranking_change">Ranking Changes</option>
                <option value="achievement_unlocked">Achievements</option>
                <option value="member_joined">Member Joined</option>
            </select>
            <input type="number" id="activity-limit" min="5" max="100" value="20" 
                   onchange="updateActivityLimit(this.value)" placeholder="Limit">
        </div>
    </div>
    
    <div class="metrics-panel">
        <h3>
            <i class="fas fa-chart-bar"></i> Performance Metrics
            <span class="refresh-btn" onclick="refreshMetrics()">
                <i class="fas fa-sync-alt"></i>
            </span>
        </h3>
        
        <div id="metrics-content" class="metrics-grid">
            <div class="loading">Loading metrics...</div>
        </div>
    </div>
    
    <div class="announcements-panel">
        <h3>
            <i class="fas fa-bullhorn"></i> Announcements
            <button class="btn-small" onclick="showCreateAnnouncement()" style="float: right;">
                <i class="fas fa-plus"></i> New
            </button>
        </h3>
        
        <div id="announcements-list" class="announcements-list">
            <div class="loading">Loading announcements...</div>
        </div>
    </div>
</div>

<style>
.engagement-container {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
    margin-top: 20px;
}

.activity-feed-panel,
.metrics-panel,
.announcements-panel {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.activity-feed-panel h3,
.metrics-panel h3,
.announcements-panel h3 {
    margin-top: 0;
    margin-bottom: 15px;
    font-size: 18px;
    color: #333;
    display: flex;
    align-items: center;
    gap: 8px;
}

.refresh-btn {
    cursor: pointer;
    color: #666;
    margin-left: auto;
    transition: color 0.2s;
}

.refresh-btn:hover {
    color: #0066cc;
    animation: spin 0.6s linear;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.activity-list {
    max-height: 400px;
    overflow-y: auto;
}

.activity-item {
    padding: 12px;
    border-bottom: 1px solid #e0e0e0;
    transition: background 0.2s;
}

.activity-item:hover {
    background: #f0f0f0;
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-time {
    font-size: 12px;
    color: #999;
}

.activity-type {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    margin: 5px 0;
}

.type-trade_buy { background: #d4edda; color: #155724; }
.type-trade_sell { background: #f8d7da; color: #721c24; }
.type-ranking_change { background: #d1ecf1; color: #0c5460; }
.type-achievement_unlocked { background: #fff3cd; color: #856404; }
.type-member_joined { background: #cce5ff; color: #004085; }

.feed-controls {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.feed-controls select,
.feed-controls input {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.metrics-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.metric-item {
    background: white;
    padding: 12px;
    border-radius: 4px;
    border-left: 4px solid #0066cc;
}

.metric-label {
    font-size: 12px;
    color: #666;
}

.metric-value {
    font-size: 20px;
    font-weight: bold;
    color: #333;
}

.announcements-list {
    max-height: 400px;
    overflow-y: auto;
}

.announcement-item {
    background: white;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 10px;
    border-left: 4px solid #0066cc;
}

.announcement-pinned {
    border-left-color: #ffc107;
    background: #fffbf0;
}

.announcement-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.announcement-time {
    font-size: 12px;
    color: #999;
}

.loading {
    text-align: center;
    color: #999;
    padding: 20px;
}

@media (max-width: 768px) {
    .engagement-container {
        grid-template-columns: 1fr;
    }
}
</style>

<script>
// Activity Feed Functions
async function refreshActivityFeed() {
    const leagueId = document.getElementById('league-id')?.value;
    if (!leagueId) return;
    
    try {
        const response = await fetch(`/api/engagement/league/${leagueId}/activity`);
        const data = await response.json();
        
        if (data.success) {
            displayActivityFeed(data.activities);
        } else {
            console.error('Error loading activities:', data.error);
        }
    } catch (error) {
        console.error('Activity fetch error:', error);
    }
}

function displayActivityFeed(activities) {
    const container = document.getElementById('activity-feed');
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<div class="activity-item">No activities yet</div>';
        return;
    }
    
    const html = activities.map(activity => `
        <div class="activity-item">
            <div>
                <span class="activity-type type-${activity.activity_type}">
                    ${formatActivityType(activity.activity_type)}
                </span>
            </div>
            <div>${activity.description}</div>
            <div class="activity-time">${formatTime(activity.created_at)}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function filterActivities(type) {
    const leagueId = document.getElementById('league-id')?.value;
    if (!leagueId) return;
    
    const filter = type ? `?type=${type}` : '';
    fetch(`/api/engagement/league/${leagueId}/activity${filter}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                displayActivityFeed(data.activities);
            }
        })
        .catch(e => console.error('Filter error:', e));
}

function updateActivityLimit(limit) {
    const leagueId = document.getElementById('league-id')?.value;
    if (!leagueId) return;
    
    fetch(`/api/engagement/league/${leagueId}/activity?limit=${limit}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                displayActivityFeed(data.activities);
            }
        })
        .catch(e => console.error('Limit update error:', e));
}

// Metrics Functions
async function refreshMetrics() {
    const leagueId = document.getElementById('league-id')?.value;
    const userId = document.getElementById('user-id')?.value;
    
    if (!leagueId || !userId) return;
    
    try {
        const response = await fetch(`/api/engagement/league/${leagueId}/user/${userId}/metrics`);
        const data = await response.json();
        
        if (data.success) {
            displayMetrics(data.metrics);
        }
    } catch (error) {
        console.error('Metrics error:', error);
    }
}

function displayMetrics(metrics) {
    const container = document.getElementById('metrics-content');
    
    if (!metrics) {
        container.innerHTML = '<div class="metric-item">No metrics available</div>';
        return;
    }
    
    const html = `
        <div class="metric-item">
            <div class="metric-label">Portfolio Value</div>
            <div class="metric-value">$${formatNumber(metrics.portfolio_value || 0)}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Rank</div>
            <div class="metric-value">#${metrics.rank || '--'}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">${(metrics.win_rate || 0).toFixed(1)}%</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Profit/Loss</div>
            <div class="metric-value" style="color: ${metrics.daily_pl >= 0 ? '#28a745' : '#dc3545'}">
                $${formatNumber(metrics.daily_pl || 0)}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Announcements Functions
async function refreshAnnouncements() {
    const leagueId = document.getElementById('league-id')?.value;
    if (!leagueId) return;
    
    try {
        const response = await fetch(`/api/engagement/league/${leagueId}/announcements`);
        const data = await response.json();
        
        if (data.success) {
            displayAnnouncements(data.announcements);
        }
    } catch (error) {
        console.error('Announcements error:', error);
    }
}

function displayAnnouncements(announcements) {
    const container = document.getElementById('announcements-list');
    
    if (!announcements || announcements.length === 0) {
        container.innerHTML = '<div class="announcement-item">No announcements</div>';
        return;
    }
    
    const html = announcements.map(ann => `
        <div class="announcement-item ${ann.pinned ? 'announcement-pinned' : ''}">
            <div class="announcement-title">
                ${ann.pinned ? '<i class="fas fa-thumbtack"></i> ' : ''}
                ${ann.title}
            </div>
            <div>${ann.content}</div>
            <div class="announcement-time">${formatTime(ann.created_at)}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function showCreateAnnouncement() {
    // Opens modal for creating new announcement
    console.log('Show create announcement modal');
}

// Utility Functions
function formatActivityType(type) {
    const map = {
        'trade_buy': 'Buy',
        'trade_sell': 'Sell',
        'ranking_change': 'Ranking',
        'achievement_unlocked': 'Achievement',
        'member_joined': 'Member Joined'
    };
    return map[type] || type;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / 1000; // seconds
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    
    return date.toLocaleDateString();
}

function formatNumber(num) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    refreshActivityFeed();
    refreshMetrics();
    refreshAnnouncements();
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        refreshActivityFeed();
        refreshMetrics();
        refreshAnnouncements();
    }, 30000);
});
</script>
'''

def add_engagement_widget_to_template(template_path):
    """Add engagement widget to a template file"""
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check if already added
    if 'engagement-container' in content:
        print(f"Widget already exists in {template_path}")
        return True
    
    # Find a good place to insert (after portfolio info, before traders list)
    widget = get_activity_feed_widget()
    
    # Insert before closing container or at end
    if '</div>' in content:
        # Insert before last closing div or at specific location
        content = content.replace('<!-- End League Content -->', widget + '\n<!-- End League Content -->', 1)
        if content.count('<!-- End League Content -->') == 1:
            # If pattern not found, append before last closing div
            content = content.rstrip()
            if content.endswith('</div>'):
                content = content[:-6] + '\n' + widget + '\n</div>'
    else:
        content += '\n' + widget
    
    with open(template_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Widget added to {template_path}")
    return True

def main():
    """Setup frontend integration"""
    print("Frontend Integration Setup")
    print("=" * 70)
    
    # Find league templates
    templates_dir = 'templates'
    target_templates = [
        'templates/league_detail.html',
        'templates/league.html',
    ]
    
    for template in target_templates:
        if os.path.exists(template):
            print(f"\nProcessing {template}...")
            add_engagement_widget_to_template(template)
        else:
            print(f"Template not found: {template}")
    
    print("\n" + "=" * 70)
    print("Frontend integration setup complete!")

if __name__ == '__main__':
    main()
