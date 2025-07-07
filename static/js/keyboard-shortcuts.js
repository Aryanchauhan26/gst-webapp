// GST Intelligence Platform - Keyboard Shortcuts Module
'use strict';

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = new Map();
        this.isEnabled = true;
        this.init();
    }

    init() {
        document.addEventListener('keydown', this.handleKeydown.bind(this));
        this.registerDefaultShortcuts();
        console.log('✅ Keyboard shortcuts initialized');
    }

    registerDefaultShortcuts() {
        // Search focus
        this.register('ctrl+k', () => {
            const searchInput = document.getElementById('gstinEnhanced') || 
                              document.querySelector('input[type="search"]') ||
                              document.querySelector('input[placeholder*="GSTIN"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        });

        // Navigation shortcuts
        this.register('ctrl+h', () => window.location.href = '/history');
        this.register('ctrl+a', () => window.location.href = '/analytics');
        this.register('ctrl+d', () => window.location.href = '/');
        
        // Theme toggle
        this.register('ctrl+shift+t', () => {
            if (window.themeManager) {
                window.themeManager.toggleTheme();
            }
        });

        // Modal management
        this.register('escape', () => {
            if (window.modalManager) {
                window.modalManager.closeAllModals();
            }
        });
    }

    register(combo, callback, description = '') {
        const normalizedCombo = this.normalizeCombo(combo);
        this.shortcuts.set(normalizedCombo, { callback, description });
    }

    unregister(combo) {
        const normalizedCombo = this.normalizeCombo(combo);
        this.shortcuts.delete(normalizedCombo);
    }

    handleKeydown(event) {
        if (!this.isEnabled || this.shouldIgnoreEvent(event)) {
            return;
        }

        try {
            const combo = this.getKeyCombo(event);
            if (combo && this.shortcuts.has(combo)) {
                event.preventDefault();
                const shortcut = this.shortcuts.get(combo);
                shortcut.callback(event);
            }
        } catch (error) {
            console.error('Keyboard shortcut error:', error);
        }
    }

    getKeyCombo(event) {
        if (!event || !event.key) return null;

        const parts = [];
        
        // Add modifiers
        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        if (event.metaKey) parts.push('meta');
        
        // Add main key (safely handle undefined)
        const key = event.key ? event.key.toLowerCase() : '';
        if (key) parts.push(key);
        
        return parts.length > 0 ? parts.join('+') : null;
    }

    normalizeCombo(combo) {
        if (!combo || typeof combo !== 'string') return '';
        
        return combo.toLowerCase()
                   .split('+')
                   .map(part => part.trim())
                   .filter(part => part.length > 0)
                   .sort((a, b) => {
                       const order = ['ctrl', 'alt', 'shift', 'meta'];
                       const aIndex = order.indexOf(a);
                       const bIndex = order.indexOf(b);
                       if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
                       if (aIndex !== -1) return -1;
                       if (bIndex !== -1) return 1;
                       return a.localeCompare(b);
                   })
                   .join('+');
    }

    shouldIgnoreEvent(event) {
        const target = event.target;
        if (!target) return false;

        const tagName = target.tagName ? target.tagName.toLowerCase() : '';
        const isInput = ['input', 'textarea', 'select'].includes(tagName);
        const isContentEditable = target.contentEditable === 'true';
        
        return isInput || isContentEditable;
    }

    enable() {
        this.isEnabled = true;
    }

    disable() {
        this.isEnabled = false;
    }

    getRegisteredShortcuts() {
        return Array.from(this.shortcuts.entries()).map(([combo, shortcut]) => ({
            combo,
            description: shortcut.description
        }));
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.keyboardShortcuts = new KeyboardShortcuts();
    });
} else {
    window.keyboardShortcuts = new KeyboardShortcuts();
}
// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts
// =====================================================

'use strict';

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        console.log('⌨️ Keyboard shortcuts initialized');
        this.setupShortcuts();
        this.bindEvents();
    }

    setupShortcuts() {
        // Global shortcuts
        this.addShortcut('ctrl+/', () => this.showShortcutsHelp());
        this.addShortcut('ctrl+k', () => this.focusSearch());
        this.addShortcut('escape', () => this.closeModals());
        
        // Navigation shortcuts
        this.addShortcut('alt+h', () => window.location.href = '/');
        this.addShortcut('alt+s', () => window.location.href = '/history');
        this.addShortcut('alt+a', () => window.location.href = '/analytics');
    }

    addShortcut(key, callback) {
        this.shortcuts.set(key, callback);
    }

    bindEvents() {
        document.addEventListener('keydown', (event) => {
            const key = this.getKeyString(event);
            if (this.shortcuts.has(key)) {
                event.preventDefault();
                this.shortcuts.get(key)();
            }
        });
    }

    getKeyString(event) {
        const parts = [];
        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        parts.push(event.key.toLowerCase());
        return parts.join('+');
    }

    focusSearch() {
        const searchInput = document.querySelector('#gstin-input, .search-input, input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    closeModals() {
        const modals = document.querySelectorAll('.modal.active, .dropdown.active');
        modals.forEach(modal => modal.classList.remove('active'));
    }

    showShortcutsHelp() {
        // Show shortcuts help modal or tooltip
        console.log('Keyboard shortcuts help requested');
    }
}

// Initialize keyboard shortcuts
document.addEventListener('DOMContentLoaded', () => {
    new KeyboardShortcuts();
});
