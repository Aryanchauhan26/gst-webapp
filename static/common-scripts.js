// GST Intelligence Platform - Enhanced Common Scripts
// Includes robust tooltip system, user dropdown, and smooth animations

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Enhanced Tooltip System - Prevents Clipping
    initializeEnhancedTooltipSystem();
    
    // 2. User Profile Dropdown System
    initializeUserDropdown();
    
    // 3. Smooth Animations with RequestAnimationFrame
    initializeSmoothAnimations();
    
    // 4. Auto-dismiss messages after 5 seconds
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s, transform 0.5s';
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });
    
    // 5. GSTIN Input Formatter and Validator
    const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin');
    gstinInputs.forEach(function(input) {
        // Auto-uppercase
        input.addEventListener('input', function(e) {
            e.target.value = e.target.value.toUpperCase();
            validateGSTIN(e.target);
        });
        
        // Paste handler
        input.addEventListener('paste', function(e) {
            setTimeout(function() {
                e.target.value = e.target.value.toUpperCase().replace(/\s/g, '');
                validateGSTIN(e.target);
            }, 10);
        });
    });
    
    // 6. Form Submit Handler with Loading State
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // Prevent double submission
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && submitBtn.disabled) {
                e.preventDefault();
                return;
            }
            
            // Show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-small"></span> Processing...';
                
                // Re-enable after 30 seconds (failsafe)
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 30000);
            }
            
            // Show loading overlay if exists
            const loadingOverlay = document.getElementById('loading');
            if (loadingOverlay) {
                loadingOverlay.style.display = 'block';
            }
        });
    });
    
    // 7. Enhanced Table Row Click Handler
    const tableRows = document.querySelectorAll('.history-table tbody tr');
    tableRows.forEach(function(row) {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(e) {
            // Don't navigate if clicking the view button or any form element
            if (e.target.tagName === 'BUTTON' || 
                e.target.closest('button') || 
                e.target.closest('form') ||
                e.target.closest('.view-btn')) {
                return;
            }
            
            const gstin = row.dataset.gstin;
            if (gstin) {
                window.location.href = `/search?gstin=${gstin}`;
            }
        });
    });
    
    // 8. Mobile Menu Toggle
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const navItems = document.querySelector('.nav-items');
    if (menuToggle && navItems) {
        menuToggle.addEventListener('click', function() {
            navItems.classList.toggle('show');
            this.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.header')) {
                navItems.classList.remove('show');
                menuToggle.classList.remove('active');
            }
        });
    }
    
    // 9. Copy to Clipboard
    window.copyToClipboard = function(text, button) {
        navigator.clipboard.writeText(text).then(function() {
            const originalText = button.innerHTML;
            button.innerHTML = 'Copied!';
            button.style.backgroundColor = '#28a745';
            
            setTimeout(function() {
                button.innerHTML = originalText;
                button.style.backgroundColor = '';
            }, 2000);
        }).catch(function(err) {
            console.error('Failed to copy:', err);
            alert('Failed to copy to clipboard');
        });
    };
    
    // 10. Share Functionality
    window.shareResults = function(title, text, url) {
        if (navigator.share) {
            navigator.share({
                title: title || 'GST Compliance Report',
                text: text || 'Check out this GST compliance report',
                url: url || window.location.href
            }).catch(function(error) {
                if (error.name !== 'AbortError') {
                    console.error('Error sharing:', error);
                }
            });
        } else {
            // Fallback - copy URL
            copyToClipboard(url || window.location.href, event.target);
        }
    };
    
    // 11. Export to Excel Handler
    window.exportToExcel = function() {
        const exportBtn = event.target.closest('button');
        exportBtn.disabled = true;
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = 'Exporting...';
        
        // Navigate to export endpoint
        window.location.href = '/export/history';
        
        // Re-enable button after delay
        setTimeout(function() {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalText;
        }, 3000);
    };
    
    // 12. Prevent Form Resubmission on Page Refresh
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }
    
    // 13. Handle Session Timeout Warning
    let sessionWarningShown = false;
    const sessionTimeout = 115 * 60 * 1000; // 115 minutes (5 min before 2 hour timeout)
    
    setTimeout(function() {
        if (!sessionWarningShown) {
            sessionWarningShown = true;
            if (confirm('Your session will expire soon. Would you like to stay logged in?')) {
                // Make a request to refresh session
                fetch('/refresh-session', { method: 'POST' })
                    .then(response => {
                        if (response.ok) {
                            sessionWarningShown = false;
                            // Reset timer
                            setTimeout(arguments.callee, sessionTimeout);
                        }
                    });
            }
        }
    }, sessionTimeout);

    // 14. Set dynamic greeting
    setDynamicGreeting();
    
    // 15. Create particle background
    if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
        createParticles();
    }
    
    // 16. Enhance score displays
    enhanceScoreDisplay();
    
    // 17. Enhance search input
    enhanceSearchInput();
    
    // 18. Animate table rows
    animateTableRows();
    
    // 19. Animate score values on results page
    const scoreValues = document.querySelectorAll('.score-value');
    scoreValues.forEach(element => {
        const value = parseInt(element.textContent);
        if (!isNaN(value)) {
            element.textContent = '0%';
            setTimeout(() => {
                animateValue(element, 0, value, 1500);
            }, 500);
            
            // Show confetti for high scores
            if (value >= 90) {
                setTimeout(showConfetti, 1500);
            }
        }
    });
    
    // 20. Add hover effects to buttons
    const buttons = document.querySelectorAll('button, .btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            if (!button.disabled) {
                requestAnimationFrame(() => {
                    button.style.transform = 'translateY(-2px)';
                });
            }
        });
        
        button.addEventListener('mouseleave', () => {
            requestAnimationFrame(() => {
                button.style.transform = '';
            });
        });
    });
    
    // FORCE USER DROPDOWN INITIALIZATION WITH RETRY
    setTimeout(function() {
        console.log('🚀 Force initializing user dropdown...');
        initializeUserDropdown();
        
        // Retry if no dropdowns were created
        setTimeout(function() {
            const dropdowns = document.querySelectorAll('.user-dropdown-wrapper');
            if (dropdowns.length === 0) {
                console.log('⚠️ No dropdowns found, retrying...');
                initializeUserDropdown();
            }
        }, 1000);
    }, 500);
});

