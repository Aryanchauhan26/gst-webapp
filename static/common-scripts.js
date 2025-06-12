// GST Intelligence Platform - Enhanced Common Scripts (FIXED)
// Single tooltip system, enhanced user dropdown, and improved performance

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 GST Platform Common Scripts Loading...');
    
    // 1. Initialize Single Tooltip System (No Duplicates)
    initializeSingleTooltipSystem();
    
    // 2. Initialize Enhanced User Dropdown
    initializeEnhancedUserDropdown();
    
    // 3. Auto-dismiss messages
    autoDismissMessages();
    
    // 4. Initialize GSTIN validation
    initializeGSTINValidation();
    
    // 5. Initialize form handlers
    initializeFormHandlers();
    
    // 6. Initialize table interactions
    initializeTableInteractions();
    
    // 7. Initialize mobile menu
    initializeMobileMenu();
    
    // 8. Initialize global functions
    initializeGlobalFunctions();
    
    // 9. Initialize PWA features
    initializePWAFeatures();
    
    // 10. Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // 11. Initialize enhanced animations
    initializeSmoothAnimations();
    
    // 12. Initialize dynamic features
    setDynamicGreeting();
    if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
        createParticles();
    }
    enhanceScoreDisplay();
    enhanceSearchInput();
    animateTableRows();
    
    // 13. Animate score values on results page
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
    
    // 14. Add hover effects to buttons
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
        initializeEnhancedUserDropdown();
        
        // Retry if no dropdowns were created
        setTimeout(function() {
            const dropdowns = document.querySelectorAll('.user-dropdown-wrapper');
            if (dropdowns.length === 0) {
                console.log('⚠️ No dropdowns found, retrying...');
                initializeEnhancedUserDropdown();
            }
        }, 1000);
    }, 500);
    
    console.log('✅ All common scripts initialized successfully');
});

