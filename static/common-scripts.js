// GST Intelligence Platform - Common Scripts
// Handles UI interactions and prevents common issues

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
    
    // 4. Table Row Click Handler
    const tableRows = document.querySelectorAll('.history-table tbody tr');
    tableRows.forEach(function(row) {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on a button
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
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

// Add CSS for spinner
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
    }
`;
document.head.appendChild(style);