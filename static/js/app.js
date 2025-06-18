// Enhanced GST Intelligence Platform - Advanced Features
// Replace or enhance your existing static/js/app.js with this

console.log('🚀 GST Platform Enhanced Scripts Loading...');

// ===========================================
// 1. ENHANCED GSTIN SUGGESTIONS SYSTEM
// ===========================================

class GSTINSuggestions {
    constructor() {
        this.suggestions = [
            { gstin: '27AABCU9603R1ZX', company: 'UBER INDIA SYSTEMS PRIVATE LIMITED', type: 'tech' },
            { gstin: '19AABCM7407R1ZZ', company: 'MICROSOFT CORPORATION (INDIA) PRIVATE LIMITED', type: 'tech' },
            { gstin: '29AABCT1332L1ZU', company: 'TATA CONSULTANCY SERVICES LIMITED', type: 'tech' },
            { gstin: '27AADCB2230M1ZX', company: 'BHARTI AIRTEL LIMITED', type: 'telecom' },
            { gstin: '07AABCI5602R1ZX', company: 'INFOSYS LIMITED', type: 'tech' },
            { gstin: '36AABCW3775K1ZT', company: 'WIPRO LIMITED', type: 'tech' },
            { gstin: '29AABCH0263N1Z1', company: 'HCL TECHNOLOGIES LIMITED', type: 'tech' },
            { gstin: '19AABCR4849E1ZU', company: 'RELIANCE INDUSTRIES LIMITED', type: 'industrial' },
            { gstin: '27AABCS0618N1ZN', company: 'STATE BANK OF INDIA', type: 'banking' },
            { gstin: '07AABCI9016A1Z7', company: 'ICICI BANK LIMITED', type: 'banking' }
        ];
        this.initSuggestions();
    }

    initSuggestions() {
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin, #gstinEnhanced');
        gstinInputs.forEach(input => this.enhanceInput(input));
    }

    enhanceInput(input) {
        const container = input.parentElement;
        if (!container.querySelector('.search-suggestions')) {
            const suggestionsEl = document.createElement('div');
            suggestionsEl.className = 'search-suggestions';
            container.style.position = 'relative';
            container.appendChild(suggestionsEl);

            input.addEventListener('input', (e) => this.handleInput(e, suggestionsEl));
            input.addEventListener('keydown', (e) => this.handleKeydown(e, suggestionsEl));
            input.addEventListener('blur', () => {
                setTimeout(() => this.hideSuggestions(suggestionsEl), 150);
            });
        }
    }

    handleInput(e, suggestionsEl) {
        const value = e.target.value.trim();
        
        if (value.length < 2) {
            this.hideSuggestions(suggestionsEl);
            return;
        }

        const matches = this.suggestions.filter(item => 
            item.gstin.toLowerCase().includes(value.toLowerCase()) ||
            item.company.toLowerCase().includes(value.toLowerCase())
        );

        if (matches.length > 0) {
            this.showSuggestions(suggestionsEl, matches, e.target);
        } else {
            this.hideSuggestions(suggestionsEl);
        }
    }

