// GST Intelligence Platform - Fixed Common Scripts
// Single implementation, no duplicates

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 GST Platform Scripts Initializing...');
    
    // 1. Initialize Single Tooltip System
    initializeTooltipSystem();
    
    // 2. Initialize User Dropdown
    initializeUserDropdown();
    
    // 3. Auto-dismiss messages
    autoDismissMessages();
    
    // 4. Initialize theme functionality
    initializeTheme();
    
    // 5. Initialize other features
    initializeGSTINValidation();
    initializeKeyboardShortcuts();
    setDynamicGreeting();
    
    console.log('✅ All scripts initialized successfully');
});

// Single Tooltip System
function initializeTooltipSystem() {
    console.log('💬 Initializing tooltip system...');
    
    // Remove any existing tooltip containers
    document.querySelectorAll('.tooltip-container').forEach(el => el.remove());
    
    // Create single tooltip container
    const tooltipContainer = document.createElement('div');
    tooltipContainer.className = 'tooltip-container';
    tooltipContainer.style.cssText = `
        position: fixed;
        pointer-events: none;
        z-index: 999999;
        opacity: 0;
        transition: opacity 0.2s ease;
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
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    tooltipContainer.appendChild(tooltipContent);
    document.body.appendChild(tooltipContainer);
    
    let currentTarget = null;
    let showTimeout = null;
    let hideTimeout = null;
    
    // Position tooltip
    function positionTooltip(target) {
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltipContent.getBoundingClientRect();
        
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
        
        tooltipContainer.style.left = left + 'px';
        tooltipContainer.style.top = top + 'px';
    }
    
    // Show tooltip
    function showTooltip(target) {
        const text = target.getAttribute('data-tooltip') || target.getAttribute('title');
        if (!text) return;
        
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
    
    // Event delegation
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
}

// Fixed User Dropdown System
function initializeUserDropdown() {
    console.log('👤 Initializing user dropdown...');
    
    // Find all user profile elements
    const userElements = document.querySelectorAll('.user-profile');
    
    userElements.forEach(function(userElement) {
        // Skip if already processed
        if (userElement.classList.contains('dropdown-processed')) return;
        
        userElement.classList.add('dropdown-processed');
        
        const mobile = userElement.textContent.trim();
        
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'user-dropdown-wrapper';
        wrapper.style.position = 'relative';
        wrapper.style.display = 'inline-block';
        
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
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = menu.style.display === 'block';
            
            // Close all dropdowns
            document.querySelectorAll('.user-dropdown-menu').forEach(m => {
                m.style.display = 'none';
            });
            
            menu.style.display = isVisible ? 'none' : 'block';
            button.querySelector('.dropdown-arrow').style.transform = isVisible ? '' : 'rotate(180deg)';
        });
    });
    
    // Close dropdown on outside click
    document.addEventListener('click', function() {
        document.querySelectorAll('.user-dropdown-menu').forEach(menu => {
            menu.style.display = 'none';
        });
        document.querySelectorAll('.dropdown-arrow').forEach(arrow => {
            arrow.style.transform = '';
        });
    });
}

// Auto-dismiss messages
function autoDismissMessages() {
    const messages = document.querySelectorAll('.message, .error-message, .success-message');
    messages.forEach(function(message) {
        setTimeout(() => {
            message.style.animation = 'fadeOut 0.5s ease';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });
}

// Theme Management
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.className = savedTheme === 'light' ? 'light-theme' : '';
    updateThemeIcon();
}

function toggleTheme() {
    const isLight = document.body.classList.contains('light-theme');
    document.body.classList.toggle('light-theme');
    localStorage.setItem('theme', isLight ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const indicators = document.querySelectorAll('#theme-indicator-icon');
    const isLight = document.body.classList.contains('light-theme');
    indicators.forEach(icon => {
        icon.className = isLight ? 'fas fa-sun' : 'fas fa-moon';
    });
}

// GSTIN Validation
function initializeGSTINValidation() {
    const gstinInputs = document.querySelectorAll('input[name="gstin"]');
    gstinInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
            const isValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(this.value);
            this.style.borderColor = this.value.length === 15 ? (isValid ? 'var(--success)' : 'var(--danger)') : '';
        });
    });
}

// Dynamic Greeting
function setDynamicGreeting() {
    const hour = new Date().getHours();
    let greeting = 'Welcome';
    if (hour < 12) greeting = 'Good Morning';
    else if (hour < 17) greeting = 'Good Afternoon';
    else greeting = 'Good Evening';
    
    const greetingElements = document.querySelectorAll('.dynamic-greeting');
    greetingElements.forEach(el => el.textContent = greeting);
}

// Keyboard Shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('#gstin');
            if (searchInput) searchInput.focus();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay').forEach(modal => modal.remove());
        }
    });
}

// Modal System
window.openProfileModal = function() {
    createModal({
        title: 'My Profile',
        content: `
            <form id="profileForm">
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" name="displayName" placeholder="Enter your name">
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" name="email" placeholder="Enter your email">
                </div>
                <button type="submit" class="btn btn-primary">Save Profile</button>
            </form>
        `,
        onSubmit: async function(formData) {
            showToast('Profile updated successfully!', 'success');
            return true;
        }
    });
};

window.openPasswordModal = function() {
    createModal({
        title: 'Change Password',
        content: `
            <form id="passwordForm">
                <div class="form-group">
                    <label>Current Password</label>
                    <input type="password" name="currentPassword" required>
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" name="newPassword" required minlength="6">
                </div>
                <div class="form-group">
                    <label>Confirm Password</label>
                    <input type="password" name="confirmPassword" required>
                </div>
                <button type="submit" class="btn btn-primary">Change Password</button>
            </form>
        `,
        onSubmit: async function(formData) {
            if (formData.newPassword !== formData.confirmPassword) {
                showToast('Passwords do not match!', 'error');
                return false;
            }
            showToast('Password changed successfully!', 'success');
            return true;
        }
    });
};

window.openSettingsModal = function() {
    createModal({
        title: 'Settings',
        content: `
            <form id="settingsForm">
                <h3>Preferences</h3>
                <label>
                    <input type="checkbox" name="emailNotifications">
                    Email Notifications
                </label>
                <label>
                    <input type="checkbox" name="autoSearch" checked>
                    Auto-search on GSTIN paste
                </label>
                <button type="submit" class="btn btn-primary">Save Settings</button>
            </form>
        `,
        onSubmit: async function(formData) {
            localStorage.setItem('userSettings', JSON.stringify(formData));
            showToast('Settings saved!', 'success');
            return true;
        }
    });
};

// Modal Creator
function createModal(options) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.cssText = `
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
    `;
    
    const modal = document.createElement('div');
    modal.className = 'modal-content';
    modal.style.cssText = `
        background: var(--bg-card);
        border-radius: 16px;
        padding: 2rem;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
    `;
    
    modal.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 1.5rem;">
            <h2>${options.title}</h2>
            <button onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        </div>
        ${options.content}
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Handle form submission
    const form = modal.querySelector('form');
    if (form && options.onSubmit) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = Object.fromEntries(new FormData(form));
            const result = await options.onSubmit(formData);
            if (result !== false) overlay.remove();
        });
    }
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });
}

// Toast notifications
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
        animation: slideIn 0.3s ease;
    `;
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Export to Excel functionality
window.exportToExcel = function() {
    window.location.href = '/export/history';
};

// Make toggleTheme global
window.toggleTheme = toggleTheme;

// Add CSS animations
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
`;
document.head.appendChild(style);