// Enhanced Tooltip System - Renders at body level to prevent clipping
function initializeEnhancedTooltipSystem() {
    // Remove any existing tooltip containers
    const existingTooltips = document.querySelectorAll('.enhanced-tooltip-container');
    existingTooltips.forEach(el => el.remove());
    
    // Create tooltip container at body level
    const tooltipContainer = document.createElement('div');
    tooltipContainer.className = 'enhanced-tooltip-container';
    tooltipContainer.style.cssText = `
        position: fixed;
        pointer-events: none;
        z-index: 999999;
        opacity: 0;
        transition: opacity 0.2s ease;
    `;
    
    const tooltipContent = document.createElement('div');
    tooltipContent.className = 'enhanced-tooltip-content';
    tooltipContent.style.cssText = `
        background: #1a1a1a;
        color: #fff;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 13px;
        line-height: 1.4;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 300px;
        word-wrap: break-word;
        white-space: pre-wrap;
    `;
    
    const tooltipArrow = document.createElement('div');
    tooltipArrow.className = 'enhanced-tooltip-arrow';
    tooltipArrow.style.cssText = `
        position: absolute;
        width: 0;
        height: 0;
        border-style: solid;
    `;
    
    tooltipContainer.appendChild(tooltipContent);
    tooltipContainer.appendChild(tooltipArrow);
    document.body.appendChild(tooltipContainer);
    
    // Light theme support
    if (document.body.classList.contains('light-theme')) {
        tooltipContent.style.background = '#333';
        tooltipContent.style.color = '#fff';
    }
    
    // Track current tooltip target
    let currentTarget = null;
    let showTimeout = null;
    let hideTimeout = null;
    
    // Position tooltip with smart positioning
    function positionTooltip(target) {
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltipContent.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const scrollY = window.scrollY;
        const scrollX = window.scrollX;
        
        // Default position: above the element
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 12;
        let arrowPosition = 'bottom';
        
        // Horizontal boundary check
        if (left < 10) {
            left = 10;
        } else if (left + tooltipRect.width > viewportWidth - 10) {
            left = viewportWidth - tooltipRect.width - 10;
        }
        
        // Vertical boundary check - show below if not enough space above
        if (top < 10) {
            top = rect.bottom + 12;
            arrowPosition = 'top';
        }
        
        // Update positions
        tooltipContainer.style.left = left + 'px';
        tooltipContainer.style.top = top + 'px';
        
        // Update arrow
        const arrowLeft = rect.left + (rect.width / 2) - left;
        tooltipArrow.style.left = arrowLeft + 'px';
        
        if (arrowPosition === 'bottom') {
            tooltipArrow.style.bottom = '-6px';
            tooltipArrow.style.top = 'auto';
            tooltipArrow.style.borderWidth = '6px 6px 0 6px';
            tooltipArrow.style.borderColor = '#1a1a1a transparent transparent transparent';
        } else {
            tooltipArrow.style.top = '-6px';
            tooltipArrow.style.bottom = 'auto';
            tooltipArrow.style.borderWidth = '0 6px 6px 6px';
            tooltipArrow.style.borderColor = 'transparent transparent #1a1a1a transparent';
        }
        
        if (document.body.classList.contains('light-theme')) {
            tooltipArrow.style.borderColor = arrowPosition === 'bottom' 
                ? '#333 transparent transparent transparent'
                : 'transparent transparent #333 transparent';
        }
    }
    
    // Show tooltip
    function showTooltip(target) {
        const text = target.getAttribute('data-tooltip');
        if (!text) return;
        
        currentTarget = target;
        tooltipContent.textContent = text;
        
        // Position before showing
        requestAnimationFrame(() => {
            positionTooltip(target);
            tooltipContainer.style.opacity = '1';
        });
    }
    
    // Hide tooltip
    function hideTooltip() {
        currentTarget = null;
        tooltipContainer.style.opacity = '0';
    }
    
    // Add event listeners using event delegation
    document.addEventListener('mouseenter', function(e) {
        const target = e.target.closest('[data-tooltip]');
        if (target) {
            clearTimeout(hideTimeout);
            showTimeout = setTimeout(() => showTooltip(target), 200);
        }
    }, true);
    
    document.addEventListener('mouseleave', function(e) {
        const target = e.target.closest('[data-tooltip]');
        if (target && target === currentTarget) {
            clearTimeout(showTimeout);
            hideTimeout = setTimeout(hideTooltip, 100);
        }
    }, true);
    
    // Update tooltip position on scroll
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        if (currentTarget) {
            clearTimeout(scrollTimeout);
            tooltipContainer.style.opacity = '0';
            scrollTimeout = setTimeout(() => {
                if (currentTarget) {
                    positionTooltip(currentTarget);
                    tooltipContainer.style.opacity = '1';
                }
            }, 100);
        }
    });
    
    // Update tooltip theme when theme changes
    document.addEventListener('themeChanged', function() {
        if (document.body.classList.contains('light-theme')) {
            tooltipContent.style.background = '#333';
            tooltipContent.style.color = '#fff';
        } else {
            tooltipContent.style.background = '#1a1a1a';
            tooltipContent.style.color = '#fff';
        }
    });
}

