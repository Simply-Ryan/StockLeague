/**
 * Real-time Leaderboard Updates
 * Handles WebSocket subscriptions to league leaderboard changes
 */

if (typeof socket === 'undefined') {
    var socket = io();
}

// Track subscribed leagues
const subscribedLeaderboards = new Set();

/**
 * Subscribe to real-time leaderboard updates for a league
 */
function subscribeToLeaderboard(leagueId) {
    if (!leagueId || subscribedLeaderboards.has(leagueId)) {
        return;
    }
    
    socket.emit('subscribe_leaderboard', { league_id: leagueId });
    subscribedLeaderboards.add(leagueId);
    console.log(`Subscribed to leaderboard for league ${leagueId}`);
}

/**
 * Unsubscribe from leaderboard updates
 */
function unsubscribeFromLeaderboard(leagueId) {
    if (!leagueId || !subscribedLeaderboards.has(leagueId)) {
        return;
    }
    
    socket.emit('unsubscribe_leaderboard', { league_id: leagueId });
    subscribedLeaderboards.delete(leagueId);
    console.log(`Unsubscribed from leaderboard for league ${leagueId}`);
}

/**
 * Request current leaderboard snapshot
 */
function requestLeaderboard(leagueId) {
    if (!leagueId) {
        console.error('leagueId is required');
        return;
    }
    
    socket.emit('request_leaderboard', { league_id: leagueId });
}

/**
 * Request details for a specific league member
 */
function requestMemberDetails(leagueId, userId) {
    if (!leagueId || !userId) {
        console.error('leagueId and userId are required');
        return;
    }
    
    socket.emit('request_leaderboard_member', { league_id: leagueId, user_id: userId });
}

/**
 * Handle leaderboard snapshots (initial data when subscribing)
 */
socket.on('leaderboard_snapshot', function(data) {
    const { league_id, members, timestamp } = data;
    console.log(`Received leaderboard snapshot for league ${league_id}`, members);
    
    // Update leaderboard table
    updateLeaderboardTable(league_id, members);
    
    // Update cache
    if (typeof leaderboardCache === 'undefined') {
        window.leaderboardCache = {};
    }
    window.leaderboardCache[league_id] = {
        members: members,
        timestamp: timestamp
    };
});

/**
 * Handle leaderboard data (requested snapshot)
 */
socket.on('leaderboard_data', function(data) {
    const { league_id, members, timestamp } = data;
    console.log(`Received leaderboard data for league ${league_id}`, members);
    
    // Update leaderboard table
    updateLeaderboardTable(league_id, members);
    
    // Update cache
    if (typeof leaderboardCache === 'undefined') {
        window.leaderboardCache = {};
    }
    window.leaderboardCache[league_id] = {
        members: members,
        timestamp: timestamp
    };
});

/**
 * Handle real-time leaderboard updates (changes detected)
 */
socket.on('leaderboard_update', function(data) {
    const { league_id, members, changes } = data;
    console.log(`Received leaderboard update for league ${league_id}`, changes);
    
    // Update leaderboard table
    updateLeaderboardTable(league_id, members);
    
    // Show alerts for significant changes
    if (changes && changes.rank_changes) {
        changes.rank_changes.forEach(change => {
            showRankChangeAlert(change);
        });
    }
    
    if (changes && changes.value_changes) {
        changes.value_changes.forEach(change => {
            animateValueChange(league_id, change);
        });
    }
    
    // Update cache
    if (typeof leaderboardCache === 'undefined') {
        window.leaderboardCache = {};
    }
    window.leaderboardCache[league_id] = {
        members: members,
        timestamp: new Date().toISOString()
    };
});

/**
 * Handle rank change alerts
 */
socket.on('rank_alert', function(data) {
    const { league_id, user_id, alert_data } = data;
    console.log(`Rank alert for user ${user_id}:`, alert_data);
    
    // Show notification
    const { old_rank, new_rank, rank_movement } = alert_data;
    const direction = rank_movement > 0 ? 'up' : 'down';
    const absMovement = Math.abs(rank_movement);
    
    showNotification(
        `Rank ${direction === 'up' ? '📈 Up' : '📉 Down'}`,
        `You moved ${direction} ${absMovement} position${absMovement > 1 ? 's' : ''}!`,
        direction === 'up' ? 'success' : 'info',
        5000
    );
});

/**
 * Handle milestone alerts
 */
socket.on('milestone_alert', function(data) {
    const { league_id, user_id, type, data: alertData } = data;
    console.log(`Milestone alert for user ${user_id}:`, type, alertData);
    
    let message = '';
    let icon = '';
    
    switch(type) {
        case 'first_place':
            message = 'Congratulations! You took first place! 🏆';
            icon = '🏆';
            break;
        case 'top_three':
            message = `You\'re in the top 3! 🎖️ (Rank #${alertData.rank})`;
            icon = '🎖️';
            break;
        case 'positive_return':
            message = `Your portfolio is now in profit! 📈 (+${alertData.return_pct.toFixed(2)}%)`;
            icon = '📈';
            break;
        case 'new_high':
            message = `New portfolio high! 💎 $${alertData.total_value.toFixed(2)}`;
            icon = '💎';
            break;
        default:
            message = 'Milestone reached!';
            icon = '⭐';
    }
    
    showNotification(icon, message, 'success', 6000);
});

/**
 * Handle member details
 */