// Fixed Single Tooltip System - Prevents Duplicates
function initializeSingleTooltipSystem() {
    console.log('💬 Initializing single tooltip system...');
    
    // Remove ALL existing tooltip containers first
    const existingTooltips = document.querySelectorAll('.tooltip-container, .enhanced-tooltip-container, .tooltip-wrapper, .custom-tooltip');
    existingTooltips.forEach(el => el.remove());
    
    // Disable CSS tooltips completely
    const style = document.createElement('style');
    style.textContent = `
        [data-tooltip]::after,
        [data-tooltip]::before,
        .tooltip::after,
        .tooltip::before,
        .enhanced-tooltip::after,
        .enhanced-tooltip::before {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }
    `;
    document.head.appendChild(style);
    
    // Create single tooltip container
    const tooltipContainer = document.createElement('div');
    tooltipContainer.className = 'tooltip-container';
    tooltipContainer.style.cssText = `
        position: fixed;
        pointer-events: none;
        z-index: 999999;
        opacity: 0;
        transition: opacity 0.2s ease;
        max-width: 300px;
    `;
    
    const tooltipContent = document.createElement('div');
    tooltipContent.className = 'tooltip-content';
    tooltipContent.style.cssText = `
        background: #1a1a1a;
        color: #fff;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        line-height: 1.4;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        word-wrap: break-word;
        white-space: pre-wrap;
    `;
    
    const tooltipArrow = document.createElement('div');
    tooltipArrow.className = 'tooltip-arrow';
    tooltipArrow.style.cssText = `
        position: absolute;
        width: 0;
        height: 0;
        border-style: solid;
    `;
    
    tooltipContainer.appendChild(tooltipContent);
    tooltipContainer.appendChild(tooltipArrow);
    document.body.appendChild(tooltipContainer);
    
    // Track current tooltip
    let currentTarget = null;
    let showTimeout = null;
    let hideTimeout = null;
    
    // Position tooltip intelligently
    function positionTooltip(target) {
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltipContent.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const scrollY = window.scrollY;
        const scrollX = window.scrollX;
        
        // Default: above the element
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 10;
        let arrowPosition = 'bottom';
        
        // Adjust horizontal position
        if (left < 10) {
            left = 10;
        } else if (left + tooltipRect.width > viewportWidth - 10) {
            left = viewportWidth - tooltipRect.width - 10;
        }
        
        // Adjust vertical position
        if (top < 10) {
            top = rect.bottom + 10;
            arrowPosition = 'top';
        }
        
        tooltipContainer.style.left = left + 'px';
        tooltipContainer.style.top = top + 'px';
        
        // Position arrow
        const arrowLeft = Math.max(10, Math.min(rect.left + (rect.width / 2) - left, tooltipRect.width - 10));
        tooltipArrow.style.left = arrowLeft + 'px';
        
        if (arrowPosition === 'bottom') {
            tooltipArrow.style.bottom = '-5px';
            tooltipArrow.style.top = 'auto';
            tooltipArrow.style.borderWidth = '5px 5px 0 5px';
            tooltipArrow.style.borderColor = '#1a1a1a transparent transparent transparent';
        } else {
            tooltipArrow.style.top = '-5px';
            tooltipArrow.style.bottom = 'auto';
            tooltipArrow.style.borderWidth = '0 5px 5px 5px';
            tooltipArrow.style.borderColor = 'transparent transparent #1a1a1a transparent';
        }
    }
    
    // Show tooltip
    function showTooltip(target) {
        const text = target.getAttribute('data-tooltip') || target.getAttribute('title');
        if (!text) return;
        
        // Remove title attribute to prevent browser tooltip
        if (target.hasAttribute('title')) {
            target.setAttribute('data-tooltip', text);
            target.removeAttribute('title');
        }
        
        currentTarget = target;
        tooltipContent.textContent = text;
        
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
    
    // Event listeners using delegation
    document.addEventListener('mouseenter', function(e) {
        const target = e.target.closest('[data-tooltip], [title]');
        if (target) {
            clearTimeout(hideTimeout);
            showTimeout = setTimeout(() => showTooltip(target), 300);
        }
    }, true);
    
    document.addEventListener('mouseleave', function(e) {
        const target = e.target.closest('[data-tooltip], [title]');
        if (target && target === currentTarget) {
            clearTimeout(showTimeout);
            hideTimeout = setTimeout(hideTooltip, 100);
        }
    }, true);
    
    // Update on scroll
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        if (currentTarget) {
            tooltipContainer.style.opacity = '0';
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                if (currentTarget) {
                    positionTooltip(currentTarget);
                    tooltipContainer.style.opacity = '1';
                }
            }, 100);
        }
    }, { passive: true });
    
    console.log('✅ Single tooltip system initialized');
}

