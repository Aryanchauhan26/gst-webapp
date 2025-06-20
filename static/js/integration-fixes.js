// =====================================================
// GST Intelligence Platform - Frontend Integration Module
// Complete integration layer for frontend-backend communication
// =====================================================

'use strict';

console.log('🔧 GST Integration Module Loading...');

// =====================================================
// 1. INTEGRATION CONFIGURATION
// =====================================================

window.GST_INTEGRATION = {
    VERSION: '2.0.0',
    DEBUG: localStorage.getItem('gst_debug') === 'true',
    
    CONFIG: {
        API_TIMEOUT: 10000,
        RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 1000,
        CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    },
    
    state: {
        initialized: false,
        userProfile: null,
        userPreferences: null,
        userStats: null
    },
    
    utils: {
        log: function(...args) {
            if (window.GST_INTEGRATION.DEBUG) {
                console.log('🔧 INTEGRATION:', ...args);
            }
        },
        
        error: function(...args) {
            console.error('❌ INTEGRATION:', ...args);
        },
        
        showNotification: function(message, type = 'info', duration = 3000) {
            if (window.notificationManager) {
                window.notificationManager.show(message, type, duration);
            } else {
                console.log(`${type.toUpperCase()}: ${message}`);
            }
        }
    }
};

// =====================================================
// 2. API CLIENT WITH RETRY LOGIC
// =====================================================

class APIClient {
    constructor() {
        this.baseURL = '';
        this.timeout = window.GST_INTEGRATION.CONFIG.API_TIMEOUT;
        this.retryAttempts = window.GST_INTEGRATION.CONFIG.RETRY_ATTEMPTS;
        this.retryDelay = window.GST_INTEGRATION.CONFIG.RETRY_DELAY;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                window.GST_INTEGRATION.utils.log(`API Request (attempt ${attempt}):`, endpoint);
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                window.GST_INTEGRATION.utils.log(`API Response:`, data);
                
                return data;
                
            } catch (error) {
                window.GST_INTEGRATION.utils.error(`API Error (attempt ${attempt}):`, error);
                
                if (attempt === this.retryAttempts) {
                    throw error;
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
            }
        }
    }

    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// =====================================================
// 3. USER PROFILE MANAGER
// =====================================================

class UserProfileManager {
    constructor(apiClient) {
        this.api = apiClient;
        this.profileCache = null;
        this.cacheTimestamp = null;
    }

    async loadUserProfile() {
        try {
            // Check cache first
            if (this.profileCache && this.isCacheValid()) {
                return this.profileCache;
            }

            const response = await this.api.get('/api/user/profile');
            if (response.success) {
                this.profileCache = response.data;
                this.cacheTimestamp = Date.now();
                window.GST_INTEGRATION.state.userProfile = response.data;
                return response.data;
            }
            throw new Error(response.error || 'Failed to load profile');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Profile load failed:', error);
            return {};
        }
    }

    async saveUserProfile(profileData) {
        try {
            const response = await this.api.post('/api/user/profile', profileData);
            if (response.success) {
                this.profileCache = { ...this.profileCache, ...profileData };
                this.cacheTimestamp = Date.now();
                window.GST_INTEGRATION.state.userProfile = this.profileCache;
                return true;
            }
            throw new Error(response.error || 'Failed to save profile');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Profile save failed:', error);
            return false;
        }
    }

    async loadUserStats() {
        try {
            const response = await this.api.get('/api/user/stats');
            if (response.success) {
                window.GST_INTEGRATION.state.userStats = response.data;
                return response.data;
            }
            throw new Error(response.error || 'Failed to load stats');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Stats load failed:', error);
            return {};
        }
    }

    async loadUserPreferences() {
        try {
            const response = await this.api.get('/api/user/preferences');
            if (response.success) {
                window.GST_INTEGRATION.state.userPreferences = response.data;
                return response.data;
            }
            throw new Error(response.error || 'Failed to load preferences');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Preferences load failed:', error);
            return {};
        }
    }

