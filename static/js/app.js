// =====================================================
// GST Intelligence Platform - Clean JavaScript Architecture
// =====================================================

/**
 * Core Application Module
 * Handles app initialization and global state
 */
class GSTApp {
  constructor() {
    this.modules = new Map();
    this.config = {
      theme: 'dark',
      apiEndpoint: '/api',
      version: '2.0.0',
      debug: false
    };
    
    this.init();
  }

  init() {
    this.loadTheme();
    this.bindGlobalEvents();
    this.initializeModules();
    
    if (this.config.debug) {
      console.log('🚀 GST App initialized');
    }
  }

  loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    this.setTheme(savedTheme);
  }

  setTheme(theme) {
    this.config.theme = theme;
    document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : null);
    localStorage.setItem('theme', theme);
    
    // Dispatch theme change event
    window.dispatchEvent(new CustomEvent('themeChanged', { 
      detail: { theme } 
    }));
  }

  toggleTheme() {
    const newTheme = this.config.theme === 'dark' ? 'light' : 'dark';
    this.setTheme(newTheme);
    return newTheme;
  }

  registerModule(name, instance) {
    this.modules.set(name, instance);
  }

  getModule(name) {
    return this.modules.get(name);
  }

  initializeModules() {
    // Initialize core modules
    this.registerModule('ui', new UIManager());
    this.registerModule('api', new APIManager());
    this.registerModule('notifications', new NotificationManager());
    this.registerModule('forms', new FormManager());
    
    // Initialize page-specific modules based on current page
    const currentPage = this.getCurrentPage();
    this.initializePageModules(currentPage);
  }

  getCurrentPage() {
    const path = window.location.pathname;
    if (path === '/') return 'dashboard';
    if (path === '/analytics') return 'analytics';
    if (path === '/history') return 'history';
    if (path.includes('/search')) return 'results';
    return 'default';
  }

  initializePageModules(page) {
    switch (page) {
      case 'dashboard':
        this.registerModule('search', new SearchManager());
        this.registerModule('dashboard', new DashboardManager());
        break;
      case 'analytics':
        this.registerModule('charts', new ChartManager());
        break;
      case 'history':
        this.registerModule('history', new HistoryManager());
        break;
      case 'results':
        this.registerModule('results', new ResultsManager());
        break;
    }
  }

  bindGlobalEvents() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'k':
            e.preventDefault();
            this.focusSearch();
            break;
          case '/':
            e.preventDefault();
            this.showShortcuts();
            break;
        }
      }
      
      if (e.key === 'Escape') {
        this.closeAllModals();
      }
    });

    // Global error handling
    window.addEventListener('error', (e) => {
      console.error('Global error:', e);
      this.getModule('notifications')?.showError('An unexpected error occurred');
    });

    // Online/offline status
    window.addEventListener('online', () => {
      this.getModule('notifications')?.showSuccess('Connection restored');
    });

    window.addEventListener('offline', () => {
      this.getModule('notifications')?.showWarning('You are now offline');
    });
  }

  focusSearch() {
    const searchInput = document.querySelector('#gstin, input[name="gstin"]');
    if (searchInput) {
      searchInput.focus();
      searchInput.select();
    }
  }

  showShortcuts() {
    this.getModule('ui')?.showModal('shortcuts');
  }

  closeAllModals() {
    this.getModule('ui')?.closeAllModals();
  }
}

/**
 * UI Manager - Handles UI components and interactions
 */
class UIManager {
  constructor() {
    this.activeModals = [];
    this.activeDropdowns = [];
    this.init();
  }

  init() {
    this.initializeTooltips();
    this.initializeDropdowns();
    this.initializeModals();
  }

  initializeTooltips() {
    // Initialize tooltips for elements with data-tooltip
    document.querySelectorAll('[data-tooltip]').forEach(element => {
      new Tooltip(element);
    });
  }

  initializeDropdowns() {
    document.querySelectorAll('[data-dropdown]').forEach(trigger => {
      new Dropdown(trigger);
    });
  }

  initializeModals() {
    // Modal triggers
    document.querySelectorAll('[data-modal]').forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const modalId = trigger.dataset.modal;
        this.showModal(modalId);
      });
    });
  }

  showModal(modalId, options = {}) {
    const modal = new Modal(modalId, options);
    this.activeModals.push(modal);
    modal.show();
    return modal;
  }

  closeAllModals() {
    this.activeModals.forEach(modal => modal.close());
    this.activeModals = [];
  }

  showLoading(element) {
    element.classList.add('loading');
    element.disabled = true;
  }

  hideLoading(element) {
    element.classList.remove('loading');
    element.disabled = false;
  }
}