// User Profile Dropdown System
function initializeUserDropdown() {
    console.log('🔧 Initializing user dropdown system...');
    
    // ENHANCED SELECTOR - More flexible element detection
    const userElements = document.querySelectorAll([
        '.user-profile',
        '.nav-link[data-tooltip*="Logged in user"]',
        '.nav-link.tooltip[data-tooltip*="Logged in user"]',
        '.nav-link.user-profile'
    ].join(', '));
    
    console.log('👤 Found user elements:', userElements.length, userElements);
    
    userElements.forEach(function(userElement, index) {
        console.log(`🔍 Processing user element ${index + 1}:`, userElement);
        
        // Skip if already processed
        if (userElement.classList.contains('dropdown-processed')) {
            console.log('⚠️ Element already processed, skipping...');
            return;
        }
        
        // Mark as processed
        userElement.classList.add('dropdown-processed');
        
        // Get mobile number
        const mobile = userElement.textContent.trim();
        console.log('📱 Mobile number:', mobile);
        
        // Create dropdown wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'user-dropdown-wrapper';
        
        // Create enhanced button
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
        
        // Add click handler
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = menu.style.display === 'block';
            
            // Hide all other dropdowns
            document.querySelectorAll('.user-dropdown-menu').forEach(m => {
                if (m !== menu) m.style.display = 'none';
            });
            
            menu.style.display = isVisible ? 'none' : 'block';
            
            // Rotate arrow
            const arrow = button.querySelector('.dropdown-arrow');
            if (arrow) {
                arrow.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
            }
        });
        
        console.log('✅ Successfully created user dropdown for:', mobile);
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-dropdown-wrapper')) {
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
            document.querySelectorAll('.dropdown-arrow').forEach(arrow => {
                arrow.style.transform = 'rotate(0deg)';
            });
        }
    });
    
    console.log('✅ User dropdown system initialized');
}

