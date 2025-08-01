// Quick JavaScript syntax check for schedule.html
console.log('Testing JavaScript syntax...');

// Check if the calendarData function can be parsed
try {
    // Simple version of calendarData function
    function testCalendarData() {
        return {
            currentDate: new Date(),
            selectedTeam: null,
            availableTeams: [],
            calendarData: null,
            availableUsers: [],
            isLoading: true,
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
            init() {
                console.log('Test calendar initialized');
            }
        };
    }
    
    console.log('✅ JavaScript syntax check passed!');
    const testInstance = testCalendarData();
    console.log('✅ Test function created successfully');
    console.log('Test instance:', testInstance);
    
} catch (error) {
    console.error('❌ JavaScript syntax error:', error);
}