    showSuggestions(suggestionsEl, suggestions, input) {
        suggestionsEl.innerHTML = suggestions.map((item, index) => `
            <div class="suggestion-item" data-gstin="${item.gstin}" data-index="${index}">
                <div class="suggestion-icon">
                    <i class="fas ${this.getTypeIcon(item.type)}"></i>
                </div>
                <div class="suggestion-content">
                    <div class="suggestion-title">${item.company}</div>
                    <div class="suggestion-subtitle">${item.gstin}</div>
                </div>
            </div>
        `).join('');

        suggestionsEl.classList.add('show');

        // Add click handlers
        suggestionsEl.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                input.value = item.dataset.gstin;
                this.hideSuggestions(suggestionsEl);
                input.focus();
                
                // Trigger validation
                input.dispatchEvent(new Event('input'));
            });
        });
    }

    hideSuggestions(suggestionsEl) {
        suggestionsEl.classList.remove('show');
        setTimeout(() => {
            suggestionsEl.innerHTML = '';
        }, 300);
    }

    handleKeydown(e, suggestionsEl) {
        const items = suggestionsEl.querySelectorAll('.suggestion-item');
        const selected = suggestionsEl.querySelector('.suggestion-item.selected');
        let selectedIndex = selected ? parseInt(selected.dataset.index) : -1;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.updateSelection(items, selectedIndex);
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                this.updateSelection(items, selectedIndex);
                break;
            case 'Enter':
                if (selected) {
                    e.preventDefault();
                    selected.click();
                }
                break;
            case 'Escape':
                this.hideSuggestions(suggestionsEl);
                break;
        }
    }

    updateSelection(items, selectedIndex) {
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === selectedIndex);
        });
    }

    getTypeIcon(type) {
        const icons = {
            tech: 'fa-laptop-code',
            telecom: 'fa-broadcast-tower',
            industrial: 'fa-industry',
            banking: 'fa-university',
            default: 'fa-building'
        };
        return icons[type] || icons.default;
    }
}

// ===========================================
// 2. ENHANCED REAL-TIME VALIDATION
// ===========================================

class EnhancedValidation {
    constructor() {
        this.initValidation();
    }

    initValidation() {
        // Enhanced GSTIN validation
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin, #gstinEnhanced');
        gstinInputs.forEach(input => {
            input.addEventListener('input', (e) => this.validateGSTIN(e.target));
            input.addEventListener('blur', (e) => this.validateGSTIN(e.target, true));
        });

        // Mobile number validation
        const mobileInputs = document.querySelectorAll('input[name="mobile"], #mobile');
        mobileInputs.forEach(input => {
            input.addEventListener('input', (e) => this.validateMobile(e.target));
        });

        // Email validation
        const emailInputs = document.querySelectorAll('input[type="email"]');
        emailInputs.forEach(input => {
            input.addEventListener('input', (e) => this.validateEmail(e.target));
        });
    }

    validateGSTIN(input, showMessage = false) {
        const value = input.value.trim().toUpperCase();
        const isValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(value);
        
        this.updateFieldState(input, value.length === 15 ? isValid : null, showMessage ? 
            (isValid ? 'Valid GSTIN format' : 'Invalid GSTIN format') : null);
        
        if (isValid) {
            this.addGlowEffect(input, 'rgba(16, 185, 129, 0.5)');
            if (typeof notificationManager !== 'undefined' && showMessage) {
                notificationManager.showSuccess('✅ Valid GSTIN format!', 2000);
            }
        } else if (value.length === 15) {
            this.addGlowEffect(input, 'rgba(239, 68, 68, 0.5)');
        } else {
            this.removeGlowEffect(input);
        }
    }

    validateMobile(input) {
        const value = input.value.trim();
        const isValid = /^[6-9][0-9]{9}$/.test(value);
        
        this.updateFieldState(input, value.length === 10 ? isValid : null, 
            value.length === 10 ? (isValid ? 'Valid mobile number' : 'Invalid mobile number') : null);
    }

    validateEmail(input) {
        const value = input.value.trim();
        const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
        
        this.updateFieldState(input, value.length > 0 ? isValid : null,
            value.length > 0 ? (isValid ? 'Valid email address' : 'Invalid email address') : null);
    }

    updateFieldState(input, isValid, message) {
        // Remove existing states
        input.classList.remove('valid', 'invalid');
        
        // Remove existing message
        const existingMessage = input.parentElement.querySelector('.field-error, .field-success');
        if (existingMessage) {
            existingMessage.remove();
        }

        if (isValid === true) {
            input.classList.add('valid');
            if (message) {
                this.showFieldMessage(input, message, 'success');
            }
        } else if (isValid === false) {
            input.classList.add('invalid');
            if (message) {
                this.showFieldMessage(input, message, 'error');
            }
        }
    }

