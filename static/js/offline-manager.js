/**
 * Offline Manager - Phase 5 Task 5.2.3
 * Handles trade queueing, offline storage, and sync when connection restored
 * Uses IndexedDB for persistent local storage
 */

class OfflineManager {
    constructor() {
        this.dbName = 'StockLeague';
        this.dbVersion = 1;
        this.db = null;
        this.isOnline = navigator.onLine;
        this.syncInProgress = false;
        
        // Initialize database and event listeners
        this.init();
    }

    /**
     * Initialize offline manager
     */
    init() {
        // Listen for online/offline events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        // Initialize IndexedDB
        this.initDB();

        // Show offline indicator if needed
        this.updateOfflineUI();
    }

    /**
     * Initialize IndexedDB database
     */
    initDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                console.error('[OfflineManager] Failed to open IndexedDB:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('[OfflineManager] IndexedDB opened successfully');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                this.db = event.target.result;
                this._createObjectStores();
            };
        });
    }

    /**
     * Create IndexedDB object stores
     */
    _createObjectStores() {
        // Trade queue store
        if (!this.db.objectStoreNames.contains('tradeQueue')) {
            const tradeStore = this.db.createObjectStore('tradeQueue', {
                keyPath: 'id',
                autoIncrement: true
            });
            tradeStore.createIndex('status', 'status', { unique: false });
            tradeStore.createIndex('timestamp', 'timestamp', { unique: false });
            console.log('[OfflineManager] Created tradeQueue store');
        }

        // Cached data store
        if (!this.db.objectStoreNames.contains('cachedData')) {
            const cacheStore = this.db.createObjectStore('cachedData', {
                keyPath: 'key'
            });
            cacheStore.createIndex('timestamp', 'timestamp', { unique: false });
            console.log('[OfflineManager] Created cachedData store');
        }

        // Sync log store
        if (!this.db.objectStoreNames.contains('syncLog')) {
            const syncStore = this.db.createObjectStore('syncLog', {
                keyPath: 'id',
                autoIncrement: true
            });
            syncStore.createIndex('timestamp', 'timestamp', { unique: false });
            console.log('[OfflineManager] Created syncLog store');
        }
    }

    /**
     * Queue a trade for offline execution
     */
    async queueTrade(tradeData) {
        if (!this.db) {
            console.error('[OfflineManager] Database not initialized');
            return null;
        }

        const trade = {
            symbol: tradeData.symbol.toUpperCase(),
            action: tradeData.action, // 'buy' or 'sell'
            shares: parseFloat(tradeData.shares),
            price: tradeData.price ? parseFloat(tradeData.price) : null,
            orderType: tradeData.orderType || 'market', // 'market' or 'limit'
            status: 'pending', // pending, syncing, completed, failed
            timestamp: new Date().toISOString(),
            errorMessage: null,
            syncAttempts: 0,
            maxRetries: 3
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tradeQueue'], 'readwrite');
            const store = transaction.objectStore('tradeQueue');
            const request = store.add(trade);

            request.onsuccess = () => {
                trade.id = request.result;
                console.log('[OfflineManager] Trade queued:', trade);
                this.updateQueueUI();
                resolve(trade);
            };

            request.onerror = () => {
                console.error('[OfflineManager] Failed to queue trade:', request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Get all pending trades
     */
    async getPendingTrades() {
        if (!this.db) return [];

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tradeQueue'], 'readonly');
            const store = transaction.objectStore('tradeQueue');
            const index = store.index('status');
            const request = index.getAll('pending');

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * Get queue size
     */
    async getQueueSize() {
        const pending = await this.getPendingTrades();
        return pending.length;
    }

    /**
     * Sync trades with server
     */
    async syncTrades() {
        if (this.syncInProgress || !this.isOnline) {
            console.log('[OfflineManager] Sync skipped: inProgress=' + this.syncInProgress + ', online=' + this.isOnline);
            return;
        }

        this.syncInProgress = true;
        const pendingTrades = await this.getPendingTrades();

        if (pendingTrades.length === 0) {
            this.syncInProgress = false;
            console.log('[OfflineManager] No trades to sync');
            return;
        }

        console.log(`[OfflineManager] Starting sync of ${pendingTrades.length} trades`);

        for (const trade of pendingTrades) {
            await this._syncTrade(trade);
        }

        this.syncInProgress = false;
        console.log('[OfflineManager] Sync complete');
    }

    /**
     * Sync individual trade
     */
    async _syncTrade(trade) {
        if (trade.syncAttempts >= trade.maxRetries) {
            console.warn('[OfflineManager] Max retries exceeded for trade:', trade);
            await this._updateTradeStatus(trade.id, 'failed', 'Max retries exceeded');
            return;
        }

        try {
            // Update status to syncing
            await this._updateTradeStatus(trade.id, 'syncing');

            // Send trade to server
            const response = await fetch('/api/trade', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    symbol: trade.symbol,
                    shares: trade.shares,
                    action: trade.action,
                    orderType: trade.orderType,
                    price: trade.price,
                    fromOfflineQueue: true
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[OfflineManager] Trade synced successfully:', result);
                await this._updateTradeStatus(trade.id, 'completed');
                this.updateQueueUI();
            } else {
                throw new Error(`Server returned ${response.status}`);
            }
        } catch (error) {
            console.error('[OfflineManager] Trade sync failed:', error);
            trade.syncAttempts++;
            await this._updateTradeSyncAttempts(trade.id, trade.syncAttempts);

            if (trade.syncAttempts >= trade.maxRetries) {
                await this._updateTradeStatus(trade.id, 'failed', error.message);
                this._notifyTradeFailure(trade, error.message);
            }
        }
    }

    /**
     * Update trade status
     */
    async _updateTradeStatus(tradeId, status, errorMessage = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tradeQueue'], 'readwrite');
            const store = transaction.objectStore('tradeQueue');
            const getRequest = store.get(tradeId);

            getRequest.onsuccess = () => {
                const trade = getRequest.result;
                if (trade) {
                    trade.status = status;
                    if (errorMessage) {
                        trade.errorMessage = errorMessage;
                    }

                    const updateRequest = store.put(trade);
                    updateRequest.onsuccess = () => resolve(trade);
                    updateRequest.onerror = () => reject(updateRequest.error);
                }
            };

            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    /**
     * Update sync attempts count
     */
    async _updateTradeSyncAttempts(tradeId, attempts) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tradeQueue'], 'readwrite');
            const store = transaction.objectStore('tradeQueue');
            const getRequest = store.get(tradeId);

            getRequest.onsuccess = () => {
                const trade = getRequest.result;
                if (trade) {
                    trade.syncAttempts = attempts;
                    const updateRequest = store.put(trade);
                    updateRequest.onsuccess = () => resolve(trade);
                    updateRequest.onerror = () => reject(updateRequest.error);
                }
            };

            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    /**
     * Cache data for offline access
     */
    async cacheData(key, data) {
        if (!this.db) return;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cachedData'], 'readwrite');
            const store = transaction.objectStore('cachedData');

            const request = store.put({
                key: key,
                data: data,
                timestamp: new Date().toISOString()
            });

            request.onsuccess = () => {
                console.log('[OfflineManager] Data cached:', key);
                resolve();
            };

            request.onerror = () => {
                console.error('[OfflineManager] Failed to cache data:', request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Get cached data
     */
    async getCachedData(key) {
        if (!this.db) return null;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cachedData'], 'readonly');
            const store = transaction.objectStore('cachedData');
            const request = store.get(key);

            request.onsuccess = () => {
                resolve(request.result ? request.result.data : null);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * Clear all cache
     */
    async clearCache() {
        if (!this.db) return;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cachedData'], 'readwrite');
            const store = transaction.objectStore('cachedData');
            const request = store.clear();

            request.onsuccess = () => {
                console.log('[OfflineManager] Cache cleared');
                resolve();
            };

            request.onerror = () => {
                console.error('[OfflineManager] Failed to clear cache:', request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Handle going online
     */
    async handleOnline() {
        console.log('[OfflineManager] Back online');
        this.isOnline = true;
        this.updateOfflineUI();
        
        // Sync trades
        await this.syncTrades();

        // Dispatch event for app to handle
        window.dispatchEvent(new CustomEvent('stockleague-online', {
            detail: { timestamp: new Date() }
        }));
    }

    /**
     * Handle going offline
     */
    handleOffline() {
        console.log('[OfflineManager] Gone offline');
        this.isOnline = false;
        this.updateOfflineUI();

        // Dispatch event for app to handle
        window.dispatchEvent(new CustomEvent('stockleague-offline', {
            detail: { timestamp: new Date() }
        }));
    }

    /**
     * Update UI to show offline status
     */
    updateOfflineUI() {
        let indicator = document.getElementById('offline-indicator');

        if (!this.isOnline) {
            // Create indicator if it doesn't exist
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'offline-indicator';
                document.body.appendChild(indicator);
            }

            indicator.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-0 end-0 m-0 rounded-0';
            indicator.style.zIndex = '9999';
            indicator.innerHTML = `
                <i class="fas fa-wifi-slash me-2"></i>
                <strong>You're Offline</strong> - Changes will sync when you're back online
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
        } else {
            // Remove indicator when online
            if (indicator) {
                indicator.remove();
            }

            // Show sync status if there are pending trades
            this.getQueueSize().then(size => {
                if (size > 0) {
                    this._showSyncNotification(size);
                }
            });
        }
    }

    /**
     * Update queue UI (show pending count)
     */
    async updateQueueUI() {
        const size = await this.getQueueSize();
        const queueIndicator = document.getElementById('queue-indicator');

        if (size > 0) {
            if (!queueIndicator) {
                const indicator = document.createElement('span');
                indicator.id = 'queue-indicator';
                indicator.className = 'badge bg-warning position-absolute top-0 start-100 translate-middle';
                // Find element to attach to (e.g., trade icon)
                const tradeLink = document.querySelector('a[href="/trade"]');
                if (tradeLink) {
                    tradeLink.style.position = 'relative';
                    tradeLink.appendChild(indicator);
                }
            }
            if (queueIndicator) {
                queueIndicator.textContent = size;
            }
        } else {
            if (queueIndicator) {
                queueIndicator.remove();
            }
        }
    }

    /**
     * Show sync notification
     */
    _showSyncNotification(count) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-info alert-dismissible fade show position-fixed bottom-0 end-0 m-3';
        alert.style.zIndex = '9998';
        alert.innerHTML = `
            <i class="fas fa-sync me-2"></i>
            <strong>Syncing!</strong> ${count} pending trade${count > 1 ? 's' : ''} being sent to server...
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    }

    /**
     * Notify user of trade failure
     */
    _notifyTradeFailure(trade, reason) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed bottom-0 end-0 m-3';
        alert.style.zIndex = '9998';
        alert.innerHTML = `
            <i class="fas fa-exclamation-circle me-2"></i>
            <strong>Trade Failed!</strong> ${trade.symbol} ${trade.action} failed to sync: ${reason}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 10000);
    }

    /**
     * Get database stats
     */
    async getStats() {
        const pending = await this.getPendingTrades();
        const estimate = await navigator.storage?.estimate?.();

        return {
            pending: pending.length,
            isOnline: this.isOnline,
            storageUsed: estimate?.usage || 'N/A',
            storageAvailable: estimate?.quota || 'N/A'
        };
    }
}

// Initialize offline manager on load
let offlineManager = null;

document.addEventListener('DOMContentLoaded', () => {
    if ('indexedDB' in window) {
        offlineManager = new OfflineManager();
        window.StockLeagueOffline = offlineManager;
        console.log('[OfflineManager] Initialized');
    } else {
        console.warn('[OfflineManager] IndexedDB not supported');
    }
});

// Expose offline manager globally for debugging
window.OfflineManager = OfflineManager;