// Modal System for Profile Management
window.openProfileModal = function() {
    // First fetch current profile
    fetch('/api/profile')
        .then(response => response.json())
        .then(profile => {
            createModal({
                title: 'My Profile',
                content: `
                    <form id="profileForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <div class="form-group">
                            <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block;">Mobile Number</label>
                            <input type="text" value="${profile.mobile || ''}" disabled style="background: var(--bg-hover); cursor: not-allowed;">
                        </div>
                        <div class="form-group">
                            <label>Display Name</label>
                            <input type="text" name="displayName" placeholder="Enter your name" value="${profile.display_name || ''}">
                        </div>
                        <div class="form-group">
                            <label>Email (Optional)</label>
                            <input type="email" name="email" placeholder="Enter your email" value="${profile.email || ''}">
                        </div>
                        <div class="form-group">
                            <label>Company Name (Optional)</label>
                            <input type="text" name="company" placeholder="Enter company name" value="${profile.company || ''}">
                        </div>
                        <button type="submit" class="btn btn-primary">Save Profile</button>
                    </form>
                `,
                onSubmit: async function(formData) {
                    try {
                        const response = await fetch('/api/profile', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(formData)
                        });
                        const result = await response.json();
                        if (response.ok) {
                            showToast('Profile updated successfully!', 'success');
                            return true;
                        } else {
                            showToast(result.error || 'Failed to update profile', 'error');
                            return false;
                        }
                    } catch (error) {
                        showToast('Error updating profile', 'error');
                        return false;
                    }
                }
            });
        })
        .catch(error => {
            showToast('Error loading profile', 'error');
        });
};

