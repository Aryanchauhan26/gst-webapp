// Missing JavaScript Implementations for GST Intelligence Platform
// Add this to your static/js/ directory or include in common scripts

// ===========================================
// 1. NOTIFICATION MANAGER (Referenced but not implemented)
// ===========================================

class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.notifications = [];
        this.defaultOptions = {
            duration: 5000,
            position: 'top-right',
            maxNotifications: 5
        };
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 10000;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-width: 400px;
        `;
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = this.defaultOptions.duration) {
        const notification = this.createNotification(message, type);
        
        // Limit number of notifications
        if (this.notifications.length >= this.defaultOptions.maxNotifications) {
            this.remove(this.notifications[0]);
        }

        this.container.appendChild(notification.element);
        this.notifications.push(notification);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(notification), duration);
        }

        return notification;
    }

    createNotification(message, type) {
        const id = Date.now() + Math.random();
        const element = document.createElement('div');
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        element.style.cssText = `
            background: var(--bg-card);
            border: 1px solid ${colors[type] || colors.info};
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            pointer-events: auto;
            cursor: pointer;
            transition: all 0.3s ease;
            animation: slideIn 0.3s ease-out;
            max-width: 100%;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        `;

        element.innerHTML = `
            <i class="${icons[type] || icons.info}" style="color: ${colors[type] || colors.info}; font-size: 1.2rem; margin-top: 0.1rem;"></i>
            <div style="flex: 1; color: var(--text-primary); font-size: 0.9rem; line-height: 1.4;">${message}</div>
            <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 0; font-size: 1.1rem;" onclick="notificationManager.remove(this.parentElement)">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add hover effect
        element.addEventListener('mouseenter', () => {
            element.style.transform = 'translateX(-5px) scale(1.02)';
        });

        element.addEventListener('mouseleave', () => {
            element.style.transform = 'translateX(0) scale(1)';
        });

        return { id, element, type };
    }

    remove(notification) {
        if (typeof notification === 'object' && notification.nodeType) {
            // If passed a DOM element directly
            notification.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
            return;
        }

        const index = this.notifications.findIndex(n => n.id === notification.id);
        if (index > -1) {
            const notificationObj = this.notifications[index];
            notificationObj.element.style.animation = 'slideOut 0.3s ease-out forwards';
            
            setTimeout(() => {
                if (notificationObj.element.parentNode) {
                    notificationObj.element.parentNode.removeChild(notificationObj.element);
                }
                this.notifications.splice(index, 1);
            }, 300);
        }
    }

    // Convenience methods
    showSuccess(message, duration) { return this.show(message, 'success', duration); }
    showError(message, duration) { return this.show(message, 'error', duration); }
    showWarning(message, duration) { return this.show(message, 'warning', duration); }
    showInfo(message, duration) { return this.show(message, 'info', duration); }
    showToast(message, type = 'info', duration) { return this.show(message, type, duration); }

    clear() {
        this.notifications.forEach(notification => this.remove(notification));
    }
}

