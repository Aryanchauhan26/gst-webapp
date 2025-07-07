// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts Module
// Enhanced keyboard navigation and accessibility
// =====================================================

'use strict';

// Only initialize if not already loaded
if (!window.KeyboardShortcuts) {
    // Keyboard Shortcuts Manager
    class KeyboardShortcuts {
        constructor() {
            console.log('⌨️ Keyboard Shortcuts Loading...');
            this.shortcuts = new Map();
            this.isEnabled = true;
            this.setupDefaultShortcuts();
            this.bindEvents();
        }

        setupDefaultShortcuts() {
            // Define default keyboard shortcuts
            this.shortcuts.set('ctrl+/', () => this.showHelp());
            this.shortcuts.set('ctrl+k', () => this.focusSearch());
            this.shortcuts.set('escape', () => this.closeModals());
        }

        bindEvents() {
            document.addEventListener('keydown', (event) => {
                if (!this.isEnabled) return;

                const key = this.getKeyString(event);
                const handler = this.shortcuts.get(key);

                if (handler) {
                    event.preventDefault();
                    handler();
                }
            });
        }

        getKeyString(event) {
            const parts = [];

            if (event.ctrlKey) parts.push('ctrl');
            if (event.altKey) parts.push('alt');
            if (event.shiftKey) parts.push('shift');
            if (event.metaKey) parts.push('meta');

            parts.push(event.key.toLowerCase());

            return parts.join('+');
        }

        showHelp() {
            console.log('⌨️ Showing keyboard shortcuts help');
            // Implementation for showing help modal
        }

        focusSearch() {
            const searchInput = document.querySelector('input[type="search"], #gstinInput, .search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        closeModals() {
            const modals = document.querySelectorAll('.modal, .overlay, .popup');
            modals.forEach(modal => {
                if (modal.style.display === 'block' || modal.classList.contains('active')) {
                    modal.style.display = 'none';
                    modal.classList.remove('active');
                }
            });
        }

        addShortcut(key, handler) {
            this.shortcuts.set(key, handler);
        }

        removeShortcut(key) {
            this.shortcuts.delete(key);
        }

        enable() {
            this.isEnabled = true;
        }

        disable() {
            this.isEnabled = false;
        }
    }

    // Store class globally and initialize
    window.KeyboardShortcuts = KeyboardShortcuts;

    // Initialize keyboard shortcuts
    if (!window.keyboardShortcuts) {
        window.keyboardShortcuts = new KeyboardShortcuts();
        console.log('⌨️ Keyboard Shortcuts initialized');
    }
}