window.openChangePasswordModal = function() {
    createModal({
        title: 'Change Password',
        content: `
            <form id="passwordForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="form-group">
                    <label>Current Password</label>
                    <input type="password" name="currentPassword" required>
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" name="newPassword" required minlength="6">
                    <div class="password-strength" style="margin-top: 0.5rem;">
                        <div class="password-strength-bar" style="height: 4px; background: var(--bg-hover); border-radius: 2px;">
                            <div id="strengthBar" style="height: 100%; width: 0; background: var(--accent-gradient); transition: width 0.3s;"></div>
                        </div>
                        <div id="strengthText" style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;"></div>
                    </div>
                </div>
                <div class="form-group">
                    <label>Confirm New Password</label>
                    <input type="password" name="confirmPassword" required>
                </div>
                <button type="submit" class="btn btn-primary">Change Password</button>
            </form>
        `,
        onMount: function() {
            // Password strength checker
            const newPasswordInput = document.querySelector('input[name="newPassword"]');
            const strengthBar = document.getElementById('strengthBar');
            const strengthText = document.getElementById('strengthText');
            
            newPasswordInput.addEventListener('input', function() {
                const password = this.value;
                let strength = 0;
                let message = '';
                
                if (password.length >= 6) strength += 25;
                if (password.length >= 8) strength += 25;
                if (/[A-Z]/.test(password)) strength += 25;
                if (/[0-9]/.test(password)) strength += 25;
                
                strengthBar.style.width = strength + '%';
                
                if (strength <= 25) {
                    strengthBar.style.background = 'var(--danger)';
                    message = 'Weak';
                } else if (strength <= 50) {
                    strengthBar.style.background = 'var(--warning)';
                    message = 'Fair';
                } else if (strength <= 75) {
                    strengthBar.style.background = 'var(--info)';
                    message = 'Good';
                } else {
                    strengthBar.style.background = 'var(--success)';
                    message = 'Strong';
                }
                
                strengthText.textContent = password.length > 0 ? message : '';
            });
        },
        onSubmit: async function(formData) {
            if (formData.newPassword !== formData.confirmPassword) {
                showToast('Passwords do not match!', 'error');
                return false;
            }
            
            try {
                const response = await fetch('/api/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const result = await response.json();
                if (response.ok) {
                    showToast('Password changed successfully!', 'success');
                    return true;
                } else {
                    showToast(result.error || 'Failed to change password', 'error');
                    return false;
                }
            } catch (error) {
                showToast('Error changing password', 'error');
                return false;
            }
        }
    });
};

window.openSettingsModal = function() {
    createModal({
        title: 'Settings',
        content: `
            <form id="settingsForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="setting-group">
                    <h3 style="margin-bottom: 1rem;">Preferences</h3>
                    <label class="toggle-setting">
                        <input type="checkbox" name="emailNotifications">
                        <span>Email Notifications</span>
                    </label>
                    <label class="toggle-setting">
                        <input type="checkbox" name="autoSearch" checked>
                        <span>Auto-search on GSTIN paste</span>
                    </label>
                    <label class="toggle-setting">
                        <input type="checkbox" name="animations" checked>
                        <span>Enable animations</span>
                    </label>
                </div>
                <div class="setting-group">
                    <h3 style="margin-bottom: 1rem;">Data & Privacy</h3>
                    <button type="button" class="btn btn-secondary" onclick="downloadUserData()">
                        <i class="fas fa-download"></i> Download My Data
                    </button>
                    <button type="button" class="btn btn-danger" onclick="confirmDeleteAccount()">
                        <i class="fas fa-trash"></i> Delete Account
                    </button>
                </div>
                <button type="submit" class="btn btn-primary">Save Settings</button>
            </form>
        `,
        onSubmit: async function(formData) {
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                if (response.ok) {
                    // Save settings locally
                    localStorage.setItem('userSettings', JSON.stringify(formData));
                    showToast('Settings saved successfully!', 'success');
                    return true;
                }
            } catch (error) {
                showToast('Error saving settings', 'error');
                return false;
            }
        }
    });
};

// Download user data
window.downloadUserData = async function() {
    try {
        const response = await fetch('/api/export-data');
        const data = await response.json();
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gst-intelligence-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Data exported successfully!', 'success');
    } catch (error) {
        showToast('Error exporting data', 'error');
    }
};

// Confirm account deletion
window.confirmDeleteAccount = function() {
    if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
        if (confirm('This will permanently delete all your data. Type "DELETE" to confirm.')) {
            const confirmation = prompt('Type DELETE to confirm account deletion:');
            if (confirmation === 'DELETE') {
                // Handle account deletion
                showToast('Account deletion request submitted', 'info');
            }
        }
    }
};

