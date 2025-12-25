"""
Mobile Optimization System for StockLeague

Provides mobile-specific optimizations:
- Responsive design utilities
- Mobile touch interactions
- Adaptive layouts
- Performance optimization for mobile
- Mobile-specific CSS classes and utilities
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device type classification."""
    MOBILE = "mobile"           # < 576px
    TABLET = "tablet"           # 576px - 1024px
    DESKTOP = "desktop"         # > 1024px


class MobileDetector:
    """Detects and classifies device type from User-Agent."""
    
    MOBILE_KEYWORDS = [
        'mobile', 'android', 'iphone', 'ipod', 'blackberry',
        'windows phone', 'webos', 'palm', 'iemobile',
        'opera mini', 'opera mobi', 'nexus 7', 'nexus 10'
    ]
    
    TABLET_KEYWORDS = [
        'ipad', 'kindle', 'playbook', 'tablet', 'nexus 7',
        'nexus 10', 'xoom', 'droid', 'samsung'
    ]
    
    @staticmethod
    def detect_device_type(user_agent: str) -> DeviceType:
        """Detect device type from User-Agent header."""
        if not user_agent:
            return DeviceType.DESKTOP
        
        user_agent_lower = user_agent.lower()
        
        # Check for tablets first (more specific)
        for keyword in MobileDetector.TABLET_KEYWORDS:
            if keyword in user_agent_lower:
                # Exclude phones that might have tablet-like keywords
                if not any(kw in user_agent_lower for kw in MobileDetector.MOBILE_KEYWORDS):
                    return DeviceType.TABLET
        
        # Check for mobile
        for keyword in MobileDetector.MOBILE_KEYWORDS:
            if keyword in user_agent_lower:
                return DeviceType.MOBILE
        
        return DeviceType.DESKTOP
    
    @staticmethod
    def is_mobile(user_agent: str) -> bool:
        """Check if device is mobile."""
        return MobileDetector.detect_device_type(user_agent) == DeviceType.MOBILE


