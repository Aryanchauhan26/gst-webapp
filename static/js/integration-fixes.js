// =============================================================================
// GST Intelligence Platform - Integration Fixes Module
// Clean and optimized integration enhancements
// =============================================================================

'use strict';

// Global Integration Module
window.GST_INTEGRATION = {
    version: '2.0.0',
    initialized: false,
    state: {
        user: null,
        preferences: {},
        cache: new Map()
    },
    
    // Utility functions
    utils: {
        log: (message, ...args) => {
            if (window.GST_APP?.debug) {
                console.log('🔧 Integration:', message, ...args);
            }
        },
        
        error: (message, ...args) => {
            console.error('❌ Integration Error:', message, ...args);
        },
        
        debounce: (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        formatGSTIN: (gstin) => {
            if (!gstin || gstin.length !== 15) return gstin;
            return `${gstin.substr(0, 2)} ${gstin.substr(2, 5)} ${gstin.substr(7, 4)} ${gstin.substr(11, 4)}`;
        },
        
        validateGSTIN: (gstin) => {
            if (!gstin) return false;
            const clean = gstin.replace(/\s/g, '').toUpperCase();
            return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(clean);
        }
    },
    
    // Modal system enhancements
    modalSystem: {
        init() {
            this.setupModalDefaults();
            this.enhanceExistingModals();
        },
        
        setupModalDefaults() {
            // Add global modal styles if not present
            if (!document.getElementById('integration-modal-styles')) {
                const style = document.createElement('style');
                style.id = 'integration-modal-styles';
                style.textContent = `
                    .modal-enhanced {
                        animation: modalSlideIn 0.3s ease-out;
                    }
                    
                    @keyframes modalSlideIn {
                        from {
                            opacity: 0;
                            transform: translateY(-50px);
                        }
                        to {
                            opacity: 1;
                            transform: translateY(0);
                        }
                    }
                    
                    .modal-backdrop-blur {
                        backdrop-filter: blur(8px);
                        background: rgba(0, 0, 0, 0.7);
                    }
                `;
                document.head.appendChild(style);
            }
        },
        
        enhanceExistingModals() {
            // Enhance any existing modals with better styling
            document.querySelectorAll('.modal').forEach(modal => {
                modal.classList.add('modal-enhanced');
                const backdrop = modal.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.classList.add('modal-backdrop-blur');
                }
            });
        },
        
        openProfileModal() {
            if (window.modalManager) {
                const modalContent = this.createProfileModalContent();
                window.modalManager.createModal('profile-modal', modalContent, {
                    onClose: () => console.log('Profile modal closed')
                });
            }
        },
        
        openSettingsModal() {
            if (window.modalManager) {
                const modalContent = this.createSettingsModalContent();
                window.modalManager.createModal('settings-modal', modalContent, {
                    onClose: () => console.log('Settings modal closed')
                });
            }
        },
        
        createProfileModalContent() {
            return `
                <div class="modal-header">
                    <h2 class="modal-title">
                        <i class="fas fa-user-edit"></i>
                        User Profile
                    </h2>
                </div>
                <div class="modal-body">
                    <form id="profileForm" class="form-grid">
                        <div class="form-group">
                            <label for="userName">Name</label>
                            <input type="text" id="userName" name="name" class="form-input" placeholder="Enter your name">
                        </div>
                        <div class="form-group">
                            <label for="userEmail">Email</label>
                            <input type="email" id="userEmail" name="email" class="form-input" placeholder="Enter your email">
                        </div>
                        <div class="form-group">
                            <label for="userCompany">Company</label>
                            <input type="text" id="userCompany" name="company" class="form-input" placeholder="Company name">
                        </div>
                        <div class="form-group">
                            <label for="userDesignation">Designation</label>
                            <input type="text" id="userDesignation" name="designation" class="form-input" placeholder="Your role">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn--secondary" data-modal-close>Cancel</button>
                    <button type="button" class="btn btn--primary" onclick="window.GST_INTEGRATION.modalSystem.saveProfile()">
                        <i class="fas fa-save"></i> Save Profile
                    </button>
                </div>
            `;
        },
        
        createSettingsModalContent() {
            return `
                <div class="modal-header">
                    <h2 class="modal-title">
                        <i class="fas fa-cog"></i>
                        Settings & Preferences
                    </h2>
                </div>
                <div class="modal-body">
                    <div class="settings-section">
                        <h3>Appearance</h3>
                        <div class="setting-item">
                            <label class="setting-label">
                                <span>Theme</span>
                                <select id="themeSelect" class="form-select">
                                    <option value="dark">Dark</option>
                                    <option value="light">Light</option>
                                    <option value="auto">Auto</option>
                                </select>
                            </label>
                        </div>
                    </div>
                    
                    <div class="settings-section">
                        <h3>Notifications</h3>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" id="enableNotifications" checked>
                                <span>Enable notifications</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" id="emailAlerts">
                                <span>Email alerts</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="settings-section">
                        <h3>Data & Privacy</h3>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" id="autoExport">
                                <span>Auto-export data monthly</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <button type="button" class="btn btn--outline" onclick="window.GST_INTEGRATION.clearUserData()">
                                <i class="fas fa-trash"></i> Clear All Data
                            </button>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn--secondary" data-modal-close>Cancel</button>
                    <button type="button" class="btn btn--primary" onclick="window.GST_INTEGRATION.modalSystem.saveSettings()">
                        <i class="fas fa-save"></i> Save Settings
                    </button>
                </div>
            `;
        },
        
        async saveProfile() {
            const form = document.getElementById('profileForm');
            if (!form) return;
            
            const formData = new FormData(form);
            const profileData = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/user/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(profileData)
                });
                
                if (response.ok) {
                    if (window.notificationManager) {
                        window.notificationManager.showSuccess('Profile updated successfully');
                    }
                    if (window.modalManager) {
                        window.modalManager.closeModal('profile-modal');
                    }
                } else {
                    throw new Error('Failed to save profile');
                }
            } catch (error) {
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to save profile');
                }
            }
        },
        
        async saveSettings() {
            const settings = {
                theme: document.getElementById('themeSelect')?.value || 'dark',
                notifications: document.getElementById('enableNotifications')?.checked || false,
                email_alerts: document.getElementById('emailAlerts')?.checked || false,
                auto_export: document.getElementById('autoExport')?.checked || false
            };
            
            try {
                const response = await fetch('/api/user/preferences', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                
                if (response.ok) {
                    // Apply theme immediately
                    if (window.themeManager) {
                        window.themeManager.setTheme(settings.theme);
                    }
                    
                    if (window.notificationManager) {
                        window.notificationManager.showSuccess('Settings saved successfully');
                    }
                    if (window.modalManager) {
                        window.modalManager.closeModal('settings-modal');
                    }
                } else {
                    throw new Error('Failed to save settings');
                }
            } catch (error) {
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to save settings');
                }
            }
        }
    },
    
    // Search enhancements
    searchEnhancements: {
        init() {
            this.setupGSTINFormatting();
            this.setupSearchSuggestions();
            this.enhanceSearchHistory();
        },
        
        setupGSTINFormatting() {
            // Auto-format GSTIN inputs
            document.querySelectorAll('input[name="gstin"], #gstinInput').forEach(input => {
                input.addEventListener('input', (e) => {
                    let value = e.target.value.toUpperCase().replace(/[^0-9A-Z]/g, '');
                    if (value.length > 15) value = value.substr(0, 15);
                    e.target.value = value;
                    
                    // Visual validation
                    if (value.length === 15) {
                        if (window.GST_INTEGRATION.utils.validateGSTIN(value)) {
                            e.target.classList.add('valid');
                            e.target.classList.remove('invalid');
                        } else {
                            e.target.classList.add('invalid');
                            e.target.classList.remove('valid');
                        }
                    } else {
                        e.target.classList.remove('valid', 'invalid');
                    }
                });
            });
        },
        
        setupSearchSuggestions() {
            // Enhanced search suggestions
            const searchInputs = document.querySelectorAll('input[name="gstin"], #gstinInput');
            searchInputs.forEach(input => {
                const suggestionsContainer = this.createSuggestionsContainer(input);
                
                input.addEventListener('input', window.GST_INTEGRATION.utils.debounce((e) => {
                    this.showSuggestions(e.target, suggestionsContainer);
                }, 300));
                
                // Hide suggestions when clicking outside
                document.addEventListener('click', (e) => {
                    if (!input.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                        suggestionsContainer.style.display = 'none';
                    }
                });
            });
        },
        
        createSuggestionsContainer(input) {
            const container = document.createElement('div');
            container.className = 'search-suggestions-enhanced';
            container.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--bg-card);
                border: 1px solid var(--border-primary);
                border-radius: 8px;
                box-shadow: var(--card-shadow);
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                display: none;
            `;
            
            input.parentElement.style.position = 'relative';
            input.parentElement.appendChild(container);
            
            return container;
        },
        
        showSuggestions(input, container) {
            const query = input.value.trim();
            if (query.length < 2) {
                container.style.display = 'none';
                return;
            }
            
            // Get recent searches from localStorage for suggestions
            const recentSearches = JSON.parse(localStorage.getItem('recentGSTINSearches') || '[]');
            const suggestions = recentSearches
                .filter(gstin => gstin.toLowerCase().includes(query.toLowerCase()))
                .slice(0, 5);
            
            if (suggestions.length === 0) {
                container.style.display = 'none';
                return;
            }
            
            container.innerHTML = suggestions
                .map(gstin => `
                    <div class="suggestion-item" style="padding: 0.75rem; cursor: pointer; border-bottom: 1px solid var(--border-primary);" 
                         onclick="window.GST_INTEGRATION.searchEnhancements.selectSuggestion('${gstin}', '${input.id}')">
                        <div style="font-weight: 600; color: var(--accent-primary);">${window.GST_INTEGRATION.utils.formatGSTIN(gstin)}</div>
                    </div>
                `)
                .join('');
            
            container.style.display = 'block';
        },
        
        selectSuggestion(gstin, inputId) {
            const input = document.getElementById(inputId);
            if (input) {
                input.value = gstin;
                input.focus();
                // Hide suggestions
                const container = input.parentElement.querySelector('.search-suggestions-enhanced');
                if (container) {
                    container.style.display = 'none';
                }
            }
        },
        
        enhanceSearchHistory() {
            // Add recent searches to localStorage
            const searchForms = document.querySelectorAll('form[action="/search"]');
            searchForms.forEach(form => {
                form.addEventListener('submit', (e) => {
                    const gstinInput = form.querySelector('input[name="gstin"]');
                    if (gstinInput && gstinInput.value) {
                        this.addToRecentSearches(gstinInput.value);
                    }
                });
            });
        },
        
        addToRecentSearches(gstin) {
            if (!window.GST_INTEGRATION.utils.validateGSTIN(gstin)) return;
            
            let recent = JSON.parse(localStorage.getItem('recentGSTINSearches') || '[]');
            recent = recent.filter(item => item !== gstin); // Remove if exists
            recent.unshift(gstin); // Add to beginning
            recent = recent.slice(0, 10); // Keep only last 10
            
            localStorage.setItem('recentGSTINSearches', JSON.stringify(recent));
        }
    },
    
    // Performance optimizations
    performance: {
        init() {
            this.setupLazyLoading();
            this.optimizeImages();
            this.enableResourceHints();
        },
        
        setupLazyLoading() {
            // Intersection Observer for lazy loading
            if ('IntersectionObserver' in window) {
                const lazyElements = document.querySelectorAll('[data-lazy-load]');
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.loadLazyElement(entry.target);
                            observer.unobserve(entry.target);
                        }
                    });
                });
                
                lazyElements.forEach(el => observer.observe(el));
            }
        },
        
        loadLazyElement(element) {
            if (element.dataset.lazySrc) {
                element.src = element.dataset.lazySrc;
                element.removeAttribute('data-lazy-src');
            }
            
            if (element.dataset.lazyLoad) {
                element.classList.add('loaded');
            }
        },
        
        optimizeImages() {
            // Add loading="lazy" to images that don't have it
            document.querySelectorAll('img:not([loading])').forEach(img => {
                img.setAttribute('loading', 'lazy');
            });
        },
        
        enableResourceHints() {
            // Add preconnect for external resources
            const preconnectLinks = [
                'https://cdnjs.cloudflare.com',
                'https://fonts.googleapis.com',
                'https://fonts.gstatic.com'
            ];
            
            preconnectLinks.forEach(href => {
                if (!document.querySelector(`link[href="${href}"]`)) {
                    const link = document.createElement('link');
                    link.rel = 'preconnect';
                    link.href = href;
                    document.head.appendChild(link);
                }
            });
        }
    },
    
    // Data management utilities
    clearUserData() {
        if (!confirm('This will clear all your local data including search history and preferences. Are you sure?')) {
            return;
        }
        
        // Clear localStorage
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('gst_') || key.includes('gstin') || key.includes('search')) {
                localStorage.removeItem(key);
            }
        });
        
        // Clear sessionStorage
        sessionStorage.clear();
        
        // Clear cache
        this.state.cache.clear();
        
        if (window.notificationManager) {
            window.notificationManager.showSuccess('All local data cleared successfully');
        }
        
        // Reload page to reset state
        setTimeout(() => location.reload(), 1000);
    },
    
    async exportAllData() {
        try {
            const response = await fetch('/api/user/export-all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `gst_data_export_${new Date().toISOString().split('T')[0]}.zip`;
                a.click();
                window.URL.revokeObjectURL(url);
                
                if (window.notificationManager) {
                    window.notificationManager.showSuccess('Data export completed');
                }
            }
        } catch (error) {
            if (window.notificationManager) {
                window.notificationManager.showError('Export failed');
            }
        }
    },
    
    resetSettings() {
        if (!confirm('This will reset all settings to default values. Continue?')) {
            return;
        }
        
        localStorage.removeItem('theme');
        localStorage.removeItem('gst_user_preferences');
        
        // Reset theme to dark
        if (window.themeManager) {
            window.themeManager.setTheme('dark');
        }
        
        if (window.notificationManager) {
            window.notificationManager.showSuccess('Settings reset to default');
        }
    }
};

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    try {
        // Wait for other modules to initialize
        setTimeout(() => {
            // Initialize all integration modules
            window.GST_INTEGRATION.modalSystem.init();
            window.GST_INTEGRATION.searchEnhancements.init();
            window.GST_INTEGRATION.performance.init();
            
            // Mark as initialized
            window.GST_INTEGRATION.initialized = true;
            window.GST_INTEGRATION.utils.log('Integration module initialized successfully');
            
            // Dispatch ready event
            window.dispatchEvent(new CustomEvent('gst:integration:ready', {
                detail: { integration: window.GST_INTEGRATION }
            }));
            
        }, 100);
        
    } catch (error) {
        window.GST_INTEGRATION.utils.error('Integration initialization failed:', error);
    }
});

// =============================================================================
// GLOBAL FUNCTIONS (for backward compatibility)
// =============================================================================

// Export functions to global scope
window.openEnhancedProfileModal = () => window.GST_INTEGRATION.modalSystem.openProfileModal();
window.openSettingsModal = () => window.GST_INTEGRATION.modalSystem.openSettingsModal();
window.clearUserData = () => window.GST_INTEGRATION.clearUserData();
window.exportAllData = () => window.GST_INTEGRATION.exportAllData();
window.resetSettings = () => window.GST_INTEGRATION.resetSettings();

// Debug helpers
if (window.GST_APP?.debug) {
    window.integrationDebug = {
        module: window.GST_INTEGRATION,
        state: () => window.GST_INTEGRATION.state,
        cache: () => window.GST_INTEGRATION.state.cache,
        clearCache: () => window.GST_INTEGRATION.state.cache.clear()
    };
}

console.log('✅ GST Integration Module loaded successfully!');