// Add CSS animations
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes slideOut {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100%);
            }
        }
    `;
    document.head.appendChild(style);
}

// ===========================================
// 2. MODAL MANAGER (Referenced but not implemented)
// ===========================================

class ModalManager {
    constructor() {
        this.modals = [];
        this.currentZIndex = 10000;
    }

    createModal(options = {}) {
        const {
            title = 'Modal',
            content = '',
            size = 'medium',
            closable = true,
            backdrop = true,
            onSubmit = null,
            onClose = null
        } = options;

        const modalId = 'modal_' + Date.now();
        const modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            z-index: ${this.currentZIndex++};
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            padding: 1rem;
        `;

        const sizeClasses = {
            small: 'max-width: 400px;',
            medium: 'max-width: 600px;',
            large: 'max-width: 800px;',
            fullscreen: 'width: 95%; height: 95%;'
        };

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-card);
                border-radius: 16px;
                ${sizeClasses[size]}
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                border: 1px solid var(--border-primary);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            ">
                <div class="modal-header" style="
                    padding: 2rem 2rem 1rem 2rem;
                    border-bottom: 1px solid var(--border-primary);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <h3 style="margin: 0; color: var(--text-primary); font-size: 1.5rem; font-weight: 600;">${title}</h3>
                    ${closable ? `
                        <button class="modal-close" style="
                            background: none;
                            border: none;
                            color: var(--text-secondary);
                            font-size: 1.5rem;
                            cursor: pointer;
                            padding: 0.5rem;
                            border-radius: 8px;
                            transition: all 0.3s ease;
                        ">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
                <div class="modal-body" style="padding: 2rem;">
                    ${content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Show animation
        setTimeout(() => {
            modal.style.opacity = '1';
            const modalContent = modal.querySelector('.modal-content');
            modalContent.style.transform = 'scale(1)';
        }, 10);

        // Event listeners
        if (closable) {
            const closeBtn = modal.querySelector('.modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeModal(modalId));
            }
        }

        if (backdrop) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modalId);
                }
            });
        }

        // Handle form submission if onSubmit provided
        if (onSubmit) {
            const form = modal.querySelector('form');
            if (form) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const data = Object.fromEntries(formData.entries());
                    
                    try {
                        const result = await onSubmit(data);
                        if (result !== false) {
                            this.closeModal(modalId);
                        }
                    } catch (error) {
                        console.error('Form submission error:', error);
                    }
                });
            }
        }

        // Escape key to close
        const escapeHandler = (e) => {
            if (e.key === 'Escape' && closable) {
                this.closeModal(modalId);
            }
        };
        document.addEventListener('keydown', escapeHandler);

        const modalObj = {
            id: modalId,
            element: modal,
            onClose,
            escapeHandler
        };

        this.modals.push(modalObj);
        return modalObj;
    }

    closeModal(modalId) {
        const modalIndex = this.modals.findIndex(m => m.id === modalId);
        if (modalIndex === -1) return;

        const modal = this.modals[modalIndex];
        
        // Call onClose callback
        if (modal.onClose) {
            modal.onClose();
        }

        // Remove escape listener
        document.removeEventListener('keydown', modal.escapeHandler);

        // Hide animation
        modal.element.style.opacity = '0';
        const modalContent = modal.element.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.transform = 'scale(0.9)';
        }

        setTimeout(() => {
            if (modal.element.parentNode) {
                modal.element.parentNode.removeChild(modal.element);
            }
            this.modals.splice(modalIndex, 1);
        }, 300);
    }

    closeAllModals() {
        [...this.modals].forEach(modal => this.closeModal(modal.id));
    }

    getTopModal() {
        return this.modals[this.modals.length - 1];
    }
}

// ===========================================
// 3. THEME MANAGER (Enhance existing implementation)
// ===========================================

class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || 'dark';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupThemeToggle();
        this.watchSystemTheme();
    }

    getStoredTheme() {
        return localStorage.getItem('theme');
    }

    setTheme(theme, save = true) {
        this.currentTheme = theme;
        this.applyTheme(theme);
        
        if (save) {
            localStorage.setItem('theme', theme);
        }

        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme } 
        }));
    }

    applyTheme(theme) {
        const html = document.documentElement;
        
        if (theme === 'light') {
            html.setAttribute('data-theme', 'light');
        } else {
            html.removeAttribute('data-theme');
        }

        // Update theme toggle indicators
        this.updateThemeToggles();
    }

    updateThemeToggles() {
        const indicators = document.querySelectorAll('#theme-indicator-icon');
        indicators.forEach(indicator => {
            if (this.currentTheme === 'light') {
                indicator.className = 'fas fa-sun';
            } else {
                indicator.className = 'fas fa-moon';
            }
        });
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        
        // Add transition class
        document.body.classList.add('theme-transitioning');
        
        this.setTheme(newTheme);
        
        // Remove transition class after animation
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, 300);
    }

    setupThemeToggle() {
        // Override global toggleTheme function
        window.toggleTheme = () => this.toggleTheme();
    }

    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    this.setTheme(e.matches ? 'light' : 'dark', false);
                }
            });
        }
    }

    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            return 'light';
        }
        return 'dark';
    }
}

// ===========================================
// 4. DEBUG UTILITIES
// ===========================================

class DebugManager {
    constructor() {
        this.enabled = localStorage.getItem('gst_debug') === 'true';
    }

    enable() {
        localStorage.setItem('gst_debug', 'true');
        this.enabled = true;
        console.log('🐛 Debug mode enabled');
    }

    disable() {
        localStorage.setItem('gst_debug', 'false');
        this.enabled = false;
        console.log('🐛 Debug mode disabled');
    }

    log(...args) {
        if (this.enabled) {
            console.log('🔍 DEBUG:', ...args);
        }
    }

    error(...args) {
        if (this.enabled) {
            console.error('❌ DEBUG ERROR:', ...args);
        }
    }

    warn(...args) {
        if (this.enabled) {
            console.warn('⚠️ DEBUG WARNING:', ...args);
        }
    }
}

// Global debug function
window.debugLog = function(...args) {
    if (window.debugManager && window.debugManager.enabled) {
        console.log('🔍 DEBUG:', ...args);
    }
};

// ===========================================
// 5. SEARCH ENHANCEMENTS (Fix autocomplete issues)
// ===========================================

class SearchEnhancements {
    constructor() {
        this.recentSearches = this.getRecentSearches();
        this.maxRecentSearches = 10;
    }

    getRecentSearches() {
        try {
            return JSON.parse(localStorage.getItem('recentGSTINSearches') || '[]');
        } catch {
            return [];
        }
    }

    addRecentSearch(gstin, companyName) {
        if (!gstin || gstin.length !== 15) return;

        const search = { gstin, companyName, timestamp: Date.now() };
        
        // Remove if already exists
        this.recentSearches = this.recentSearches.filter(s => s.gstin !== gstin);
        
        // Add to beginning
        this.recentSearches.unshift(search);
        
        // Limit size
        this.recentSearches = this.recentSearches.slice(0, this.maxRecentSearches);
        
        // Save
        localStorage.setItem('recentGSTINSearches', JSON.stringify(this.recentSearches));
    }

    getSearchSuggestions(query) {
        if (!query || query.length < 2) return [];

        const suggestions = [];
        
        // Add recent searches
        const recentMatches = this.recentSearches.filter(search => 
            search.gstin.toLowerCase().includes(query.toLowerCase()) ||
            (search.companyName && search.companyName.toLowerCase().includes(query.toLowerCase()))
        );
        
        suggestions.push(...recentMatches.map(search => ({
            type: 'recent',
            gstin: search.gstin,
            company: search.companyName,
            icon: 'fas fa-history'
        })));

        return suggestions.slice(0, 5);
    }
}

// ===========================================
// 6. INITIALIZATION
// ===========================================

// Initialize all managers when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize global managers
    window.notificationManager = new NotificationManager();
    window.modalManager = new ModalManager();
    window.themeManager = new ThemeManager();
    window.debugManager = new DebugManager();
    window.searchEnhancements = new SearchEnhancements();

    console.log('✅ All managers initialized successfully');

    // Show welcome notification if first visit
    if (!localStorage.getItem('welcomeShown')) {
        setTimeout(() => {
            notificationManager.showSuccess('🎉 Welcome to GST Intelligence Platform!', 5000);
            localStorage.setItem('welcomeShown', 'true');
        }, 1000);
    }
});

// Export managers for use in other scripts
window.GST_MANAGERS = {
    notification: () => window.notificationManager,
    modal: () => window.modalManager,
    theme: () => window.themeManager,
    debug: () => window.debugManager,
    search: () => window.searchEnhancements
};

// Additional Missing Implementations Found
// These are critical functions that were referenced but not implemented

// ===========================================
// 1. SERVICE WORKER REGISTRATION (PWA Support)
// ===========================================

// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('✅ Service Worker registered:', registration);
            
            // Check for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New version available
                        if (window.notificationManager) {
                            window.notificationManager.showInfo(
                                '🔄 New version available! <button onclick="location.reload()" style="background:var(--accent-primary);color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;margin-left:0.5rem;cursor:pointer;">Update</button>', 
                                10000
                            );
                        }
                    }
                });
            });
        } catch (error) {
            console.log('❌ Service Worker registration failed:', error);
        }
    });
}

// ===========================================
// 2. PWA INSTALLATION PROMPT
// ===========================================

let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // Show install button after delay
    setTimeout(() => {
        if (window.notificationManager && !localStorage.getItem('pwa-install-dismissed')) {
            window.notificationManager.show(
                '📱 Install GST Intelligence as an app for better experience! <button onclick="installPWA()" style="background:var(--accent-primary);color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;margin-left:0.5rem;cursor:pointer;">Install</button> <button onclick="dismissPWAPrompt()" style="background:transparent;color:var(--text-secondary);border:none;padding:0.25rem;cursor:pointer;">×</button>',
                'info',
                15000
            );
        }
    }, 5000);
});

window.installPWA = async function() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`PWA install ${outcome}`);
        deferredPrompt = null;
    }
};

window.dismissPWAPrompt = function() {
    localStorage.setItem('pwa-install-dismissed', 'true');
    // Find and close the notification
    const notifications = document.querySelectorAll('#notification-container > div');
    notifications.forEach(notification => {
        if (notification.textContent.includes('Install GST Intelligence')) {
            notification.remove();
        }
    });
};

// ===========================================
// 3. MISSING CHART.JS ERROR HANDLING
// ===========================================

// Ensure Chart.js is loaded before initializing charts
window.ensureChartJS = function() {
    return new Promise((resolve, reject) => {
        if (window.Chart) {
            resolve();
            return;
        }
        
        // Load Chart.js if not already loaded
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js';
        script.onload = () => {
            console.log('✅ Chart.js loaded dynamically');
            resolve();
        };
        script.onerror = () => {
            console.error('❌ Failed to load Chart.js');
            reject(new Error('Failed to load Chart.js'));
        };
        document.head.appendChild(script);
    });
};

// Enhanced chart initialization with error handling
window.initializeChartsSafely = async function() {
    try {
        await window.ensureChartJS();
        
        // Set Chart.js defaults
        if (window.Chart) {
            Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim();
            Chart.defaults.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color').trim();
        }
        
        console.log('✅ Charts initialized safely');
    } catch (error) {
        console.error('❌ Chart initialization failed:', error);
        if (window.notificationManager) {
            window.notificationManager.showError('Charts failed to load. Some visualizations may not work.');
        }
    }
};

// ===========================================
// 4. MISSING EXCEL EXPORT IMPLEMENTATION
// ===========================================

window.exportToExcel = async function() {
    try {
        if (window.notificationManager) {
            window.notificationManager.showInfo('📊 Preparing Excel export...', 3000);
        }
        
        // Create download link
        const link = document.createElement('a');
        link.href = '/export/history';
        link.download = `gst_search_history_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        if (window.notificationManager) {
            window.notificationManager.showSuccess('📥 Download started!', 3000);
        }
    } catch (error) {
        console.error('Export error:', error);
        if (window.notificationManager) {
            window.notificationManager.showError('Export failed. Please try again.');
        }
    }
};

