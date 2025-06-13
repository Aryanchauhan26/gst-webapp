// GST Intelligence Platform - FIXED Common Scripts
// Complete JavaScript Framework - No Conflicts, Consistent Functionality

console.log('🚀 GST Platform Scripts Loading...');

// Global configuration
const GST_CONFIG = {
    TOOLTIP_DELAY: 300,
    TOOLTIP_HIDE_DELAY: 100,
    ANIMATION_DURATION: 300,
    THEME_STORAGE_KEY: 'gst_theme',
    DEBUG: false
};

// Debug logging
function debugLog(message, ...args) {
    if (GST_CONFIG.DEBUG) {
        console.log(`[GST Debug] ${message}`, ...args);
    }
}

// ===========================================
// 1. TOOLTIP SYSTEM - SINGLE IMPLEMENTATION
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
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.4;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            word-wrap: break-word;
            border: 1px solid #333;
        `;
        
        this.tooltipContainer.appendChild(tooltipContent);
        document.body.appendChild(this.tooltipContainer);
        
        // Bind events
        this.bindEvents();
        
        debugLog('Tooltip system initialized');
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
// 2. THEME SYSTEM - FIXED IMPLEMENTATION
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
        
        debugLog('Theme system initialized with theme:', savedTheme);
    }

    setTheme(theme, save = true) {
        this.currentTheme = theme;
        
        // Apply theme to body
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
        
        debugLog('Theme set to:', theme);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        
        // Show feedback
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
            border-radius: 8px;
            padding: 1rem;
            box-shadow: var(--card-shadow);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            color: var(--text-primary);
        `;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas ${theme === 'light' ? 'fa-sun' : 'fa-moon'}"></i>
                <span>Switched to ${theme} theme</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }
}

// ===========================================
// 3. USER DROPDOWN - DASHBOARD ONLY
// ===========================================

class UserDropdownManager {
    constructor() {
        this.init();
    }

    init() {
        // Only initialize on dashboard (check for specific elements or page indicators)
        if (!this.isDashboardPage()) {
            debugLog('Not dashboard page, skipping user dropdown');
            return;
        }

        this.initializeUserDropdowns();
        this.bindOutsideClickEvents();
        
        debugLog('User dropdown system initialized for dashboard');
    }

    isDashboardPage() {
        // Check if we're on the dashboard by looking for dashboard-specific elements
        return document.querySelector('.welcome-section') !== null ||
               document.querySelector('.search-section') !== null ||
               window.location.pathname === '/' ||
               document.body.classList.contains('page-dashboard');
    }

    initializeUserDropdowns() {
        const userElements = document.querySelectorAll('.user-profile');
        
        userElements.forEach((userElement) => {
            // Skip if already processed
            if (userElement.classList.contains('dropdown-processed')) return;
            
            userElement.classList.add('dropdown-processed');
            
            const mobile = userElement.textContent.trim();
            
            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'user-dropdown-wrapper';
            wrapper.style.cssText = `
                position: relative;
                display: inline-block;
            `;
            
            // Create button
            const button = document.createElement('button');
            button.className = 'user-profile-btn';
            button.innerHTML = `
                <i class="fas fa-user-circle"></i>
                <span>${mobile}</span>
                <i class="fas fa-chevron-down dropdown-arrow"></i>
            `;
            
            // Create dropdown menu
            const menu = document.createElement('div');
            menu.className = 'user-dropdown-menu';
            menu.style.display = 'none';
            menu.innerHTML = `
                <div class="dropdown-item" onclick="openProfileModal()">
                    <i class="fas fa-user-edit"></i>
                    <span>Edit Profile</span>
                </div>
                <div class="dropdown-item" onclick="openPasswordModal()">
                    <i class="fas fa-key"></i>
                    <span>Change Password</span>
                </div>
                <div class="dropdown-item" onclick="openSettingsModal()">
                    <i class="fas fa-cog"></i>
                    <span>Settings</span>
                </div>
                <div class="dropdown-divider"></div>
                <div class="dropdown-item logout-item" onclick="window.location.href='/logout'">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>Logout</span>
                </div>
            `;
            
            // Replace original element
            userElement.parentNode.insertBefore(wrapper, userElement);
            wrapper.appendChild(button);
            wrapper.appendChild(menu);
            userElement.remove();
            
            // Toggle dropdown
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown(menu, button);
            });
        });
    }

    toggleDropdown(menu, button) {
        const isVisible = menu.style.display === 'block';
        
        // Close all dropdowns first
        document.querySelectorAll('.user-dropdown-menu').forEach(m => {
            m.style.display = 'none';
        });
        document.querySelectorAll('.dropdown-arrow').forEach(arrow => {
            arrow.style.transform = '';
        });
        
        // Toggle current dropdown
        if (!isVisible) {
            menu.style.display = 'block';
            button.querySelector('.dropdown-arrow').style.transform = 'rotate(180deg)';
            debugLog('User dropdown opened');
        } else {
            debugLog('User dropdown closed');
        }
    }

    bindOutsideClickEvents() {
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-dropdown-wrapper')) {
                document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                    menu.style.display = 'none';
                });
                document.querySelectorAll('.dropdown-arrow').forEach(arrow => {
                    arrow.style.transform = '';
                });
            }
        });
    }
}