// Modal Creator Function
function createModal(options) {
    // Remove existing modals
    const existingModals = document.querySelectorAll('.modal-overlay');
    existingModals.forEach(modal => modal.remove());
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s;
    `;
    
    // Create modal content
    const modal = document.createElement('div');
    modal.className = 'modal-content';
    modal.style.cssText = `
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 2rem;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: var(--card-shadow);
        transform: scale(0.9);
        transition: transform 0.3s;
    `;
    
    modal.innerHTML = `
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="margin: 0; color: var(--text-primary);">${options.title}</h2>
            <button class="modal-close" style="background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            ${options.content}
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Apply common form styles
    const style = document.createElement('style');
    style.textContent = `
        .modal-content .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .modal-content label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        .modal-content input {
            padding: 0.75rem;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            transition: all 0.3s;
        }
        .modal-content input:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        .modal-content .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .modal-content .btn-primary {
            background: var(--accent-gradient);
            color: white;
        }
        .modal-content .btn-secondary {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        .modal-content .btn-danger {
            background: var(--danger);
            color: white;
        }
        .modal-content .toggle-setting {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0;
            cursor: pointer;
        }
        .modal-content .setting-group {
            padding: 1rem;
            background: var(--bg-hover);
            border-radius: 8px;
        }
    `;
    document.head.appendChild(style);
    
    // Show modal with animation
    requestAnimationFrame(() => {
        overlay.style.opacity = '1';
        modal.style.transform = 'scale(1)';
    });
    
    // Close functionality
    const closeModal = () => {
        overlay.style.opacity = '0';
        modal.style.transform = 'scale(0.9)';
        setTimeout(() => {
            overlay.remove();
            style.remove();
        }, 300);
    };
    
    // Close button
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
    
    // Handle form submission if exists
    const form = modal.querySelector('form');
    if (form && options.onSubmit) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = {};
            const inputs = form.querySelectorAll('input:not([type="submit"]), select, textarea');
            inputs.forEach(input => {
                if (input.type === 'checkbox') {
                    formData[input.name] = input.checked;
                } else {
                    formData[input.name] = input.value;
                }
            });
            
            const result = options.onSubmit(formData);
            if (result !== false) {
                closeModal();
            }
        });
    }
    
    // Call onMount if provided
    if (options.onMount) {
        options.onMount();
    }
}

// Helper function to get current user mobile
function getCurrentUserMobile() {
    const userElement = document.querySelector('.user-profile-btn span');
    return userElement ? userElement.textContent : '';
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--info)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        z-index: 10001;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        animation: toastSlideIn 0.3s ease;
        max-width: 400px;
    `;
    
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
    toast.innerHTML = `<i class="fas fa-${icon}"></i> ${message}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Smooth animations with RequestAnimationFrame
function initializeSmoothAnimations() {
    // Optimize scroll performance
    let ticking = false;
    function updateScrollEffects() {
        const scrollY = window.scrollY;
        
        // Header shadow on scroll
        const header = document.querySelector('.header');
        if (header) {
            if (scrollY > 50) {
                header.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.1)';
            } else {
                header.style.boxShadow = '';
            }
        }
        
        // Parallax effects
        const parallaxElements = document.querySelectorAll('[data-parallax]');
        parallaxElements.forEach(el => {
            const speed = el.dataset.parallax || 0.5;
            const yPos = -(scrollY * speed);
            el.style.transform = `translateY(${yPos}px)`;
        });
        
        ticking = false;
    }
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(updateScrollEffects);
            ticking = true;
        }
    });
    
    // Smooth hover effects for cards
    const cards = document.querySelectorAll('.card, .info-card, .stat-card');
    cards.forEach(card => {
        card.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        card.style.willChange = 'transform';
        
        card.addEventListener('mouseenter', () => {
            requestAnimationFrame(() => {
                card.style.transform = 'translateY(-5px)';
                card.style.boxShadow = 'var(--hover-shadow)';
            });
        });
        
        card.addEventListener('mouseleave', () => {
            requestAnimationFrame(() => {
                card.style.transform = '';
                card.style.boxShadow = '';
            });
        });
    });
}

// GSTIN Validation Function
function validateGSTIN(input) {
    const gstin = input.value;
    const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    
    // Remove any existing validation message
    const existingMsg = input.parentElement.querySelector('.validation-message');
    if (existingMsg) {
        existingMsg.remove();
    }
    
    if (gstin.length === 0) {
        input.style.borderColor = '';
        return true;
    }
    
    if (gstin.length < 15) {
        input.style.borderColor = '#ffc107';
        return false;
    }
    
    if (!pattern.test(gstin)) {
        input.style.borderColor = '#dc3545';
        const msg = document.createElement('small');
        msg.className = 'validation-message text-danger';
        msg.style.display = 'block';
        msg.style.marginTop = '0.25rem';
        msg.textContent = 'Invalid GSTIN format';
        input.parentElement.appendChild(msg);
        return false;
    }
    
    input.style.borderColor = '#28a745';
    return true;
}