// ===========================================
// 5. MISSING BATCH SEARCH IMPLEMENTATION
// ===========================================

window.batchSearchModal = function() {
    if (!window.modalManager) {
        console.error('Modal manager not available');
        return;
    }

    window.modalManager.createModal({
        title: '🔍 Batch GSTIN Search',
        size: 'large',
        content: `
            <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div style="background: var(--bg-hover); border-radius: 12px; padding: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary);">Enter GSTINs (max 10)</h4>
                    <textarea id="batchGstinInput" placeholder="Enter GSTINs separated by new lines or commas&#10;e.g.:&#10;27AABCU9603R1ZX&#10;19AABCM7407R1ZZ&#10;29AABCT1332L1ZU" style="
                        width: 100%; 
                        height: 200px; 
                        padding: 1rem; 
                        background: var(--bg-input); 
                        border: 1px solid var(--border-color); 
                        border-radius: 8px; 
                        color: var(--text-primary); 
                        font-family: monospace; 
                        resize: vertical;
                    "></textarea>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-secondary);">
                        💡 Tip: Paste from Excel or enter one GSTIN per line
                    </div>
                </div>
                
                <div id="batchResults" style="display: none;">
                    <h4 style="color: var(--text-primary); margin-bottom: 1rem;">Results</h4>
                    <div id="batchResultsContent"></div>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <button type="button" onclick="processBatchSearch()" class="btn btn--primary" style="flex: 1; padding: 1rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        <i class="fas fa-search"></i> Process Batch Search
                    </button>
                    <button type="button" onclick="clearBatchInput()" class="btn btn--secondary" style="padding: 1rem 1.5rem; background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 8px; font-weight: 600; cursor: pointer;">
                        <i class="fas fa-trash"></i> Clear
                    </button>
                </div>
            </div>
        `
    });
};

