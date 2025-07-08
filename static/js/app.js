// GST Intelligence Platform - Enhanced Common Scripts
// Complete JavaScript Framework with Glow Effects and Working Interactions

console.log('🚀 GST Platform Enhanced Scripts Loading...');

// Global configuration
const GST_CONFIG = {
    TOOLTIP_DELAY: 300,
    TOOLTIP_HIDE_DELAY: 100,
    ANIMATION_DURATION: 300,
    THEME_STORAGE_KEY: 'gst_theme',
    USER_PREFERENCES_KEY: 'gst_user_preferences',
    DEBUG: false
};

// ===========================================
// 1. ENHANCED NOTIFICATION SYSTEM
// ===========================================

class NotificationManager {
    constructor() {
        this.notifications = [];
        this.container = null;
        this.init();
    }

    init() {
        this.createContainer();
        console.log('✅ Enhanced notification system initialized');
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'notification-container';
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
    }

    showToast(message, type = 'info', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = 'gst-toast';
        toast.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1rem 1.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1), 0 8px 32px rgba(124, 58, 237, 0.3);
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
            border-left: 4px solid var(--accent-primary);
        `;
        
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
        
        // Add glowing effect
        const glowAnimation = document.createElement('style');
        glowAnimation.textContent = `
            @keyframes toastGlow {
                0%, 100% { box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1), 0 8px 32px rgba(124, 58, 237, 0.3); }
                50% { box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2), 0 8px 32px rgba(124, 58, 237, 0.6); }
            }
            .gst-toast { animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1), toastGlow 2s ease-in-out infinite; }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        if (!document.getElementById('toastStyles')) {
            glowAnimation.id = 'toastStyles';
            document.head.appendChild(glowAnimation);
        }
        
        toast.innerHTML = `
            <div style="width: 40px; height: 40px; background: ${colors[type] || colors.info}; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; flex-shrink: 0;">
                <i class="${icons[type] || icons.info}"></i>
            </div>
            <span style="flex: 1; font-weight: 500;">${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; border-radius: 4px; transition: all 0.2s;">
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
        
        console.log(`✅ Toast notification shown: ${message} (${type})`);
        return toast;
    }

    showSuccess(message, duration = 4000) {
        return this.showToast(message, 'success', duration);
    }

    showError(message, duration = 6000) {
        return this.showToast(message, 'error', duration);
    }

    showWarning(message, duration = 5000) {
        return this.showToast(message, 'warning', duration);
    }

    showInfo(message, duration = 4000) {
        return this.showToast(message, 'info', duration);
    }
}

// ===========================================
// 2. ENHANCED MODAL SYSTEM
// ===========================================

class ModalManager {
    constructor() {
        this.activeModals = [];
        this.init();
    }

    init() {
        this.injectModalStyles();
        console.log('✅ Enhanced modal system initialized');
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
            
            @keyframes modalGlow {
                0%, 100% { box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 8px 32px rgba(124, 58, 237, 0.3); }
                50% { box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4), 0 12px 48px rgba(124, 58, 237, 0.6); }
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
            background: rgba(0, 0, 0, 0.6);
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
            animation: modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1), modalGlow 3s ease-in-out infinite;
            border: 1px solid rgba(124, 58, 237, 0.3);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 8px 32px rgba(124, 58, 237, 0.3);
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
        
        // Enhanced close button with glow effect
        const closeBtn = modalContent.querySelector('.modal-close-btn');
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.background = 'var(--error)';
            closeBtn.style.color = 'white';
            closeBtn.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.5)';
        });
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.background = 'var(--bg-hover)';
            closeBtn.style.color = 'var(--text-muted)';
            closeBtn.style.boxShadow = 'none';
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
        
        console.log(`✅ Enhanced modal created: ${options.title}`);
        return modal;
    }

    closeModal(modal) {
        const content = modal.querySelector('.modal-content');
        modal.style.animation = 'modalFadeIn 0.3s ease reverse';
        content.style.animation = 'modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) reverse';
        
        setTimeout(() => {
            modal.remove();
            this.activeModals = this.activeModals.filter(m => m !== modal);
        }, 300);
        
        console.log('✅ Enhanced modal closed');
    }

    closeAllModals() {
        this.activeModals.forEach(modal => this.closeModal(modal));
    }
}

// ===========================================
// 3. UTILITY FUNCTIONS
// ===========================================

function addGlowEffect(element, color = 'rgba(124, 58, 237, 0.5)') {
    element.style.boxShadow = `0 0 20px ${color}`;
    element.style.transition = 'box-shadow 0.3s ease';
}

function removeGlowEffect(element) {
    element.style.boxShadow = '';
}

// ===========================================
// 4. GLOBAL MODAL FUNCTIONS
// ===========================================

window.openEnhancedProfileModal = function() {
    modalManager.createModal({
        title: '✨ Enhanced Profile',
        content: `
            <form id="enhancedProfileForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary);">✨ Your Activity</h4>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);" id="modalTotalSearches">-</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">Total Searches</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);" id="modalAvgCompliance">-</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">Avg Compliance</div>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Display Name</label>
                    <input type="text" name="displayName" class="form-input" placeholder="Enter your name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                
                <div class="form-group">
                    <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Company</label>
                    <input type="text" name="company" class="form-input" placeholder="Company name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                
                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <button type="submit" class="btn btn-primary" style="flex: 1; padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        💾 Save Profile
                    </button>
                    <button type="button" onclick="clearUserData()" class="btn btn-danger" style="padding: 0.75rem 1rem; background: var(--error); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        🗑️ Clear Data
                    </button>
                </div>
            </form>
        `,
        onSubmit: async function(formData) {
            notificationManager.showSuccess('✨ Profile updated successfully!', 3000);
            return true;
        }
    });
    
    // Load user stats in modal
    loadUserStatsForModal();
};

window.openSettingsModal = function() {
    const currentSettings = JSON.parse(localStorage.getItem(GST_CONFIG.USER_PREFERENCES_KEY) || '{}');
    
    modalManager.createModal({
        title: '⚙️ Settings & Preferences',
        content: `
            <form id="settingsForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div style="margin-bottom: 1rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary); font-size: 1.1rem;">🎨 General Preferences</h4>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="emailNotifications" ${currentSettings.emailNotifications ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">📧 Email Notifications</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Receive email updates about your searches</div>
                            </div>
                        </label>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="autoSearch" ${currentSettings.autoSearch !== false ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">🚀 Auto-search on GSTIN paste</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Automatically search when you paste a GSTIN</div>
                            </div>
                        </label>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.75rem; cursor: pointer; padding: 0.75rem; background: var(--bg-hover); border-radius: 8px; transition: all 0.2s;">
                            <input type="checkbox" name="glowEffects" ${currentSettings.glowEffects !== false ? 'checked' : ''} style="width: 18px; height: 18px;">
                            <div>
                                <div style="font-weight: 500; color: var(--text-primary);">✨ Glow Effects</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">Enable enhanced visual effects and animations</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary" style="padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    💾 Save Settings
                </button>
            </form>
        `,
        onSubmit: async function(formData) {
            localStorage.setItem(GST_CONFIG.USER_PREFERENCES_KEY, JSON.stringify(formData));
            localStorage.setItem('autoSearch', formData.autoSearch ? 'true' : 'false');
            notificationManager.showSuccess('⚙️ Settings saved successfully!', 3000);
            return true;
        }
    });
};

async function loadUserStatsForModal() {
    try {
        const response = await fetch('/api/user/stats');
        const result = await response.json();
        
        if (result.success) {
            const totalSearchesEl = document.getElementById('modalTotalSearches');
            const avgComplianceEl = document.getElementById('modalAvgCompliance');
            
            if (totalSearchesEl) {
                totalSearchesEl.textContent = result.data.total_searches;
                addGlowEffect(totalSearchesEl, 'rgba(124, 58, 237, 0.3)');
            }
            
            if (avgComplianceEl) {
                avgComplianceEl.textContent = Math.round(result.data.avg_compliance) + '%';
                addGlowEffect(avgComplianceEl, 'rgba(16, 185, 129, 0.3)');
            }
        }
    } catch (error) {
        console.error('Error loading user stats for modal:', error);
    }
}

window.clearUserData = function() {
    if (confirm('🗑️ Are you sure you want to clear all your search history? This action cannot be undone.')) {
        localStorage.removeItem('searchHistory');
        notificationManager.showSuccess('✨ Search history cleared', 3000);
        modalManager.closeAllModals();
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    }
};

// ===========================================
// 5. ENHANCED SEARCH FUNCTIONALITY
// ===========================================

function enhanceSearchFunctionality() {
    const searchForms = document.querySelectorAll('form[action="/search"], form[action*="search"]');
    
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const gstinInput = form.querySelector('input[name="gstin"]');
            if (gstinInput) {
                const gstin = gstinInput.value.trim().toUpperCase();
                
                if (!isValidGSTIN(gstin)) {
                    e.preventDefault();
                    notificationManager.showError('❌ Please enter a valid 15-digit GSTIN format', 4000);
                    addGlowEffect(gstinInput, 'rgba(239, 68, 68, 0.5)');
                    setTimeout(() => removeGlowEffect(gstinInput), 3000);
                    return false;
                }
                
                // Add success glow effect
                addGlowEffect(gstinInput, 'rgba(16, 185, 129, 0.5)');
                notificationManager.showInfo('🔍 Searching for company data...', 3000);
            }
        });
    });
    
    console.log('✅ Enhanced search functionality initialized');
}

function isValidGSTIN(gstin) {
    return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
}

// ===========================================
// 6. ENHANCED COMPANY ROW INTERACTIONS
// ===========================================

function enhanceCompanyRows() {
    const companyRows = document.querySelectorAll('.company-row, tr[data-gstin]');
    
    companyRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on a button or link
            if (e.target.closest('button, a')) return;
            
            const gstin = this.getAttribute('data-gstin') || 
                         this.querySelector('.gstin-code')?.textContent ||
                         this.querySelector('code')?.textContent;
            
            if (gstin) {
                // Add click effect
                addGlowEffect(this, 'rgba(124, 58, 237, 0.3)');
                
                // Create and submit form
                const form = document.createElement('form');
                form.method = 'GET';
                form.action = '/search';
                form.style.display = 'none';
                
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'gstin';
                input.value = gstin.trim();
                
                form.appendChild(input);
                document.body.appendChild(form);
                
                notificationManager.showInfo(`🔍 Searching for ${gstin}...`, 2000);
                
                setTimeout(() => {
                    form.submit();
                }, 300);
            }
        });
        
        // Add hover effects
        row.addEventListener('mouseenter', function() {
            if (!this.style.boxShadow) {
                addGlowEffect(this, 'rgba(124, 58, 237, 0.1)');
            }
        });
        
        row.addEventListener('mouseleave', function() {
            if (this.style.boxShadow.includes('0.1')) {
                removeGlowEffect(this);
            }
        });
    });
    
    console.log(`✅ Enhanced ${companyRows.length} company rows with click functionality`);
}

// ===========================================
// 7. ENHANCED VIEW BUTTONS
// ===========================================

function enhanceViewButtons() {
    const viewButtons = document.querySelectorAll('.view-btn, button[type="submit"]:contains("View")');
    
    viewButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            addGlowEffect(this, 'rgba(124, 58, 237, 0.5)');
        });
        
        button.addEventListener('mouseleave', function() {
            removeGlowEffect(this);
        });
        
        button.addEventListener('click', function() {
            addGlowEffect(this, 'rgba(16, 185, 129, 0.5)');
            notificationManager.showInfo('🔍 Loading company details...', 2000);
        });
    });
    
    console.log(`✅ Enhanced ${viewButtons.length} view buttons with glow effects`);
}

// ===========================================
// 8. ENHANCED FORM INPUTS
// ===========================================

function enhanceFormInputs() {
    const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin');
    
    gstinInputs.forEach(input => {
        // Add glowing effect on focus
        input.addEventListener('focus', () => {
            input.style.boxShadow = '0 0 20px rgba(124, 58, 237, 0.3), 0 0 0 3px rgba(124, 58, 237, 0.1)';
            input.style.borderColor = 'var(--accent-primary)';
        });
        
        input.addEventListener('blur', () => {
            if (!input.classList.contains('is-valid') && !input.classList.contains('is-invalid')) {
                input.style.boxShadow = '';
                input.style.borderColor = 'var(--border-color)';
            }
        });
        
        input.addEventListener('input', (e) => {
            const value = e.target.value.toUpperCase();
            e.target.value = value;
            
            const isValid = isValidGSTIN(value);
            
            if (value.length === 15) {
                if (isValid) {
                    addGlowEffect(e.target, 'rgba(16, 185, 129, 0.3)');
                    e.target.style.borderColor = '#10b981';
                } else {
                    addGlowEffect(e.target, 'rgba(239, 68, 68, 0.3)');
                    e.target.style.borderColor = '#ef4444';
                }
            } else {
                removeGlowEffect(e.target);
                e.target.style.borderColor = 'var(--border-color)';
            }
        });
        
        // Enhanced paste handling with glow effect
        input.addEventListener('paste', (e) => {
            setTimeout(() => {
                const value = e.target.value.trim();
                if (value.length === 15 && isValidGSTIN(value)) {
                    // Add success glow
                    addGlowEffect(e.target, 'rgba(16, 185, 129, 0.5)');
                    notificationManager.showSuccess('Valid GSTIN pasted!', 2000);
                    
                    const autoSearch = localStorage.getItem('autoSearch');
                    if (autoSearch === 'true' || autoSearch === null) {
                        const form = e.target.closest('form');
                        if (form) {
                            notificationManager.showInfo('Auto-searching pasted GSTIN...', 2000);
                            setTimeout(() => form.submit(), 500);
                        }
                    }
                }
            }, 100);
        });
    });
    
    console.log(`✅ Enhanced ${gstinInputs.length} GSTIN inputs with validation and glow effects`);
}

// ===========================================
// 9. GLOBAL EXPORT FUNCTIONS
// ===========================================

window.exportToExcel = function() {
    window.location.href = '/export/history';
    if (window.notificationManager) {
        window.notificationManager.showToast('📊 Exporting data...', 'info');
    }
};

// ===========================================
// 10. INITIALIZATION
// ===========================================

// Global instances
let modalManager;
let notificationManager;

// Initialize all systems when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize managers
    modalManager = new ModalManager();
    notificationManager = new NotificationManager();
    
    // Initialize enhancements
    enhanceSearchFunctionality();
    enhanceCompanyRows();
    enhanceViewButtons();
    enhanceFormInputs();
    
    // Add enhanced styles
    const enhancedStyles = document.createElement('style');
    enhancedStyles.textContent = `
        .form-input:focus {
            transform: translateY(-1px);
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }
        
        .company-row:hover {
            transform: translateX(5px);
            transition: all 0.3s ease;
        }
        
        .view-btn:hover {
            box-shadow: 0 0 20px rgba(124, 58, 237, 0.5);
        }
        
        .score-badge:hover {
            transform: scale(1.1);
            box-shadow: 0 0 15px rgba(124, 58, 237, 0.3);
        }
        
        /* Enhanced glow effects for buttons and interactive elements */
        .export-btn:hover {
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.5);
        }
        
        .stat-card:hover {
            box-shadow: var(--hover-shadow), 0 0 30px rgba(124, 58, 237, 0.3);
        }
        
        /* Smooth transitions for all interactive elements */
        * {
            transition: box-shadow 0.3s ease, transform 0.3s ease, border-color 0.3s ease;
        }
        
        /* Custom scrollbar with glow */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--accent-primary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-secondary);
            box-shadow: 0 0 10px rgba(124, 58, 237, 0.5);
        }
    `;
    
    if (!document.getElementById('enhancedStyles')) {
        enhancedStyles.id = 'enhancedStyles';
        document.head.appendChild(enhancedStyles);
    }
    
    console.log('✅ GST Intelligence Platform - All enhanced systems initialized');
    
    // Show enhanced welcome notification for new users
    if (!localStorage.getItem('enhancedWelcomeShown')) {
        setTimeout(() => {
            notificationManager.showInfo('✨ Welcome to GST Intelligence Platform! Enhanced with glow effects and smooth interactions.', 6000);
            localStorage.setItem('enhancedWelcomeShown', 'true');
        }, 1000);
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden - cleanup if needed
        console.log('Page hidden - cleaning up effects');
    }
});

// Handle online/offline status with enhanced notifications
window.addEventListener('online', () => {
    if (typeof notificationManager !== 'undefined') {
        notificationManager.showSuccess('🌐 Connection restored - All features available', 3000);
    }
});

window.addEventListener('offline', () => {
    if (typeof notificationManager !== 'undefined') {
        notificationManager.showWarning('📡 Connection lost - Some features may not work', 5000);
    }
});

// Enhanced keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('#gstin, input[name="gstin"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
            addGlowEffect(searchInput, 'rgba(124, 58, 237, 0.5)');
            if (typeof notificationManager !== 'undefined') {
                notificationManager.showInfo('🔍 Search focused - Ready for GSTIN input', 2000);
            }
        }
    }
    
    // Escape to close modals and dropdowns
    if (e.key === 'Escape') {
        if (typeof modalManager !== 'undefined') {
            modalManager.closeAllModals();
        }
        
        const userDropdown = document.getElementById('userDropdownMenu');
        if (userDropdown && userDropdown.classList.contains('active')) {
            if (typeof closeUserDropdown === 'function') {
                closeUserDropdown();
            }
        }
    }
});

// Auto-dismiss messages with enhanced effects
function autoDismissMessages() {
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach((message, index) => {
        // Add glow effect to messages
        addGlowEffect(message, 'rgba(124, 58, 237, 0.2)');
        
        setTimeout(() => {
            if (message.parentElement) {
                message.style.animation = 'fadeOut 0.5s ease';
                setTimeout(() => {
                    message.remove();
                }, 500);
            }
        }, 5000 + (index * 1000));
    });
}

// Call auto-dismiss on load
setTimeout(autoDismissMessages, 1000);

// Export for debugging and external access
window.GST_ENHANCED = {
    modalManager,
    notificationManager,
    config: GST_CONFIG,
    utils: {
        addGlowEffect,
        removeGlowEffect,
        isValidGSTIN
    }
};

console.log('🎉 GST Intelligence Platform Enhanced Scripts Loaded Successfully!');

// Additional helper functions for better UX
function animateNumber(element, start, end, duration, suffix = '') {
    const startTime = performance.now();
    const difference = end - start;
    
    function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (difference * progress));
        
        element.textContent = current + suffix;
        
        // Add glow effect during animation
        if (progress < 1) {
            addGlowEffect(element, 'rgba(124, 58, 237, 0.3)');
            requestAnimationFrame(step);
        } else {
            setTimeout(() => removeGlowEffect(element), 1000);
        }
    }
    
    requestAnimationFrame(step);
}

// Enhanced table row highlighting
function enhanceTableRows() {
    const tableRows = document.querySelectorAll('table tbody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.background = 'var(--bg-hover)';
            addGlowEffect(this, 'rgba(124, 58, 237, 0.1)');
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.background = '';
            removeGlowEffect(this);
        });
    });
}

// Call table enhancement after DOM load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(enhanceTableRows, 500);
});

// Enhanced tooltip system
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            addGlowEffect(this, 'rgba(124, 58, 237, 0.2)');
        });
        
        element.addEventListener('mouseleave', function() {
            removeGlowEffect(this);
        });
    });
}

// Initialize tooltips after DOM load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initTooltips, 500);
});

// Enhanced error handling with visual feedback
window.addEventListener('error', function(e) {
    console.error('Global error:', e);
    if (typeof notificationManager !== 'undefined') {
        notificationManager.showError('⚠️ An unexpected error occurred. Please try again.', 5000);
    }
});

// Enhanced form submission feedback
document.addEventListener('submit', function(e) {
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
    
    if (submitBtn) {
        addGlowEffect(submitBtn, 'rgba(124, 58, 237, 0.5)');
        submitBtn.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            submitBtn.style.transform = '';
        }, 150);
    }
});

// Service worker registration with enhanced feedback
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('✅ SW registered:', registration);
                if (typeof notificationManager !== 'undefined') {
                    notificationManager.showSuccess('🔧 App enhanced for offline use!', 3000);
                }
            })
            .catch(registrationError => {
                console.log('❌ SW registration failed:', registrationError);
            });
    });
}