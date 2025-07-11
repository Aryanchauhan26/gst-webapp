// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts Module (FIXED)
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

                try {
                    const key = this.getKeyCombo(event);
                    const handler = this.shortcuts.get(key);

                    if (handler) {
                        event.preventDefault();
                        handler();
                    }
                } catch (error) {
                    console.error('Keyboard shortcut error:', error);
                }
            });
        }

        getKeyCombo(event) {
            // FIXED: Add comprehensive null/undefined checks
            if (!event) {
                console.warn('No event provided to getKeyCombo');
                return '';
            }

            const parts = [];

            // Check for modifier keys
            if (event.ctrlKey) parts.push('ctrl');
            if (event.altKey) parts.push('alt');
            if (event.shiftKey) parts.push('shift');
            if (event.metaKey) parts.push('meta');

            // FIXED: Robust key handling with multiple fallbacks
            let key = null;
            
            if (event.key && typeof event.key === 'string') {
                key = event.key;
            } else if (event.code && typeof event.code === 'string') {
                key = event.code;
            } else if (event.keyCode && typeof event.keyCode === 'number') {
                // Fallback to keyCode mapping
                key = this.getKeyFromCode(event.keyCode);
            }

            if (key && typeof key === 'string') {
                parts.push(key.toLowerCase());
            } else {
                console.warn('Could not determine key from event:', event);
                return '';
            }

            return parts.join('+');
        }

        getKeyFromCode(keyCode) {
            // Basic keyCode to key mapping for fallback
            const keyMap = {
                27: 'escape',
                13: 'enter',
                32: ' ',
                191: '/',
                75: 'k'
            };
            return keyMap[keyCode] || String.fromCharCode(keyCode);
        }

        showHelp() {
            console.log('⌨️ Showing keyboard shortcuts help');
            // Implementation for showing help modal
        }

        focusSearch() {
            const searchInput = document.querySelector('input[type="search"], #gstinInput, .search-input, input[name="gstin"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        closeModals() {
            const modals = document.querySelectorAll('.modal, .overlay, .popup, .modal-overlay');
            modals.forEach(modal => {
                if (modal.style.display === 'block' || modal.classList.contains('active')) {
                    modal.style.display = 'none';
                    modal.classList.remove('active');
                }
            });
        }

        addShortcut(key, handler) {
            if (typeof key === 'string' && typeof handler === 'function') {
                this.shortcuts.set(key, handler);
            }
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

        destroy() {
            this.shortcuts.clear();
            this.isEnabled = false;
            // Remove event listeners if needed
        }
    }

    // Store class globally and initialize
    window.KeyboardShortcuts = KeyboardShortcuts;

    // Initialize keyboard shortcuts with error handling
    try {
        if (!window.keyboardShortcuts) {
            window.keyboardShortcuts = new KeyboardShortcuts();
            console.log('⌨️ Keyboard Shortcuts initialized successfully');
        }
    } catch (error) {
        console.error('❌ Failed to initialize Keyboard Shortcuts:', error);
    }
}