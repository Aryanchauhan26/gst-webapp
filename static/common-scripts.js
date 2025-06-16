// GST Intelligence Platform - Enhanced Common Scripts
// Complete JavaScript Framework - Clean and Consistent

console.log('🚀 GST Platform Scripts Loading...');

// Global configuration
const GST_CONFIG = {
    TOOLTIP_DELAY: 300,
    TOOLTIP_HIDE_DELAY: 100,
    ANIMATION_DURATION: 300,
    THEME_STORAGE_KEY: 'gst_theme',
    USER_PREFERENCES_KEY: 'gst_user_preferences',
    DEBUG: false
};

// Debug logging
function debugLog(message, ...args) {
    if (GST_CONFIG.DEBUG) {
        console.log(`[GST Debug] ${message}`, ...args);
    }
}

// ===========================================
// 1. ENHANCED TOOLTIP SYSTEM
// ===========================================

class TooltipManager {
    constructor() {
        this.tooltipContainer = null;
        this.currentTarget = null;
        this.showTimeout = null;
        this.hideTimeout = null;
        this.init();
    }

    init() {
        // Remove any existing tooltip containers
        document.querySelectorAll('.gst-tooltip-container').forEach(el => el.remove());
        
        // Create single tooltip container
        this.tooltipContainer = document.createElement('div');
        this.tooltipContainer.className = 'gst-tooltip-container';
        this.tooltipContainer.style.cssText = `
            position: fixed;
            pointer-events: none;
            z-index: 99999;
            opacity: 0;
            transition: opacity 0.2s ease;
            max-width: 300px;
        `;
        
        const tooltipContent = document.createElement('div');
        tooltipContent.className = 'gst-tooltip-content';
        tooltipContent.style.cssText = `
            background: #1a1a1a;
            color: #fff;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.4;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            word-wrap: break-word;
            border: 1px solid #333;
            backdrop-filter: blur(10px);
        `;
        
        this.tooltipContainer.appendChild(tooltipContent);
        document.body.appendChild(this.tooltipContainer);
        
        // Bind events
        this.bindEvents();
        
        debugLog('Enhanced tooltip system initialized');
    }

    bindEvents() {
        // Use event delegation for better performance
        document.addEventListener('mouseenter', (e) => {
            const target = e.target.closest('[data-tooltip], [title]');
            if (target && target !== this.currentTarget) {
                this.clearTimeouts();
                this.showTimeout = setTimeout(() => this.showTooltip(target), GST_CONFIG.TOOLTIP_DELAY);
            }
        }, true);
        
        document.addEventListener('mouseleave', (e) => {
            const target = e.target.closest('[data-tooltip], [title]');
            if (target && target === this.currentTarget) {
                this.clearTimeouts();
                this.hideTimeout = setTimeout(() => this.hideTooltip(), GST_CONFIG.TOOLTIP_HIDE_DELAY);
            }
        }, true);
        
        // Hide on scroll and resize
        window.addEventListener('scroll', () => this.hideTooltip(), { passive: true });
        window.addEventListener('resize', () => this.hideTooltip());
    }

    showTooltip(target) {
        const text = target.getAttribute('data-tooltip') || target.getAttribute('title');
        if (!text) return;
        
        // Store original title and replace with data-tooltip
        if (target.hasAttribute('title')) {
            target.setAttribute('data-tooltip', text);
            target.removeAttribute('title');
        }
        
        this.currentTarget = target;
        const tooltipContent = this.tooltipContainer.querySelector('.gst-tooltip-content');
        tooltipContent.textContent = text;
        
        // Position tooltip
        requestAnimationFrame(() => {
            this.positionTooltip(target);
            this.tooltipContainer.style.opacity = '1';
        });
        
        debugLog('Tooltip shown for:', target, 'Text:', text);
    }

    positionTooltip(target) {
        const rect = target.getBoundingClientRect();
        const tooltipRect = this.tooltipContainer.getBoundingClientRect();
        
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 10;
        
        // Adjust for viewport boundaries
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10;
        }
        
        this.tooltipContainer.style.left = left + 'px';
        this.tooltipContainer.style.top = top + 'px';
    }

    hideTooltip() {
        this.currentTarget = null;
        this.tooltipContainer.style.opacity = '0';
        debugLog('Tooltip hidden');
    }

    clearTimeouts() {
        if (this.showTimeout) {
            clearTimeout(this.showTimeout);
            this.showTimeout = null;
        }
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }
    }
}