// Debounce Function for Search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format Date Function
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('en-IN', options);
}

// Enhanced Theme Toggle Functionality
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.getElementById('theme-indicator-icon');
    
    if (body.classList.contains('light-theme')) {
        body.classList.remove('light-theme');
        if (themeIcon) themeIcon.className = 'fas fa-moon';
        localStorage.setItem('theme', 'dark');
    } else {
        body.classList.add('light-theme');
        if (themeIcon) themeIcon.className = 'fas fa-sun';
        localStorage.setItem('theme', 'light');
    }
    
    // Dispatch custom event for theme change
    document.dispatchEvent(new Event('themeChanged'));
}

// 1. Animated Number Counter
function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value + '%';
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// 2. Particle Background Generator
function createParticles() {
    const particlesContainer = document.createElement('div');
    particlesContainer.className = 'particles';
    particlesContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        z-index: -1;
        pointer-events: none;
    `;
    document.body.appendChild(particlesContainer);
    
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: 5px;
            height: 5px;
            background: rgba(124, 58, 237, 0.5);
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            animation: particleFloat ${15 + Math.random() * 10}s linear infinite;
            animation-delay: ${Math.random() * 15}s;
        `;
        particlesContainer.appendChild(particle);
    }
}

// 3. Dynamic Greeting Based on Time
function setDynamicGreeting() {
    const hour = new Date().getHours();
    let greeting = '';
    
    if (hour < 12) {
        greeting = '🌅 Good Morning';
    } else if (hour < 17) {
        greeting = '☀️ Good Afternoon';
    } else {
        greeting = '🌙 Good Evening';
    }
    
    const greetingElements = document.querySelectorAll('.welcome-title');
    greetingElements.forEach(element => {
        if (element.textContent.includes('Welcome')) {
            element.textContent = `${greeting}, Welcome to GST Intelligence Platform`;
        }
    });
}

// 4. Interactive Score Display
function enhanceScoreDisplay() {
    const scoreElements = document.querySelectorAll('.score-badge');
    scoreElements.forEach(element => {
        element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        element.addEventListener('mouseenter', function() {
            requestAnimationFrame(() => {
                this.style.transform = 'scale(1.1) rotate(5deg)';
            });
        });
        
        element.addEventListener('mouseleave', function() {
            requestAnimationFrame(() => {
                this.style.transform = 'scale(1) rotate(0deg)';
            });
        });
    });
}

// 5. Enhanced Search Input with Better Validation
function enhanceSearchInput() {
    const searchInput = document.getElementById('gstin');
    if (searchInput) {
        // Auto-format GSTIN as user types
        searchInput.addEventListener('input', function(e) {
            let value = e.target.value.toUpperCase();
            
            // Visual feedback for valid/invalid GSTIN
            if (value.length === 15) {
                const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
                if (pattern.test(value)) {
                    e.target.style.borderColor = '#10b981';
                    e.target.style.boxShadow = '0 0 0 4px rgba(16, 185, 129, 0.1)';
                    // Add success animation
                    e.target.classList.add('success-pulse');
                } else {
                    e.target.style.borderColor = '#ef4444';
                    e.target.style.boxShadow = '0 0 0 4px rgba(239, 68, 68, 0.1)';
                    e.target.classList.remove('success-pulse');
                }
            } else {
                e.target.style.borderColor = '';
                e.target.style.boxShadow = '';
                e.target.classList.remove('success-pulse');
            }
        });
        
        // Add placeholder animation
        const placeholders = [
            'e.g., 27AADCB2230M1Z8',
            'Enter 15-digit GSTIN',
            'Search company by GSTIN'
        ];
        let placeholderIndex = 0;
        
        setInterval(() => {
            if (!searchInput.value && searchInput !== document.activeElement) {
                placeholderIndex = (placeholderIndex + 1) % placeholders.length;
                searchInput.placeholder = placeholders[placeholderIndex];
            }
        }, 3000);
    }
}

