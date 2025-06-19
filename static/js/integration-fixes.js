// Frontend-Backend Integration Fixes
// This file contains fixes for missing functions referenced in templates

// ===========================================
// 1. GLOBAL CONFIGURATION
// ===========================================

window.GST_CONFIG = {
    API_BASE_URL: '',
    USER_PREFERENCES_KEY: 'gst_user_preferences',
    RECENT_SEARCHES_KEY: 'recentGSTINSearches',
    DEBUG_MODE: localStorage.getItem('gst_debug') === 'true',
    MAX_RECENT_SEARCHES: 10,
    NOTIFICATION_DURATION: 5000,
    THEME_TRANSITION_DURATION: 300
};

// ===========================================
// 2. ENHANCED PROFILE MODAL (Fix for missing implementation)
// ===========================================

window.openEnhancedProfileModal = async function() {
    if (!window.modalManager) {
        console.error('Modal manager not initialized');
        return;
    }

    try {
        // Load current user profile data
        const profileResponse = await fetch('/api/user/profile');
        const profileResult = await profileResponse.json();
        
        const statsResponse = await fetch('/api/user/stats');
        const statsResult = await statsResponse.json();
        
        const currentProfile = profileResult.success ? profileResult.data : {};
        const userStats = statsResult.success ? statsResult.data : {};

        const modal = window.modalManager.createModal({
            title: '👤 Enhanced Profile Settings',
            size: 'large',
            content: `
                <div style="display: flex; flex-direction: column; gap: 2rem;">
                    <!-- User Stats Overview -->
                    <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); border-radius: 12px; padding: 2rem; border: 1px solid rgba(124, 58, 237, 0.2);">
                        <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-chart-bar"></i>
                            Your Activity Overview
                        </h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">
                            <div style="text-align: center; background: var(--bg-card); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 1.8rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 0.25rem;">${userStats.total_searches || 0}</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">Total Searches</div>
                            </div>
                            <div style="text-align: center; background: var(--bg-card); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 1.8rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 0.25rem;">${userStats.unique_companies || 0}</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">Companies Analyzed</div>
                            </div>
                            <div style="text-align: center; background: var(--bg-card); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 1.8rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 0.25rem;">${Math.round(userStats.avg_compliance || 0)}%</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">Avg Compliance</div>
                            </div>
                            <div style="text-align: center; background: var(--bg-card); padding: 1rem; border-radius: 8px;">
                                <div style="font-size: 1.8rem; font-weight: 700; color: var(--accent-primary); margin-bottom: 0.25rem;">${userStats.recent_searches || 0}</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">Recent Activity</div>
                            </div>
                        </div>
                        
                        <!-- User Level Badge -->
                        <div style="margin-top: 1.5rem; text-align: center;">
                            <div style="display: inline-flex; align-items: center; gap: 1rem; background: var(--bg-card); padding: 1rem 2rem; border-radius: 20px; border: 1px solid rgba(124, 58, 237, 0.3);">
                                <div style="width: 40px; height: 40px; background: var(--accent-gradient); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white;">
                                    <i class="${userStats.user_level?.icon || 'fas fa-user'}"></i>
                                </div>
                                <div>
                                    <div style="font-weight: 600; color: var(--text-primary);">${userStats.user_level?.level || 'New User'}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-secondary);">Current Level</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Profile Form -->
                    <form id="enhancedProfileForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-user-edit"></i>
                                Personal Information
                            </h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                                <div>
                                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Display Name *</label>
                                    <input type="text" name="display_name" id="displayNameInput" value="${currentProfile.display_name || ''}" placeholder="Your full name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);" required>
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Designation</label>
                                    <input type="text" name="designation" id="designationInput" value="${currentProfile.designation || ''}" placeholder="Your job title" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                                </div>
                            </div>
                        </div>
                        
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-building"></i>
                                Company Information
                            </h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                                <div>
                                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Company Name</label>
                                    <input type="text" name="company" id="companyInput" value="${currentProfile.company || ''}" placeholder="Your company name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Email</label>
                                    <input type="email" name="email" id="emailInput" value="${currentProfile.email || ''}" placeholder="your.email@company.com" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Achievements Section -->
                        ${userStats.achievements && userStats.achievements.length > 0 ? `
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-trophy"></i>
                                Your Achievements
                            </h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                                ${userStats.achievements.map(achievement => `
                                    <div style="background: ${achievement.unlocked ? 'rgba(16, 185, 129, 0.1)' : 'var(--bg-secondary)'}; border: 1px solid ${achievement.unlocked ? 'var(--success)' : 'var(--border-color)'}; border-radius: 8px; padding: 1rem; text-align: center; ${achievement.unlocked ? '' : 'opacity: 0.6;'}">
                                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">${achievement.unlocked ? '🏆' : '🔒'}</div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">${achievement.title}</div>
                                        <div style="font-size: 0.8rem; color: var(--text-secondary);">${achievement.description}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                        
                        <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                            <button type="submit" class="btn btn--primary" style="flex: 1; padding: 1rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                                <i class="fas fa-save"></i>
                                Save Profile
                            </button>
                            <button type="button" onclick="clearUserData()" class="btn btn--danger" style="padding: 1rem 1.5rem; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-trash"></i>
                                Clear Data
                            </button>
                        </div>
                    </form>
                </div>
            `,
            onSubmit: async function(formData) {
                try {
                    const response = await fetch('/api/user/profile', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        window.notificationManager.showSuccess('✨ Profile updated successfully!', 3000);
                        
                        // Refresh page data
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                        
                        return true;
                    } else {
                        window.notificationManager.showError(result.error || 'Failed to save profile');
                        return false;
                    }
                } catch (error) {
                    console.error('Error saving profile:', error);
                    window.notificationManager.showError('Failed to save profile');
                    return false;
                }
            }
        });

    } catch (error) {
        console.error('Error opening profile modal:', error);
        window.notificationManager.showError('Failed to load profile data');
    }
};

// ===========================================
// 3. SETTINGS MODAL (Fix for missing implementation)
// ===========================================

window.openSettingsModal = async function() {
    if (!window.modalManager) {
        console.error('Modal manager not initialized');
        return;
    }

    try {
        // Load current preferences
        const response = await fetch('/api/user/preferences');
        const result = await response.json();
        const preferences = result.success ? result.data : {};

        const modal = window.modalManager.createModal({
            title: '⚙️ Settings & Preferences',
            size: 'medium',
            content: `
                <div style="display: flex; flex-direction: column; gap: 2rem;">
                    <form id="settingsForm" style="display: flex; flex-direction: column; gap: 2rem;">
                        <!-- Theme Settings -->
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-palette"></i>
                                Theme & Appearance
                            </h4>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                                <span style="color: var(--text-primary);">Dark Mode</span>
                                <div class="theme-toggle" onclick="window.themeManager.toggleTheme()" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 50px; padding: 4px; cursor: pointer; display: flex; align-items: center; position: relative; width: 60px; height: 32px;">
                                    <div class="theme-toggle-indicator" style="position: absolute; width: 24px; height: 24px; background: var(--accent-gradient); border-radius: 50%; transition: transform 0.3s; left: 4px;">
                                        <i class="fas fa-moon" style="color: white; font-size: 12px; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;"></i>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Notification Settings -->
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-bell"></i>
                                Notifications
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 1rem;">
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Email Notifications</span>
                                    <input type="checkbox" name="emailNotifications" ${preferences.emailNotifications ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Push Notifications</span>
                                    <input type="checkbox" name="pushNotifications" ${preferences.pushNotifications ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                            </div>
                        </div>

                        <!-- Application Settings -->
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-cog"></i>
                                Application Settings
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 1rem;">
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Auto-Search on GSTIN Paste</span>
                                    <input type="checkbox" name="autoSearch" ${preferences.autoSearch !== false ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Save Search History</span>
                                    <input type="checkbox" name="saveHistory" ${preferences.saveHistory !== false ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Enable Analytics</span>
                                    <input type="checkbox" name="analytics" ${preferences.analytics !== false ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Compact Mode</span>
                                    <input type="checkbox" name="compactMode" ${preferences.compactMode ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                            </div>
                        </div>

                        <!-- Debug Settings -->
                        <div style="background: var(--bg-hover); border-radius: 12px; padding: 2rem;">
                            <h4 style="margin-bottom: 1.5rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-bug"></i>
                                Developer Settings
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 1rem;">
                                <label style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;">
                                    <span style="color: var(--text-primary);">Debug Mode</span>
                                    <input type="checkbox" id="debugModeToggle" ${window.debugManager?.enabled ? 'checked' : ''} style="width: 20px; height: 20px;">
                                </label>
                                <button type="button" onclick="exportAllUserData()" style="background: var(--accent-gradient); color: white; border: none; padding: 0.75rem 1rem; border-radius: 8px; cursor: pointer; width: 100%;">
                                    <i class="fas fa-download"></i> Export All Data
                                </button>
                            </div>
                        </div>

                        <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                            <button type="submit" class="btn btn--primary" style="flex: 1; padding: 1rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                                <i class="fas fa-save"></i> Save Settings
                            </button>
                            <button type="button" onclick="resetAllSettings()" class="btn btn--secondary" style="padding: 1rem 1.5rem; background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 8px; font-weight: 600; cursor: pointer;">
                                <i class="fas fa-undo"></i> Reset
                            </button>
                        </div>
                    </form>
                </div>
            `,
            onSubmit: async function(formData) {
                try {
                    // Handle debug mode toggle
                    const debugToggle = document.getElementById('debugModeToggle');
                    if (debugToggle?.checked) {
                        window.debugManager?.enable();
                    } else {
                        window.debugManager?.disable();
                    }

                    const response = await fetch('/api/user/preferences', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        window.notificationManager.showSuccess('⚙️ Settings saved successfully!', 3000);
                        
                        // Apply settings immediately
                        localStorage.setItem(GST_CONFIG.USER_PREFERENCES_KEY, JSON.stringify(formData));
                        
                        return true;
                    } else {
                        window.notificationManager.showError(result.error || 'Failed to save settings');
                        return false;
                    }
                } catch (error) {
                    console.error('Error saving settings:', error);
                    window.notificationManager.showError('Failed to save settings');
                    return false;
                }
            }
        });

    } catch (error) {
        console.error('Error opening settings modal:', error);
        window.notificationManager.showError('Failed to load settings');
    }
};

// ===========================================
// 4. UTILITY FUNCTIONS (Fix missing implementations)
// ===========================================

window.clearUserData = async function() {
    if (!confirm('⚠️ Are you sure you want to clear all your search history? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/user/data', {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.notificationManager.showSuccess(`🗑️ Cleared ${result.deleted_count || 0} search records`, 3000);
            
            // Close modal and refresh page
            window.modalManager.closeAllModals();
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            window.notificationManager.showError('Failed to clear data');
        }
    } catch (error) {
        console.error('Error clearing data:', error);
        window.notificationManager.showError('Failed to clear data');
    }
};

window.exportAllUserData = function() {
    window.location.href = '/export/history';
    window.notificationManager.showInfo('📊 Preparing data export...', 3000);
};

window.resetAllSettings = async function() {
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
        const response = await fetch('/api/user/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(defaultSettings)
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.notificationManager.showSuccess('⚙️ Settings reset to defaults!', 3000);
            window.modalManager.closeAllModals();
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            window.notificationManager.showError('Failed to reset settings');
        }
    } catch (error) {
        console.error('Error resetting settings:', error);
        window.notificationManager.showError('Failed to reset settings');
    }
};

// ===========================================
// 5. ENHANCED SEARCH FUNCTIONALITY
// ===========================================

window.enhanceSearchInputs = function() {
    const searchInputs = document.querySelectorAll('input[name="gstin"], #gstin, #gstinEnhanced');
    
    searchInputs.forEach(input => {
        // Add autocomplete functionality
        input.addEventListener('input', async function(e) {
            const query = e.target.value.trim();
            
            if (query.length >= 2) {
                try {
                    const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`);
                    const result = await response.json();
                    
                    if (result.success && result.suggestions.length > 0) {
                        showSearchSuggestions(e.target, result.suggestions);
                    }
                } catch (error) {
                    console.error('Error fetching suggestions:', error);
                }
            }
        });

        // Auto-search on valid GSTIN paste
        input.addEventListener('paste', function(e) {
            setTimeout(() => {
                const value = e.target.value.trim().toUpperCase();
                const preferences = JSON.parse(localStorage.getItem(GST_CONFIG.USER_PREFERENCES_KEY) || '{}');
                
                if (value.length === 15 && isValidGSTIN(value) && preferences.autoSearch !== false) {
                    window.notificationManager.showInfo('🔍 Auto-searching pasted GSTIN...', 2000);
                    
                    setTimeout(() => {
                        const form = e.target.closest('form');
                        if (form) {
                            form.submit();
                        }
                    }, 500);
                }
            }, 100);
        });
    });
};

function showSearchSuggestions(input, suggestions) {
    // Remove existing suggestions
    const existingSuggestions = document.querySelector('.search-suggestions');
    if (existingSuggestions) {
        existingSuggestions.remove();
    }

    const suggestionsEl = document.createElement('div');
    suggestionsEl.className = 'search-suggestions';
    suggestionsEl.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: var(--card-shadow);
        max-height: 300px;
        overflow-y: auto;
        z-index: 1000;
        margin-top: 4px;
    `;

    suggestionsEl.innerHTML = suggestions.map((suggestion, index) => `
        <div class="suggestion-item" data-gstin="${suggestion.gstin}" style="
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 1rem;
        " onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='transparent'">
            <div style="width: 40px; height: 40px; background: var(--accent-gradient); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white;">
                <i class="${suggestion.icon || 'fas fa-building'}"></i>
            </div>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">${suggestion.company}</div>
                <div style="font-size: 0.875rem; color: var(--text-secondary); font-family: monospace;">${suggestion.gstin}</div>
                ${suggestion.compliance_score ? `<div style="font-size: 0.75rem; color: var(--accent-primary);">Score: ${Math.round(suggestion.compliance_score)}%</div>` : ''}
            </div>
        </div>
    `).join('');

    // Position and show
    const container = input.parentElement;
    container.style.position = 'relative';
    container.appendChild(suggestionsEl);

    // Add click handlers
    suggestionsEl.querySelectorAll('.suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
            input.value = item.dataset.gstin;
            suggestionsEl.remove();
            input.focus();
            input.dispatchEvent(new Event('input'));
        });
    });

    // Hide on outside click
    const hideHandler = (e) => {
        if (!container.contains(e.target)) {
            suggestionsEl.remove();
            document.removeEventListener('click', hideHandler);
        }
    };
    
    setTimeout(() => {
        document.addEventListener('click', hideHandler);
    }, 100);
}

function isValidGSTIN(gstin) {
    return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
}

// ===========================================
// 6. INITIALIZATION AND EVENT HANDLERS
// ===========================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize enhanced search functionality
    window.enhanceSearchInputs();
    
    // Initialize tooltips enhancement
    initializeTooltips();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Initialize performance monitoring
    if (window.debugManager?.enabled) {
        initializePerformanceMonitoring();
    }
    
    console.log('🎯 Frontend integration fixes loaded successfully');
});

function initializeTooltips() {
    // Enhanced tooltip functionality
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'enhanced-tooltip';
            tooltip.textContent = e.target.getAttribute('data-tooltip');
            tooltip.style.cssText = `
                position: absolute;
                background: var(--bg-card);
                color: var(--text-primary);
                padding: 0.75rem 1rem;
                border-radius: 8px;
                font-size: 0.875rem;
                box-shadow: var(--card-shadow);
                border: 1px solid var(--border-color);
                z-index: 10000;
                pointer-events: none;
                max-width: 250px;
                word-wrap: break-word;
                animation: fadeIn 0.2s ease;
            `;
            
            document.body.appendChild(tooltip);
            
            const rect = e.target.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();
            
            tooltip.style.left = Math.min(
                rect.left + (rect.width / 2) - (tooltipRect.width / 2),
                window.innerWidth - tooltipRect.width - 10
            ) + 'px';
            
            tooltip.style.top = (rect.top - tooltipRect.height - 10) + 'px';
            
            e.target._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function(e) {
            if (e.target._tooltip) {
                e.target._tooltip.remove();
                delete e.target._tooltip;
            }
        });
    });
}

