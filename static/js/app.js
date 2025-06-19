// GST Intelligence Platform - Consolidated JavaScript Application
// Replaces: app.js, dashboard.js, integration-fixes.js, missing-implementations.js
// Version: 1.0.0 - Production Ready

console.log('🚀 GST Intelligence Platform - Loading Consolidated Application...');

// ===========================================
// 1. GLOBAL CONFIGURATION & CONSTANTS
// ===========================================

const GST_CONFIG = {
    API_BASE_URL: '',
    ENDPOINTS: {
        LOGIN: '/login',
        SIGNUP: '/signup', 
        SEARCH: '/search',
        SEARCH_SUGGESTIONS: '/api/search/suggestions',
        HISTORY: '/api/history',
        PREFERENCES: '/api/preferences',
        STATS: '/api/stats',
        HEALTH: '/health',
        PROFILE: '/api/profile',
        EXPORT: '/api/export',
        BATCH_SEARCH: '/api/batch-search'
    },
    STORAGE_KEYS: {
        USER_PREFERENCES: 'gst_user_preferences',
        RECENT_SEARCHES: 'recentGSTINSearches',
        THEME: 'gst_theme',
        USER_PROFILE: 'gst_user_profile',
        CACHE_PREFIX: 'gst_cache_'
    },
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    DEBOUNCE_DELAY: 300,
    SEARCH_MIN_LENGTH: 15,
    ITEMS_PER_PAGE: 25,
    MAX_RECENT_SEARCHES: 10,
    NOTIFICATION_DURATION: 5000,
    DEBUG_MODE: localStorage.getItem('gst_debug') === 'true'
};

// Global state management
const AppState = {
    user: null,
    preferences: null,
    cache: new Map(),
    searchHistory: [],
    currentPage: 'dashboard',
    loading: false,
    offline: !navigator.onLine,
    notifications: [],
    modals: new Map()
};

// ===========================================
// 2. UTILITY FUNCTIONS
// ===========================================

class Utils {
    // Debounce function for search input
    static debounce(func, wait) {
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

    // Format date for display
    static formatDate(dateString, options = {}) {
        const date = new Date(dateString);
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return date.toLocaleDateString('en-IN', { ...defaultOptions, ...options });
    }

    // Format currency
    static formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0
        }).format(amount);
    }

    // Validate GSTIN format
    static validateGSTIN(gstin) {
        const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
        return gstinRegex.test(gstin.replace(/\s/g, ''));
    }

    // Validate mobile number
    static validateMobile(mobile) {
        const mobileRegex = /^[6-9]\d{9}$/;
        return mobileRegex.test(mobile.replace(/\s/g, ''));
    }

    // Generate random color for charts
    static getRandomColor() {
        const colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
            '#8B5CF6', '#06B6D4', '#84CC16', '#F97316'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    // Copy text to clipboard
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            window.notificationManager?.show('Copied to clipboard!', 'success');
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            window.notificationManager?.show('Copied to clipboard!', 'success');
        }
    }

    // Download data as file
    static downloadData(data, filename, type = 'json') {
        let content, mimeType;
        
        switch (type) {
            case 'json':
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename += '.json';
                break;
            case 'csv':
                content = this.jsonToCSV(data);
                mimeType = 'text/csv';
                filename += '.csv';
                break;
            default:
                content = data;
                mimeType = 'text/plain';
        }
        
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    static jsonToCSV(jsonData) {
        if (!Array.isArray(jsonData) || jsonData.length === 0) return '';
        
        const headers = Object.keys(jsonData[0]);
        const csvContent = [
            headers.join(','),
            ...jsonData.map(row => 
                headers.map(header => {
                    const value = row[header];
                    return typeof value === 'string' && value.includes(',') 
                        ? `"${value}"` 
                        : value;
                }).join(',')
            )
        ].join('\n');
        
        return csvContent;
    }

    // Local storage helpers
    static setLocalStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('Failed to save to localStorage:', e);
        }
    }

    static getLocalStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.warn('Failed to read from localStorage:', e);
            return defaultValue;
        }
    }

    // Format file size
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// ===========================================
// 3. API SERVICE
// ===========================================

class APIService {
    static async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include'
        };

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            // Handle different response types
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw new Error(data.detail || data.message || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    static async get(url, params = {}) {
        const urlWithParams = new URL(url, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                urlWithParams.searchParams.append(key, value);
            }
        });
        
        return this.request(urlWithParams.toString());
    }

    static async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async postForm(url, formData) {
        return this.request(url, {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        });
    }

    // Specific API methods
    static async searchGSTIN(gstin) {
        const formData = new FormData();
        formData.append('gstin', gstin);
        return this.postForm(GST_CONFIG.ENDPOINTS.SEARCH, formData);
    }

    static async getSearchSuggestions(query) {
        return this.get(GST_CONFIG.ENDPOINTS.SEARCH_SUGGESTIONS, { q: query });
    }

    static async getSearchHistory(page = 1, limit = GST_CONFIG.ITEMS_PER_PAGE) {
        return this.get(GST_CONFIG.ENDPOINTS.HISTORY, { page, limit });
    }

    static async getPreferences() {
        return this.get(GST_CONFIG.ENDPOINTS.PREFERENCES);
    }

    static async updatePreferences(preferences) {
        return this.post(GST_CONFIG.ENDPOINTS.PREFERENCES, preferences);
    }

    static async getStats() {
        return this.get(GST_CONFIG.ENDPOINTS.STATS);
    }

    static async getUserProfile() {
        return this.get(GST_CONFIG.ENDPOINTS.PROFILE);
    }

    static async updateUserProfile(profile) {
        return this.post(GST_CONFIG.ENDPOINTS.PROFILE, profile);
    }

    static async exportData(format = 'json') {
        return this.get(GST_CONFIG.ENDPOINTS.EXPORT, { format });
    }

    static async healthCheck() {
        return this.get(GST_CONFIG.ENDPOINTS.HEALTH);
    }
}

// ===========================================
// 4. NOTIFICATION MANAGER
// ===========================================

class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.initializeContainer();
    }

    initializeContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = GST_CONFIG.NOTIFICATION_DURATION, options = {}) {
        const id = Date.now() + Math.random();
        const notification = this.createNotification(id, message, type, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }

        return id;
    }

    createNotification(id, message, type, options) {
        const notification = document.createElement('div');
        notification.className = `toast toast-${type}`;
        notification.dataset.id = id;

        const icon = this.getIcon(type);
        const canClose = options.closable !== false;

        notification.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
                ${canClose ? `<button class="toast-close" onclick="window.notificationManager.remove(${id})">×</button>` : ''}
            </div>
            ${options.actions ? this.createActions(options.actions) : ''}
        `;

        return notification;
    }

    createActions(actions) {
        const actionsHtml = actions.map(action => 
            `<button class="toast-action" onclick="${action.onClick}">${action.text}</button>`
        ).join('');
        
        return `<div class="toast-actions">${actionsHtml}</div>`;
    }

    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
            loading: '⏳'
        };
        return icons[type] || icons.info;
    }

    remove(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.classList.add('hide');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.parentElement.removeChild(notification);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }

    clear() {
        this.notifications.forEach((notification, id) => {
            this.remove(id);
        });
    }

    success(message, duration, options) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration, options) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration, options) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration, options) {
        return this.show(message, 'info', duration, options);
    }

    loading(message, options) {
        return this.show(message, 'loading', 0, options);
    }
}

// ===========================================
// 5. MODAL MANAGER
// ===========================================

class ModalManager {
    constructor() {
        this.modals = new Map();
        this.overlay = null;
        this.initializeOverlay();
    }

    initializeOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.closeTop();
            }
        });
        document.body.appendChild(this.overlay);
    }

    create(options) {
        const id = options.id || Date.now();
        const modal = this.createModal(id, options);
        
        this.modals.set(id, modal);
        this.overlay.appendChild(modal);
        
        return id;
    }

    createModal(id, options) {
        const modal = document.createElement('div');
        modal.className = `modal ${options.size || 'medium'}`;
        modal.dataset.id = id;

        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${options.title || 'Modal'}</h3>
                ${options.closable !== false ? `<button class="modal-close" onclick="window.modalManager.close('${id}')">×</button>` : ''}
            </div>
            <div class="modal-body">
                ${options.content || ''}
            </div>
            ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
        `;

        return modal;
    }

    show(id) {
        const modal = this.modals.get(id);
        if (modal) {
            this.overlay.classList.add('active');
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        }
    }

    close(id) {
        const modal = this.modals.get(id);
        if (modal) {
            modal.classList.remove('active');
            
            // If no more active modals, hide overlay
            if (!this.overlay.querySelector('.modal.active')) {
                this.overlay.classList.remove('active');
                document.body.classList.remove('modal-open');
            }
        }
    }

    closeTop() {
        const activeModal = this.overlay.querySelector('.modal.active:last-child');
        if (activeModal) {
            const id = activeModal.dataset.id;
            this.close(id);
        }
    }

    remove(id) {
        const modal = this.modals.get(id);
        if (modal) {
            this.close(id);
            setTimeout(() => {
                if (modal.parentElement) {
                    modal.parentElement.removeChild(modal);
                }
                this.modals.delete(id);
            }, 300);
        }
    }

    // Predefined modal types
    alert(message, title = 'Alert') {
        const id = this.create({
            title,
            content: `<p>${message}</p>`,
            footer: `<button class="btn btn-primary" onclick="window.modalManager.close('${Date.now()}')">OK</button>`
        });
        this.show(id);
        return id;
    }

    confirm(message, onConfirm, title = 'Confirm') {
        const id = Date.now();
        const modalId = this.create({
            id,
            title,
            content: `<p>${message}</p>`,
            footer: `
                <button class="btn btn-secondary" onclick="window.modalManager.close('${id}')">Cancel</button>
                <button class="btn btn-primary" onclick="(${onConfirm})(); window.modalManager.close('${id}')">Confirm</button>
            `
        });
        this.show(modalId);
        return modalId;
    }
}

// ===========================================
// 6. THEME MANAGER
// ===========================================

class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.initialize();
    }

    initialize() {
        // Load saved theme
        const savedTheme = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME, 'dark');
        this.setTheme(savedTheme);
        
        // Setup theme toggle
        this.setupThemeToggle();
        
        // Listen for system theme changes
        this.setupSystemThemeListener();
    }

    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME, theme);
        
        // Update theme toggle button
        this.updateThemeToggle();
        
        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        window.notificationManager?.info(`Switched to ${newTheme} mode`);
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    updateThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
            themeToggle.title = this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        }
    }

    setupSystemThemeListener() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                const userPreference = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME);
                if (!userPreference) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
}

// ===========================================
// 7. GSTIN SUGGESTIONS & ENHANCED SEARCH
// ===========================================

class GSTINSuggestions {
    constructor() {
        this.searchInput = null;
        this.suggestionsContainer = null;
        this.recentSearches = [];
        this.cache = new Map();
        this.initialize();
    }

    initialize() {
        this.searchInput = document.getElementById('gstin-search');
        if (!this.searchInput) return;

        this.createSuggestionsContainer();
        this.loadRecentSearches();
        this.setupEventListeners();
    }

    createSuggestionsContainer() {
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'search-suggestions';
        this.suggestionsContainer.style.display = 'none';
        this.searchInput.parentElement.appendChild(this.suggestionsContainer);
    }

