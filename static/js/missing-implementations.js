// =====================================================
// GST Intelligence Platform - Core JavaScript Framework
// Missing Implementations & Essential Functionality
// =====================================================

'use strict';

// Global Configuration
window.GST_CONFIG = {
    API_BASE_URL: '',
    USER_PREFERENCES_KEY: 'gst_user_preferences',
    RECENT_SEARCHES_KEY: 'recentGSTINSearches',
    DEBUG_MODE: localStorage.getItem('gst_debug') === 'true',
    MAX_RECENT_SEARCHES: 10,
    NOTIFICATION_DURATION: 5000,
    THEME_TRANSITION_DURATION: 300
};

// =====================================================
// 1. NOTIFICATION MANAGER
// =====================================================

class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.notifications = [];
        this.defaultOptions = {
            duration: 5000,
            position: 'top-right',
            maxNotifications: 5
        };
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 1080;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-width: 400px;
        `;
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = this.defaultOptions.duration) {
        const notification = this.createNotification(message, type);
        
        // Limit notifications
        if (this.notifications.length >= this.defaultOptions.maxNotifications) {
            this.remove(this.notifications[0]);
        }

        this.container.appendChild(notification.element);
        this.notifications.push(notification);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(notification), duration);
        }

        return notification;
    }

    createNotification(message, type) {
        const id = Date.now() + Math.random();
        const element = document.createElement('div');
        
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const colorMap = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        element.style.cssText = `
            background: var(--bg-card);
            border: 1px solid ${colorMap[type] || colorMap.info};
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            pointer-events: auto;
            cursor: pointer;
            transition: all 0.3s ease;
            animation: slideIn 0.3s ease-out;
            max-width: 100%;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        `;

        element.innerHTML = `
            <i class="${iconMap[type] || iconMap.info}" style="color: ${colorMap[type] || colorMap.info}; font-size: 1.2rem; margin-top: 0.1rem; flex-shrink: 0;"></i>
            <div style="flex: 1; color: var(--text-primary); font-size: 0.9rem; line-height: 1.4;">${message}</div>
            <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 0; font-size: 1.1rem; flex-shrink: 0;" onclick="event.stopPropagation(); window.notificationManager.removeElement(this.parentElement)">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add hover effect
        element.addEventListener('mouseenter', () => {
            element.style.transform = 'translateX(-5px) scale(1.02)';
        });

        element.addEventListener('mouseleave', () => {
            element.style.transform = 'translateX(0) scale(1)';
        });

        return { id, element, type };
    }

    remove(notification) {
        const index = this.notifications.findIndex(n => n.id === notification.id);
        if (index > -1) {
            const notificationObj = this.notifications[index];
            this.removeElement(notificationObj.element);
            this.notifications.splice(index, 1);
        }
    }

    removeElement(element) {
        if (element && element.parentNode) {
            element.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => {
                if (element.parentNode) {
                    element.parentNode.removeChild(element);
                }
            }, 300);
        }
    }

    // Convenience methods
    showSuccess(message, duration) { return this.show(message, 'success', duration); }
    showError(message, duration) { return this.show(message, 'error', duration); }
    showWarning(message, duration) { return this.show(message, 'warning', duration); }
    showInfo(message, duration) { return this.show(message, 'info', duration); }
    showToast(message, type = 'info', duration) { return this.show(message, type, duration); }

    clear() {
        this.notifications.forEach(notification => this.remove(notification));
    }
}