class MobileOptimization:
    """Main mobile optimization manager."""
    
    def __init__(self):
        """Initialize mobile optimization."""
        self.viewport_config = self._get_viewport_config()
        self.breakpoints = self._get_breakpoints()
        self.touch_targets = self._get_touch_targets()
    
    def _get_viewport_config(self) -> Dict[str, str]:
        """Get viewport configuration for mobile."""
        return {
            'width': 'device-width',
            'initial-scale': '1.0',
            'minimum-scale': '1.0',
            'maximum-scale': '5.0',
            'user-scalable': 'yes',
            'viewport-fit': 'cover'  # For notched phones
        }
    
    def _get_breakpoints(self) -> Dict[str, int]:
        """Get CSS breakpoints for responsive design."""
        return {
            'xs': 0,           # Extra small devices (< 576px)
            'sm': 576,         # Small devices (≥ 576px)
            'md': 768,         # Medium devices (≥ 768px)
            'lg': 992,         # Large devices (≥ 992px)
            'xl': 1200,        # Extra large devices (≥ 1200px)
            'xxl': 1400        # Extra extra large (≥ 1400px)
        }
    
    def _get_touch_targets(self) -> Dict[str, int]:
        """Get recommended touch target sizes (in pixels)."""
        return {
            'minimum': 44,     # Apple Human Interface Guidelines
            'comfortable': 48,  # Material Design recommended
            'large': 56        # For important actions
        }
    
    def get_viewport_meta_tag(self) -> str:
        """Generate viewport meta tag."""
        config = self.viewport_config
        content = ", ".join(f"{k}={v}" for k, v in config.items())
        return f'<meta name="viewport" content="{content}" />'
    
    def get_mobile_css(self) -> str:
        """Get mobile optimization CSS."""
        return """
/* Mobile Optimization CSS */

/* Viewport and Safe Area */
html {
    width: 100%;
    height: 100%;
    overflow-x: hidden;
}

body {
    margin: 0;
    padding: 0;
    width: 100%;
    -webkit-text-size-adjust: 100%;
    -moz-text-size-adjust: 100%;
    -ms-text-size-adjust: 100%;
    text-size-adjust: 100%;
    
    /* Prevent scroll bouncing */
    -webkit-user-select: none;
    -webkit-touch-callout: none;
    
    /* Better text rendering */
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Safe area insets for notched phones */
@supports (padding: max(0px)) {
    body {
        padding-left: max(padding-left, env(safe-area-inset-left));
        padding-right: max(padding-right, env(safe-area-inset-right));
    }
    
    .navbar {
        padding-top: max(0px, env(safe-area-inset-top));
        padding-left: max(0px, env(safe-area-inset-left));
        padding-right: max(0px, env(safe-area-inset-right));
    }
    
    .navbar-bottom {
        padding-bottom: max(padding-bottom, env(safe-area-inset-bottom));
    }
}

/* Touch Target Sizes */
button, a.btn, input[type="button"], 
input[type="submit"], input[type="reset"] {
    min-width: 48px;
    min-height: 48px;
    padding: 12px 16px;
}

a, label, input[type="radio"], 
input[type="checkbox"], select {
    min-height: 44px;
    padding: 8px 12px;
}

/* Remove tap highlight on mobile */
button, a {
    -webkit-tap-highlight-color: rgba(0, 0, 0, 0.1);
}

/* Input improvements */
input, textarea, select {
    border-radius: 8px;
    font-size: 16px; /* Prevents zoom on iOS */
    padding: 12px;
    border: 1px solid #ddd;
}

input:focus, textarea:focus, select:focus {
    outline: 2px solid #0066cc;
    outline-offset: 2px;
}

/* Prevent iOS input zoom */
input[type="email"],
input[type="number"],
input[type="password"],
input[type="search"],
input[type="tel"],
input[type="text"],
input[type="url"],
select,
textarea {
    font-size: 16px;
}

/* Better form labels on mobile */
label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #333;
}

/* Cards and containers */
.card, .container-like {
    border-radius: 8px;
    overflow: hidden;
}

/* List improvements */
ul, ol {
    margin: 0;
    padding-left: 20px;
}

li {
    padding: 8px 0;
}

/* Images responsive */
img {
    max-width: 100%;
    height: auto;
    display: block;
}

/* Tables on mobile */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
}

table th, table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

/* Navigation adjustments */
.navbar {
    position: sticky;
    top: 0;
    z-index: 1000;
    border-bottom: 1px solid #eee;
}

.navbar-toggler {
    border: none;
    padding: 8px;
}

.navbar-brand {
    font-size: 18px;
    font-weight: 600;
}

/* Content spacing */
.container {
    padding: 16px;
}

.container-sm {
    padding: 12px;
}

/* Margins and padding utilities */
.mt-mobile {
    margin-top: 16px;
}

.mb-mobile {
    margin-bottom: 16px;
}

.px-mobile {
    padding-left: 12px;
    padding-right: 12px;
}

.py-mobile {
    padding-top: 12px;
    padding-bottom: 12px;
}

/* Modal improvements */
.modal {
    width: 100% !important;
    height: 100% !important;
    max-height: 100vh;
}

.modal-content {
    border-radius: 12px 12px 0 0;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
}

.modal-header {
    padding: 16px;
    border-bottom: 1px solid #eee;
}

.modal-body {
    padding: 16px;
}

.modal-footer {
    padding: 16px;
    border-top: 1px solid #eee;
}

/* Drawer/Sidebar adjustments */
.drawer, .sidebar {
    position: fixed;
    width: 80%;
    max-width: 300px;
    height: 100vh;
    z-index: 1001;
    background: white;
    overflow-y: auto;
}

/* Bottom navigation for mobile */
.navbar-bottom {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: space-around;
    background: white;
    border-top: 1px solid #eee;
    z-index: 1000;
}

.navbar-bottom-item {
    flex: 1;
    text-align: center;
    padding: 12px 8px;
    min-height: 56px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    cursor: pointer;
    border-radius: 8px;
}

.navbar-bottom-item:active {
    background: #f5f5f5;
}

.navbar-bottom-item i {
    font-size: 24px;
}

.navbar-bottom-item span {
    font-size: 12px;
}

/* Content adjustment for bottom nav */
body.has-bottom-nav {
    padding-bottom: 70px;
}

/* Utility Classes for Mobile */
.d-mobile { display: none; }
.d-mobile-block { display: none; }
.d-mobile-inline { display: none; }
.d-mobile-flex { display: none; }
.d-mobile-grid { display: none; }

.hide-on-mobile { display: block; }
.show-on-mobile { display: none; }

.text-center-mobile { text-align: left; }
.text-start-mobile { text-align: left; }
.text-end-mobile { text-align: left; }

/* Responsive Typography */
h1, h2, h3, h4, h5, h6 {
    line-height: 1.3;
    margin: 16px 0 8px 0;
}

p {
    line-height: 1.6;
    margin: 8px 0;
}

/* Extra small devices (portrait phones, less than 576px) */
@media (max-width: 575.98px) {
    .d-mobile { display: block !important; }
    .d-mobile-block { display: block !important; }
    .d-mobile-inline { display: inline !important; }
    .d-mobile-flex { display: flex !important; }
    .d-mobile-grid { display: grid !important; }
    
    .hide-on-mobile { display: none !important; }
    .show-on-mobile { display: block !important; }
    
    .text-center-mobile { text-align: center; }
    .text-start-mobile { text-align: start; }
    .text-end-mobile { text-align: end; }
    
    /* Adjust font sizes */
    h1 { font-size: 24px; }
    h2 { font-size: 20px; }
    h3 { font-size: 18px; }
    h4 { font-size: 16px; }
    h5 { font-size: 14px; }
    
    body { font-size: 14px; }
    
    /* Adjust spacing */
    .container { padding: 12px; }
    .card { margin: 8px 0; }
    
    /* Full width buttons on mobile */
    .btn-mobile-full {
        width: 100%;
        display: block;
    }
    
    /* Stacked columns */
    .row-mobile-stack > [class*="col"] {
        margin-bottom: 12px;
    }
}

/* Small devices (landscape phones, 576px and up) */
@media (min-width: 576px) {
    h1 { font-size: 28px; }
    h2 { font-size: 24px; }
    h3 { font-size: 20px; }
    
    .container { padding: 16px; }
}

/* Medium devices (tablets, 768px and up) */
@media (min-width: 768px) {
    .hide-on-tablet { display: none !important; }
    .show-on-tablet { display: block !important; }
    
    h1 { font-size: 32px; }
    h2 { font-size: 28px; }
    h3 { font-size: 24px; }
    
    .container { padding: 20px; }
}

/* Large devices (desktops, 992px and up) */
@media (min-width: 992px) {
    .hide-on-desktop { display: none !important; }
    .show-on-desktop { display: block !important; }
    
    h1 { font-size: 36px; }
    h2 { font-size: 32px; }
}
"""
    
    def get_mobile_javascript(self) -> str:
        """Get mobile optimization JavaScript."""
        return """
// Mobile Optimization JavaScript

(function() {
    'use strict';
    
    // Detect device type
    const Mobile = {
        isPhone: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
        isMobile: /Android|webOS|iPhone|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
        isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        isAndroid: /Android/.test(navigator.userAgent),
        
        // Check if touch enabled
        isTouchEnabled: () => {
            return (('ontouchstart' in window) ||
                    (navigator.maxTouchPoints > 0) ||
                    (navigator.msMaxTouchPoints > 0));
        },
        
        // Get viewport width
        getViewportWidth: () => {
            return Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
        },
        
        // Get viewport height
        getViewportHeight: () => {
            return Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
        }
    };
    
    // Touch event handling
    const TouchHandling = {
        enableFastClick: () => {
            // Remove 300ms delay on tap
            document.addEventListener('touchend', (e) => {
                if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON') {
                    e.target.click();
                }
            }, false);
        },
        
        // Handle long press
        onLongPress: (element, callback, duration = 500) => {
            let pressTimer = null;
            
            element.addEventListener('touchstart', () => {
                pressTimer = setTimeout(() => {
                    callback();
                }, duration);
            });
            
            element.addEventListener('touchend', () => {
                if (pressTimer) clearTimeout(pressTimer);
            });
        },
        
        // Handle swipe
        onSwipe: (element, callback) => {
            let startX, startY;
            
            element.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            });
            
            element.addEventListener('touchend', (e) => {
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                
                const deltaX = endX - startX;
                const deltaY = endY - startY;
                
                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    if (deltaX > 0) {
                        callback('right');
                    } else {
                        callback('left');
                    }
                } else {
                    if (deltaY > 0) {
                        callback('down');
                    } else {
                        callback('up');
                    }
                }
            });
        }
    };
    
    // Performance optimizations
    const Performance = {
        // Lazy load images
        lazyLoadImages: () => {
            if ('IntersectionObserver' in window) {
                const images = document.querySelectorAll('img[data-src]');
                const imageObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    });
                });
                images.forEach(img => imageObserver.observe(img));
            }
        },
        
        // Debounce function
        debounce: (func, delay) => {
            let timeout;
            return (...args) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => func(...args), delay);
            };
        },
        
        // Throttle function
        throttle: (func, limit) => {
            let inThrottle;
            return (...args) => {
                if (!inThrottle) {
                    func(...args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        }
    };
    
    // Viewport utilities
    const Viewport = {
        addClassOnScroll: (className, offset = 0) => {
            window.addEventListener('scroll', Performance.throttle(() => {
                if (window.scrollY > offset) {
                    document.body.classList.add(className);
                } else {
                    document.body.classList.remove(className);
                }
            }, 100));
        },
        
        // Hide navbar on scroll down
        hideNavbarOnScroll: (navbarSelector = '.navbar') => {
            let lastScrollTop = 0;
            const navbar = document.querySelector(navbarSelector);
            
            window.addEventListener('scroll', Performance.throttle(() => {
                const st = window.scrollY;
                if (st > lastScrollTop && st > 100) {
                    navbar.style.transform = 'translateY(-100%)';
                } else {
                    navbar.style.transform = 'translateY(0)';
                }
                lastScrollTop = st <= 0 ? 0 : st;
            }, 100), false);
        }
    };
    
    // Orientation handling
    const Orientation = {
        isPortrait: () => window.innerHeight > window.innerWidth,
        isLandscape: () => window.innerWidth > window.innerHeight,
        
        onOrientationChange: (callback) => {
            window.addEventListener('orientationchange', callback);
            window.addEventListener('resize', callback);
        }
    };
    
    // Export to window
    window.Mobile = Mobile;
    window.TouchHandling = TouchHandling;
    window.Performance = Performance;
    window.Viewport = Viewport;
    window.Orientation = Orientation;
    
    // Initialize on load
    document.addEventListener('DOMContentLoaded', () => {
        // Enable optimizations if touch-enabled
        if (Mobile.isTouchEnabled()) {
            document.body.classList.add('touch-enabled');
            TouchHandling.enableFastClick();
        }
        
        // Lazy load images
        Performance.lazyLoadImages();
    });
})();
"""