    async saveUserPreferences(preferences) {
        try {
            const response = await this.api.post('/api/user/preferences', preferences);
            if (response.success) {
                window.GST_INTEGRATION.state.userPreferences = { 
                    ...window.GST_INTEGRATION.state.userPreferences, 
                    ...preferences 
                };
                return true;
            }
            throw new Error(response.error || 'Failed to save preferences');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Preferences save failed:', error);
            return false;
        }
    }

    async changePassword(currentPassword, newPassword) {
        try {
            const response = await this.api.post('/api/user/change-password', {
                currentPassword,
                newPassword
            });
            return response.success;
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Password change failed:', error);
            return false;
        }
    }

    async clearUserData() {
        try {
            const response = await this.api.delete('/api/user/data');
            if (response.success) {
                // Clear local cache
                this.profileCache = null;
                this.cacheTimestamp = null;
                return response.deleted_count || 0;
            }
            throw new Error(response.error || 'Failed to clear data');
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Data clear failed:', error);
            return 0;
        }
    }

    isCacheValid() {
        return this.cacheTimestamp && 
               (Date.now() - this.cacheTimestamp) < window.GST_INTEGRATION.CONFIG.CACHE_DURATION;
    }

    invalidateCache() {
        this.profileCache = null;
        this.cacheTimestamp = null;
    }
}

// =====================================================
// 4. ENHANCED MODAL SYSTEM
// =====================================================

class EnhancedModalSystem {
    constructor() {
        this.activeModals = new Map();
        this.zIndexCounter = 1050;
    }

    async openProfileModal() {
        try {
            const [profileData, statsData] = await Promise.all([
                window.GST_INTEGRATION.userManager.loadUserProfile(),
                window.GST_INTEGRATION.userManager.loadUserStats()
            ]);

            const modalContent = this.createProfileModalContent(profileData, statsData);
            
            return this.createModal({
                id: 'profile-modal',
                title: '👤 Enhanced Profile Settings',
                content: modalContent,
                size: 'large',
                onSubmit: this.handleProfileSubmit.bind(this)
            });
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Profile modal error:', error);
            window.GST_INTEGRATION.utils.showNotification('Failed to load profile data', 'error');
        }
    }

