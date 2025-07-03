// =============================================================================
// GST Intelligence Platform - Consolidated Error Handling System
// Version: 2.1.0 - Removes duplicates and improves UX
// =============================================================================

class ErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.maxQueueSize = 50;
        this.retryDelays = [1000, 3000, 5000, 10000]; // Progressive delays
        this.isOnline = navigator.onLine;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Global error handlers
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'javascript',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: Date.now()
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'promise',
                message: event.reason?.message || 'Unhandled promise rejection',
                stack: event.reason?.stack,
                timestamp: Date.now()
            });
        });

        // Network status monitoring
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.flushErrorQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }

    handleError(errorInfo) {
        console.error('Error captured:', errorInfo);
        
        // Show user-friendly notification
        this.showUserNotification(errorInfo);
        
        // Queue for server reporting
        this.queueError(errorInfo);
        
        // Send to server if online
        if (this.isOnline) {
            this.sendToServer(errorInfo);
        }
    }

    showUserNotification(errorInfo) {
        const message = this.getFriendlyMessage(errorInfo);
        
        // Use notification manager if available
        if (window.notificationManager) {
            window.notificationManager.showError(message);
        } else {
            // Fallback to simple alert
            console.warn('Notification manager not available, using fallback');
            this.showFallbackNotification(message);
        }
    }

    showFallbackNotification(message) {
        // Create a simple notification element
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Add styles if not present
        if (!document.getElementById('error-notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'error-notification-styles';
            styles.textContent = `
                .error-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #ff4444;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 10000;
                    max-width: 400px;
                    animation: slideInRight 0.3s ease-out;
                }
                .notification-content {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .notification-content button {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                }
                @keyframes slideInRight {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getFriendlyMessage(errorInfo) {
        const errorMap = {
            'NetworkError': '🌐 Network connection issue. Please check your internet.',
            'TypeError': '⚠️ Something went wrong. Please refresh the page.',
            'ReferenceError': '⚠️ Feature temporarily unavailable.',
            'SyntaxError': '⚠️ Please refresh the page and try again.',
            'Failed to fetch': '🌐 Connection failed. Please try again.',
            'Load failed': '📡 Failed to load resource. Please refresh.',
            'Script error': '⚠️ An error occurred. Please refresh the page.'
        };

        const message = errorInfo.message || '';
        
        // Check for specific error patterns
        for (const [pattern, friendlyMsg] of Object.entries(errorMap)) {
            if (message.includes(pattern)) {
                return friendlyMsg;
            }
        }

        // Check error type
        if (errorInfo.type === 'promise') {
            return '⚠️ Something went wrong. Please try again.';
        }

        return '⚠️ An unexpected error occurred. Please refresh the page if the problem persists.';
    }

    queueError(errorInfo) {
        this.errorQueue.push({
            ...errorInfo,
            id: Date.now() + Math.random().toString(36).substr(2, 9),
            retryCount: 0
        });
        
        // Limit queue size
        if (this.errorQueue.length > this.maxQueueSize) {
            this.errorQueue = this.errorQueue.slice(-this.maxQueueSize);
        }
    }

    async sendToServer(errorInfo) {
        try {
            const response = await fetch('/api/system/error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...errorInfo,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });

            if (response.ok) {
                // Remove from queue if sent successfully
                this.errorQueue = this.errorQueue.filter(e => e.id !== errorInfo.id);
            } else {
                throw new Error(`Server responded with ${response.status}`);
            }
        } catch (error) {
            console.warn('Failed to send error to server:', error);
            // Increment retry count
            const queuedError = this.errorQueue.find(e => e.id === errorInfo.id);
            if (queuedError) {
                queuedError.retryCount++;
            }
        }
    }

    async flushErrorQueue() {
        if (!this.isOnline || this.errorQueue.length === 0) return;

        console.log(`📤 Flushing ${this.errorQueue.length} queued errors...`);
        
        const queue = [...this.errorQueue];
        for (const errorInfo of queue) {
            if (errorInfo.retryCount < this.retryDelays.length) {
                await this.sendToServer(errorInfo);
                // Wait between requests to avoid overwhelming the server
                await new Promise(resolve => setTimeout(resolve, 100));
            } else {
                // Remove errors that have failed too many times
                this.errorQueue = this.errorQueue.filter(e => e.id !== errorInfo.id);
            }
        }
    }
}

// =============================================================================
// API ERROR HANDLING
// =============================================================================

class APIErrorHandler {
    constructor() {
        this.setupInterceptors();
    }

    setupInterceptors() {
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                if (!response.ok) {
                    await this.handleAPIError(response, args[0]);
                }
                
                return response;
            } catch (error) {
                this.handleNetworkError(error, args[0]);
                throw error;
            }
        };
    }

    async handleAPIError(response, request) {
        const url = typeof request === 'string' ? request : request.url;
        
        try {
            const errorData = await response.json();
            
            window.errorHandler?.handleError({
                type: 'api',
                message: errorData.error || `API Error: ${response.status}`,
                url: url,
                status: response.status,
                timestamp: Date.now()
            });
            
        } catch (parseError) {
            window.errorHandler?.handleError({
                type: 'api',
                message: `API Error: ${response.status} ${response.statusText}`,
                url: url,
                status: response.status,
                timestamp: Date.now()
            });
        }
    }

    handleNetworkError(error, request) {
        const url = typeof request === 'string' ? request : request.url;
        
        window.errorHandler?.handleError({
            type: 'network',
            message: error.message || 'Network error',
            url: url,
            timestamp: Date.now()
        });
    }
}

// =============================================================================
// PERFORMANCE MONITORING
// =============================================================================

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            apiResponseTimes: [],
            resourceLoadTimes: []
        };
        this.setupMonitoring();
    }

    setupMonitoring() {
        // Monitor page load time
        window.addEventListener('load', () => {
            const loadTime = performance.now();
            this.metrics.pageLoadTime = loadTime;
            
            if (loadTime > 5000) { // More than 5 seconds
                window.errorHandler?.handleError({
                    type: 'performance',
                    message: `Slow page load: ${Math.round(loadTime)}ms`,
                    timestamp: Date.now()
                });
            }
        });

        // Monitor API response times
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                this.metrics.apiResponseTimes.push({
                    url: args[0],
                    duration: duration,
                    timestamp: Date.now()
                });
                
                // Keep only last 100 measurements
                if (this.metrics.apiResponseTimes.length > 100) {
                    this.metrics.apiResponseTimes = this.metrics.apiResponseTimes.slice(-100);
                }
                
                // Alert on slow API calls
                if (duration > 10000) { // More than 10 seconds
                    window.errorHandler?.handleError({
                        type: 'performance',
                        message: `Slow API response: ${Math.round(duration)}ms for ${args[0]}`,
                        timestamp: Date.now()
                    });
                }
                
                return response;
            } catch (error) {
                throw error;
            }
        };
    }

    getMetrics() {
        return {
            ...this.metrics,
            averageApiResponseTime: this.metrics.apiResponseTimes.length > 0 
                ? this.metrics.apiResponseTimes.reduce((sum, item) => sum + item.duration, 0) / this.metrics.apiResponseTimes.length
                : 0
        };
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Initialize error handling system
document.addEventListener('DOMContentLoaded', () => {
    window.errorHandler = new ErrorHandler();
    window.apiErrorHandler = new APIErrorHandler();
    window.performanceMonitor = new PerformanceMonitor();
    
    console.log('✅ Error handling system initialized');
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ErrorHandler, APIErrorHandler, PerformanceMonitor };
}