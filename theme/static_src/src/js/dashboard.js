/**
 * Dashboard functionality for TPS Application
 * Handles dashboard data management and interactions
 */

// Alpine.js Dashboard Data
function dashboardData() {
    return {
        stats: {
            myShifts: window.dashboardStats?.myShifts || 0,
            pendingApprovals: window.dashboardStats?.pendingApprovals || 0,
            activeMembers: window.dashboardStats?.activeMembers || 0,
            monthlyAssignments: window.dashboardStats?.monthlyAssignments || 0,
            systemHealth: window.dashboardStats?.systemHealth || 0,
            fairnessScore: window.dashboardStats?.fairnessScore || 0
        },
        
        // Computed property for fairness card classes
        get fairnessCardClasses() {
            const score = this.stats.fairnessScore;
            if (score >= 90) {
                return 'bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-emerald-500/30 hover:shadow-xl hover:shadow-emerald-500/40';
            } else if (score >= 75) {
                return 'bg-gradient-to-br from-amber-500 to-amber-600 shadow-amber-500/30 hover:shadow-xl hover:shadow-amber-500/40';
            } else {
                return 'bg-gradient-to-br from-red-500 to-red-600 shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/40';
            }
        },
        
        // Quick Action Functions converted to Alpine methods
        openPlanningWizard() {
            window.location.href = '/planning/';
        },

        openQuickAssign() {
            this.$dispatch('show-notification', { 
                message: window.translations?.quickAssignSoon || 'Quick assign functionality coming soon!', 
                type: 'info' 
            });
        },

        showPendingApprovals() {
            this.$dispatch('show-notification', { 
                message: window.translations?.viewingPending || 'Viewing pending approvals...', 
                type: 'info' 
            });
        },

        exportSchedule() {
            this.$dispatch('show-notification', { 
                message: window.translations?.exportingSchedule || 'Exporting schedule...', 
                type: 'info' 
            });
        },

        // Assignment approval functions with proper Alpine.js patterns
        async approveAssignment(assignmentId) {
            const confirmMessage = window.translations?.confirmApprove || 'Are you sure you want to approve this assignment?';
            if (confirm(confirmMessage)) {
                const button = document.querySelector(`[data-assignment-id="${assignmentId}"][data-action="approve"]`);
                const resetLoading = button ? window.showLoadingState(button, window.translations?.approving || 'Approving...') : null;

                try {
                    const data = await window.TPS.utils.apiCall(`/api/v1/assignments/${assignmentId}/approve_assignment/`, {
                        method: 'POST'
                    });
                    
                    this.$dispatch('show-notification', { 
                        message: window.translations?.assignmentApproved || 'Assignment approved successfully!', 
                        type: 'success' 
                    });
                    
                    // Update stats
                    this.stats.pendingApprovals = Math.max(0, this.stats.pendingApprovals - 1);
                    
                    // Optionally reload page for full refresh
                    setTimeout(() => location.reload(), 1500);
                } catch (error) {
                    console.error('Error approving assignment:', error);
                } finally {
                    if (resetLoading) resetLoading();
                }
            }
        },

        async declineAssignment(assignmentId) {
            const reason = prompt(window.translations?.declineReason || 'Please provide a reason for declining (optional):');
            if (reason !== null) { // User didn't cancel
                const button = document.querySelector(`[data-assignment-id="${assignmentId}"][data-action="decline"]`);
                const resetLoading = button ? window.showLoadingState(button, window.translations?.declining || 'Declining...') : null;

                try {
                    const data = await window.TPS.utils.apiCall(`/api/v1/assignments/${assignmentId}/reject_assignment/`, {
                        method: 'POST',
                        body: JSON.stringify({
                            reason: reason || (window.translations?.noReasonProvided || 'No reason provided')
                        })
                    });
                    
                    this.$dispatch('show-notification', { 
                        message: window.translations?.assignmentDeclined || 'Assignment declined successfully!', 
                        type: 'success' 
                    });
                    
                    // Update stats
                    this.stats.pendingApprovals = Math.max(0, this.stats.pendingApprovals - 1);
                    
                    // Optionally reload page for full refresh
                    setTimeout(() => location.reload(), 1500);
                } catch (error) {
                    console.error('Error declining assignment:', error);
                } finally {
                    if (resetLoading) resetLoading();
                }
            }
        },

        // Real-time dashboard updates
        async updateDashboardStats() {
            try {
                const data = await window.TPS.utils.apiCall('/api/v1/dashboard/stats/');
                
                // Update stats reactively
                this.stats = {
                    myShifts: data.my_upcoming_shifts,
                    pendingApprovals: data.pending_approvals,
                    activeMembers: data.active_members,
                    monthlyAssignments: data.monthly_assignments,
                    systemHealth: data.system_health,
                    fairnessScore: data.fairness_score
                };
            } catch (error) {
                console.error('Error updating dashboard stats:', error);
            }
        },

        // Initialize dashboard
        init() {
            // Update dashboard stats every 30 seconds
            const updateInterval = setInterval(() => this.updateDashboardStats(), 30000);
            
            // Cleanup on component destroy
            this.$el.addEventListener('x-destroy', () => {
                clearInterval(updateInterval);
            });
            
            // Listen for custom notifications
            this.$watch('$store.notifications', (notifications) => {
                // Handle notifications if needed
            });
        }
    }
}

// Make function globally available
window.dashboardData = dashboardData;