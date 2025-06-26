// =============================================================================
// GST Intelligence Platform - Main Application JavaScript
// Core functionality for the web application
// =============================================================================

'use strict';

// Global Configuration
window.GST_APP = {
    version: '2.0.0',
    debug: localStorage.getItem('gst_debug') === 'true',
    api: {
        baseURL: '',
        timeout: 30000
    },
    features: {
        offline: true,
        notifications: true,
        analytics: true,
        export: true
    }
};

// =============================================================================
// CORE APPLICATION CLASS
// =============================================================================

class GSTApplication {
    constructor() {
        this.initialized = false;
        this.user = null;
        this.preferences = {};
        this.cache = new Map();
        
        // Core managers
        this.notification = null;
        this.theme = null;
        this.offline = null;
        
        // Event listeners
        this.eventListeners = new Map();
        
        this.init();
    }
    
    async init() {
        try {
            await this.loadDependencies();
            await this.setupCore();
            await this.loadUserData();
            this.setupEventListeners();
            this.setupPerformanceMonitoring();
            
            this.initialized = true;
            this.log('✅ GST Application initialized successfully');
            
            // Dispatch ready event
            window.dispatchEvent(new CustomEvent('gst:ready', {
                detail: { app: this }
            }));
            
        } catch (error) {
            this.error('❌ Application initialization failed:', error);
        }
    }
    
    async loadDependencies() {
        // Check if core managers exist
        if (!window.NotificationManager) {
            this.error('NotificationManager not found');
            return;
        }
        
        // Initialize core managers
        this.notification = new NotificationManager();
        
        if (window.ThemeManager) {
            this.theme = new ThemeManager();
        }
        
        if (window.OfflineManager) {
            this.offline = window.offlineManager;
        }
    }
    