// 6. Table Row Animation
function animateTableRows() {
    const rows = document.querySelectorAll('.history-table tbody tr');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            requestAnimationFrame(() => {
                row.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                row.style.opacity = '1';
                row.style.transform = 'translateX(0)';
            });
        }, index * 50);
    });
}

// 7. Add Confetti Effect for High Scores
function showConfetti() {
    const confettiColors = ['#f093fb', '#f5576c', '#ffc837', '#4facfe', '#43e97b'];
    const confettiCount = 100;
    
    for (let i = 0; i < confettiCount; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 10px;
            height: 10px;
            background: ${confettiColors[Math.floor(Math.random() * confettiColors.length)]};
            left: ${Math.random() * 100}%;
            top: -10px;
            transform: rotate(${Math.random() * 360}deg);
            z-index: 9999;
            pointer-events: none;
        `;
        document.body.appendChild(confetti);
        
        confetti.animate([
            { transform: `translateY(0) rotate(0deg)`, opacity: 1 },
            { transform: `translateY(${window.innerHeight}px) rotate(${Math.random() * 720}deg)`, opacity: 0 }
        ], {
            duration: 3000 + Math.random() * 2000,
            easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
        }).onfinish = () => confetti.remove();
    }
}

// 9. Enhanced Keyboard Shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('gstin');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Ctrl/Cmd + D for theme toggle
    if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        toggleTheme();
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('gstin');
        if (searchInput && searchInput === document.activeElement) {
            searchInput.value = '';
            searchInput.blur();
            // Reset input styling
            searchInput.style.borderColor = '';
            searchInput.style.boxShadow = '';
            searchInput.classList.remove('success-pulse');
        }
    }
});

// Add Enhanced CSS Styles
const enhancedStyles = document.createElement('style');
enhancedStyles.textContent = `
    /* Spinner Styles */
    .spinner-small {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #333;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    .validation-message {
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }
    
    .text-danger {
        color: #dc3545;
    }
    
    /* User Dropdown Styles */
    .user-dropdown-wrapper {
        position: relative;
        display: inline-block;
    }
    
    .user-profile-btn:hover {
        background: var(--bg-hover) !important;
        border-color: var(--accent-primary) !important;
    }
    
    .dropdown-arrow {
        transition: transform 0.3s;
        font-size: 0.8rem;
        margin-left: 0.25rem;
    }
    
    .dropdown-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        color: var(--text-primary);
        text-decoration: none;
        transition: all 0.2s;
    }
    
    .dropdown-item:hover {
        background: var(--bg-hover);
        color: var(--accent-primary);
    }
    
    .dropdown-item i {
        width: 20px;
        text-align: center;
    }
    
    .dropdown-divider {
        height: 1px;
        background: var(--border-color);
        margin: 0.5rem 0;
    }
    
    .logout-item {
        color: var(--danger);
    }
    
    .logout-item:hover {
        background: rgba(239, 68, 68, 0.1);
        color: var(--danger);
    }
    
    /* Toast Animations */
    @keyframes toastSlideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes toastSlideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    /* Particle Animation */
    @keyframes particleFloat {
        from {
            transform: translateY(100vh) translateX(0);
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        to {
            transform: translateY(-100vh) translateX(100px);
            opacity: 0;
        }
    }
    
    /* Success pulse animation */
    .success-pulse {
        animation: successPulse 2s infinite;
    }
    
    @keyframes successPulse {
        0% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    
    /* Smooth transitions for cards */
    .card, .info-card, .stat-card {
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                    box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    border-color 0.3s ease;
        will-change: transform;
    }
    
    /* Optimized animations */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* GPU acceleration for animated elements */
    .particle,
    .logo-icon,
    .score-circle-progress,
    .category-toggle {
        transform: translateZ(0);
        backface-visibility: hidden;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @media (max-width: 768px) {
        .nav-items.show {
            display: flex !important;
            flex-direction: column;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: inherit;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .user-dropdown-menu {
            right: -50px !important;
        }
    }
`;
document.head.appendChild(enhancedStyles);