// Add notification styles
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes slideOut {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100%);
            }
        }
    `;
    document.head.appendChild(style);
}

// =====================================================
// 2. MODAL MANAGER
// =====================================================

class ModalManager {
    constructor() {
        this.modals = [];
        this.currentZIndex = 1050;
    }

    createModal(options = {}) {
        const {
            title = 'Modal',
            content = '',
            size = 'medium',
            closable = true,
            backdrop = true,
            onSubmit = null,
            onClose = null
        } = options;

        const modalId = 'modal_' + Date.now();
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            z-index: ${this.currentZIndex++};
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            padding: 1rem;
        `;

        const sizeStyles = {
            small: 'max-width: 400px;',
            medium: 'max-width: 600px;',
            large: 'max-width: 800px;',
            fullscreen: 'width: 95%; height: 95%;'
        };

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-card);
                border-radius: 16px;
                ${sizeStyles[size]}
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                border: 1px solid var(--border-primary);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            ">
                <div class="modal-header" style="
                    padding: 2rem 2rem 1rem 2rem;
                    border-bottom: 1px solid var(--border-primary);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <h3 style="margin: 0; color: var(--text-primary); font-size: 1.5rem; font-weight: 600;">${title}</h3>
                    ${closable ? `
                        <button class="modal-close" style="
                            background: none;
                            border: none;
                            color: var(--text-secondary);
                            font-size: 1.5rem;
                            cursor: pointer;
                            padding: 0.5rem;
                            border-radius: 8px;
                            transition: all 0.3s ease;
                        " onclick="window.modalManager.closeModal('${modalId}')">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
                <div class="modal-body" style="padding: 2rem;">
                    ${content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Show animation
        setTimeout(() => {
            modal.style.opacity = '1';
            const modalContent = modal.querySelector('.modal-content');
            modalContent.style.transform = 'scale(1)';
        }, 10);

        // Event listeners
        if (backdrop) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modalId);
                }
            });
        }

        // Handle form submission
        if (onSubmit) {
            const form = modal.querySelector('form');
            if (form) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const data = Object.fromEntries(formData.entries());
                    
                    try {
                        const result = await onSubmit(data);
                        if (result !== false) {
                            this.closeModal(modalId);
                        }
                    } catch (error) {
                        console.error('Form submission error:', error);
                    }
                });
            }
        }

        // Escape key handler
        const escapeHandler = (e) => {
            if (e.key === 'Escape' && closable) {
                this.closeModal(modalId);
            }
        };
        document.addEventListener('keydown', escapeHandler);

        const modalObj = {
            id: modalId,
            element: modal,
            onClose,
            escapeHandler
        };

        this.modals.push(modalObj);
        return modalObj;
    }

    closeModal(modalId) {
        const modalIndex = this.modals.findIndex(m => m.id === modalId);
        if (modalIndex === -1) return;

        const modal = this.modals[modalIndex];
        
        if (modal.onClose) {
            modal.onClose();
        }

        document.removeEventListener('keydown', modal.escapeHandler);

        modal.element.style.opacity = '0';
        const modalContent = modal.element.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.transform = 'scale(0.9)';
        }

        setTimeout(() => {
            if (modal.element.parentNode) {
                modal.element.parentNode.removeChild(modal.element);
            }
            this.modals.splice(modalIndex, 1);
        }, 300);
    }

    closeAllModals() {
        [...this.modals].forEach(modal => this.closeModal(modal.id));
    }
}

// =====================================================
// 3. THEME MANAGER
// =====================================================

class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || 'dark';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupThemeToggle();
        this.watchSystemTheme();
    }

    getStoredTheme() {
        return localStorage.getItem('theme');
    }

    setTheme(theme, save = true) {
        this.currentTheme = theme;
        this.applyTheme(theme);
        
        if (save) {
            localStorage.setItem('theme', theme);
        }

        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme } 
        }));
    }

    applyTheme(theme) {
        const html = document.documentElement;
        
        if (theme === 'light') {
            html.setAttribute('data-theme', 'light');
        } else {
            html.removeAttribute('data-theme');
        }

        this.updateThemeToggles();
    }

    updateThemeToggles() {
        const indicators = document.querySelectorAll('[data-theme-icon]');
        indicators.forEach(indicator => {
            const icon = indicator.querySelector('i');
            if (icon) {
                if (this.currentTheme === 'light') {
                    icon.className = 'fas fa-sun';
                } else {
                    icon.className = 'fas fa-moon';
                }
            }
        });
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        
        document.body.classList.add('theme-transitioning');
        this.setTheme(newTheme);
        
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, window.GST_CONFIG.THEME_TRANSITION_DURATION);
    }

    setupThemeToggle() {
        window.toggleTheme = () => this.toggleTheme();
    }

    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.setTheme(e.matches ? 'light' : 'dark', false);
                }
            });
        }
    }
}

// =====================================================
// 4. DEBUG MANAGER
// =====================================================

class DebugManager {
    constructor() {
        this.enabled = localStorage.getItem('gst_debug') === 'true';
    }

    enable() {
        localStorage.setItem('gst_debug', 'true');
        this.enabled = true;
        window.GST_CONFIG.DEBUG_MODE = true;
        console.log('🐛 Debug mode enabled');
    }

    disable() {
        localStorage.setItem('gst_debug', 'false');
        this.enabled = false;
        window.GST_CONFIG.DEBUG_MODE = false;
        console.log('🐛 Debug mode disabled');
    }

    log(...args) {
        if (this.enabled) {
            console.log('🔍 DEBUG:', ...args);
        }
    }

    error(...args) {
        if (this.enabled) {
            console.error('❌ DEBUG ERROR:', ...args);
        }
    }

    warn(...args) {
        if (this.enabled) {
            console.warn('⚠️ DEBUG WARNING:', ...args);
        }
    }
}

// =====================================================
// 5. SEARCH ENHANCEMENTS
// =====================================================

class SearchEnhancements {
    constructor() {
        this.recentSearches = this.getRecentSearches();
        this.maxRecentSearches = window.GST_CONFIG.MAX_RECENT_SEARCHES;
    }

    getRecentSearches() {
        try {
            return JSON.parse(localStorage.getItem(window.GST_CONFIG.RECENT_SEARCHES_KEY) || '[]');
        } catch {
            return [];
        }
    }

    addRecentSearch(gstin, companyName) {
        if (!gstin || gstin.length !== 15) return;

        const search = { gstin, companyName, timestamp: Date.now() };
        
        this.recentSearches = this.recentSearches.filter(s => s.gstin !== gstin);
        this.recentSearches.unshift(search);
        this.recentSearches = this.recentSearches.slice(0, this.maxRecentSearches);
        
        localStorage.setItem(window.GST_CONFIG.RECENT_SEARCHES_KEY, JSON.stringify(this.recentSearches));
    }

    getSearchSuggestions(query) {
        if (!query || query.length < 2) return [];

        return this.recentSearches
            .filter(search => 
                search.gstin.toLowerCase().includes(query.toLowerCase()) ||
                (search.companyName && search.companyName.toLowerCase().includes(query.toLowerCase()))
            )
            .slice(0, 5)
            .map(search => ({
                type: 'recent',
                gstin: search.gstin,
                company: search.companyName,
                icon: 'fas fa-history'
            }));
    }
}

// =====================================================
// 6. UTILITY FUNCTIONS
// =====================================================

// Chart.js loader
window.ensureChartJS = function() {
    return new Promise((resolve, reject) => {
        if (window.Chart) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
        script.onload = () => {
            console.log('✅ Chart.js loaded dynamically');
            resolve();
        };
        script.onerror = () => {
            console.error('❌ Failed to load Chart.js');
            reject(new Error('Failed to load Chart.js'));
        };
        document.head.appendChild(script);
    });
};

// Excel export
window.exportToExcel = function() {
    try {
        if (window.notificationManager) {
            window.notificationManager.showInfo('📊 Preparing Excel export...', 3000);
        }
        
        const link = document.createElement('a');
        link.href = '/export/history';
        link.download = `gst_search_history_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        if (window.notificationManager) {
            window.notificationManager.showSuccess('📥 Download started!', 3000);
        }
    } catch (error) {
        console.error('Export error:', error);
        if (window.notificationManager) {
            window.notificationManager.showError('Export failed. Please try again.');
        }
    }
};