// ===========================================
// 2. ENHANCED THEME SYSTEM
// ===========================================

class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.init();
    }

    init() {
        // Load saved theme
        const savedTheme = localStorage.getItem(GST_CONFIG.THEME_STORAGE_KEY) || 'dark';
        this.setTheme(savedTheme, false);
        this.updateAllThemeIndicators();
        
        debugLog('Enhanced theme system initialized with theme:', savedTheme);
    }

    setTheme(theme, save = true) {
        this.currentTheme = theme;
        
        // Apply theme to body with smooth transition
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        
        if (theme === 'light') {
            document.body.classList.add('light-theme');
        } else {
            document.body.classList.remove('light-theme');
        }
        
        // Save to localStorage
        if (save) {
            localStorage.setItem(GST_CONFIG.THEME_STORAGE_KEY, theme);
        }
        
        // Update all theme indicators
        this.updateAllThemeIndicators();
        
        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
        
        debugLog('Theme set to:', theme);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        
        // Show enhanced feedback
        this.showThemeChangeNotification(newTheme);
        
        debugLog('Theme toggled to:', newTheme);
    }

    updateAllThemeIndicators() {
        const indicators = document.querySelectorAll('#theme-indicator-icon, .theme-indicator-icon');
        const isLight = this.currentTheme === 'light';
        
        indicators.forEach(icon => {
            if (icon) {
                icon.className = isLight ? 'fas fa-sun' : 'fas fa-moon';
            }
        });
        
        debugLog('Theme indicators updated. Count:', indicators.length);
    }

    showThemeChangeNotification(theme) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1), 0 8px 32px rgba(124, 58, 237, 0.1);
            z-index: 10000;
            animation: slideInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            color: var(--text-primary);
            backdrop-filter: blur(20px);
        `;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="width: 40px; height: 40px; background: var(--accent-gradient); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px;">
                    <i class="fas ${theme === 'light' ? 'fa-sun' : 'fa-moon'}"></i>
                </div>
                <div>
                    <div style="font-weight: 600; margin-bottom: 2px;">Theme Changed</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Switched to ${theme} mode</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutDown 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => notification.remove(), 400);
        }, 2500);
    }
}

// ===========================================
// 3. ENHANCED MODAL SYSTEM
// ===========================================

class ModalManager {
    constructor() {
        this.activeModals = [];
        this.init();
    }

    init() {
        // Add keyframe animations to document
        this.injectModalStyles();
        debugLog('Enhanced modal system initialized');
    }

    injectModalStyles() {
        if (document.getElementById('modalStyles')) return;
        
        const style = document.createElement('style');
        style.id = 'modalStyles';
        style.textContent = `
            @keyframes modalFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes modalSlideIn {
                from { 
                    opacity: 0; 
                    transform: translate(-50%, -50%) scale(0.9) translateY(20px); 
                }
                to { 
                    opacity: 1; 
                    transform: translate(-50%, -50%) scale(1) translateY(0); 
                }
            }
            
            @keyframes modalFadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
            
            @keyframes modalSlideOut {
                from { 
                    opacity: 1; 
                    transform: translate(-50%, -50%) scale(1) translateY(0); 
                }
                to { 
                    opacity: 0; 
                    transform: translate(-50%, -50%) scale(0.9) translateY(20px); 
                }
            }
            
            @keyframes slideInUp {
                from { transform: translateY(100%); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            
            @keyframes slideOutDown {
                from { transform: translateY(0); opacity: 1; }
                to { transform: translateY(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    createModal(options) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: modalFadeIn 0.3s ease;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
            background: var(--bg-card);
            border-radius: 20px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            position: relative;
            animation: modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid var(--border-color);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
        `;
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2 style="color: var(--text-primary); margin: 0; font-size: 1.5rem; font-weight: 600;">${options.title}</h2>
                <button class="modal-close-btn" style="background: var(--bg-hover); border: none; width: 32px; height: 32px; border-radius: 8px; cursor: pointer; color: var(--text-muted); transition: all 0.2s; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            ${options.content}
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        this.activeModals.push(modal);
        
        // Enhance close button
        const closeBtn = modalContent.querySelector('.modal-close-btn');
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.background = 'var(--danger)';
            closeBtn.style.color = 'white';
        });
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.background = 'var(--bg-hover)';
            closeBtn.style.color = 'var(--text-muted)';
        });
        
        // Bind close events
        closeBtn.addEventListener('click', () => this.closeModal(modal));
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal(modal);
        });
        
        // Handle form submission if provided
        const form = modalContent.querySelector('form');
        if (form && options.onSubmit) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = Object.fromEntries(new FormData(form));
                const result = await options.onSubmit(formData);
                if (result !== false) this.closeModal(modal);
            });
        }
        
        // Focus first input
        const firstInput = modalContent.querySelector('input, textarea, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
        
        debugLog('Enhanced modal created:', options.title);
        return modal;
    }

    closeModal(modal) {
        const content = modal.querySelector('.modal-content');
        modal.style.animation = 'modalFadeOut 0.3s ease';
        content.style.animation = 'modalSlideOut 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        setTimeout(() => {
            modal.remove();
            this.activeModals = this.activeModals.filter(m => m !== modal);
        }, 300);
        
        debugLog('Enhanced modal closed');
    }

    closeAllModals() {
        this.activeModals.forEach(modal => this.closeModal(modal));
    }
}

// ===========================================
// 4. ENHANCED NOTIFICATION SYSTEM
// ===========================================

class NotificationManager {
    constructor() {
        this.notifications = [];
        this.container = null;
        this.init();
    }

    init() {
        // Create notification container
        this.container = document.createElement('div');
        this.container.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            z-index: 10001;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            pointer-events: none;
        `;
        document.body.appendChild(this.container);
        debugLog('Enhanced notification system initialized');
    }

    showToast(message, type = 'info', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = 'gst-toast';
        toast.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1rem 1.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1), 0 8px 32px rgba(124, 58, 237, 0.1);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            max-width: 400px;
            color: var(--text-primary);
            pointer-events: auto;
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
        `;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        const colors = {
            success: 'var(--success)',
            error: 'var(--danger)',
            warning: 'var(--warning)',
            info: 'var(--info)'
        };
        
        // Add colored accent bar
        const accentBar = document.createElement('div');
        accentBar.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: ${colors[type] || colors.info};
        `;
        toast.appendChild(accentBar);
        
        toast.innerHTML += `
            <div style="width: 40px; height: 40px; background: ${colors[type] || colors.info}; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; flex-shrink: 0;">
                <i class="${icons[type] || icons.info}"></i>
            </div>
            <span style="flex: 1; font-weight: 500;">${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; border-radius: 4px; transition: background 0.2s;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        this.container.appendChild(toast);
        this.notifications.push(toast);
        
        // Auto remove
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                setTimeout(() => {
                    toast.remove();
                    this.notifications = this.notifications.filter(n => n !== toast);
                }, 400);
            }
        }, duration);
        
        debugLog('Enhanced toast notification shown:', message, type);
    }
}

// ===========================================
// 5. ENHANCED FORM MANAGEMENT
// ===========================================

class FormManager {
    constructor() {
        this.init();
    }

    init() {
        this.initializeGSTINValidation();
        this.initializeMobileValidation();
        this.initializePasswordStrength();
        this.initializeFormSubmissions();
        this.initializeRealTimeValidation();
        
        debugLog('Enhanced form management system initialized');
    }

    initializeGSTINValidation() {
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin');
        
        gstinInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const value = e.target.value.toUpperCase();
                e.target.value = value;
                
                const isValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(value);
                
                if (value.length === 15) {
                    this.setInputValidation(e.target, isValid, isValid ? 'Valid GSTIN format' : 'Invalid GSTIN format');
                } else {
                    this.clearInputValidation(e.target);
                }
            });
            
            // Enhanced paste handling
            input.addEventListener('paste', (e) => {
                setTimeout(() => {
                    const value = e.target.value.trim();
                    if (value.length === 15 && this.isValidGSTIN(value)) {
                        const autoSearch = localStorage.getItem('autoSearch');
                        if (autoSearch === 'true') {
                            const form = e.target.closest('form');
                            if (form) {
                                notificationManager.showToast('Auto-searching pasted GSTIN...', 'info');
                                setTimeout(() => form.submit(), 500);
                            }
                        }
                    }
                }, 100);
            });
        });
    }

    initializeMobileValidation() {
        const mobileInputs = document.querySelectorAll('input[name="mobile"]');
        
        mobileInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const value = e.target.value.replace(/\D/g, '');
                e.target.value = value;
                
                if (value.length === 10) {
                    const isValid = /^[6-9][0-9]{9}$/.test(value);
                    this.setInputValidation(e.target, isValid, isValid ? 'Valid mobile number' : 'Invalid mobile number');
                } else {
                    this.clearInputValidation(e.target);
                }
            });
        });
    }

    initializePasswordStrength() {
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        
        passwordInputs.forEach(input => {
            if (input.name === 'password' || input.id === 'passwordInput') {
                input.addEventListener('input', (e) => {
                    this.updatePasswordStrength(e.target);
                });
            }
        });
    }

    initializeRealTimeValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
            
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateInput(input);
                });
                
                input.addEventListener('input', () => {
                    if (input.classList.contains('is-invalid')) {
                        this.validateInput(input);
                    }
                });
            });
        });
    }

    validateInput(input) {
        const value = input.value.trim();
        const type = input.type;
        const required = input.hasAttribute('required');
        
        let isValid = true;
        let message = '';
        
        if (required && !value) {
            isValid = false;
            message = 'This field is required';
        } else if (value) {
            switch (type) {
                case 'email':
                    isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                    message = isValid ? 'Valid email' : 'Invalid email format';
                    break;
                case 'tel':
                    isValid = /^[6-9][0-9]{9}$/.test(value);
                    message = isValid ? 'Valid mobile number' : 'Invalid mobile number';
                    break;
                case 'password':
                    isValid = value.length >= 6;
                    message = isValid ? 'Password strength: Good' : 'Password must be at least 6 characters';
                    break;
            }
        }
        
        this.setInputValidation(input, isValid, message);
        return isValid;
    }

    setInputValidation(input, isValid, message) {
        input.classList.remove('is-valid', 'is-invalid');
        input.classList.add(isValid ? 'is-valid' : 'is-invalid');
        
        const borderColor = isValid ? 'var(--success)' : 'var(--danger)';
        input.style.borderColor = borderColor;
        
        this.showValidationFeedback(input, isValid, message);
    }

    clearInputValidation(input) {
        input.classList.remove('is-valid', 'is-invalid');
        input.style.borderColor = 'var(--border-color)';
        this.removeValidationFeedback(input);
    }

    showValidationFeedback(input, isValid, message) {
        this.removeValidationFeedback(input);
        
        if (!message) return;
        
        const feedback = document.createElement('div');
        feedback.className = 'validation-feedback';
        feedback.style.cssText = `
            font-size: 0.85rem;
            margin-top: 0.5rem;
            color: ${isValid ? 'var(--success)' : 'var(--danger)'};
            display: flex;
            align-items: center;
            gap: 0.25rem;
            animation: slideInDown 0.2s ease;
        `;
        feedback.innerHTML = `
            <i class="fas ${isValid ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            ${message}
        `;
        
        input.parentNode.appendChild(feedback);
    }

    removeValidationFeedback(input) {
        const existingFeedback = input.parentNode.querySelector('.validation-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
    }

    updatePasswordStrength(input) {
        const password = input.value;
        const strength = this.calculatePasswordStrength(password);
        
        const strengthBar = document.getElementById('strengthBar');
        const strengthText = document.getElementById('strengthText');
        
        if (strengthBar && strengthText) {
            strengthBar.style.width = `${strength.score}%`;
            strengthBar.style.background = strength.color;
            strengthText.textContent = strength.text;
            strengthText.style.color = strength.color;
        }
    }

    calculatePasswordStrength(password) {
        let score = 0;
        let feedback = '';
        
        if (password.length >= 8) score += 25;
        if (/[a-z]/.test(password)) score += 25;
        if (/[A-Z]/.test(password)) score += 25;
        if (/[0-9]/.test(password)) score += 25;
        if (/[^a-zA-Z0-9]/.test(password)) score += 25;
        
        if (score <= 25) {
            feedback = 'Very Weak';
            return { score: Math.min(score, 100), color: '#ef4444', text: feedback };
        } else if (score <= 50) {
            feedback = 'Weak';
            return { score: Math.min(score, 100), color: '#f59e0b', text: feedback };
        } else if (score <= 75) {
            feedback = 'Good';
            return { score: Math.min(score, 100), color: '#3b82f6', text: feedback };
        } else {
            feedback = 'Strong';
            return { score: Math.min(score, 100), color: '#10b981', text: feedback };
        }
    }

    initializeFormSubmissions() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    this.setLoadingState(submitBtn, true);
                    
                    // Re-enable after 10 seconds as fallback
                    setTimeout(() => {
                        this.setLoadingState(submitBtn, false);
                    }, 10000);
                }
            });
        });
    }

    setLoadingState(button, loading) {
        if (loading) {
            button.classList.add('loading');
            button.disabled = true;
            button.style.pointerEvents = 'none';
        } else {
            button.classList.remove('loading');
            button.disabled = false;
            button.style.pointerEvents = 'auto';
        }
    }

    isValidGSTIN(gstin) {
        return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
    }
}

// ===========================================
// 6. ENHANCED KEYBOARD SHORTCUTS
// ===========================================

class KeyboardShortcutManager {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        // Register enhanced shortcuts
        this.registerShortcut('ctrl+k', () => this.focusSearch());
        this.registerShortcut('cmd+k', () => this.focusSearch());
        this.registerShortcut('escape', () => this.handleEscape());
        this.registerShortcut('ctrl+/', () => this.showShortcutsHelp());
        this.registerShortcut('cmd+/', () => this.showShortcutsHelp());
        this.registerShortcut('ctrl+shift+t', () => themeManager.toggleTheme());
        this.registerShortcut('cmd+shift+t', () => themeManager.toggleTheme());
        
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        debugLog('Enhanced keyboard shortcuts initialized');
    }

    registerShortcut(combination, callback) {
        this.shortcuts.set(combination.toLowerCase(), callback);
    }

    handleKeydown(e) {
        const keys = [];
        if (e.ctrlKey) keys.push('ctrl');
        if (e.metaKey) keys.push('cmd');
        if (e.shiftKey) keys.push('shift');
        if (e.altKey) keys.push('alt');
        
        const key = e.key.toLowerCase();
        if (!['control', 'meta', 'shift', 'alt'].includes(key)) {
            keys.push(key);
        }
        
        const combination = keys.join('+');
        const callback = this.shortcuts.get(combination);
        
        if (callback) {
            e.preventDefault();
            callback(e);
            debugLog('Keyboard shortcut executed:', combination);
        }
    }

    handleEscape() {
        // Close modals first
        modalManager.closeAllModals();
        
        // Close user dropdown if open
        const userDropdown = document.getElementById('userDropdownMenu');
        if (userDropdown && userDropdown.classList.contains('active')) {
            closeUserDropdown();
        }
    }

    focusSearch() {
        const searchInput = document.querySelector('#gstin, input[name="gstin"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
            notificationManager.showToast('Search focused', 'info', 1500);
        }
    }

    showShortcutsHelp() {
        const shortcuts = [
            { keys: 'Ctrl+K / Cmd+K', description: 'Focus search input' },
            { keys: 'Ctrl+Shift+T / Cmd+Shift+T', description: 'Toggle theme' },
            { keys: 'Escape', description: 'Close modals and dropdowns' },
            { keys: 'Ctrl+/ / Cmd+/', description: 'Show this help' }
        ];
        
        const content = `
            <div style="margin-bottom: 1rem;">
                <h3 style="margin-bottom: 1rem; color: var(--text-primary);">Keyboard Shortcuts</h3>
                ${shortcuts.map(s => `
                    <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border-color);">
                        <code style="background: var(--bg-hover); padding: 0.5rem 0.75rem; border-radius: 6px; font-family: monospace; font-size: 0.85rem;">${s.keys}</code>
                        <span style="color: var(--text-secondary); margin-left: 1rem;">${s.description}</span>
                    </div>
                `).join('')}
            </div>
            <button onclick="modalManager.closeAllModals()" class="btn btn-primary" style="width: 100%; padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Got it!</button>
        `;
        
        modalManager.createModal({
            title: 'Keyboard Shortcuts',
            content: content
        });
    }
}

// ===========================================
// 7. UTILITY FUNCTIONS
// ===========================================

function autoDismissMessages() {
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach((message, index) => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.animation = 'fadeOut 0.5s ease';
                setTimeout(() => message.remove(), 500);
            }
        }, 5000 + (index * 1000));
    });
}

function setDynamicGreeting() {
    const hour = new Date().getHours();
    let greeting = 'Welcome';
    
    if (hour < 12) greeting = 'Good Morning';
    else if (hour < 17) greeting = 'Good Afternoon';
    else greeting = 'Good Evening';
    
    const greetingElements = document.querySelectorAll('.dynamic-greeting');
    greetingElements.forEach(el => {
        if (el) el.textContent = greeting;
    });
}

function initPageTransitions() {
    const content = document.querySelector('.container, main');
    if (content) {
        content.style.animation = 'pageSlide 0.3s ease-out';
    }
}

function initPerformanceMonitoring() {
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const loadTime = performance.now();
            if (loadTime > 3000) {
                console.warn('Page load time is slow:', loadTime + 'ms');
            }
            debugLog('Page loaded in:', loadTime + 'ms');
        });
    }
}

// ===========================================
// 8. GLOBAL MODAL FUNCTIONS
// ===========================================

window.openProfileModal = function() {
    modalManager.createModal({
        title: 'My Profile',
        content: `
            <form id="profileForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="form-group">
                    <label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Confirm Password</label>
                    <input type="password" name="confirmPassword" class="form-input" required style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Change Password</button>
            </form>
        `,
        onSubmit: async function(formData) {
            if (formData.newPassword !== formData.confirmPassword) {
                notificationManager.showToast('Passwords do not match!', 'error');
                return false;
            }
            if (formData.newPassword.length < 6) {
                notificationManager.showToast('Password must be at least 6 characters!', 'error');
                return false;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            notificationManager.showToast('Password changed successfully!', 'success');
            return true;
        }
    });
};

window.openSettingsModal = function() {
    const currentSettings = JSON.parse(localStorage.getItem(GST_CONFIG.USER_PREFERENCES_KEY) || '{}');
    
    modalManager.createModal({
        title: 'Settings & Preferences',
        content: `
            <form id="settingsForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div style="margin-bottom: 1rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary); font-size: 1.1rem;">General Preferences</h4>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="emailNotifications" ${currentSettings.emailNotifications ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">Email Notifications</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Receive email updates about your searches</div>
                            </div>
                        </label>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="autoSearch" ${currentSettings.autoSearch !== false ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">Auto-search on GSTIN paste</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Automatically search when you paste a GSTIN</div>
                            </div>
                        </label>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="darkMode" ${themeManager.currentTheme === 'dark' ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">Dark Mode</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Use dark theme for better viewing in low light</div>
                            </div>
                        </label>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="compactMode" ${currentSettings.compactMode ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">Compact Mode</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Show more information in less space</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary); font-size: 1.1rem;">Data & Privacy</h4>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Data Retention</label>
                        <select name="dataRetention" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                            <option value="30" ${currentSettings.dataRetention === '30' ? 'selected' : ''}>30 days</option>
                            <option value="90" ${currentSettings.dataRetention === '90' ? 'selected' : ''}>90 days</option>
                            <option value="365" ${currentSettings.dataRetention === '365' ? 'selected' : ''}>1 year</option>
                            <option value="forever" ${currentSettings.dataRetention === 'forever' ? 'selected' : ''}>Forever</option>
                        </select>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <button type="button" onclick="clearUserData()" style="width: 100%; padding: 0.75rem; background: var(--danger); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                            Clear All Search History
                        </button>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary" style="padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Save Settings</button>
            </form>
        `,
        onSubmit: async function(formData) {
            localStorage.setItem(GST_CONFIG.USER_PREFERENCES_KEY, JSON.stringify(formData));
            
            if (formData.darkMode !== (themeManager.currentTheme === 'dark')) {
                themeManager.toggleTheme();
            }
            
            // Apply compact mode
            if (formData.compactMode) {
                document.body.classList.add('compact-mode');
            } else {
                document.body.classList.remove('compact-mode');
            }
            
            notificationManager.showToast('Settings saved successfully!', 'success');
            return true;
        }
    });
};

// ===========================================
// 9. GLOBAL FUNCTIONS
// ===========================================

window.toggleTheme = function() {
    themeManager.toggleTheme();
};

window.clearUserData = function() {
    if (confirm('Are you sure you want to clear all your search history? This action cannot be undone.')) {
        // This would typically make an API call to clear server data
        localStorage.removeItem('searchHistory');
        notificationManager.showToast('Search history cleared', 'success');
        
        // Optionally reload the page to reflect changes
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    }
};

// ===========================================
// 10. ENHANCED ANIMATION SYSTEM
// ===========================================

function injectEnhancedStyles() {
    if (document.getElementById('enhancedStyles')) return;
    
    const style = document.createElement('style');
    style.id = 'enhancedStyles';
    style.textContent = `
        /* Enhanced Animations */
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes slideInDown {
            from { transform: translateY(-10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes fadeOut {
            to { opacity: 0; transform: translateY(-10px); }
        }
        
        @keyframes pageSlide {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Enhanced Form Validation Styles */
        .form-input.is-valid {
            border-color: var(--success) !important;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;
        }
        
        .form-input.is-invalid {
            border-color: var(--danger) !important;
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
        }
        
        /* Loading Button Animation */
        .loading {
            position: relative;
            pointer-events: none;
            opacity: 0.8;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Compact Mode Styles */
        .compact-mode .stat-card {
            padding: 1rem;
        }
        
        .compact-mode .info-card {
            padding: 1rem;
        }
        
        .compact-mode .returns-table th,
        .compact-mode .returns-table td {
            padding: 0.5rem;
            font-size: 0.85rem;
        }
        
        /* Enhanced Hover Effects */
        .nav-link:hover {
            transform: translateY(-2px);
        }
        
        .stat-card:hover {
            transform: translateY(-3px);
        }
        
        /* Improved Focus Styles */
        .form-input:focus {
            transform: translateY(-1px);
        }
        
        /* Enhanced Theme Toggle */
        .theme-toggle:hover {
            transform: scale(1.05);
        }
        
        /* Responsive Improvements */
        @media (max-width: 768px) {
            .gst-toast {
                margin: 0 1rem;
                max-width: calc(100vw - 2rem);
            }
            
            .user-profile-btn {
                min-width: 100px;
            }
        }
    `;
    document.head.appendChild(style);
}

// ===========================================
// 11. INITIALIZATION
// ===========================================

// Global instances
let tooltipManager;
let themeManager;
let modalManager;
let notificationManager;
let formManager;
let keyboardManager;

// Initialize all systems when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all managers
    tooltipManager = new TooltipManager();
    themeManager = new ThemeManager();
    modalManager = new ModalManager();
    notificationManager = new NotificationManager();
    formManager = new FormManager();
    keyboardManager = new KeyboardShortcutManager();
    
    // Inject enhanced styles
    injectEnhancedStyles();
    
    // Initialize utility functions
    autoDismissMessages();
    setDynamicGreeting();
    initPageTransitions();
    initPerformanceMonitoring();
    
    // Apply saved user preferences
    const userPrefs = JSON.parse(localStorage.getItem(GST_CONFIG.USER_PREFERENCES_KEY) || '{}');
    if (userPrefs.compactMode) {
        document.body.classList.add('compact-mode');
    }
    
    console.log('✅ GST Intelligence Platform - All systems initialized');
    
    // Show welcome notification for new users
    if (!localStorage.getItem('welcomeShown')) {
        setTimeout(() => {
            notificationManager.showToast('Welcome to GST Intelligence Platform! Press Ctrl+/ for shortcuts.', 'info', 6000);
            localStorage.setItem('welcomeShown', 'true');
        }, 1000);
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden - cleanup if needed
        tooltipManager.hideTooltip();
    }
});

// Handle online/offline status
window.addEventListener('online', () => {
    notificationManager.showToast('Connection restored', 'success', 3000);
});

window.addEventListener('offline', () => {
    notificationManager.showToast('Connection lost - Some features may not work', 'warning', 5000);
});

// Export for debugging
window.GST_DEBUG = {
    tooltipManager,
    themeManager,
    modalManager,
    notificationManager,
    formManager,
    keyboardManager,
    config: GST_CONFIG
};<label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Display Name</label>
                    <input type="text" name="displayName" class="form-input" placeholder="Enter your name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Email</label>
                    <input type="email" name="email" class="form-input" placeholder="Enter your email" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Company</label>
                    <input type="text" name="company" class="form-input" placeholder="Company name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Save Profile</button>
            </form>
        `,
        onSubmit: async function(formData) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            notificationManager.showToast('Profile updated successfully!', 'success');
            return true;
        }
    });
};

window.openPasswordModal = function() {
    modalManager.createModal({
        title: 'Change Password',
        content: `
            <form id="passwordForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="form-group">
                    <label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Current Password</label>
                    <input type="password" name="currentPassword" class="form-input" required style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label class="form-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">New Password</label>
                    <input type="password" name="newPassword" class="form-input" required minlength="6" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <div class="form-group"></div>