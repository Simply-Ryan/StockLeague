/**
 * Real-time WebSocket Trading Features
 * Handles live price updates, portfolio changes, and order notifications
 */

// Initialize Socket.IO connection (if not already connected)
if (typeof socket === 'undefined') {
    var socket = io();
}

// Track subscribed symbols
const subscribedSymbols = new Set();

/**
 * Subscribe to real-time price updates for a symbol
 */
function subscribeToStock(symbol) {
    if (!symbol || subscribedSymbols.has(symbol)) {
        return;
    }
    
    socket.emit('subscribe_stock', { symbol: symbol.toUpperCase() });
    subscribedSymbols.add(symbol.toUpperCase());
    console.log(`Subscribed to ${symbol}`);
}

/**
 * Unsubscribe from price updates
 */
function unsubscribeFromStock(symbol) {
    if (!symbol || !subscribedSymbols.has(symbol)) {
        return;
    }
    
    socket.emit('unsubscribe_stock', { symbol: symbol.toUpperCase() });
    subscribedSymbols.delete(symbol.toUpperCase());
    console.log(`Unsubscribed from ${symbol}`);
}

/**
 * Handle incoming stock price updates
 */
socket.on('stock_update', function(data) {
    const { symbol, price, change_percent, volume, high, low, open, timestamp } = data;
    
    // Update price displays on the page
    const priceElements = document.querySelectorAll(`[data-symbol="${symbol}"]`);
    priceElements.forEach(el => {
        // Update price
        const priceEl = el.querySelector('.stock-price');
        if (priceEl) {
            priceEl.textContent = formatCurrency(price);
            
            // Add animation
            priceEl.classList.remove('price-update');
            void priceEl.offsetWidth; // Trigger reflow
            priceEl.classList.add('price-update');
        }
        
        // Update change percentage
        const changeEl = el.querySelector('.stock-change');
        if (changeEl) {
            const changeText = change_percent >= 0 ? `+${change_percent.toFixed(2)}%` : `${change_percent.toFixed(2)}%`;
            changeEl.textContent = changeText;
            changeEl.className = 'stock-change ' + (change_percent >= 0 ? 'text-success' : 'text-danger');
        }
        
        // Update volume if displayed
        const volumeEl = el.querySelector('.stock-volume');
        if (volumeEl && volume) {
            volumeEl.textContent = formatVolume(volume);
        }
    });
    
    // Update chart if it exists
    if (window.stockChart && window.stockChart.symbol === symbol) {
        updateStockChart(data);
    }
});

/**
 * Handle portfolio value updates
 */
socket.on('portfolio_update', function(data) {
    const { cash, total_value, stocks } = data;
    
    // Update cash display
    const cashEl = document.getElementById('user-cash');
    if (cashEl) {
        cashEl.textContent = formatCurrency(cash);
        animateValueChange(cashEl);
    }
    
    // Update total portfolio value
    const totalEl = document.getElementById('portfolio-value');
    if (totalEl) {
        totalEl.textContent = formatCurrency(total_value);
        animateValueChange(totalEl);
    }
    
    // Update holdings table
    stocks.forEach(stock => {
        const row = document.querySelector(`tr[data-symbol="${stock.symbol}"]`);
        if (row) {
            const sharesEl = row.querySelector('.shares-count');
            if (sharesEl) {
                sharesEl.textContent = stock.shares;
                animateValueChange(sharesEl);
            }
        }
    });
    
    console.log('Portfolio updated:', data);
});

/**
 * Handle order execution notifications
 */
socket.on('order_executed', function(data) {
    const { type, symbol, shares, price, total, timestamp } = data;
    
    // Show toast notification
    const action = type === 'buy' ? 'Bought' : 'Sold';
    const toastHtml = `
        <div class="toast align-items-center text-white ${type === 'buy' ? 'bg-success' : 'bg-info'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${action} ${shares} shares of ${symbol}</strong><br>
                    <small>@ ${formatCurrency(price)} = ${formatCurrency(total)}</small>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    showToast(toastHtml);
    
    // Play sound notification (optional)
    playNotificationSound();
    
    console.log('Order executed:', data);
});

/**
 * Handle connection events
 */
socket.on('connect', function() {
    console.log('WebSocket connected');
    
    // Resubscribe to any active symbols
    subscribedSymbols.forEach(symbol => {
        socket.emit('subscribe_stock', { symbol: symbol });
    });
});

socket.on('disconnect', function() {
    console.log('WebSocket disconnected');
});

socket.on('error', function(error) {
    console.error('WebSocket error:', error);
});

/**
 * Utility Functions
 */

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

function formatVolume(volume) {
    if (volume >= 1000000) {
        return (volume / 1000000).toFixed(2) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(2) + 'K';
    }
    return volume.toString();
}

function animateValueChange(element) {
    element.classList.remove('value-change');
    void element.offsetWidth; // Trigger reflow
    element.classList.add('value-change');
    
    setTimeout(() => {
        element.classList.remove('value-change');
    }, 1000);
}

function showToast(html) {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    // Add toast
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const toastElement = tempDiv.firstElementChild;
    container.appendChild(toastElement);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

function playNotificationSound() {
    // Optional: Add a subtle notification sound
    // Uncomment if you add a sound file
    // const audio = new Audio('/static/sounds/notification.mp3');
    // audio.volume = 0.3;
    // audio.play().catch(e => console.log('Sound play failed:', e));
}

/**
 * Chart update function
 */
function updateStockChart(data) {
    if (!window.stockChart || !window.stockChart.chart) {
        return;
    }
    
    const chart = window.stockChart.chart;
    const { price, high, low, open, volume, timestamp } = data;
    
    // Add new data point to chart
    const newDataPoint = {
        x: new Date(timestamp),
        y: [open, high, low, price]  // OHLC format
    };
    
    // Update chart data
    if (chart.data.datasets && chart.data.datasets[0]) {
        chart.data.datasets[0].data.push(newDataPoint);
        
        // Keep only last N points (e.g., 100)
        if (chart.data.datasets[0].data.length > 100) {
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none'); // Update without animation for smooth real-time updates
    }
}

/**
 * Auto-subscribe to stocks on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Subscribe to stocks in portfolio
    const portfolioSymbols = document.querySelectorAll('[data-symbol]');
    portfolioSymbols.forEach(el => {
        const symbol = el.getAttribute('data-symbol');
        if (symbol) {
            subscribeToStock(symbol);
        }
    });
    
    // Subscribe to quote page symbol
    const quoteSymbol = document.getElementById('quote-symbol');
    if (quoteSymbol) {
        const symbol = quoteSymbol.value || quoteSymbol.textContent;
        if (symbol) {
            subscribeToStock(symbol);
        }
    }
});

// Export functions for use in other scripts
window.realtimeTrading = {
    subscribeToStock,
    unsubscribeFromStock,
    subscribedSymbols
};
