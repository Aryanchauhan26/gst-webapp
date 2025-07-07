
// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts Module
// =====================================================

'use strict';

// Only initialize if not already initialized
if (typeof window.keyboardShortcuts === 'undefined') {
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
            helpModal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;
            
            helpModal.innerHTML = `
                <div class="shortcuts-help-content" style="
                    background: var(--bg-card);
                    border-radius: 12px;
                    padding: 2rem;
                    max-width: 500px;
                    width: 90%;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                ">
                    <h3 style="margin-bottom: 1.5rem; color: var(--text-primary);">Keyboard Shortcuts</h3>
                    <div class="shortcuts-list" style="display: grid; gap: 0.75rem;">
                        <div class="shortcut-item" style="display: flex; justify-content: space-between; align-items: center;">
                            <div><kbd>Ctrl</kbd> + <kbd>K</kbd></div>
                            <span>Focus search</span>
                        </div>
                        <div class="shortcut-item" style="display: flex; justify-content: space-between; align-items: center;">
                            <div><kbd>Ctrl</kbd> + <kbd>H</kbd></div>
                            <span>Go to home</span>
                        </div>
                        <div class="shortcut-item" style="display: flex; justify-content: space-between; align-items: center;">
                            <div><kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>H</kbd></div>
                            <span>Go to history</span>
                        </div>
                        <div class="shortcut-item" style="display: flex; justify-content: space-between; align-items: center;">
                            <div><kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>A</kbd></div>
                            <span>Go to analytics</span>
                        </div>
                        <div class="shortcut-item" style="display: flex; justify-content: space-between; align-items: center;">
                            <div><kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd></div>
                            <span>Toggle theme</span>
                        </div>
                    </div>
                    <button onclick="this.closest('.shortcuts-help-modal').remove()" 
                            style="margin-top: 1.5rem; padding: 0.5rem 1rem; background: var(--accent-primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                        Close
                    </button>
                </div>
            `;

            document.body.appendChild(helpModal);

            // Auto remove after 10 seconds or on click outside
            const autoRemove = setTimeout(() => {
                if (helpModal.parentNode) {
                    helpModal.remove();
                }
            }, 10000);

            helpModal.addEventListener('click', (e) => {
                if (e.target === helpModal) {
                    clearTimeout(autoRemove);
                    helpModal.remove();
                }
            });
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
