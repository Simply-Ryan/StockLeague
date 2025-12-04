// StockLeague JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Add loading state to buttons on form submit
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && form.checkValidity()) {
                submitButton.disabled = true;
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
                
                // Re-enable after 5 seconds as fallback
                setTimeout(() => {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }, 5000);
            }
        });
    });

    // Format currency inputs
    const currencyInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });

    // Table row click handler for portfolio
    const tableRows = document.querySelectorAll('.table-hover tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            const symbol = this.querySelector('td:first-child strong')?.textContent;
            if (symbol) {
                // You can add actions here, like showing a modal with stock details
                console.log('Clicked on stock:', symbol);
            }
        });
    });

    // Stock symbol uppercase enforcement
    const symbolInputs = document.querySelectorAll('input[name="symbol"]');
    symbolInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });

    // Confirmation for selling stocks
    const sellForm = document.querySelector('form[action="/sell"]');
    if (sellForm) {
        sellForm.addEventListener('submit', function(e) {
            const symbol = document.getElementById('symbol').value;
            const shares = document.getElementById('shares').value;
            
            if (symbol && shares) {
                const confirmed = confirm(`Are you sure you want to sell ${shares} shares of ${symbol}?`);
                if (!confirmed) {
                    e.preventDefault();
                }
            }
        });
    }

    // Real-time stock price updates (placeholder for WebSocket implementation)
    // This would require a WebSocket connection to get real-time updates
    function updateStockPrices() {
        // Placeholder for real-time price updates
        // In a production app, you'd connect to a WebSocket service
        console.log('Stock prices update placeholder');
    }

    // Uncomment to enable periodic price updates (every 30 seconds)
    // setInterval(updateStockPrices, 30000);

    // Add tooltips to all elements with title attribute
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Dark mode toggle (optional feature)
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        });

        // Load dark mode preference
        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
        }
    }

    // Chart initialization placeholder (for future Chart.js integration)
    function initializeCharts() {
        const chartElements = document.querySelectorAll('.stock-chart');
        chartElements.forEach(element => {
            // Placeholder for Chart.js initialization
            console.log('Chart placeholder for:', element.id);
        });
    }

    // Call chart initialization if charts exist on page
    if (document.querySelector('.stock-chart')) {
        initializeCharts();
    }

    // Handle quick amount buttons on add cash page
    const quickAmountButtons = document.querySelectorAll('.quick-amount');
    quickAmountButtons.forEach(button => {
        button.addEventListener('click', function() {
            const amount = this.dataset.amount;
            const amountInput = document.getElementById('amount');
            if (amountInput) {
                amountInput.value = amount;
                amountInput.focus();
            }
        });
    });

    // Handle quick quote buttons
    const quickQuoteButtons = document.querySelectorAll('.quick-quote');
    quickQuoteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.dataset.symbol;
            const symbolInput = document.getElementById('symbol');
            if (symbolInput) {
                symbolInput.value = symbol;
                // Auto-submit the form
                this.closest('form')?.submit();
            }
        });
    });

    // Add animation to cards on hover
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Console welcome message
    console.log('%c🚀 StockLeague Trading Platform', 'color: #667eea; font-size: 20px; font-weight: bold;');
    console.log('%cBuilt with Flask, Python, and Bootstrap', 'color: #764ba2; font-size: 14px;');
});

// Utility function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Utility function to format large numbers
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

// Error handling for fetch requests
async function fetchWithErrorHandling(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// Export functions for use in other scripts
window.StockLeague = {
    formatCurrency,
    formatNumber,
    fetchWithErrorHandling
};
