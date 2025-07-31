"""
TPS V1.4 - Context Processors
Global template context variables
"""

from apps.teams.models import Team, TeamMembership


def user_teams(request):
    """
    Add user's teams to template context for team switcher
    """
    if request.user.is_authenticated:
        # Get user's teams with membership info
        user_teams = Team.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
            is_active=True
        ).distinct().order_by('name')
        
        # Get current active team (primary team or first team)
        current_team = None
        if user_teams.exists():
            # Try to get primary team first
            primary_membership = TeamMembership.objects.filter(
                user=request.user,
                is_active=True,
                is_primary_team=True
            ).first()
            
            if primary_membership:
                current_team = primary_membership.team
            else:
                current_team = user_teams.first()
        
        return {
            'user_teams': user_teams,
            'current_team': current_team,
        }
    
    return {
        'user_teams': [],
        'current_team': None,
    }