// Global debug function
window.debugLog = function(...args) {
    if (window.debugManager && window.debugManager.enabled) {
        console.log('🔍 DEBUG:', ...args);
    }
};

// =====================================================
// 7. OFFLINE SUPPORT
// =====================================================

window.offlineManager = {
    isOnline: navigator.onLine,
    
    init() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            if (window.notificationManager) {
                window.notificationManager.showSuccess('🌐 Connection restored!', 3000);
            }
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            if (window.notificationManager) {
                window.notificationManager.showWarning('📡 You are offline. Some features may be limited.', 5000);
            }
        });
    },
    
    async syncOfflineData() {
        const offlineSearches = JSON.parse(localStorage.getItem('offlineSearches') || '[]');
        
        if (offlineSearches.length > 0) {
            try {
                for (const search of offlineSearches) {
                    await fetch('/api/search/recent', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(search)
                    });
                }
                
                localStorage.removeItem('offlineSearches');
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`📤 Synced ${offlineSearches.length} offline searches`);
                }
            } catch (error) {
                console.error('Sync failed:', error);
            }
        }
    }
};

// =====================================================
// 8. ERROR BOUNDARY
// =====================================================

window.errorBoundary = {
    lastErrorTime: 0,
    
    init() {
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'JavaScript Error');
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'Unhandled Promise Rejection');
            event.preventDefault();
        });
    },
    
    handleError(error, type) {
        console.error(`${type}:`, error);
        
        if (!this.lastErrorTime || Date.now() - this.lastErrorTime > 5000) {
            if (window.notificationManager) {
                window.notificationManager.showError(
                    '⚠️ Something went wrong. If this persists, please refresh the page.',
                    8000
                );
            }
            this.lastErrorTime = Date.now();
        }
        
        if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            this.logErrorToServer(error, type);
        }
    },
    
    async logErrorToServer(error, type) {
        try {
            await fetch('/api/system/error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type,
                    message: error.message || String(error),
                    stack: error.stack,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (logError) {
            console.warn('Failed to log error to server:', logError);
        }
    }
};

// =====================================================
// 9. ACCESSIBILITY MANAGER
// =====================================================

window.accessibilityManager = {
    init() {
        this.setupKeyboardNavigation();
        this.setupScreenReaderSupport();
        this.setupFocusManagement();
    },
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (window.modalManager) {
                    window.modalManager.closeAllModals();
                }
                
                const activeDropdowns = document.querySelectorAll('.user__dropdown.active');
                activeDropdowns.forEach(dropdown => {
                    dropdown.classList.remove('active');
                    const trigger = document.querySelector('.user__trigger.active');
                    if (trigger) {
                        trigger.classList.remove('active');
                        trigger.focus();
                    }
                });
            }
        });
    },
    
    setupScreenReaderSupport() {
        this.announcer = document.createElement('div');
        this.announcer.setAttribute('aria-live', 'polite');
        this.announcer.setAttribute('aria-atomic', 'true');
        this.announcer.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
        document.body.appendChild(this.announcer);
    },
    
    announce(message) {
        if (this.announcer) {
            this.announcer.textContent = message;
        }
    },
    
    setupFocusManagement() {
        document.addEventListener('keydown', () => {
            document.body.classList.add('keyboard-navigation');
        });
        
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }
};

