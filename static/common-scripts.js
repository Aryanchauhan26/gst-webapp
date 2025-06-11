// GST Intelligence Platform - Common Scripts
// Add shared JavaScript here if needed.

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Auto-dismiss messages after 5 seconds
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
    
    // 2. GSTIN Input Formatter and Validator
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
    
    // 3. Form Submit Handler with Loading State
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
    
    // 4. Enhanced Table Row Click Handler with Tooltip Fix
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
    
    // 5. Mobile Menu Toggle
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
    
    // 6. Copy to Clipboard
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
    
    // 7. Share Functionality
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
    
    // 8. Export to Excel Handler
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
    
    // 9. Prevent Form Resubmission on Page Refresh
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }
    
    // 10. Handle Session Timeout Warning
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

    // 11. Enhanced Tooltip System - Prevents Clipping Issues
    function createTooltipSystem() {
        // Create tooltip container that won't be clipped
        const tooltipContainer = document.createElement('div');
        tooltipContainer.className = 'tooltip-wrapper enhanced-tooltip';
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
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.4;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 300px;
            word-wrap: break-word;
            white-space: nowrap;
        `;
        
        // Light theme support
        if (document.body.classList.contains('light-theme')) {
            tooltipContent.style.background = '#333';
            tooltipContent.style.color = '#fff';
        }
        
        tooltipContainer.appendChild(tooltipContent);
        document.body.appendChild(tooltipContainer);
        
        // Add event listeners to all elements with data-tooltip
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', function(e) {
                const text = this.getAttribute('data-tooltip');
                if (!text) return;
                
                tooltipContent.textContent = text;
                tooltipContainer.style.opacity = '1';
                
                // Position tooltip with viewport boundary detection
                const rect = this.getBoundingClientRect();
                const tooltipRect = tooltipContent.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                
                let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                let top = rect.top - tooltipRect.height - 12;
                
                // Horizontal boundary check
                if (left < 10) {
                    left = 10;
                } else if (left + tooltipRect.width > viewportWidth - 10) {
                    left = viewportWidth - tooltipRect.width - 10;
                }
                
                // Vertical boundary check
                if (top < 10) {
                    // Show below if not enough space above
                    top = rect.bottom + 12;
                    // Add arrow pointing up
                    tooltipContent.style.position = 'relative';
                }
                
                tooltipContainer.style.left = left + 'px';
                tooltipContainer.style.top = top + 'px';
            });
            
            element.addEventListener('mouseleave', function() {
                tooltipContainer.style.opacity = '0';
            });
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
    
    // Initialize enhanced tooltip system
    createTooltipSystem();

    // 12. Set dynamic greeting
    setDynamicGreeting();
    
    // 13. Create particle background
    if (window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
        createParticles();
    }
    
    // 14. Enhance score displays
    enhanceScoreDisplay();
    
    // 15. Enhance search input
    enhanceSearchInput();
    
    // 16. Animate table rows
    animateTableRows();
    
    // 17. Animate score values on results page
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
    
    // 18. Add hover effects to buttons
    const buttons = document.querySelectorAll('button, .btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            if (!button.disabled) {
                button.style.transform = 'translateY(-2px)';
            }
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = '';
        });
    });
});

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

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    const themeIcon = document.getElementById('theme-indicator-icon');
    
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        if (themeIcon) themeIcon.className = 'fas fa-sun';
    }
    
    // Add theme toggle to existing DOMContentLoaded or create new one
    const themeToggleBtn = document.querySelector('.theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
});

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
    document.body.appendChild(particlesContainer);
    
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = 15 + Math.random() * 10 + 's';
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
    
    const greetingElement = document.querySelector('.welcome-title');
    if (greetingElement) {
        greetingElement.textContent = `${greeting}, Welcome to GST Intelligence Platform`;
    }
}

// 4. Interactive Score Display
function enhanceScoreDisplay() {
    const scoreElements = document.querySelectorAll('.score-badge');
    scoreElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1) rotate(5deg)';
            this.style.transition = 'transform 0.3s ease';
        });
        element.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1) rotate(0deg)';
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
            row.style.transition = 'all 0.5s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

// 7. Add Confetti Effect for High Scores
function showConfetti() {
    const confettiColors = ['#f093fb', '#f5576c', '#ffc837', '#4facfe', '#43e97b'];
    const confettiCount = 100;
    
    for (let i = 0; i < confettiCount; i++) {
        const confetti = document.createElement('div');
        confetti.style.position = 'fixed';
        confetti.style.width = '10px';
        confetti.style.height = '10px';
        confetti.style.backgroundColor = confettiColors[Math.floor(Math.random() * confettiColors.length)];
        confetti.style.left = Math.random() * 100 + '%';
        confetti.style.top = '-10px';
        confetti.style.transform = `rotate(${Math.random() * 360}deg)`;
        confetti.style.zIndex = '9999';
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
const style = document.createElement('style');
style.textContent = `
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
    
    /* Enhanced tooltip visibility */
    .enhanced-tooltip {
        backdrop-filter: blur(10px);
    }
    
    /* Smooth button hover effects */
    button, .btn {
        transition: all 0.3s ease;
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
        
        .enhanced-tooltip .tooltip-content {
            max-width: 250px;
            font-size: 12px;
        }
    }
`;
document.head.appendChild(style);
