// =====================================================
// GST Intelligence Platform - Core Application Module
// Self-contained, modular, and complete functionality
// =====================================================

'use strict';

console.log('🚀 GST Platform Core Application Loading...');

// =====================================================
// 1. CORE CONFIGURATION & CONSTANTS
// =====================================================

window.GST_APP = {
    VERSION: '2.0.0',
    DEBUG: localStorage.getItem('gst_debug') === 'true',
    CONFIG: {
        API_BASE_URL: '',
        MAX_RECENT_SEARCHES: 10,
        DEBOUNCE_DELAY: 300,
        ANIMATION_DURATION: 300,
        CACHE_TTL: 5 * 60 * 1000, // 5 minutes
    },
    
    // State management
    state: {
        initialized: false,
        suggestions: [],
        recentSearches: [],
        userPreferences: {}
    },
    
    // Utility functions
    utils: {
        log: function(...args) {
            if (window.GST_APP.DEBUG) {
                console.log('🔍 GST_APP:', ...args);
            }
        },
        
        error: function(...args) {
            console.error('❌ GST_APP:', ...args);
        },
        
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
        
        isValidGSTIN: function(gstin) {
            return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin?.trim().toUpperCase());
        },
        
        formatGSTIN: function(gstin) {
            return gstin?.trim().toUpperCase().replace(/\s/g, '') || '';
        },
        
        getCache: function(key) {
            try {
                const item = localStorage.getItem(`gst_cache_${key}`);
                if (!item) return null;
                
                const { data, timestamp } = JSON.parse(item);
                if (Date.now() - timestamp > window.GST_APP.CONFIG.CACHE_TTL) {
                    localStorage.removeItem(`gst_cache_${key}`);
                    return null;
                }
                return data;
            } catch {
                return null;
            }
        },
        
        setCache: function(key, data) {
            try {
                localStorage.setItem(`gst_cache_${key}`, JSON.stringify({
                    data,
                    timestamp: Date.now()
                }));
            } catch (error) {
                window.GST_APP.utils.error('Cache storage failed:', error);
            }
        }
    }
};

// =====================================================
// 2. ENHANCED GSTIN SUGGESTIONS ENGINE
// =====================================================

class GSTINSuggestionsEngine {
    constructor() {
        this.suggestions = [
            { gstin: '27AABCU9603R1ZX', company: 'UBER INDIA SYSTEMS PRIVATE LIMITED', type: 'tech', sector: 'Technology' },
            { gstin: '19AABCM7407R1ZZ', company: 'MICROSOFT CORPORATION (INDIA) PRIVATE LIMITED', type: 'tech', sector: 'Technology' },
            { gstin: '29AABCT1332L1ZU', company: 'TATA CONSULTANCY SERVICES LIMITED', type: 'tech', sector: 'IT Services' },
            { gstin: '27AADCB2230M1ZX', company: 'BHARTI AIRTEL LIMITED', type: 'telecom', sector: 'Telecommunications' },
            { gstin: '07AABCI5602R1ZX', company: 'INFOSYS LIMITED', type: 'tech', sector: 'IT Services' },
            { gstin: '36AABCW3775K1ZT', company: 'WIPRO LIMITED', type: 'tech', sector: 'IT Services' },
            { gstin: '29AABCH0263N1Z1', company: 'HCL TECHNOLOGIES LIMITED', type: 'tech', sector: 'IT Services' },
            { gstin: '19AABCR4849E1ZU', company: 'RELIANCE INDUSTRIES LIMITED', type: 'industrial', sector: 'Conglomerate' },
            { gstin: '27AABCS0618N1ZN', company: 'STATE BANK OF INDIA', type: 'banking', sector: 'Banking' },
            { gstin: '07AABCI9016A1Z7', company: 'ICICI BANK LIMITED', type: 'banking', sector: 'Banking' }
        ];
        
        this.activeElements = new Set();
        this.currentIndex = -1;
    }

    initialize() {
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin, #gstinEnhanced');
        gstinInputs.forEach(input => this.enhanceInput(input));
        window.GST_APP.utils.log('GSTIN Suggestions Engine initialized');
    }