socket.on('leaderboard_member', function(data) {
    const { league_id, member, timestamp } = data;
    console.log(`Received member details for league ${league_id}:`, member);
    
    // Update member details in UI (if there's a details panel)
    const detailsPanel = document.getElementById(`member-details-${member.user_id}`);
    if (detailsPanel) {
        updateMemberDetailsPanel(detailsPanel, member);
    }
});

/**
 * Handle leaderboard errors
 */
socket.on('leaderboard_error', function(data) {
    console.error('Leaderboard error:', data.message);
    showNotification('⚠️', data.message, 'error', 4000);
});

/**
 * Update leaderboard table with new member data
 */
function updateLeaderboardTable(leagueId, members) {
    const table = document.querySelector(`[data-league-id="${leagueId}"] .leaderboard-table tbody`);
    if (!table) {
        console.warn(`Leaderboard table not found for league ${leagueId}`);
        return;
    }
    
    // Clear existing rows
    table.innerHTML = '';
    
    // Add new rows
    members.forEach((member, index) => {
        const row = document.createElement('tr');
        row.className = 'leaderboard-row';
        row.setAttribute('data-user-id', member.user_id);
        
        const rankColor = getRankColor(index + 1);
        const returnClass = member.profit_loss >= 0 ? 'positive' : 'negative';
        
        row.innerHTML = `
            <td class="rank ${rankColor}">
                <span class="rank-badge">#${index + 1}</span>
            </td>
            <td class="username">
                <span class="username-text">${escapeHtml(member.username)}</span>
            </td>
            <td class="portfolio-value">
                $${parseFloat(member.total_value).toFixed(2)}
            </td>
            <td class="profit-loss ${returnClass}">
                <span class="amount">${parseFloat(member.profit_loss).toFixed(2)}</span>
                <span class="percent">${parseFloat(member.return_pct).toFixed(2)}%</span>
            </td>
            <td class="shares">
                ${member.share_count || 0} shares
            </td>
        `;
        
        table.appendChild(row);
    });
    
    console.log(`Updated leaderboard table for league ${leagueId} with ${members.length} members`);
}

/**
 * Show rank change animation/alert
 */
function showRankChangeAlert(change) {
    const { user_id, old_rank, new_rank, username } = change;
    const movement = old_rank - new_rank; // Positive = rank up, Negative = rank down
    
    if (movement === 0) return; // No change
    
    const row = document.querySelector(`.leaderboard-row[data-user-id="${user_id}"]`);
    if (!row) return;
    
    // Add animation class
    if (movement > 0) {
        row.classList.add('rank-up');
        setTimeout(() => row.classList.remove('rank-up'), 1000);
    } else {
        row.classList.add('rank-down');
        setTimeout(() => row.classList.remove('rank-down'), 1000);
    }
}

/**
 * Animate value change with highlight
 */
function animateValueChange(leagueId, change) {
    const { user_id, old_value, new_value } = change;
    const valueElement = document.querySelector(
        `[data-league-id="${leagueId}"] .leaderboard-row[data-user-id="${user_id}"] .portfolio-value`
    );
    
    if (!valueElement) return;
    
    const isIncrease = new_value > old_value;
    valueElement.classList.add(isIncrease ? 'value-increase' : 'value-decrease');
    
    setTimeout(() => {
        valueElement.classList.remove('value-increase', 'value-decrease');
    }, 1500);
}

/**
 * Update member details panel
 */
function updateMemberDetailsPanel(panel, member) {
    panel.innerHTML = `
        <div class="member-details">
            <h4>${escapeHtml(member.username)}</h4>
            <div class="detail-row">
                <span class="label">Rank:</span>
                <span class="value">#${member.rank}</span>
            </div>
            <div class="detail-row">
                <span class="label">Portfolio Value:</span>
                <span class="value">$${parseFloat(member.total_value).toFixed(2)}</span>
            </div>
            <div class="detail-row">
                <span class="label">Profit/Loss:</span>
                <span class="value ${member.profit_loss >= 0 ? 'positive' : 'negative'}">
                    $${parseFloat(member.profit_loss).toFixed(2)}
                </span>
            </div>
            <div class="detail-row">
                <span class="label">Return %:</span>
                <span class="value ${member.return_pct >= 0 ? 'positive' : 'negative'}">
                    ${parseFloat(member.return_pct).toFixed(2)}%
                </span>
            </div>
            <div class="detail-row">
                <span class="label">Shares Owned:</span>
                <span class="value">${member.share_count || 0}</span>
            </div>
        </div>
    `;
}

/**
 * Show notification toast
 */
function showNotification(icon, message, type = 'info', duration = 3000) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;
    
    // Add to page
    const container = document.getElementById('toast-container');
    if (container) {
        container.appendChild(toast);
    } else {
        document.body.appendChild(toast);
    }
    
    // Remove after duration
    setTimeout(() => {
        toast.remove();
    }, duration);
}

/**
 * Get color class for rank badge
 */
function getRankColor(rank) {
    if (rank === 1) return 'gold';
    if (rank === 2) return 'silver';
    if (rank === 3) return 'bronze';
    return 'default';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Initialize leaderboard real-time updates on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Auto-subscribe to leaderboard if we're on a league detail page
    const leagueId = document.body.getAttribute('data-league-id');
    if (leagueId) {
        console.log(`Auto-subscribing to leaderboard for league ${leagueId}`);
        subscribeToLeaderboard(leagueId);
    }
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        subscribedLeaderboards.forEach(leagueId => {
            unsubscribeFromLeaderboard(leagueId);
        });
    });
});
