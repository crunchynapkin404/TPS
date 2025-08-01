// Test the calendarData function syntax
console.log('Testing updated calendarData function syntax...');

try {
    // Simulate the complete calendarData function
    function calendarData() {
        return {
            // State
            currentDate: new Date(),
            selectedTeam: null,
            availableTeams: [],
            calendarData: null,
            availableUsers: [],
            assignmentTypes: [
                { value: 'waakdienst', label: '🛡️ Waakdienst' },
                { value: 'incident', label: '🚨 Incident Response' }
            ],
            isLoading: false,
            error: null,
            currentView: 'month',
            isInitialized: true,
            
            // Modals
            showAssignmentModal: false,
            isCreating: false,
            
            // Forms
            assignmentForm: {
                user_id: '',
                date: '',
                assignment_type: 'waakdienst',
                start_time: '09:00',
                end_time: '17:00',
                notes: '',
                team_id: 4
            },
            
            // Stats
            stats: {
                totalAssignments: 0,
                activeUsers: 0
            },
            
            // Configuration
            API_BASE: '/api/v1',
            CSRF_TOKEN: '',
            
            // Computed properties
            get currentPeriod() {
                return 'August 2025';
            },
            
            get weekDaysHeader() {
                return '<div>Loading...</div>';
            },
            
            get monthDaysHeader() {
                return '<div>Loading...</div>';
            },
            
            get monthUsersList() {
                return '<div>Loading...</div>';
            },
            
            get monthContent() {
                return '<div>Loading...</div>';
            },
            
            // Modal management
            openQuickAssignmentModal(userId = '', date = '') {
                console.log('Opening assignment modal');
                this.showAssignmentModal = true;
            },
            
            closeAssignmentModal() {
                console.log('Closing assignment modal');
                this.showAssignmentModal = false;
            },
            
            // Navigation methods
            selectTeam(team) {
                console.log('Selecting team:', team);
                this.selectedTeam = team;
            },
            
            switchView(view) {
                console.log('Switching to view:', view);
                this.currentView = view;
            },
            
            navigatePrevious() {
                console.log('Navigating to previous period');
                const currentDate = new Date(this.currentDate);
                if (this.currentView === 'month') {
                    currentDate.setMonth(currentDate.getMonth() - 1);
                } else {
                    currentDate.setDate(currentDate.getDate() - 7);
                }
                this.currentDate = currentDate;
            },
            
            navigateNext() {
                console.log('Navigating to next period');
                const currentDate = new Date(this.currentDate);
                if (this.currentView === 'month') {
                    currentDate.setMonth(currentDate.getMonth() + 1);
                } else {
                    currentDate.setDate(currentDate.getDate() + 7);
                }
                this.currentDate = currentDate;
            },
            
            goToToday() {
                console.log('Going to today');
                this.currentDate = new Date();
            },
            
            refreshCalendar() {
                console.log('Refreshing calendar');
                this.isLoading = true;
                return new Promise(resolve => {
                    setTimeout(() => {
                        this.isLoading = false;
                        console.log('Calendar refreshed');
                        resolve();
                    }, 1000);
                });
            },
            
            loadCalendar() {
                console.log('Loading calendar');
                this.isLoading = true;
                this.error = null;
                return new Promise(resolve => {
                    setTimeout(() => {
                        this.isLoading = false;
                        console.log('Calendar loaded');
                        resolve();
                    }, 1000);
                });
            },
            
            async createQuickAssignment() {
                console.log('Creating quick assignment');
                this.isCreating = true;
                
                try {
                    // Simulate API call
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    console.log('Assignment created successfully');
                    this.closeAssignmentModal();
                } catch (error) {
                    console.error('Failed to create assignment:', error);
                } finally {
                    this.isCreating = false;
                }
            },
            
            // Utility methods
            formatDate(date, format = 'short') {
                const d = new Date(date);
                return d.toLocaleDateString('en-GB');
            },
            
            isToday(dateString) {
                const today = new Date().toISOString().split('T')[0];
                return dateString === today;
            },
            
            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            },
            
            getAssignmentTypeClass(type) {
                return 'assignment-other';
            },
            
            // Initialize
            async init() {
                console.log('🎯 TPS Schedule System initializing...');
                this.isLoading = false;
                this.error = null;
                this.isInitialized = true;
                console.log('✅ Calendar initialized successfully');
            }
        };
    }
    
    // Test function creation
    const testInstance = calendarData();
    console.log('✅ Updated JavaScript syntax test passed!');
    console.log('✅ Function properties count:', Object.keys(testInstance).length);
    
    // Test some methods
    testInstance.switchView('week');
    testInstance.selectTeam({id: 1, name: 'Test Team'});
    testInstance.openQuickAssignmentModal('user1', '2025-08-01');
    testInstance.closeAssignmentModal();
    
    console.log('✅ All method calls successful!');
    
} catch (error) {
    console.error('❌ JavaScript syntax error:', error);
    console.error('Error stack:', error.stack);
}