window.processBatchSearch = async function() {
    const input = document.getElementById('batchGstinInput');
    const resultsDiv = document.getElementById('batchResults');
    const resultsContent = document.getElementById('batchResultsContent');
    
    if (!input || !resultsDiv || !resultsContent) return;
    
    const text = input.value.trim();
    if (!text) {
        window.notificationManager.showWarning('Please enter at least one GSTIN');
        return;
    }
    
    // Parse GSTINs
    const gstins = text
        .split(/[\n,;]/)
        .map(gstin => gstin.trim().toUpperCase())
        .filter(gstin => gstin.length === 15)
        .slice(0, 10); // Limit to 10
    
    if (gstins.length === 0) {
        window.notificationManager.showError('No valid GSTINs found. Please check the format.');
        return;
    }
    
    try {
        window.notificationManager.showInfo(`🔍 Processing ${gstins.length} GSTINs...`, 5000);
        
        const response = await fetch('/api/search/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ gstins })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayBatchResults(result.results);
            resultsDiv.style.display = 'block';
            window.notificationManager.showSuccess(`✅ Processed ${result.successful}/${result.processed} GSTINs successfully`);
        } else {
            window.notificationManager.showError(result.error || 'Batch search failed');
        }
    } catch (error) {
        console.error('Batch search error:', error);
        window.notificationManager.showError('Network error. Please try again.');
    }
};

