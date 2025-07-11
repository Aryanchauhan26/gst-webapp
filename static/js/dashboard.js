// Enhanced User Dashboard Component
// Add this to your common-scripts.js or create a separate dashboard.js file

class UserDashboard {
    constructor() {
        this.userStats = null;
        this.charts = {};
        this.init();
    }

    async init() {
        await this.loadUserStats();
        this.updateUserProfile();
        this.initializeCharts();
        this.setupRealTimeUpdates();
        
        console.log('Enhanced user dashboard initialized');
    }

    async loadUserStats() {
        try {
            const response = await fetch('/api/user/stats');
            const result = await response.json();
            
            if (result.success) {
                this.userStats = result.data;
                this.updateQuickStats();
                this.updateAchievements();
            }
        } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    updateUserProfile() {
        const userStatsElements = {
            searchCount: document.getElementById('userSearchCount'),
            avgScore: document.getElementById('userAvgScore'),
            userLevel: document.querySelector('.user-level'),
            userProgress: document.querySelector('.user-progress')
        };

        if (this.userStats) {
            // Update dropdown stats
            if (userStatsElements.searchCount) {
                this.animateNumber(userStatsElements.searchCount, 0, this.userStats.total_searches, 800);
            }
            
            if (userStatsElements.avgScore) {
                this.animateNumber(userStatsElements.avgScore, 0, Math.round(this.userStats.avg_compliance), 1000, '%');
            }

            // Update user level display
            if (userStatsElements.userLevel) {
                const level = this.userStats.user_level;
                userStatsElements.userLevel.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                        <i class="${level.icon}" style="color: ${level.color};"></i>
                        <span style="color: ${level.color}; font-weight: 600;">${level.level}</span>
                    </div>
                `;
            }

            // Update progress indicators
            this.updateUserProgress();
        }
    }

    updateUserProgress() {
        const level = this.userStats?.user_level;
        const totalSearches = this.userStats?.total_searches || 0;
        
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
                        <div style="background: var(--accent-gradient); height: 100%; width: ${progress}%; transition: width 1s ease;"></div>
                    </div>
                </div>
            `;
        }
    }

    updateQuickStats() {
        const statsElements = document.querySelectorAll('[data-user-stat]');
        
        statsElements.forEach(element => {
            const statType = element.getAttribute('data-user-stat');
            let value = 0;
            
            switch (statType) {
                case 'total-searches':
                    value = this.userStats.total_searches;
                    break;
                case 'unique-companies':
                    value = this.userStats.unique_companies;
                    break;
                case 'avg-compliance':
                    value = Math.round(this.userStats.avg_compliance);
                    break;
                case 'recent-searches':
                    value = this.userStats.recent_searches;
                    break;
            }
            
            this.animateNumber(element, 0, value, 1000, statType === 'avg-compliance' ? '%' : '');
        });
    }

    updateAchievements() {
        const achievementsContainer = document.querySelector('.user-achievements');
        if (!achievementsContainer || !this.userStats.achievements) return;

        const achievementsHTML = this.userStats.achievements.map(achievement => `
            <div class="achievement-item ${achievement.unlocked ? 'unlocked' : 'locked'}" 
                 data-tooltip="${achievement.description}${achievement.progress ? ` (${achievement.progress}/${achievement.target})` : ''}">
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

    async initializeCharts() {
        try {
            const response = await fetch('/api/user/activity?days=30');
            const result = await response.json();
            
            if (result.success) {
                this.createActivityChart(result.data.daily_activity);
                this.createHourlyChart(result.data.hourly_activity);
            }
        } catch (error) {
            console.error('Error loading activity data:', error);
        }
    }

    createActivityChart(dailyData) {
        const canvas = document.getElementById('userActivityChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.charts.activity) {
            this.charts.activity.destroy();
        }

        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dailyData.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
                datasets: [{
                    label: 'Daily Searches',
                    data: dailyData.map(d => d.searches),
                    borderColor: '#7c3aed',
                    backgroundColor: 'rgba(124, 58, 237, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#7c3aed',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 26, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#a1a1aa',
                        borderColor: '#7c3aed',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            title: function(context) {
                                return `${context[0].label}`;
                            },
                            label: function(context) {
                                return `${context.parsed.y} searches`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(39, 39, 42, 0.3)'
                        },
                        ticks: {
                            color: '#a1a1aa'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#a1a1aa'
                        },
                        grid: {
                            color: 'rgba(39, 39, 42, 0.3)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    createHourlyChart(hourlyData) {
        const canvas = document.getElementById('userHourlyChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.hourly) {
            this.charts.hourly.destroy();
        }

        // Fill missing hours with 0
        const fullHourlyData = Array.from({ length: 24 }, (_, i) => {
            const hourData = hourlyData.find(h => h.hour === i);
            return hourData ? hourData.searches : 0;
        });

        this.charts.hourly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Array.from({ length: 24 }, (_, i) => i === 0 ? '12 AM' : i === 12 ? '12 PM' : i < 12 ? `${i} AM` : `${i - 12} PM`),
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
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 26, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#a1a1aa',
                        borderColor: '#7c3aed',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#a1a1aa',
                            maxRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#a1a1aa'
                        },
                        grid: {
                            color: 'rgba(39, 39, 42, 0.3)'
                        }
                    }
                }
            }
        });
    }

    setupRealTimeUpdates() {
        // Update stats every 5 minutes
        setInterval(() => {
            this.loadUserStats();
        }, 5 * 60 * 1000);

        // Listen for search completion events
        document.addEventListener('searchCompleted', () => {
            setTimeout(() => {
                this.loadUserStats();
            }, 1000);
        });
    }

    animateNumber(element, start, end, duration, suffix = '') {
        const startTime = performance.now();
        const difference = end - start;
        
        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (difference * progress));
            
            element.textContent = current + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        
        requestAnimationFrame(step);
    }

    async refreshData() {
        await this.loadUserStats();
        await this.initializeCharts();
        notificationManager.showToast('Dashboard data refreshed', 'success', 2000);
    }
}

// Enhanced User Profile Manager
class UserProfileManager {
    constructor() {
        this.preferences = null;
        this.init();
    }

    async init() {
        await this.loadPreferences();
        this.setupProfileDropdown();
        this.setupAvatarGeneration();
        
        console.log('Enhanced user profile manager initialized');
    }

    async loadPreferences() {
        try {
            const response = await fetch('/api/user/preferences');
            const result = await response.json();
            
            if (result.success) {
                this.preferences = result.data;
                this.applyPreferences();
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    applyPreferences() {
        if (!this.preferences) return;

        // Apply theme
        if (this.preferences.theme !== themeManager.currentTheme) {
            themeManager.setTheme(this.preferences.theme, false);
        }

        // Apply compact mode
        if (this.preferences.compactMode) {
            document.body.classList.add('compact-mode');
        }

        // Store in localStorage for client-side access
        localStorage.setItem(GST_CONFIG.USER_PREFERENCES_KEY, JSON.stringify(this.preferences));
    }

    setupProfileDropdown() {
        const profileBtn = document.getElementById('userProfileBtn');
        const dropdownMenu = document.getElementById('userDropdownMenu');
        
        if (!profileBtn || !dropdownMenu) return;

        // Enhanced dropdown with animations
        profileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-profile-wrapper')) {
                this.closeDropdown();
            }
        });

        // Add keyboard navigation
        dropdownMenu.addEventListener('keydown', (e) => {
            const items = dropdownMenu.querySelectorAll('.dropdown-item');
            const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                    items[nextIndex].focus();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                    items[prevIndex].focus();
                    break;
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    document.activeElement.click();
                    break;
            }
        });
    }

    toggleDropdown() {
        const btn = document.getElementById('userProfileBtn');
        const menu = document.getElementById('userDropdownMenu');
        
        const isActive = btn.classList.contains('active');
        
        if (isActive) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }

    openDropdown() {
        const btn = document.getElementById('userProfileBtn');
        const menu = document.getElementById('userDropdownMenu');
        
        btn.classList.add('active');
        menu.classList.add('active');
        
        // Focus first focusable element
        setTimeout(() => {
            const firstFocusable = menu.querySelector('.dropdown-item');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        }, 100);
        
        // Load fresh stats
        if (window.userDashboard) {
            window.userDashboard.loadUserStats();
        }
    }

    closeDropdown() {
        const btn = document.getElementById('userProfileBtn');
        const menu = document.getElementById('userDropdownMenu');
        
        btn.classList.remove('active');
        menu.classList.remove('active');
        
        // Return focus to button
        btn.focus();
    }

    setupAvatarGeneration() {
        const avatarElements = document.querySelectorAll('.user-avatar, .dropdown-avatar');
        const userName = document.querySelector('.user-name')?.textContent || 'User';
        
        avatarElements.forEach(avatar => {
            // Generate gradient based on username
            const colors = this.generateAvatarColors(userName);
            avatar.style.background = `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`;
            
            // Add hover effect
            avatar.addEventListener('mouseenter', () => {
                avatar.style.transform = 'scale(1.1) rotate(5deg)';
            });
            
            avatar.addEventListener('mouseleave', () => {
                avatar.style.transform = 'scale(1) rotate(0deg)';
            });
        });
    }

    generateAvatarColors(name) {
        const colors = [
            { primary: '#7c3aed', secondary: '#a855f7' },
            { primary: '#3b82f6', secondary: '#60a5fa' },
            { primary: '#10b981', secondary: '#34d399' },
            { primary: '#f59e0b', secondary: '#fbbf24' },
            { primary: '#ef4444', secondary: '#f87171' },
            { primary: '#8b5cf6', secondary: '#a78bfa' },
            { primary: '#06b6d4', secondary: '#22d3ee' },
            { primary: '#84cc16', secondary: '#a3e635' }
        ];
        
        const hash = name.split('').reduce((a, b) => {
            a = ((a << 5) - a) + b.charCodeAt(0);
            return a & a;
        }, 0);
        
        return colors[Math.abs(hash) % colors.length];
    }

    async updateProfile(profileData) {
        try {
            const response = await fetch('/api/user/preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(profileData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.preferences = { ...this.preferences, ...profileData };
                this.applyPreferences();
                return true;
            }
        } catch (error) {
            console.error('Error updating profile:', error);
        }
        
        return false;
    }

    async clearUserData() {
        if (!confirm('Are you sure you want to clear all your search history? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/user/data', {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                notificationManager.showToast(`Cleared ${result.deleted_count} search records`, 'success');
                
                // Refresh dashboard
                if (window.userDashboard) {
                    setTimeout(() => {
                        window.userDashboard.refreshData();
                    }, 1000);
                }
            } else {
                notificationManager.showToast('Failed to clear data', 'error');
            }
        } catch (error) {
            console.error('Error clearing data:', error);
            notificationManager.showToast('Failed to clear data', 'error');
        }
    }
}

// Initialize enhanced user components
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on pages with user profile
    if (document.getElementById('userProfileBtn')) {
        window.userDashboard = new UserDashboard();
        window.userProfileManager = new UserProfileManager();
        
        // Add achievement styles
        const achievementStyles = `
            <style>
                .user-achievements {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                    margin-top: 1rem;
                }

                .achievement-item {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.5rem;
                    border-radius: 8px;
                    transition: all 0.2s;
                }

                .achievement-item.unlocked {
                    background: rgba(16, 185, 129, 0.1);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                }

                .achievement-item.locked {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-color);
                    opacity: 0.6;
                }

                .achievement-icon {
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                }

                .achievement-item.unlocked .achievement-icon {
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
                    font-size: 0.8rem;
                    font-weight: 600;
                    color: var(--text-primary);
                    margin-bottom: 0.25rem;
                }

                .achievement-progress {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }

                .progress-bar {
                    flex: 1;
                    height: 4px;
                    background: var(--bg-hover);
                    border-radius: 2px;
                    overflow: hidden;
                }

                .progress-fill {
                    height: 100%;
                    background: var(--accent-gradient);
                    transition: width 1s ease;
                }

                .progress-text {
                    font-size: 0.7rem;
                    color: var(--text-secondary);
                    white-space: nowrap;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', achievementStyles);
    }
});

// Export functions for global access
window.openEnhancedProfileModal = function() {
    const userData = window.userDashboard?.userStats;
    
    modalManager.createModal({
        title: 'My Profile & Stats',
        content: `
            <div style="display: flex; flex-direction: column; gap: 2rem;">
                <!-- User Stats Overview -->
                <div style="background: var(--bg-hover); border-radius: 12px; padding: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-primary);">Your Activity</h4>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);">${userData?.total_searches || 0}</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">Total Searches</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);">${Math.round(userData?.avg_compliance || 0)}%</div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary);">Avg Compliance</div>
                        </div>
                    </div>
                </div>
                
                <!-- Profile Form -->
                <form id="enhancedProfileForm">
                    <div style="display: flex; flex-direction: column; gap: 1rem;">
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Display Name</label>
                            <input type="text" name="displayName" class="form-input" placeholder="Enter your name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">Company</label>
                            <input type="text" name="company" class="form-input" placeholder="Company name" style="width: 100%; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 500;">User Level</label>
                            <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px;">
                                <i class="${userData?.user_level?.icon || 'fas fa-user'}" style="color: ${userData?.user_level?.color || 'var(--accent-primary)'};"></i>
                                <span style="color: var(--text-primary); font-weight: 600;">${userData?.user_level?.level || 'New User'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                        <button type="submit" class="btn btn-primary" style="flex: 1; padding: 0.75rem; background: var(--accent-gradient); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Save Profile</button>
                        <button type="button" onclick="window.userProfileManager.clearUserData(); modalManager.closeAllModals();" class="btn btn-danger" style="padding: 0.75rem 1rem; background: var(--danger); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Clear Data</button>
                    </div>
                </form>
            </div>
        `,
        onSubmit: async function(formData) {
            const success = await window.userProfileManager.updateProfile(formData);
            if (success) {
                notificationManager.showToast('Profile updated successfully!', 'success');
                return true;
            } else {
                notificationManager.showToast('Failed to update profile', 'error');
                return false;
            }
        }
    });
};