/**
 * Mobile Performance Optimization - Task 5.1.4
 * Handles lazy loading, performance metrics, and optimization
 */

(function() {
    'use strict';

    // Performance logging utility
    const perfLog = {
        enabled: false, // Set to true for debugging
        log: function(message, data) {
            if (this.enabled) {
                console.log(`[PERF] ${message}`, data || '');
            }
        },
        error: function(message, error) {
            if (this.enabled) {
                console.error(`[PERF ERROR] ${message}`, error);
            }
        }
    };

    /**
     * Lazy Load Images - Intersection Observer API
     * Loads images only when they come into viewport
     */
    function initLazyLoading() {
        perfLog.log('Initializing lazy loading...');

        if (!('IntersectionObserver' in window)) {
            perfLog.log('IntersectionObserver not supported, loading all images');
            // Fallback: load all images immediately
            document.querySelectorAll('img[data-src]').forEach(img => {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            });
            return;
        }

        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        perfLog.log('Lazy loaded image:', img.src);
                    }
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px' // Start loading 50px before image enters viewport
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });

        perfLog.log('Lazy loading initialized');
    }

    /**
     * Defer Non-Critical JavaScript
     * Loads non-essential scripts after page is interactive
     */
    function deferNonCriticalScripts() {
        perfLog.log('Deferring non-critical scripts...');

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                loadDeferredScripts();
            });
        } else {
            loadDeferredScripts();
        }
    }

    function loadDeferredScripts() {
        const deferredScripts = document.querySelectorAll('script[data-defer]');
        deferredScripts.forEach(script => {
            const newScript = document.createElement('script');
            if (script.src) {
                newScript.src = script.src;
            } else {
                newScript.textContent = script.textContent;
            }
            newScript.async = true;
            document.body.appendChild(newScript);
            perfLog.log('Loaded deferred script:', script.src || 'inline');
        });
    }

    /**
     * Preconnect to External Domains
     * Speeds up connections to frequently used APIs/CDNs
     */
    function addPreconnects() {
        const domains = [
            'https://api.example.com', // Your API domain
            'https://cdn.example.com',
            'https://fonts.googleapis.com'
        ];

        domains.forEach(domain => {
            const link = document.createElement('link');
            link.rel = 'preconnect';
            link.href = domain;
            document.head.appendChild(link);
        });

        perfLog.log('Preconnects added');
    }

    /**
     * Monitor Core Web Vitals
     * Tracks Largest Contentful Paint (LCP), Cumulative Layout Shift (CLS), etc.
     */
    function monitorCoreWebVitals() {
        if (!('PerformanceObserver' in window)) {
            perfLog.log('PerformanceObserver not supported');
            return;
        }

        // Largest Contentful Paint
        try {
            const paintObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                const lastEntry = entries[entries.length - 1];
                perfLog.log('LCP:', lastEntry.renderTime || lastEntry.loadTime);
            });
            paintObserver.observe({ entryTypes: ['largest-contentful-paint'] });
        } catch (e) {
            perfLog.error('LCP monitoring failed', e);
        }

        // Cumulative Layout Shift
        try {
            let clsValue = 0;
            const clsObserver = new PerformanceObserver((list) => {
                list.getEntries().forEach((entry) => {
                    if (!entry.hadRecentInput) {
                        clsValue += entry.value;
                        perfLog.log('CLS:', clsValue);
                    }
                });
            });
            clsObserver.observe({ entryTypes: ['layout-shift'] });
        } catch (e) {
            perfLog.error('CLS monitoring failed', e);
        }
    }

    /**
     * Optimize Bundle Size
     * Remove unused CSS classes and minify inline styles
     */
    function optimizeBundleSize() {
        perfLog.log('Optimizing bundle size...');

        // Remove debug classes in production
        if (window.DEBUG_MODE !== true) {
            document.body.classList.remove('debug-touch-targets');
        }

        // Defer non-critical CSS loading
        const links = document.querySelectorAll('link[rel="stylesheet"][data-defer]');
        links.forEach(link => {
            link.onload = function() {
                link.media = 'all';
            };
            link.media = 'print'; // Load in print media first (lower priority)
        });

        perfLog.log('Bundle size optimized');
    }

    /**
     * Enable Service Worker for Offline Support
     */
    function registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            perfLog.log('Service Worker not supported');
            return;
        }

        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then(registration => {
                perfLog.log('Service Worker registered:', registration.scope);
            })
            .catch(error => {
                perfLog.error('Service Worker registration failed', error);
            });
    }

    /**
     * Network Information API - Adapt to Connection Speed
     */
    function adaptToNetworkSpeed() {
        if (!('connection' in navigator)) {
            perfLog.log('Connection API not supported');
            return;
        }

        const connection = navigator.connection;
        const effectiveType = connection.effectiveType;

        perfLog.log('Connection type:', effectiveType);

        // High-quality images for fast connections
        const imageQuality = {
            '4g': 'high',
            '3g': 'medium',
            '2g': 'low'
        };

        const quality = imageQuality[effectiveType] || 'medium';
        document.documentElement.setAttribute('data-image-quality', quality);

        // Listen for connection changes
        connection.addEventListener('change', () => {
            const newType = navigator.connection.effectiveType;
            const newQuality = imageQuality[newType] || 'medium';
            document.documentElement.setAttribute('data-image-quality', newQuality);
            perfLog.log('Connection changed to:', newType);
        });
    }

    /**
     * Reduce Motion for Accessibility
     */
    function respectReducedMotion() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.documentElement.style.setProperty('--animation-duration', '0.01ms');
            perfLog.log('Reduced motion enabled');
        }
    }

    /**
     * Initialize all performance optimizations
     */
    function init() {
        perfLog.log('Initializing mobile performance optimizations...');

        initLazyLoading();
        deferNonCriticalScripts();
        optimizeBundleSize();
        monitorCoreWebVitals();
        respectReducedMotion();
        adaptToNetworkSpeed();

        // Register service worker after page loads
        window.addEventListener('load', registerServiceWorker);

        perfLog.log('Mobile performance optimizations complete');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for debugging
    window.mobilePerformance = {
        perfLog: perfLog,
        enableDebug: () => { perfLog.enabled = true; }
    };
})();
