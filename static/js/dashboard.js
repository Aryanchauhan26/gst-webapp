// =====================================================
// GST Intelligence Platform - Dashboard Module
// Advanced dashboard functionality with real-time analytics
// =====================================================

'use strict';

console.log('📊 GST Dashboard Module Loading...');

// =====================================================
// 1. DASHBOARD CONFIGURATION
// =====================================================

window.GST_DASHBOARD = {
    VERSION: '2.0.0',
    DEBUG: localStorage.getItem('gst_debug') === 'true',
    
    CONFIG: {
        REFRESH_INTERVAL: 30000, // 30 seconds
        CHART_ANIMATION_DURATION: 1000,
        COUNTER_ANIMATION_DURATION: 2000,
        MAX_CHART_POINTS: 30,
        CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
    },
    
    state: {
        initialized: false,
        charts: new Map(),
        refreshTimer: null,
        userStats: null,
        analyticsData: null
    },
    
    utils: {
        log: function(...args) {
            if (window.GST_DASHBOARD.DEBUG) {
                console.log('📊 DASHBOARD:', ...args);
            }
        },
        
        error: function(...args) {
            console.error('❌ DASHBOARD:', ...args);
        },
        
        formatNumber: function(num) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
            return num.toString();
        },
        
        formatDate: function(date) {
            return new Date(date).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short'
            });
        },
        
        debounce: function(func, wait) {
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
    }
};

// =====================================================
// 2. DASHBOARD DATA MANAGER
// =====================================================

class DashboardDataManager {
    constructor() {
        this.cache = new Map();
        this.isLoading = false;
    }

    async loadUserStats() {
        try {
            const cacheKey = 'user_stats';
            const cached = this.getFromCache(cacheKey);
            if (cached) return cached;

            window.GST_DASHBOARD.utils.log('Loading user stats...');
            
            const response = await fetch('/api/user/stats');
            const result = await response.json();
            
            if (result.success) {
                const stats = result.data;
                this.setCache(cacheKey, stats);
                window.GST_DASHBOARD.state.userStats = stats;
                return stats;
            }
            
            throw new Error(result.error || 'Failed to load user stats');
        } catch (error) {
            window.GST_DASHBOARD.utils.error('User stats load failed:', error);
            return this.getDefaultStats();
        }
    }

    async loadAnalyticsData(days = 30) {
        try {
            const cacheKey = `analytics_${days}`;
            const cached = this.getFromCache(cacheKey);
            if (cached) return cached;

            window.GST_DASHBOARD.utils.log('Loading analytics data...');
            
            const response = await fetch(`/api/user/activity?days=${days}`);
            const result = await response.json();
            
            if (result.success) {
                const data = result.data;
                this.setCache(cacheKey, data);
                window.GST_DASHBOARD.state.analyticsData = data;
                return data;
            }
            
            throw new Error(result.error || 'Failed to load analytics data');
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Analytics data load failed:', error);
            return this.getDefaultAnalyticsData();
        }
    }

    async refreshAllData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            window.GST_DASHBOARD.utils.log('Refreshing all dashboard data...');
            
            // Clear cache to force fresh data
            this.cache.clear();
            
            const [userStats, analyticsData] = await Promise.all([
                this.loadUserStats(),
                this.loadAnalyticsData()
            ]);
            
            // Dispatch refresh event
            window.dispatchEvent(new CustomEvent('dashboardDataRefreshed', {
                detail: { userStats, analyticsData }
            }));
            
            return { userStats, analyticsData };
        } finally {
            this.isLoading = false;
        }
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;
        
        if (Date.now() - cached.timestamp > window.GST_DASHBOARD.CONFIG.CACHE_DURATION) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    getDefaultStats() {
        return {
            total_searches: 0,
            unique_companies: 0,
            avg_compliance: 0,
            recent_searches: 0,
            last_search: null,
            user_level: { level: 'New User', icon: 'fas fa-user-plus', color: '#6b7280' },
            achievements: []
        };
    }

    getDefaultAnalyticsData() {
        return {
            daily_activity: [],
            hourly_activity: [],
            score_distribution: []
        };
    }
}

// =====================================================
// 3. CHART MANAGER
// =====================================================

