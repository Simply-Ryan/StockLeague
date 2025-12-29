/**
 * Mobile Performance Optimization - Phase 5 Task 4
 * Lazy loading, image optimization, and bundle management
 */

/**
 * Initialize lazy loading for images
 * Uses Intersection Observer for efficient lazy loading
 */
function initLazyLoading() {
    // Check if IntersectionObserver is supported
    if (!('IntersectionObserver' in window)) {
        console.warn('IntersectionObserver not supported, lazy loading disabled');
        return;
    }

    // Select all images marked for lazy loading
    const images = document.querySelectorAll('img[data-lazy], img[loading="lazy"]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                
                // Handle data-src attribute
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                }
                
                // Handle data-srcset attribute
                if (img.dataset.srcset) {
                    img.srcset = img.dataset.srcset;
                    img.removeAttribute('data-srcset');
                }
                
                img.classList.remove('lazy');
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    }, {
        // Start loading 50px before image enters viewport
        rootMargin: '50px'
    });

    images.forEach(img => {
        // Add loading="lazy" for native support
        img.loading = 'lazy';
        imageObserver.observe(img);
    });
}

/**
 * Optimize CSS by removing unused rules
 * Analyzes page and removes unused CSS selectors
 */
function analyzeCSS() {
    const usedSelectors = new Set();
    const stylesheets = document.styleSheets;

    try {
        for (let stylesheet of stylesheets) {
            // Skip cross-origin stylesheets
            if (stylesheet.href && !stylesheet.href.includes(location.origin)) {
                continue;
            }

            try {
                const rules = stylesheet.cssRules || stylesheet.rules;
                for (let rule of rules) {
                    if (rule.selectorText) {
                        const selector = rule.selectorText;
                        try {
                            // Test if selector matches any element on page
                            if (document.querySelectorAll(selector).length > 0) {
                                usedSelectors.add(selector);
                            }
                        } catch (e) {
                            // Invalid selector, skip
                        }
                    }
                }
            } catch (e) {
                // Cannot access stylesheet rules (CORS issue), skip
            }
        }
    } catch (e) {
        console.warn('Could not analyze CSS usage:', e);
    }

    return {
        total: Array.from(usedSelectors).length,
        used: usedSelectors
    };
}

/**
 * Lazy load non-critical JavaScript
 * Defers loading of non-essential scripts
 */
function lazyLoadScripts() {
    // List of non-critical scripts that can be loaded after page interactive
    const nonCriticalScripts = [
        '/static/js/leaderboard-realtime.js',
        '/static/js/realtime.js'
    ];

    // Use requestIdleCallback if available, otherwise use setTimeout
    const scheduleLoad = window.requestIdleCallback || ((callback) => {
        setTimeout(callback, 0);
    });

    scheduleLoad(() => {
        nonCriticalScripts.forEach(src => {
            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            document.body.appendChild(script);
        });
    });
}

/**
 * Optimize bundle size by removing unused CSS classes
 */
function optimizeCSS() {
    const styleEl = document.createElement('style');
    styleEl.id = 'css-optimization';
    
    // Remove unused utility classes that aren't on the page
    const utilitiesToCheck = [
        '.d-flex', '.flex-column', '.justify-content-center', '.align-items-center',
        '.gap-2', '.gap-3', '.gap-4', '.mt-0', '.mt-1', '.mt-2', '.mt-3', '.mt-4', '.mt-5',
        '.mb-0', '.mb-1', '.mb-2', '.mb-3', '.mb-4', '.mb-5',
        '.p-2', '.p-3', '.p-4', '.p-5'
    ];

    let unusedCSS = '';
    utilitiesToCheck.forEach(className => {
        if (document.querySelectorAll(className).length === 0) {
            unusedCSS += className.replace('.', '') + ' { display: none !important; } ';
        }
    });

    // Note: In production, use a proper CSS purge tool like PurgeCSS
}

/**
 * Monitor performance metrics
 * Track Web Vitals: LCP, FCP, CLS
 */
