
// =====================================================
// GST Intelligence Platform - Keyboard Shortcuts Module
// Enhanced keyboard navigation and accessibility
// =====================================================

'use strict';

// Only initialize if not already loaded
if (!window.keyboardShortcuts) {
    console.log('⌨️ Keyboard Shortcuts Loading...');

    class KeyboardShortcuts {
        constructor() {
            this.shortcuts = new Map();
            this.isEnabled = true;
            this.activeModals = [];
            this.init();
        }

        init() {
            this.registerDefaultShortcuts();
            this.attachEventListeners();
            console.log('⌨️ Keyboard Shortcuts initialized');
        }

        registerDefaultShortcuts() {
            // Global shortcuts
            this.register('/', () => this.focusSearch(), { description: 'Focus search input' });
            this.register('Escape', () => this.handleEscape(), { description: 'Close modals/clear focus' });
            this.register('?', () => this.showHelp(), { shift: true, description: 'Show keyboard shortcuts help' });
            
            // Navigation shortcuts
            this.register('g h', () => this.navigate('/'), { description: 'Go to home/dashboard' });
            this.register('g s', () => this.navigate('/search'), { description: 'Go to search' });
            this.register('g h', () => this.navigate('/history'), { description: 'Go to history' });
            this.register('g a', () => this.navigate('/analytics'), { description: 'Go to analytics' });
            
            // Form shortcuts
            this.register('ctrl+Enter', () => this.submitActiveForm(), { description: 'Submit active form' });
            this.register('Tab', () => this.handleTabNavigation(), { description: 'Navigate form fields' });
        }

        register(combination, callback, options = {}) {
            const key = this.normalizeShortcut(combination);
            this.shortcuts.set(key, {
                callback,
                description: options.description || '',
                ctrl: options.ctrl || false,
                shift: options.shift || false,
                alt: options.alt || false,
                preventDefault: options.preventDefault !== false
            });
        }

        normalizeShortcut(combination) {
            return combination.toLowerCase().trim();
        }

        attachEventListeners() {
            document.addEventListener('keydown', (e) => {
                if (!this.isEnabled) return;
                
                this.handleKeydown(e);
            });

            // Handle focus management
            document.addEventListener('focusin', (e) => {
                this.handleFocusIn(e);
            });
        }

        handleKeydown(e) {
            // Skip if user is typing in input fields
            if (this.isInputActive(e.target)) {
                if (e.key === 'Escape') {
                    e.target.blur();
                }
                return;
            }

            const shortcut = this.buildShortcutKey(e);
            const action = this.shortcuts.get(shortcut);

            if (action) {
                if (action.preventDefault) {
                    e.preventDefault();
                }
                action.callback(e);
            }
        }

        buildShortcutKey(e) {
            let key = e.key.toLowerCase();
            
            if (e.ctrlKey && key !== 'control') key = `ctrl+${key}`;
            if (e.altKey && key !== 'alt') key = `alt+${key}`;
            if (e.shiftKey && key !== 'shift' && key.length > 1) key = `shift+${key}`;
            
            return key;
        }

        isInputActive(element) {
            const tagName = element.tagName.toLowerCase();
            return (
                tagName === 'input' ||
                tagName === 'textarea' ||
                tagName === 'select' ||
                element.contentEditable === 'true' ||
                element.isContentEditable
            );
        }

        // Shortcut actions
        focusSearch() {
            const searchInput = document.querySelector('input[name="gstin"], #searchInput, .search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        handleEscape() {
            // Close modals
            const modals = document.querySelectorAll('.modal.show, .modal.active');
            modals.forEach(modal => {
                modal.classList.remove('show', 'active');
            });

            // Clear focus
            if (document.activeElement) {
                document.activeElement.blur();
            }

            // Close dropdowns
            const dropdowns = document.querySelectorAll('.dropdown.show, .dropdown.active');
            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('show', 'active');
            });
        }

        navigate(path) {
            window.location.href = path;
        }

        submitActiveForm() {
            const activeForm = document.querySelector('form:focus-within, form:has(:focus)');
            if (activeForm) {
                const submitBtn = activeForm.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.click();
                }
            }
        }

        handleTabNavigation() {
            // Enhanced tab navigation for forms
            const focusedElement = document.activeElement;
            if (focusedElement && focusedElement.form) {
                const formElements = Array.from(focusedElement.form.elements);
                const currentIndex = formElements.indexOf(focusedElement);
                const nextIndex = (currentIndex + 1) % formElements.length;
                formElements[nextIndex]?.focus();
            }
        }

        showHelp() {
            const shortcuts = Array.from(this.shortcuts.entries())
                .filter(([key, action]) => action.description)
                .map(([key, action]) => ({ key, description: action.description }));

            this.displayShortcutsModal(shortcuts);
        }

        displayShortcutsModal(shortcuts) {
            // Create and show shortcuts help modal
            const modal = document.createElement('div');
            modal.className = 'keyboard-shortcuts-modal';
            modal.innerHTML = `
                <div class="modal-overlay">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3>Keyboard Shortcuts</h3>
                            <button class="close-btn" onclick="this.closest('.keyboard-shortcuts-modal').remove()">×</button>
                        </div>
                        <div class="modal-body">
                            <div class="shortcuts-grid">
                                ${shortcuts.map(shortcut => `
                                    <div class="shortcut-item">
                                        <kbd class="shortcut-key">${shortcut.key}</kbd>
                                        <span class="shortcut-desc">${shortcut.description}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Add styles if not present
            if (!document.getElementById('keyboard-shortcuts-styles')) {
                const style = document.createElement('style');
                style.id = 'keyboard-shortcuts-styles';
                style.textContent = `
                    .keyboard-shortcuts-modal {
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        z-index: 10000;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    
                    .keyboard-shortcuts-modal .modal-overlay {
                        background: rgba(0, 0, 0, 0.8);
                        position: absolute;
                        inset: 0;
                    }
                    
                    .keyboard-shortcuts-modal .modal-content {
                        background: var(--bg-card);
                        border-radius: 12px;
                        max-width: 600px;
                        width: 90%;
                        max-height: 80vh;
                        overflow-y: auto;
                        position: relative;
                        z-index: 1;
                    }
                    
                    .keyboard-shortcuts-modal .modal-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 1.5rem;
                        border-bottom: 1px solid var(--border-color);
                    }
                    
                    .keyboard-shortcuts-modal .close-btn {
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                        color: var(--text-secondary);
                    }
                    
                    .shortcuts-grid {
                        display: grid;
                        gap: 1rem;
                        padding: 1.5rem;
                    }
                    
                    .shortcut-item {
                        display: flex;
                        align-items: center;
                        gap: 1rem;
                    }
                    
                    .shortcut-key {
                        background: var(--bg-secondary);
                        border: 1px solid var(--border-color);
                        border-radius: 4px;
                        padding: 0.25rem 0.5rem;
                        font-family: monospace;
                        min-width: 80px;
                        text-align: center;
                    }
                    
                    .shortcut-desc {
                        color: var(--text-secondary);
                    }
                `;
                document.head.appendChild(style);
            }

            document.body.appendChild(modal);

            // Close on overlay click
            modal.querySelector('.modal-overlay').addEventListener('click', () => {
                modal.remove();
            });

            // Close on escape
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
        }

        handleFocusIn(e) {
            // Add focus indicators and accessibility
            if (e.target.matches('input, button, select, textarea, [tabindex]')) {
                e.target.classList.add('keyboard-focused');
            }
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
        }
    }

    // Initialize keyboard shortcuts
    window.keyboardShortcuts = new KeyboardShortcuts();
} else {
    console.log('⌨️ Keyboard Shortcuts already initialized');
}