// =====================================================
// 10. INITIALIZATION
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize core managers
    window.notificationManager = new NotificationManager();
    window.modalManager = new ModalManager();
    window.themeManager = new ThemeManager();
    window.debugManager = new DebugManager();
    window.searchEnhancements = new SearchEnhancements();

    // Initialize utility managers
    window.offlineManager.init();
    window.errorBoundary.init();
    window.accessibilityManager.init();

    console.log('✅ Core JavaScript framework initialized');

    // Show welcome notification on first visit
    if (!localStorage.getItem('welcomeShown')) {
        setTimeout(() => {
            window.notificationManager.showSuccess('🎉 Welcome to GST Intelligence Platform!', 5000);
            localStorage.setItem('welcomeShown', 'true');
        }, 1000);
    }
});

// =====================================================
// 11. GLOBAL EXPORTS
// =====================================================

window.GST_MANAGERS = {
    notification: () => window.notificationManager,
    modal: () => window.modalManager,
    theme: () => window.themeManager,
    debug: () => window.debugManager,
    search: () => window.searchEnhancements
};

// PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('✅ Service Worker registered:', registration);
            
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        if (window.notificationManager) {
                            window.notificationManager.showInfo(
                                '🔄 New version available! <button onclick="location.reload()" style="background:var(--accent-primary);color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;margin-left:0.5rem;cursor:pointer;">Update</button>', 
                                10000
                            );
                        }
                    }
                });
            });
        } catch (error) {
            console.log('❌ Service Worker registration failed:', error);
        }
    });
}

// PWA installation prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    setTimeout(() => {
        if (window.notificationManager && !localStorage.getItem('pwa-install-dismissed')) {
            window.notificationManager.show(
                '📱 Install GST Intelligence as an app! <button onclick="installPWA()" style="background:var(--accent-primary);color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;margin-left:0.5rem;cursor:pointer;">Install</button> <button onclick="dismissPWAPrompt()" style="background:transparent;color:var(--text-secondary);border:none;padding:0.25rem;cursor:pointer;">×</button>',
                'info',
                15000
            );
        }
    }, 5000);
});

window.installPWA = async function() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`PWA install ${outcome}`);
        deferredPrompt = null;
    }
};

window.dismissPWAPrompt = function() {
    localStorage.setItem('pwa-install-dismissed', 'true');
    // Close notification automatically handled by notification manager
};

console.log('🎉 GST Intelligence Core Framework Loaded Successfully!');