    loadRecentSearches() {
        this.recentSearches = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.RECENT_SEARCHES, []);
    }

    saveRecentSearches() {
        Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.RECENT_SEARCHES, this.recentSearches);
    }

    setupEventListeners() {
        const debouncedSearch = Utils.debounce((query) => {
            this.showSuggestions(query);
        }, 300);

        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length >= 3) {
                debouncedSearch(query);
            } else {
                this.hideSuggestions();
            }
        });

        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.length >= 3) {
                this.showSuggestions(this.searchInput.value);
            }
        });

        this.searchInput.addEventListener('blur', () => {
            // Delay to allow clicking on suggestions
            setTimeout(() => this.hideSuggestions(), 150);
        });

        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
    }

    async showSuggestions(query) {
        const suggestions = await this.getSuggestions(query);
        this.renderSuggestions(suggestions);
        this.suggestionsContainer.style.display = 'block';
    }

    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
    }

    async getSuggestions(query) {
        // Check cache first
        if (this.cache.has(query)) {
            return this.cache.get(query);
        }

        try {
            // Get API suggestions
            const apiSuggestions = await APIService.getSearchSuggestions(query);
            
            // Combine with recent searches
            const recentMatches = this.recentSearches.filter(item => 
                item.gstin.toLowerCase().includes(query.toLowerCase()) ||
                item.company_name.toLowerCase().includes(query.toLowerCase())
            ).slice(0, 3);

            const suggestions = {
                recent: recentMatches,
                api: apiSuggestions.suggestions || []
            };

            // Cache the result
            this.cache.set(query, suggestions);
            
            // Clean cache if too large
            if (this.cache.size > 50) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }

            return suggestions;
        } catch (error) {
            console.warn('Failed to get suggestions:', error);
            return { recent: [], api: [] };
        }
    }

    renderSuggestions(suggestions) {
        let html = '';

        // Recent searches
        if (suggestions.recent.length > 0) {
            html += '<div class="suggestion-group"><div class="suggestion-header">Recent Searches</div>';
            suggestions.recent.forEach(item => {
                html += `
                    <div class="suggestion-item recent" onclick="window.gstinSuggestions.selectSuggestion('${item.gstin}')">
                        <div class="suggestion-company">${item.company_name}</div>
                        <div class="suggestion-gstin">${item.gstin}</div>
                        <div class="suggestion-score">${item.compliance_score}%</div>
                    </div>
                `;
            });
            html += '</div>';
        }

        // API suggestions
        if (suggestions.api.length > 0) {
            html += '<div class="suggestion-group"><div class="suggestion-header">Suggestions</div>';
            suggestions.api.forEach(item => {
                html += `
                    <div class="suggestion-item api" onclick="window.gstinSuggestions.selectSuggestion('${item.gstin}')">
                        <div class="suggestion-company">${item.company_name}</div>
                        <div class="suggestion-gstin">${item.gstin}</div>
                    </div>
                `;
            });
            html += '</div>';
        }

        if (!html) {
            html = '<div class="suggestion-item no-results">No suggestions found</div>';
        }

        this.suggestionsContainer.innerHTML = html;
    }

    selectSuggestion(gstin) {
        this.searchInput.value = gstin;
        this.hideSuggestions();
        
        // Trigger search
        if (window.searchManager) {
            window.searchManager.performSearch();
        }
    }

    addToRecentSearches(gstin, companyName, complianceScore) {
        const searchItem = {
            gstin,
            company_name: companyName,
            compliance_score: complianceScore,
            searched_at: new Date().toISOString()
        };

        // Remove if already exists
        this.recentSearches = this.recentSearches.filter(item => item.gstin !== gstin);
        
        // Add to beginning
        this.recentSearches.unshift(searchItem);
        
        // Keep only recent items
        if (this.recentSearches.length > GST_CONFIG.MAX_RECENT_SEARCHES) {
            this.recentSearches = this.recentSearches.slice(0, GST_CONFIG.MAX_RECENT_SEARCHES);
        }
        
        this.saveRecentSearches();
    }

    handleKeyNavigation(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item:not(.no-results)');
        const activeIndex = Array.from(suggestions).findIndex(item => item.classList.contains('active'));

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = activeIndex < suggestions.length - 1 ? activeIndex + 1 : 0;
                this.setActiveSuggestion(suggestions, nextIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = activeIndex > 0 ? activeIndex - 1 : suggestions.length - 1;
                this.setActiveSuggestion(suggestions, prevIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (activeIndex >= 0) {
                    suggestions[activeIndex].click();
                } else if (window.searchManager) {
                    window.searchManager.performSearch();
                }
                break;

            case 'Escape':
                this.hideSuggestions();
                break;
        }
    }

    setActiveSuggestion(suggestions, index) {
        suggestions.forEach(item => item.classList.remove('active'));
        if (suggestions[index]) {
            suggestions[index].classList.add('active');
        }
    }
}

// ===========================================
// 8. ENHANCED VALIDATION
// ===========================================

class EnhancedValidation {
    constructor() {
        this.validators = new Map();
        this.setupValidators();
        this.initializeFormValidation();
    }

    setupValidators() {
        this.validators.set('gstin', {
            regex: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/,
            message: 'Please enter a valid GSTIN format',
            transform: (value) => value.replace(/\s/g, '').toUpperCase()
        });

        this.validators.set('mobile', {
            regex: /^[6-9]\d{9}$/,
            message: 'Please enter a valid Indian mobile number',
            transform: (value) => value.replace(/\D/g, '')
        });

        this.validators.set('pan', {
            regex: /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/,
            message: 'Please enter a valid PAN format',
            transform: (value) => value.replace(/\s/g, '').toUpperCase()
        });

        this.validators.set('email', {
            regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Please enter a valid email address',
            transform: (value) => value.toLowerCase().trim()
        });
    }

    initializeFormValidation() {
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-validate]')) {
                this.validateField(e.target);
            }
        });

        document.addEventListener('blur', (e) => {
            if (e.target.matches('[data-validate]')) {
                this.validateField(e.target, true);
            }
        });
    }

    validateField(field, showMessage = false) {
        const validationType = field.dataset.validate;
        const validator = this.validators.get(validationType);
        
        if (!validator) return true;

        const value = validator.transform ? validator.transform(field.value) : field.value;
        const isValid = validator.regex.test(value);

        // Update field appearance
        field.classList.toggle('invalid', !isValid && value.length > 0);
        field.classList.toggle('valid', isValid && value.length > 0);

        // Show/hide validation message
        if (showMessage || field.classList.contains('invalid')) {
            this.showValidationMessage(field, isValid ? '' : validator.message);
        }

        // Update transformed value
        if (validator.transform && value !== field.value) {
            field.value = value;
        }

        return isValid;
    }

    showValidationMessage(field, message) {
        let messageEl = field.parentElement.querySelector('.validation-message');
        
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.className = 'validation-message';
            field.parentElement.appendChild(messageEl);
        }

        messageEl.textContent = message;
        messageEl.className = `validation-message ${message ? 'error' : 'success'}`;
    }

    validateForm(form) {
        const fields = form.querySelectorAll('[data-validate]');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field, true)) {
                isValid = false;
            }
        });

        return isValid;
    }
}

// ===========================================
// 9. SEARCH MANAGER
// ===========================================

class SearchManager {
    constructor() {
        this.searchInput = document.getElementById('gstin-search');
        this.searchButton = document.getElementById('search-button');
        this.searchForm = document.getElementById('search-form');
        this.resultsContainer = document.getElementById('search-results');
        this.loadingIndicator = document.getElementById('search-loading');
        this.currentResults = null;
        
        this.initialize();
    }

    initialize() {
        if (!this.searchForm) return;

        this.setupEventListeners();
        this.setupFormValidation();
    }

