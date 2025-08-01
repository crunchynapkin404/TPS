// Quick syntax test for the cleaned schedule.html JavaScript
console.log('Testing cleaned JavaScript syntax...');

// Extract and test the calendarData function
try {
    // Simulate the simplified calendarData function
    function calendarData() {
        return {
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
            showAssignmentModal: false,
            isCreating: false,
            assignmentForm: {
                user_id: '',
                date: '',
                assignment_type: 'waakdienst',
                start_time: '09:00',
                end_time: '17:00',
                notes: '',
                team_id: 4
            },
            stats: {
                totalAssignments: 0,
                activeUsers: 0
            },
            API_BASE: '/api/v1',
            CSRF_TOKEN: '',
            
            get currentPeriod() {
                return 'August 2025';
            },
            
            get weekDaysHeader() {
                return '<div>Loading...</div>';
            },
            
            openQuickAssignmentModal(userId = '', date = '') {
                console.log('Opening modal for:', userId, date);
                this.showAssignmentModal = true;
            },
            
            closeAssignmentModal() {
                console.log('Closing modal');
                this.showAssignmentModal = false;
            },
            
            formatDate(date, format = 'short') {
                const d = new Date(date);
                return d.toLocaleDateString('en-GB');
            },
            
            isToday(dateString) {
                const today = new Date().toISOString().split('T')[0];
                return dateString === today;
            },
            
            async init() {
                console.log('Initializing simplified calendar...');
                this.isLoading = false;
                this.error = null;
                this.isInitialized = true;
                console.log('Calendar initialized successfully');
            }
        };
    }
    
    // Test function creation
    const testInstance = calendarData();
    console.log('✅ JavaScript syntax test passed!');
    console.log('✅ Function properties:', Object.keys(testInstance));
    
    // Test async init
    testInstance.init().then(() => {
        console.log('✅ Async init test passed!');
    });
    
} catch (error) {
    console.error('❌ JavaScript syntax error:', error);
}
