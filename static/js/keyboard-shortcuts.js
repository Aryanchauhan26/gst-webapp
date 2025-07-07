// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts Module
// =====================================================

'use strict';

// Only declare if not already declared
if (typeof KeyboardShortcuts === 'undefined') {
    class KeyboardShortcuts {
        constructor() {
            this.shortcuts = new Map();
            this.isEnabled = true;
            this.init();
        }

        init() {
            console.log('⌨️ Keyboard Shortcuts initialized');
            this.setupDefaultShortcuts();
            this.bindEvents();
        }

        setupDefaultShortcuts() {
            // Search shortcut
            this.register('ctrl+k', () => {
                const searchInput = document.querySelector('#gstinInput, .search-input, input[type="search"]');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            });

            // Navigation shortcuts
            this.register('ctrl+h', () => {
                window.location.href = '/';
            });

            this.register('ctrl+shift+h', () => {
                window.location.href = '/history';
            });

            this.register('ctrl+shift+a', () => {
                window.location.href = '/analytics';
            });

            // Help shortcut
            this.register('ctrl+shift+?', () => {
                this.showShortcutsHelp();
            });

            // Toggle theme
            this.register('ctrl+shift+t', () => {
                if (typeof toggleTheme === 'function') {
                    toggleTheme();
                }
            });
        }

        register(shortcut, callback) {
            this.shortcuts.set(shortcut.toLowerCase(), callback);
        }

        bindEvents() {
            document.addEventListener('keydown', (event) => {
                if (!this.isEnabled) return;

                const shortcut = this.getShortcutString(event);
                const callback = this.shortcuts.get(shortcut);

                if (callback) {
                    event.preventDefault();
                    callback(event);
                }
            });
        }

        getShortcutString(event) {
            const parts = [];

            if (event.ctrlKey) parts.push('ctrl');
            if (event.altKey) parts.push('alt');
            if (event.shiftKey) parts.push('shift');
            if (event.metaKey) parts.push('meta');

            if (event.key && event.key !== 'Control' && event.key !== 'Alt' && event.key !== 'Shift' && event.key !== 'Meta') {
                parts.push(event.key.toLowerCase());
            }

            return parts.join('+');
        }

        showShortcutsHelp() {
            const helpModal = document.createElement('div');
            helpModal.className = 'shortcuts-help-modal';
            helpModal.innerHTML = `
                <div class="shortcuts-help-content">
                    <h3>Keyboard Shortcuts</h3>
                    <div class="shortcuts-list">
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>K</kbd>
                            <span>Focus search</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>H</kbd>
                            <span>Go to home</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>H</kbd>
                            <span>Go to history</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>A</kbd>
                            <span>Go to analytics</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd>
                            <span>Toggle theme</span>
                        </div>
                    </div>
                    <button onclick="this.closest('.shortcuts-help-modal').remove()">Close</button>
                </div>
            `;

            document.body.appendChild(helpModal);

            // Auto remove after 5 seconds
            setTimeout(() => {
                if (helpModal.parentNode) {
                    helpModal.remove();
                }
            }, 5000);
        }

        enable() {
            this.isEnabled = true;
        }

        disable() {
            this.isEnabled = false;
        }
    }

    // Initialize keyboard shortcuts
    window.keyboardShortcuts = new KeyboardShortcuts();
}