    createProfileModalContent(profile, stats) {
        return `
            <div class="profile-modal-content">
                <!-- User Stats Overview -->
                <div class="stats-overview">
                    <h4><i class="fas fa-chart-bar"></i> Your Activity Overview</h4>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${stats.total_searches || 0}</div>
                            <div class="stat-label">Total Searches</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${stats.unique_companies || 0}</div>
                            <div class="stat-label">Companies Analyzed</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${Math.round(stats.avg_compliance || 0)}%</div>
                            <div class="stat-label">Avg Compliance</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${stats.recent_searches || 0}</div>
                            <div class="stat-label">Recent Activity</div>
                        </div>
                    </div>
                    
                    <!-- User Level Badge -->
                    <div class="user-level-badge">
                        <div class="level-icon">
                            <i class="${stats.user_level?.icon || 'fas fa-user'}"></i>
                        </div>
                        <div class="level-info">
                            <div class="level-title">${stats.user_level?.level || 'New User'}</div>
                            <div class="level-subtitle">Current Level</div>
                        </div>
                    </div>
                </div>
                
                <!-- Profile Form -->
                <form id="profileForm" class="profile-form">
                    <div class="form-section">
                        <h4><i class="fas fa-user-edit"></i> Personal Information</h4>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="displayName">Display Name *</label>
                                <input type="text" 
                                       id="displayName" 
                                       name="display_name" 
                                       value="${profile.display_name || ''}" 
                                       placeholder="Your full name"
                                       required>
                            </div>
                            <div class="form-group">
                                <label for="designation">Designation</label>
                                <input type="text" 
                                       id="designation" 
                                       name="designation" 
                                       value="${profile.designation || ''}" 
                                       placeholder="Your job title">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <h4><i class="fas fa-building"></i> Company Information</h4>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="company">Company Name</label>
                                <input type="text" 
                                       id="company" 
                                       name="company" 
                                       value="${profile.company || ''}" 
                                       placeholder="Your company name">
                            </div>
                            <div class="form-group">
                                <label for="email">Email</label>
                                <input type="email" 
                                       id="email" 
                                       name="email" 
                                       value="${profile.email || ''}" 
                                       placeholder="your.email@company.com">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Achievements Section -->
                    ${this.createAchievementsSection(stats.achievements)}
                    
                    <div class="form-actions">
                        <button type="submit" class="btn btn--primary">
                            <i class="fas fa-save"></i> Save Profile
                        </button>
                        <button type="button" class="btn btn--danger" onclick="window.GST_INTEGRATION.clearUserData()">
                            <i class="fas fa-trash"></i> Clear Data
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    createAchievementsSection(achievements) {
        if (!achievements || achievements.length === 0) return '';
        
        return `
            <div class="form-section">
                <h4><i class="fas fa-trophy"></i> Your Achievements</h4>
                <div class="achievements-grid">
                    ${achievements.map(achievement => `
                        <div class="achievement-item ${achievement.unlocked ? 'unlocked' : 'locked'}">
                            <div class="achievement-icon">${achievement.unlocked ? '🏆' : '🔒'}</div>
                            <div class="achievement-info">
                                <div class="achievement-title">${achievement.title}</div>
                                <div class="achievement-desc">${achievement.description}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    async openSettingsModal() {
        try {
            const preferences = await window.GST_INTEGRATION.userManager.loadUserPreferences();
            const modalContent = this.createSettingsModalContent(preferences);
            
            return this.createModal({
                id: 'settings-modal',
                title: '⚙️ Settings & Preferences',
                content: modalContent,
                size: 'medium',
                onSubmit: this.handleSettingsSubmit.bind(this)
            });
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Settings modal error:', error);
            window.GST_INTEGRATION.utils.showNotification('Failed to load settings', 'error');
        }
    }

    createSettingsModalContent(preferences) {
        return `
            <div class="settings-modal-content">
                <form id="settingsForm" class="settings-form">
                    <!-- Theme Settings -->
                    <div class="settings-section">
                        <h4><i class="fas fa-palette"></i> Theme & Appearance</h4>
                        <div class="setting-item">
                            <span class="setting-label">Dark Mode</span>
                            <div class="theme-toggle-control">
                                <label class="toggle-switch">
                                    <input type="checkbox" ${this.getCurrentTheme() === 'dark' ? 'checked' : ''} onchange="window.themeManager?.toggleTheme()">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Notification Settings -->
                    <div class="settings-section">
                        <h4><i class="fas fa-bell"></i> Notifications</h4>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="emailNotifications" ${preferences.emailNotifications ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Email Notifications</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="pushNotifications" ${preferences.pushNotifications ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Push Notifications</span>
                            </label>
                        </div>
                    </div>

                    <!-- Application Settings -->
                    <div class="settings-section">
                        <h4><i class="fas fa-cog"></i> Application Settings</h4>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="autoSearch" ${preferences.autoSearch !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Auto-Search on GSTIN Paste</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="saveHistory" ${preferences.saveHistory !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Save Search History</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="analytics" ${preferences.analytics !== false ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Enable Analytics</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" name="compactMode" ${preferences.compactMode ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Compact Mode</span>
                            </label>
                        </div>
                    </div>

                    <!-- Debug Settings -->
                    <div class="settings-section">
                        <h4><i class="fas fa-bug"></i> Developer Settings</h4>
                        <div class="setting-item">
                            <label class="setting-checkbox">
                                <input type="checkbox" id="debugModeToggle" ${window.GST_INTEGRATION.DEBUG ? 'checked' : ''}>
                                <span class="checkbox-custom"></span>
                                <span class="setting-label">Debug Mode</span>
                            </label>
                        </div>
                        <div class="setting-item">
                            <button type="button" class="btn btn--secondary" onclick="window.GST_INTEGRATION.exportAllData()">
                                <i class="fas fa-download"></i> Export All Data
                            </button>
                        </div>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn--primary">
                            <i class="fas fa-save"></i> Save Settings
                        </button>
                        <button type="button" class="btn btn--secondary" onclick="window.GST_INTEGRATION.resetSettings()">
                            <i class="fas fa-undo"></i> Reset
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    createModal(options) {
        const { id, title, content, size = 'medium', onSubmit } = options;
        
        // Remove existing modal with same ID
        if (this.activeModals.has(id)) {
            this.closeModal(id);
        }

        const modal = document.createElement('div');
        modal.id = id;
        modal.className = 'enhanced-modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(5px);
            z-index: ${this.zIndexCounter++};
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            padding: 1rem;
        `;

        const sizeStyles = {
            small: 'max-width: 400px;',
            medium: 'max-width: 600px;',
            large: 'max-width: 900px;',
            fullscreen: 'width: 95%; height: 95%;'
        };

        modal.innerHTML = `
            <div class="enhanced-modal-content" style="
                background: var(--bg-card);
                border-radius: 20px;
                ${sizeStyles[size]}
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: var(--hover-shadow);
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
                    <button class="modal-close-btn" style="
                        background: none;
                        border: none;
                        color: var(--text-secondary);
                        font-size: 1.5rem;
                        cursor: pointer;
                        padding: 0.5rem;
                        border-radius: 8px;
                        transition: all 0.3s ease;
                    " onclick="window.GST_INTEGRATION.modalSystem.closeModal('${id}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body" style="padding: 2rem;">
                    ${content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Show animation
        requestAnimationFrame(() => {
            modal.style.opacity = '1';
            const modalContent = modal.querySelector('.enhanced-modal-content');
            modalContent.style.transform = 'scale(1)';
        });

        // Handle backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(id);
            }
        });

        // Handle form submission
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
                            this.closeModal(id);
                        }
                    } catch (error) {
                        window.GST_INTEGRATION.utils.error('Form submission error:', error);
                    }
                });
            }
        }

        // Store modal reference
        this.activeModals.set(id, { element: modal, options });
        
        return modal;
    }

    closeModal(id) {
        const modalData = this.activeModals.get(id);
        if (!modalData) return;

        const modal = modalData.element;
        modal.style.opacity = '0';
        
        const modalContent = modal.querySelector('.enhanced-modal-content');
        if (modalContent) {
            modalContent.style.transform = 'scale(0.9)';
        }

        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
            this.activeModals.delete(id);
        }, 300);
    }

    async handleProfileSubmit(formData) {
        try {
            const success = await window.GST_INTEGRATION.userManager.saveUserProfile(formData);
            if (success) {
                window.GST_INTEGRATION.utils.showNotification('✨ Profile updated successfully!', 'success');
                
                // Update display name in UI
                this.updateDisplayName(formData.display_name);
                
                // Refresh page data after delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                
                return true;
            } else {
                window.GST_INTEGRATION.utils.showNotification('Failed to save profile', 'error');
                return false;
            }
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Profile submission error:', error);
            window.GST_INTEGRATION.utils.showNotification('Failed to save profile', 'error');
            return false;
        }
    }

    async handleSettingsSubmit(formData) {
        try {
            // Handle debug mode toggle
            const debugCheckbox = document.getElementById('debugModeToggle');
            if (debugCheckbox) {
                if (debugCheckbox.checked) {
                    localStorage.setItem('gst_debug', 'true');
                    window.GST_INTEGRATION.DEBUG = true;
                } else {
                    localStorage.setItem('gst_debug', 'false');
                    window.GST_INTEGRATION.DEBUG = false;
                }
            }

            const success = await window.GST_INTEGRATION.userManager.saveUserPreferences(formData);
            if (success) {
                window.GST_INTEGRATION.utils.showNotification('⚙️ Settings saved successfully!', 'success');
                
                // Apply settings immediately
                this.applySettings(formData);
                
                return true;
            } else {
                window.GST_INTEGRATION.utils.showNotification('Failed to save settings', 'error');
                return false;
            }
        } catch (error) {
            window.GST_INTEGRATION.utils.error('Settings submission error:', error);
            window.GST_INTEGRATION.utils.showNotification('Failed to save settings', 'error');
            return false;
        }
    }

    updateDisplayName(displayName) {
        const nameElements = document.querySelectorAll('#userDisplayName, .user__name, .user-name');
        nameElements.forEach(element => {
            if (displayName) {
                element.textContent = displayName;
            }
        });
    }

    applySettings(settings) {
        // Apply compact mode
        if (settings.compactMode) {
            document.body.classList.add('compact-mode');
        } else {
            document.body.classList.remove('compact-mode');
        }

        // Store settings in localStorage for immediate access
        localStorage.setItem('gst_user_preferences', JSON.stringify(settings));
    }

    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    }
}

