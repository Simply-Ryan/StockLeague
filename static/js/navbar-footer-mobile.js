/**
 * Enhanced Navbar & Dropdown Mobile Interactions
 * Provides smooth, mobile-friendly navigation behavior
 */

class MobileNavbar {
    constructor() {
        this.navbar = document.getElementById('mainNavbar');
        this.toggler = document.querySelector('.navbar-toggler');
        this.collapse = document.querySelector('.navbar-collapse');
        this.togglerIcon = this.toggler ? this.toggler.querySelector('.navbar-toggler-icon') : null;
        this.navLinks = document.querySelectorAll('.nav-link');
        this.dropdownToggles = document.querySelectorAll('.nav-link.dropdown-toggle');
        this.isOpen = false;
        
        // Validate elements exist
        if (!this.navbar || !this.toggler || !this.collapse) {
            console.warn('MobileNavbar: Missing required navbar elements');
            console.warn('  navbar:', this.navbar);
            console.warn('  toggler:', this.toggler);
            console.warn('  collapse:', this.collapse);
            return;
        }
        
        console.log('MobileNavbar initialized successfully');
        this.init();
    }

    init() {
        // Initialize event listeners
        this.setupTogglerEvents();
        this.setupDropdownEvents();
        this.setupNavLinkEvents();
        this.setupDocumentClickEvents();
        this.setupWindowResizeEvents();
        this.setupOrientationChangeEvents();
        
        // Set initial icon to hamburger
        this.updateToggerIcon();
    }

    /**
     * Setup hamburger menu toggle events
     */
    setupTogglerEvents() {
        if (!this.toggler) {
            console.error('Toggler not found');
            return;
        }

        console.log('Setting up toggler events');
        
        // Attach click handler DIRECTLY without cloning
        this.toggler.addEventListener('click', (e) => {
            console.log('Toggler clicked');
            e.preventDefault();
            e.stopPropagation();
            this.toggleNavbar();
        }, false);

        // Touch events
        this.toggler.addEventListener('touchstart', (e) => {
            e.preventDefault();
        }, false);

        this.toggler.addEventListener('touchend', (e) => {
            e.preventDefault();
        }, false);
    }

    /**
     * Toggle navbar open/closed state
     */
    toggleNavbar() {
        this.isOpen = !this.isOpen;
        console.log('Navbar toggle state:', this.isOpen);

        if (this.isOpen) {
            console.log('OPENING NAVBAR - Adding show class');
            this.collapse.classList.add('show');
            this.navbar.setAttribute('aria-expanded', 'true');
            document.body.style.overflow = 'hidden';
            this.updateToggerIcon(); // Change icon to X
            this.collapse.scrollTop = 0;
        } else {
            console.log('CLOSING NAVBAR - Removing show class');
            this.collapse.classList.remove('show');
            this.navbar.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
            this.updateToggerIcon(); // Change icon to hamburger
            this.closeAllDropdowns();
        }
    }
    
    /**
     * Update toggler icon - hamburger or X
     */
    updateToggerIcon() {
        if (!this.togglerIcon) return;
        
        if (this.isOpen) {
            // Show X icon
            this.togglerIcon.style.backgroundImage = 'url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 30 30\'%3e%3cpath stroke=\'rgba%28099, 102, 241, 1%29\' stroke-linecap=\'round\' stroke-miterlimit=\'10\' stroke-width=\'2.5\' d=\'M7 7l16 16M23 7L7 23\'/%3e%3c/svg%3e")';
        } else {
            // Show hamburger icon
            this.togglerIcon.style.backgroundImage = 'url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 30 30\'%3e%3cpath stroke=\'rgba%28099, 102, 241, 1%29\' stroke-linecap=\'round\' stroke-miterlimit=\'10\' stroke-width=\'2.5\' d=\'M4 7h22M4 15h22M4 23h22\'/%3e%3c/svg%3e")';
        }
    }

    /**
     * Setup dropdown menu events
     */
    setupDropdownEvents() {
        this.dropdownToggles.forEach((toggle) => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleDropdownClick(toggle);
            });

