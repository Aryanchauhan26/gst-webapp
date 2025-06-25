// =============================================================================
// GST Intelligence Platform - Core Application JavaScript (CLEANED & OPTIMIZED)
// Enhanced with loan management integration and performance improvements
// =============================================================================

'use strict';

// =============================================================================
// GLOBAL APPLICATION NAMESPACE
// =============================================================================

window.GST_APP = {
    VERSION: '2.0.0',
    CONFIG: {
        API_BASE_URL: '',
        ANIMATION_DURATION: 300,
        DEBOUNCE_DELAY: 300,
        SUGGESTION_LIMIT: 8,
        SEARCH_CACHE_TTL: 300000, // 5 minutes
        RETRY_ATTEMPTS: 3,
        TOAST_DURATION: 4000
    },
    
    state: {
        initialized: false,
        user: null,
        searchCache: new Map(),
        isOnline: navigator.onLine,
        pendingRequests: new Set()
    },
    
    utils: {},
    components: {},
    modules: {}
};

// =============================================================================
// CORE UTILITIES
// =============================================================================

GST_APP.utils = {
    
    // Logging utility
    log: (message, ...args) => {
        if (window.location.hostname === 'localhost' || window.location.search.includes('debug=true')) {
            console.log(`[GST-APP] ${message}`, ...args);
        }
    },
    
    error: (message, ...args) => {
        console.error(`[GST-APP ERROR] ${message}`, ...args);
        
        // Send error to server for tracking
        if (typeof window.reportError === 'function') {
            window.reportError({
                type: 'javascript',
                message: message,
                stack: new Error().stack,
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString()
            });
        }
    },
    
    // Debounce function
    debounce: (func, delay) => {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(null, args), delay);
        };
    },
    
    // Throttle function
    throttle: (func, limit) => {
        let inThrottle;
        return (...args) => {
            if (!inThrottle) {
                func.apply(null, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Format currency
    formatCurrency: (amount, currency = 'INR') => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    },
    
    // Format number with commas
    formatNumber: (num) => {
        return new Intl.NumberFormat('en-IN').format(num);
    },
    
    // Validate GSTIN
    validateGSTIN: (gstin) => {
        const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
        return pattern.test(gstin?.trim()?.toUpperCase());
    },
    
    // Validate mobile number
    validateMobile: (mobile) => {
        const pattern = /^[6-9]\d{9}$/;
        return pattern.test(mobile?.trim());
    },
    
    // Validate email
    validateEmail: (email) => {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return pattern.test(email?.trim());
    },
    
    // Generate unique ID
    generateId: () => {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },
    
    // Safe JSON parse
    safeJsonParse: (str, fallback = null) => {
        try {
            return JSON.parse(str);
        } catch {
            return fallback;
        }
    },
    
    // Get element safely
    getElement: (selector) => {
        try {
            return document.querySelector(selector);
        } catch {
            GST_APP.utils.error('Invalid selector:', selector);
            return null;
        }
    },
    
    // Storage utilities
    storage: {
        set: (key, value, expiry = null) => {
            try {
                const item = {
                    value: value,
                    timestamp: Date.now(),
                    expiry: expiry
                };
                localStorage.setItem(`gst_app_${key}`, JSON.stringify(item));
                return true;
            } catch {
                return false;
            }
        },
        
        get: (key) => {
            try {
                const item = JSON.parse(localStorage.getItem(`gst_app_${key}`));
                if (!item) return null;
                
                if (item.expiry && Date.now() > item.expiry) {
                    localStorage.removeItem(`gst_app_${key}`);
                    return null;
                }
                
                return item.value;
            } catch {
                return null;
            }
        },
        
        remove: (key) => {
            try {
                localStorage.removeItem(`gst_app_${key}`);
                return true;
            } catch {
                return false;
            }
        }
    }
};

// =============================================================================
// TOAST NOTIFICATION SYSTEM
// =============================================================================

GST_APP.components.Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            this.container.innerHTML = '';
            document.body.appendChild(this.container);
            
            // Add CSS if not present
            if (!document.getElementById('toast-styles')) {
                const style = document.createElement('style');
                style.id = 'toast-styles';
                style.textContent = `
                    .toast-container {
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        z-index: 10000;
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                        pointer-events: none;
                    }
                    .toast {
                        background: #2a2037;
                        color: #e2e8f0;
                        padding: 16px 20px;
                        border-radius: 12px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        min-width: 300px;
                        max-width: 400px;
                        pointer-events: auto;
                        transform: translateX(400px);
                        transition: all 0.3s ease;
                        border-left: 4px solid var(--accent-primary);
                    }
                    .toast.show {
                        transform: translateX(0);
                    }
                    .toast.success {
                        border-left-color: #10b981;
                    }
                    .toast.error {
                        border-left-color: #ef4444;
                    }
                    .toast.warning {
                        border-left-color: #f59e0b;
                    }
                    .toast-icon {
                        font-size: 1.2rem;
                        flex-shrink: 0;
                    }
                    .toast-message {
                        flex-grow: 1;
                        font-weight: 500;
                    }
                    .toast-close {
                        background: none;
                        border: none;
                        color: #94a3b8;
                        cursor: pointer;
                        padding: 4px;
                        border-radius: 4px;
                        transition: color 0.2s;
                    }
                    .toast-close:hover {
                        color: #e2e8f0;
                    }
                `;
                document.head.appendChild(style);
            }
        }
    },
    
    show(message, type = 'info', duration = GST_APP.CONFIG.TOAST_DURATION) {
        this.init();
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" type="button">×</button>
        `;
        
        // Add event listeners
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.hide(toast));
        
        // Add to container
        this.container.appendChild(toast);
        
        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        // Auto-hide
        if (duration > 0) {
            setTimeout(() => this.hide(toast), duration);
        }
        
        return toast;
    },
    
    hide(toast) {
        if (toast && toast.parentNode) {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    },
    
    success(message, duration) {
        return this.show(message, 'success', duration);
    },
    
    error(message, duration) {
        return this.show(message, 'error', duration);
    },
    
    warning(message, duration) {
        return this.show(message, 'warning', duration);
    },
    
    info(message, duration) {
        return this.show(message, 'info', duration);
    }
};

// =============================================================================
// API CLIENT
// =============================================================================

GST_APP.modules.ApiClient = {
    
    async request(endpoint, options = {}) {
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            ...options
        };
        
        // Add request to pending set
        const requestId = GST_APP.utils.generateId();
        GST_APP.state.pendingRequests.add(requestId);
        
        try {
            const response = await fetch(endpoint, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
            
        } catch (error) {
            GST_APP.utils.error('API request failed:', endpoint, error);
            throw error;
        } finally {
            GST_APP.state.pendingRequests.delete(requestId);
        }
    },
    
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        return this.request(url.toString());
    },
    
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
};

// =============================================================================
// GSTIN SUGGESTIONS ENGINE
// =============================================================================

GST_APP.components.GSTINSuggestions = {
    
    init() {
        this.bindEvents();
        this.loadSuggestions();
    },
    
    bindEvents() {
        const gstinInputs = document.querySelectorAll('input[data-gstin-search]');
        
        gstinInputs.forEach(input => {
            if (input.dataset.suggestionsInitialized) return;
            
            input.dataset.suggestionsInitialized = 'true';
            
            // Create suggestions container
            const container = this.createSuggestionsContainer(input);
            
            // Debounced search function
            const debouncedSearch = GST_APP.utils.debounce((value) => {
                this.searchSuggestions(value, container);
            }, GST_APP.CONFIG.DEBOUNCE_DELAY);
            
            // Event listeners
            input.addEventListener('input', (e) => {
                const value = e.target.value.trim();
                if (value.length >= 2) {
                    debouncedSearch(value);
                } else {
                    this.hideSuggestions(container);
                }
            });
            
            input.addEventListener('focus', (e) => {
                const value = e.target.value.trim();
                if (value.length >= 2) {
                    this.searchSuggestions(value, container);
                }
            });
            
            input.addEventListener('blur', (e) => {
                // Delay hiding to allow click on suggestions
                setTimeout(() => {
                    this.hideSuggestions(container);
                }, 150);
            });
            
            input.addEventListener('keydown', (e) => {
                this.handleKeyNavigation(e, container);
            });
        });
    },
    
    createSuggestionsContainer(input) {
        const container = document.createElement('div');
        container.className = 'gstin-suggestions';
        container.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #2a2037;
            border: 1px solid #7c3aed;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        
        // Position container relative to input
        const wrapper = input.parentNode;
        if (wrapper && !wrapper.style.position) {
            wrapper.style.position = 'relative';
        }
        
        wrapper.appendChild(container);
        return container;
    },
    
    async searchSuggestions(query, container) {
        try {
            // Check cache first
            const cacheKey = `suggestions_${query.toLowerCase()}`;
            let suggestions = GST_APP.state.searchCache.get(cacheKey);
            
            if (!suggestions) {
                // Fetch from API
                const response = await GST_APP.modules.ApiClient.get('/api/search/suggestions', { q: query });
                
                if (response.success) {
                    suggestions = response.suggestions || [];
                    
                    // Cache for 5 minutes
                    GST_APP.state.searchCache.set(cacheKey, suggestions);
                    setTimeout(() => {
                        GST_APP.state.searchCache.delete(cacheKey);
                    }, GST_APP.CONFIG.SEARCH_CACHE_TTL);
                } else {
                    suggestions = [];
                }
            }
            
            this.displaySuggestions(suggestions, container, query);
            
        } catch (error) {
            GST_APP.utils.error('Failed to fetch suggestions:', error);
            this.hideSuggestions(container);
        }
    },
    
    displaySuggestions(suggestions, container, query) {
        if (!suggestions || suggestions.length === 0) {
            this.hideSuggestions(container);
            return;
        }
        
        const html = suggestions.map((suggestion, index) => {
            const typeClass = this.getTypeClass(suggestion.type);
            const complianceColor = this.getComplianceColor(suggestion.compliance_score);
            
            return `
                <div class="suggestion-item" data-index="${index}" data-gstin="${suggestion.gstin}">
                    <div class="suggestion-icon ${typeClass}">
                        <i class="${suggestion.icon || 'fas fa-building'}"></i>
                    </div>
                    <div class="suggestion-content">
                        <div class="suggestion-company">${this.highlightMatch(suggestion.company, query)}</div>
                        <div class="suggestion-gstin">${this.highlightMatch(suggestion.gstin, query)}</div>
                        ${suggestion.compliance_score ? 
                            `<div class="suggestion-compliance" style="color: ${complianceColor}">
                                Compliance: ${Math.round(suggestion.compliance_score)}%
                            </div>` : ''
                        }
                    </div>
                    <div class="suggestion-type">${suggestion.type}</div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
        container.style.display = 'block';
        
        // Add click handlers
        container.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectSuggestion(item);
            });
        });
    },
    
    hideSuggestions(container) {
        container.style.display = 'none';
        container.innerHTML = '';
    },
    
    selectSuggestion(item) {
        const gstin = item.dataset.gstin;
        const input = item.closest('.gstin-suggestions').previousElementSibling;
        
        if (input && gstin) {
            input.value = gstin;
            
            // Trigger search if this is a search input
            if (input.form) {
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                input.form.dispatchEvent(submitEvent);
            }
            
            // Hide suggestions
            this.hideSuggestions(item.closest('.gstin-suggestions'));
            
            GST_APP.components.Toast.info('GSTIN selected: ' + gstin);
        }
    },
    
    handleKeyNavigation(e, container) {
        if (container.style.display === 'none') return;
        
        const items = container.querySelectorAll('.suggestion-item');
        if (items.length === 0) return;
        
        const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
        let newIndex = currentIndex;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                break;
                
            case 'Enter':
                e.preventDefault();
                if (currentIndex >= 0) {
                    this.selectSuggestion(items[currentIndex]);
                }
                return;
                
            case 'Escape':
                this.hideSuggestions(container);
                e.target.blur();
                return;
                
            default:
                return;
        }
        
        // Update active item
        items.forEach((item, index) => {
            item.classList.toggle('active', index === newIndex);
        });
        
        // Scroll into view
        if (items[newIndex]) {
            items[newIndex].scrollIntoView({ block: 'nearest' });
        }
    },
    
    highlightMatch(text, query) {
        if (!query || !text) return text;
        
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    },
    
    getTypeClass(type) {
        const classes = {
            'recent': 'suggestion-recent',
            'api': 'suggestion-api',
            'builtin': 'suggestion-builtin'
        };
        return classes[type] || 'suggestion-default';
    },
    
    getComplianceColor(score) {
        if (!score) return '#94a3b8';
        
        if (score >= 90) return '#10b981';
        if (score >= 80) return '#34d399';
        if (score >= 70) return '#fbbf24';
        if (score >= 60) return '#f97316';
        return '#ef4444';
    },
    
    loadSuggestions() {
        // Load recent searches from storage
        const recentSearches = GST_APP.utils.storage.get('recent_searches') || [];
        
        // Pre-cache recent searches
        if (recentSearches.length > 0) {
            GST_APP.state.searchCache.set('suggestions_recent', recentSearches);
        }
    }
};

