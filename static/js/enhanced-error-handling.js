// Enhanced Error Handling & User Experience
'use strict';

class EnhancedErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.isOnline = navigator.onLine;
        this.maxQueueSize = 50;
        this.init();
    }

    init() {
        // Global error handlers
        window.addEventListener('error', this.handleJavaScriptError.bind(this));
        window.addEventListener('unhandledrejection', this.handlePromiseRejection.bind(this));
        
        // Network status monitoring
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.flushErrorQueue();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });

        console.log('✅ Enhanced error handler initialized');
    }

    handleJavaScriptError(event) {
        const errorInfo = {
            type: 'JavaScript Error',
            message: event.message || 'Unknown error',
            filename: event.filename || 'unknown',
            lineno: event.lineno || 0,
            colno: event.colno || 0,
            stack: event.error?.stack || 'No stack trace',
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString()
        };

        this.processError(errorInfo);
    }

    handlePromiseRejection(event) {
        const errorInfo = {
            type: 'Unhandled Promise Rejection',
            message: event.reason?.message || String(event.reason) || 'Unknown rejection',
            stack: event.reason?.stack || 'No stack trace',
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString()
        };

        this.processError(errorInfo);
        event.preventDefault(); // Prevent console logging
    }

    processError(errorInfo) {
        // Log to console for development
        console.error('🚨 Error captured:', errorInfo);

        // Show user-friendly notification
        this.showUserNotification(errorInfo);

        // Queue for server logging
        this.queueError(errorInfo);

        // Attempt immediate send if online
        if (this.isOnline) {
            this.sendToServer(errorInfo);
        }
    }

    showUserNotification(errorInfo) {
        // Don't spam user with too many error notifications
        const recentErrors = this.errorQueue.filter(
            err => new Date() - new Date(err.timestamp) < 10000
        );

        if (recentErrors.length > 3) return;

        if (window.notificationManager) {
            const message = this.getFriendlyErrorMessage(errorInfo);
            window.notificationManager.showError(message, 8000);
        }
    }

    getFriendlyErrorMessage(errorInfo) {
        // Map technical errors to user-friendly messages
        const errorMap = {
            'Failed to fetch': '🌐 Network connection issue. Please check your internet.',
            'NetworkError': '🌐 Network error occurred. Please try again.',
            'TypeError': '⚠️ Something went wrong. Please refresh the page.',
            'ReferenceError': '⚠️ Feature temporarily unavailable.',
            'SyntaxError': '⚠️ Please refresh the page and try again.'
        };

        const message = errorInfo.message || '';
        for (const [error, friendlyMsg] of Object.entries(errorMap)) {
            if (message.includes(error)) {
                return friendlyMsg;
            }
        }

        return '⚠️ An unexpected error occurred. Please try refreshing the page.';
    }

    queueError(errorInfo) {
        this.errorQueue.push(errorInfo);
        
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
                body: JSON.stringify(errorInfo)
            });

            if (response.ok) {
                // Remove from queue if sent successfully
                const index = this.errorQueue.findIndex(e => e.timestamp === errorInfo.timestamp);
                if (index > -1) {
                    this.errorQueue.splice(index, 1);
                }
            }
        } catch (sendError) {
            console.warn('Failed to send error to server:', sendError);
        }
    }

    async flushErrorQueue() {
        const queue = [...this.errorQueue];
        for (const errorInfo of queue) {
            await this.sendToServer(errorInfo);
        }
    }
}

// Initialize enhanced error handler
window.enhancedErrorHandler = new EnhancedErrorHandler();