// ===========================================
// 4. FORM VALIDATION & ENHANCEMENT
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
        
        debugLog('Form management system initialized');
    }

    initializeGSTINValidation() {
        const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin');
        
        gstinInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const value = e.target.value.toUpperCase();
                e.target.value = value;
                
                const isValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(value);
                
                if (value.length === 15) {
                    e.target.style.borderColor = isValid ? 'var(--success)' : 'var(--danger)';
                    
                    // Add validation feedback
                    this.showValidationFeedback(e.target, isValid, isValid ? 'Valid GSTIN format' : 'Invalid GSTIN format');
                } else {
                    e.target.style.borderColor = 'var(--border-color)';
                    this.removeValidationFeedback(e.target);
                }
            });
            
            // Auto-search on paste if enabled
            input.addEventListener('paste', (e) => {
                setTimeout(() => {
                    const value = e.target.value.trim();
                    if (value.length === 15 && this.isValidGSTIN(value)) {
                        const autoSearch = localStorage.getItem('autoSearch');
                        if (autoSearch === 'true') {
                            const form = e.target.closest('form');
                            if (form) {
                                this.showToast('Auto-searching pasted GSTIN...', 'info');
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
                const value = e.target.value.replace(/\D/g, ''); // Remove non-digits
                e.target.value = value;
                
                if (value.length === 10) {
                    const isValid = /^[6-9][0-9]{9}$/.test(value);
                    e.target.style.borderColor = isValid ? 'var(--success)' : 'var(--danger)';
                    this.showValidationFeedback(e.target, isValid, isValid ? 'Valid mobile number' : 'Invalid mobile number');
                } else {
                    e.target.style.borderColor = 'var(--border-color)';
                    this.removeValidationFeedback(e.target);
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
        // Add loading states to form submissions
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    submitBtn.classList.add('loading');
                    submitBtn.disabled = true;
                    
                    // Re-enable after 5 seconds as fallback
                    setTimeout(() => {
                        submitBtn.classList.remove('loading');
                        submitBtn.disabled = false;
                    }, 5000);
                }
            });
        });
    }

    isValidGSTIN(gstin) {
        return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
    }

    showValidationFeedback(input, isValid, message) {
        this.removeValidationFeedback(input);
        
        const feedback = document.createElement('div');
        feedback.className = 'validation-feedback';
        feedback.style.cssText = `
            font-size: 0.875rem;
            margin-top: 0.25rem;
            color: ${isValid ? 'var(--success)' : 'var(--danger)'};
        `;
        feedback.textContent = message;
        
        input.parentNode.appendChild(feedback);
    }

    removeValidationFeedback(input) {
        const existingFeedback = input.parentNode.querySelector('.validation-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
    }
}

// ===========================================
// 5. MODAL SYSTEM
// ===========================================

class ModalManager {
    constructor() {
        this.activeModals = [];
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
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
            background: var(--bg-card);
            border-radius: 16px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            animation: slideIn 0.3s ease;
        `;
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2 style="color: var(--text-primary); margin: 0;">${options.title}</h2>
                <button class="modal-close-btn" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-muted);">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            ${options.content}
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        this.activeModals.push(modal);
        
        // Bind close events
        const closeBtn = modalContent.querySelector('.modal-close-btn');
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
        
        debugLog('Modal created:', options.title);
        return modal;
    }

    closeModal(modal) {
        modal.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            modal.remove();
            this.activeModals = this.activeModals.filter(m => m !== modal);
        }, 300);
        
        debugLog('Modal closed');
    }

    closeAllModals() {
        this.activeModals.forEach(modal => this.closeModal(modal));
    }
}

// ===========================================
// 6. NOTIFICATION SYSTEM
// ===========================================

class NotificationManager {
    constructor() {
        this.notifications = [];
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'gst-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            box-shadow: var(--card-shadow);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            animation: slideIn 0.3s ease;
            z-index: 10001;
            max-width: 400px;
            color: var(--text-primary);
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
        
        toast.innerHTML = `
            <i class="${icons[type] || icons.info}" style="color: ${colors[type] || colors.info}; font-size: 1.2rem;"></i>
            <span style="flex: 1;">${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Stack toasts
        const existingToasts = document.querySelectorAll('.gst-toast');
        existingToasts.forEach((existing, index) => {
            existing.style.bottom = `${4 + (index + 1) * 5}rem`;
        });
        
        document.body.appendChild(toast);
        this.notifications.push(toast);
        
        // Auto remove
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    toast.remove();
                    this.notifications = this.notifications.filter(n => n !== toast);
                }, 300);
            }
        }, duration);
        
        debugLog('Toast notification shown:', message, type);
    }
}