function displayBatchResults(results) {
    const content = document.getElementById('batchResultsContent');
    if (!content) return;
    
    content.innerHTML = `
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; overflow: hidden;">
                <thead>
                    <tr style="background: var(--bg-hover);">
                        <th style="padding: 0.75rem; text-align: left; color: var(--text-primary); border-bottom: 1px solid var(--border-color);">GSTIN</th>
                        <th style="padding: 0.75rem; text-align: left; color: var(--text-primary); border-bottom: 1px solid var(--border-color);">Company</th>
                        <th style="padding: 0.75rem; text-align: center; color: var(--text-primary); border-bottom: 1px solid var(--border-color);">Score</th>
                        <th style="padding: 0.75rem; text-align: center; color: var(--text-primary); border-bottom: 1px solid var(--border-color);">Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${results.map(result => `
                        <tr style="border-bottom: 1px solid var(--border-color);">
                            <td style="padding: 0.75rem; font-family: monospace; color: var(--text-primary);">${result.gstin}</td>
                            <td style="padding: 0.75rem; color: var(--text-primary);">${result.success ? result.company_name : 'N/A'}</td>
                            <td style="padding: 0.75rem; text-align: center;">
                                ${result.success && result.compliance_score ? 
                                    `<span style="background: ${result.compliance_score >= 80 ? 'rgba(16, 185, 129, 0.2)' : result.compliance_score >= 60 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${result.compliance_score >= 80 ? 'var(--success)' : result.compliance_score >= 60 ? 'var(--warning)' : 'var(--error)'}; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">${Math.round(result.compliance_score)}%</span>` : 
                                    '<span style="color: var(--text-muted);">N/A</span>'
                                }
                            </td>
                            <td style="padding: 0.75rem; text-align: center;">
                                ${result.success ? 
                                    '<span style="color: var(--success);">✅ Success</span>' : 
                                    '<span style="color: var(--error);">❌ Failed</span>'
                                }
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

window.clearBatchInput = function() {
    const input = document.getElementById('batchGstinInput');
    const resultsDiv = document.getElementById('batchResults');
    
    if (input) input.value = '';
    if (resultsDiv) resultsDiv.style.display = 'none';
};

// ===========================================
// 6. MISSING PRINT FUNCTIONALITY
// ===========================================

window.printResults = function() {
    window.print();
};

// Enhanced print styles
const printStyles = document.createElement('style');
printStyles.textContent = `
    @media print {
        /* Hide unnecessary elements */
        .no-print, nav, .header, .back-btn, .action-buttons, .fab {
            display: none !important;
        }
        
        /* Optimize for print */
        body {
            background: white !important;
            color: black !important;
        }
        
        .company-header {
            background: #f8f9fa !important;
            color: black !important;
            -webkit-print-color-adjust: exact;
        }
        
        .info-card, .card {
            border: 1px solid #dee2e6 !important;
            page-break-inside: avoid;
        }
        
        /* Ensure table readability */
        table {
            border-collapse: collapse !important;
        }
        
        th, td {
            border: 1px solid #dee2e6 !important;
            padding: 0.5rem !important;
        }
    }
`;
document.head.appendChild(printStyles);

// ===========================================
// 7. MISSING OFFLINE FUNCTIONALITY
// ===========================================

window.offlineManager = {
    isOnline: navigator.onLine,
    
    init() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            if (window.notificationManager) {
                window.notificationManager.showSuccess('🌐 Connection restored!', 3000);
            }
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            if (window.notificationManager) {
                window.notificationManager.showWarning('📡 You are offline. Some features may be limited.', 5000);
            }
        });
    },
    
    async syncOfflineData() {
        // Sync any offline stored data when connection is restored
        const offlineSearches = JSON.parse(localStorage.getItem('offlineSearches') || '[]');
        
        if (offlineSearches.length > 0) {
            try {
                for (const search of offlineSearches) {
                    await fetch('/api/search/recent', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(search)
                    });
                }
                
                localStorage.removeItem('offlineSearches');
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`📤 Synced ${offlineSearches.length} offline searches`);
                }
            } catch (error) {
                console.error('Sync failed:', error);
            }
        }
    }
};

