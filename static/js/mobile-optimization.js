/**
 * Mobile UX Optimization
 * Provides enhanced mobile experience without affecting desktop UX
 */

class MobileOptimization {
    constructor() {
        this.isMobile = this.detectMobile();
        this.isTablet = this.detectTablet();
        this.viewportWidth = window.innerWidth;
        this.viewportHeight = window.innerHeight;
        
        if (this.isMobile || this.isTablet) {
            this.init();
        }
    }
    
    /**
     * Detect if device is mobile
     */
    detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
            || window.innerWidth < 768;
    }
    
    /**
     * Detect if device is tablet
     */
    detectTablet() {
        return /iPad|Android/i.test(navigator.userAgent) && window.innerWidth >= 768;
    }
    
    /**
     * Initialize all mobile optimizations
     */
    init() {
        this.optimizeViewport();
        this.enhanceNavigation();
        this.optimizeForms();
        this.optimizeModals();
        this.enhanceTouchInteractions();
        this.optimizeScrolling();
        this.handleOrientation();
        this.preventCommonMobileIssues();
        
        // Listen for viewport changes
        window.addEventListener('resize', () => this.handleResize());
        window.addEventListener('orientationchange', () => this.handleOrientation());
    }
    
    /**
     * Optimize viewport settings
     */
    optimizeViewport() {
        // Ensure viewport is properly set (it should be in HTML, but verify)
        let viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            // Verify viewport settings are correct
            const content = viewport.getAttribute('content');
            if (!content.includes('viewport-fit=cover')) {
                viewport.setAttribute('content', 
                    'width=device-width, initial-scale=1.0, viewport-fit=cover, maximum-scale=1.0');
            }
        }
    }
    
    /**
     * Enhance mobile navigation with complete redesign
     */
    enhanceNavigation() {
        console.log('%c🔍 MobileOptimization: Starting navigation setup', 'color: blue; font-weight: bold');
        
        // Only run on mobile
        if (window.innerWidth > 768) {
            console.log('📱 Viewport:', window.innerWidth, '- Desktop, skipping mobile navbar setup');
            return;
        }
        
        console.log('📱 Viewport:', window.innerWidth, '- Mobile, setting up navbar');
        
        // Find elements
        let toggler = document.getElementById('mobileToggler');
        const collapse = document.getElementById('navbarNav');
        
        if (!toggler) {
            console.error('❌ Could not find #mobileToggler');
            return;
        }
        if (!collapse) {
            console.error('❌ Could not find #navbarNav');
            return;
        }
        
        console.log('✅ Found elements:', { toggler, collapse });
        
        // Step 1: Destroy any existing Bootstrap Collapse instances
        try {
            const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapse);
            if (bsCollapse) {
                bsCollapse.hide();  // Make sure it's hidden first
                bsCollapse.dispose();  // Destroy the instance
                console.log('✅ Destroyed Bootstrap Collapse instance');
            }
        } catch (e) {
            console.log('ℹ️  No Bootstrap Collapse to destroy');
        }
        
        // Step 2: Remove all Bootstrap data attributes that trigger auto-initialization
        toggler.removeAttribute('data-bs-toggle');
        toggler.removeAttribute('data-bs-target');
        toggler.removeAttribute('data-bs-parent');
        collapse.removeAttribute('data-bs-parent');
        console.log('✅ Removed Bootstrap data attributes');
        
        // Step 3: Clone button to remove ALL event listeners (including Bootstrap's)
        const newToggler = toggler.cloneNode(true);
        toggler.parentNode.replaceChild(newToggler, toggler);
        toggler = newToggler;
        console.log('✅ Cloned button to remove Bootstrap listeners');
        
        // Ensure menu is hidden initially
        collapse.classList.remove('show');
        toggler.classList.add('collapsed');
        console.log('✅ Reset menu to closed state');
        
        // Animation duration should match CSS transition time (300ms)
        const ANIMATION_DURATION = 300;
        let isToggling = false;
        
        // Helper: Create debounced toggle with animation-aware delay
        const createDebouncedToggle = (callback, delay) => {
            let isExecuting = false;
            return function(e) {
                if (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                }
                
                // DEBOUNCE: Prevent rapid successive calls
                if (isExecuting) {
                    console.log('⏸️  Debounced - ignoring rapid click');
                    return;
                }
                
                isExecuting = true;
                callback.call(this, e);
                
                // Reset debounce after animation completes
                setTimeout(() => {
                    isExecuting = false;
                }, delay);
            };
        };
        
        // Create the toggle function
        const toggle = createDebouncedToggle(() => {
            console.log('%c🔄 Toggle function called', 'color: green');
            const isOpen = collapse.classList.contains('show');
            console.log('   Current state:', isOpen ? 'OPEN' : 'CLOSED');
            
            if (isOpen) {
                // CLOSE
                console.log('   Action: CLOSING menu');
                collapse.classList.remove('show');
                toggler.classList.add('collapsed');
                toggler.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
                console.log('%c✅ Menu CLOSED', 'color: green');
            } else {
                // OPEN
                console.log('   Action: OPENING menu');
                collapse.classList.add('show');
                toggler.classList.remove('collapsed');
                toggler.setAttribute('aria-expanded', 'true');
                document.body.style.overflow = 'hidden';
                console.log('%c✅ Menu OPENED', 'color: green');
            }
        }, ANIMATION_DURATION);
        
        // Step 4: Attach ONLY our click listener (no useCapture - use bubble phase)
        toggler.addEventListener('click', toggle, false);
        console.log('✅ Click listener attached');
        
        // Step 5: Block any further Bootstrap initialization
        // by preventing new Collapse instances
        const originalCollapse = bootstrap.Collapse;
        const preventInit = new Proxy(originalCollapse, {
            construct(target, args) {
                if (args[0] === collapse) {
                    console.log('🚫 Blocked Bootstrap from initializing collapse');
                    return {
                        show: () => {},
                        hide: () => {},
                        toggle: () => {},
                        dispose: () => {}
                    };
                }
                return new target(...args);
            }
        });
        bootstrap.Collapse = preventInit;
        console.log('✅ Prevented Bootstrap from re-initializing');
        
        // Setup custom mobile dropdown system
        this.setupMobileDropdowns(navbar);
        
        // Store for debugging
        window.debugNavbar = { toggle, toggler, collapse };
        console.log('💡 Use window.debugNavbar.toggle() to test manually');
        console.log('%c✅ Navigation setup complete!', 'color: green; font-weight: bold');
    }
    
    /**
     * Close navigation menu
     */
    closeNavMenu(collapse, toggler) {
        collapse.classList.remove('show');
        toggler.classList.add('collapsed');
        toggler.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    }
    
    /**
     * Open navigation menu
     */
    openNavMenu(collapse, toggler) {
        collapse.classList.add('show');
        toggler.classList.remove('collapsed');
        toggler.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * Setup mobile dropdown system - completely custom, no Bootstrap interference
     */
    setupMobileDropdowns(navbar) {
        // Only run on mobile
        if (window.innerWidth > 768) return;
        
        const dropdownToggles = navbar.querySelectorAll('.dropdown-toggle');
        
        dropdownToggles.forEach(toggle => {
            // Remove Bootstrap data attributes to prevent interference
            toggle.removeAttribute('data-bs-toggle');
            toggle.removeAttribute('data-bs-target');
            
            // Remove any existing Bootstrap dropdown instances
            try {
                const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                if (bsDropdown) bsDropdown.dispose();
            } catch (e) {
                // Bootstrap Dropdown not available or already removed
            }
            
            const parentItem = toggle.parentElement;
            const menu = parentItem.querySelector('.dropdown-menu');
            
            if (!menu) return;
            
            // Prevent default link behavior
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            }, false);
            
            // Custom debounced toggle handler with short debounce for dropdown
            let isTogglingDropdown = false;
            const handleDropdownClick = (e) => {
                if (isTogglingDropdown) return;
                isTogglingDropdown = true;
                // Shorter debounce for dropdowns (matches 0.16s CSS animation)
                setTimeout(() => { isTogglingDropdown = false; }, 160);
                
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                
                const isOpen = menu.classList.contains('show');
                
                // Close all other dropdowns at this level
                const navContainer = toggle.closest('.navbar-nav');
                const otherToggles = navContainer.querySelectorAll('.dropdown-toggle');
                otherToggles.forEach(otherToggle => {
                    if (otherToggle !== toggle) {
                        const otherMenu = otherToggle.parentElement.querySelector('.dropdown-menu');
                        if (otherMenu && otherMenu.classList.contains('show')) {
                            otherMenu.classList.remove('show');
                            otherToggle.classList.add('collapsed');
                            otherToggle.setAttribute('aria-expanded', 'false');
                        }
                    }
                });
                
                // Toggle current dropdown
                if (isOpen) {
                    menu.classList.remove('show');
                    toggle.classList.add('collapsed');
                    toggle.setAttribute('aria-expanded', 'false');
                } else {
                    menu.classList.add('show');
                    toggle.classList.remove('collapsed');
                    toggle.setAttribute('aria-expanded', 'true');
                }
            };
            
            toggle.addEventListener('click', handleDropdownClick, false);
        });
        
        // Close dropdowns when clicking menu items (links, not buttons)
        const dropdownItems = navbar.querySelectorAll('.dropdown-item');
        dropdownItems.forEach(item => {
            // Only auto-close on link clicks, not button/form submissions
            if (item.tagName === 'A') {
                item.addEventListener('click', (e) => {
                    const parentDropdown = item.closest('.dropdown-menu');
                    if (parentDropdown) {
                        parentDropdown.classList.remove('show');
                        const toggle = parentDropdown.previousElementSibling;
                        if (toggle && toggle.classList.contains('dropdown-toggle')) {
                            toggle.classList.add('collapsed');
                            toggle.setAttribute('aria-expanded', 'false');
                        }
                    }
                }, false);
            }
        });
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            // Check if click is outside all dropdowns
            const clickedDropdown = e.target.closest('.dropdown');
            if (!clickedDropdown) {
                dropdownToggles.forEach(toggle => {
                    const menu = toggle.parentElement.querySelector('.dropdown-menu');
                    if (menu && menu.classList.contains('show')) {
                        menu.classList.remove('show');
                        toggle.classList.add('collapsed');
                        toggle.setAttribute('aria-expanded', 'false');
                    }
                });
            }
        }, false);
        
        console.log('✅ Mobile dropdowns setup complete - smooth animation system active');
    }
    
    /**
     * Setup menu scroll behavior
     */
    setupMenuScroll(collapse, toggler) {
        let touchStartY = 0;
        let touchEndY = 0;
        
        collapse.addEventListener('touchstart', (e) => {
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });
        
        collapse.addEventListener('touchend', (e) => {
            touchEndY = e.changedTouches[0].screenY;
            
            // Swipe down to close menu
            if (touchStartY - touchEndY < -50) {
                this.closeNavMenu(collapse, toggler);
            }
        }, { passive: true });
    }
    
    /**
     * Optimize form interactions
     */
    optimizeForms() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            // Ensure form fields have proper mobile sizing
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                // Ensure minimum touch size
                const height = window.getComputedStyle(input).height;
                if (parseFloat(height) < 44) {
                    input.style.minHeight = '44px';
                }
                
                // Add better focus states
                input.addEventListener('focus', () => {
                    input.parentElement.classList.add('focused');
                });
                
                input.addEventListener('blur', () => {
                    input.parentElement.classList.remove('focused');
                });
            });
            
            // Enhance form submission feedback
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
                }
            });
        });
    }
    
    /**
     * Optimize modal display on mobile
     */
    optimizeModals() {
        // Observer for new modals being added
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.classList && node.classList.contains('modal')) {
                            this.enhanceModal(node);
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, { 
            childList: true, 
            subtree: true 
        });
        
        // Enhance existing modals
        document.querySelectorAll('.modal').forEach(modal => {
            this.enhanceModal(modal);
        });
    }
    
    /**
     * Enhance individual modal
     */
    enhanceModal(modal) {
        const body = modal.querySelector('.modal-body');
        if (!body) return;
        
        // Ensure scrolling works smoothly on iOS
        body.style.webkitOverflowScrolling = 'touch';
        
        // Prevent modal from being dismissed accidentally
        const backdrop = modal.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.style.opacity = '0.5';
        }
        
        // Handle keyboard on mobile
        const closeBtn = modal.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    closeBtn.click();
                }
            });
        }
    }
    
    /**
     * Enhance touch interactions
     */
    enhanceTouchInteractions() {
        // Add touch feedback to buttons and clickable elements
        const touchElements = document.querySelectorAll('button, [role="button"], .list-group-item, .card');
        
        touchElements.forEach(element => {
            element.addEventListener('touchstart', (e) => {
                element.style.opacity = '0.8';
            }, { passive: true });
            
            element.addEventListener('touchend', (e) => {
                element.style.opacity = '1';
            }, { passive: true });
            
            element.addEventListener('touchcancel', (e) => {
                element.style.opacity = '1';
            }, { passive: true });
        });
        
        // Swipe gesture support for navigation
        this.enableSwipeNavigation();
    }
    
    /**
     * Enable swipe-to-go-back on mobile
     */
    enableSwipeNavigation() {
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe(touchStartX, touchEndX);
        }, { passive: true });
    }
    
    /**
     * Handle swipe gestures
     */
    handleSwipe(startX, endX) {
        const threshold = 100;
        const diff = startX - endX;
        
        // Swipe right: go back
        if (diff < -threshold && startX < 50) {
            // User swiped right from left edge, go back
            if (window.history.length > 1) {
                window.history.back();
            }
        }
    }
    
    /**
     * Optimize scrolling performance
     */
    optimizeScrolling() {
        // Use passive event listeners for scroll performance
        let scrollTimer;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimer);
            document.body.classList.add('scrolling');
            
            scrollTimer = setTimeout(() => {
                document.body.classList.remove('scrolling');
            }, 150);
        }, { passive: true });
        
        // Optimize table scrolling
        const tables = document.querySelectorAll('.table-responsive');
        tables.forEach(table => {
            table.style.webkitOverflowScrolling = 'touch';
        });
    }
    
    /**
     * Handle orientation changes
     */
    handleOrientation() {
        const orientation = window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
        document.body.setAttribute('data-orientation', orientation);
        
        // Adjust spacing in landscape mode
        if (orientation === 'landscape') {
            document.body.style.setProperty('--landscape-mode', 'true');
        } else {
            document.body.style.removeProperty('--landscape-mode');
        }
    }
    
    /**
     * Handle viewport resize
     */
    handleResize() {
        this.viewportWidth = window.innerWidth;
        this.viewportHeight = window.innerHeight;
        
        // Re-detect device type
        const wasMobile = this.isMobile;
        this.isMobile = this.detectMobile();
        
        // If transitioned between mobile/desktop, reload optimizations
        if (wasMobile !== this.isMobile) {
            this.enhanceNavigation();
            this.optimizeForms();
        }
    }
    
    /**
     * Prevent common mobile issues
     */
    preventCommonMobileIssues() {
        // Prevent double-tap zoom on buttons
        document.addEventListener('touchstart', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                e.preventDefault();
                e.target.click();
            }
        }, { passive: false });
        
        // Prevent horizontal scroll
        let maxWidth = window.innerWidth;
        window.addEventListener('resize', () => {
            if (window.innerWidth > maxWidth) {
                document.body.style.overflowX = 'hidden';
            }
        }, { passive: true });
        
        // Fix iOS input zoom
        document.addEventListener('focusin', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                // Prevent zoom on iOS
                setTimeout(() => {
                    e.target.style.fontSize = '16px';
                }, 0);
            }
        });
        
        // Prevent accidental text selection on long press
        document.querySelectorAll('a, button, [role="button"]').forEach(element => {
            element.style.webkitUserSelect = 'none';
            element.style.userSelect = 'none';
        });
    }
    
    /**
     * Add loading state to buttons during submission
     */
    static showButtonLoading(button) {
        if (!button) return;
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
        return originalText;
    }
    
    /**
     * Remove loading state from buttons
     */
    static hideButtonLoading(button, originalText) {
        if (!button) return;
        button.disabled = false;
        button.innerHTML = originalText || 'Submit';
    }
    
    /**
     * Show mobile-friendly toast notification
     */
    static showToast(message, type = 'info', duration = 3000) {
        const toastHtml = `
            <div class="toast toast-${type} align-items-center border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = document.querySelector('.toast-container') || 
                               document.createElement('div');
        if (!toastContainer.classList.contains('toast-container')) {
            toastContainer.classList.add('toast-container', 'position-fixed', 'bottom-0', 'end-0', 'p-3');
            document.body.appendChild(toastContainer);
        }
        
        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        const toast = toastElement.firstChild;
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove element after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Initialize mobile optimization when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mobileOptimization = new MobileOptimization();
});

// Also initialize if script is loaded after DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.mobileOptimization = new MobileOptimization();
    });
} else {
    window.mobileOptimization = new MobileOptimization();
}
