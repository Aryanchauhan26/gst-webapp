// /static/js/dashboard.js - Complete Dashboard Functionality
"use strict";

console.log("📊 Loading dashboard functionality...");

// =============================================================================
// 1. GLOBAL DASHBOARD CONFIGURATION
// =============================================================================
window.GST_DASHBOARD = {
    CONFIG: {
        CACHE_DURATION: 5 * 60 * 1000, // 5 minutes
        CHART_ANIMATION_DURATION: 1000,
        REFRESH_INTERVAL: 30 * 1000, // 30 seconds
        DEBOUNCE_DELAY: 300,
        MAX_RETRY_ATTEMPTS: 3,
    },

    state: {
        isInitialized: false,
        currentUser: null,
        userStats: null,
        analyticsData: null,
        lastRefresh: null,
        activeCharts: new Map(),
        refreshInterval: null,
    },

    utils: {
        log: (message, ...args) =>
            console.log(`[Dashboard] ${message}`, ...args),
        error: (message, ...args) =>
            console.error(`[Dashboard] ${message}`, ...args),
        warn: (message, ...args) =>
            console.warn(`[Dashboard] ${message}`, ...args),
    },
};

// =============================================================================
// 2. DASHBOARD MANAGER
// =============================================================================
class DashboardManager {
    constructor() {
        this.cache = new Map();
        this.isLoading = false;
        this.retryCount = 0;
        this.refreshTimer = null;
    }

