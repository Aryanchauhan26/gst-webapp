// /static/js/missing-globals.js
// Create this file to provide missing global dependencies
// Load this BEFORE other JavaScript files

"use strict";

console.log("🔧 Loading missing globals...");

// =============================================================================
// 1. NOTIFICATION MANAGER (Referenced by multiple files)
// =============================================================================
window.notificationManager = {
    notifications: [],

    show(message, type = "info", duration = 5000) {
        const notification = this.create(message, type, duration);
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add("notification-show"), 100);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(notification), duration);
        }

        return notification;
    },

    create(message, type, duration) {
        const notification = document.createElement("div");
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getIcon(type)}"></i>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="window.notificationManager.remove(this.parentElement.parentElement)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        // Add styles if not present
        this.ensureStyles();

        this.notifications.push(notification);
        return notification;
    },

    remove(notification) {
        if (!notification || !notification.parentNode) return;

        notification.classList.add("notification-hide");
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            const index = this.notifications.indexOf(notification);
            if (index > -1) {
                this.notifications.splice(index, 1);
            }
        }, 300);
    },

    getIcon(type) {
        const icons = {
            success: "check-circle",
            error: "exclamation-circle",
            warning: "exclamation-triangle",
            info: "info-circle",
        };
        return icons[type] || "info-circle";
    },

    ensureStyles() {
        if (document.getElementById("notification-styles")) return;

        const style = document.createElement("style");
        style.id = "notification-styles";
        style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                min-width: 300px;
                max-width: 500px;
                background: var(--bg-card);
                border: 1px solid var(--border-primary);
                border-radius: 12px;
                box-shadow: var(--shadow-lg);
                z-index: 10000;
                transform: translateX(100%);
                transition: transform 0.3s ease;
            }

            .notification-show {
                transform: translateX(0);
            }

            .notification-hide {
                transform: translateX(100%);
            }

            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px;
            }

            .notification-message {
                flex: 1;
                color: var(--text-primary);
                font-weight: 500;
            }

            .notification-close {
                background: none;
                border: none;
                color: var(--text-muted);
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: color 0.2s ease;
            }

            .notification-close:hover {
                color: var(--text-primary);
            }

            .notification-success { border-left: 4px solid var(--success); }
            .notification-error { border-left: 4px solid var(--error); }
            .notification-warning { border-left: 4px solid var(--warning); }
            .notification-info { border-left: 4px solid var(--info); }
        `;
        document.head.appendChild(style);
    },
};

// =============================================================================
// 2. ERROR HANDLER (Referenced by dashboard.js)
// =============================================================================
window.GSTPlatform = {
    errorHandler: {
        handleAPIError(error, context = {}) {
            console.error("API Error:", error, context);

            let message = "An error occurred";

            if (error?.status === 401) {
                message = "Session expired. Please login again.";
                setTimeout(() => (window.location.href = "/login"), 2000);
            } else if (error?.status === 403) {
                message = "Access denied";
            } else if (error?.status === 404) {
                message = "Resource not found";
            } else if (error?.status >= 500) {
                message = "Server error. Please try again later.";
            } else if (error?.message) {
                message = error.message;
            }

            window.notificationManager.show(message, "error");
        },

        handleNetworkError(error) {
            console.error("Network Error:", error);
            window.notificationManager.show(
                "Network error. Please check your connection.",
                "error",
            );
        },
    },
};

// =============================================================================
// 3. LOADING MANAGER
// =============================================================================
window.loadingManager = {
    activeLoaders: new Set(),

    show(id = "global") {
        this.activeLoaders.add(id);
        this.updateGlobalLoader();
        return id;
    },

    hide(id = "global") {
        this.activeLoaders.delete(id);
        this.updateGlobalLoader();
    },

    updateGlobalLoader() {
        const hasLoaders = this.activeLoaders.size > 0;
        document.body.classList.toggle("loading", hasLoaders);

        // Update page loader if it exists
        const pageLoader = document.getElementById("page-loader");
        if (pageLoader) {
            pageLoader.style.display = hasLoaders ? "flex" : "none";
        }
    },
};

// =============================================================================
// 4. UTILITY FUNCTIONS
// =============================================================================
window.utils = {
    // Format numbers
    formatNumber(num) {
        if (num === null || num === undefined) return "N/A";
        return new Intl.NumberFormat("en-IN").format(num);
    },

    // Format currency
    formatCurrency(amount) {
        if (amount === null || amount === undefined) return "N/A";
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
        }).format(amount);
    },

    // Format date
    formatDate(date) {
        if (!date) return "N/A";
        return new Date(date).toLocaleDateString("en-IN", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    },

    // Format relative time
    formatRelativeTime(date) {
        if (!date) return "N/A";

        const now = new Date();
        const target = new Date(date);
        const diff = now - target;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days} day${days > 1 ? "s" : ""} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
        if (minutes > 0)
            return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
        return "Just now";
    },

    // Debounce function
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
    },

    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function () {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => (inThrottle = false), limit);
            }
        };
    },

    // Safe API call wrapper
    async safeApiCall(apiCall, context = {}) {
        const loaderId = window.loadingManager.show();

        try {
            const response = await apiCall();
            window.loadingManager.hide(loaderId);
            return response;
        } catch (error) {
            window.loadingManager.hide(loaderId);
            window.GSTPlatform.errorHandler.handleAPIError(error, context);
            throw error;
        }
    },
};

// =============================================================================
// 5. THEME MANAGER
// =============================================================================
window.themeManager = {
    init() {
        // Get saved theme or default to dark
        const savedTheme = localStorage.getItem("theme") || "dark";
        this.setTheme(savedTheme);

        // Listen for system theme changes
        if (window.matchMedia) {
            window
                .matchMedia("(prefers-color-scheme: dark)")
                .addEventListener("change", (e) => {
                    if (!localStorage.getItem("theme")) {
                        this.setTheme(e.matches ? "dark" : "light");
                    }
                });
        }
    },

    setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);

        // Update theme toggle button if it exists
        const themeToggle = document.getElementById("theme-toggle");
        if (themeToggle) {
            const icon = themeToggle.querySelector("i");
            if (icon) {
                icon.className =
                    theme === "dark" ? "fas fa-sun" : "fas fa-moon";
            }
        }
    },

    toggle() {
        const currentTheme =
            document.documentElement.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        this.setTheme(newTheme);
    },
};

// =============================================================================
// 6. FORM VALIDATION HELPERS
// =============================================================================
window.formValidator = {
    // Validate GSTIN
    validateGSTIN(gstin) {
        if (!gstin) return { valid: false, message: "GSTIN is required" };

        const cleanGstin = gstin.replace(/\s/g, "").toUpperCase();

        if (cleanGstin.length !== 15) {
            return { valid: false, message: "GSTIN must be 15 characters" };
        }

        const pattern =
            /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$/;
        if (!pattern.test(cleanGstin)) {
            return { valid: false, message: "Invalid GSTIN format" };
        }

        return { valid: true, value: cleanGstin };
    },

    // Validate mobile number
    validateMobile(mobile) {
        if (!mobile)
            return { valid: false, message: "Mobile number is required" };

        const cleanMobile = mobile.replace(/\D/g, "");

        if (cleanMobile.length !== 10) {
            return { valid: false, message: "Mobile number must be 10 digits" };
        }

        if (!/^[6-9]/.test(cleanMobile)) {
            return {
                valid: false,
                message: "Mobile number must start with 6, 7, 8, or 9",
            };
        }

        return { valid: true, value: cleanMobile };
    },

    // Validate email
    validateEmail(email) {
        if (!email) return { valid: false, message: "Email is required" };

        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!pattern.test(email)) {
            return { valid: false, message: "Invalid email format" };
        }

        return { valid: true, value: email.toLowerCase() };
    },

    // Show field error
    showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        // Remove existing error
        this.clearFieldError(fieldId);

        // Add error class
        field.classList.add("field-error");

        // Add error message
        const errorDiv = document.createElement("div");
        errorDiv.className = "field-error-message";
        errorDiv.textContent = message;
        errorDiv.id = `${fieldId}-error`;

        field.parentNode.appendChild(errorDiv);
    },

    // Clear field error
    clearFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;

        field.classList.remove("field-error");

        const errorMsg = document.getElementById(`${fieldId}-error`);
        if (errorMsg) {
            errorMsg.remove();
        }
    },
};

// =============================================================================
// 7. ANALYTICS HELPERS
// =============================================================================
window.analytics = {
    // Track page view
    trackPageView(page) {
        // Add your analytics tracking here
        console.log("Page view:", page);
    },

    // Track event
    trackEvent(category, action, label = null) {
        // Add your analytics tracking here
        console.log("Event:", { category, action, label });
    },

    // Track search
    trackSearch(gstin, success) {
        this.trackEvent("Search", success ? "Success" : "Failed", gstin);
    },
};

// =============================================================================
// 8. ENHANCED SEARCH FUNCTIONALITY
// =============================================================================
window.searchCompany = function(gstin) {
    if (gstin) {
        window.location.href = `/search?gstin=${gstin}`;
    }
};

// Enhanced export functionality
window.exportToExcel = function() {
    window.location.href = '/export/history';
    if (window.notificationManager) {
        window.notificationManager.showToast('📊 Exporting data...', 'info');
    }
};

// Enhanced profile modal
window.openEnhancedProfileModal = function() {
    if (window.modalManager) {
        window.modalManager.createModal({
            title: 'User Profile',
            content: `
                <div style="text-align: center; padding: 2rem;">
                    <h4>Enhanced Profile Features</h4>
                    <p>Profile management coming soon...</p>
                </div>
            `
        });
    }
};

// Enhanced clear data function
window.clearUserData = function() {
    if (confirm('Are you sure you want to clear all data?')) {
        localStorage.clear();
        if (window.notificationManager) {
            window.notificationManager.showToast('Data cleared successfully', 'success');
        }
        setTimeout(() => window.location.reload(), 1000);
    }
};

// =============================================================================
// 9. INITIALIZATION
// =============================================================================
document.addEventListener("DOMContentLoaded", function () {
    // Initialize theme manager
    window.themeManager.init();

    // Add global error handlers
    window.addEventListener("error", function (e) {
        console.error("Global error:", e.error);
        window.notificationManager.show(
            "An unexpected error occurred",
            "error",
        );
    });

    window.addEventListener("unhandledrejection", function (e) {
        console.error("Unhandled promise rejection:", e.reason);
        window.notificationManager.show(
            "An unexpected error occurred",
            "error",
        );
    });

    // Add loading styles if not present
    if (!document.getElementById("loading-styles")) {
        const style = document.createElement("style");
        style.id = "loading-styles";
        style.textContent = `
            body.loading {
                cursor: wait;
            }

            body.loading * {
                pointer-events: none;
            }

            .field-error {
                border-color: var(--error) !important;
                box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1) !important;
            }

            .field-error-message {
                color: var(--error);
                font-size: 0.875rem;
                margin-top: 0.25rem;
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }

            .field-error-message::before {
                content: "⚠";
                font-size: 0.75rem;
            }
        `;
        document.head.appendChild(style);
    }

    console.log("✅ Global dependencies loaded successfully");
});

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        notificationManager: window.notificationManager,
        GSTPlatform: window.GSTPlatform,
        loadingManager: window.loadingManager,
        utils: window.utils,
        themeManager: window.themeManager,
        formValidator: window.formValidator,
        analytics: window.analytics,
    };
}
s;