    showFieldMessage(input, message, type) {
        const messageEl = document.createElement('div');
        messageEl.className = `field-${type}`;
        messageEl.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            ${message}
        `;
        input.parentElement.appendChild(messageEl);
    }

    addGlowEffect(element, color) {
        element.style.boxShadow = `0 0 20px ${color}`;
        element.style.transition = 'box-shadow 0.3s ease';
    }

    removeGlowEffect(element) {
        element.style.boxShadow = '';
    }
}

// ===========================================
// 3. ENHANCED CONTEXT MENU SYSTEM
// ===========================================

class ContextMenu {
    constructor() {
        this.menu = null;
        this.init();
    }

    init() {
        document.addEventListener('contextmenu', (e) => this.handleContextMenu(e));
        document.addEventListener('click', () => this.hide());
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.hide();
        });
    }

    handleContextMenu(e) {
        // Check if right-click is on a GSTIN or company row
        const gstinElement = e.target.closest('[data-gstin], .company-row, .gstin-code');
        
        if (gstinElement) {
            e.preventDefault();
            const gstin = gstinElement.dataset.gstin || 
                         gstinElement.querySelector('.gstin-code')?.textContent ||
                         gstinElement.textContent;
            
            if (gstin && /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin.trim())) {
                this.show(e.clientX, e.clientY, gstin.trim());
            }
        }
    }

    show(x, y, gstin) {
        this.hide();

        this.menu = document.createElement('div');
        this.menu.className = 'context-menu';
        this.menu.innerHTML = `
            <div class="context-menu-item" onclick="contextMenuAction('search', '${gstin}')">
                <i class="fas fa-search"></i>
                <span>Search Company</span>
            </div>
            <div class="context-menu-item" onclick="contextMenuAction('copy', '${gstin}')">
                <i class="fas fa-copy"></i>
                <span>Copy GSTIN</span>
            </div>
            <div class="context-menu-divider"></div>
            <div class="context-menu-item" onclick="contextMenuAction('bookmark', '${gstin}')">
                <i class="fas fa-bookmark"></i>
                <span>Bookmark</span>
            </div>
            <div class="context-menu-item" onclick="contextMenuAction('share', '${gstin}')">
                <i class="fas fa-share"></i>
                <span>Share</span>
            </div>
        `;

        document.body.appendChild(this.menu);

        // Position menu
        const rect = this.menu.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width;
        const maxY = window.innerHeight - rect.height;

        this.menu.style.left = Math.min(x, maxX) + 'px';
        this.menu.style.top = Math.min(y, maxY) + 'px';

        setTimeout(() => {
            this.menu.classList.add('show');
        }, 10);
    }

    hide() {
        if (this.menu) {
            this.menu.classList.remove('show');
            setTimeout(() => {
                if (this.menu) {
                    this.menu.remove();
                    this.menu = null;
                }
            }, 200);
        }
    }
}

// ===========================================
// 4. ENHANCED KEYBOARD SHORTCUTS
// ===========================================

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {
            'ctrl+k': () => this.focusSearch(),
            'ctrl+h': () => this.goToHistory(),
            'ctrl+a': () => this.goToAnalytics(),
            'ctrl+p': () => this.openProfile(),
            'ctrl+s': () => this.openSettings(),
            'ctrl+shift+e': () => this.exportData(),
            'escape': () => this.closeModals(),
            'f1': () => this.showHelp()
        };
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.showShortcutsHint();
    }

    handleKeydown(e) {
        const key = this.getKeyCombo(e);
        if (this.shortcuts[key]) {
            e.preventDefault();
            this.shortcuts[key]();
        }
    }

    getKeyCombo(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        
        if (e.key !== 'Control' && e.key !== 'Shift' && e.key !== 'Alt' && e.key !== 'Meta') {
            parts.push(e.key.toLowerCase());
        }
        
        return parts.join('+');
    }

    focusSearch() {
        const searchInput = document.querySelector('#gstin, #gstinEnhanced, input[name="gstin"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
            if (typeof notificationManager !== 'undefined') {
                notificationManager.showInfo('🔍 Search focused', 1500);
            }
        }
    }

    goToHistory() {
        if (window.location.pathname !== '/history') {
            window.location.href = '/history';
        }
    }

    goToAnalytics() {
        if (window.location.pathname !== '/analytics') {
            window.location.href = '/analytics';
        }
    }

    openProfile() {
        if (typeof openEnhancedProfileModal === 'function') {
            openEnhancedProfileModal();
        }
    }

    openSettings() {
        if (typeof openSettingsModal === 'function') {
            openSettingsModal();
        }
    }

    exportData() {
        window.location.href = '/export/history';
    }

    closeModals() {
        // Close user dropdown
        const userDropdown = document.getElementById('userDropdownMenu');
        if (userDropdown && userDropdown.classList.contains('active')) {
            if (typeof closeUserDropdown === 'function') {
                closeUserDropdown();
            }
        }

        // Close modals
        if (typeof modalManager !== 'undefined') {
            modalManager.closeAllModals();
        }

        // Hide context menu
        if (window.contextMenu) {
            window.contextMenu.hide();
        }
    }

    showHelp() {
        if (typeof modalManager !== 'undefined') {
            modalManager.createModal({
                title: '⌨️ Keyboard Shortcuts',
                content: `
                    <div style="display: grid; gap: 1rem;">
                        <div class="shortcut-item">
                            <kbd>Ctrl + K</kbd>
                            <span>Focus search input</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl + H</kbd>
                            <span>Go to history page</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl + A</kbd>
                            <span>Go to analytics page</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl + P</kbd>
                            <span>Open profile settings</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl + S</kbd>
                            <span>Open settings</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl + Shift + E</kbd>
                            <span>Export data</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Escape</kbd>
                            <span>Close modals/dropdowns</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>F1</kbd>
                            <span>Show this help</span>
                        </div>
                    </div>
                    <style>
                        .shortcut-item {
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 0.75rem;
                            background: var(--bg-hover);
                            border-radius: 8px;
                        }
                        kbd {
                            background: var(--bg-card);
                            border: 1px solid var(--border-color);
                            border-radius: 4px;
                            padding: 0.25rem 0.5rem;
                            font-family: monospace;
                            font-size: 0.875rem;
                            color: var(--accent-primary);
                        }
                    </style>
                `
            });
        }
    }

    showShortcutsHint() {
        if (!localStorage.getItem('shortcutsHintShown')) {
            setTimeout(() => {
                if (typeof notificationManager !== 'undefined') {
                    notificationManager.showInfo('💡 Press F1 for keyboard shortcuts', 5000);
                    localStorage.setItem('shortcutsHintShown', 'true');
                }
            }, 3000);
        }
    }
}

// ===========================================
// 5. ENHANCED PERFORMANCE MONITORING
// ===========================================

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            searchTime: 0,
            apiCalls: 0,
            errors: 0
        };
        this.init();
    }

    init() {
        // Monitor page load time
        window.addEventListener('load', () => {
            this.metrics.pageLoadTime = performance.now();
            this.reportMetric('page_load', this.metrics.pageLoadTime);
        });

        // Monitor API calls
        this.interceptFetch();

        // Monitor errors
        window.addEventListener('error', (e) => {
            this.metrics.errors++;
            this.reportError(e.error);
        });
    }

    interceptFetch() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            this.metrics.apiCalls++;
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                this.reportMetric('api_call', endTime - startTime);
                return response;
            } catch (error) {
                this.metrics.errors++;
                this.reportError(error);
                throw error;
            }
        };
    }

    reportMetric(name, value) {
        if (window.gtag) {
            window.gtag('event', name, {
                event_category: 'performance',
                value: Math.round(value)
            });
        }
        
        console.log(`📊 Performance: ${name} = ${Math.round(value)}ms`);
    }

    reportError(error) {
        console.error('🚨 Error tracked:', error);
        
        if (window.gtag) {
            window.gtag('event', 'exception', {
                description: error.message || 'Unknown error',
                fatal: false
            });
        }
    }

    getMetrics() {
        return {
            ...this.metrics,
            memoryUsage: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) : 'N/A'
        };
    }
}

// ===========================================
// 6. GLOBAL CONTEXT MENU ACTIONS
// ===========================================

window.contextMenuAction = function(action, gstin) {
    switch (action) {
        case 'search':
            const form = document.createElement('form');
            form.method = 'GET';
            form.action = '/search';
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'gstin';
            input.value = gstin;
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
            break;
            
        case 'copy':
            navigator.clipboard.writeText(gstin).then(() => {
                if (typeof notificationManager !== 'undefined') {
                    notificationManager.showSuccess(`📋 GSTIN ${gstin} copied to clipboard!`, 3000);
                }
            });
            break;
            
        case 'bookmark':
            const bookmarks = JSON.parse(localStorage.getItem('gstinBookmarks') || '[]');
            if (!bookmarks.includes(gstin)) {
                bookmarks.push(gstin);
                localStorage.setItem('gstinBookmarks', JSON.stringify(bookmarks));
                if (typeof notificationManager !== 'undefined') {
                    notificationManager.showSuccess(`🔖 GSTIN ${gstin} bookmarked!`, 3000);
                }
            } else {
                if (typeof notificationManager !== 'undefined') {
                    notificationManager.showInfo('📌 Already bookmarked', 2000);
                }
            }
            break;
            
        case 'share':
            if (navigator.share) {
                navigator.share({
                    title: 'GST Company Information',
                    text: `Check out this GSTIN: ${gstin}`,
                    url: `${window.location.origin}/search?gstin=${gstin}`
                });
            } else {
                const shareUrl = `${window.location.origin}/search?gstin=${gstin}`;
                navigator.clipboard.writeText(shareUrl).then(() => {
                    if (typeof notificationManager !== 'undefined') {
                        notificationManager.showSuccess('🔗 Share link copied to clipboard!', 3000);
                    }
                });
            }
            break;
    }
    
    if (window.contextMenu) {
        window.contextMenu.hide();
    }
};

// ===========================================
// 7. INITIALIZATION
// ===========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Initializing enhanced features...');
    
    // Initialize all enhanced features
    window.gstinSuggestions = new GSTINSuggestions();
    window.enhancedValidation = new EnhancedValidation();
    window.contextMenu = new ContextMenu();
    window.keyboardShortcuts = new KeyboardShortcuts();
    window.performanceMonitor = new PerformanceMonitor();
    
    console.log('✅ All enhanced features initialized successfully!');
    
    // Show enhanced welcome message
    if (!localStorage.getItem('enhancedFeaturesShown') && typeof notificationManager !== 'undefined') {
        setTimeout(() => {
            notificationManager.showSuccess('🎉 Enhanced features loaded! Try right-clicking on GSTIN numbers and press F1 for shortcuts.', 6000);
            localStorage.setItem('enhancedFeaturesShown', 'true');
        }, 2000);
    }
});

// ===========================================
// 8. EXPORT FOR DEBUGGING
// ===========================================

window.GST_ENHANCED = {
    gstinSuggestions: () => window.gstinSuggestions,
    validation: () => window.enhancedValidation,
    contextMenu: () => window.contextMenu,
    shortcuts: () => window.keyboardShortcuts,
    performance: () => window.performanceMonitor,
    getMetrics: () => window.performanceMonitor?.getMetrics() || {}
};

console.log('🎉 GST Intelligence Platform Enhanced Scripts Loaded Successfully!');