// ===========================================
// 8. MISSING SESSION MANAGEMENT
// ===========================================

window.sessionManager = {
    checkInterval: null,
    
    init() {
        // Check session every 5 minutes
        this.checkInterval = setInterval(() => {
            this.checkSession();
        }, 5 * 60 * 1000);
        
        // Check on visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkSession();
            }
        });
    },
    
    async checkSession() {
        try {
            const response = await fetch('/api/user/stats');
            if (response.status === 401 || response.status === 403) {
                this.handleExpiredSession();
            }
        } catch (error) {
            console.warn('Session check failed:', error);
        }
    },
    
    handleExpiredSession() {
        if (window.notificationManager) {
            window.notificationManager.showWarning(
                '⏰ Your session has expired. <button onclick="location.reload()" style="background:var(--accent-primary);color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;margin-left:0.5rem;cursor:pointer;">Refresh</button>',
                10000
            );
        }
        
        // Clear interval to prevent repeated checks
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
    },
    
    destroy() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
    }
};

// ===========================================
// 9. MISSING ERROR BOUNDARY
// ===========================================

window.errorBoundary = {
    init() {
        // Global error handler
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'JavaScript Error');
        });
        
        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'Unhandled Promise Rejection');
            event.preventDefault(); // Prevent browser default handling
        });
    },
    
    handleError(error, type) {
        console.error(`${type}:`, error);
        
        // Don't spam the user with error notifications
        if (!this.lastErrorTime || Date.now() - this.lastErrorTime > 5000) {
            if (window.notificationManager) {
                window.notificationManager.showError(
                    '⚠️ Something went wrong. If this persists, please refresh the page.',
                    8000
                );
            }
            this.lastErrorTime = Date.now();
        }
        
        // Log to server if in production
        if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            this.logErrorToServer(error, type);
        }
    },
    
    async logErrorToServer(error, type) {
        try {
            await fetch('/api/system/error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type,
                    message: error.message || String(error),
                    stack: error.stack,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (logError) {
            console.warn('Failed to log error to server:', logError);
        }
    }
};

// ===========================================
// 10. MISSING ACCESSIBILITY FEATURES
// ===========================================

window.accessibilityManager = {
    init() {
        this.setupKeyboardNavigation();
        this.setupScreenReaderSupport();
        this.setupFocusManagement();
    },
    
    setupKeyboardNavigation() {
        // Escape key handling
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close any open modals or dropdowns
                if (window.modalManager) {
                    window.modalManager.closeAllModals();
                }
                
                // Close user dropdown
                const userDropdown = document.getElementById('userDropdownMenu');
                if (userDropdown && userDropdown.classList.contains('active')) {
                    userDropdown.classList.remove('active');
                    const userBtn = document.getElementById('userProfileBtn');
                    if (userBtn) {
                        userBtn.classList.remove('active');
                        userBtn.focus();
                    }
                }
            }
        });
    },
    
    setupScreenReaderSupport() {
        // Add screen reader announcements for dynamic content
        this.announcer = document.createElement('div');
        this.announcer.setAttribute('aria-live', 'polite');
        this.announcer.setAttribute('aria-atomic', 'true');
        this.announcer.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
        document.body.appendChild(this.announcer);
    },
    
    announce(message) {
        if (this.announcer) {
            this.announcer.textContent = message;
        }
    },
    
    setupFocusManagement() {
        // Focus visible outline for keyboard users
        document.addEventListener('keydown', () => {
            document.body.classList.add('keyboard-navigation');
        });
        
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }
};

// ===========================================
// 11. INITIALIZE ALL ADDITIONAL FEATURES
// ===========================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all additional features
    setTimeout(() => {
        if (window.Chart) {
            window.initializeChartsSafely();
        }
        
        window.offlineManager.init();
        window.sessionManager.init();
        window.errorBoundary.init();
        window.accessibilityManager.init();
        
        console.log('✅ Additional features initialized');
    }, 1000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.sessionManager) {
        window.sessionManager.destroy();
    }
});

console.log('🔧 Additional missing implementations loaded');