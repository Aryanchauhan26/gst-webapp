// /static/js/app-core.js - Consolidated implementation
class GSTPlatformCore {
    constructor() {
        this.themeManager = new ThemeManager();
        this.modalManager = new ModalManager();
        this.debugManager = new DebugManager();
        this.errorHandler = new ErrorHandler();
        this.init();
    }

    init() {
        console.log('🚀 GST Platform Core initialized');
        this.setupEventListeners();
        this.initializeModules();
    }

    setupEventListeners() {
        // Consolidated event handling
        document.addEventListener('DOMContentLoaded', () => {
            this.onDOMReady();
        });
        
        // Global error handling
        window.addEventListener('error', (event) => {
            this.errorHandler.handleGlobalError(event);
        });
        
        // Unhandled promise rejection
        window.addEventListener('unhandledrejection', (event) => {
            this.errorHandler.handlePromiseRejection(event);
        });
    }

    onDOMReady() {
        this.themeManager.initialize();
        this.setupAPIHandlers();
        this.initializeCharts();
    }
}

// Theme Manager - Fixed Implementation
class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        this.themes = ['light', 'dark'];
    }

    initialize() {
        this.applyTheme(this.currentTheme);
        this.setupThemeToggle();
        this.watchSystemTheme();
    }

    getStoredTheme() {
        try {
            return localStorage.getItem('gst-theme');
        } catch (error) {
            console.warn('Failed to access localStorage for theme');
            return null;
        }
    }

    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    applyTheme(theme) {
        if (!this.themes.includes(theme)) {
            console.warn(`Invalid theme: ${theme}`);
            theme = 'dark';
        }

        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        
        try {
            localStorage.setItem('gst-theme', theme);
        } catch (error) {
            console.warn('Failed to save theme to localStorage');
        }

        this.updateThemeIndicators();
        this.notifyThemeChange(theme);
    }

    updateThemeIndicators() {
        const indicators = document.querySelectorAll('[data-theme-toggle]');
        indicators.forEach(indicator => {
            const icon = indicator.querySelector('i');
            if (icon) {
                icon.className = this.currentTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
            }
        });
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
    }

    setupThemeToggle() {
        window.toggleTheme = () => this.toggleTheme();
        
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.addEventListener('click', () => this.toggleTheme());
        });
    }

    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    notifyThemeChange(theme) {
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme, timestamp: Date.now() }
        }));
    }
}

// Enhanced Modal Manager - Fixed Memory Leaks
class ModalManager {
    constructor() {
        this.activeModals = new Map();
        this.setupGlobalHandlers();
    }