// FIXED: Enhanced User Dropdown System
function initializeEnhancedUserDropdown() {
    console.log('👤 Initializing enhanced user dropdown...');
    
    // Find user profile elements with multiple selectors
    const userElements = document.querySelectorAll([
        '.user-profile',
        '.nav-link[data-tooltip*="Logged in"]',
        '.nav-link[data-tooltip*="user"]',
        '.nav-link.user-profile'
    ].join(', '));
    
    console.log(`Found ${userElements.length} user elements:`, userElements);
    
    userElements.forEach(function(userElement, index) {
        // Skip if already processed
        if (userElement.classList.contains('dropdown-processed')) {
            return;
        }
        
        userElement.classList.add('dropdown-processed');
        
        const mobile = userElement.textContent.trim();
        console.log(`Processing user element ${index + 1}: ${mobile}`);
        
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'user-dropdown-wrapper';
        wrapper.style.cssText = `
            position: relative;
            display: inline-block;
        `;
        
        // Create enhanced button
        const button = document.createElement('button');
        button.className = 'user-profile-btn';
        button.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 500;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-family: inherit;
            font-size: 0.95rem;
            white-space: nowrap;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        `;
        
        button.innerHTML = `
            <i class="fas fa-user-circle" style="font-size: 1.1rem; color: var(--accent-primary);"></i>
            <span>${mobile}</span>
            <i class="fas fa-chevron-down dropdown-arrow" style="font-size: 0.8rem; margin-left: 0.5rem; transition: transform 0.3s;"></i>
        `;
        
        // Create dropdown menu
        const menu = document.createElement('div');
        menu.className = 'user-dropdown-menu';
        menu.style.cssText = `
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 0.75rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            box-shadow: 0 12px 48px rgba(0, 0, 0, 0.3);
            min-width: 220px;
            z-index: 1000;
            overflow: hidden;
            backdrop-filter: blur(20px);
            display: none;
        `;
        
        menu.innerHTML = `
            <div class="dropdown-item" onclick="openProfileModal()" style="display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem; color: var(--text-primary); cursor: pointer; border-bottom: 1px solid var(--border-color); transition: all 0.2s;">
                <i class="fas fa-user-edit" style="width: 20px; text-align: center;"></i>
                <span>Edit Profile</span>
            </div>
            <div class="dropdown-item" onclick="openPasswordModal()" style="display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem; color: var(--text-primary); cursor: pointer; border-bottom: 1px solid var(--border-color); transition: all 0.2s;">
                <i class="fas fa-key" style="width: 20px; text-align: center;"></i>
                <span>Change Password</span>
            </div>
            <div class="dropdown-item" onclick="openSettingsModal()" style="display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem; color: var(--text-primary); cursor: pointer; border-bottom: 1px solid var(--border-color); transition: all 0.2s;">
                <i class="fas fa-cog" style="width: 20px; text-align: center;"></i>
                <span>Settings</span>
            </div>
            <div class="dropdown-item logout-item" onclick="window.location.href='/logout'" style="display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem; color: var(--danger); cursor: pointer; transition: all 0.2s;">
                <i class="fas fa-sign-out-alt" style="width: 20px; text-align: center;"></i>
                <span>Logout</span>
            </div>
        `;
        
        // Replace original element
        userElement.parentNode.insertBefore(wrapper, userElement);
        wrapper.appendChild(button);
        wrapper.appendChild(menu);
        userElement.remove();
        
        // Add hover effects to dropdown items
        const dropdownItems = menu.querySelectorAll('.dropdown-item');
        dropdownItems.forEach(item => {
            item.addEventListener('mouseenter', function() {
                if (!this.classList.contains('logout-item')) {
                    this.style.background = 'var(--bg-hover)';
                    this.style.color = 'var(--accent-primary)';
                    this.style.paddingLeft = '1.5rem';
                } else {
                    this.style.background = 'rgba(239, 68, 68, 0.1)';
                }
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.background = '';
                this.style.color = this.classList.contains('logout-item') ? 'var(--danger)' : 'var(--text-primary)';
                this.style.paddingLeft = '1.25rem';
            });
        });
        
        // Add click handler
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = menu.style.display === 'block';
            
            // Hide all other dropdowns
            document.querySelectorAll('.user-dropdown-menu').forEach(m => {
                if (m !== menu) {
                    m.style.display = 'none';
                    const otherArrow = m.parentElement.querySelector('.dropdown-arrow');
                    if (otherArrow) otherArrow.style.transform = 'rotate(0deg)';
                }
            });
            
            menu.style.display = isVisible ? 'none' : 'block';
            
            // Rotate arrow
            const arrow = button.querySelector('.dropdown-arrow');
            if (arrow) {
                arrow.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
            }
            
            // Add button hover effect
            if (!isVisible) {
                button.style.background = 'var(--bg-hover)';
                button.style.borderColor = 'var(--accent-primary)';
                button.style.transform = 'translateY(-1px)';
                button.style.boxShadow = '0 4px 16px rgba(124, 58, 237, 0.2)';
            }
        });
        
        // Button hover effects
        button.addEventListener('mouseenter', function() {
            if (menu.style.display !== 'block') {
                this.style.background = 'var(--bg-hover)';
                this.style.borderColor = 'var(--accent-primary)';
                this.style.transform = 'translateY(-1px)';
                this.style.boxShadow = '0 4px 16px rgba(124, 58, 237, 0.2)';
            }
        });
        
        button.addEventListener('mouseleave', function() {
            if (menu.style.display !== 'block') {
                this.style.background = 'var(--bg-card)';
                this.style.borderColor = 'var(--border-color)';
                this.style.transform = '';
                this.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
            }
        });
        
        console.log(`✅ Created enhanced dropdown for: ${mobile}`);
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-dropdown-wrapper')) {
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
                const button = menu.parentElement.querySelector('.user-profile-btn');
                const arrow = menu.parentElement.querySelector('.dropdown-arrow');
                
                if (button) {
                    button.style.background = 'var(--bg-card)';
                    button.style.borderColor = 'var(--border-color)';
                    button.style.transform = '';
                    button.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                }
                if (arrow) {
                    arrow.style.transform = 'rotate(0deg)';
                }
            });
        }
    });
    
    console.log('✅ Enhanced user dropdown system initialized');
}

// Modal System for Profile Management
window.openProfileModal = function() {
    createModal({
        title: 'My Profile',
        content: `
            <form id="profileForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Mobile Number</label>
                    <input type="text" value="Loading..." disabled style="background: var(--bg-hover); cursor: not-allowed; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Display Name</label>
                    <input type="text" name="displayName" placeholder="Enter your name" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Email (Optional)</label>
                    <input type="email" name="email" placeholder="Enter your email" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Company Name (Optional)</label>
                    <input type="text" name="company" placeholder="Enter company name" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <button type="submit" style="background: var(--accent-gradient); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer;">Save Profile</button>
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
};

window.openPasswordModal = function() {
    createModal({
        title: 'Change Password',
        content: `
            <form id="passwordForm" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Current Password</label>
                    <input type="password" name="currentPassword" required style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">New Password</label>
                    <input type="password" name="newPassword" required minlength="6" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <div class="form-group">
                    <label style="color: var(--text-secondary); margin-bottom: 0.5rem; display: block; font-weight: 500;">Confirm New Password</label>
                    <input type="password" name="confirmPassword" required style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-input); color: var(--text-primary);">
                </div>
                <button type="submit" style="background: var(--accent-gradient); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer;">Change Password</button>
            </form>
        `,
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
                <div style="padding: 1rem; background: var(--bg-hover); border-radius: 8px;">
                    <h3 style="margin-bottom: 1rem; color: var(--text-primary);">Preferences</h3>
                    <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; cursor: pointer;">
                        <input type="checkbox" name="emailNotifications">
                        <span style="color: var(--text-primary);">Email Notifications</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; cursor: pointer;">
                        <input type="checkbox" name="autoSearch" checked>
                        <span style="color: var(--text-primary);">Auto-search on GSTIN paste</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; cursor: pointer;">
                        <input type="checkbox" name="animations" checked>
                        <span style="color: var(--text-primary);">Enable animations</span>
                    </label>
                </div>
                <div style="padding: 1rem; background: var(--bg-hover); border-radius: 8px;">
                    <h3 style="margin-bottom: 1rem; color: var(--text-primary);">Data & Privacy</h3>
                    <button type="button" onclick="downloadUserData()" style="background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); padding: 0.75rem 1rem; border-radius: 8px; cursor: pointer; margin-right: 1rem; margin-bottom: 0.5rem;">
                        <i class="fas fa-download"></i> Download My Data
                    </button>
                    <button type="button" onclick="confirmDeleteAccount()" style="background: var(--danger); color: white; border: none; padding: 0.75rem 1rem; border-radius: 8px; cursor: pointer;">
                        <i class="fas fa-trash"></i> Delete Account
                    </button>
                </div>
                <button type="submit" style="background: var(--accent-gradient); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer;">Save Settings</button>
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
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="margin: 0; color: var(--text-primary);">${options.title}</h2>
            <button class="modal-close" style="background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div>
            ${options.content}
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Show modal with animation
    requestAnimationFrame(() => {
        overlay.style.opacity = '1';
        modal.style.transform = 'scale(1)';
    });
    
    // Close functionality
    const closeModal = () => {
        overlay.style.opacity = '0';
        modal.style.transform = 'scale(0.9)';
        setTimeout(() => overlay.remove(), 300);
    };
    
    // Close button
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    
    // Handle form submission
    const form = modal.querySelector('form');
    if (form && options.onSubmit) {
        form.addEventListener('submit', async (e) => {
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
            
            const result = await options.onSubmit(formData);
            if (result !== false) closeModal();
        });
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
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

// Auto-dismiss messages
function autoDismissMessages() {
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s, transform 0.5s';
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });
}

// GSTIN Input Validation
function initializeGSTINValidation() {
    const gstinInputs = document.querySelectorAll('input[name="gstin"], #gstin');
    gstinInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            e.target.value = e.target.value.toUpperCase();
            validateGSTIN(e.target);
        });
        
        input.addEventListener('paste', function(e) {
            setTimeout(function() {
                e.target.value = e.target.value.toUpperCase().replace(/\s/g, '');
                validateGSTIN(e.target);
            }, 10);
        });
    });
}