    enhanceInput(input) {
        if (this.activeElements.has(input)) return;
        this.activeElements.add(input);

        const container = input.parentElement;
        container.style.position = 'relative';
        
        // Create suggestions container
        const suggestionsEl = this.createSuggestionsElement();
        container.appendChild(suggestionsEl);

        // Debounced input handler
        const debouncedHandler = window.GST_APP.utils.debounce((e) => {
            this.handleInput(e, suggestionsEl);
        }, window.GST_APP.CONFIG.DEBOUNCE_DELAY);

        // Event listeners
        input.addEventListener('input', debouncedHandler);
        input.addEventListener('keydown', (e) => this.handleKeydown(e, suggestionsEl));
        input.addEventListener('blur', () => this.hideSuggestions(suggestionsEl));
        input.addEventListener('focus', (e) => {
            if (e.target.value.length >= 2) {
                this.handleInput(e, suggestionsEl);
            }
        });
    }

    createSuggestionsElement() {
        const element = document.createElement('div');
        element.className = 'gstin-suggestions';
        element.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: var(--hover-shadow);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            margin-top: 4px;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-10px);
            transition: all 0.3s ease;
        `;
        return element;
    }

    async handleInput(e, suggestionsEl) {
        const value = window.GST_APP.utils.formatGSTIN(e.target.value);
        
        if (value.length < 2) {
            this.hideSuggestions(suggestionsEl);
            return;
        }

        // Get suggestions from multiple sources
        const suggestions = await this.getAllSuggestions(value);
        
        if (suggestions.length > 0) {
            this.showSuggestions(suggestionsEl, suggestions, e.target);
        } else {
            this.hideSuggestions(suggestionsEl);
        }
    }

    async getAllSuggestions(query) {
        const suggestions = [];
        
        // 1. Built-in suggestions
        const builtInSuggestions = this.getBuiltInSuggestions(query);
        suggestions.push(...builtInSuggestions);
        
        // 2. Recent searches
        const recentSuggestions = this.getRecentSearchSuggestions(query);
        suggestions.push(...recentSuggestions);
        
        // 3. API suggestions (if available)
        try {
            const apiSuggestions = await this.getAPISuggestions(query);
            suggestions.push(...apiSuggestions);
        } catch (error) {
            window.GST_APP.utils.error('API suggestions failed:', error);
        }
        
        // Remove duplicates and limit results
        const uniqueSuggestions = this.removeDuplicates(suggestions);
        return uniqueSuggestions.slice(0, 8);
    }

    getBuiltInSuggestions(query) {
        return this.suggestions
            .filter(item => 
                item.gstin.toLowerCase().includes(query.toLowerCase()) ||
                item.company.toLowerCase().includes(query.toLowerCase()) ||
                item.sector.toLowerCase().includes(query.toLowerCase())
            )
            .map(item => ({
                ...item,
                source: 'builtin',
                icon: this.getTypeIcon(item.type)
            }));
    }

    getRecentSearchSuggestions(query) {
        try {
            const recentSearches = JSON.parse(localStorage.getItem('recentGSTINSearches') || '[]');
            return recentSearches
                .filter(search => 
                    search.gstin?.toLowerCase().includes(query.toLowerCase()) ||
                    search.companyName?.toLowerCase().includes(query.toLowerCase())
                )
                .map(search => ({
                    gstin: search.gstin,
                    company: search.companyName,
                    type: 'recent',
                    sector: 'Recent Search',
                    source: 'recent',
                    icon: 'fas fa-history'
                }));
        } catch {
            return [];
        }
    }

    async getAPISuggestions(query) {
        // Check cache first
        const cached = window.GST_APP.utils.getCache(`suggestions_${query}`);
        if (cached) return cached;
        
        try {
            const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('API request failed');
            
            const result = await response.json();
            const suggestions = result.success ? result.suggestions : [];
            
            // Cache the results
            window.GST_APP.utils.setCache(`suggestions_${query}`, suggestions);
            
            return suggestions.map(item => ({
                ...item,
                source: 'api'
            }));
        } catch (error) {
            window.GST_APP.utils.error('API suggestions error:', error);
            return [];
        }
    }

    removeDuplicates(suggestions) {
        const seen = new Set();
        return suggestions.filter(item => {
            const key = item.gstin;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    showSuggestions(suggestionsEl, suggestions, input) {
        const maxSuggestions = 6;
        const limitedSuggestions = suggestions.slice(0, maxSuggestions);
        
        suggestionsEl.innerHTML = limitedSuggestions.map((item, index) => `
            <div class="suggestion-item" 
                 data-gstin="${item.gstin}" 
                 data-index="${index}"
                 style="
                     display: flex;
                     align-items: center;
                     gap: 1rem;
                     padding: 1rem;
                     cursor: pointer;
                     transition: all 0.2s ease;
                     border-bottom: 1px solid var(--border-color);
                 "
                 onmouseover="this.style.background='var(--bg-hover)'" 
                 onmouseout="this.style.background='transparent'">
                <div style="
                    width: 40px;
                    height: 40px;
                    background: ${this.getSourceColor(item.source)};
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 1rem;
                    flex-shrink: 0;
                ">
                    <i class="${item.icon || this.getTypeIcon(item.type)}"></i>
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="
                        font-weight: 600;
                        color: var(--text-primary);
                        margin-bottom: 0.25rem;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    ">${item.company || 'Unknown Company'}</div>
                    <div style="
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 0.875rem;
                        color: var(--accent-primary);
                        margin-bottom: 0.25rem;
                    ">${item.gstin}</div>
                    <div style="
                        font-size: 0.75rem;
                        color: var(--text-secondary);
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    ">
                        <span>${item.sector || item.type || 'Business'}</span>
                        ${item.compliance_score ? `<span style="color: var(--accent-primary);">Score: ${Math.round(item.compliance_score)}%</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        // Show the dropdown
        suggestionsEl.style.opacity = '1';
        suggestionsEl.style.visibility = 'visible';
        suggestionsEl.style.transform = 'translateY(0)';

        // Add click handlers
        this.attachSuggestionClickHandlers(suggestionsEl, input);
        
        // Reset current index
        this.currentIndex = -1;
    }

    attachSuggestionClickHandlers(suggestionsEl, input) {
        const suggestionItems = suggestionsEl.querySelectorAll('.suggestion-item');
        suggestionItems.forEach((item) => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const gstin = item.dataset.gstin;
                input.value = gstin;
                this.hideSuggestions(suggestionsEl);
                
                // Trigger validation
                input.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Focus and notify
                input.focus();
                
                if (window.notificationManager) {
                    window.notificationManager.showSuccess('✅ GSTIN selected!', 2000);
                }
                
                window.GST_APP.utils.log('Suggestion selected:', gstin);
            });
        });
    }

    hideSuggestions(suggestionsEl) {
        suggestionsEl.style.opacity = '0';
        suggestionsEl.style.visibility = 'hidden';
        suggestionsEl.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            if (suggestionsEl.style.opacity === '0') {
                suggestionsEl.innerHTML = '';
            }
        }, window.GST_APP.CONFIG.ANIMATION_DURATION);
        
        this.currentIndex = -1;
    }

    handleKeydown(e, suggestionsEl) {
        if (!suggestionsEl.innerHTML) return;
        
        const items = suggestionsEl.querySelectorAll('.suggestion-item');
        if (!items.length) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.currentIndex = Math.min(this.currentIndex + 1, items.length - 1);
                this.updateSelection(items);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.currentIndex = Math.max(this.currentIndex - 1, -1);
                this.updateSelection(items);
                break;
                
            case 'Enter':
                if (this.currentIndex >= 0 && items[this.currentIndex]) {
                    e.preventDefault();
                    items[this.currentIndex].click();
                }
                break;
                
            case 'Escape':
                this.hideSuggestions(suggestionsEl);
                e.target.blur();
                break;
        }
    }

    updateSelection(items) {
        items.forEach((item, index) => {
            if (index === this.currentIndex) {
                item.style.background = 'var(--accent-primary)';
                item.style.color = 'white';
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.style.background = 'transparent';
                item.style.color = '';
            }
        });
    }

    getTypeIcon(type) {
        const icons = {
            tech: 'fas fa-laptop-code',
            telecom: 'fas fa-broadcast-tower',
            industrial: 'fas fa-industry',
            banking: 'fas fa-university',
            recent: 'fas fa-history',
            api: 'fas fa-search',
            default: 'fas fa-building'
        };
        return icons[type] || icons.default;
    }

    getSourceColor(source) {
        const colors = {
            builtin: 'linear-gradient(135deg, #7c3aed, #a855f7)',
            recent: 'linear-gradient(135deg, #10b981, #34d399)',
            api: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
            default: 'linear-gradient(135deg, #6b7280, #9ca3af)'
        };
        return colors[source] || colors.default;
    }
}

// =====================================================
// 3. ENHANCED VALIDATION ENGINE
// =====================================================

class ValidationEngine {
    constructor() {
        this.validators = new Map();
        this.activeFields = new Set();
    }

    initialize() {
        this.setupGSTINValidation();
        this.setupMobileValidation();
        this.setupEmailValidation();
        this.setupPasswordValidation();
        window.GST_APP.utils.log('Validation Engine initialized');
    }

    setupGSTINValidation() {
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin, #gstinEnhanced');
        gstinInputs.forEach(input => {
            if (this.activeFields.has(input)) return;
            this.activeFields.add(input);

            const validator = this.createGSTINValidator(input);
            this.validators.set(input, validator);

            input.addEventListener('input', validator.handleInput);
            input.addEventListener('blur', validator.handleBlur);
            input.addEventListener('paste', validator.handlePaste);
        });
    }

    createGSTINValidator(input) {
        return {
            handleInput: (e) => {
                const value = window.GST_APP.utils.formatGSTIN(e.target.value);
                e.target.value = value;

                if (value.length === 0) {
                    this.clearFieldState(input);
                } else if (value.length === 15) {
                    const isValid = window.GST_APP.utils.isValidGSTIN(value);
                    this.updateFieldState(input, isValid, isValid ? '✅ Valid GSTIN format' : '❌ Invalid GSTIN format');
                    
                    if (isValid) {
                        this.addSuccessEffect(input);
                    } else {
                        this.addErrorEffect(input);
                    }
                } else {
                    this.updateFieldState(input, null, `${value.length}/15 characters`);
                    this.clearEffects(input);
                }
            },

            handleBlur: (e) => {
                const value = window.GST_APP.utils.formatGSTIN(e.target.value);
                if (value.length > 0 && value.length !== 15) {
                    this.updateFieldState(input, false, '❌ GSTIN must be exactly 15 characters');
                }
            },

            handlePaste: (e) => {
                setTimeout(() => {
                    const value = window.GST_APP.utils.formatGSTIN(e.target.value);
                    if (window.GST_APP.utils.isValidGSTIN(value)) {
                        this.addSuccessEffect(input);
                        
                        if (window.notificationManager) {
                            window.notificationManager.showSuccess('✅ Valid GSTIN pasted!', 2000);
                        }
                        
                        // Auto-search if enabled
                        const autoSearch = localStorage.getItem('autoSearch');
                        if (autoSearch !== 'false') {
                            setTimeout(() => {
                                const form = input.closest('form');
                                if (form && window.confirm('Auto-search this GSTIN?')) {
                                    form.submit();
                                }
                            }, 1000);
                        }
                    }
                }, 100);
            }
        };
    }

    setupMobileValidation() {
        const mobileInputs = document.querySelectorAll('input[name="mobile"], input[type="tel"]');
        mobileInputs.forEach(input => {
            if (this.activeFields.has(input)) return;
            this.activeFields.add(input);

            input.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 10) value = value.slice(0, 10);
                e.target.value = value;

                if (value.length === 10) {
                    const isValid = /^[6-9][0-9]{9}$/.test(value);
                    this.updateFieldState(input, isValid, 
                        isValid ? '✅ Valid mobile number' : '❌ Invalid mobile number');
                } else if (value.length > 0) {
                    this.updateFieldState(input, null, `${value.length}/10 digits`);
                } else {
                    this.clearFieldState(input);
                }
            });
        });
    }

    setupEmailValidation() {
        const emailInputs = document.querySelectorAll('input[type="email"]');
        emailInputs.forEach(input => {
            if (this.activeFields.has(input)) return;
            this.activeFields.add(input);

            const debouncedValidation = window.GST_APP.utils.debounce((e) => {
                const value = e.target.value.trim();
                if (value.length === 0) {
                    this.clearFieldState(input);
                } else {
                    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                    this.updateFieldState(input, isValid,
                        isValid ? '✅ Valid email address' : '❌ Invalid email format');
                }
            }, 500);

            input.addEventListener('input', debouncedValidation);
        });
    }

    setupPasswordValidation() {
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        passwordInputs.forEach(input => {
            if (this.activeFields.has(input) || input.name === 'confirm_password') return;
            this.activeFields.add(input);

            input.addEventListener('input', (e) => {
                const strength = this.calculatePasswordStrength(e.target.value);
                this.updatePasswordStrength(input, strength);
            });
        });
    }

    calculatePasswordStrength(password) {
        let score = 0;
        const checks = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            numbers: /[0-9]/.test(password),
            special: /[^A-Za-z0-9]/.test(password)
        };

        score = Object.values(checks).filter(Boolean).length;

        const levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
        const colors = ['#ef4444', '#f59e0b', '#eab308', '#10b981', '#059669'];

        return {
            score,
            level: levels[score] || 'Very Weak',
            color: colors[score] || colors[0],
            percentage: (score / 5) * 100,
            checks
        };
    }

    updatePasswordStrength(input, strength) {
        let strengthIndicator = input.parentElement.querySelector('.password-strength');
        
        if (!strengthIndicator) {
            strengthIndicator = document.createElement('div');
            strengthIndicator.className = 'password-strength';
            strengthIndicator.style.cssText = `
                margin-top: 0.5rem;
                padding: 0.5rem;
                border-radius: 8px;
                background: var(--bg-hover);
                border: 1px solid var(--border-color);
            `;
            input.parentElement.appendChild(strengthIndicator);
        }

        strengthIndicator.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 0.875rem; color: var(--text-primary);">Password Strength</span>
                <span style="font-size: 0.875rem; font-weight: 600; color: ${strength.color};">${strength.level}</span>
            </div>
            <div style="width: 100%; height: 4px; background: var(--bg-secondary); border-radius: 2px; overflow: hidden;">
                <div style="height: 100%; background: ${strength.color}; width: ${strength.percentage}%; transition: all 0.3s ease;"></div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.25rem; margin-top: 0.5rem; font-size: 0.75rem;">
                ${Object.entries(strength.checks).map(([key, passed]) => `
                    <span style="color: ${passed ? '#10b981' : '#6b7280'};">
                        ${passed ? '✓' : '○'} ${key.charAt(0).toUpperCase() + key.slice(1)}
                    </span>
                `).join('')}
            </div>
        `;
    }

