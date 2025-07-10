// GST Intelligence Platform - Main Application JS (FIXED & INTEGRATED)
// =====================================================

'use strict';

// Global application state
window.GST_APP = {
    version: '2.0.0',
    initialized: false,
    modules: {},
    config: {
        API_BASE_URL: '/api',
        DEBOUNCE_DELAY: 300,
        CACHE_TTL: 5 * 60 * 1000, // 5 minutes
        MAX_RETRIES: 3
    }
};

// =====================================================
// ENSURE DEPENDENCIES ARE AVAILABLE
// =====================================================
function ensureDependencies() {
    // If modules aren't available from app-modules.js, create basic fallbacks
    if (typeof APIModule === 'undefined') {
        window.APIModule = class {
            async init() { console.log('📡 Basic API module loaded'); }
            async request(url, options = {}) {
                const response = await fetch(url, options);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            }
            async get(endpoint) { return this.request(endpoint); }
            async post(endpoint, data) { 
                return this.request(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
            }
            cleanup() {}
        };
    }

    if (typeof UIModule === 'undefined') {
        window.UIModule = class {
            async init() { console.log('🎨 Basic UI module loaded'); }
            cleanup() {}
        };
    }

    if (typeof AuthModule === 'undefined') {
        window.AuthModule = class {
            async init() { console.log('🔐 Basic Auth module loaded'); }
            cleanup() {}
        };
    }

    if (typeof NavigationModule === 'undefined') {
        window.NavigationModule = class {
            async init() { console.log('🧭 Basic Navigation module loaded'); }
            cleanup() {}
        };
    }

    if (typeof ProfileModule === 'undefined') {
        window.ProfileModule = class {
            async init() { console.log('👤 Basic Profile module loaded'); }
            cleanup() {}
        };
    }

    if (typeof LoansModule === 'undefined') {
        window.LoansModule = class {
            async init() { console.log('💰 Basic Loans module loaded'); }
            cleanup() {}
        };
    }
}

// =====================================================
// CORE APPLICATION CLASS
// =====================================================

class GSTIntelligenceApp {
    constructor() {
        this.modules = new Map();
        this.eventBus = new EventTarget();
        this.cache = new Map();
        this.initialized = false;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.onDOMReady = this.onDOMReady.bind(this);
    }

    async init() {
        if (this.initialized) return;
        
        try {
            console.log('🚀 Initializing GST Intelligence Platform...');
            
            // Ensure dependencies are available
            ensureDependencies();
            
            // Initialize core modules
            await this.initializeModules();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize theme
            this.initializeTheme();
            
            // Initialize UI components
            this.initializeUI();
            
            // Mark as initialized
            this.initialized = true;
            window.GST_APP.initialized = true;
            
            console.log('✅ GST Intelligence Platform initialized successfully');
            
            // Emit initialization event
            this.eventBus.dispatchEvent(new CustomEvent('app:initialized'));
            
        } catch (error) {
            console.error('❌ Failed to initialize GST Intelligence Platform:', error);
            this.handleInitializationError(error);
        }
    }

    async initializeModules() {
        // Initialize API module
        this.modules.set('api', new APIModule());
        
        // Initialize UI module
        this.modules.set('ui', new UIModule());
        
        // Initialize Authentication module
        this.modules.set('auth', new AuthModule());
        
        // Initialize Navigation module
        this.modules.set('nav', new NavigationModule());
        
        // Initialize Profile module
        this.modules.set('profile', new ProfileModule());
        
        // Initialize Loans module if on loans page
        if (window.location.pathname === '/loans') {
            this.modules.set('loans', new LoansModule());
        }
        
        // Initialize each module
        for (const [name, module] of this.modules) {
            try {
                if (module.init) {
                    await module.init();
                }
                console.log(`✅ ${name} module initialized`);
            } catch (error) {
                console.error(`❌ Failed to initialize ${name} module:`, error);
            }
        }
    }

    setupEventListeners() {
        // Global error handler
        window.addEventListener('error', this.handleGlobalError.bind(this));
        window.addEventListener('unhandledrejection', this.handleUnhandledRejection.bind(this));
        
        // Visibility change handler
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Beforeunload handler
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme');
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        const theme = savedTheme || systemTheme;
        
        document.documentElement.setAttribute('data-theme', theme);
        
        // Update theme toggle indicator
        const indicator = document.getElementById('theme-indicator-icon');
        if (indicator) {
            indicator.className = theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }

    initializeUI() {
        // Initialize dropdowns
        this.initializeDropdowns();
        
        // Initialize mobile navigation
        this.initializeMobileNavigation();
        
        // Initialize forms
        this.initializeForms();
        
        // Initialize tooltips
        this.initializeTooltips();
        
        // Initialize modals
        this.initializeModals();
    }

    initializeDropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown');
        
        dropdowns.forEach(dropdown => {
            const trigger = dropdown.querySelector('.dropdown-toggle, .user__trigger');
            const menu = dropdown.querySelector('.dropdown-menu');
            
            if (!trigger || !menu) return;
            
            // Toggle dropdown on click
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown(dropdown);
            });
            
            // Close dropdown on outside click
            document.addEventListener('click', (e) => {
                if (!dropdown.contains(e.target)) {
                    this.closeDropdown(dropdown);
                }
            });
            
            // Handle keyboard navigation
            menu.addEventListener('keydown', (e) => {
                this.handleDropdownKeyboard(e, menu);
            });
        });
    }

    toggleDropdown(dropdown) {
        const isActive = dropdown.classList.contains('active');
        
        // Close all other dropdowns
        document.querySelectorAll('.dropdown.active').forEach(d => {
            if (d !== dropdown) {
                this.closeDropdown(d);
            }
        });
        
        // Toggle current dropdown
        if (isActive) {
            this.closeDropdown(dropdown);
        } else {
            this.openDropdown(dropdown);
        }
    }

    openDropdown(dropdown) {
        dropdown.classList.add('active');
        
        const trigger = dropdown.querySelector('.dropdown-toggle, .user__trigger');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (trigger) {
            trigger.setAttribute('aria-expanded', 'true');
        }
        
        if (menu) {
            // Focus first focusable element
            const firstFocusable = menu.querySelector('a, button, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 100);
            }
        }
    }

    closeDropdown(dropdown) {
        dropdown.classList.remove('active');
        
        const trigger = dropdown.querySelector('.dropdown-toggle, .user__trigger');
        if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
        }
    }

    handleDropdownKeyboard(e, menu) {
        const items = menu.querySelectorAll('a, button, [tabindex]:not([tabindex="-1"])');
        const currentIndex = Array.from(items).indexOf(document.activeElement);
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                items[nextIndex].focus();
                break;
            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                items[prevIndex].focus();
                break;
            case 'Enter':
            case ' ':
                e.preventDefault();
                document.activeElement.click();
                break;
            case 'Escape':
                e.preventDefault();
                const dropdown = menu.closest('.dropdown');
                this.closeDropdown(dropdown);
                const trigger = dropdown.querySelector('.dropdown-toggle, .user__trigger');
                if (trigger) trigger.focus();
                break;
        }
    }

    initializeMobileNavigation() {
        const toggle = document.getElementById('mobile-nav-toggle');
        const nav = document.getElementById('main-nav');
        
        if (!toggle || !nav) return;
        
        toggle.addEventListener('click', () => {
            const isOpen = nav.classList.contains('mobile-nav-open');
            
            if (isOpen) {
                nav.classList.remove('mobile-nav-open');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
                toggle.setAttribute('aria-label', 'Open navigation');
            } else {
                nav.classList.add('mobile-nav-open');
                toggle.innerHTML = '<i class="fas fa-times"></i>';
                toggle.setAttribute('aria-label', 'Close navigation');
            }
        });
        
        // Close mobile nav when clicking nav links
        nav.addEventListener('click', (e) => {
            if (e.target.matches('.nav__link')) {
                nav.classList.remove('mobile-nav-open');
                toggle.innerHTML = '<i class="fas fa-bars"></i>';
                toggle.setAttribute('aria-label', 'Open navigation');
            }
        });
    }

    initializeForms() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            // Add loading state on submit
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                }
            });
            
            // Add real-time validation
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(input);
                });
            });
        });
    }

    validateField(field) {
        const value = field.value.trim();
        const type = field.type;
        let isValid = true;
        let errorMessage = '';
        
        // Basic validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        } else if (type === 'email' && value && !this.isValidEmail(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address';
        } else if (field.name === 'mobile' && value && !this.isValidMobile(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid mobile number';
        }
        
        // Show/hide error message
        this.showFieldError(field, isValid ? null : errorMessage);
        
        return isValid;
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    isValidMobile(mobile) {
        return /^[6-9]\d{9}$/.test(mobile);
    }

    showFieldError(field, message) {
        // Remove existing error
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error if message provided
        if (message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            errorDiv.style.color = 'var(--error)';
            errorDiv.style.fontSize = '0.875rem';
            errorDiv.style.marginTop = '0.25rem';
            errorDiv.textContent = message;
            
            field.parentNode.appendChild(errorDiv);
            field.style.borderColor = 'var(--error)';
        } else {
            field.style.borderColor = '';
        }
    }

    initializeTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target);
            });
            
            element.addEventListener('mouseleave', (e) => {
                this.hideTooltip(e.target);
            });
        });
    }

    showTooltip(element) {
        const text = element.getAttribute('data-tooltip');
        if (!text) return;
        
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: var(--bg-card);
            color: var(--text-primary);
            padding: 0.5rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            pointer-events: none;
            white-space: nowrap;
        `;
        
        document.body.appendChild(tooltip);
        
        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
        
        // Store reference for cleanup
        element._tooltip = tooltip;
    }

    hideTooltip(element) {
        if (element._tooltip) {
            element._tooltip.remove();
            element._tooltip = null;
        }
    }

    initializeModals() {
        // Modal triggers
        const modalTriggers = document.querySelectorAll('[data-modal]');
        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = trigger.getAttribute('data-modal');
                this.openModal(modalId);
            });
        });
        
        // Modal close buttons
        const modalCloses = document.querySelectorAll('.modal-close, [data-modal-close]');
        modalCloses.forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.closeModal(closeBtn.closest('.modal'));
            });
        });
        
        // Close modal on outside click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
        
        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.active');
                if (openModal) {
                    this.closeModal(openModal);
                }
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Focus first focusable element
        const firstFocusable = modal.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }

    closeModal(modal) {
        if (!modal) return;
        
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Theme toggle function
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update theme indicator
        const indicator = document.getElementById('theme-indicator-icon');
        if (indicator) {
            indicator.className = newTheme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }

        // Emit theme change event
        this.eventBus.dispatchEvent(new CustomEvent('theme:changed', {
            detail: { theme: newTheme }
        }));
    }

    // Error handlers
    handleGlobalError(event) {
        console.error('Global error:', event.error);
        this.showNotification('An error occurred. Please try again.', 'error');
    }

    handleUnhandledRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        this.showNotification('A network error occurred. Please check your connection.', 'error');
    }

    handleVisibilityChange() {
        if (document.visibilityState === 'visible') {
            // Page became visible - could refresh data
            this.eventBus.dispatchEvent(new CustomEvent('page:visible'));
        } else {
            // Page became hidden
            this.eventBus.dispatchEvent(new CustomEvent('page:hidden'));
        }
    }

    handleBeforeUnload() {
        // Cleanup before page unload
        this.cleanup();
    }

    handleInitializationError(error) {
        console.error('Initialization error:', error);
        
        // Show user-friendly error message
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--error);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            z-index: 10000;
            max-width: 400px;
        `;
        errorDiv.innerHTML = `
            <strong>Initialization Error</strong><br>
            The application failed to load properly. Please refresh the page.
        `;
        
        document.body.appendChild(errorDiv);
        
        // Remove error after 10 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 10000);
    }

    // Notification system - Use existing notificationManager if available
    showNotification(message, type = 'info', duration = 5000) {
        // Use existing notification manager if available
        if (window.notificationManager && window.notificationManager.show) {
            window.notificationManager.show(message, type, duration);
            return;
        }

        // Fallback notification system
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--bg-card);
            color: var(--text-primary);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid var(--${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'});
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            max-width: 400px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="margin-left: auto; background: none; border: none; color: var(--text-muted); cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, duration);
    }

    // Cleanup function
    cleanup() {
        // Clear caches
        this.cache.clear();
        
        // Cleanup modules
        for (const [name, module] of this.modules) {
            if (module.cleanup) {
                module.cleanup();
            }
        }
    }

    // Utility methods
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

    formatCurrency(amount, currency = 'INR') {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        return new Intl.DateTimeFormat('en-IN', { ...defaultOptions, ...options }).format(new Date(date));
    }

    // Module getter
    getModule(name) {
        return this.modules.get(name);
    }
}

// =====================================================
// INITIALIZE APPLICATION
// =====================================================

// Create global app instance
window.gstApp = new GSTIntelligenceApp();

// Make theme toggle globally available
window.toggleTheme = () => window.gstApp.toggleTheme();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gstApp.init();
    });
} else {
    window.gstApp.init();
}

// =====================================================
// BACKWARD COMPATIBILITY
// =====================================================

// Export for backward compatibility
window.GST_APP.modules = window.gstApp.modules;
window.GST_APP.showNotification = (message, type, duration) => window.gstApp.showNotification(message, type, duration);
window.GST_APP.formatCurrency = (amount, currency) => window.gstApp.formatCurrency(amount, currency);
window.GST_APP.formatDate = (date, options) => window.gstApp.formatDate(date, options);

console.log('📱 GST Intelligence Platform JS loaded successfully');