// =====================================================
// 5. UTILITY FUNCTIONS
// =====================================================

async function clearUserData() {
    if (!confirm('⚠️ Are you sure you want to clear all your search history? This action cannot be undone.')) {
        return;
    }

    try {
        const deletedCount = await window.GST_INTEGRATION.userManager.clearUserData();
        window.GST_INTEGRATION.utils.showNotification(
            `🗑️ Cleared ${deletedCount} search records`, 
            'success'
        );
        
        // Close modal and refresh page
        window.GST_INTEGRATION.modalSystem.closeModal('profile-modal');
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    } catch (error) {
        window.GST_INTEGRATION.utils.error('Data clear error:', error);
        window.GST_INTEGRATION.utils.showNotification('Failed to clear data', 'error');
    }
}

function exportAllData() {
    window.location.href = '/export/history';
    window.GST_INTEGRATION.utils.showNotification('📊 Preparing data export...', 'info');
}

async function resetSettings() {
    if (!confirm('Reset all settings to default values?')) {
        return;
    }

    const defaultSettings = {
        emailNotifications: false,
        pushNotifications: false,
        autoSearch: true,
        saveHistory: true,
        analytics: true,
        compactMode: false
    };

    try {
        const success = await window.GST_INTEGRATION.userManager.saveUserPreferences(defaultSettings);
        if (success) {
            window.GST_INTEGRATION.utils.showNotification('⚙️ Settings reset to defaults!', 'success');
            window.GST_INTEGRATION.modalSystem.closeModal('settings-modal');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            window.GST_INTEGRATION.utils.showNotification('Failed to reset settings', 'error');
        }
    } catch (error) {
        window.GST_INTEGRATION.utils.error('Settings reset error:', error);
        window.GST_INTEGRATION.utils.showNotification('Failed to reset settings', 'error');
    }
}

