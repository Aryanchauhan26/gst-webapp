// /static/js/missing-globals.js
// Create this file to provide missing global dependencies
// Load this BEFORE other JavaScript files

'use strict';

console.log('🔧 Loading missing globals...');

// Global notification manager
if (!window.notificationManager) {
    window.notificationManager = {
        showSuccess: function(message, duration = 3000) {
            this.showNotification(message, 'success', duration);
        },

        showError: function(message, duration = 5000) {
            this.showNotification(message, 'error', duration);
        },

        showWarning: function(message, duration = 4000) {
            this.showNotification(message, 'warning', duration);
        },

        showInfo: function(message, duration = 3000) {
            this.showNotification(message, 'info', duration);
        },

        showNotification: function(message, type = 'info', duration = 3000) {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10000;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
                max-width: 400px;
                word-wrap: break-word;
            `;

            // Set background color based on type
            const colors = {
                success: '#10b981',
                error: '#ef4444',
                warning: '#f59e0b',
                info: '#3b82f6'
            };
            notification.style.backgroundColor = colors[type] || colors.info;

            notification.textContent = message;

            // Add close button
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '×';
            closeBtn.style.cssText = `
                background: none;
                border: none;
                color: white;
                font-size: 1.2rem;
                margin-left: 0.5rem;
                cursor: pointer;
                opacity: 0.8;
            `;
            closeBtn.onclick = () => this.removeNotification(notification);
            notification.appendChild(closeBtn);

            document.body.appendChild(notification);

            // Show notification
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 100);

            // Auto remove
            setTimeout(() => {
                this.removeNotification(notification);
            }, duration);
        },

        removeNotification: function(notification) {
            if (notification && notification.parentNode) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }
    };
}

// Global utility functions
if (!window.utils) {
    window.utils = {
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        },

        formatNumber: function(num) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
            return num.toString();
        },

        formatCurrency: function(amount, currency = 'INR') {
            return new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: currency
            }).format(amount);
        },

        formatDate: function(date) {
            return new Intl.DateTimeFormat('en-IN').format(new Date(date));
        },

        copyToClipboard: function(text) {
            if (navigator.clipboard) {
                return navigator.clipboard.writeText(text);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return Promise.resolve();
            }
        }
    };
}

// Global event emitter
if (!window.eventBus) {
    window.eventBus = new EventTarget();
}

// Global loading manager
if (!window.loadingManager) {
    window.loadingManager = {
        show: function(message = 'Loading...') {
            this.hide(); // Remove any existing loader

            const loader = document.createElement('div');
            loader.id = 'global-loader';
            loader.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                backdrop-filter: blur(2px);
            `;

            loader.innerHTML = `
                <div style="
                    background: var(--bg-card);
                    padding: 2rem;
                    border-radius: 12px;
                    text-align: center;
                    color: var(--text-primary);
                ">
                    <div style="
                        width: 40px;
                        height: 40px;
                        border: 3px solid var(--border-color);
                        border-top: 3px solid var(--accent-primary);
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 1rem;
                    "></div>
                    <div>${message}</div>
                </div>
            `;

            // Add spin animation if not exists
            if (!document.getElementById('loader-styles')) {
                const style = document.createElement('style');
                style.id = 'loader-styles';
                style.textContent = `
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `;
                document.head.appendChild(style);
            }

            document.body.appendChild(loader);
        },

        hide: function() {
            const loader = document.getElementById('global-loader');
            if (loader) {
                loader.remove();
            }
        }
    };
}

// Global form validation helpers
if (!window.validation) {
    window.validation = {
        validateGSTIN: function(gstin) {
            const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
            return pattern.test(gstin?.trim().toUpperCase());
        },

        validateEmail: function(email) {
            const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return pattern.test(email?.trim());
        },

        validateMobile: function(mobile) {
            const pattern = /^[6-9][0-9]{9}$/;
            return pattern.test(mobile?.trim());
        },

        validatePAN: function(pan) {
            const pattern = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
            return pattern.test(pan?.trim().toUpperCase());
        }
    };
}

// Global bridge functions to connect modules
window.bridges = {
    establish: function() {
        // Bridge between different modules
        console.log('🔗 Global bridges established');
    }
};

// Initialize bridges
window.bridges.establish();

console.log('✅ Missing globals loaded successfully!');

// Log error to server
fetch('/api/system/error', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: 'Example error message',
            stack: 'Example stack trace'
        })
    })
    .then(response => {
        if (!response.ok) {
            console.error('Failed to log error to server:', response.status);
        }
    })
    .catch(error => {
        console.error('Error logging error to server:', error);
    });