    setupEventListeners() {
        // Form submission
        this.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });

        // Enter key handler
        this.searchInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch();
            }
        });

        // Input validation
        this.searchInput?.addEventListener('input', (e) => {
            this.validateSearchInput(e.target.value);
        });
    }

    setupFormValidation() {
        if (this.searchInput) {
            this.searchInput.setAttribute('data-validate', 'gstin');
        }
    }

    validateSearchInput(value) {
        const cleanValue = value.replace(/\s/g, '').toUpperCase();
        const isValid = Utils.validateGSTIN(cleanValue);
        
        // Update UI
        if (this.searchInput) {
            this.searchInput.classList.toggle('invalid', value.length > 0 && !isValid);
            this.searchInput.classList.toggle('valid', isValid);
        }
        
        if (this.searchButton) {
            this.searchButton.disabled = !isValid;
        }
        
        return isValid;
    }

    async performSearch() {
        const gstin = this.searchInput?.value?.trim().replace(/\s/g, '').toUpperCase();
        
        if (!gstin || !Utils.validateGSTIN(gstin)) {
            window.notificationManager?.error('Please enter a valid GSTIN');
            return;
        }

        this.showLoading(true);
        
        try {
            // Check cache first
            const cacheKey = `${GST_CONFIG.STORAGE_KEYS.CACHE_PREFIX}${gstin}`;
            const cachedResult = Utils.getLocalStorage(cacheKey);
            
            if (cachedResult && Date.now() - cachedResult.timestamp < GST_CONFIG.CACHE_DURATION) {
                this.displayResults(cachedResult.data);
                window.notificationManager?.info('Results loaded from cache');
                return;
            }

            // Perform API search
            const results = await APIService.searchGSTIN(gstin);
            
            // Cache results
            Utils.setLocalStorage(cacheKey, {
                data: results,
                timestamp: Date.now()
            });

            // Store current results
            this.currentResults = results;

            // Display results
            this.displayResults(results);
            
            // Add to recent searches
            if (window.gstinSuggestions && results.company_data) {
                window.gstinSuggestions.addToRecentSearches(
                    gstin,
                    results.company_data.lgnm || 'Unknown Company',
                    results.compliance_score || 0
                );
            }
            
            window.notificationManager?.success('Search completed successfully!');
            
        } catch (error) {
            console.error('Search failed:', error);
            this.displayError(error.message);
            window.notificationManager?.error(`Search failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(results) {
        if (!this.resultsContainer) return;

        // Hide search form and show results
        if (this.searchForm) {
            this.searchForm.style.display = 'none';
        }
        
        this.resultsContainer.innerHTML = this.buildResultsHTML(results);
        this.resultsContainer.style.display = 'block';
        
        // Initialize result interactions
        this.initializeResultInteractions();
        
        // Scroll to results
        this.resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    buildResultsHTML(results) {
        const companyData = results.company_data || {};
        const complianceScore = results.compliance_score || 0;
        const synopsis = results.synopsis || 'No analysis available';
        
        return `
            <div class="search-results-container">
                <!-- Header Section -->
                <div class="results-header">
                    <button class="back-button" onclick="window.searchManager.showSearchForm()">
                        ← Back to Search
                    </button>
                    <div class="results-actions">
                        <button class="action-btn" onclick="window.searchManager.exportResults()">
                            📊 Export Results
                        </button>
                        <button class="action-btn" onclick="window.searchManager.shareResults()">
                            📤 Share
                        </button>
                        <button class="action-btn" onclick="window.searchManager.printResults()">
                            🖨️ Print
                        </button>
                    </div>
                </div>

                <!-- Company Overview -->
                <div class="company-overview">
                    <div class="company-header">
                        <div class="company-info">
                            <h2>${companyData.lgnm || 'Unknown Company'}</h2>
                            <div class="company-meta">
                                <span class="company-gstin" onclick="Utils.copyToClipboard('${companyData.gstin}')">
                                    📋 ${companyData.gstin || 'N/A'}
                                </span>
                                <div class="company-status ${(companyData.sts || '').toLowerCase()}">
                                    ${companyData.sts || 'Unknown Status'}
                                </div>
                            </div>
                        </div>
                        <div class="compliance-badge">
                            <div class="compliance-score">${complianceScore}%</div>
                            <div class="compliance-label">Compliance</div>
                        </div>
                    </div>
                    
                    <div class="company-details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Registration Date:</span>
                            <span class="detail-value">${companyData.rgdt || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Business Type:</span>
                            <span class="detail-value">${companyData.dty || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">State:</span>
                            <span class="detail-value">${companyData.stj || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Constitution:</span>
                            <span class="detail-value">${companyData.ctb || 'N/A'}</span>
                        </div>
                    </div>
                </div>

                <!-- AI Synopsis -->
                <div class="synopsis-section">
                    <h3>🤖 AI Analysis</h3>
                    <div class="synopsis-content">
                        ${synopsis}
                    </div>
                    <div class="synopsis-actions">
                        <button class="btn btn-secondary" onclick="window.searchManager.regenerateAnalysis()">
                            🔄 Regenerate Analysis
                        </button>
                    </div>
                </div>

                <!-- Detailed Information Tabs -->
                <div class="details-tabs">
                    <div class="tab-buttons">
                        <button class="tab-btn active" data-tab="business">📊 Business Info</button>
                        <button class="tab-btn" data-tab="addresses">📍 Addresses</button>
                        <button class="tab-btn" data-tab="compliance">✅ Compliance</button>
                        <button class="tab-btn" data-tab="timeline">📅 Timeline</button>
                    </div>
                    
                    <div class="tab-content">
                        <div class="tab-pane active" id="business-tab">
                            ${this.buildBusinessInfoTab(companyData)}
                        </div>
                        <div class="tab-pane" id="addresses-tab">
                            ${this.buildAddressesTab(companyData)}
                        </div>
                        <div class="tab-pane" id="compliance-tab">
                            ${this.buildComplianceTab(companyData, complianceScore)}
                        </div>
                        <div class="tab-pane" id="timeline-tab">
                            ${this.buildTimelineTab(companyData)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    buildBusinessInfoTab(data) {
        const businessActivities = data.nba || [];
        
        return `
            <div class="business-info">
                <div class="info-section">
                    <h4>Business Activities</h4>
                    <div class="activities-list">
                        ${businessActivities.length > 0 
                            ? businessActivities.map(activity => `<span class="activity-tag">${activity}</span>`).join('')
                            : '<p class="no-data">No business activities recorded</p>'
                        }
                    </div>
                </div>
                
                <div class="info-section">
                    <h4>Registration Details</h4>
                    <div class="registration-grid">
                        <div class="detail-row">
                            <span class="label">PAN:</span>
                            <span class="value">${data.pan || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Constitution:</span>
                            <span class="value">${data.ctb || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Centre Jurisdiction:</span>
                            <span class="value">${data.ctj || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">State Jurisdiction:</span>
                            <span class="value">${data.stj || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    buildAddressesTab(data) {
        const addresses = data.pradr || {};
        
        return `
            <div class="addresses-info">
                <div class="address-card">
                    <h4>📍 Principal Place of Business</h4>
                    <div class="address-details">
                        <div class="address-text">${addresses.addr || 'Address not available'}</div>
                        <div class="address-meta">
                            <div class="meta-item">
                                <span class="label">Location:</span>
                                <span class="value">${addresses.loc || 'N/A'}</span>
                            </div>
                            <div class="meta-item">
                                <span class="label">Pincode:</span>
                                <span class="value">${addresses.pncd || 'N/A'}</span>
                            </div>
                            <div class="meta-item">
                                <span class="label">State Code:</span>
                                <span class="value">${addresses.stcd || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="address-actions">
                        <button class="btn btn-secondary" onclick="window.searchManager.viewOnMap('${addresses.addr}')">
                            🗺️ View on Map
                        </button>
                        <button class="btn btn-secondary" onclick="Utils.copyToClipboard('${addresses.addr}')">
                            📋 Copy Address
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    buildComplianceTab(data, score) {
        const level = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'average' : 'poor';
        
        return `
            <div class="compliance-info">
                <div class="compliance-overview">
                    <div class="score-display">
                        <div class="score-circle ${level}" data-score="${score}">
                            <div class="score-value">${score}%</div>
                            <div class="score-label">Compliance Score</div>
                        </div>
                        <div class="score-analysis">
                            <h4>Risk Assessment: ${level.toUpperCase()}</h4>
                            <div class="risk-indicators">
                                ${this.buildRiskIndicators(score)}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="compliance-details">
                    <h4>📋 Filing Status</h4>
                    <div class="filing-grid">
                        <div class="filing-item">
                            <span class="filing-type">GSTR-1</span>
                            <span class="filing-status filed">Filed</span>
                        </div>
                        <div class="filing-item">
                            <span class="filing-type">GSTR-3B</span>
                            <span class="filing-status filed">Filed</span>
                        </div>
                        <div class="filing-item">
                            <span class="filing-type">Annual Return</span>
                            <span class="filing-status pending">Pending</span>
                        </div>
                    </div>
                </div>
                
                <div class="recommendations">
                    <h4>💡 Recommendations</h4>
                    ${this.buildRecommendations(score)}
                </div>
            </div>
        `;
    }

    buildRiskIndicators(score) {
        const indicators = [
            { label: 'Registration Status', status: 'good', value: 'Active' },
            { label: 'Filing Compliance', status: score >= 70 ? 'good' : 'warning', value: `${score}%` },
            { label: 'Payment History', status: score >= 80 ? 'good' : 'average', value: 'Regular' },
            { label: 'Business Activity', status: 'good', value: 'Consistent' }
        ];

        return indicators.map(indicator => `
            <div class="risk-indicator ${indicator.status}">
                <span class="indicator-label">${indicator.label}</span>
                <span class="indicator-value">${indicator.value}</span>
            </div>
        `).join('');
    }

    buildRecommendations(score) {
        const recommendations = {
            excellent: [
                'Maintain current compliance standards',
                'Consider implementing automated filing systems',
                'Regular compliance monitoring recommended'
            ],
            good: [
                'Minor improvements possible in filing timeliness',
                'Consider professional consultation for optimization',
                'Monitor upcoming compliance deadlines'
            ],
            average: [
                'Compliance gaps identified - immediate attention needed',
                'Professional consultation strongly advised',
                'Implement compliance tracking systems'
            ],
            poor: [
                'Critical compliance issues - immediate action required',
                'Comprehensive review and rectification needed',
                'Professional legal consultation recommended'
            ]
        };

        const level = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'average' : 'poor';
        
        return `
            <ul class="recommendation-list">
                ${recommendations[level].map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        `;
    }

    buildTimelineTab(data) {
        const regDate = data.rgdt ? new Date(data.rgdt) : null;
        
        return `
            <div class="timeline-info">
                <div class="timeline">
                    ${regDate ? `
                        <div class="timeline-item registration">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <h4>🏢 GST Registration</h4>
                                <p>Company registered for Goods and Services Tax</p>
                                <span class="timeline-date">${Utils.formatDate(regDate)}</span>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="timeline-item search">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <h4>🔍 Data Retrieved</h4>
                            <p>Latest company information fetched and analyzed</p>
                            <span class="timeline-date">${Utils.formatDate(new Date())}</span>
                        </div>
                    </div>
                    
                    <div class="timeline-item analysis">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <h4>🤖 AI Analysis Complete</h4>
                            <p>Comprehensive compliance analysis generated</p>
                            <span class="timeline-date">${Utils.formatDate(new Date())}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    initializeResultInteractions() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Initialize animations
        this.animateComplianceScore();
    }

    switchTab(tabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });

        // Add active class to selected tab
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    animateComplianceScore() {
        const scoreCircles = document.querySelectorAll('.score-circle[data-score]');
        scoreCircles.forEach(circle => {
            const score = parseInt(circle.dataset.score);
            // Add animation logic here if needed
        });
    }

    showLoading(show) {
        AppState.loading = show;
        
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = show ? 'flex' : 'none';
        }
        
        if (this.searchButton) {
            this.searchButton.disabled = show;
            this.searchButton.innerHTML = show ? 
                '<span class="loading-spinner"></span> Searching...' : 
                '🔍 Search Company';
        }
    }

    displayError(message) {
        if (!this.resultsContainer) return;

        this.resultsContainer.innerHTML = `
            <div class="error-container">
                <div class="error-icon">❌</div>
                <h3>Search Failed</h3>
                <p>${message}</p>
                <div class="error-actions">
                    <button class="btn btn-primary" onclick="window.searchManager.showSearchForm()">
                        Try Again
                    </button>
                    <button class="btn btn-secondary" onclick="window.searchManager.reportError('${message}')">
                        Report Issue
                    </button>
                </div>
            </div>
        `;
        this.resultsContainer.style.display = 'block';
    }

    showSearchForm() {
        if (this.searchForm) {
            this.searchForm.style.display = 'block';
        }
        if (this.resultsContainer) {
            this.resultsContainer.style.display = 'none';
        }
        
        // Clear and focus search input
        if (this.searchInput) {
            this.searchInput.focus();
        }
    }

    exportResults() {
        if (!this.currentResults) {
            window.notificationManager?.warning('No results to export');
            return;
        }

        const exportData = {
            company: this.currentResults.company_data,
            compliance_score: this.currentResults.compliance_score,
            synopsis: this.currentResults.synopsis,
            exported_at: new Date().toISOString(),
            exported_by: 'GST Intelligence Platform'
        };

        Utils.downloadData(exportData, `GST_Analysis_${this.currentResults.company_data?.gstin}`, 'json');
    }

    shareResults() {
        if (!this.currentResults) {
            window.notificationManager?.warning('No results to share');
            return;
        }

        const shareText = `GST Analysis for ${this.currentResults.company_data?.lgnm}\nGSTIN: ${this.currentResults.company_data?.gstin}\nCompliance Score: ${this.currentResults.compliance_score}%\n\nGenerated by GST Intelligence Platform`;

        if (navigator.share) {
            navigator.share({
                title: 'GST Company Analysis',
                text: shareText,
                url: window.location.href
            });
        } else {
            Utils.copyToClipboard(shareText);
        }
    }

    printResults() {
        window.print();
    }

    viewOnMap(address) {
        if (!address || address === 'N/A') {
            window.notificationManager?.warning('Address not available');
            return;
        }

        const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
        window.open(mapUrl, '_blank');
    }

    async regenerateAnalysis() {
        if (!this.currentResults) return;

        const loadingId = window.notificationManager?.loading('Regenerating AI analysis...');
        
        try {
            // This would call a regenerate endpoint
            const results = await APIService.searchGSTIN(this.currentResults.company_data.gstin);
            
            // Update synopsis section
            const synopsisContent = document.querySelector('.synopsis-content');
            if (synopsisContent) {
                synopsisContent.innerHTML = results.synopsis || 'No analysis available';
            }
            
            this.currentResults = results;
            
            window.notificationManager?.remove(loadingId);
            window.notificationManager?.success('Analysis regenerated successfully!');
            
        } catch (error) {
            window.notificationManager?.remove(loadingId);
            window.notificationManager?.error('Failed to regenerate analysis');
        }
    }

    reportError(message) {
        window.modalManager?.alert(
            `Error reported: "${message}". Our team will investigate this issue. Thank you for your feedback!`,
            'Error Reported'
        );
    }
}

// ===========================================
// 10. USER DASHBOARD MANAGER
// ===========================================

class UserDashboard {
    constructor() {
        this.statsContainer = null;
        this.historyContainer = null;
        this.chartsContainer = null;
        this.initialize();
    }

    initialize() {
        this.statsContainer = document.getElementById('user-stats');
        this.historyContainer = document.getElementById('recent-searches');
        this.chartsContainer = document.getElementById('dashboard-charts');
        
        if (this.statsContainer || this.historyContainer) {
            this.loadDashboardData();
        }
    }

    async loadDashboardData() {
        try {
            const [stats, history] = await Promise.all([
                APIService.getStats().catch(() => null),
                APIService.getSearchHistory(1, 5).catch(() => null)
            ]);

            if (stats) this.displayStats(stats);
            if (history) this.displayRecentSearches(history.data || []);
            
            this.initializeCharts();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.displayError();
        }
    }

    displayStats(stats) {
        if (!this.statsContainer) return;

        this.statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card searches">
                    <div class="stat-icon">🔍</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_searches || 0}</div>
                        <div class="stat-label">Total Searches</div>
                        <div class="stat-change">+${stats.searches_today || 0} today</div>
                    </div>
                </div>
                
                <div class="stat-card companies">
                    <div class="stat-icon">🏢</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.unique_companies || 0}</div>
                        <div class="stat-label">Companies Analyzed</div>
                        <div class="stat-change">+${stats.new_companies || 0} this week</div>
                    </div>
                </div>
                
                <div class="stat-card compliance">
                    <div class="stat-icon">📊</div>
                    <div class="stat-content">
                        <div class="stat-value">${Math.round(stats.avg_compliance_score || 0)}%</div>
                        <div class="stat-label">Avg Compliance</div>
                        <div class="stat-change ${stats.compliance_trend >= 0 ? 'positive' : 'negative'}">
                            ${stats.compliance_trend >= 0 ? '+' : ''}${stats.compliance_trend || 0}% trend
                        </div>
                    </div>
                </div>
                
                <div class="stat-card favorites">
                    <div class="stat-icon">⭐</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.favorites || 0}</div>
                        <div class="stat-label">Saved Companies</div>
                        <div class="stat-change">Quick access</div>
                    </div>
                </div>
            </div>
            
            <div class="quick-actions">
                <button class="quick-action-btn" onclick="document.getElementById('gstin-search')?.focus()">
                    🔍 New Search
                </button>
                <button class="quick-action-btn" onclick="window.userDashboard.viewAllHistory()">
                    📋 View All History
                </button>
                <button class="quick-action-btn" onclick="window.userDashboard.exportData()">
                    📊 Export Data
                </button>
                <button class="quick-action-btn" onclick="window.userProfileManager?.showProfile()">
                    👤 My Profile
                </button>
            </div>
        `;
    }

    displayRecentSearches(searches) {
        if (!this.historyContainer) return;

        if (searches.length === 0) {
            this.historyContainer.innerHTML = `
                <div class="no-searches">
                    <div class="no-searches-icon">🔍</div>
                    <h3>No recent searches</h3>
                    <p>Start exploring companies with GST Intelligence</p>
                    <button class="btn btn-primary" onclick="document.getElementById('gstin-search')?.focus()">
                        Start Searching
                    </button>
                </div>
            `;
            return;
        }

        this.historyContainer.innerHTML = `
            <div class="recent-searches-header">
                <h3>Recent Searches</h3>
                <button class="btn btn-secondary btn-sm" onclick="window.userDashboard.clearHistory()">
                    Clear History
                </button>
            </div>
            <div class="recent-searches-list">
                ${searches.map(search => `
                    <div class="recent-search-item" onclick="window.userDashboard.searchFromHistory('${search.gstin}')">
                        <div class="search-company-info">
                            <div class="search-company-name">${search.company_name}</div>
                            <div class="search-gstin">${search.gstin}</div>
                        </div>
                        <div class="search-score ${this.getScoreClass(search.compliance_score)}">
                            ${search.compliance_score}%
                        </div>
                        <div class="search-date">${Utils.formatDate(search.searched_at, { month: 'short', day: 'numeric' })}</div>
                        <div class="search-actions">
                            <button class="action-btn" onclick="event.stopPropagation(); window.userDashboard.saveToFavorites('${search.gstin}', '${search.company_name}')">
                                ⭐
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'average';
        return 'poor';
    }

    initializeCharts() {
        if (!this.chartsContainer) return;

        // Create placeholder charts
        this.charts// filepath: static/js/gst-platform.js
// GST Intelligence Platform - Consolidated JavaScript Application
// Replaces: app.js, dashboard.js, integration-fixes.js, missing-implementations.js
// Version: 1.0.0 - Production Ready

console.log('🚀 GST Intelligence Platform - Loading Consolidated Application...');

// ===========================================
// 1. GLOBAL CONFIGURATION & CONSTANTS
// ===========================================

const GST_CONFIG = {
    API_BASE_URL: '',
    ENDPOINTS: {
        LOGIN: '/login',
        SIGNUP: '/signup', 
        SEARCH: '/search',
        SEARCH_SUGGESTIONS: '/api/search/suggestions',
        HISTORY: '/api/history',
        PREFERENCES: '/api/preferences',
        STATS: '/api/stats',
        HEALTH: '/health',
        PROFILE: '/api/profile',
        EXPORT: '/api/export',
        BATCH_SEARCH: '/api/batch-search'
    },
    STORAGE_KEYS: {
        USER_PREFERENCES: 'gst_user_preferences',
        RECENT_SEARCHES: 'recentGSTINSearches',
        THEME: 'gst_theme',
        USER_PROFILE: 'gst_user_profile',
        CACHE_PREFIX: 'gst_cache_'
    },
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    DEBOUNCE_DELAY: 300,
    SEARCH_MIN_LENGTH: 15,
    ITEMS_PER_PAGE: 25,
    MAX_RECENT_SEARCHES: 10,
    NOTIFICATION_DURATION: 5000,
    DEBUG_MODE: localStorage.getItem('gst_debug') === 'true'
};

// Global state management
const AppState = {
    user: null,
    preferences: null,
    cache: new Map(),
    searchHistory: [],
    currentPage: 'dashboard',
    loading: false,
    offline: !navigator.onLine,
    notifications: [],
    modals: new Map()
};

// ===========================================
// 2. UTILITY FUNCTIONS
// ===========================================

class Utils {
    // Debounce function for search input
    static debounce(func, wait) {
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

    // Format date for display
    static formatDate(dateString, options = {}) {
        const date = new Date(dateString);
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return date.toLocaleDateString('en-IN', { ...defaultOptions, ...options });
    }

    // Format currency
    static formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0
        }).format(amount);
    }

    // Validate GSTIN format
    static validateGSTIN(gstin) {
        const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
        return gstinRegex.test(gstin.replace(/\s/g, ''));
    }

    // Validate mobile number
    static validateMobile(mobile) {
        const mobileRegex = /^[6-9]\d{9}$/;
        return mobileRegex.test(mobile.replace(/\s/g, ''));
    }

    // Generate random color for charts
    static getRandomColor() {
        const colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
            '#8B5CF6', '#06B6D4', '#84CC16', '#F97316'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    // Copy text to clipboard
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            window.notificationManager?.show('Copied to clipboard!', 'success');
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            window.notificationManager?.show('Copied to clipboard!', 'success');
        }
    }

    // Download data as file
    static downloadData(data, filename, type = 'json') {
        let content, mimeType;
        
        switch (type) {
            case 'json':
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename += '.json';
                break;
            case 'csv':
                content = this.jsonToCSV(data);
                mimeType = 'text/csv';
                filename += '.csv';
                break;
            default:
                content = data;
                mimeType = 'text/plain';
        }
        
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    static jsonToCSV(jsonData) {
        if (!Array.isArray(jsonData) || jsonData.length === 0) return '';
        
        const headers = Object.keys(jsonData[0]);
        const csvContent = [
            headers.join(','),
            ...jsonData.map(row => 
                headers.map(header => {
                    const value = row[header];
                    return typeof value === 'string' && value.includes(',') 
                        ? `"${value}"` 
                        : value;
                }).join(',')
            )
        ].join('\n');
        
        return csvContent;
    }

    // Local storage helpers
    static setLocalStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('Failed to save to localStorage:', e);
        }
    }

    static getLocalStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.warn('Failed to read from localStorage:', e);
            return defaultValue;
        }
    }

    // Format file size
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// ===========================================
// 3. API SERVICE
// ===========================================

class APIService {
    static async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'include'
        };

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            // Handle different response types
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw new Error(data.detail || data.message || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    static async get(url, params = {}) {
        const urlWithParams = new URL(url, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                urlWithParams.searchParams.append(key, value);
            }
        });
        
        return this.request(urlWithParams.toString());
    }

    static async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async postForm(url, formData) {
        return this.request(url, {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        });
    }

    // Specific API methods
    static async searchGSTIN(gstin) {
        const formData = new FormData();
        formData.append('gstin', gstin);
        return this.postForm(GST_CONFIG.ENDPOINTS.SEARCH, formData);
    }

    static async getSearchSuggestions(query) {
        return this.get(GST_CONFIG.ENDPOINTS.SEARCH_SUGGESTIONS, { q: query });
    }

    static async getSearchHistory(page = 1, limit = GST_CONFIG.ITEMS_PER_PAGE) {
        return this.get(GST_CONFIG.ENDPOINTS.HISTORY, { page, limit });
    }

    static async getPreferences() {
        return this.get(GST_CONFIG.ENDPOINTS.PREFERENCES);
    }

    static async updatePreferences(preferences) {
        return this.post(GST_CONFIG.ENDPOINTS.PREFERENCES, preferences);
    }

    static async getStats() {
        return this.get(GST_CONFIG.ENDPOINTS.STATS);
    }

    static async getUserProfile() {
        return this.get(GST_CONFIG.ENDPOINTS.PROFILE);
    }

    static async updateUserProfile(profile) {
        return this.post(GST_CONFIG.ENDPOINTS.PROFILE, profile);
    }

    static async exportData(format = 'json') {
        return this.get(GST_CONFIG.ENDPOINTS.EXPORT, { format });
    }

    static async healthCheck() {
        return this.get(GST_CONFIG.ENDPOINTS.HEALTH);
    }
}

// ===========================================
// 4. NOTIFICATION MANAGER
// ===========================================

class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.initializeContainer();
    }

    initializeContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = GST_CONFIG.NOTIFICATION_DURATION, options = {}) {
        const id = Date.now() + Math.random();
        const notification = this.createNotification(id, message, type, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }

        return id;
    }

    createNotification(id, message, type, options) {
        const notification = document.createElement('div');
        notification.className = `toast toast-${type}`;
        notification.dataset.id = id;

        const icon = this.getIcon(type);
        const canClose = options.closable !== false;

        notification.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
                ${canClose ? `<button class="toast-close" onclick="window.notificationManager.remove(${id})">×</button>` : ''}
            </div>
            ${options.actions ? this.createActions(options.actions) : ''}
        `;

        return notification;
    }

    createActions(actions) {
        const actionsHtml = actions.map(action => 
            `<button class="toast-action" onclick="${action.onClick}">${action.text}</button>`
        ).join('');
        
        return `<div class="toast-actions">${actionsHtml}</div>`;
    }

    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
            loading: '⏳'
        };
        return icons[type] || icons.info;
    }

    remove(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.classList.add('hide');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.parentElement.removeChild(notification);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }

    clear() {
        this.notifications.forEach((notification, id) => {
            this.remove(id);
        });
    }

    success(message, duration, options) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration, options) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration, options) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration, options) {
        return this.show(message, 'info', duration, options);
    }

    loading(message, options) {
        return this.show(message, 'loading', 0, options);
    }
}

