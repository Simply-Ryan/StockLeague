/**
 * Push Notifications Manager - Task 5.2.4
 * Handles Web Push API, notification permissions, and delivery
 * 
 * Features:
 * - Request notification permissions
 * - Subscribe to push notifications
 * - Handle incoming notifications
 * - Unsubscribe functionality
 * - Store subscription on backend
 */

(function() {
    'use strict';

    // Configuration
    const config = {
        enabled: true,
        debug: false,
        vapidPublicKey: null, // Set from backend
        maxNotifications: 5,
        notificationTimeout: 5000 // Auto-close after 5 seconds
    };

    // State
    let state = {
        supported: 'serviceWorker' in navigator && 'PushManager' in window,
        registration: null,
        subscription: null,
        permissionGranted: false
    };

    // Utility functions
    const util = {
        log: (msg, data) => {
            if (config.debug) {
                console.log(`[PUSH] ${msg}`, data || '');
            }
        },
        error: (msg, err) => {
            console.error(`[PUSH ERROR] ${msg}`, err);
        },
        sendToServer: async (endpoint, data) => {
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                return await response.json();
            } catch (error) {
                util.error('Server request failed', error);
                throw error;
            }
        }
    };

    /**
     * Initialize Push Notifications
     */
    async function init() {
        if (!state.supported) {
            util.log('Push notifications not supported');
            return false;
        }

        try {
            // Get service worker registration
            const registration = await navigator.serviceWorker.ready;
            state.registration = registration;
            util.log('Service Worker ready for push');

            // Get existing subscription
            const subscription = await registration.pushManager.getSubscription();
            if (subscription) {
                state.subscription = subscription;
                state.permissionGranted = Notification.permission === 'granted';
                util.log('Existing subscription found');
            }

            // Listen for service worker messages
            navigator.serviceWorker.addEventListener('message', handleServiceWorkerMessage);

            // Setup permission UI
            setupPermissionUI();

            // Auto-check for permission changes
            setInterval(checkPermissionStatus, 5000);

            util.log('Push notifications initialized');
            return true;
        } catch (error) {
            util.error('Initialization failed', error);
            return false;
        }
    }

    /**
     * Request Notification Permission
     */
    async function requestPermission() {
        if (!state.supported) {
            util.log('Notifications not supported');
            return false;
        }

        try {
            // Request permission
            const permission = await Notification.requestPermission();
            util.log('Permission result:', permission);

            if (permission === 'granted') {
                state.permissionGranted = true;
                await subscribe();
                return true;
            } else if (permission === 'denied') {
                util.log('User denied notification permission');
                return false;
            } else if (permission === 'default') {
                util.log('Permission dismissed');
                return false;
            }
        } catch (error) {
            util.error('Permission request failed', error);
            return false;
        }
    }

    /**
     * Subscribe to Push Notifications
     */
    async function subscribe() {
        if (!state.registration || !state.permissionGranted) {
            util.log('Cannot subscribe: registration or permission missing');
            return null;
        }

        try {
            // Get VAPID key from backend if not already set
            if (!config.vapidPublicKey) {
                const response = await fetch('/api/push/vapid-key');
                const data = await response.json();
                config.vapidPublicKey = data.vapidPublicKey;
            }

            const subscription = await state.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(config.vapidPublicKey)
            });

            state.subscription = subscription;
            util.log('Subscribed to push:', subscription);

            // Send subscription to backend
            await util.sendToServer('/api/push/subscribe', {
                subscription: subscription.toJSON(),
                timestamp: new Date().toISOString()
            });

            return subscription;
        } catch (error) {
            util.error('Subscription failed', error);
            return null;
        }
    }

    /**
     * Unsubscribe from Push Notifications
     */
    async function unsubscribe() {
        if (!state.subscription) {
            util.log('No subscription to remove');
            return true;
        }

        try {
            await state.subscription.unsubscribe();
            state.subscription = null;
            state.permissionGranted = false;
            util.log('Unsubscribed from push');

            // Notify backend
            await util.sendToServer('/api/push/unsubscribe', {
                timestamp: new Date().toISOString()
            }).catch(() => {}); // Ignore errors

            return true;
        } catch (error) {
            util.error('Unsubscribe failed', error);
            return false;
        }
    }

    /**
     * Handle incoming notifications from service worker
     */
    function handleServiceWorkerMessage(event) {
        const { type, data } = event.data;

        if (type === 'NOTIFICATION_CLICK') {
            util.log('Notification clicked:', data);
            // Navigate to relevant page
            if (data.url) {
                window.location.href = data.url;
            }
        } else if (type === 'NOTIFICATION_CLOSE') {
            util.log('Notification closed:', data);
        }
    }

    /**
     * Show test notification
     */
    async function showTestNotification() {
        if (!state.registration) {
            util.log('Service Worker not ready');
            return;
        }

        try {
            await state.registration.showNotification('StockLeague Test', {
                body: 'Push notifications are working!',
                icon: '/static/icons/icon-192x192.png',
                badge: '/static/icons/icon-96x96.png',
                tag: 'test-notification',
                requireInteraction: false,
                actions: [
                    {
                        action: 'open',
                        title: 'Open App',
                        icon: '/static/icons/icon-96x96.png'
                    },
                    {
                        action: 'close',
                        title: 'Close'
                    }
                ]
            });

            util.log('Test notification shown');
        } catch (error) {
            util.error('Failed to show notification', error);
        }
    }

    /**
     * Check Permission Status
     */
    function checkPermissionStatus() {
        if (!state.supported) return;

        const currentPermission = Notification.permission;
        if (currentPermission !== 'granted' && state.permissionGranted) {
            // User revoked permission
            state.permissionGranted = false;
            state.subscription = null;
            updatePermissionUI();
        }
    }

    /**
     * Setup Permission UI
     */
    function setupPermissionUI() {
        const permissionBtn = document.getElementById('enableNotificationsBtn');
        if (permissionBtn) {
            permissionBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const result = await requestPermission();
                if (result) {
                    permissionBtn.textContent = '✓ Notifications Enabled';
                    permissionBtn.disabled = true;
                }
            });

            updatePermissionUI();
        }
    }

    /**
     * Update Permission UI
     */
    function updatePermissionUI() {
        const permissionBtn = document.getElementById('enableNotificationsBtn');
        if (!permissionBtn) return;

        if (state.permissionGranted && state.subscription) {
            permissionBtn.textContent = '✓ Notifications Enabled';
            permissionBtn.disabled = true;
            permissionBtn.className = 'btn btn-success';
        } else if (Notification.permission === 'denied') {
            permissionBtn.textContent = '✗ Notifications Blocked';
            permissionBtn.disabled = true;
            permissionBtn.className = 'btn btn-danger';
        } else {
            permissionBtn.textContent = '🔔 Enable Notifications';
            permissionBtn.disabled = false;
            permissionBtn.className = 'btn btn-primary';
        }
    }

    /**
     * Convert VAPID key from base64 to Uint8Array
     */
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }

    /**
     * Notify User of Trade
     */
    async function notifyTrade(data) {
        if (!state.registration || !state.permissionGranted) {
            return;
        }

        const {
            action,
            symbol,
            shares,
            price,
            total
        } = data;

        const title = action === 'buy' ? '📈 Buy Confirmed' : '📉 Sell Confirmed';
        const body = `${action.toUpperCase()} ${shares} shares of ${symbol} at $${price} (Total: $${total})`;

        try {
            await state.registration.showNotification(title, {
                body: body,
                icon: '/static/icons/icon-192x192.png',
                badge: '/static/icons/icon-96x96.png',
                tag: `trade-${Date.now()}`,
                data: {
                    url: '/portfolio'
                }
            });

            util.log('Trade notification sent:', data);
        } catch (error) {
            util.error('Trade notification failed', error);
        }
    }

    /**
     * Notify League Update
     */
    async function notifyLeagueUpdate(data) {
        if (!state.registration || !state.permissionGranted) {
            return;
        }

        const { leagueName, message } = data;

        try {
            await state.registration.showNotification(`⚡ ${leagueName}`, {
                body: message,
                icon: '/static/icons/icon-192x192.png',
                badge: '/static/icons/icon-96x96.png',
                tag: `league-${Date.now()}`,
                data: {
                    url: '/leagues'
                }
            });

            util.log('League notification sent:', data);
        } catch (error) {
            util.error('League notification failed', error);
        }
    }

    /**
     * Enable Debug Mode
     */
    function enableDebug() {
        config.debug = true;
        util.log('Debug mode enabled');
    }

    // Export API
    window.pushNotifications = {
        init,
        requestPermission,
        subscribe,
        unsubscribe,
        showTestNotification,
        notifyTrade,
        notifyLeagueUpdate,
        getSubscription: () => state.subscription,
        isSupported: () => state.supported,
        isGranted: () => state.permissionGranted,
        enableDebug
    };

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init().catch(err => util.error('Init error', err));
        });
    } else {
        init().catch(err => util.error('Init error', err));
    }
})();