    async init() {
        if (window.GST_DASHBOARD.state.isInitialized) {
            window.GST_DASHBOARD.utils.warn("Dashboard already initialized");
            return;
        }

        try {
            window.GST_DASHBOARD.utils.log("Initializing dashboard...");

            // Get current user from global state
            window.GST_DASHBOARD.state.currentUser =
                window.GST_APP_STATE?.currentUser;

            if (!window.GST_DASHBOARD.state.currentUser) {
                throw new Error("User not authenticated");
            }

            // Load initial data
            await this.loadDashboardData();

            // Initialize charts
            await this.initializeCharts();

            // Set up event listeners
            this.setupEventListeners();

            // Start auto-refresh
            this.startAutoRefresh();

            window.GST_DASHBOARD.state.isInitialized = true;
            window.GST_DASHBOARD.utils.log(
                "Dashboard initialized successfully",
            );
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Dashboard initialization failed:",
                error,
            );
            window.GSTPlatform?.errorHandler?.handleAPIError(error, {
                context: "dashboard_init",
            });
        }
    }

    async loadDashboardData() {
        if (this.isLoading) {
            window.GST_DASHBOARD.utils.warn("Data loading already in progress");
            return;
        }

        try {
            this.isLoading = true;
            const loaderId = window.loadingManager?.show("dashboard-data");

            window.GST_DASHBOARD.utils.log("Loading dashboard data...");

            // Load user stats and analytics in parallel
            const [userStats, analyticsData] = await Promise.all([
                this.fetchUserStats(),
                this.fetchAnalyticsData(),
            ]);

            // Update state
            window.GST_DASHBOARD.state.userStats = userStats;
            window.GST_DASHBOARD.state.analyticsData = analyticsData;
            window.GST_DASHBOARD.state.lastRefresh = new Date();

            // Update UI
            this.updateStatsDisplay(userStats);
            this.updateRecentActivity();

            // Trigger custom event
            window.dispatchEvent(
                new CustomEvent("dashboardDataLoaded", {
                    detail: { userStats, analyticsData },
                }),
            );

            this.retryCount = 0; // Reset retry count on success

            if (loaderId) {
                window.loadingManager?.hide(loaderId);
            }

            window.GST_DASHBOARD.utils.log(
                "Dashboard data loaded successfully",
            );
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to load dashboard data:",
                error,
            );

            if (
                this.retryCount < window.GST_DASHBOARD.CONFIG.MAX_RETRY_ATTEMPTS
            ) {
                this.retryCount++;
                window.GST_DASHBOARD.utils.log(
                    `Retrying data load (${this.retryCount}/${window.GST_DASHBOARD.CONFIG.MAX_RETRY_ATTEMPTS})...`,
                );

                setTimeout(() => {
                    this.loadDashboardData();
                }, 2000 * this.retryCount); // Exponential backoff
            } else {
                window.GSTPlatform?.errorHandler?.handleAPIError(error, {
                    context: "dashboard_data",
                });
            }
        } finally {
            this.isLoading = false;
        }
    }

    async fetchUserStats() {
        const cacheKey = "user_stats";
        const cached = this.getFromCache(cacheKey);

        if (cached) {
            window.GST_DASHBOARD.utils.log("Using cached user stats");
            return cached;
        }

        try {
            const response = await fetch("/api/user/stats", {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            const data = await response.json();
            this.setCache(cacheKey, data);

            return data;
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to fetch user stats:",
                error,
            );

            // Return default stats on error
            return this.getDefaultStats();
        }
    }

    async fetchAnalyticsData() {
        const cacheKey = "analytics_data";
        const cached = this.getFromCache(cacheKey);

        if (cached) {
            window.GST_DASHBOARD.utils.log("Using cached analytics data");
            return cached;
        }

        try {
            const response = await fetch("/api/analytics/dashboard", {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            const data = await response.json();
            this.setCache(cacheKey, data);

            return data;
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to fetch analytics data:",
                error,
            );

            // Return default analytics data on error
            return this.getDefaultAnalyticsData();
        }
    }

    updateStatsDisplay(stats) {
        try {
            // Update stat cards
            const statElements = {
                totalSearches: document.getElementById("total-searches"),
                uniqueCompanies: document.getElementById("unique-companies"),
                avgCompliance: document.getElementById("avg-compliance"),
                recentSearches: document.getElementById("recent-searches"),
            };

            if (statElements.totalSearches) {
                statElements.totalSearches.textContent =
                    window.utils?.formatNumber(stats.total_searches) ||
                    stats.total_searches ||
                    "0";
            }

            if (statElements.uniqueCompanies) {
                statElements.uniqueCompanies.textContent =
                    window.utils?.formatNumber(stats.unique_companies) ||
                    stats.unique_companies ||
                    "0";
            }

            if (statElements.avgCompliance) {
                const avgScore = stats.avg_compliance || 0;
                statElements.avgCompliance.textContent = `${Math.round(avgScore)}%`;

                // Update compliance score color
                const scoreElement = statElements.avgCompliance.closest(
                    ".stat-card-enhanced",
                );
                if (scoreElement) {
                    scoreElement.className = scoreElement.className.replace(
                        /compliance-\w+/,
                        "",
                    );
                    if (avgScore >= 80) {
                        scoreElement.classList.add("compliance-excellent");
                    } else if (avgScore >= 60) {
                        scoreElement.classList.add("compliance-good");
                    } else if (avgScore >= 40) {
                        scoreElement.classList.add("compliance-average");
                    } else {
                        scoreElement.classList.add("compliance-poor");
                    }
                }
            }

            if (statElements.recentSearches) {
                statElements.recentSearches.textContent =
                    window.utils?.formatNumber(stats.recent_searches) ||
                    stats.recent_searches ||
                    "0";
            }

            // Update user level if available
            if (stats.user_level) {
                const userLevelElement = document.getElementById("user-level");
                if (userLevelElement) {
                    userLevelElement.innerHTML = `
                        <i class="${stats.user_level.icon}" style="color: ${stats.user_level.color}"></i>
                        ${stats.user_level.level}
                    `;
                }
            }

            // Update last activity
            if (stats.last_search) {
                const lastActivityElement =
                    document.getElementById("last-activity");
                if (lastActivityElement) {
                    lastActivityElement.textContent =
                        window.utils?.formatRelativeTime(stats.last_search) ||
                        "Never";
                }
            }

            window.GST_DASHBOARD.utils.log("Stats display updated");
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to update stats display:",
                error,
            );
        }
    }

    updateRecentActivity() {
        try {
            const analyticsData = window.GST_DASHBOARD.state.analyticsData;
            if (!analyticsData || !analyticsData.top_companies) {
                return;
            }

            const activityContainer =
                document.getElementById("recent-activity");
            if (!activityContainer) {
                return;
            }

            const companies = analyticsData.top_companies.slice(0, 5); // Show only top 5

            if (companies.length === 0) {
                activityContainer.innerHTML = `
                    <div class="no-activity">
                        <i class="fas fa-search text-muted"></i>
                        <p class="text-muted">No recent searches</p>
                    </div>
                `;
                return;
            }

            activityContainer.innerHTML = companies
                .map(
                    (company) => `
                <div class="activity-item">
                    <div class="activity-info">
                        <div class="activity-company">${company.company_name || "Unknown Company"}</div>
                        <div class="activity-time">${window.utils?.formatRelativeTime(company.searched_at) || "Recently"}</div>
                    </div>
                    <div class="activity-score">
                        <span class="badge ${this.getScoreBadgeClass(company.compliance_score)}">
                            ${Math.round(company.compliance_score || 0)}%
                        </span>
                    </div>
                </div>
            `,
                )
                .join("");

            window.GST_DASHBOARD.utils.log("Recent activity updated");
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to update recent activity:",
                error,
            );
        }
    }

    getScoreBadgeClass(score) {
        if (score >= 80) return "badge--success";
        if (score >= 60) return "badge--info";
        if (score >= 40) return "badge--warning";
        return "badge--error";
    }

    async initializeCharts() {
        try {
            window.GST_DASHBOARD.utils.log("Initializing charts...");

            const chartManager = new ChartManager();
            await chartManager.ensureChartJS();

            const analyticsData = window.GST_DASHBOARD.state.analyticsData;
            if (!analyticsData) {
                window.GST_DASHBOARD.utils.warn(
                    "No analytics data available for charts",
                );
                return;
            }

            // Initialize mini charts on dashboard
            this.initMiniActivityChart(analyticsData.daily_searches || []);
            this.initMiniScoreChart(analyticsData.score_distribution || []);

            window.GST_DASHBOARD.utils.log("Charts initialized successfully");
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to initialize charts:",
                error,
            );
        }
    }

    initMiniActivityChart(data) {
        const canvas = document.getElementById("mini-activity-chart");
        if (!canvas || !window.Chart) {
            return;
        }

        try {
            // Destroy existing chart
            const existingChart =
                window.GST_DASHBOARD.state.activeCharts.get("mini-activity");
            if (existingChart) {
                existingChart.destroy();
            }

            const ctx = canvas.getContext("2d");
            const chart = new window.Chart(ctx, {
                type: "line",
                data: {
                    labels: data.map((item) => {
                        const date = new Date(item.date);
                        return date.toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                        });
                    }),
                    datasets: [
                        {
                            data: data.map((item) => item.count),
                            borderColor: "#7c3aed",
                            backgroundColor: "rgba(124, 58, 237, 0.1)",
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: "index",
                            intersect: false,
                            backgroundColor: "var(--bg-card)",
                            titleColor: "var(--text-primary)",
                            bodyColor: "var(--text-secondary)",
                            borderColor: "var(--border-primary)",
                            borderWidth: 1,
                        },
                    },
                    scales: {
                        x: { display: false },
                        y: { display: false },
                    },
                    interaction: {
                        intersect: false,
                        mode: "index",
                    },
                    animation: {
                        duration:
                            window.GST_DASHBOARD.CONFIG
                                .CHART_ANIMATION_DURATION,
                    },
                },
            });

            window.GST_DASHBOARD.state.activeCharts.set("mini-activity", chart);
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to create mini activity chart:",
                error,
            );
        }
    }

    initMiniScoreChart(data) {
        const canvas = document.getElementById("mini-score-chart");
        if (!canvas || !window.Chart) {
            return;
        }

        try {
            // Destroy existing chart
            const existingChart =
                window.GST_DASHBOARD.state.activeCharts.get("mini-score");
            if (existingChart) {
                existingChart.destroy();
            }

            const ctx = canvas.getContext("2d");
            const chart = new window.Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.map((item) => item.category),
                    datasets: [
                        {
                            data: data.map((item) => item.count),
                            backgroundColor: [
                                "#10b981", // Excellent - Green
                                "#3b82f6", // Good - Blue
                                "#f59e0b", // Average - Yellow
                                "#ef4444", // Poor - Red
                            ],
                            borderWidth: 0,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: "var(--bg-card)",
                            titleColor: "var(--text-primary)",
                            bodyColor: "var(--text-secondary)",
                            borderColor: "var(--border-primary)",
                            borderWidth: 1,
                        },
                    },
                    cutout: "60%",
                    animation: {
                        duration:
                            window.GST_DASHBOARD.CONFIG
                                .CHART_ANIMATION_DURATION,
                    },
                },
            });

            window.GST_DASHBOARD.state.activeCharts.set("mini-score", chart);
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to create mini score chart:",
                error,
            );
        }
    }

    setupEventListeners() {
        try {
            window.GST_DASHBOARD.utils.log("Setting up event listeners...");

            // Refresh button
            const refreshBtn = document.getElementById("refresh-dashboard");
            if (refreshBtn) {
                refreshBtn.addEventListener("click", () => {
                    this.handleRefreshClick();
                });
            }

            // Search form
            const searchForm = document.getElementById("gstin-search-form");
            if (searchForm) {
                searchForm.addEventListener("submit", (e) => {
                    this.handleSearchSubmit(e);
                });
            }

            // Quick actions
            const quickActions = document.querySelectorAll(
                "[data-quick-action]",
            );
            quickActions.forEach((action) => {
                action.addEventListener("click", (e) => {
                    this.handleQuickAction(e);
                });
            });

            // Window events
            window.addEventListener("focus", () => {
                // Refresh data when window gains focus
                if (this.shouldRefreshOnFocus()) {
                    this.loadDashboardData();
                }
            });

            // Custom events
            window.addEventListener("searchCompleted", (e) => {
                // Refresh dashboard after successful search
                setTimeout(() => {
                    this.loadDashboardData();
                }, 1000);
            });

            window.GST_DASHBOARD.utils.log(
                "Event listeners set up successfully",
            );
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to set up event listeners:",
                error,
            );
        }
    }

    async handleRefreshClick() {
        try {
            window.GST_DASHBOARD.utils.log("Manual refresh triggered");

            const refreshBtn = document.getElementById("refresh-dashboard");
            if (refreshBtn) {
                refreshBtn.classList.add("btn--loading");
                refreshBtn.disabled = true;
            }

            // Clear cache to force fresh data
            this.cache.clear();

            await this.loadDashboardData();

            // Update charts with new data
            await this.initializeCharts();

            window.notificationManager?.show(
                "Dashboard refreshed successfully",
                "success",
                3000,
            );
        } catch (error) {
            window.GST_DASHBOARD.utils.error(
                "Failed to refresh dashboard:",
                error,
            );
            window.notificationManager?.show(
                "Failed to refresh dashboard",
                "error",
            );
        } finally {
            const refreshBtn = document.getElementById("refresh-dashboard");
            if (refreshBtn) {
                refreshBtn.classList.remove("btn--loading");
                refreshBtn.disabled = false;
            }
        }
    }

    async handleSearchSubmit(e) {
        e.preventDefault();

        const formData = new FormData(e.target);
        const gstin = formData.get("gstin")?.trim();

        if (!gstin) {
            window.notificationManager?.show("Please enter a GSTIN", "warning");
            return;
        }

        // Validate GSTIN format
        const validation = window.formValidator?.validateGSTIN(gstin);
        if (!validation?.valid) {
            window.notificationManager?.show(
                validation?.message || "Invalid GSTIN format",
                "error",
            );
            return;
        }

        try {
            window.GST_DASHBOARD.utils.log(
                "Submitting search for GSTIN:",
                validation.value,
            );

            const submitBtn = e.target.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add("btn--loading");
                submitBtn.disabled = true;
            }

            const response = await fetch("/api/search", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: `gstin=${encodeURIComponent(validation.value)}`,
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.show(
                    "Search completed successfully",
                    "success",
                );

                // Trigger custom event
                window.dispatchEvent(
                    new CustomEvent("searchCompleted", {
                        detail: { gstin: validation.value, data: data.data },
                    }),
                );

                // Clear form
                e.target.reset();

                // Track analytics
                window.analytics?.trackSearch(validation.value, true);
            } else {
                throw new Error(data.error || "Search failed");
            }
        } catch (error) {
            window.GST_DASHBOARD.utils.error("Search failed:", error);
            window.notificationManager?.show(
                error.message || "Search failed",
                "error",
            );
            window.analytics?.trackSearch(gstin, false);
        } finally {
            const submitBtn = e.target.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.remove("btn--loading");
                submitBtn.disabled = false;
            }
        }
    }

    handleQuickAction(e) {
        const action = e.currentTarget.dataset.quickAction;

        switch (action) {
            case "view-history":
                window.location.href = "/history";
                break;
            case "view-analytics":
                window.location.href = "/analytics";
                break;
            case "export-data":
                this.handleExportData();
                break;
            case "clear-history":
                this.handleClearHistory();
                break;
            default:
                window.GST_DASHBOARD.utils.warn(
                    "Unknown quick action:",
                    action,
                );
        }
    }

    async handleExportData() {
        try {
            window.GST_DASHBOARD.utils.log("Exporting user data...");

            window.notificationManager?.show("Preparing export...", "info");

            const response = await fetch("/export/history", {
                method: "GET",
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `gst_search_history_${new Date().toISOString().split("T")[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            window.notificationManager?.show(
                "Data exported successfully",
                "success",
            );
            window.analytics?.trackEvent("Export", "History", "CSV");
        } catch (error) {
            window.GST_DASHBOARD.utils.error("Export failed:", error);
            window.notificationManager?.show("Export failed", "error");
        }
    }

    async handleClearHistory() {
        if (
            !confirm(
                "Are you sure you want to clear your search history? This action cannot be undone.",
            )
        ) {
            return;
        }

        try {
            window.GST_DASHBOARD.utils.log("Clearing user history...");

            const response = await fetch("/api/user/clear-history", {
                method: "DELETE",
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            // Refresh dashboard
            this.cache.clear();
            await this.loadDashboardData();
            await this.initializeCharts();

            window.notificationManager?.show(
                "History cleared successfully",
                "success",
            );
            window.analytics?.trackEvent("User", "Clear History");
        } catch (error) {
            window.GST_DASHBOARD.utils.error("Failed to clear history:", error);
            window.notificationManager?.show(
                "Failed to clear history",
                "error",
            );
        }
    }

    startAutoRefresh() {
        // Clear existing interval
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        this.refreshTimer = setInterval(() => {
            if (document.visibilityState === "visible") {
                this.loadDashboardData();
            }
        }, window.GST_DASHBOARD.CONFIG.REFRESH_INTERVAL);

        window.GST_DASHBOARD.utils.log("Auto-refresh started");
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
            window.GST_DASHBOARD.utils.log("Auto-refresh stopped");
        }
    }

    shouldRefreshOnFocus() {
        const lastRefresh = window.GST_DASHBOARD.state.lastRefresh;
        if (!lastRefresh) return true;

        const timeSinceRefresh = Date.now() - lastRefresh.getTime();
        return timeSinceRefresh > window.GST_DASHBOARD.CONFIG.CACHE_DURATION;
    }

    async refreshData() {
        try {
            // Clear cache and reload
            this.cache.clear();
            await this.loadDashboardData();

            // Dispatch refresh event
            window.dispatchEvent(
                new CustomEvent("dashboardDataRefreshed", {
                    detail: {
                        userStats: window.GST_DASHBOARD.state.userStats,
                        analyticsData: window.GST_DASHBOARD.state.analyticsData,
                    },
                }),
            );

            return {
                userStats: window.GST_DASHBOARD.state.userStats,
                analyticsData: window.GST_DASHBOARD.state.analyticsData,
            };
        } finally {
            this.isLoading = false;
        }
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;

        if (
            Date.now() - cached.timestamp >
            window.GST_DASHBOARD.CONFIG.CACHE_DURATION
        ) {
            this.cache.delete(key);
            return null;
        }

        return cached.data;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now(),
        });
    }

    getDefaultStats() {
        return {
            total_searches: 0,
            unique_companies: 0,
            avg_compliance: 0,
            recent_searches: 0,
            last_search: null,
            user_level: {
                level: "New User",
                icon: "fas fa-user-plus",
                color: "#6b7280",
            },
            achievements: [],
        };
    }

    getDefaultAnalyticsData() {
        return {
            daily_searches: [],
            score_distribution: [],
            top_companies: [],
        };
    }

    destroy() {
        // Stop auto-refresh
        this.stopAutoRefresh();

        // Destroy charts
        window.GST_DASHBOARD.state.activeCharts.forEach((chart) => {
            chart.destroy();
        });
        window.GST_DASHBOARD.state.activeCharts.clear();

        // Clear cache
        this.cache.clear();

        // Reset state
        window.GST_DASHBOARD.state.isInitialized = false;

        window.GST_DASHBOARD.utils.log("Dashboard destroyed");
    }
}

// =============================================================================
// 3. CHART MANAGER
// =============================================================================
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
            const script = document.createElement("script");
            script.src =
                "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.min.js";
            script.onload = () => {
                this.chartJS = window.Chart;
                this.configureDefaults();
                window.GST_DASHBOARD.utils.log("Chart.js loaded successfully");
                resolve(this.chartJS);
            };
            script.onerror = () => {
                window.GST_DASHBOARD.utils.error("Failed to load Chart.js");
                reject(new Error("Failed to load Chart.js"));
            };
            document.head.appendChild(script);
        });
    }

    configureDefaults() {
        if (!this.chartJS) return;

        this.chartJS.defaults.color = "var(--text-secondary)";
        this.chartJS.defaults.borderColor = "var(--border-color)";
        this.chartJS.defaults.backgroundColor = "rgba(124, 58, 237, 0.1)";
        this.chartJS.defaults.plugins.legend.display = false;
        this.chartJS.defaults.responsive = true;
        this.chartJS.defaults.maintainAspectRatio = false;
        this.chartJS.defaults.animation.duration =
            window.GST_DASHBOARD.CONFIG.CHART_ANIMATION_DURATION;
    }
}

// =============================================================================
// 4. INITIALIZATION
// =============================================================================
let dashboardManager = null;

document.addEventListener("DOMContentLoaded", async function () {
    try {
        window.GST_DASHBOARD.utils.log("DOM loaded, initializing dashboard...");

        // Check if user is authenticated
        if (!window.GST_APP_STATE?.isAuthenticated) {
            window.GST_DASHBOARD.utils.warn(
                "User not authenticated, skipping dashboard initialization",
            );
            return;
        }

        // Initialize dashboard manager
        dashboardManager = new DashboardManager();
        await dashboardManager.init();

        // Make dashboard manager globally available
        window.dashboardManager = dashboardManager;

        window.GST_DASHBOARD.utils.log("Dashboard ready");
    } catch (error) {
        window.GST_DASHBOARD.utils.error(
            "Failed to initialize dashboard:",
            error,
        );
    }
});

// Cleanup on page unload
window.addEventListener("beforeunload", function () {
    if (dashboardManager) {
        dashboardManager.destroy();
    }
});

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
    module.exports = { DashboardManager, ChartManager };
}

console.log("✅ Dashboard functionality loaded successfully");
