/* ============================================
   MOBILE INTERACTION IMPROVEMENTS
   Fixes for mobile UX issues
   ============================================ */

(function() {
    'use strict';

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initMobileOptimizations();
    });

    /**
     * Initialize all mobile optimizations
     */
    function initMobileOptimizations() {
        fixNavbarMobile();
        fixDropdownsMobile();
        fixFormInputs();
        preventIOSZoom();
        optimizeModals();
        improveScrollPerformance();
        setupTouchFeedback();
    }

    /**
     * Fix navbar behavior on mobile
     */
    function fixNavbarMobile() {
        // Note: Navbar behavior is now handled by MobileNavbar class in navbar-footer-mobile.js
        // This function is kept for backwards compatibility but does not interfere with custom navbar handling
        
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');

        if (!navbarToggler || !navbarCollapse) return;

        // All navbar interactions are now delegated to the MobileNavbar class
        // Remove any Bootstrap collapse manipulation to avoid conflicts
        // The MobileNavbar class handles:
        // - Toggle button clicks
        // - Dropdown toggles
        // - Outside clicks to close menu
        // - Escape key handling
    }

    /**
     * Fix dropdowns for mobile touch devices
     */
    function fixDropdownsMobile() {
        const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

        dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                // On mobile, prevent default link behavior for dropdowns
                if (isTouchDevice()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        });

        // Close dropdowns when tapping outside
        document.addEventListener('click', function(e) {
            if (isTouchDevice()) {
                const allDropdowns = document.querySelectorAll('.dropdown-menu.show');
                allDropdowns.forEach(dropdown => {
                    if (!dropdown.closest('.dropdown').contains(e.target)) {
                        dropdown.classList.remove('show');
                    }
                });
            }
        });
    }

    /**
     * Fix form inputs for better mobile experience
     */
    function fixFormInputs() {
        // Increase input sizes for touch
        const inputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="number"], textarea');
        
        inputs.forEach(input => {
            if (isTouchDevice()) {
                input.style.fontSize = '16px'; // Prevent zoom on iOS
                input.style.padding = '0.75rem';
                input.style.minHeight = '44px';
            }
        });

        // Add focus/blur feedback
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.classList.add('input-focused');
            });

            input.addEventListener('blur', function() {
                this.parentElement.classList.remove('input-focused');
            });
        });
    }

    /**
     * Prevent iOS zoom on input focus
     */
    function preventIOSZoom() {
        if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
            const inputs = document.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('focus', function() {
                    this.style.fontSize = '16px';
                    // Scroll input into view on iOS
                    setTimeout(() => {
                        this.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 100);
                });
            });
        }
    }

    /**
     * Optimize modals for mobile
     */
    function optimizeModals() {
        const modals = document.querySelectorAll('.modal');

        modals.forEach(modal => {
            // Close modal on background click on mobile
            modal.addEventListener('click', function(e) {
                if (e.target === this && isTouchDevice()) {
                    const bsModal = bootstrap.Modal.getInstance(this);
                    if (bsModal) bsModal.hide();
                }
            });

            // Prevent body scroll when modal is open
            const modalInstance = new bootstrap.Modal(modal, { backdrop: true });
            modal.addEventListener('shown.bs.modal', function() {
                document.body.style.overflow = 'hidden';
            });

            modal.addEventListener('hidden.bs.modal', function() {
                document.body.style.overflow = 'auto';
            });
        });
    }

    /**
     * Improve scroll performance on mobile
     */
    function improveScrollPerformance() {
        // Use passive event listeners for better scroll performance
        const scrollElements = document.querySelectorAll('.table-responsive, .modal-body');
        
        scrollElements.forEach(el => {
            el.addEventListener('scroll', function() {
                // Throttle scroll events
                if (!this.scrolling) {
                    this.scrolling = true;
                    setTimeout(() => {
                        this.scrolling = false;
                    }, 100);
                }
            }, { passive: true });
        });

        // Add momentum scrolling for iOS
        scrollElements.forEach(el => {
            el.style.webkitOverflowScrolling = 'touch';
        });
    }

    /**
     * Setup touch feedback for interactive elements
     */
    function setupTouchFeedback() {
        if (!isTouchDevice()) return;

        const interactiveElements = document.querySelectorAll('button, a.btn, [role="button"], .nav-link, .list-group-item');

        interactiveElements.forEach(el => {
            el.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            }, { passive: true });

            el.addEventListener('touchend', function() {
                this.classList.remove('touch-active');
            }, { passive: true });
        });
    }

    /**
     * Utility function to detect touch devices
     */
    function isTouchDevice() {
        return (
            (typeof window !== 'undefined' &&
                ('ontouchstart' in window ||
                    (navigator.maxTouchPoints !== undefined && navigator.maxTouchPoints > 0) ||
                    (navigator.msMaxTouchPoints !== undefined && navigator.msMaxTouchPoints > 0)))
        );
    }

    /**
     * Handle viewport resize
     */
    window.addEventListener('resize', function() {
        // Re-initialize on resize for orientation changes
        if (window.innerHeight < 500 && window.innerWidth > window.innerHeight) {
            // Landscape mode - reduce padding
            document.body.classList.add('landscape-mode');
        } else {
            document.body.classList.remove('landscape-mode');
        }
    });

    /**
     * Safe area support for devices with notches/Dynamic Island
     */
    function applySafeAreaInsets() {
        const supportsEnv = CSS.supports('padding', 'max(0px)');
        if (!supportsEnv) return;

        const htmlElement = document.documentElement;
        const style = getComputedStyle(htmlElement);
        
        // CSS will handle this through @supports query
        // This is just a fallback check
    }

    applySafeAreaInsets();

    /**
     * Improve table scrolling on mobile
     */
    function initTableResponsive() {
        const tables = document.querySelectorAll('table');
        
        tables.forEach(table => {
            if (!table.classList.contains('table-responsive') && table.parentElement.classList.contains('table-responsive')) {
                // Already wrapped
                return;
            }

            // Add scroll hint for tables
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        });
    }

    // Initialize tables after DOM ready
    if (document.readyState !== 'loading') {
        initTableResponsive();
    } else {
        document.addEventListener('DOMContentLoaded', initTableResponsive);
    }

    /**
     * Add visual feedback for form validation on mobile
     */
    function enhanceFormValidation() {
        const forms = document.querySelectorAll('form');

        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const isValid = form.checkValidity() === false;
                if (isValid) {
                    e.preventDefault();
                    e.stopPropagation();

                    // Scroll to first invalid input
                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        firstInvalid.focus();
                    }
                }
                form.classList.add('was-validated');
            }, false);
        });
    }

    enhanceFormValidation();

    /**
     * Fix button spacing in button groups on mobile
     */
    function fixButtonGroups() {
        const buttonGroups = document.querySelectorAll('.btn-group, .button-group');

        buttonGroups.forEach(group => {
            if (isTouchDevice()) {
                group.style.display = 'flex';
                group.style.flexDirection = 'column';
                group.style.gap = '0.5rem';

                const buttons = group.querySelectorAll('.btn');
                buttons.forEach(btn => {
                    btn.style.width = '100%';
                });
            }
        });
    }

    fixButtonGroups();

})();

// Add CSS for touch-active state
const style = document.createElement('style');
style.textContent = `
    @media (hover: none) and (pointer: coarse) {
        .touch-active {
            background-color: var(--bg-tertiary, rgba(99, 102, 241, 0.1)) !important;
            transform: scale(0.98) !important;
            transition: all 0.1s ease !important;
        }

        input:focus {
            font-size: 16px !important;
        }

        .input-focused {
            outline: 2px solid var(--primary-color) !important;
            outline-offset: -1px !important;
        }
    }

    .landscape-mode .navbar {
        padding: 0.25rem 0 !important;
    }

    .landscape-mode main {
        margin-top: 0.25rem !important;
    }
`;
document.head.appendChild(style);