/**
 * Tooltip Component
 */
class Tooltip {
  constructor(element) {
    this.element = element;
    this.tooltip = null;
    this.content = element.dataset.tooltip;
    this.position = element.dataset.tooltipPosition || 'top';
    this.delay = 300;
    this.hideDelay = 100;
    this.showTimeout = null;
    this.hideTimeout = null;
    
    this.init();
  }

  init() {
    this.element.addEventListener('mouseenter', () => this.show());
    this.element.addEventListener('mouseleave', () => this.hide());
    this.element.addEventListener('focus', () => this.show());
    this.element.addEventListener('blur', () => this.hide());
  }

  show() {
    this.clearTimeouts();
    this.showTimeout = setTimeout(() => {
      this.createTooltip();
      this.positionTooltip();
      this.tooltip.classList.add('tooltip--visible');
    }, this.delay);
  }

  hide() {
    this.clearTimeouts();
    this.hideTimeout = setTimeout(() => {
      if (this.tooltip) {
        this.tooltip.remove();
        this.tooltip = null;
      }
    }, this.hideDelay);
  }

  createTooltip() {
    if (this.tooltip) return;

    this.tooltip = document.createElement('div');
    this.tooltip.className = 'tooltip';
    this.tooltip.textContent = this.content;
    this.tooltip.setAttribute('role', 'tooltip');
    
    document.body.appendChild(this.tooltip);
  }

  positionTooltip() {
    if (!this.tooltip) return;

    const rect = this.element.getBoundingClientRect();
    const tooltipRect = this.tooltip.getBoundingClientRect();
    
    let top, left;

    switch (this.position) {
      case 'top':
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.right + 8;
        break;
    }

    // Adjust for viewport boundaries
    if (left < 8) left = 8;
    if (left + tooltipRect.width > window.innerWidth - 8) {
      left = window.innerWidth - tooltipRect.width - 8;
    }
    if (top < 8) top = rect.bottom + 8;

    this.tooltip.style.top = `${top}px`;
    this.tooltip.style.left = `${left}px`;
  }

  clearTimeouts() {
    if (this.showTimeout) clearTimeout(this.showTimeout);
    if (this.hideTimeout) clearTimeout(this.hideTimeout);
  }
}

/**
 * Dropdown Component
 */
class Dropdown {
  constructor(trigger) {
    this.trigger = trigger;
    this.dropdown = document.querySelector(trigger.dataset.dropdown);
    this.isOpen = false;
    
    this.init();
  }

  init() {
    this.trigger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.toggle();
    });

    document.addEventListener('click', (e) => {
      if (!this.trigger.contains(e.target) && !this.dropdown.contains(e.target)) {
        this.close();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });
  }

  toggle() {
    this.isOpen ? this.close() : this.open();
  }

  open() {
    this.isOpen = true;
    this.trigger.setAttribute('aria-expanded', 'true');
    this.dropdown.classList.add('dropdown--open');
    
    // Focus first focusable element
    const firstFocusable = this.dropdown.querySelector('a, button, input, [tabindex="0"]');
    if (firstFocusable) {
      setTimeout(() => firstFocusable.focus(), 100);
    }
  }

  close() {
    this.isOpen = false;
    this.trigger.setAttribute('aria-expanded', 'false');
    this.dropdown.classList.remove('dropdown--open');
    this.trigger.focus();
  }
}

/**
 * Modal Component
 */
class Modal {
  constructor(modalId, options = {}) {
    this.modalId = modalId;
    this.options = {
      title: options.title || 'Modal',
      content: options.content || '',
      size: options.size || 'medium',
      closeOnOverlay: options.closeOnOverlay !== false,
      ...options
    };
    this.modal = null;
    this.backdrop = null;
  }

  show() {
    this.createModal();
    this.bindEvents();
    
    // Animate in
    requestAnimationFrame(() => {
      this.backdrop.classList.add('modal-backdrop--visible');
      this.modal.classList.add('modal--visible');
    });

    // Focus management
    this.previousFocus = document.activeElement;
    this.focusModal();
  }

  createModal() {
    // Create backdrop
    this.backdrop = document.createElement('div');
    this.backdrop.className = 'modal-backdrop';
    
    // Create modal
    this.modal = document.createElement('div');
    this.modal.className = `modal modal--${this.options.size}`;
    this.modal.setAttribute('role', 'dialog');
    this.modal.setAttribute('aria-modal', 'true');
    this.modal.setAttribute('aria-labelledby', 'modal-title');

    this.modal.innerHTML = `
      <div class="modal__header">
        <h2 id="modal-title" class="modal__title">${this.options.title}</h2>
        <button class="modal__close" aria-label="Close modal">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="modal__body">
        ${this.options.content}
      </div>
      ${this.options.footer ? `<div class="modal__footer">${this.options.footer}</div>` : ''}
    `;

    this.backdrop.appendChild(this.modal);
    document.body.appendChild(this.backdrop);
  }

