
// =====================================================
// GST Intelligence Platform - Core Application Module
// =====================================================

'use strict';

class GSTPlatformCore {
    constructor() {
        this.version = '2.0.0';
        this.modules = new Map();
        this.eventBus = new EventTarget();
        this.init();
    }

    init() {
        console.log('🚀 GST Platform Core initialized');
        this.initializeModules();

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.onDOMReady());
        } else {
            this.onDOMReady();
        }
    }

    initializeModules() {
        // Initialize core modules
        this.modules.set('api', new APIManager());
        this.modules.set('ui', new UIManager());
        this.modules.set('utils', new UtilityManager());
        this.modules.set('performance', new PerformanceManager());
    }

    onDOMReady() {
        console.log('📱 DOM Ready - Initializing GST Platform Core');
        try {
            this.setupGlobalErrorHandler();
            this.setupAPIHandlers();
            this.setupUtilities();
            this.setupModules();
            this.setupPerformanceMonitoring();
            console.log('✅ GST Platform Core Application Loaded Successfully!');
        } catch (error) {
            console.error('❌ Failed to load GST Platform Core', error);
            this.handleError(error);
        }
    }

    setupAPIHandlers() {
        // Setup API handlers
        console.log('🔗 Setting up API handlers');
        this.modules.get('api')?.init();
    }

    setupGlobalErrorHandler() {
        window.addEventListener('error', (event) => {
            console.log('Global error:', event.error);
            this.logError({
                type: 'javascript',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.log('Unhandled promise rejection:', event.reason);
            this.logError({
                type: 'promise',
                message: `Unhandled Promise Rejection: ${event.reason}`,
                stack: event.reason?.stack,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            });
        });
    }

    setupUtilities() {
        // Setup utility functions
        this.modules.get('utils')?.init();
    }

    setupModules() {
        // Setup UI modules
        this.modules.get('ui')?.init();
    }

    setupPerformanceMonitoring() {
        // Setup performance monitoring
        this.modules.get('performance')?.init();
    }

    async logError(errorData) {
        console.log('🚨 Error logged:', errorData);
        try {
            await fetch('/api/system/error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(errorData)
            });
        } catch (e) {
            console.error('Failed to log error to server:', e);
        }
    }

    handleError(error) {
        console.error('Core application error:', error);
        this.logError({
            type: 'core',
            message: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href
        });
    }
}

// API Manager
class APIManager {
    init() {
        console.log('🔗 API Manager initialized');
    }

    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
}

// UI Manager
class UIManager {
    init() {
        console.log('🎨 UI Manager initialized');
        this.setupTooltips();
        this.setupModals();
        this.setupDropdowns();
    }

    setupTooltips() {
        // Tooltip functionality
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', this.showTooltip.bind(this));
            element.addEventListener('mouseleave', this.hideTooltip.bind(this));
        });
    }

    setupModals() {
        // Modal functionality
        document.querySelectorAll('[data-modal]').forEach(trigger => {
            trigger.addEventListener('click', this.openModal.bind(this));
        });
    }

    setupDropdowns() {
        // Dropdown functionality
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            toggle.addEventListener('click', this.toggleDropdown.bind(this));
        });
    }

    showTooltip(event) {
        const element = event.target;
        const text = element.getAttribute('data-tooltip');
        // Implementation for tooltip display
    }

    hideTooltip(event) {
        // Implementation for tooltip hiding
    }

    openModal(event) {
        const modalId = event.target.getAttribute('data-modal');
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
        }
    }

    toggleDropdown(event) {
        const dropdown = event.target.nextElementSibling;
        if (dropdown) {
            dropdown.classList.toggle('active');
        }
    }
}

// Utility Manager
class UtilityManager {
    init() {
        console.log('🛠️ Utility Manager initialized');
    }

    formatCurrency(amount, currency = 'INR') {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('en-IN').format(new Date(date));
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
}

// Performance Manager
class PerformanceManager {
    init() {
        console.log('⚡ Performance Manager initialized');
        this.measurePageLoad();
    }

    measurePageLoad() {
        window.addEventListener('load', () => {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log('Page load time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
        });
    }
}

// Initialize the core application
try {
    window.GSTCore = new GSTPlatformCore();
} catch (error) {
    console.error('Failed to initialize GST Platform Core:', error);
}