// ===========================================
// 7. KEYBOARD SHORTCUTS
// ===========================================

class KeyboardShortcutManager {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        // Register default shortcuts
        this.registerShortcut('ctrl+k', () => this.focusSearch());
        this.registerShortcut('cmd+k', () => this.focusSearch());
        this.registerShortcut('escape', () => modalManager.closeAllModals());
        this.registerShortcut('ctrl+/', () => this.showShortcutsHelp());
        this.registerShortcut('cmd+/', () => this.showShortcutsHelp());
        
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        debugLog('Keyboard shortcuts initialized');
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

    focusSearch() {
        const searchInput = document.querySelector('#gstin, input[name="gstin"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    showShortcutsHelp() {
        const shortcuts = [
            { keys: 'Ctrl+K / Cmd+K', description: 'Focus search input' },
            { keys: 'Escape', description: 'Close modals' },
            { keys: 'Ctrl+/ / Cmd+/', description: 'Show this help' }
        ];
        
        const content = `
            <div style="margin-bottom: 1rem;">
                <h3 style="margin-bottom: 1rem; color: var(--text-primary);">Keyboard Shortcuts</h3>
                ${shortcuts.map(s => `
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color);">
                        <code style="background: var(--bg-hover); padding: 0.25rem 0.5rem; border-radius: 4px; font-family: monospace;">${s.keys}</code>
                        <span style="color: var(--text-secondary);">${s.description}</span>
                    </div>
                `).join('')}
            </div>
            <button onclick="modalManager.closeAllModals()" class="btn btn-primary" style="width: 100%;">Got it!</button>
        `;
        
        modalManager.createModal({
            title: 'Keyboard Shortcuts',
            content: content
        });
    }
}

// ===========================================
// 8. AUTO-DISMISS MESSAGES
// ===========================================

function autoDismissMessages() {
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach((message, index) => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.animation = 'fadeOut 0.5s ease';
                setTimeout(() => message.remove(), 500);
            }
        }, 5000 + (index * 1000)); // Stagger dismissal
    });
}

// ===========================================
// 9. UTILITY FUNCTIONS
// ===========================================

// Dynamic greeting based on time
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

// Export functionality
function exportToExcel() {
    window.location.href = '/export/history';
    notificationManager.showToast('Exporting data to Excel...', 'info');
}

// Page transition effects
function initPageTransitions() {
    const content = document.querySelector('.container, main');
    if (content) {
        content.style.animation = 'pageSlide 0.3s ease-out';
    }
}

// Performance monitoring
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
// 10. MODAL FUNCTIONS (GLOBAL)
// ===========================================

window.openProfileModal = function() {
    modalManager.createModal({
        title: 'My Profile',
        content: `
            <form id="profileForm">
                <div class="form-group">
                    <label class="form-label">Display Name</label>
                    <input type="text" name="displayName" class="form-input" placeholder="Enter your name">
                </div>
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" name="email" class="form-input" placeholder="Enter your email">
                </div>
                <div class="form-group">
                    <label class="form-label">Company</label>
                    <input type="text" name="company" class="form-input" placeholder="Company name">
                </div>
                <button type="submit" class="btn btn-primary">Save Profile</button>
            </form>
        `,
        onSubmit: async function(formData) {
            // Simulate API call
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
            <form id="passwordForm">
                <div class="form-group">
                    <label class="form-label">Current Password</label>
                    <input type="password" name="currentPassword" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">New Password</label>
                    <input type="password" name="newPassword" class="form-input" required minlength="6">
                </div>
                <div class="form-group">
                    <label class="form-label">Confirm Password</label>
                    <input type="password" name="confirmPassword" class="form-input" required>
                </div>
                <button type="submit" class="btn btn-primary">Change Password</button>
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
            
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            notificationManager.showToast('Password changed successfully!', 'success');
            return true;
        }
    });
};