  bindEvents() {
    // Close button
    const closeBtn = this.modal.querySelector('.modal__close');
    closeBtn.addEventListener('click', () => this.close());

    // Overlay click
    if (this.options.closeOnOverlay) {
      this.backdrop.addEventListener('click', (e) => {
        if (e.target === this.backdrop) {
          this.close();
        }
      });
    }

    // Escape key
    this.escapeHandler = (e) => {
      if (e.key === 'Escape') {
        this.close();
      }
    };
    document.addEventListener('keydown', this.escapeHandler);
  }

  focusModal() {
    const firstFocusable = this.modal.querySelector('button, input, textarea, select, a[href], [tabindex="0"]');
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }

  close() {
    // Animate out
    this.backdrop.classList.remove('modal-backdrop--visible');
    this.modal.classList.remove('modal--visible');

    setTimeout(() => {
      this.cleanup();
    }, 200);
  }

  cleanup() {
    if (this.backdrop) {
      this.backdrop.remove();
    }
    
    // Remove event listener
    document.removeEventListener('keydown', this.escapeHandler);
    
    // Restore focus
    if (this.previousFocus) {
      this.previousFocus.focus();
    }
  }
}

/**
 * Notification Manager
 */
class NotificationManager {
  constructor() {
    this.container = null;
    this.notifications = [];
    this.init();
  }

  init() {
    this.createContainer();
  }

  createContainer() {
    this.container = document.createElement('div');
    this.container.className = 'notification-container';
    this.container.setAttribute('aria-live', 'polite');
    this.container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(this.container);
  }

  show(message, type = 'info', duration = 4000) {
    const notification = this.createNotification(message, type);
    this.notifications.push(notification);
    this.container.appendChild(notification);

    // Animate in
    requestAnimationFrame(() => {
      notification.classList.add('notification--visible');
    });

    // Auto remove
    if (duration > 0) {
      setTimeout(() => {
        this.remove(notification);
      }, duration);
    }

    return notification;
  }

  createNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification notification--${type}`;
    
    const icons = {
      success: 'fas fa-check-circle',
      error: 'fas fa-exclamation-circle',
      warning: 'fas fa-exclamation-triangle',
      info: 'fas fa-info-circle'
    };

    notification.innerHTML = `
      <div class="notification__icon">
        <i class="${icons[type] || icons.info}"></i>
      </div>
      <div class="notification__content">
        <div class="notification__message">${message}</div>
      </div>
      <button class="notification__close" aria-label="Close notification">
        <i class="fas fa-times"></i>
      </button>
    `;

    // Bind close event
    const closeBtn = notification.querySelector('.notification__close');
    closeBtn.addEventListener('click', () => {
      this.remove(notification);
    });

    return notification;
  }

  remove(notification) {
    notification.classList.remove('notification--visible');
    
    setTimeout(() => {
      notification.remove();
      this.notifications = this.notifications.filter(n => n !== notification);
    }, 200);
  }

  showSuccess(message, duration = 4000) {
    return this.show(message, 'success', duration);
  }

  showError(message, duration = 6000) {
    return this.show(message, 'error', duration);
  }

  showWarning(message, duration = 5000) {
    return this.show(message, 'warning', duration);
  }

  showInfo(message, duration = 4000) {
    return this.show(message, 'info', duration);
  }

  clear() {
    this.notifications.forEach(notification => {
      this.remove(notification);
    });
  }
}

/**
 * API Manager - Handles API requests
 */
class APIManager {
  constructor() {
    this.baseURL = '/api';
    this.defaultHeaders = {
      'Content-Type': 'application/json'
    };
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: { ...this.defaultHeaders, ...options.headers },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  async get(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin + this.baseURL);
    Object.keys(params).forEach(key => 
      url.searchParams.append(key, params[key])
    );
    
    return this.request(url.pathname + url.search);
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
}

/**
 * Form Manager - Handles form validation and submission
 */
class FormManager {
  constructor() {
    this.forms = new Map();
    this.init();
  }

  init() {
    this.initializeForms();
    this.setupGlobalValidation();
  }

  initializeForms() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
      this.registerForm(form);
    });
  }

  registerForm(form) {
    const formInstance = new Form(form);
    this.forms.set(form, formInstance);
    return formInstance;
  }

  setupGlobalValidation() {
    // Global GSTIN validation
    document.querySelectorAll('input[name="gstin"]').forEach(input => {
      input.addEventListener('input', (e) => {
        this.validateGSTIN(e.target);
      });
    });

    // Global mobile validation
    document.querySelectorAll('input[name="mobile"]').forEach(input => {
      input.addEventListener('input', (e) => {
        this.validateMobile(e.target);
      });
    });
  }

  validateGSTIN(input) {
    const gstin = input.value.toUpperCase();
    input.value = gstin;
    
    const isValid = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
    
    if (gstin.length === 15) {
      this.setFieldValidation(input, isValid, isValid ? 'Valid GSTIN format' : 'Invalid GSTIN format');
    } else {
      this.clearFieldValidation(input);
    }
    
    return isValid;
  }

  validateMobile(input) {
    const mobile = input.value.replace(/\D/g, '');
    input.value = mobile;
    
    if (mobile.length === 10) {
      const isValid = /^[6-9][0-9]{9}$/.test(mobile);
      this.setFieldValidation(input, isValid, isValid ? 'Valid mobile number' : 'Invalid mobile number');
      return isValid;
    } else {
      this.clearFieldValidation(input);
      return false;
    }
  }

  setFieldValidation(field, isValid, message) {
    field.classList.remove('input--valid', 'input--error');
    field.classList.add(isValid ? 'input--valid' : 'input--error');
    
    this.showFieldMessage(field, message, isValid ? 'success' : 'error');
  }

  clearFieldValidation(field) {
    field.classList.remove('input--valid', 'input--error');
    this.hideFieldMessage(field);
  }

  showFieldMessage(field, message, type) {
    this.hideFieldMessage(field);
    
    const messageEl = document.createElement('div');
    messageEl.className = `field-message field-message--${type}`;
    messageEl.textContent = message;
    
    field.parentNode.appendChild(messageEl);
  }

  hideFieldMessage(field) {
    const existingMessage = field.parentNode.querySelector('.field-message');
    if (existingMessage) {
      existingMessage.remove();
    }
  }
}

/**
 * Form Class for individual form instances
 */
class Form {
  constructor(element) {
    this.element = element;
    this.fields = new Map();
    this.isValid = false;
    
    this.init();
  }

  init() {
    this.bindSubmission();
    this.initializeFields();
  }

  bindSubmission() {
    this.element.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      if (this.validate()) {
        await this.submit();
      }
    });
  }

  initializeFields() {
    this.element.querySelectorAll('input, textarea, select').forEach(field => {
      this.fields.set(field.name, field);
      
      field.addEventListener('blur', () => {
        this.validateField(field);
      });
    });
  }

  validate() {
    let isValid = true;
    
    this.fields.forEach((field) => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });
    
    this.isValid = isValid;
    return isValid;
  }

  validateField(field) {
    // Add custom validation logic here
    const value = field.value.trim();
    const required = field.hasAttribute('required');
    
    if (required && !value) {
      app.getModule('forms').setFieldValidation(field, false, 'This field is required');
      return false;
    }
    
    return true;
  }

  async submit() {
    const submitBtn = this.element.querySelector('button[type="submit"]');
    
    try {
      app.getModule('ui').showLoading(submitBtn);
      
      const formData = new FormData(this.element);
      const data = Object.fromEntries(formData.entries());
      
      // Get action and method from form
      const action = this.element.action || window.location.href;
      const method = this.element.method || 'POST';
      
      const response = await fetch(action, {
        method: method.toUpperCase(),
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (response.ok) {
        app.getModule('notifications').showSuccess('Form submitted successfully!');
        
        // Handle redirect if specified
        const redirectTo = response.headers.get('Location');
        if (redirectTo) {
          window.location.href = redirectTo;
        }
      } else {
        throw new Error('Form submission failed');
      }
      
    } catch (error) {
      console.error('Form submission error:', error);
      app.getModule('notifications').showError('Form submission failed. Please try again.');
    } finally {
      app.getModule('ui').hideLoading(submitBtn);
    }
  }

  reset() {
    this.element.reset();
    this.fields.forEach((field) => {
      app.getModule('forms').clearFieldValidation(field);
    });
  }
}

// Initialize the application
let app;

document.addEventListener('DOMContentLoaded', () => {
  app = new GSTApp();
  
  // Make app globally available for debugging
  if (window.location.hostname === 'localhost' || app.config.debug) {
    window.gstApp = app;
  }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { GSTApp, UIManager, NotificationManager, APIManager, FormManager };
}