// =============================================================================
// LOAN INTEGRATION MODULE
// =============================================================================

GST_APP.modules.LoanIntegration = {
    
    init() {
        this.bindLoanEvents();
        this.loadLoanApplications();
    },
    
    bindLoanEvents() {
        // Loan application form
        const loanForm = document.getElementById('loan-application-form');
        if (loanForm) {
            loanForm.addEventListener('submit', this.handleLoanApplication.bind(this));
        }
        
        // Loan eligibility check
        const eligibilityBtn = document.getElementById('check-eligibility');
        if (eligibilityBtn) {
            eligibilityBtn.addEventListener('click', this.checkEligibility.bind(this));
        }
        
        // Loan calculator
        const calculatorInputs = document.querySelectorAll('.loan-calculator input');
        calculatorInputs.forEach(input => {
            input.addEventListener('input', GST_APP.utils.debounce(this.calculateLoan.bind(this), 500));
        });
    },
    
    async handleLoanApplication(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const applicationData = Object.fromEntries(formData.entries());
        
        // Validate required fields
        const requiredFields = ['gstin', 'company_name', 'loan_amount', 'purpose', 'tenure_months'];
        const missingFields = requiredFields.filter(field => !applicationData[field]);
        
        if (missingFields.length > 0) {
            GST_APP.components.Toast.error(`Please fill in: ${missingFields.join(', ')}`);
            return;
        }
        
        // Show loading
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Submitting...';
        submitBtn.disabled = true;
        
        try {
            const response = await GST_APP.modules.ApiClient.post('/api/loans/apply', applicationData);
            
            if (response.success) {
                GST_APP.components.Toast.success('Loan application submitted successfully!');
                e.target.reset();
                this.loadLoanApplications();
            } else {
                GST_APP.components.Toast.error(response.error || 'Failed to submit application');
            }
            
        } catch (error) {
            GST_APP.utils.error('Loan application failed:', error);
            GST_APP.components.Toast.error('Failed to submit loan application');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    },
    
    async checkEligibility() {
        const gstinInput = document.getElementById('eligibility-gstin');
        const turnoverInput = document.getElementById('eligibility-turnover');
        const complianceInput = document.getElementById('eligibility-compliance');
        const vintageInput = document.getElementById('eligibility-vintage');
        
        if (!gstinInput?.value || !turnoverInput?.value) {
            GST_APP.components.Toast.warning('Please enter GSTIN and annual turnover');
            return;
        }
        
        const params = {
            gstin: gstinInput.value,
            annual_turnover: parseFloat(turnoverInput.value),
            compliance_score: parseFloat(complianceInput.value) || 75,
            business_vintage_months: parseInt(vintageInput.value) || 12
        };
        
        try {
            const response = await GST_APP.modules.ApiClient.get('/api/loans/eligibility', params);
            
            if (response.success) {
                this.displayEligibilityResult(response.data);
            } else {
                GST_APP.components.Toast.error(response.error || 'Failed to check eligibility');
            }
            
        } catch (error) {
            GST_APP.utils.error('Eligibility check failed:', error);
            GST_APP.components.Toast.error('Failed to check loan eligibility');
        }
    },
    
    displayEligibilityResult(eligibility) {
        const resultContainer = document.getElementById('eligibility-result');
        if (!resultContainer) return;
        
        let html = `
            <div class="eligibility-card ${eligibility.eligible ? 'eligible' : 'not-eligible'}">
                <div class="eligibility-status">
                    <i class="fas fa-${eligibility.eligible ? 'check-circle' : 'times-circle'}"></i>
                    <span>${eligibility.eligible ? 'Eligible for Loan' : 'Not Eligible'}</span>
                </div>
        `;
        
        if (eligibility.eligible) {
            html += `
                <div class="eligibility-details">
                    <div class="detail-item">
                        <label>Maximum Loan Amount:</label>
                        <value>${GST_APP.utils.formatCurrency(eligibility.max_loan_amount)}</value>
                    </div>
                    <div class="detail-item">
                        <label>Recommended Amount:</label>
                        <value>${GST_APP.utils.formatCurrency(eligibility.recommended_amount)}</value>
                    </div>
                    ${eligibility.estimated_interest_rate ? 
                        `<div class="detail-item">
                            <label>Estimated Interest Rate:</label>
                            <value>${eligibility.estimated_interest_rate.toFixed(2)}% per annum</value>
                        </div>` : ''
                    }
                </div>
                <button type="button" class="btn btn--primary" onclick="GST_APP.modules.LoanIntegration.proceedToApplication()">
                    Apply for Loan
                </button>
            `;
        } else {
            html += `
                <div class="eligibility-reasons">
                    <h4>Reasons:</h4>
                    <ul>
                        ${eligibility.reasons.map(reason => `<li>${reason}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        html += '</div>';
        
        resultContainer.innerHTML = html;
        resultContainer.style.display = 'block';
    },
    
    proceedToApplication() {
        // Pre-fill application form with eligibility data
        const eligibilityForm = document.getElementById('eligibility-form');
        const applicationForm = document.getElementById('loan-application-form');
        
        if (eligibilityForm && applicationForm) {
            const formData = new FormData(eligibilityForm);
            
            // Copy values to application form
            for (const [key, value] of formData.entries()) {
                const targetInput = applicationForm.querySelector(`[name="${key}"]`);
                if (targetInput) {
                    targetInput.value = value;
                }
            }
            
            // Scroll to application form
            applicationForm.scrollIntoView({ behavior: 'smooth' });
        }
    },
    
    calculateLoan() {
        const amountInput = document.getElementById('calc-amount');
        const tenureInput = document.getElementById('calc-tenure');
        const rateInput = document.getElementById('calc-rate');
        const resultContainer = document.getElementById('loan-calculation');
        
        if (!amountInput?.value || !tenureInput?.value || !rateInput?.value) {
            return;
        }
        
        const principal = parseFloat(amountInput.value);
        const tenure = parseInt(tenureInput.value);
        const rate = parseFloat(rateInput.value) / 100 / 12; // Monthly rate
        
        // EMI calculation
        const emi = (principal * rate * Math.pow(1 + rate, tenure)) / (Math.pow(1 + rate, tenure) - 1);
        const totalPayable = emi * tenure;
        const totalInterest = totalPayable - principal;
        
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="loan-calculation-result">
                    <div class="calc-item">
                        <label>Monthly EMI:</label>
                        <value>${GST_APP.utils.formatCurrency(emi)}</value>
                    </div>
                    <div class="calc-item">
                        <label>Total Payable:</label>
                        <value>${GST_APP.utils.formatCurrency(totalPayable)}</value>
                    </div>
                    <div class="calc-item">
                        <label>Total Interest:</label>
                        <value>${GST_APP.utils.formatCurrency(totalInterest)}</value>
                    </div>
                </div>
            `;
        }
    },
    
    async loadLoanApplications() {
        const container = document.getElementById('loan-applications-list');
        if (!container) return;
        
        try {
            const response = await GST_APP.modules.ApiClient.get('/api/loans/applications');
            
            if (response.success && response.data.length > 0) {
                this.displayLoanApplications(response.data, container);
            } else {
                container.innerHTML = `
                    <div class="no-applications">
                        <i class="fas fa-file-alt"></i>
                        <p>No loan applications found</p>
                    </div>
                `;
            }
            
        } catch (error) {
            GST_APP.utils.error('Failed to load loan applications:', error);
        }
    },
    
    displayLoanApplications(applications, container) {
        const html = applications.map(app => `
            <div class="loan-application-card" data-id="${app.id}">
                <div class="app-header">
                    <div class="app-id">#${app.id}</div>
                    <div class="app-status status-${app.status}">${app.status.toUpperCase()}</div>
                </div>
                <div class="app-details">
                    <div class="detail-row">
                        <span>Company:</span>
                        <span>${app.company_name}</span>
                    </div>
                    <div class="detail-row">
                        <span>GSTIN:</span>
                        <span>${app.gstin}</span>
                    </div>
                    <div class="detail-row">
                        <span>Amount:</span>
                        <span>${GST_APP.utils.formatCurrency(app.loan_amount)}</span>
                    </div>
                    <div class="detail-row">
                        <span>Tenure:</span>
                        <span>${app.tenure_months} months</span>
                    </div>
                    <div class="detail-row">
                        <span>Applied:</span>
                        <span>${new Date(app.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
                ${app.offers && app.offers.length > 0 ? 
                    `<div class="app-offers">
                        <h5>Available Offers</h5>
                        ${this.renderLoanOffers(app.offers)}
                    </div>` : ''
                }
            </div>
        `).join('');
        
        container.innerHTML = html;
    },
    
    renderLoanOffers(offers) {
        return offers.map(offer => `
            <div class="loan-offer" data-id="${offer.id}">
                <div class="offer-details">
                    <div>Amount: ${GST_APP.utils.formatCurrency(offer.loan_amount)}</div>
                    <div>Interest: ${offer.interest_rate}% p.a.</div>
                    <div>EMI: ${GST_APP.utils.formatCurrency(offer.emi_amount)}</div>
                </div>
                ${!offer.is_accepted && offer.status === 'generated' ? 
                    `<button class="btn btn--sm btn--primary" onclick="GST_APP.modules.LoanIntegration.acceptOffer(${offer.id})">
                        Accept Offer
                    </button>` : 
                    `<span class="offer-status">${offer.status.toUpperCase()}</span>`
                }
            </div>
        `).join('');
    },
    
    async acceptOffer(offerId) {
        if (!confirm('Are you sure you want to accept this loan offer?')) {
            return;
        }
        
        try {
            const response = await GST_APP.modules.ApiClient.post(`/api/loans/offers/${offerId}/accept`);
            
            if (response.success) {
                GST_APP.components.Toast.success('Loan offer accepted successfully!');
                this.loadLoanApplications();
            } else {
                GST_APP.components.Toast.error(response.error || 'Failed to accept offer');
            }
            
        } catch (error) {
            GST_APP.utils.error('Failed to accept loan offer:', error);
            GST_APP.components.Toast.error('Failed to accept loan offer');
        }
    }
};

// =============================================================================
// MAIN APPLICATION INITIALIZATION
// =============================================================================

GST_APP.init = function() {
    if (this.state.initialized) {
        return;
    }
    
    try {
        // Initialize core components
        this.components.GSTINSuggestions.init();
        this.modules.LoanIntegration.init();
        
        // Add global styles
        this.addGlobalStyles();
        
        // Set up global event listeners
        this.bindGlobalEvents();
        
        // Mark as initialized
        this.state.initialized = true;
        
        this.utils.log('GST Intelligence Platform initialized successfully');
        
        // Notify other scripts
        window.dispatchEvent(new CustomEvent('gstAppReady', {
            detail: { version: this.VERSION }
        }));
        
    } catch (error) {
        this.utils.error('Failed to initialize application:', error);
    }
};

GST_APP.addGlobalStyles = function() {
    if (document.getElementById('gst-app-global-styles')) {
        return;
    }
    
    const style = document.createElement('style');
    style.id = 'gst-app-global-styles';
    style.textContent = `
        /* GSTIN Suggestions Styles */
        .gstin-suggestions {
            font-family: inherit;
        }
        .suggestion-item {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            transition: background-color 0.2s;
            border-bottom: 1px solid rgba(124, 58, 237, 0.1);
        }
        .suggestion-item:last-child {
            border-bottom: none;
        }
        .suggestion-item:hover,
        .suggestion-item.active {
            background-color: rgba(124, 58, 237, 0.1);
        }
        .suggestion-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            color: white;
            font-size: 14px;
        }
        .suggestion-content {
            flex-grow: 1;
            min-width: 0;
        }
        .suggestion-company {
            font-weight: 600;
            color: #e2e8f0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .suggestion-gstin {
            font-size: 12px;
            color: #94a3b8;
            font-family: monospace;
        }
        .suggestion-compliance {
            font-size: 11px;
            margin-top: 2px;
        }
        .suggestion-type {
            font-size: 10px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .gstin-suggestions mark {
            background-color: #fbbf24;
            color: #1f2937;
            padding: 1px 2px;
            border-radius: 2px;
        }
        
        /* Loan Components Styles */
        .loan-application-card {
            background: #2a2037;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }
        .app-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .app-id {
            font-weight: 600;
            color: #7c3aed;
        }
        .app-status {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-pending { background: #fbbf24; color: #1f2937; }
        .status-approved { background: #10b981; color: white; }
        .status-rejected { background: #ef4444; color: white; }
        .status-disbursed { background: #3b82f6; color: white; }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .detail-row span:first-child {
            color: #94a3b8;
        }
        .detail-row span:last-child {
            color: #e2e8f0;
            font-weight: 500;
        }
        .loan-offer {
            background: rgba(124, 58, 237, 0.1);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 8px;
            padding: 12px;
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .offer-details {
            display: flex;
            gap: 16px;
            font-size: 12px;
        }
        .eligibility-card {
            background: #2a2037;
            border-radius: 12px;
            padding: 24px;
            margin-top: 16px;
        }
        .eligibility-card.eligible {
            border: 2px solid #10b981;
        }
        .eligibility-card.not-eligible {
            border: 2px solid #ef4444;
        }
        .eligibility-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
        }
        .eligibility-details {
            margin-bottom: 20px;
        }
        .detail-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(124, 58, 237, 0.1);
        }
        .detail-item label {
            color: #94a3b8;
        }
        .detail-item value {
            color: #e2e8f0;
            font-weight: 600;
        }
    `;
    
    document.head.appendChild(style);
};

GST_APP.bindGlobalEvents = function() {
    // Online/offline detection
    window.addEventListener('online', () => {
        this.state.isOnline = true;
        this.components.Toast.success('Connection restored');
    });
    
    window.addEventListener('offline', () => {
        this.state.isOnline = false;
        this.components.Toast.warning('You are now offline');
    });
    
    // Error reporting
    window.addEventListener('error', (e) => {
        this.utils.error('Global error:', e.error?.message || e.message);
    });
    
    // Unhandled promise rejections
    window.addEventListener('unhandledrejection', (e) => {
        this.utils.error('Unhandled promise rejection:', e.reason);
    });
};

// =============================================================================
// AUTO-INITIALIZE WHEN DOM IS READY
// =============================================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => GST_APP.init());
} else {
    GST_APP.init();
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GST_APP;
}

console.log('✅ GST Intelligence Platform Core Application Loaded Successfully!');