class ChartManager {
    constructor() {
        this.charts = new Map();
        this.chartJS = null;
    }

    async ensureChartJS() {
        if (this.chartJS) return this.chartJS;
        
        if (window.Chart) {
            this.chartJS = window.Chart;
            this.configureDefaults();
            return this.chartJS;
        }
        
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.min.js';
            script.onload = () => {
                this.chartJS = window.Chart;
                this.configureDefaults();
                window.GST_DASHBOARD.utils.log('Chart.js loaded successfully');
                resolve(this.chartJS);
            };
            script.onerror = () => {
                window.GST_DASHBOARD.utils.error('Failed to load Chart.js');
                reject(new Error('Failed to load Chart.js'));
            };
            document.head.appendChild(script);
        });
    }

    configureDefaults() {
        if (!this.chartJS) return;
        
        this.chartJS.defaults.color = 'var(--text-secondary)';
        this.chartJS.defaults.borderColor = 'var(--border-color)';
        this.chartJS.defaults.backgroundColor = 'rgba(124, 58, 237, 0.1)';
        this.chartJS.defaults.plugins.legend.display = false;
        this.chartJS.defaults.responsive = true;
        this.chartJS.defaults.maintainAspectRatio = false;
        this.chartJS.defaults.animation.duration = window.GST_DASHBOARD.CONFIG.CHART_ANIMATION_DURATION;
    }

    async createActivityChart(canvasId, dailyData) {
        try {
            await this.ensureChartJS();
            
            const canvas = document.getElementById(canvasId);
            if (!canvas) {
                window.GST_DASHBOARD.utils.error(`Canvas ${canvasId} not found`);
                return null;
            }

            // Destroy existing chart
            this.destroyChart(canvasId);

            const ctx = canvas.getContext('2d');
            
            // Prepare data
            const labels = dailyData.map(d => window.GST_DASHBOARD.utils.formatDate(d.date));
            const searchData = dailyData.map(d => d.search_count || 0);
            const scoreData = dailyData.map(d => d.avg_score || 0);

            const chart = new this.chartJS(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Daily Searches',
                            data: searchData,
                            borderColor: '#7c3aed',
                            backgroundColor: 'rgba(124, 58, 237, 0.1)',
                            tension: 0.4,
                            fill: true,
                            pointBackgroundColor: '#7c3aed',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        },
                        {
                            label: 'Avg Compliance Score',
                            data: scoreData,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            fill: false,
                            pointBackgroundColor: '#10b981',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointRadius: 3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        tooltip: {
                            backgroundColor: 'rgba(26, 26, 26, 0.9)',
                            titleColor: '#ffffff',
                            bodyColor: '#a1a1aa',
                            borderColor: '#7c3aed',
                            borderWidth: 1,
                            cornerRadius: 8,
                            displayColors: true,
                            callbacks: {
                                title: function(context) {
                                    return context[0].label;
                                },
                                label: function(context) {
                                    const label = context.dataset.label;
                                    const value = context.parsed.y;
                                    return `${label}: ${label.includes('Score') ? value + '%' : value}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(100, 116, 139, 0.1)'
                            },
                            ticks: {
                                color: 'var(--text-secondary)'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(100, 116, 139, 0.1)'
                            },
                            ticks: {
                                color: 'var(--text-secondary)',
                                stepSize: 1
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                drawOnChartArea: false,
                            },
                            ticks: {
                                color: 'var(--text-secondary)',
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });

            this.charts.set(canvasId, chart);
            window.GST_DASHBOARD.utils.log(`Activity chart created: ${canvasId}`);
            
            return chart;
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Failed to create activity chart:', error);
            return null;
        }
    }

    async createDistributionChart(canvasId, distributionData) {
        try {
            await this.ensureChartJS();
            
            const canvas = document.getElementById(canvasId);
            if (!canvas) return null;

            this.destroyChart(canvasId);

            const ctx = canvas.getContext('2d');
            
            const chart = new this.chartJS(ctx, {
                type: 'doughnut',
                data: {
                    labels: distributionData.map(d => d.range),
                    datasets: [{
                        data: distributionData.map(d => d.count),
                        backgroundColor: [
                            '#10b981', // Excellent - Green
                            '#3b82f6', // Very Good - Blue  
                            '#f59e0b', // Good - Yellow
                            '#8b5cf6', // Average - Purple
                            '#ef4444'  // Poor - Red
                        ],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            backgroundColor: 'rgba(26, 26, 26, 0.9)',
                            titleColor: '#ffffff',
                            bodyColor: '#a1a1aa',
                            borderColor: '#7c3aed',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return `${context.label}: ${context.parsed} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });

            this.charts.set(canvasId, chart);
            window.GST_DASHBOARD.utils.log(`Distribution chart created: ${canvasId}`);
            
            return chart;
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Failed to create distribution chart:', error);
            return null;
        }
    }

    async createHourlyChart(canvasId, hourlyData) {
        try {
            await this.ensureChartJS();
            
            const canvas = document.getElementById(canvasId);
            if (!canvas) return null;

            this.destroyChart(canvasId);

            const ctx = canvas.getContext('2d');
            
            // Fill missing hours with 0
            const fullHourlyData = Array.from({ length: 24 }, (_, i) => {
                const hourData = hourlyData.find(h => h.hour === i);
                return hourData ? hourData.searches : 0;
            });

            const chart = new this.chartJS(ctx, {
                type: 'bar',
                data: {
                    labels: Array.from({ length: 24 }, (_, i) => {
                        if (i === 0) return '12 AM';
                        if (i === 12) return '12 PM';
                        return i < 12 ? `${i} AM` : `${i - 12} PM`;
                    }),
                    datasets: [{
                        label: 'Searches by Hour',
                        data: fullHourlyData,
                        backgroundColor: 'rgba(124, 58, 237, 0.6)',
                        borderColor: '#7c3aed',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            backgroundColor: 'rgba(26, 26, 26, 0.9)',
                            titleColor: '#ffffff',
                            bodyColor: '#a1a1aa',
                            borderColor: '#7c3aed',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: 'var(--text-secondary)',
                                maxRotation: 45
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1,
                                color: 'var(--text-secondary)'
                            },
                            grid: {
                                color: 'rgba(100, 116, 139, 0.1)'
                            }
                        }
                    }
                }
            });

            this.charts.set(canvasId, chart);
            window.GST_DASHBOARD.utils.log(`Hourly chart created: ${canvasId}`);
            
            return chart;
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Failed to create hourly chart:', error);
            return null;
        }
    }

    destroyChart(canvasId) {
        const existingChart = this.charts.get(canvasId);
        if (existingChart) {
            existingChart.destroy();
            this.charts.delete(canvasId);
        }
    }

    destroyAllCharts() {
        this.charts.forEach((chart, id) => {
            chart.destroy();
        });
        this.charts.clear();
    }

    updateChart(canvasId, newData) {
        const chart = this.charts.get(canvasId);
        if (!chart) return;

        chart.data = newData;
        chart.update('active');
    }
}

