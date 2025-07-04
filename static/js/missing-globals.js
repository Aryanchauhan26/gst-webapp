// /static/js/missing-globals.js
// Create this file to provide missing global dependencies
// Load this BEFORE other JavaScript files

'use strict';

console.log('🔧 Loading missing globals...');

// =============================================================================
// 1. NOTIFICATION MANAGER (Referenced by multiple files)
// =============================================================================
window.notificationManager = {
    notifications: [],
    
    show(message, type = 'info', duration = 5000) {
        const notification = this.create(message, type, duration);
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('notification-show'), 100);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(notification), duration);
        }
        
        return notification;
    },
    
    create(message, type, duration) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getIcon(type)}"></i>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="window.notificationManager.remove(this.parentElement.parentElement)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add styles if not present
        this.ensureStyles();
        
        this.notifications.push(notification);
        return notification;
    },
    
    remove(notification) {
        if (!notification || !notification.parentNode) return;
        
        notification.classList.add('notification-hide');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            const index = this.notifications.indexOf(notification);
            if (index > -1) {
                this.notifications.splice(index, 1);
            }
        }, 300);
    },
    
    getIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle', 
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    ensureStyles() {
        if (document.getElementById('notification-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                min-width: 300px;
                max-width: 500px;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
                transform: translateX(100%);
                opacity: 0;
                transition: all 0.3s ease;
                margin-bottom: 10px;
            }
            
            .notification-show {
                transform: translateX(0);
                opacity: 1;
            }
            
            .notification-hide {
                transform: translateX(100%);
                opacity: 0;
            }
            
            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px;
            }
            
            .notification-message {
                flex: 1;
                color: var(--text-primary);
                font-size: 14px;
                line-height: 1.4;
            }
            
            .notification-close {
                background: none;
                border: none;
                cursor: pointer;
                color: var(--text-secondary);
                padding: 4px;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .notification-close:hover {
                background: var(--bg-hover);
                color: var(--text-primary);
            }
            
            .notification-success {
                border-left: 4px solid var(--success);
            }
            
            .notification-error {
                border-left: 4px solid var(--error);
            }
            
            .notification-warning {
                border-left: 4px solid var(--warning);
            }
            
            .notification-info {
                border-left: 4px solid var(--accent-primary);
            }
            
            .notification i {
                font-size: 18px;
            }
            
            .notification-success i { color: var(--success); }
            .notification-error i { color: var(--error); }
            .notification-warning i { color: var(--warning); }
            .notification-info i { color: var(--accent-primary); }
        `;
        document.head.appendChild(style);
    },
    
    // Convenience methods
    showSuccess: function(message, duration) { return this.show(message, 'success', duration); },
    showError: function(message, duration) { return this.show(message, 'error', duration); },
    showWarning: function(message, duration) { return this.show(message, 'warning', duration); },
    showInfo: function(message, duration) { return this.show(message, 'info', duration); },
    
    clear() {
        this.notifications.forEach(n => this.remove(n));
    }
};

// =============================================================================
// 2. CHART.JS LOADER (Centralized to prevent conflicts)
// =============================================================================
window.ensureChartJS = function() {
    return new Promise((resolve, reject) => {
        if (window.Chart) {
            resolve(window.Chart);
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.min.js';
        script.onload = () => {
            console.log('✅ Chart.js loaded successfully');
            
            // Configure defaults
            if (window.Chart) {
                window.Chart.defaults.color = 'var(--text-secondary)';
                window.Chart.defaults.borderColor = 'var(--border-color)';
                window.Chart.defaults.responsive = true;
                window.Chart.defaults.maintainAspectRatio = false;
            }
            
            resolve(window.Chart);
        };
        script.onerror = () => {
            console.error('❌ Failed to load Chart.js');
            reject(new Error('Failed to load Chart.js'));
        };
        document.head.appendChild(script);
    });
};

// =============================================================================
// 3. GLOBAL CONFIGURATION
// =============================================================================
window.GST_CONFIG = {
    API_TIMEOUT: 30000,
    MAX_RECENT_SEARCHES: 10,
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
    DEBUG_MODE: localStorage.getItem('gst_debug') === 'true',
    THEME_TRANSITION_DURATION: 300,
    CACHE_DURATION: 5 * 60 * 1000 // 5 minutes
};

// =============================================================================
// 4. BRIDGE TO EXISTING MANAGERS
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for other modules to load
    setTimeout(() => {
        // Bridge to existing theme manager
        if (window.GSTPlatform?.themeManager && !window.themeManager) {
            window.themeManager = window.GSTPlatform.themeManager;
        }
        
        // Bridge to existing modal manager  
        if (window.GSTPlatform?.modalManager && !window.modalManager) {
            window.modalManager = window.GSTPlatform.modalManager;
        }
        
        // Bridge to existing debug manager
        if (window.GSTPlatform?.debugManager && !window.debugManager) {
            window.debugManager = window.GSTPlatform.debugManager;
        }
        
        // Fallback theme manager if none exists
        if (!window.themeManager) {
            window.themeManager = {
                toggleTheme: function() {
                    const html = document.documentElement;
                    const currentTheme = html.getAttribute('data-theme');
                    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                    html.setAttribute('data-theme', newTheme);
                    localStorage.setItem('gst-theme', newTheme);
                    console.log(`Theme switched to: ${newTheme}`);
                }
            };
        }
        
        console.log('🔗 Global bridges established');
    }, 100);
});

// =============================================================================
// 5. GLOBAL UTILITY FUNCTIONS
// =============================================================================
window.debugLog = function(...args) {
    if (window.GST_CONFIG.DEBUG_MODE) {
        console.log('🔍 DEBUG:', ...args);
    }
};

window.showError = function(message, duration = 5000) {
    return window.notificationManager.showError(message, duration);
};

window.showSuccess = function(message, duration = 3000) {
    return window.notificationManager.showSuccess(message, duration);
};

// =============================================================================
// 6. ERROR HANDLING
// =============================================================================
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    
    // Don't spam notifications
    const now = Date.now();
    if (!window.lastErrorNotification || now - window.lastErrorNotification > 5000) {
        window.notificationManager.showError('Something went wrong. Please refresh if issues persist.');
        window.lastErrorNotification = now;
    }
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    event.preventDefault(); // Prevent console spam
});

console.log('✅ Missing globals loaded successfully!');

// Export for verification
window.GST_GLOBALS_LOADED = true;