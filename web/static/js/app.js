// web/static/js/app.js

/**
 * Main JavaScript Application
 * Handles UI interactions, AJAX requests, and general functionality
 */

class TradingBotApp {
    constructor() {
        this.isLoading = false;
        this.init();
    }

    init() {
        // Initialize theme
        this.initTheme();
        
        // Initialize mobile menu
        this.initMobileMenu();
        
        // Initialize notifications
        this.initNotifications();
        
        // Initialize forms
        this.initForms();
        
        // Initialize auto-refresh
        this.initAutoRefresh();
        
        // Initialize tooltips
        this.initTooltips();
        
        console.log('TradingBot App initialized');
    }

    // Theme Management
    initTheme() {
        const darkMode = localStorage.getItem('darkMode') === 'true';
        this.setTheme(darkMode);
    }

    toggleTheme() {
        const isDark = document.documentElement.classList.contains('dark');
        this.setTheme(!isDark);
    }

    setTheme(isDark) {
        const html = document.documentElement;
        const lightIcon = document.getElementById('theme-icon-light');
        const darkIcon = document.getElementById('theme-icon-dark');

        if (isDark) {
            html.classList.add('dark');
            if (lightIcon) lightIcon.classList.remove('hidden');
            if (darkIcon) darkIcon.classList.add('hidden');
        } else {
            html.classList.remove('dark');
            if (lightIcon) lightIcon.classList.add('hidden');
            if (darkIcon) darkIcon.classList.remove('hidden');
        }

        localStorage.setItem('darkMode', isDark);
    }