// =====================================================
// 4. STATS ANIMATOR
// =====================================================

class StatsAnimator {
    constructor() {
        this.runningAnimations = new Set();
    }

    animateNumber(element, startValue, endValue, duration = window.GST_DASHBOARD.CONFIG.COUNTER_ANIMATION_DURATION, suffix = '') {
        if (!element || this.runningAnimations.has(element)) return;

        this.runningAnimations.add(element);
        
        const startTime = performance.now();
        const difference = endValue - startValue;
        
        const step = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(startValue + (difference * easeOutQuart));
            
            element.textContent = window.GST_DASHBOARD.utils.formatNumber(current) + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = window.GST_DASHBOARD.utils.formatNumber(endValue) + suffix;
                this.runningAnimations.delete(element);
            }
        };
        
        requestAnimationFrame(step);
    }

    animateProgressBar(element, targetPercentage, duration = 1000) {
        if (!element) return;

        const startTime = performance.now();
        
        const step = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentPercentage = targetPercentage * easeOutQuart;
            
            element.style.width = currentPercentage + '%';
            
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };
        
        requestAnimationFrame(step);
    }

    animateCountUp(elements, stats) {
        elements.forEach(element => {
            const statType = element.getAttribute('data-stat-type');
            let targetValue = 0;
            let suffix = '';
            
            switch (statType) {
                case 'total-searches':
                    targetValue = stats.total_searches || 0;
                    break;
                case 'unique-companies':
                    targetValue = stats.unique_companies || 0;
                    break;
                case 'avg-compliance':
                    targetValue = Math.round(stats.avg_compliance || 0);
                    suffix = '%';
                    break;
                case 'recent-searches':
                    targetValue = stats.recent_searches || 0;
                    break;
            }
            
            this.animateNumber(element, 0, targetValue, 
                window.GST_DASHBOARD.CONFIG.COUNTER_ANIMATION_DURATION, suffix);
        });
    }
}