    setupGlobalHandlers() {
        // Global escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeTopModal();
            }
        });

        // Global click outside handler
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                const modalId = e.target.getAttribute('data-modal-id');
                if (modalId) {
                    this.closeModal(modalId);
                }
            }
        });
    }

    openModal(config) {
        const { id, title, content, size = 'medium', onClose } = config;
        
        // Close existing modal with same ID
        if (this.activeModals.has(id)) {
            this.closeModal(id);
        }

        const modal = this.createModalElement(id, title, content, size);
        document.body.appendChild(modal);
        
        // Store modal reference
        this.activeModals.set(id, {
            element: modal,
            onClose: onClose || null
        });

        // Animate in
        requestAnimationFrame(() => {
            modal.classList.add('modal-visible');
        });

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        return modal;
    }

    createModalElement(id, title, content, size) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.setAttribute('data-modal-id', id);
        
        modal.innerHTML = `
            <div class="modal-content modal-${size}">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button type="button" class="modal-close" data-close-modal="${id}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;

        // Add close button handler
        const closeBtn = modal.querySelector('[data-close-modal]');
        closeBtn.addEventListener('click', () => this.closeModal(id));

        return modal;
    }

    closeModal(id) {
        const modalData = this.activeModals.get(id);
        if (!modalData) return;

        const modal = modalData.element;
        
        // Call onClose callback
        if (modalData.onClose) {
            modalData.onClose();
        }

        // Animate out
        modal.classList.remove('modal-visible');
        
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
            this.activeModals.delete(id);
            
            // Restore body scroll if no modals
            if (this.activeModals.size === 0) {
                document.body.style.overflow = '';
            }
        }, 300);
    }

    closeTopModal() {
        if (this.activeModals.size > 0) {
            const lastModalId = Array.from(this.activeModals.keys()).pop();
            this.closeModal(lastModalId);
        }
    }

    closeAllModals() {
        Array.from(this.activeModals.keys()).forEach(id => {
            this.closeModal(id);
        });
    }
}

// Enhanced Error Handler
class ErrorHandler {
    constructor() {
        this.errors = [];
        this.maxErrors = 100;
        this.apiEndpoint = '/api/system/log-error';
    }

    handleGlobalError(event) {
        const error = {
            type: 'javascript',
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error?.stack,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        this.logError(error);
        this.reportError(error);
    }

    handlePromiseRejection(event) {
        const error = {
            type: 'promise',
            message: event.reason?.message || 'Unhandled Promise Rejection',
            stack: event.reason?.stack,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        this.logError(error);
        this.reportError(error);
    }

    handleAPIError(response, context = {}) {
        const error = {
            type: 'api',
            message: `API Error: ${response.status} ${response.statusText}`,
            url: response.url,
            status: response.status,
            context: context,
            timestamp: new Date().toISOString()
        };

        this.logError(error);
        this.showUserError('Network error occurred. Please try again.');
    }

    logError(error) {
        console.error('🚨 Error logged:', error);
        this.errors.push(error);
        
        // Keep only recent errors
        if (this.errors.length > this.maxErrors) {
            this.errors = this.errors.slice(-this.maxErrors);
        }
    }

    async reportError(error) {
        try {
            await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(error)
            });
        } catch (reportError) {
            console.warn('Failed to report error to server:', reportError);
        }
    }

    showUserError(message, type = 'error') {
        // Show user-friendly error notification
        this.showNotification(message, type);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getIconForType(type)}"></i>
            <span>${message}</span>
            <button type="button" class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        document.body.appendChild(notification);

        // Auto remove
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.add('notification-exit');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 5000);

        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.classList.add('notification-exit');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        });
    }

    getIconForType(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    getErrorSummary() {
        return {
            total: this.errors.length,
            byType: this.errors.reduce((acc, error) => {
                acc[error.type] = (acc[error.type] || 0) + 1;
                return acc;
            }, {}),
            recent: this.errors.slice(-10)
        };
    }
}

// Debug Manager
class DebugManager {
    constructor() {
        this.enabled = this.getDebugState();
        this.logs = [];
        this.maxLogs = 500;
    }

    getDebugState() {
        try {
            return localStorage.getItem('gst-debug') === 'true' || 
                   window.location.search.includes('debug=true');
        } catch {
            return false;
        }
    }

    enable() {
        this.enabled = true;
        try {
            localStorage.setItem('gst-debug', 'true');
        } catch (error) {
            console.warn('Failed to save debug state');
        }
        console.log('🐛 Debug mode enabled');
    }

    disable() {
        this.enabled = false;
        try {
            localStorage.setItem('gst-debug', 'false');
        } catch (error) {
            console.warn('Failed to save debug state');
        }
        console.log('🐛 Debug mode disabled');
    }

    log(...args) {
        if (this.enabled) {
            const timestamp = new Date().toISOString();
            console.log(`🔍 [${timestamp}] DEBUG:`, ...args);
            
            this.logs.push({
                timestamp,
                level: 'debug',
                args: args
            });
            
            this.trimLogs();
        }
    }

    error(...args) {
        if (this.enabled) {
            const timestamp = new Date().toISOString();
            console.error(`❌ [${timestamp}] DEBUG ERROR:`, ...args);
            
            this.logs.push({
                timestamp,
                level: 'error',
                args: args
            });
            
            this.trimLogs();
        }
    }

    warn(...args) {
        if (this.enabled) {
            const timestamp = new Date().toISOString();
            console.warn(`⚠️ [${timestamp}] DEBUG WARNING:`, ...args);
            
            this.logs.push({
                timestamp,
                level: 'warning',
                args: args
            });
            
            this.trimLogs();
        }
    }

    trimLogs() {
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs);
        }
    }

    exportLogs() {
        const data = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            logs: this.logs
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gst-debug-logs-${Date.now()}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
    }

    getSystemInfo() {
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth
            },
            localStorage: !!window.localStorage,
            sessionStorage: !!window.sessionStorage,
            webGL: !!window.WebGLRenderingContext,
            indexedDB: !!window.indexedDB
        };
    }
}

// Initialize on load
window.GSTPlatform = new GSTPlatformCore();