// =====================================================
// 6. INITIALIZATION & EXPORTS
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    if (window.GST_INTEGRATION.state.initialized) return;

    try {
        // Initialize core components
        window.GST_INTEGRATION.apiClient = new APIClient();
        window.GST_INTEGRATION.userManager = new UserProfileManager(window.GST_INTEGRATION.apiClient);
        window.GST_INTEGRATION.modalSystem = new EnhancedModalSystem();

        // Add required CSS
        if (!document.getElementById('integration-styles')) {
            const style = document.createElement('style');
            style.id = 'integration-styles';
            style.textContent = `
                .profile-modal-content { display: flex; flex-direction: column; gap: 2rem; }
                .stats-overview { background: var(--bg-hover); border-radius: 12px; padding: 1.5rem; }
                .stats-overview h4 { margin-bottom: 1rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
                .stat-item { text-align: center; background: var(--bg-card); padding: 1rem; border-radius: 8px; }
                .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 0.25rem; }
                .stat-label { font-size: 0.8rem; color: var(--text-secondary); }
                .user-level-badge { display: flex; align-items: center; justify-content: center; gap: 1rem; background: var(--bg-card); padding: 1rem; border-radius: 12px; }
                .level-icon { width: 40px; height: 40px; background: var(--accent-gradient); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; }
                .level-title { font-weight: 600; color: var(--text-primary); }
                .level-subtitle { font-size: 0.8rem; color: var(--text-secondary); }
                .form-section { background: var(--bg-hover); border-radius: 12px; padding: 1.5rem; }
                .form-section h4 { margin-bottom: 1rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem; }
                .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
                .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
                .form-group label { font-weight: 500; color: var(--text-secondary); }
                .form-group input { padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); }
                .achievements-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
                .achievement-item { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; text-align: center; }
                .achievement-item.unlocked { border-color: var(--success); background: rgba(16, 185, 129, 0.1); }
                .achievement-icon { font-size: 2rem; margin-bottom: 0.5rem; }
                .achievement-title { font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
                .achievement-desc { font-size: 0.8rem; color: var(--text-secondary); }
                .form-actions { display: flex; gap: 1rem; margin-top: 1.5rem; }
                .settings-modal-content { display: flex; flex-direction: column; gap: 1.5rem; }
                .settings-section { background: var(--bg-hover); border-radius: 12px; padding: 1.5rem; }
                .settings-section h4 { margin-bottom: 1rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem; }
                .setting-item { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border-color); }
                .setting-item:last-child { border-bottom: none; }
                .setting-label { color: var(--text-primary); }
                .setting-checkbox { display: flex; align-items: center; gap: 0.75rem; cursor: pointer; }
                .checkbox-custom { width: 20px; height: 20px; border: 2px solid var(--border-color); border-radius: 4px; position: relative; transition: all 0.3s; }
                .setting-checkbox input:checked + .checkbox-custom { background: var(--accent-primary); border-color: var(--accent-primary); }
                .setting-checkbox input:checked + .checkbox-custom::after { content: '✓'; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 12px; font-weight: bold; }
                .setting-checkbox input { display: none; }
                .toggle-switch { position: relative; display: inline-block; width: 60px; height: 30px; }
                .toggle-switch input { opacity: 0; width: 0; height: 0; }
                .toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 30px; transition: 0.3s; }
                .toggle-slider:before { position: absolute; content: ""; height: 22px; width: 22px; left: 3px; bottom: 3px; background: var(--text-primary); border-radius: 50%; transition: 0.3s; }
                .toggle-switch input:checked + .toggle-slider { background: var(--accent-primary); }
                .toggle-switch input:checked + .toggle-slider:before { transform: translateX(30px); background: white; }
            `;
            document.head.appendChild(style);
        }

        // Export global functions
        window.openEnhancedProfileModal = () => window.GST_INTEGRATION.modalSystem.openProfileModal();
        window.openSettingsModal = () => window.GST_INTEGRATION.modalSystem.openSettingsModal();
        window.GST_INTEGRATION.clearUserData = clearUserData;
        window.GST_INTEGRATION.exportAllData = exportAllData;
        window.GST_INTEGRATION.resetSettings = resetSettings;

        window.GST_INTEGRATION.state.initialized = true;
        window.GST_INTEGRATION.utils.log('Integration Module initialized successfully');

    } catch (error) {
        window.GST_INTEGRATION.utils.error('Integration initialization failed:', error);
    }
});

console.log('✅ GST Integration Module Loaded Successfully!');