    // Mobile Menu
    initMobileMenu() {
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('mobile-menu-overlay');
            
            if (overlay && !overlay.classList.contains('hidden') && 
                !sidebar.contains(e.target) && !e.target.closest('[onclick="toggleMobileMenu()"]')) {
                this.toggleMobileMenu();
            }
        });
    }

    toggleMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-menu-overlay');

        if (sidebar && overlay) {
            const isHidden = overlay.classList.contains('hidden');
            
            if (isHidden) {
                // Show menu
                overlay.classList.remove('hidden');
                sidebar.classList.remove('-translate-x-full');
                document.body.style.overflow = 'hidden';
            } else {
                // Hide menu
                overlay.classList.add('hidden');
                sidebar.classList.add('-translate-x-full');
                document.body.style.overflow = '';
            }
        }
    }

    // Notifications
    initNotifications() {
        // Load notifications on page load
        this.loadNotifications();
        
        // Check for new notifications periodically
        setInterval(() => {
            this.loadNotifications();
        }, 30000); // 30 seconds
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/v1/notifications?unread_only=true&limit=10');
            if (response.ok) {
                const notifications = await response.json();
                this.updateNotificationBadge(notifications.length);
                this.updateNotificationList(notifications);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    updateNotificationBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    updateNotificationList(notifications) {
        const list = document.getElementById('notification-list');
        if (!list) return;

        if (notifications.length === 0) {
            list.innerHTML = `
                <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                    <p>No new notifications</p>
                </div>
            `;
            return;
        }

        list.innerHTML = notifications.map(notif => `
            <div class="p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                 onclick="app.markNotificationRead('${notif.id}')">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        ${this.getNotificationIcon(notif.type)}
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="text-sm font-medium text-gray-900 dark:text-white">${notif.title}</p>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${notif.message}</p>
                        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">${this.formatTimestamp(notif.timestamp)}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    getNotificationIcon(type) {
        const icons = {
            'trade_executed': `<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>`,
            'strategy_signal': `<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
            </svg>`,
            'system_alert': `<svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>`
        };
        return icons[type] || icons['system_alert'];
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }

    async markNotificationRead(notificationId) {
        try {
            const response = await fetch(`/api/v1/notifications/${notificationId}/read`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.loadNotifications();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    toggleNotifications() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    }

    // User Menu
    toggleUserMenu() {
        const menu = document.getElementById('user-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    }

    // Form Handling
    initForms() {
        // Handle form submissions with loading states
        document.querySelectorAll('form[data-ajax]').forEach(form => {
            form.addEventListener('submit', (e) => {
                this.handleAjaxForm(e);
            });
        });

        // Handle confirmation dialogs
        document.querySelectorAll('[data-confirm]').forEach(element => {
            element.addEventListener('click', (e) => {
                const message = element.dataset.confirm;
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    async handleAjaxForm(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const method = form.method || 'POST';
        const action = form.action;

        this.showLoading();

        try {
            const response = await fetch(action, {
                method: method,
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.showMessage(result.message || 'Success', 'success');
                
                // Trigger custom event
                const event = new CustomEvent('formSuccess', { detail: result });
                form.dispatchEvent(event);
            } else {
                const error = await response.json();
                this.showMessage(error.detail || 'An error occurred', 'error');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            this.showMessage('Network error occurred', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Auto-refresh
    initAutoRefresh() {
        const refreshInterval = 30000; // 30 seconds
        
        setInterval(() => {
            this.refreshDashboardData();
        }, refreshInterval);
    }

    async refreshDashboardData() {
        // Only refresh if on dashboard page
        if (!window.location.pathname.includes('dashboard')) return;

        try {
            const response = await fetch('/api/dashboard-data');
            if (response.ok) {
                const data = await response.json();
                this.updateDashboardElements(data);
            }
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
        }
    }

    updateDashboardElements(data) {
        // Update portfolio metrics
        const metrics = data.portfolio_metrics;
        if (metrics) {
            this.updateElement('total-balance', this.formatCurrency(metrics.total_balance));
            this.updateElement('daily-change', this.formatCurrency(metrics.daily_change));
            this.updateElement('daily-change-pct', `${metrics.daily_change_pct}%`);
            this.updateElement('active-trades', metrics.active_positions_count);
            this.updateElement('win-rate', `${metrics.win_rate}%`);
        }

        // Update last refresh time
        this.updateElement('last-updated', 'Just now');
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    // Tooltips
    initTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });
            
            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.id = 'tooltip';
        tooltip.className = 'absolute bg-gray-900 text-white text-sm rounded px-2 py-1 z-50 pointer-events-none';
        tooltip.textContent = text;
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
    }

    hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    // Loading Management
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
        this.isLoading = true;
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
        this.isLoading = false;
    }

    // Message Display
    showMessage(message, type = 'info') {
        const colors = {
            success: 'bg-green-50 border-green-200 text-green-800',
            error: 'bg-red-50 border-red-200 text-red-800',
            warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
            info: 'bg-blue-50 border-blue-200 text-blue-800'
        };

        const messageDiv = document.createElement('div');
        messageDiv.className = `fixed top-20 right-4 z-50 p-4 border rounded-md ${colors[type]} max-w-sm`;
        messageDiv.innerHTML = `
            <div class="flex">
                <div class="flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-3 flex-shrink-0">
                    <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(messageDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }

    // Utility Functions
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    formatPercentage(value) {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }

    formatNumber(value, decimals = 2) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(value);
    }

    // Chart Helpers
    createChart(canvasId, config) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            ...config,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                ...config.options
            }
        });
    }

    // API Helpers
    async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }
}

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new TradingBotApp();
});

// Global functions for onclick handlers
function toggleTheme() {
    if (app) app.toggleTheme();
}

function toggleMobileMenu() {
    if (app) app.toggleMobileMenu();
}

function toggleNotifications() {
    if (app) app.toggleNotifications();
}

function toggleUserMenu() {
    if (app) app.toggleUserMenu();
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const notificationDropdown = document.getElementById('notification-dropdown');
    const userMenu = document.getElementById('user-menu');
    
    if (notificationDropdown && !notificationDropdown.contains(e.target) && 
        !e.target.closest('[onclick="toggleNotifications()"]')) {
        notificationDropdown.classList.add('hidden');
    }
    
    if (userMenu && !userMenu.contains(e.target) && 
        !e.target.closest('[onclick="toggleUserMenu()"]')) {
        userMenu.classList.add('hidden');
    }
});

// Export for use in other modules
window.TradingBotApp = TradingBotApp;