function validateGSTIN(input) {
    const gstin = input.value;
    const pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    
    // Remove existing validation message
    const existingMsg = input.parentElement.querySelector('.validation-message');
    if (existingMsg) existingMsg.remove();
    
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
        msg.className = 'validation-message';
        msg.style.cssText = 'display: block; margin-top: 0.25rem; color: #dc3545; font-size: 0.875rem;';
        msg.textContent = 'Invalid GSTIN format';
        input.parentElement.appendChild(msg);
        return false;
    }
    
    input.style.borderColor = '#28a745';
    return true;
}

// Form Submit Handler
function initializeFormHandlers() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && submitBtn.disabled) {
                e.preventDefault();
                return;
            }
            
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-small"></span> Processing...';
                
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 30000);
            }
            
            const loadingOverlay = document.getElementById('loading');
            if (loadingOverlay) {
                loadingOverlay.style.display = 'block';
            }
        });
    });
}

// Table Row Click Handler
function initializeTableInteractions() {
    const tableRows = document.querySelectorAll('.history-table tbody tr');
    tableRows.forEach(function(row) {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(e) {
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
}

// Mobile Menu Toggle
function initializeMobileMenu() {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const navItems = document.querySelector('.nav-items');
    if (menuToggle && navItems) {
        menuToggle.addEventListener('click', function() {
            navItems.classList.toggle('show');
            this.classList.toggle('active');
        });
        
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.header')) {
                navItems.classList.remove('show');
                menuToggle.classList.remove('active');
            }
        });
    }
}