    updateFieldState(input, isValid, message) {
        this.clearFieldState(input);

        if (isValid === true) {
            input.style.borderColor = 'var(--success)';
            input.style.backgroundColor = 'rgba(16, 185, 129, 0.05)';
        } else if (isValid === false) {
            input.style.borderColor = 'var(--error)';
            input.style.backgroundColor = 'rgba(239, 68, 68, 0.05)';
        } else {
            input.style.borderColor = 'var(--accent-primary)';
            input.style.backgroundColor = 'var(--bg-input)';
        }

        if (message) {
            this.showFieldMessage(input, message, isValid);
        }
    }

    showFieldMessage(input, message, isValid) {
        const messageEl = document.createElement('div');
        messageEl.className = 'field-message';
        messageEl.style.cssText = `
            margin-top: 0.5rem;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: ${isValid === true ? 'var(--success)' : isValid === false ? 'var(--error)' : 'var(--text-secondary)'};
            animation: messageSlideIn 0.3s ease-out;
        `;
        messageEl.innerHTML = message;
        input.parentElement.appendChild(messageEl);
    }

    clearFieldState(input) {
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        
        const existingMessage = input.parentElement.querySelector('.field-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        this.clearEffects(input);
    }

    addSuccessEffect(input) {
        input.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.3)';
        input.style.transform = 'scale(1.02)';
        setTimeout(() => {
            input.style.transform = '';
        }, 200);
    }