    setupCore() {
        // Setup global error handling
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event.error, 'JavaScript Error', {
                filename: event.filename,
                lineno: event.lineno
            });
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.handleGlobalError(event.reason, 'Unhandled Promise Rejection');
        });
        
        // Setup API interceptors
        this.setupAPIInterceptors();
    }
    
    async loadUserData() {
        try {
            const response = await this.api('/api/user/profile');
            if (response.success) {
                this.user = response.data;
            }
            
            const prefsResponse = await this.api('/api/user/preferences');
            if (prefsResponse.success) {
                this.preferences = prefsResponse.data;
                this.applyUserPreferences();
            }
        } catch (error) {
            this.warn('Failed to load user data:', error);
        }
    }
    
    setupEventListeners() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.onPageHidden();
            } else {
                this.onPageVisible();
            }
        });
        
        // Network status changes
        window.addEventListener('online', () => this.onNetworkOnline());
        window.addEventListener('offline', () => this.onNetworkOffline());
        
        // Beforeunload for cleanup
        window.addEventListener('beforeunload', () => this.cleanup());
    }
    
    setupPerformanceMonitoring() {
        // Performance observer for monitoring
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.duration > 1000) { // Log slow operations
                        this.warn(`Slow operation detected: ${entry.name} took ${entry.duration}ms`);
                    }
                }
            });
            
            observer.observe({ entryTypes: ['measure', 'navigation'] });
        }
    }
    
    // =============================================================================
    // API METHODS
    // =============================================================================
    
    async api(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${window.location.origin}${endpoint}`;
        
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return response;
            
        } catch (error) {
            this.error('API request failed:', error);
            throw error;
        }
    }
    
    setupAPIInterceptors() {
        // Intercept fetch requests for global error handling
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                // Handle authentication errors
                if (response.status === 401) {
                    this.handleAuthError();
                }
                
                return response;
            } catch (error) {
                this.handleNetworkError(error);
                throw error;
            }
        };
    }
    
    handleAuthError() {
        this.notification.showError('Session expired. Please login again.');
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    handleNetworkError(error) {
        if (!navigator.onLine) {
            this.notification.showWarning('You are offline. Some features may not work.');
        } else {
            this.notification.showError('Network error. Please check your connection.');
        }
    }
    
    // =============================================================================
    // USER INTERFACE METHODS
    // =============================================================================
    
    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'flex';
            const text = overlay.querySelector('.loading-text');
            if (text) text.textContent = message;
        }
    }
    
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    updatePageTitle(title) {
        document.title = title ? `${title} - GST Intelligence` : 'GST Intelligence Platform';
    }
    
    scrollToTop(smooth = true) {
        window.scrollTo({
            top: 0,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }
    
    // =============================================================================
    // GSTIN UTILITIES
    // =============================================================================
    
    isValidGSTIN(gstin) {
        if (!gstin || typeof gstin !== 'string') return false;
        
        const clean = gstin.replace(/\s/g, '').toUpperCase();
        const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
        
        return pattern.test(clean);
    }
    
    formatGSTIN(gstin) {
        if (!gstin) return '';
        
        const clean = gstin.replace(/\s/g, '').toUpperCase();
        if (clean.length === 15) {
            return `${clean.substr(0, 2)} ${clean.substr(2, 5)} ${clean.substr(7, 4)} ${clean.substr(11, 4)}`;
        }
        
        return clean;
    }
    
    async searchGSTIN(gstin) {
        if (!this.isValidGSTIN(gstin)) {
            throw new Error('Invalid GSTIN format');
        }
        
        this.showLoading('Searching GSTIN...');
        
        try {
            const response = await this.api('/api/search', {
                method: 'POST',
                body: JSON.stringify({ gstin: gstin.replace(/\s/g, '').toUpperCase() })
            });
            
            return response;
        } finally {
            this.hideLoading();
        }
    }
    
    // =============================================================================
    // CACHE MANAGEMENT
    // =============================================================================
    
    setCache(key, value, ttl = 300000) { // 5 minutes default
        this.cache.set(key, {
            value,
            expires: Date.now() + ttl
        });
    }
    
    getCache(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        if (Date.now() > item.expires) {
            this.cache.delete(key);
            return null;
        }
        
        return item.value;
    }
    
    clearCache() {
        this.cache.clear();
        this.log('Cache cleared');
    }
    
    // =============================================================================
    // USER PREFERENCES
    // =============================================================================
    
    applyUserPreferences() {
        if (this.preferences.theme) {
            this.setTheme(this.preferences.theme);
        }
        
        if (this.preferences.notifications === false) {
            this.notification.disable();
        }
    }
    
    async updatePreferences(newPrefs) {
        try {
            const response = await this.api('/api/user/preferences', {
                method: 'POST',
                body: JSON.stringify(newPrefs)
            });
            
            if (response.success) {
                this.preferences = { ...this.preferences, ...newPrefs };
                this.applyUserPreferences();
                this.notification.showSuccess('Preferences updated successfully');
            }
        } catch (error) {
            this.notification.showError('Failed to update preferences');
        }
    }
    
    setTheme(theme) {
        if (this.theme) {
            this.theme.setTheme(theme);
        } else {
            // Fallback theme switching
            const html = document.documentElement;
            if (theme === 'light') {
                html.setAttribute('data-theme', 'light');
            } else {
                html.removeAttribute('data-theme');
            }
        }
    }
    
    // =============================================================================
    // EVENT HANDLING
    // =============================================================================
    
    on(event, callback) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(callback);
    }
    
    emit(event, data) {
        if (this.eventListeners.has(event)) {
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    this.error('Event handler error:', error);
                }
            });
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="gstin"], #gstinInput');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            if (window.modalManager) {
                window.modalManager.closeAllModals();
            }
        }
        
        // Alt + T for theme toggle
        if (e.altKey && e.key === 't') {
            e.preventDefault();
            if (this.theme) {
                this.theme.toggleTheme();
            }
        }
    }
    
    onPageHidden() {
        this.log('Page hidden');
        // Pause non-critical operations
    }
    
    onPageVisible() {
        this.log('Page visible');
        // Resume operations
        this.syncData();
    }
    
    onNetworkOnline() {
        this.notification.showSuccess('Connection restored');
        this.syncData();
    }
    
    onNetworkOffline() {
        this.notification.showWarning('You are offline');
    }
    
    // =============================================================================
    // DATA SYNCHRONIZATION
    // =============================================================================
    
    async syncData() {
        if (!navigator.onLine) return;
        
        try {
            // Sync offline searches if any
            if (this.offline) {
                await this.offline.syncOfflineData();
            }
            
            // Refresh user data
            await this.loadUserData();
            
        } catch (error) {
            this.warn('Data sync failed:', error);
        }
    }
    
    // =============================================================================
    // ERROR HANDLING
    // =============================================================================
    
    handleGlobalError(error, type, context = {}) {
        this.error(`${type}:`, error);
        
        // Report to server in production
        if (window.location.hostname !== 'localhost') {
            this.reportError(error, type, context);
        }
        
        // Show user-friendly message
        if (this.notification) {
            this.notification.showError('Something went wrong. Please try again.');
        }
    }
    
    async reportError(error, type, context = {}) {
        try {
            await this.api('/api/system/error', {
                method: 'POST',
                body: JSON.stringify({
                    type,
                    message: error.message || String(error),
                    stack: error.stack,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString(),
                    context
                })
            });
        } catch (reportError) {
            this.warn('Failed to report error:', reportError);
        }
    }
    
    // =============================================================================
    // UTILITY METHODS
    // =============================================================================
    
    log(...args) {
        if (this.debug) {
            console.log('🔧 GST App:', ...args);
        }
    }
    
    warn(...args) {
        console.warn('⚠️ GST App:', ...args);
    }
    
    error(...args) {
        console.error('❌ GST App:', ...args);
    }
    
    formatCurrency(amount, currency = '₹') {
        if (typeof amount !== 'number') return '₹0';
        
        if (amount >= 10000000) {
            return `${currency}${(amount / 10000000).toFixed(1)}Cr`;
        } else if (amount >= 100000) {
            return `${currency}${(amount / 100000).toFixed(1)}L`;
        } else if (amount >= 1000) {
            return `${currency}${(amount / 1000).toFixed(1)}K`;
        }
        
        return `${currency}${amount.toLocaleString()}`;
    }
    
    formatDate(date, format = 'relative') {
        if (!date) return 'N/A';
        
        const dateObj = new Date(date);
        if (isNaN(dateObj.getTime())) return 'Invalid Date';
        
        if (format === 'relative') {
            const now = new Date();
            const diff = now - dateObj;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            
            if (days === 0) return 'Today';
            if (days === 1) return 'Yesterday';
            if (days < 7) return `${days} days ago`;
            if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
            if (days < 365) return `${Math.floor(days / 30)} months ago`;
            return `${Math.floor(days / 365)} years ago`;
        }
        
        return dateObj.toLocaleDateString();
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // =============================================================================
    // CLEANUP
    // =============================================================================
    
    cleanup() {
        // Clear timers, observers, etc.
        this.clearCache();
        
        // Remove event listeners
        this.eventListeners.clear();
        
        this.log('Application cleanup completed');
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Initialize application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gstApp = new GSTApplication();
    });
} else {
    window.gstApp = new GSTApplication();
}

// =============================================================================
// GLOBAL UTILITIES (for backward compatibility)
// =============================================================================

// Make common functions globally available
window.isValidGSTIN = (gstin) => window.gstApp?.isValidGSTIN(gstin) || false;
window.formatGSTIN = (gstin) => window.gstApp?.formatGSTIN(gstin) || gstin;
window.showLoading = (message) => window.gstApp?.showLoading(message);
window.hideLoading = () => window.gstApp?.hideLoading();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GSTApplication;
}

// Debug helpers
window.addEventListener('load', () => {
    if (window.GST_APP.debug) {
        console.log('🚀 GST Intelligence Platform loaded');
        console.log('📊 Performance:', performance.getEntriesByType('navigation')[0]);
        
        // Add debug helpers to window
        window.gstDebug = {
            app: window.gstApp,
            cache: () => window.gstApp?.cache,
            preferences: () => window.gstApp?.preferences,
            clearCache: () => window.gstApp?.clearCache(),
            toggleDebug: () => {
                const current = localStorage.getItem('gst_debug') === 'true';
                localStorage.setItem('gst_debug', (!current).toString());
                location.reload();
            }
        };
        
        console.log('🔧 Debug helpers available at window.gstDebug');
    }
});

console.log('✅ GST Application core loaded successfully');