class MobileUIComponents:
    """Mobile-specific UI components."""
    
    @staticmethod
    def get_bottom_navigation_template() -> str:
        """Get bottom navigation template for mobile."""
        return """
        <nav class="navbar-bottom" id="bottomNav">
            <div class="navbar-bottom-item" data-page="home">
                <i class="fas fa-home"></i>
                <span>Home</span>
            </div>
            <div class="navbar-bottom-item" data-page="portfolio">
                <i class="fas fa-briefcase"></i>
                <span>Portfolio</span>
            </div>
            <div class="navbar-bottom-item" data-page="explore">
                <i class="fas fa-search"></i>
                <span>Explore</span>
            </div>
            <div class="navbar-bottom-item" data-page="leagues">
                <i class="fas fa-trophy"></i>
                <span>Leagues</span>
            </div>
            <div class="navbar-bottom-item" data-page="profile">
                <i class="fas fa-user"></i>
                <span>Profile</span>
            </div>
        </nav>
        """
    
    @staticmethod
    def get_mobile_menu_template() -> str:
        """Get mobile menu template."""
        return """
        <div class="mobile-menu drawer" id="mobileMenu">
            <div class="drawer-header">
                <h3>Menu</h3>
                <button class="close-btn" id="closeMenu">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="drawer-content">
                <a href="/home" class="menu-item">
                    <i class="fas fa-home"></i> Home
                </a>
                <a href="/leagues" class="menu-item">
                    <i class="fas fa-trophy"></i> Leagues
                </a>
                <a href="/explore" class="menu-item">
                    <i class="fas fa-search"></i> Explore
                </a>
                <a href="/portfolio" class="menu-item">
                    <i class="fas fa-briefcase"></i> Portfolio
                </a>
                <a href="/profile" class="menu-item">
                    <i class="fas fa-user"></i> Profile
                </a>
                <a href="/settings" class="menu-item">
                    <i class="fas fa-cog"></i> Settings
                </a>
                <a href="/logout" class="menu-item">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
        """
    
    @staticmethod
    def get_mobile_search_template() -> str:
        """Get mobile search template."""
        return """
        <div class="mobile-search" id="mobileSearch">
            <div class="search-input-group">
                <input type="text" class="form-control" 
                       placeholder="Search stocks..." 
                       id="mobileSearchInput"
                       autocomplete="off">
                <button class="btn-search">
                    <i class="fas fa-search"></i>
                </button>
            </div>
            <div class="search-results" id="searchResults"></div>
        </div>
        """
    
    @staticmethod
    def get_floating_action_button_template(action: str, label: str, icon: str) -> str:
        """Get floating action button template."""
        return f"""
        <button class="fab btn-primary fab-{action}" 
                data-action="{action}" 
                title="{label}">
            <i class="fas fa-{icon}"></i>
        </button>
        """


def mobile_responsive(f):
    """Decorator to add mobile optimization headers to response."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        # Add headers for mobile optimization if needed
        if hasattr(response, 'headers'):
            response.headers['X-UA-Compatible'] = 'IE=edge'
            response.headers['viewport'] = 'width=device-width, initial-scale=1'
        return response
    return decorated_function
