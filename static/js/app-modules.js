// =====================================================
// GST Intelligence Platform - Application Modules
// =====================================================

'use strict';

// =====================================================
// API MODULE - Handles all API communications
// =====================================================

class APIModule {
    constructor() {
        this.baseURL = '/api';
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.requestQueue = [];
        this.isOnline = navigator.onLine;
        
        // Setup online/offline detection
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processQueue();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }

    async init() {
        console.log('🔗 API Module initialized');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Check cache for GET requests
        if (config.method === 'GET') {
            const cachedData = this.getFromCache(url);
            if (cachedData) {
                return cachedData;
            }
        }

        // Handle offline state
        if (!this.isOnline) {
            const queueItem = { url, config, timestamp: Date.now() };
            this.requestQueue.push(queueItem);
            throw new Error('Request queued - device is offline');
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Cache successful GET requests
            if (config.method === 'GET') {
                this.setCache(url, data);
            }

            return data;
            
        } catch (error) {
            console.error(`API request failed: ${url}`, error);
            throw error;
        }
    }

    async get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${endpoint}?${query}` : endpoint;
        return this.request(url);
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
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
            return cached.data;
        }
        this.cache.delete(key);
        return null;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    clearCache() {
        this.cache.clear();
    }

    async processQueue() {
        while (this.requestQueue.length > 0) {
            const { url, config } = this.requestQueue.shift();
            try {
                await fetch(url, config);
            } catch (error) {
                console.error('Queued request failed:', error);
            }
        }
    }

    cleanup() {
        this.clearCache();
        this.requestQueue = [];
    }
}

// =====================================================
// UI MODULE - Handles UI interactions and components
// =====================================================

class UIModule {
    constructor() {
        this.components = new Map();
        this.animations = new Map();
    }

    async init() {
        this.setupLoadingStates();
        this.setupScrollEffects();
        this.setupIntersectionObserver();
        console.log('🎨 UI Module initialized');
    }

    setupLoadingStates() {
        // Add loading class to elements during operations
        const loadingElements = document.querySelectorAll('[data-loading]');
        loadingElements.forEach(element => {
            element.addEventListener('click', () => {
                this.showLoading(element);
            });
        });
    }

    showLoading(element) {
        element.classList.add('loading');
        element.setAttribute('aria-busy', 'true');
        
        const originalText = element.textContent;
        element.textContent = 'Loading...';
        
        // Store original text for restoration
        element.dataset.originalText = originalText;
    }

    hideLoading(element) {
        element.classList.remove('loading');
        element.setAttribute('aria-busy', 'false');
        
        if (element.dataset.originalText) {
            element.textContent = element.dataset.originalText;
            delete element.dataset.originalText;
        }
    }

    setupScrollEffects() {
        // Add scroll-based animations
        const scrollElements = document.querySelectorAll('[data-scroll]');
        
        const handleScroll = this.throttle(() => {
            scrollElements.forEach(element => {
                const rect = element.getBoundingClientRect();
                const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
                
                if (isVisible) {
                    element.classList.add('in-view');
                }
            });
        }, 100);

        window.addEventListener('scroll', handleScroll);
        handleScroll(); // Initial check
    }

    setupIntersectionObserver() {
        // Lazy loading and scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in');
                    
                    // Lazy load images
                    if (entry.target.dataset.src) {
                        entry.target.src = entry.target.dataset.src;
                        entry.target.removeAttribute('data-src');
                    }
                    
                    observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px'
        });

        // Observe elements
        const observeElements = document.querySelectorAll('[data-observe]');
        observeElements.forEach(element => {
            observer.observe(element);
        });
    }

    // Utility methods
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    animate(element, animation, duration = 300) {
        return new Promise((resolve) => {
            element.style.animation = `${animation} ${duration}ms ease`;
            
            const handleAnimationEnd = () => {
                element.style.animation = '';
                element.removeEventListener('animationend', handleAnimationEnd);
                resolve();
            };
            
            element.addEventListener('animationend', handleAnimationEnd);
        });
    }

    cleanup() {
        this.components.clear();
        this.animations.clear();
    }
}

// =====================================================
// AUTH MODULE - Handles authentication state
// =====================================================

class AuthModule {
    constructor() {
        this.currentUser = window.GST_APP_STATE?.currentUser || null;
        this.isAuthenticated = window.GST_APP_STATE?.isAuthenticated || false;
        this.sessionCheckInterval = null;
    }

    async init() {
        await this.checkAuthStatus();
        this.setupSessionMonitoring();
        console.log('🔐 Auth Module initialized');
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            
            this.currentUser = data.user;
            this.isAuthenticated = data.authenticated;
            
            // Update global state
            window.GST_APP_STATE.currentUser = this.currentUser;
            window.GST_APP_STATE.isAuthenticated = this.isAuthenticated;
            
        } catch (error) {
            console.error('Auth status check failed:', error);
            this.isAuthenticated = false;
            this.currentUser = null;
        }
    }

    setupSessionMonitoring() {
        // Check session every 5 minutes
        this.sessionCheckInterval = setInterval(() => {
            this.checkAuthStatus();
        }, 5 * 60 * 1000);
    }

    async logout() {
        try {
            await fetch('/logout', { method: 'POST' });
            this.currentUser = null;
            this.isAuthenticated = false;
            
            // Redirect to login
            window.location.href = '/login';
            
        } catch (error) {
            console.error('Logout failed:', error);
        }
    }

    requireAuth() {
        if (!this.isAuthenticated) {
            window.location.href = '/login';
            return false;
        }
        return true;
    }

    cleanup() {
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
        }
    }
}

// =====================================================
// NAVIGATION MODULE - Handles navigation and routing
// =====================================================

class NavigationModule {
    constructor() {
        this.currentPath = window.location.pathname;
        this.navigationItems = [];
    }

    async init() {
        this.setupNavigationItems();
        this.setupActiveStates();
        this.setupMobileNavigation();
        console.log('🧭 Navigation Module initialized');
    }

    setupNavigationItems() {
        this.navigationItems = document.querySelectorAll('.nav__link');
        
        this.navigationItems.forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleNavigationClick(e, item);
            });
        });
    }

    setupActiveStates() {
        this.navigationItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href === this.currentPath) {
                item.classList.add('nav__link--active');
                item.setAttribute('aria-current', 'page');
            } else {
                item.classList.remove('nav__link--active');
                item.removeAttribute('aria-current');
            }
        });
    }

    setupMobileNavigation() {
        const mobileToggle = document.getElementById('mobile-nav-toggle');
        const mobileNav = document.getElementById('main-nav');
        
        if (!mobileToggle || !mobileNav) return;

        mobileToggle.addEventListener('click', () => {
            const isOpen = mobileNav.classList.contains('mobile-nav-open');
            
            if (isOpen) {
                this.closeMobileNav();
            } else {
                this.openMobileNav();
            }
        });

        // Close mobile nav when clicking outside
        document.addEventListener('click', (e) => {
            if (!mobileNav.contains(e.target) && !mobileToggle.contains(e.target)) {
                this.closeMobileNav();
            }
        });
    }

    openMobileNav() {
        const mobileNav = document.getElementById('main-nav');
        const mobileToggle = document.getElementById('mobile-nav-toggle');
        
        mobileNav.classList.add('mobile-nav-open');
        mobileToggle.innerHTML = '<i class="fas fa-times"></i>';
        mobileToggle.setAttribute('aria-label', 'Close navigation');
        
        // Focus first navigation item
        const firstNavItem = mobileNav.querySelector('.nav__link');
        if (firstNavItem) {
            firstNavItem.focus();
        }
    }

    closeMobileNav() {
        const mobileNav = document.getElementById('main-nav');
        const mobileToggle = document.getElementById('mobile-nav-toggle');
        
        mobileNav.classList.remove('mobile-nav-open');
        mobileToggle.innerHTML = '<i class="fas fa-bars"></i>';
        mobileToggle.setAttribute('aria-label', 'Open navigation');
    }

    handleNavigationClick(e, item) {
        // Close mobile nav if open
        this.closeMobileNav();
        
        // Update active states
        this.navigationItems.forEach(navItem => {
            navItem.classList.remove('nav__link--active');
            navItem.removeAttribute('aria-current');
        });
        
        item.classList.add('nav__link--active');
        item.setAttribute('aria-current', 'page');
    }

    navigateTo(path) {
        window.location.href = path;
    }

    cleanup() {
        // Nothing to cleanup
    }
}

// =====================================================
// PROFILE MODULE - Handles user profile functionality
// =====================================================

class ProfileModule {
    constructor() {
        this.profileData = null;
        this.api = null;
    }

    async init() {
        this.api = window.gstApp.getModule('api');
        this.setupProfileDropdown();
        this.setupProfileActions();
        await this.loadProfileData();
        console.log('👤 Profile Module initialized');
    }

    setupProfileDropdown() {
        const profileDropdown = document.getElementById('userProfileDropdown');
        if (!profileDropdown) return;

        const profileBtn = document.getElementById('userProfileBtn');
        const dropdownMenu = document.getElementById('userDropdownMenu');

        if (!profileBtn || !dropdownMenu) return;

        profileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleProfileDropdown();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!profileDropdown.contains(e.target)) {
                this.closeProfileDropdown();
            }
        });

        // Handle dropdown menu clicks
        dropdownMenu.addEventListener('click', (e) => {
            const item = e.target.closest('.dropdown-item');
            if (item) {
                this.handleProfileAction(item);
            }
        });
    }

    setupProfileActions() {
        // Setup profile form if exists
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleProfileUpdate(new FormData(profileForm));
            });
        }
    }

    async loadProfileData() {
        try {
            const response = await this.api.get('/user/profile');
            if (response.success) {
                this.profileData = response.data;
                this.updateProfileUI();
            }
        } catch (error) {
            console.error('Failed to load profile data:', error);
        }
    }

    updateProfileUI() {
        if (!this.profileData) return;

        // Update profile display elements
        const profileElements = {
            userName: document.querySelector('.user__name'),
            userRole: document.querySelector('.user__role'),
            userAvatar: document.querySelector('.user__avatar')
        };

        if (profileElements.userName) {
            profileElements.userName.textContent = this.profileData.displayName || this.profileData.mobile;
        }

        if (profileElements.userRole) {
            profileElements.userRole.textContent = this.profileData.role || 'Member';
        }

        if (profileElements.userAvatar) {
            const initial = (this.profileData.displayName || this.profileData.mobile || 'U')[0].toUpperCase();
            profileElements.userAvatar.textContent = initial;
        }
    }

    toggleProfileDropdown() {
        const dropdown = document.getElementById('userProfileDropdown');
        const isActive = dropdown.classList.contains('active');
        
        if (isActive) {
            this.closeProfileDropdown();
        } else {
            this.openProfileDropdown();
        }
    }

    openProfileDropdown() {
        const dropdown = document.getElementById('userProfileDropdown');
        const button = document.getElementById('userProfileBtn');
        
        dropdown.classList.add('active');
        button.setAttribute('aria-expanded', 'true');
        
        // Load fresh profile data
        this.loadProfileData();
    }

    closeProfileDropdown() {
        const dropdown = document.getElementById('userProfileDropdown');
        const button = document.getElementById('userProfileBtn');
        
        dropdown.classList.remove('active');
        button.setAttribute('aria-expanded', 'false');
    }

    handleProfileAction(item) {
        const href = item.getAttribute('href');
        
        if (href === '/logout') {
            this.handleLogout();
        } else if (href) {
            window.location.href = href;
        }
        
        this.closeProfileDropdown();
    }

    async handleProfileUpdate(formData) {
        try {
            const response = await this.api.post('/user/profile', Object.fromEntries(formData));
            
            if (response.success) {
                window.gstApp.showNotification('Profile updated successfully!', 'success');
                await this.loadProfileData();
            } else {
                window.gstApp.showNotification('Failed to update profile', 'error');
            }
        } catch (error) {
            console.error('Profile update failed:', error);
            window.gstApp.showNotification('Profile update failed', 'error');
        }
    }

    async handleLogout() {
        try {
            await fetch('/logout', { method: 'POST' });
            window.location.href = '/login';
        } catch (error) {
            console.error('Logout failed:', error);
            window.location.href = '/login';
        }
    }

    cleanup() {
        this.profileData = null;
    }
}

// =====================================================
// LOANS MODULE - Handles loan functionality
// =====================================================

class LoansModule {
    constructor() {
        this.loanData = null;
        this.api = null;
    }

    async init() {
        this.api = window.gstApp.getModule('api');
        this.setupLoanForm();
        this.setupLoanCalculator();
        this.setupLoanTabs();
        await this.loadLoanData();
        console.log('💰 Loans Module initialized');
    }

    setupLoanForm() {
        const loanForm = document.getElementById('loanApplicationForm');
        if (!loanForm) return;

        loanForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLoanApplication(new FormData(loanForm));
        });

        // Setup form validation
        const inputs = loanForm.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.validateLoanForm();
            });
        });
    }

    setupLoanCalculator() {
        const calculatorInputs = document.querySelectorAll('#calcLoanAmount, #calcInterestRate, #calcTenure');
        
        calculatorInputs.forEach(input => {
            input.addEventListener('input', this.debounce(() => {
                this.calculateEMI();
            }, 300));
        });
    }

    setupLoanTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.dataset.tab;
                this.switchTab(targetTab, tabButtons, tabContents);
            });
        });
    }

    switchTab(targetTab, tabButtons, tabContents) {
        // Update button states
        tabButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === targetTab) {
                btn.classList.add('active');
            }
        });

        // Update content visibility
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === targetTab) {
                content.classList.add('active');
            }
        });
    }

    async loadLoanData() {
        try {
            const response = await this.api.get('/loans/applications');
            if (response.success) {
                this.loanData = response.data;
                this.updateLoanUI();
            }
        } catch (error) {
            console.error('Failed to load loan data:', error);
        }
    }

    updateLoanUI() {
        // Update loan applications display
        const applicationsContainer = document.getElementById('loanApplications');
        if (applicationsContainer && this.loanData) {
            // Render loan applications
            this.renderLoanApplications(applicationsContainer);
        }
    }

    renderLoanApplications(container) {
        if (!this.loanData || !this.loanData.applications) {
            container.innerHTML = '<p>No loan applications found.</p>';
            return;
        }

        const html = this.loanData.applications.map(app => `
            <div class="loan-application-card">
                <div class="application-header">
                    <div>
                        <div class="application-amount">₹${this.formatCurrency(app.amount)}</div>
                        <div class="application-purpose">${app.purpose}</div>
                    </div>
                    <div class="status-badge status-${app.status}">${app.status}</div>
                </div>
                <div class="application-details">
                    <div>Applied: ${this.formatDate(app.appliedDate)}</div>
                    <div>Tenure: ${app.tenure} months</div>
                    <div>Status: ${app.status}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    validateLoanForm() {
        const form = document.getElementById('loanApplicationForm');
        if (!form) return;

        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
            } else {
                field.classList.remove('error');
            }
        });

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = !isValid;
        }

        return isValid;
    }

    calculateEMI() {
        const amount = parseFloat(document.getElementById('calcLoanAmount')?.value) || 0;
        const rate = parseFloat(document.getElementById('calcInterestRate')?.value) || 0;
        const tenure = parseInt(document.getElementById('calcTenure')?.value) || 0;
        
        if (amount > 0 && rate > 0 && tenure > 0) {
            const monthlyRate = rate / (12 * 100);
            const emi = (amount * monthlyRate * Math.pow(1 + monthlyRate, tenure)) / 
                       (Math.pow(1 + monthlyRate, tenure) - 1);
            
            const totalAmount = emi * tenure;
            const totalInterest = totalAmount - amount;
            
            // Update UI
            this.updateEMIDisplay(emi, totalInterest, totalAmount);
        }
    }

    updateEMIDisplay(emi, totalInterest, totalAmount) {
        const emiAmountEl = document.getElementById('emiAmount');
        const totalInterestEl = document.getElementById('totalInterest');
        const totalAmountEl = document.getElementById('totalAmount');
        
        if (emiAmountEl) {
            emiAmountEl.textContent = `₹${this.formatNumber(Math.round(emi))}`;
        }
        if (totalInterestEl) {
            totalInterestEl.textContent = `₹${this.formatNumber(Math.round(totalInterest))}`;
        }
        if (totalAmountEl) {
            totalAmountEl.textContent = `₹${this.formatNumber(Math.round(totalAmount))}`;
        }
    }

    async handleLoanApplication(formData) {
        try {
            const response = await this.api.post('/loans/apply', Object.fromEntries(formData));
            
            if (response.success) {
                window.gstApp.showNotification('Loan application submitted successfully!', 'success');
                await this.loadLoanData();
                
                // Reset form
                document.getElementById('loanApplicationForm').reset();
            } else {
                window.gstApp.showNotification('Failed to submit loan application', 'error');
            }
        } catch (error) {
            console.error('Loan application failed:', error);
            window.gstApp.showNotification('Loan application failed', 'error');
        }
    }

    // Utility methods
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN').format(amount);
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-IN').format(num);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(new Date(date));
    }

    debounce(func, wait) {
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

    cleanup() {
        this.loanData = null;
    }
}

// =====================================================
// EXPORT MODULES
// =====================================================

// Make modules available globally
window.APIModule = APIModule;
window.UIModule = UIModule;
window.AuthModule = AuthModule;
window.NavigationModule = NavigationModule;
window.ProfileModule = ProfileModule;
window.LoansModule = LoansModule;

console.log('📦 Application modules loaded successfully');