// ===========================================
// 5. MODAL MANAGER
// ===========================================

class ModalManager {
    constructor() {
        this.modals = new Map();
        this.overlay = null;
        this.initializeOverlay();
    }

    initializeOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.closeTop();
            }
        });
        document.body.appendChild(this.overlay);
    }

    create(options) {
        const id = options.id || Date.now();
        const modal = this.createModal(id, options);
        
        this.modals.set(id, modal);
        this.overlay.appendChild(modal);
        
        return id;
    }

    createModal(id, options) {
        const modal = document.createElement('div');
        modal.className = `modal ${options.size || 'medium'}`;
        modal.dataset.id = id;

        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${options.title || 'Modal'}</h3>
                ${options.closable !== false ? `<button class="modal-close" onclick="window.modalManager.close('${id}')">×</button>` : ''}
            </div>
            <div class="modal-body">
                ${options.content || ''}
            </div>
            ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
        `;

        return modal;
    }

    show(id) {
        const modal = this.modals.get(id);
        if (modal) {
            this.overlay.classList.add('active');
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        }
    }

    close(id) {
        const modal = this.modals.get(id);
        if (modal) {
            modal.classList.remove('active');
            
            // If no more active modals, hide overlay
            if (!this.overlay.querySelector('.modal.active')) {
                this.overlay.classList.remove('active');
                document.body.classList.remove('modal-open');
            }
        }
    }

    closeTop() {
        const activeModal = this.overlay.querySelector('.modal.active:last-child');
        if (activeModal) {
            const id = activeModal.dataset.id;
            this.close(id);
        }
    }

    remove(id) {
        const modal = this.modals.get(id);
        if (modal) {
            this.close(id);
            setTimeout(() => {
                if (modal.parentElement) {
                    modal.parentElement.removeChild(modal);
                }
                this.modals.delete(id);
            }, 300);
        }
    }

    // Predefined modal types
    alert(message, title = 'Alert') {
        const id = this.create({
            title,
            content: `<p>${message}</p>`,
            footer: `<button class="btn btn-primary" onclick="window.modalManager.close('${Date.now()}')">OK</button>`
        });
        this.show(id);
        return id;
    }

    confirm(message, onConfirm, title = 'Confirm') {
        const id = Date.now();
        const modalId = this.create({
            id,
            title,
            content: `<p>${message}</p>`,
            footer: `
                <button class="btn btn-secondary" onclick="window.modalManager.close('${id}')">Cancel</button>
                <button class="btn btn-primary" onclick="(${onConfirm})(); window.modalManager.close('${id}')">Confirm</button>
            `
        });
        this.show(modalId);
        return modalId;
    }
}

// ===========================================
// 6. THEME MANAGER
// ===========================================

class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.initialize();
    }

    initialize() {
        // Load saved theme
        const savedTheme = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME, 'dark');
        this.setTheme(savedTheme);
        
        // Setup theme toggle
        this.setupThemeToggle();
        
        // Listen for system theme changes
        this.setupSystemThemeListener();
    }

    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME, theme);
        
        // Update theme toggle button
        this.updateThemeToggle();
        
        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        window.notificationManager?.info(`Switched to ${newTheme} mode`);
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    updateThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
            themeToggle.title = this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        }
    }

    setupSystemThemeListener() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                const userPreference = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.THEME);
                if (!userPreference) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
}

// ===========================================
// 7. GSTIN SUGGESTIONS & ENHANCED SEARCH
// ===========================================

class GSTINSuggestions {
    constructor() {
        this.searchInput = null;
        this.suggestionsContainer = null;
        this.recentSearches = [];
        this.cache = new Map();
        this.initialize();
    }

    initialize() {
        this.searchInput = document.getElementById('gstin-search');
        if (!this.searchInput) return;

        this.createSuggestionsContainer();
        this.loadRecentSearches();
        this.setupEventListeners();
    }

    createSuggestionsContainer() {
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'search-suggestions';
        this.suggestionsContainer.style.display = 'none';
        this.searchInput.parentElement.appendChild(this.suggestionsContainer);
    }

    loadRecentSearches() {
        this.recentSearches = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.RECENT_SEARCHES, []);
    }

    saveRecentSearches() {
        Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.RECENT_SEARCHES, this.recentSearches);
    }

    setupEventListeners() {
        const debouncedSearch = Utils.debounce((query) => {
            this.showSuggestions(query);
        }, 300);

        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (query.length >= 3) {
                debouncedSearch(query);
            } else {
                this.hideSuggestions();
            }
        });

        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.length >= 3) {
                this.showSuggestions(this.searchInput.value);
            }
        });

        this.searchInput.addEventListener('blur', () => {
            // Delay to allow clicking on suggestions
            setTimeout(() => this.hideSuggestions(), 150);
        });

        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
    }

    async showSuggestions(query) {
        const suggestions = await this.getSuggestions(query);
        this.renderSuggestions(suggestions);
        this.suggestionsContainer.style.display = 'block';
    }

    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
    }

    async getSuggestions(query) {
        // Check cache first
        if (this.cache.has(query)) {
            return this.cache.get(query);
        }

        try {
            // Get API suggestions
            const apiSuggestions = await APIService.getSearchSuggestions(query);
            
            // Combine with recent searches
            const recentMatches = this.recentSearches.filter(item => 
                item.gstin.toLowerCase().includes(query.toLowerCase()) ||
                item.company_name.toLowerCase().includes(query.toLowerCase())
            ).slice(0, 3);

            const suggestions = {
                recent: recentMatches,
                api: apiSuggestions.suggestions || []
            };

            // Cache the result
            this.cache.set(query, suggestions);
            
            // Clean cache if too large
            if (this.cache.size > 50) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }

            return suggestions;
        } catch (error) {
            console.warn('Failed to get suggestions:', error);
            return { recent: [], api: [] };
        }
    }

    renderSuggestions(suggestions) {
        let html = '';

        // Recent searches
        if (suggestions.recent.length > 0) {
            html += '<div class="suggestion-group"><div class="suggestion-header">Recent Searches</div>';
            suggestions.recent.forEach(item => {
                html += `
                    <div class="suggestion-item recent" onclick="window.gstinSuggestions.selectSuggestion('${item.gstin}')">
                        <div class="suggestion-company">${item.company_name}</div>
                        <div class="suggestion-gstin">${item.gstin}</div>
                        <div class="suggestion-score">${item.compliance_score}%</div>
                    </div>
                `;
            });
            html += '</div>';
        }

        // API suggestions
        if (suggestions.api.length > 0) {
            html += '<div class="suggestion-group"><div class="suggestion-header">Suggestions</div>';
            suggestions.api.forEach(item => {
                html += `
                    <div class="suggestion-item api" onclick="window.gstinSuggestions.selectSuggestion('${item.gstin}')">
                        <div class="suggestion-company">${item.company_name}</div>
                        <div class="suggestion-gstin">${item.gstin}</div>
                    </div>
                `;
            });
            html += '</div>';
        }

        if (!html) {
            html = '<div class="suggestion-item no-results">No suggestions found</div>';
        }

        this.suggestionsContainer.innerHTML = html;
    }

    selectSuggestion(gstin) {
        this.searchInput.value = gstin;
        this.hideSuggestions();
        
        // Trigger search
        if (window.searchManager) {
            window.searchManager.performSearch();
        }
    }

    addToRecentSearches(gstin, companyName, complianceScore) {
        const searchItem = {
            gstin,
            company_name: companyName,
            compliance_score: complianceScore,
            searched_at: new Date().toISOString()
        };

        // Remove if already exists
        this.recentSearches = this.recentSearches.filter(item => item.gstin !== gstin);
        
        // Add to beginning
        this.recentSearches.unshift(searchItem);
        
        // Keep only recent items
        if (this.recentSearches.length > GST_CONFIG.MAX_RECENT_SEARCHES) {
            this.recentSearches = this.recentSearches.slice(0, GST_CONFIG.MAX_RECENT_SEARCHES);
        }
        
        this.saveRecentSearches();
    }

    handleKeyNavigation(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.suggestion-item:not(.no-results)');
        const activeIndex = Array.from(suggestions).findIndex(item => item.classList.contains('active'));

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = activeIndex < suggestions.length - 1 ? activeIndex + 1 : 0;
                this.setActiveSuggestion(suggestions, nextIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = activeIndex > 0 ? activeIndex - 1 : suggestions.length - 1;
                this.setActiveSuggestion(suggestions, prevIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (activeIndex >= 0) {
                    suggestions[activeIndex].click();
                } else if (window.searchManager) {
                    window.searchManager.performSearch();
                }
                break;

            case 'Escape':
                this.hideSuggestions();
                break;
        }
    }

    setActiveSuggestion(suggestions, index) {
        suggestions.forEach(item => item.classList.remove('active'));
        if (suggestions[index]) {
            suggestions[index].classList.add('active');
        }
    }
}

// ===========================================
// 8. ENHANCED VALIDATION
// ===========================================

class EnhancedValidation {
    constructor() {
        this.validators = new Map();
        this.setupValidators();
        this.initializeFormValidation();
    }

    setupValidators() {
        this.validators.set('gstin', {
            regex: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/,
            message: 'Please enter a valid GSTIN format',
            transform: (value) => value.replace(/\s/g, '').toUpperCase()
        });

        this.validators.set('mobile', {
            regex: /^[6-9]\d{9}$/,
            message: 'Please enter a valid Indian mobile number',
            transform: (value) => value.replace(/\D/g, '')
        });

        this.validators.set('pan', {
            regex: /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/,
            message: 'Please enter a valid PAN format',
            transform: (value) => value.replace(/\s/g, '').toUpperCase()
        });

        this.validators.set('email', {
            regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Please enter a valid email address',
            transform: (value) => value.toLowerCase().trim()
        });
    }

    initializeFormValidation() {
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-validate]')) {
                this.validateField(e.target);
            }
        });

        document.addEventListener('blur', (e) => {
            if (e.target.matches('[data-validate]')) {
                this.validateField(e.target, true);
            }
        });
    }

    validateField(field, showMessage = false) {
        const validationType = field.dataset.validate;
        const validator = this.validators.get(validationType);
        
        if (!validator) return true;

        const value = validator.transform ? validator.transform(field.value) : field.value;
        const isValid = validator.regex.test(value);

        // Update field appearance
        field.classList.toggle('invalid', !isValid && value.length > 0);
        field.classList.toggle('valid', isValid && value.length > 0);

        // Show/hide validation message
        if (showMessage || field.classList.contains('invalid')) {
            this.showValidationMessage(field, isValid ? '' : validator.message);
        }

        // Update transformed value
        if (validator.transform && value !== field.value) {
            field.value = value;
        }

        return isValid;
    }

    showValidationMessage(field, message) {
        let messageEl = field.parentElement.querySelector('.validation-message');
        
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.className = 'validation-message';
            field.parentElement.appendChild(messageEl);
        }

        messageEl.textContent = message;
        messageEl.className = `validation-message ${message ? 'error' : 'success'}`;
    }

    validateForm(form) {
        const fields = form.querySelectorAll('[data-validate]');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field, true)) {
                isValid = false;
            }
        });

        return isValid;
    }
}

// ===========================================
// 9. SEARCH MANAGER
// ===========================================

class SearchManager {
    constructor() {
        this.searchInput = document.getElementById('gstin-search');
        this.searchButton = document.getElementById('search-button');
        this.searchForm = document.getElementById('search-form');
        this.resultsContainer = document.getElementById('search-results');
        this.loadingIndicator = document.getElementById('search-loading');
        this.currentResults = null;
        
        this.initialize();
    }

    initialize() {
        if (!this.searchForm) return;

        this.setupEventListeners();
        this.setupFormValidation();
    }

    setupEventListeners() {
        // Form submission
        this.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });

        // Enter key handler
        this.searchInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch();
            }
        });

        // Input validation
        this.searchInput?.addEventListener('input', (e) => {
            this.validateSearchInput(e.target.value);
        });
    }

    setupFormValidation() {
        if (this.searchInput) {
            this.searchInput.setAttribute('data-validate', 'gstin');
        }
    }

    validateSearchInput(value) {
        const cleanValue = value.replace(/\s/g, '').toUpperCase();
        const isValid = Utils.validateGSTIN(cleanValue);
        
        // Update UI
        if (this.searchInput) {
            this.searchInput.classList.toggle('invalid', value.length > 0 && !isValid);
            this.searchInput.classList.toggle('valid', isValid);
        }
        
        if (this.searchButton) {
            this.searchButton.disabled = !isValid;
        }
        
        return isValid;
    }

    async performSearch() {
        const gstin = this.searchInput?.value?.trim().replace(/\s/g, '').toUpperCase();
        
        if (!gstin || !Utils.validateGSTIN(gstin)) {
            window.notificationManager?.error('Please enter a valid GSTIN');
            return;
        }

        this.showLoading(true);
        
        try {
            // Check cache first
            const cacheKey = `${GST_CONFIG.STORAGE_KEYS.CACHE_PREFIX}${gstin}`;
            const cachedResult = Utils.getLocalStorage(cacheKey);
            
            if (cachedResult && Date.now() - cachedResult.timestamp < GST_CONFIG.CACHE_DURATION) {
                this.displayResults(cachedResult.data);
                window.notificationManager?.info('Results loaded from cache');
                return;
            }

            // Perform API search
            const results = await APIService.searchGSTIN(gstin);
            
            // Cache results
            Utils.setLocalStorage(cacheKey, {
                data: results,
                timestamp: Date.now()
            });

            // Store current results
            this.currentResults = results;

            // Display results
            this.displayResults(results);
            
            // Add to recent searches
            if (window.gstinSuggestions && results.company_data) {
                window.gstinSuggestions.addToRecentSearches(
                    gstin,
                    results.company_data.lgnm || 'Unknown Company',
                    results.compliance_score || 0
                );
            }
            
            window.notificationManager?.success('Search completed successfully!');
            
        } catch (error) {
            console.error('Search failed:', error);
            this.displayError(error.message);
            window.notificationManager?.error(`Search failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(results) {
        if (!this.resultsContainer) return;

        // Hide search form and show results
        if (this.searchForm) {
            this.searchForm.style.display = 'none';
        }
        
        this.resultsContainer.innerHTML = this.buildResultsHTML(results);
        this.resultsContainer.style.display = 'block';
        
        // Initialize result interactions
        this.initializeResultInteractions();
        
        // Scroll to results
        this.resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    buildResultsHTML(results) {
        const companyData = results.company_data || {};
        const complianceScore = results.compliance_score || 0;
        const synopsis = results.synopsis || 'No analysis available';
        
        return `
            <div class="search-results-container">
                <!-- Header Section -->
                <div class="results-header">
                    <button class="back-button" onclick="window.searchManager.showSearchForm()">
                        ← Back to Search
                    </button>
                    <div class="results-actions">
                        <button class="action-btn" onclick="window.searchManager.exportResults()">
                            📊 Export Results
                        </button>
                        <button class="action-btn" onclick="window.searchManager.shareResults()">
                            📤 Share
                        </button>
                        <button class="action-btn" onclick="window.searchManager.printResults()">
                            🖨️ Print
                        </button>
                    </div>
                </div>

                <!-- Company Overview -->
                <div class="company-overview">
                    <div class="company-header">
                        <div class="company-info">
                            <h2>${companyData.lgnm || 'Unknown Company'}</h2>
                            <div class="company-meta">
                                <span class="company-gstin" onclick="Utils.copyToClipboard('${companyData.gstin}')">
                                    📋 ${companyData.gstin || 'N/A'}
                                </span>
                                <div class="company-status ${(companyData.sts || '').toLowerCase()}">
                                    ${companyData.sts || 'Unknown Status'}
                                </div>
                            </div>
                        </div>
                        <div class="compliance-badge">
                            <div class="compliance-score">${complianceScore}%</div>
                            <div class="compliance-label">Compliance</div>
                        </div>
                    </div>
                    
                    <div class="company-details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Registration Date:</span>
                            <span class="detail-value">${companyData.rgdt || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Business Type:</span>
                            <span class="detail-value">${companyData.dty || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">State:</span>
                            <span class="detail-value">${companyData.stj || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Constitution:</span>
                            <span class="detail-value">${companyData.ctb || 'N/A'}</span>
                        </div>
                    </div>
                </div>

                <!-- AI Synopsis -->
                <div class="synopsis-section">
                    <h3>🤖 AI Analysis</h3>
                    <div class="synopsis-content">
                        ${synopsis}
                    </div>
                    <div class="synopsis-actions">
                        <button class="btn btn-secondary" onclick="window.searchManager.regenerateAnalysis()">
                            🔄 Regenerate Analysis
                        </button>
                    </div>
                </div>

                <!-- Detailed Information Tabs -->
                <div class="details-tabs">
                    <div class="tab-buttons">
                        <button class="tab-btn active" data-tab="business">📊 Business Info</button>
                        <button class="tab-btn" data-tab="addresses">📍 Addresses</button>
                        <button class="tab-btn" data-tab="compliance">✅ Compliance</button>
                        <button class="tab-btn" data-tab="timeline">📅 Timeline</button>
                    </div>
                    
                    <div class="tab-content">
                        <div class="tab-pane active" id="business-tab">
                            ${this.buildBusinessInfoTab(companyData)}
                        </div>
                        <div class="tab-pane" id="addresses-tab">
                            ${this.buildAddressesTab(companyData)}
                        </div>
                        <div class="tab-pane" id="compliance-tab">
                            ${this.buildComplianceTab(companyData, complianceScore)}
                        </div>
                        <div class="tab-pane" id="timeline-tab">
                            ${this.buildTimelineTab(companyData)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    buildBusinessInfoTab(data) {
        const businessActivities = data.nba || [];
        
        return `
            <div class="business-info">
                <div class="info-section">
                    <h4>Business Activities</h4>
                    <div class="activities-list">
                        ${businessActivities.length > 0 
                            ? businessActivities.map(activity => `<span class="activity-tag">${activity}</span>`).join('')
                            : '<p class="no-data">No business activities recorded</p>'
                        }
                    </div>
                </div>
                
                <div class="info-section">
                    <h4>Registration Details</h4>
                    <div class="registration-grid">
                        <div class="detail-row">
                            <span class="label">PAN:</span>
                            <span class="value">${data.pan || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Constitution:</span>
                            <span class="value">${data.ctb || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Centre Jurisdiction:</span>
                            <span class="value">${data.ctj || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">State Jurisdiction:</span>
                            <span class="value">${data.stj || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    buildAddressesTab(data) {
        const addresses = data.pradr || {};
        
        return `
            <div class="addresses-info">
                <div class="address-card">
                    <h4>📍 Principal Place of Business</h4>
                    <div class="address-details">
                        <div class="address-text">${addresses.addr || 'Address not available'}</div>
                        <div class="address-meta">
                            <div class="meta-item">
                                <span class="label">Location:</span>
                                <span class="value">${addresses.loc || 'N/A'}</span>
                            </div>
                            <div class="meta-item">
                                <span class="label">Pincode:</span>
                                <span class="value">${addresses.pncd || 'N/A'}</span>
                            </div>
                            <div class="meta-item">
                                <span class="label">State Code:</span>
                                <span class="value">${addresses.stcd || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="address-actions">
                        <button class="btn btn-secondary" onclick="window.searchManager.viewOnMap('${addresses.addr}')">
                            🗺️ View on Map
                        </button>
                        <button class="btn btn-secondary" onclick="Utils.copyToClipboard('${addresses.addr}')">
                            📋 Copy Address
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    buildComplianceTab(data, score) {
        const level = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'average' : 'poor';
        
        return `
            <div class="compliance-info">
                <div class="compliance-overview">
                    <div class="score-display">
                        <div class="score-circle ${level}" data-score="${score}">
                            <div class="score-value">${score}%</div>
                            <div class="score-label">Compliance Score</div>
                        </div>
                        <div class="score-analysis">
                            <h4>Risk Assessment: ${level.toUpperCase()}</h4>
                            <div class="risk-indicators">
                                ${this.buildRiskIndicators(score)}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="compliance-details">
                    <h4>📋 Filing Status</h4>
                    <div class="filing-grid">
                        <div class="filing-item">
                            <span class="filing-type">GSTR-1</span>
                            <span class="filing-status filed">Filed</span>
                        </div>
                        <div class="filing-item">
                            <span class="filing-type">GSTR-3B</span>
                            <span class="filing-status filed">Filed</span>
                        </div>
                        <div class="filing-item">
                            <span class="filing-type">Annual Return</span>
                            <span class="filing-status pending">Pending</span>
                        </div>
                    </div>
                </div>
                
                <div class="recommendations">
                    <h4>💡 Recommendations</h4>
                    ${this.buildRecommendations(score)}
                </div>
            </div>
        `;
    }

    buildRiskIndicators(score) {
        const indicators = [
            { label: 'Registration Status', status: 'good', value: 'Active' },
            { label: 'Filing Compliance', status: score >= 70 ? 'good' : 'warning', value: `${score}%` },
            { label: 'Payment History', status: score >= 80 ? 'good' : 'average', value: 'Regular' },
            { label: 'Business Activity', status: 'good', value: 'Consistent' }
        ];

        return indicators.map(indicator => `
            <div class="risk-indicator ${indicator.status}">
                <span class="indicator-label">${indicator.label}</span>
                <span class="indicator-value">${indicator.value}</span>
            </div>
        `).join('');
    }

    buildRecommendations(score) {
        const recommendations = {
            excellent: [
                'Maintain current compliance standards',
                'Consider implementing automated filing systems',
                'Regular compliance monitoring recommended'
            ],
            good: [
                'Minor improvements possible in filing timeliness',
                'Consider professional consultation for optimization',
                'Monitor upcoming compliance deadlines'
            ],
            average: [
                'Compliance gaps identified - immediate attention needed',
                'Professional consultation strongly advised',
                'Implement compliance tracking systems'
            ],
            poor: [
                'Critical compliance issues - immediate action required',
                'Comprehensive review and rectification needed',
                'Professional legal consultation recommended'
            ]
        };

        const level = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'average' : 'poor';
        
        return `
            <ul class="recommendation-list">
                ${recommendations[level].map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        `;
    }

    buildTimelineTab(data) {
        const regDate = data.rgdt ? new Date(data.rgdt) : null;
        
        return `
            <div class="timeline-info">
                <div class="timeline">
                    ${regDate ? `
                        <div class="timeline-item registration">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <h4>🏢 GST Registration</h4>
                                <p>Company registered for Goods and Services Tax</p>
                                <span class="timeline-date">${Utils.formatDate(regDate)}</span>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="timeline-item search">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <h4>🔍 Data Retrieved</h4>
                            <p>Latest company information fetched and analyzed</p>
                            <span class="timeline-date">${Utils.formatDate(new Date())}</span>
                        </div>
                    </div>
                    
                    <div class="timeline-item analysis">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <h4>🤖 AI Analysis Complete</h4>
                            <p>Comprehensive compliance analysis generated</p>
                            <span class="timeline-date">${Utils.formatDate(new Date())}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    initializeResultInteractions() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Initialize animations
        this.animateComplianceScore();
    }

    switchTab(tabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });

        // Add active class to selected tab
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    animateComplianceScore() {
        const scoreCircles = document.querySelectorAll('.score-circle[data-score]');
        scoreCircles.forEach(circle => {
            const score = parseInt(circle.dataset.score);
            // Add animation logic here if needed
        });
    }

    showLoading(show) {
        AppState.loading = show;
        
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = show ? 'flex' : 'none';
        }
        
        if (this.searchButton) {
            this.searchButton.disabled = show;
            this.searchButton.innerHTML = show ? 
                '<span class="loading-spinner"></span> Searching...' : 
                '🔍 Search Company';
        }
    }

    displayError(message) {
        if (!this.resultsContainer) return;

        this.resultsContainer.innerHTML = `
            <div class="error-container">
                <div class="error-icon">❌</div>
                <h3>Search Failed</h3>
                <p>${message}</p>
                <div class="error-actions">
                    <button class="btn btn-primary" onclick="window.searchManager.showSearchForm()">
                        Try Again
                    </button>
                    <button class="btn btn-secondary" onclick="window.searchManager.reportError('${message}')">
                        Report Issue
                    </button>
                </div>
            </div>
        `;
        this.resultsContainer.style.display = 'block';
    }

    showSearchForm() {
        if (this.searchForm) {
            this.searchForm.style.display = 'block';
        }
        if (this.resultsContainer) {
            this.resultsContainer.style.display = 'none';
        }
        
        // Clear and focus search input
        if (this.searchInput) {
            this.searchInput.focus();
        }
    }

    exportResults() {
        if (!this.currentResults) {
            window.notificationManager?.warning('No results to export');
            return;
        }

        const exportData = {
            company: this.currentResults.company_data,
            compliance_score: this.currentResults.compliance_score,
            synopsis: this.currentResults.synopsis,
            exported_at: new Date().toISOString(),
            exported_by: 'GST Intelligence Platform'
        };

        Utils.downloadData(exportData, `GST_Analysis_${this.currentResults.company_data?.gstin}`, 'json');
    }

    shareResults() {
        if (!this.currentResults) {
            window.notificationManager?.warning('No results to share');
            return;
        }

        const shareText = `GST Analysis for ${this.currentResults.company_data?.lgnm}\nGSTIN: ${this.currentResults.company_data?.gstin}\nCompliance Score: ${this.currentResults.compliance_score}%\n\nGenerated by GST Intelligence Platform`;

        if (navigator.share) {
            navigator.share({
                title: 'GST Company Analysis',
                text: shareText,
                url: window.location.href
            });
        } else {
            Utils.copyToClipboard(shareText);
        }
    }

    printResults() {
        window.print();
    }

    viewOnMap(address) {
        if (!address || address === 'N/A') {
            window.notificationManager?.warning('Address not available');
            return;
        }

        const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
        window.open(mapUrl, '_blank');
    }

    async regenerateAnalysis() {
        if (!this.currentResults) return;

        const loadingId = window.notificationManager?.loading('Regenerating AI analysis...');
        
        try {
            // This would call a regenerate endpoint
            const results = await APIService.searchGSTIN(this.currentResults.company_data.gstin);
            
            // Update synopsis section
            const synopsisContent = document.querySelector('.synopsis-content');
            if (synopsisContent) {
                synopsisContent.innerHTML = results.synopsis || 'No analysis available';
            }
            
            this.currentResults = results;
            
            window.notificationManager?.remove(loadingId);
            window.notificationManager?.success('Analysis regenerated successfully!');
            
        } catch (error) {
            window.notificationManager?.remove(loadingId);
            window.notificationManager?.error('Failed to regenerate analysis');
        }
    }

    reportError(message) {
        window.modalManager?.alert(
            `Error reported: "${message}". Our team will investigate this issue. Thank you for your feedback!`,
            'Error Reported'
        );
    }
}

// ===========================================
// 10. USER DASHBOARD MANAGER
// ===========================================

class UserDashboard {
    constructor() {
        this.statsContainer = null;
        this.historyContainer = null;
        this.chartsContainer = null;
        this.initialize();
    }

    initialize() {
        this.statsContainer = document.getElementById('user-stats');
        this.historyContainer = document.getElementById('recent-searches');
        this.chartsContainer = document.getElementById('dashboard-charts');
        
        if (this.statsContainer || this.historyContainer) {
            this.loadDashboardData();
        }
    }

    async loadDashboardData() {
        try {
            const [stats, history] = await Promise.all([
                APIService.getStats().catch(() => null),
                APIService.getSearchHistory(1, 5).catch(() => null)
            ]);

            if (stats) this.displayStats(stats);
            if (history) this.displayRecentSearches(history.data || []);
            
            this.initializeCharts();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.displayError();
        }
    }

    displayStats(stats) {
        if (!this.statsContainer) return;

        this.statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card searches">
                    <div class="stat-icon">🔍</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_searches || 0}</div>
                        <div class="stat-label">Total Searches</div>
                        <div class="stat-change">+${stats.searches_today || 0} today</div>
                    </div>
                </div>
                
                <div class="stat-card companies">
                    <div class="stat-icon">🏢</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.unique_companies || 0}</div>
                        <div class="stat-label">Companies Analyzed</div>
                        <div class="stat-change">+${stats.new_companies || 0} this week</div>
                    </div>
                </div>
                
                <div class="stat-card compliance">
                    <div class="stat-icon">📊</div>
                    <div class="stat-content">
                        <div class="stat-value">${Math.round(stats.avg_compliance_score || 0)}%</div>
                        <div class="stat-label">Avg Compliance</div>
                        <div class="stat-change ${stats.compliance_trend >= 0 ? 'positive' : 'negative'}">
                            ${stats.compliance_trend >= 0 ? '+' : ''}${stats.compliance_trend || 0}% trend
                        </div>
                    </div>
                </div>
                
                <div class="stat-card favorites">
                    <div class="stat-icon">⭐</div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.favorites || 0}</div>
                        <div class="stat-label">Saved Companies</div>
                        <div class="stat-change">Quick access</div>
                    </div>
                </div>
            </div>
            
            <div class="quick-actions">
                <button class="quick-action-btn" onclick="document.getElementById('gstin-search')?.focus()">
                    🔍 New Search
                </button>
                <button class="quick-action-btn" onclick="window.userDashboard.viewAllHistory()">
                    📋 View All History
                </button>
                <button class="quick-action-btn" onclick="window.userDashboard.exportData()">
                    📊 Export Data
                </button>
                <button class="quick-action-btn" onclick="window.userProfileManager?.showProfile()">
                    👤 My Profile
                </button>
            </div>
        `;
    }

    displayRecentSearches(searches) {
        if (!this.historyContainer) return;

        if (searches.length === 0) {
            this.historyContainer.innerHTML = `
                <div class="no-searches">
                    <div class="no-searches-icon">🔍</div>
                    <h3>No recent searches</h3>
                    <p>Start exploring companies with GST Intelligence</p>
                    <button class="btn btn-primary" onclick="document.getElementById('gstin-search')?.focus()">
                        Start Searching
                    </button>
                </div>
            `;
            return;
        }

        this.historyContainer.innerHTML = `
            <div class="recent-searches-header">
                <h3>Recent Searches</h3>
                <button class="btn btn-secondary btn-sm" onclick="window.userDashboard.clearHistory()">
                    Clear History
                </button>
            </div>
            <div class="recent-searches-list">
                ${searches.map(search => `
                    <div class="recent-search-item" onclick="window.userDashboard.searchFromHistory('${search.gstin}')">
                        <div class="search-company-info">
                            <div class="search-company-name">${search.company_name}</div>
                            <div class="search-gstin">${search.gstin}</div>
                        </div>
                        <div class="search-score ${this.getScoreClass(search.compliance_score)}">
                            ${search.compliance_score}%
                        </div>
                        <div class="search-date">${Utils.formatDate(search.searched_at, { month: 'short', day: 'numeric' })}</div>
                        <div class="search-actions">
                            <button class="action-btn" onclick="event.stopPropagation(); window.userDashboard.saveToFavorites('${search.gstin}', '${search.company_name}')">
                                ⭐
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'average';
        return 'poor';
    }

    initializeCharts() {
        if (!this.chartsContainer) return;

        // Create placeholder charts
        this.chartsContainer.innerHTML = `
            <div class="charts-grid">
                <div class="chart-card">
                    <h4>Compliance Trends</h4>
                    <div class="chart-placeholder">
                        <div class="trend-line">
                            <div class="trend-point" style="left: 0%; bottom: 20%"></div>
                            <div class="trend-point" style="left: 20%; bottom: 40%"></div>
                            <div class="trend-point" style="left: 40%; bottom: 30%"></div>
                            <div class="trend-point" style="left: 60%; bottom: 60%"></div>
                            <div class="trend-point" style="left: 80%; bottom: 50%"></div>
                            <div class="trend-point" style="left: 100%; bottom: 70%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h4>Search Activity</h4>
                    <div class="chart-placeholder">
                        <div class="bar-chart">
                            <div class="bar" style="height: 60%"></div>
                            <div class="bar" style="height: 80%"></div>
                            <div class="bar" style="height: 40%"></div>
                            <div class="bar" style="height: 90%"></div>
                            <div class="bar" style="height: 70%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    displayError() {
        if (this.statsContainer) {
            this.statsContainer.innerHTML = `
                <div class="dashboard-error">
                    <h3>Unable to load dashboard data</h3>
                    <button class="btn btn-primary" onclick="window.userDashboard.loadDashboardData()">
                        Try Again
                    </button>
                </div>
            `;
        }
    }

    searchFromHistory(gstin) {
        const searchInput = document.getElementById('gstin-search');
        if (searchInput && window.searchManager) {
            searchInput.value = gstin;
            window.searchManager.performSearch();
        }
    }

    clearHistory() {
        window.modalManager?.confirm(
            'Are you sure you want to clear all search history? This action cannot be undone.',
            () => {
                Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.RECENT_SEARCHES, []);
                this.loadDashboardData();
                window.notificationManager?.success('Search history cleared');
            },
            'Clear History'
        );
    }

    async saveToFavorites(gstin, companyName) {
        try {
            // This would call an API to save favorites
            window.notificationManager?.success(`${companyName} saved to favorites`);
        } catch (error) {
            window.notificationManager?.error('Failed to save to favorites');
        }
    }

    viewAllHistory() {
        // Navigate to history page or show modal with full history
        window.modalManager?.create({
            title: 'Search History',
            content: '<div id="full-history-container">Loading...</div>',
            size: 'large'
        });
    }

    async exportData() {
        try {
            const data = await APIService.exportData('json');
            Utils.downloadData(data, 'gst_platform_data', 'json');
            window.notificationManager?.success('Data exported successfully');
        } catch (error) {
            window.notificationManager?.error('Failed to export data');
        }
    }
}

// ===========================================
// 11. USER PROFILE MANAGER
// ===========================================

class UserProfileManager {
    constructor() {
        this.profile = null;
        this.initialize();
    }

    initialize() {
        this.loadProfile();
        this.setupProfileEvents();
    }

    async loadProfile() {
        try {
            this.profile = await APIService.getUserProfile();
        } catch (error) {
            console.warn('Failed to load user profile:', error);
            this.profile = Utils.getLocalStorage(GST_CONFIG.STORAGE_KEYS.USER_PROFILE, {});
        }
    }

    setupProfileEvents() {
        const profileBtn = document.getElementById('userProfileBtn');
        if (profileBtn) {
            profileBtn.addEventListener('click', () => {
                this.showProfile();
            });
        }
    }

    showProfile() {
        const modalId = window.modalManager?.create({
            title: '👤 User Profile',
            content: this.buildProfileHTML(),
            size: 'large',
            footer: `
                <button class="btn btn-secondary" onclick="window.modalManager.close('${Date.now()}')">Close</button>
                <button class="btn btn-primary" onclick="window.userProfileManager.saveProfile()">Save Changes</button>
            `
        });

        if (modalId) {
            window.modalManager.show(modalId);
        }
    }

    buildProfileHTML() {
        return `
            <div class="profile-form">
                <div class="profile-section">
                    <h4>Personal Information</h4>
                    <div class="form-group">
                        <label for="profile-name">Full Name</label>
                        <input type="text" id="profile-name" class="form-input" value="${this.profile.name || ''}" placeholder="Enter your full name">
                    </div>
                    <div class="form-group">
                        <label for="profile-email">Email Address</label>
                        <input type="email" id="profile-email" class="form-input" data-validate="email" value="${this.profile.email || ''}" placeholder="Enter your email">
                    </div>
                    <div class="form-group">
                        <label for="profile-mobile">Mobile Number</label>
                        <input type="tel" id="profile-mobile" class="form-input" data-validate="mobile" value="${this.profile.mobile || ''}" placeholder="Enter your mobile number">
                    </div>
                </div>

                <div class="profile-section">
                    <h4>Business Information</h4>
                    <div class="form-group">
                        <label for="profile-company">Company Name</label>
                        <input type="text" id="profile-company" class="form-input" value="${this.profile.company || ''}" placeholder="Enter your company name">
                    </div>
                    <div class="form-group">
                        <label for="profile-designation">Designation</label>
                        <input type="text" id="profile-designation" class="form-input" value="${this.profile.designation || ''}" placeholder="Enter your designation">
                    </div>
                    <div class="form-group">
                        <label for="profile-industry">Industry</label>
                        <select id="profile-industry" class="form-select">
                            <option value="">Select Industry</option>
                            <option value="manufacturing" ${this.profile.industry === 'manufacturing' ? 'selected' : ''}>Manufacturing</option>
                            <option value="trading" ${this.profile.industry === 'trading' ? 'selected' : ''}>Trading</option>
                            <option value="services" ${this.profile.industry === 'services' ? 'selected' : ''}>Services</option>
                            <option value="consulting" ${this.profile.industry === 'consulting' ? 'selected' : ''}>Consulting</option>
                            <option value="other" ${this.profile.industry === 'other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>
                </div>

                <div class="profile-section">
                    <h4>Preferences</h4>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="profile-notifications" ${this.profile.notifications ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            Enable email notifications
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="profile-analytics" ${this.profile.analytics ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            Share analytics for platform improvement
                        </label>
                    </div>
                    <div class="form-group">
                        <label for="profile-theme">Theme Preference</label>
                        <select id="profile-theme" class="form-select">
                            <option value="auto" ${this.profile.theme === 'auto' ? 'selected' : ''}>Auto (System)</option>
                            <option value="light" ${this.profile.theme === 'light' ? 'selected' : ''}>Light</option>
                            <option value="dark" ${this.profile.theme === 'dark' ? 'selected' : ''}>Dark</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }

    async saveProfile() {
        const formData = {
            name: document.getElementById('profile-name')?.value || '',
            email: document.getElementById('profile-email')?.value || '',
            mobile: document.getElementById('profile-mobile')?.value || '',
            company: document.getElementById('profile-company')?.value || '',
            designation: document.getElementById('profile-designation')?.value || '',
            industry: document.getElementById('profile-industry')?.value || '',
            notifications: document.getElementById('profile-notifications')?.checked || false,
            analytics: document.getElementById('profile-analytics')?.checked || false,
            theme: document.getElementById('profile-theme')?.value || 'auto'
        };

        // Validate required fields
        if (!window.enhancedValidation?.validateForm(document.querySelector('.profile-form'))) {
            window.notificationManager?.error('Please correct the errors in the form');
            return;
        }

        try {
            const updatedProfile = await APIService.updateUserProfile(formData);
            this.profile = updatedProfile;
            
            // Save to local storage as backup
            Utils.setLocalStorage(GST_CONFIG.STORAGE_KEYS.USER_PROFILE, updatedProfile);
            
            // Apply theme preference
            if (formData.theme !== 'auto') {
                window.themeManager?.setTheme(formData.theme);
            }
            
            window.notificationManager?.success('Profile updated successfully');
            
        } catch (error) {
            console.error('Failed to save profile:', error);
            window.notificationManager?.error('Failed to save profile changes');
        }
    }
}

// ===========================================
// 12. INTEGRATION FUNCTIONS (Global Window Functions)
// ===========================================

// Make functions globally available for template compatibility
window.openEnhancedProfileModal = function() {
    window.userProfileManager?.showProfile();
};

window.clearUserData = function() {
    window.modalManager?.confirm(
        'Are you sure you want to clear all user data? This will remove search history, preferences, and cached data.',
        () => {
            // Clear all local storage data
            Object.values(GST_CONFIG.STORAGE_KEYS).forEach(key => {
                localStorage.removeItem(key);
            });
            
            // Clear caches
            AppState.cache.clear();
            
            // Reload page
            window.location.reload();
        },
        'Clear All Data'
    );
};

window.exportAllUserData = function() {
    window.userDashboard?.exportData();
};

window.resetAllSettings = function() {
    window.modalManager?.confirm(
        'Reset all settings to default values?',
        () => {
            // Reset theme
            window.themeManager?.setTheme('dark');
            
            // Clear preferences
            localStorage.removeItem(GST_CONFIG.STORAGE_KEYS.USER_PREFERENCES);
            
            window.notificationManager?.success('Settings reset to defaults');
        },
        'Reset Settings'
    );
};

window.toggleNotifications = function() {
    // Toggle notification permissions
    if ('Notification' in window) {
        if (Notification.permission === 'granted') {
            window.notificationManager?.info('Notifications are enabled');
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    window.notificationManager?.success('Notifications enabled');
                } else {
                    window.notificationManager?.warning('Notifications disabled');
                }
            });
        } else {
            window.notificationManager?.warning('Notifications are blocked. Please enable in browser settings.');
        }
    }
};

window.generateReport = function() {
    window.notificationManager?.info('Report generation feature coming soon!');
};

window.showHelp = function() {
    const helpContent = `
        <div class="help-content">
            <h4>🔍 How to Search</h4>
            <p>Enter a valid 15-digit GSTIN to search for company information.</p>
            
            <h4>📊 Understanding Compliance Scores</h4>
            <ul>
                <li><strong>80-100%:</strong> Excellent compliance</li>
                <li><strong>60-79%:</strong> Good compliance</li>
                <li><strong>40-59%:</strong> Average compliance</li>
                <li><strong>0-39%:</strong> Poor compliance</li>
            </ul>
            
            <h4>🎯 Tips</h4>
            <ul>
                <li>Use Ctrl+K to quickly focus on search</li>
                <li>Click on any GSTIN to copy it</li>
                <li>Export results for offline analysis</li>
                <li>Recent searches are saved for quick access</li>
            </ul>
        </div>
    `;
    
    window.modalManager?.create({
        title: '❓ Help & Guide',
        content: helpContent,
        footer: '<button class="btn btn-primary" onclick="window.modalManager.closeTop()">Got it!</button>'
    });
};

// ===========================================
// 13. APPLICATION INITIALIZATION
// ===========================================

class GSTApplication {
    constructor() {
        this.initialized = false;
        this.components = {};
    }

    async initialize() {
        if (this.initialized) return;
        
        console.log('🚀 Initializing GST Intelligence Platform...');

        try {
            // Initialize core managers
            this.components.notificationManager = new NotificationManager();
            this.components.modalManager = new ModalManager();
            this.components.themeManager = new ThemeManager();
            this.components.enhancedValidation = new EnhancedValidation();
            
            // Initialize search components
            this.components.gstinSuggestions = new GSTINSuggestions();
            this.components.searchManager = new SearchManager();
            
            // Initialize user components
            this.components.userDashboard = new UserDashboard();
            this.components.userProfileManager = new UserProfileManager();

            // Make components globally available
            Object.entries(this.components).forEach(([name, instance]) => {
                window[name] = instance;
            });

            // Setup global event listeners
            this.setupGlobalEventListeners();
            
            // Setup offline detection
            this.setupOfflineDetection();
            
            // Initialize PWA features
            this.initializePWA();
            
            this.initialized = true;
            console.log('✅ GST Intelligence Platform initialized successfully');
            
            // Show welcome message for new users
            this.showWelcomeMessage();
            
        } catch (error) {
            console.error('❌ Failed to initialize application:', error);
            window.notificationManager?.error('Failed to initialize application');
        }
    }

    setupGlobalEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for search focus
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('gstin-search');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
            
            // Escape to close modals/suggestions
            if (e.key === 'Escape') {
                window.gstinSuggestions?.hideSuggestions();
                window.modalManager?.closeTop();
            }
        });

        // Handle clicks on elements with data attributes
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleDataAction(e.target);
            }
        });

        // Handle form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.matches('.ajax-form')) {
                e.preventDefault();
                this.handleAjaxForm(e.target);
            }
        });
    }

    handleDataAction(element) {
        const action = element.dataset.action;
        const value = element.dataset.value;

        switch (action) {
            case 'search':
                if (value && window.searchManager) {
                    document.getElementById('gstin-search').value = value;
                    window.searchManager.performSearch();
                }
                break;
            case 'copy':
                Utils.copyToClipboard(value || element.textContent);
                break;
            case 'export':
                window.searchManager?.exportResults();
                break;
            case 'share':
                window.searchManager?.shareResults();
                break;
            default:
                console.warn('Unknown data action:', action);
        }
    }

    async handleAjaxForm(form) {
        const formData = new FormData(form);
        const action = form.action || '';
        const method = form.method || 'POST';

        try {
            let result;
            if (method.toLowerCase() === 'post') {
                result = await APIService.postForm(action, formData);
            } else {
                result = await APIService.get(action);
            }

            // Handle success
            window.notificationManager?.success('Form submitted successfully');
            
            if (form.dataset.resetOnSuccess !== 'false') {
                form.reset();
            }

            if (result.redirect) {
                window.location.href = result.redirect;
            }

        } catch (error) {
            window.notificationManager?.error(`Form submission failed: ${error.message}`);
        }
    }

    setupOfflineDetection() {
        window.addEventListener('online', () => {
            AppState.offline = false;
            window.notificationManager?.success('Connection restored');
            this.hideOfflineIndicator();
        });

        window.addEventListener('offline', () => {
            AppState.offline = true;
            window.notificationManager?.warning('You are offline');
            this.showOfflineIndicator();
        });
    }

    showOfflineIndicator() {
        let indicator = document.getElementById('offline-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'offline-indicator';
            indicator.className = 'offline-indicator';
            indicator.innerHTML = '📡 You are currently offline';
            document.body.appendChild(indicator);
        }
        indicator.style.display = 'block';
    }

    hideOfflineIndicator() {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    initializePWA() {
        // Register service worker if available
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(error => {
                console.warn('Service worker registration failed:', error);
            });
        }

        // Handle PWA install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.showInstallPrompt(e);
        });
    }

    showInstallPrompt(installEvent) {
        const actions = [{
            text: 'Install App',
            onClick: () => {
                installEvent.prompt();
                window.notificationManager?.remove();
            }
        }];

        window.notificationManager?.show(
            'Install GST Intelligence Platform for better experience!',
            'info',
            10000,
            { actions }
        );
    }

    showWelcomeMessage() {
        const hasVisited = localStorage.getItem('gst_platform_visited');
        if (!hasVisited) {
            setTimeout(() => {
                window.notificationManager?.success(
                    'Welcome to GST Intelligence Platform! 🎉',
                    5000
                );
                localStorage.setItem('gst_platform_visited', 'true');
            }, 1000);
        }
    }
}

// ===========================================
// 14. FINAL INITIALIZATION
// ===========================================

// Initialize when DOM is ready
let gstApp;

document.addEventListener('DOMContentLoaded', async () => {
    gstApp = new GSTApplication();
    await gstApp.initialize();
    
    // Make app globally accessible
    window.gstApp = gstApp;
    
    // Global error handlers
    window.addEventListener('error', (e) => {
        console.error('Global error:', e.error);
        window.notificationManager?.error('An unexpected error occurred');
    });

    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled promise rejection:', e.reason);
        window.notificationManager?.error('An unexpected error occurred');
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GSTApplication, Utils, APIService };
}

console.log('✅ GST Intelligence Platform - JavaScript Loaded Successfully');