function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Only handle shortcuts when not in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('#gstin, #gstinEnhanced, input[name="gstin"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
                window.notificationManager.showInfo('🔍 Search focused (Ctrl+K)', 1500);
            }
        }
        
        // Ctrl/Cmd + P for profile
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            window.openEnhancedProfileModal();
        }
        
        // Ctrl/Cmd + , for settings
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            window.openSettingsModal();
        }
    });
}

function initializePerformanceMonitoring() {
    // Basic performance monitoring
    let pageLoadTime = performance.now();
    
    window.addEventListener('load', () => {
        pageLoadTime = performance.now();
        console.log(`📊 Page loaded in ${Math.round(pageLoadTime)}ms`);
    });
    
    // Monitor API calls
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        const startTime = performance.now();
        try {
            const response = await originalFetch(...args);
            const endTime = performance.now();
            console.log(`🌐 API call to ${args[0]} took ${Math.round(endTime - startTime)}ms`);
            return response;
        } catch (error) {
            console.error(`❌ API call to ${args[0]} failed:`, error);
            throw error;
        }
    };
}

// Export functions for global access
window.GST_INTEGRATION = {
    openProfile: window.openEnhancedProfileModal,
    openSettings: window.openSettingsModal,
    clearData: window.clearUserData,
    exportData: window.exportAllUserData,
    resetSettings: window.resetAllSettings
};