// Global Functions
function initializeGlobalFunctions() {
    // Copy to Clipboard
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
    
    // Share Functionality
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
            copyToClipboard(url || window.location.href, event.target);
        }
    };
    
    // Export to Excel Handler
    window.exportToExcel = function() {
        const exportBtn = event.target.closest('button');
        exportBtn.disabled = true;
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = 'Exporting...';
        
        window.location.href = '/export/history';
        
        setTimeout(function() {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalText;
        }, 3000);
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
                    showToast('Account deletion request submitted', 'info');
                }
            }
        }
    };
}

// PWA Features
function initializePWAFeatures() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js');
    }
}

// Enhanced Keyboard Shortcuts
function initializeKeyboardShortcuts() {
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
            if (typeof toggleTheme === 'function') {
                toggleTheme();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('gstin');
            if (searchInput && searchInput === document.activeElement) {
                searchInput.value = '';
                searchInput.blur();
                searchInput.style.borderColor = '';
                searchInput.style.boxShadow = '';
            }
        }
    });
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

// Add Enhanced CSS Styles
const enhancedStyles = document.createElement('style');
enhancedStyles.textContent = `
    /* Toast Animations */
    @keyframes toastSlideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes toastSlideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    /* Spinner */
    .spinner-small {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #333;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Ensure dropdowns are always visible */
    .user-dropdown-wrapper {
        position: relative !important;
        z-index: 1000 !important;
    }
    
    .user-dropdown-menu {
        z-index: 1001 !important;
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
`;
document.head.appendChild(enhancedStyles);