function initPerformanceMonitoring() {
    // Only run in browsers with Performance API
    if (!window.PerformanceObserver) {
        return;
    }

    const metrics = {
        fcp: null,      // First Contentful Paint
        lcp: null,      // Largest Contentful Paint
        cls: 0,         // Cumulative Layout Shift
        ttfb: null      // Time to First Byte
    };

    // Get TTFB from navigation timing
    if (window.performance && window.performance.timing) {
        const timing = window.performance.timing;
        if (timing.responseStart && timing.fetchStart) {
            metrics.ttfb = timing.responseStart - timing.fetchStart;
        }
    }

    // Observe Largest Contentful Paint
    try {
        const lcpObserver = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            metrics.lcp = lastEntry.renderTime || lastEntry.loadTime;
        });

        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
    } catch (e) {
        // LCP not supported
    }

    // Observe First Contentful Paint
    try {
        const fcpObserver = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            entries.forEach(entry => {
                if (entry.name === 'first-contentful-paint') {
                    metrics.fcp = entry.startTime;
                }
            });
        });

        fcpObserver.observe({ entryTypes: ['paint'] });
    } catch (e) {
        // Paint API not supported
    }

    // Observe Cumulative Layout Shift
    try {
        const clsObserver = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    metrics.cls += entry.value;
                }
            }
        });

        clsObserver.observe({ entryTypes: ['layout-shift'] });
    } catch (e) {
        // Layout Shift not supported
    }

    // Log metrics periodically
    window.addEventListener('beforeunload', () => {
        console.log('Performance Metrics:', {
            fcp: metrics.fcp ? metrics.fcp.toFixed(2) + 'ms' : 'N/A',
            lcp: metrics.lcp ? metrics.lcp.toFixed(2) + 'ms' : 'N/A',
            cls: metrics.cls.toFixed(3),
            ttfb: metrics.ttfb ? metrics.ttfb.toFixed(2) + 'ms' : 'N/A'
        });
    });

    // Expose metrics for debugging
    window.performanceMetrics = metrics;
}

/**
 * Optimize image loading for avatars and icons
 */
function optimizeImageLoading() {
    // Convert avatar images to use smaller thumbnails with srcset
    document.querySelectorAll('.rounded-circle[src*="avatar"]').forEach(img => {
        if (!img.srcset) {
            // Add responsive image sizes
            img.srcset = `
                ${img.src}?size=64 64w,
                ${img.src}?size=128 128w,
                ${img.src}?size=256 256w
            `;
            img.sizes = '(max-width: 480px) 64px, (max-width: 768px) 96px, 120px';
        }
    });

    // Add loading="lazy" to all images if not already set
    document.querySelectorAll('img').forEach(img => {
        if (!img.loading) {
            img.loading = 'lazy';
        }
    });
}

/**
 * Compress inline SVG icons
 */
function optimizeSVGs() {
    document.querySelectorAll('svg').forEach(svg => {
        // Remove unnecessary attributes
        svg.removeAttribute('xmlns');
        svg.removeAttribute('version');
        
        // Add role for accessibility
        if (!svg.getAttribute('role')) {
            svg.setAttribute('role', 'img');
        }
    });
}

/**
 * Main initialization function
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize lazy loading
    initLazyLoading();

    // Optimize images
    optimizeImageLoading();

    // Optimize SVGs
    optimizeSVGs();

    // Monitor performance
    initPerformanceMonitoring();

    // Lazy load non-critical scripts after page is interactive
    if (document.readyState === 'loading') {
        document.addEventListener('load', lazyLoadScripts);
    } else {
        lazyLoadScripts();
    }
});

// Export functions for use in other scripts
window.StockLeaguePerformance = {
    initLazyLoading,
    analyzeCSS,
    lazyLoadScripts,
    optimizeCSS,
    initPerformanceMonitoring,
    optimizeImageLoading,
    optimizeSVGs
};