// =====================================================
// 5. DASHBOARD CONTROLLER
// =====================================================

class DashboardController {
    constructor() {
        this.dataManager = new DashboardDataManager();
        this.chartManager = new ChartManager();
        this.statsAnimator = new StatsAnimator();
        this.refreshTimer = null;
    }

    async initialize() {
        try {
            window.GST_DASHBOARD.utils.log('Initializing dashboard...');
            
            // Load initial data
            await this.loadAndDisplayData();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Setup auto-refresh
            this.setupAutoRefresh();
            
            // Mark as initialized
            window.GST_DASHBOARD.state.initialized = true;
            
            window.GST_DASHBOARD.utils.log('Dashboard initialized successfully');
            
            // Dispatch ready event
            window.dispatchEvent(new CustomEvent('dashboardReady'));
            
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Dashboard initialization failed:', error);
        }
    }

    async loadAndDisplayData() {
        try {
            // Show loading state
            this.showLoadingState();
            
            // Load data
            const [userStats, analyticsData] = await Promise.all([
                this.dataManager.loadUserStats(),
                this.dataManager.loadAnalyticsData()
            ]);
            
            // Update UI
            await this.updateDashboardUI(userStats, analyticsData);
            
            // Hide loading state
            this.hideLoadingState();
            
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Failed to load dashboard data:', error);
            this.hideLoadingState();
        }
    }

    async updateDashboardUI(userStats, analyticsData) {
        // Update stats counters
        this.updateStatsCounters(userStats);
        
        // Update user level
        this.updateUserLevel(userStats);
        
        // Update achievements
        this.updateAchievements(userStats.achievements);
        
        // Update charts
        await this.updateCharts(analyticsData);
        
        // Update last update time
        this.updateLastUpdateTime();
    }

    updateStatsCounters(stats) {
        const statElements = document.querySelectorAll('[data-stat-type]');
        if (statElements.length > 0) {
            this.statsAnimator.animateCountUp(statElements, stats);
        }
        
        // Update individual stat elements
        const elements = {
            totalSearches: document.querySelector('[data-user-stat="total-searches"]'),
            uniqueCompanies: document.querySelector('[data-user-stat="unique-companies"]'),
            avgCompliance: document.querySelector('[data-user-stat="avg-compliance"]'),
            recentSearches: document.querySelector('[data-user-stat="recent-searches"]')
        };
        
        if (elements.totalSearches) {
            this.statsAnimator.animateNumber(elements.totalSearches, 0, stats.total_searches || 0);
        }
        
        if (elements.uniqueCompanies) {
            this.statsAnimator.animateNumber(elements.uniqueCompanies, 0, stats.unique_companies || 0);
        }
        
        if (elements.avgCompliance) {
            this.statsAnimator.animateNumber(elements.avgCompliance, 0, 
                Math.round(stats.avg_compliance || 0), 1000, '%');
        }
        
        if (elements.recentSearches) {
            this.statsAnimator.animateNumber(elements.recentSearches, 0, stats.recent_searches || 0);
        }
    }