window.openSettingsModal = function() {
    const currentSettings = JSON.parse(localStorage.getItem('userSettings') || '{}');
    
    modalManager.createModal({
        title: 'Settings',
        content: `
            <form id="settingsForm">
                <h4 style="margin-bottom: 1rem; color: var(--text-primary);">Preferences</h4>
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" name="emailNotifications" ${currentSettings.emailNotifications ? 'checked' : ''}>
                        <span>Email Notifications</span>
                    </label>
                </div>
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" name="autoSearch" ${currentSettings.autoSearch !== false ? 'checked' : ''}>
                        <span>Auto-search on GSTIN paste</span>
                    </label>
                </div>
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" name="darkMode" ${themeManager.currentTheme === 'dark' ? 'checked' : ''}>
                        <span>Dark Mode</span>
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">Save Settings</button>
            </form>
        `,
        onSubmit: async function(formData) {
            // Save settings
            localStorage.setItem('userSettings', JSON.stringify(formData));
            
            // Apply theme change if needed
            if (formData.darkMode !== (themeManager.currentTheme === 'dark')) {
                themeManager.toggleTheme();
            }
            
            notificationManager.showToast('Settings saved!', 'success');
            return true;
        }
    });
};

// ===========================================
// 11. GLOBAL THEME TOGGLE FUNCTION
// ===========================================

window.toggleTheme = function() {
    themeManager.toggleTheme();
};

// ===========================================
// 12. ANIMATION KEYFRAMES (CSS-in-JS)
// ===========================================

function injectAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeOut {
            to { opacity: 0; transform: translateY(-10px); }
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            to { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes pageSlide {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
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
    `;
    
    // Only add if not already present
    if (!document.querySelector('#gst-animations')) {
        style.id = 'gst-animations';
        document.head.appendChild(style);
    }
}

// ===========================================
// 13. MAIN INITIALIZATION
// ===========================================

// Global instances
let tooltipManager;
let themeManager;
let userDropdownManager;
let formManager;
let modalManager;
let notificationManager;
let keyboardManager;

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 GST Platform Scripts Initializing...');
    
    try {
        // Initialize CSS animations
        injectAnimationStyles();
        
        // Initialize core systems
        tooltipManager = new TooltipManager();
        themeManager = new ThemeManager();
        modalManager = new ModalManager();
        notificationManager = new NotificationManager();
        keyboardManager = new KeyboardShortcutManager();
        
        // Initialize form management
        formManager = new FormManager();
        
        // Initialize user dropdown (dashboard only)
        userDropdownManager = new UserDropdownManager();
        
        // Initialize utility functions
        setDynamicGreeting();
        autoDismissMessages();
        initPageTransitions();
        initPerformanceMonitoring();
        
        // Refresh greeting every hour
        setInterval(setDynamicGreeting, 60 * 60 * 1000);
        
        console.log('✅ All GST Platform scripts initialized successfully');
        
        // Show welcome notification on dashboard
        if (window.location.pathname === '/') {
            setTimeout(() => {
                notificationManager.showToast('Welcome to GST Intelligence Platform! Press Ctrl+K to search.', 'info', 5000);
            }, 1000);
        }
        
    } catch (error) {
        console.error('❌ Error initializing GST Platform scripts:', error);
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, close dropdowns and modals
        if (userDropdownManager) {
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }
    }
});

// Handle window resize
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Close dropdowns on resize
        document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
            menu.style.display = 'none';
        });
    }, 250);
});

// ===========================================
// 14. DEBUG AND DEVELOPMENT HELPERS
// ===========================================

// Development helper functions (only in debug mode)
if (GST_CONFIG.DEBUG) {
    window.GST_DEBUG = {
        tooltipManager,
        themeManager,
        userDropdownManager,
        formManager,
        modalManager,
        notificationManager,
        keyboardManager,
        showToast: (msg, type) => notificationManager.showToast(msg, type),
        toggleDebug: () => {
            GST_CONFIG.DEBUG = !GST_CONFIG.DEBUG;
            console.log('Debug mode:', GST_CONFIG.DEBUG ? 'ON' : 'OFF');
        }
    };
    
    console.log('🐛 Debug mode enabled. Access GST_DEBUG object for debugging.');
}

// Service Worker registration (if available)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                debugLog('Service Worker registered:', registration);
            })
            .catch(error => {
                debugLog('Service Worker registration failed:', error);
            });
    });
}