    addErrorEffect(input) {
        input.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.3)';
        input.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            input.style.animation = '';
        }, 500);
    }

    clearEffects(input) {
        input.style.boxShadow = '';
        input.style.transform = '';
        input.style.animation = '';
    }
}

// =====================================================
// 4. INITIALIZATION & EXPORT
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    if (window.GST_APP.state.initialized) return;

    try {
        // Initialize core components
        window.GST_APP.suggestionsEngine = new GSTINSuggestionsEngine();
        window.GST_APP.validationEngine = new ValidationEngine();

        // Initialize components
        window.GST_APP.suggestionsEngine.initialize();
        window.GST_APP.validationEngine.initialize();

        // Add required CSS if not present
        if (!document.getElementById('gst-app-styles')) {
            const style = document.createElement('style');
            style.id = 'gst-app-styles';
            style.textContent = `
                @keyframes messageSlideIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-5px); }
                    75% { transform: translateX(5px); }
                }
                
                .gstin-suggestions::-webkit-scrollbar {
                    width: 6px;
                }
                
                .gstin-suggestions::-webkit-scrollbar-track {
                    background: var(--bg-secondary);
                }
                
                .gstin-suggestions::-webkit-scrollbar-thumb {
                    background: var(--accent-primary);
                    border-radius: 3px;
                }
            `;
            document.head.appendChild(style);
        }

        // Mark as initialized
        window.GST_APP.state.initialized = true;
        
        window.GST_APP.utils.log('Core Application initialized successfully');
        
        // Notify other modules
        window.dispatchEvent(new CustomEvent('gstAppReady', {
            detail: { version: window.GST_APP.VERSION }
        }));

    } catch (error) {
        window.GST_APP.utils.error('Initialization failed:', error);
    }
});

// Global export
window.GST_APP.ready = () => window.GST_APP.state.initialized;

console.log('✅ GST Platform Core Application Loaded Successfully!');