    updateUserLevel(stats) {
        const userLevelElement = document.querySelector('.user-level');
        const userProgressElement = document.querySelector('.user-progress');
        
        if (userLevelElement && stats.user_level) {
            const level = stats.user_level;
            userLevelElement.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                    <i class="${level.icon}" style="color: ${level.color};"></i>
                    <span style="color: ${level.color}; font-weight: 600;">${level.level}</span>
                </div>
            `;
        }
        
        if (userProgressElement) {
            this.updateUserProgress(stats);
        }
    }

    updateUserProgress(stats) {
        const totalSearches = stats.total_searches || 0;
        
        // Determine next milestone
        let nextMilestone = 5;
        if (totalSearches >= 5) nextMilestone = 20;
        if (totalSearches >= 20) nextMilestone = 50;
        if (totalSearches >= 50) nextMilestone = 100;
        if (totalSearches >= 100) nextMilestone = 200;

        const progressElement = document.querySelector('.user-progress');
        if (progressElement && totalSearches < nextMilestone) {
            const progress = (totalSearches / nextMilestone) * 100;
            
            progressElement.innerHTML = `
                <div style="margin-top: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <span style="font-size: 0.75rem; color: var(--text-secondary);">Progress to next level</span>
                        <span style="font-size: 0.75rem; color: var(--text-secondary);">${totalSearches}/${nextMilestone}</span>
                    </div>
                    <div style="background: var(--bg-secondary); height: 4px; border-radius: 2px; overflow: hidden;">
                        <div class="progress-bar" style="background: var(--accent-gradient); height: 100%; width: 0%; transition: width 1s ease;"></div>
                    </div>
                </div>
            `;
            
            // Animate progress bar
            setTimeout(() => {
                const progressBar = progressElement.querySelector('.progress-bar');
                if (progressBar) {
                    this.statsAnimator.animateProgressBar(progressBar, progress);
                }
            }, 500);
        }
    }

    updateAchievements(achievements) {
        const achievementsContainer = document.querySelector('.user-achievements');
        if (!achievementsContainer || !achievements) return;

        const achievementsHTML = achievements.map(achievement => `
            <div class="achievement-item ${achievement.unlocked ? 'unlocked' : 'locked'}" 
                 data-tooltip="${achievement.description}">
                <div class="achievement-icon">
                    <i class="${achievement.icon}"></i>
                </div>
                <div class="achievement-info">
                    <div class="achievement-title">${achievement.title}</div>
                    ${achievement.progress ? `
                        <div class="achievement-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${(achievement.progress / achievement.target) * 100}%"></div>
                            </div>
                            <span class="progress-text">${achievement.progress}/${achievement.target}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        achievementsContainer.innerHTML = achievementsHTML;
    }

    async updateCharts(analyticsData) {
        if (!analyticsData) return;
        
        // Activity chart
        if (analyticsData.daily_activity && analyticsData.daily_activity.length > 0) {
            await this.chartManager.createActivityChart('userActivityChart', analyticsData.daily_activity);
        }
        
        // Hourly activity chart
        if (analyticsData.hourly_activity) {
            await this.chartManager.createHourlyChart('userHourlyChart', analyticsData.hourly_activity);
        }
        
        // Score distribution chart
        if (analyticsData.score_distribution) {
            await this.chartManager.createDistributionChart('scoreDistributionChart', analyticsData.score_distribution);
        }
    }

    updateLastUpdateTime() {
        const timeElements = document.querySelectorAll('.last-updated-time, #lastUpdated');
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-IN', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
        
        timeElements.forEach(element => {
            element.textContent = timeString;
        });
    }

    setupEventListeners() {
        // Refresh button
        const refreshButtons = document.querySelectorAll('.refresh-btn, [data-action="refresh"]');
        refreshButtons.forEach(btn => {
            btn.addEventListener('click', () => this.refreshData());
        });
        
        // Search completion event
        window.addEventListener('searchCompleted', () => {
            setTimeout(() => {
                this.refreshData();
            }, 2000);
        });
        
        // Dashboard data refresh event
        window.addEventListener('dashboardDataRefreshed', (e) => {
            this.updateDashboardUI(e.detail.userStats, e.detail.analyticsData);
        });
        
        // Visibility change (refresh when tab becomes visible)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && window.GST_DASHBOARD.state.initialized) {
                this.refreshData();
            }
        });
    }

    setupAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            if (!document.hidden) {
                this.refreshData();
            }
        }, window.GST_DASHBOARD.CONFIG.REFRESH_INTERVAL);
        
        window.GST_DASHBOARD.state.refreshTimer = this.refreshTimer;
    }

    async refreshData() {
        try {
            window.GST_DASHBOARD.utils.log('Refreshing dashboard data...');
            
            const { userStats, analyticsData } = await this.dataManager.refreshAllData();
            await this.updateDashboardUI(userStats, analyticsData);
            
            // Show refresh notification
            if (window.notificationManager) {
                window.notificationManager.showSuccess('📊 Dashboard refreshed', 2000);
            }
            
        } catch (error) {
            window.GST_DASHBOARD.utils.error('Dashboard refresh failed:', error);
        }
    }

    showLoadingState() {
        const loadingElements = document.querySelectorAll('.dashboard-loading');
        loadingElements.forEach(el => el.style.display = 'block');
        
        const contentElements = document.querySelectorAll('.dashboard-content');
        contentElements.forEach(el => el.style.opacity = '0.5');
    }

    hideLoadingState() {
        const loadingElements = document.querySelectorAll('.dashboard-loading');
        loadingElements.forEach(el => el.style.display = 'none');
        
        const contentElements = document.querySelectorAll('.dashboard-content');
        contentElements.forEach(el => el.style.opacity = '1');
    }

    destroy() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        this.chartManager.destroyAllCharts();
        window.GST_DASHBOARD.state.initialized = false;
    }
}

// =====================================================
// 6. INITIALIZATION & EXPORTS
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on pages with dashboard elements
    const hasDashboardElements = document.querySelector('[data-stat-type], [data-user-stat], .user-achievements, canvas[id*="Chart"]');
    
    if (!hasDashboardElements || window.GST_DASHBOARD.state.initialized) {
        return;
    }

    try {
        // Initialize dashboard controller
        window.GST_DASHBOARD.controller = new DashboardController();
        window.GST_DASHBOARD.controller.initialize();
        
        // Add required CSS if not present
        if (!document.getElementById('dashboard-styles')) {
            const style = document.createElement('style');
            style.id = 'dashboard-styles';
            style.textContent = `
                .achievement-item {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.75rem;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                    border: 1px solid var(--border-color);
                }
                
                .achievement-item.unlocked {
                    background: rgba(16, 185, 129, 0.1);
                    border-color: var(--success);
                }
                
                .achievement-item.locked {
                    background: var(--bg-secondary);
                    opacity: 0.6;
                }
                
                .achievement-icon {
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.2rem;
                    color: var(--success);
                }
                
                .achievement-item.locked .achievement-icon {
                    color: var(--text-muted);
                }
                
                .achievement-info {
                    flex: 1;
                    min-width: 0;
                }
                
                .achievement-title {
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: var(--text-primary);
                    margin-bottom: 0.25rem;
                }
                
                .achievement-progress {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                
                .achievement-progress .progress-bar {
                    flex: 1;
                    height: 4px;
                    background: var(--bg-hover);
                    border-radius: 2px;
                    overflow: hidden;
                }
                
                .achievement-progress .progress-fill {
                    height: 100%;
                    background: var(--accent-gradient);
                    transition: width 1s ease;
                }
                
                .achievement-progress .progress-text {
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                    white-space: nowrap;
                }
                
                .dashboard-loading {
                    display: none;
                    text-align: center;
                    color: var(--text-secondary);
                    padding: 2rem;
                }
                
                .dashboard-content {
                    transition: opacity 0.3s ease;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                .loading-pulse {
                    animation: pulse 1.5s ease-in-out infinite;
                }
            `;
            document.head.appendChild(style);
        }
        
        window.GST_DASHBOARD.utils.log('Dashboard module initialized successfully');
        
    } catch (error) {
        window.GST_DASHBOARD.utils.error('Dashboard initialization failed:', error);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.GST_DASHBOARD.controller) {
        window.GST_DASHBOARD.controller.destroy();
    }
});

// Export global functions
window.refreshDashboard = function() {
    if (window.GST_DASHBOARD.controller) {
        return window.GST_DASHBOARD.controller.refreshData();
    }
};

window.getDashboardStats = function() {
    return window.GST_DASHBOARD.state.userStats;
};

console.log('✅ GST Dashboard Module Loaded Successfully!');