            // Keyboard navigation
            toggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.handleDropdownClick(toggle);
                }
            });
        });
    }

    /**
     * Handle dropdown toggle click
     */
    handleDropdownClick(toggle) {
        const menu = toggle.nextElementSibling;
        if (!menu || !menu.classList.contains('dropdown-menu')) return;

        const isOpen = menu.classList.contains('show');

        // Close other dropdowns
        this.dropdownToggles.forEach((t) => {
            if (t !== toggle) {
                const m = t.nextElementSibling;
                if (m && m.classList.contains('show')) {
                    m.classList.remove('show');
                    t.setAttribute('aria-expanded', 'false');
                }
            }
        });

        // Toggle current dropdown
        if (isOpen) {
            menu.classList.remove('show');
            toggle.setAttribute('aria-expanded', 'false');
        } else {
            menu.classList.add('show');
            toggle.setAttribute('aria-expanded', 'true');
            
            // Scroll into view if needed
            setTimeout(() => {
                menu.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }
    }

    /**
     * Setup navigation link events
     */
    setupNavLinkEvents() {
        this.navLinks.forEach((link) => {
            // Close navbar when a non-dropdown link is clicked
            if (!link.classList.contains('dropdown-toggle')) {
                link.addEventListener('click', () => {
                    if (this.isOpen) {
                        this.toggleNavbar();
                    }
                });
            }

            // Close on touch for better mobile UX
            link.addEventListener('touchend', function (e) {
                // Don't close if it's a dropdown toggle
                if (!this.classList.contains('dropdown-toggle')) {
                    // Link will close navbar naturally
                }
            });
        });

        // Dropdown items should close navbar
        const dropdownItems = document.querySelectorAll('.dropdown-item');
        dropdownItems.forEach((item) => {
            item.addEventListener('click', () => {
                if (this.isOpen) {
                    this.toggleNavbar();
                }
            });

            // Touch feedback
            item.addEventListener('touchstart', function () {
                this.style.opacity = '0.8';
            });

            item.addEventListener('touchend', function () {
                this.style.opacity = '1';
            });
        });
    }

    /**
     * Setup document click to close navbar
     */
    setupDocumentClickEvents() {
        document.addEventListener('click', (e) => {
            // Don't close if clicking navbar
            if (!this.navbar.contains(e.target)) {
                if (this.isOpen) {
                    this.toggleNavbar();
                }
                this.closeAllDropdowns();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.isOpen) {
                    this.toggleNavbar();
                }
                this.closeAllDropdowns();
            }
        });
    }

    /**
     * Close all open dropdowns
     */
    closeAllDropdowns() {
        this.dropdownToggles.forEach((toggle) => {
            const menu = toggle.nextElementSibling;
            if (menu && menu.classList.contains('show')) {
                menu.classList.remove('show');
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /**
     * Setup window resize events
     */
    setupWindowResizeEvents() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                // On mobile-to-desktop transition, close navbar
                if (window.innerWidth >= 768 && this.isOpen) {
                    this.toggleNavbar();
                }
            }, 250);
        });
    }

    /**
     * Setup orientation change events
     */
    setupOrientationChangeEvents() {
        window.addEventListener('orientationchange', () => {
            // Prevent navbar from staying open after rotation
            setTimeout(() => {
                if (this.isOpen && window.innerWidth >= 768) {
                    this.toggleNavbar();
                }
            }, 500);
        });
    }
}

/**
 * Enhanced Footer Interactions
 */
class MobileFooter {
    constructor() {
        this.footer = document.querySelector('.footer');
        this.links = document.querySelectorAll('.footer a');
        
        this.init();
    }

    init() {
        this.setupLinkEvents();
        this.setupAccessibility();
    }

    /**
     * Setup footer link interactions
     */
    setupLinkEvents() {
        this.links.forEach((link) => {
            // Touch feedback
            link.addEventListener('touchstart', function () {
                this.style.opacity = '0.7';
            });

            link.addEventListener('touchend', function () {
                this.style.opacity = '1';
            });

            // Keyboard navigation
            link.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    link.click();
                }
            });
        });
    }

    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        this.links.forEach((link) => {
            // Ensure links are keyboard focusable
            if (!link.hasAttribute('tabindex')) {
                link.setAttribute('tabindex', '0');
            }
        });
    }
}

/**
 * Initialize mobile navbar and footer
 */
function initializeNavbarFooter() {
    // Initialize navbar
    const navbar = new MobileNavbar();
    
    // Initialize footer
    const footer = new MobileFooter();
    
    return { navbar, footer };
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM Ready - Initializing navbar and footer');
        initializeNavbarFooter();
    });
} else {
    console.log('DOM Already Ready - Initializing navbar and footer');
    initializeNavbarFooter();
}

/**
 * Export for testing (if using modules)
 */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MobileNavbar, MobileFooter, initializeNavbarFooter };
}
