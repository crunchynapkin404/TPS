"""
TPS V1.4 - Profile API Views
API endpoints for user profile management
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import UserSkill, Skill, SkillCategory

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user_profile(request):
    """
    Get current user's profile data
    GET /api/v1/profile/
    """
    user = request.user
    
    # Get user's skills
    user_skills = []
    for user_skill in user.user_skills.select_related('skill__category').all():
        user_skills.append({
            'id': user_skill.id,
            'name': user_skill.skill.name,
            'level': user_skill.proficiency_level.title(),
            'certification': 'Certified' if user_skill.is_certified else 'Not Certified',
            'proficiency': min(100, max(0, {
                'learning': 20,
                'basic': 40,
                'intermediate': 60,
                'advanced': 80,
                'expert': 95
            }.get(user_skill.proficiency_level, 50))),
            'icon': '🔧',  # Default icon, could be enhanced later
            'iconBg': 'bg-blue-500'
        })
    
    # Parse shift preferences
    shift_preferences = user.preferred_shift_types or []
    shift_types = {
        'day': 'day' in shift_preferences,
        'night': 'night' in shift_preferences,
        'waakdienst': 'waakdienst' in shift_preferences
    }
    
    # Build response data
    profile_data = {
        'basicInfo': {
            'firstName': user.first_name or '',
            'lastName': user.last_name or '',
            'email': user.email or '',
            'phone': user.phone or '',
            'employeeId': user.employee_id or '',
            'department': getattr(user, 'department', '') or ''
        },
        'preferences': {
            'shiftTypes': shift_types,
            'maxHoursWeek': 40,  # Default value, could be added to model later
            'maxConsecutiveDays': user.max_consecutive_days or 7,
            'notifications': {
                'email': True,
                'sms': False,
                'assignments': True
            }
        },
        'skills': user_skills,
        'stats': {
            'hoursThisMonth': float(user.ytd_hours_logged or 0),
            'shiftsCompleted': 0,  # Could calculate from assignments
            'fairnessScore': 8.5,  # Could calculate from fairness service
            'nextShift': 'No upcoming shifts'
        }
    }
    
    return Response(profile_data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_current_user_profile(request):
    """
    Update current user's profile basic information
    PUT /api/v1/profile/basic-info/
    """
    user = request.user
    data = request.data
    
    try:
        # Update basic information
        if 'firstName' in data:
            user.first_name = data['firstName']
        if 'lastName' in data:
            user.last_name = data['lastName']
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        
        # Validate email uniqueness
        if 'email' in data:
            existing_user = User.objects.filter(email=data['email']).exclude(id=user.id).first()
            if existing_user:
                return Response(
                    {'error': 'Email address is already in use'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        user.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'basicInfo': {
                'firstName': user.first_name,
                'lastName': user.last_name,
                'email': user.email,
                'phone': user.phone,
                'employeeId': user.employee_id,
                'department': getattr(user, 'department', '') or ''
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to update profile: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_preferences(request):
    """
    Update current user's work preferences
    PUT /api/v1/profile/preferences/
    """
    user = request.user
    data = request.data
    
    try:
        # Update shift preferences
        if 'shiftTypes' in data:
            shift_types = []
            if data['shiftTypes'].get('day'):
                shift_types.append('day')
            if data['shiftTypes'].get('night'):
                shift_types.append('night')
            if data['shiftTypes'].get('waakdienst'):
                shift_types.append('waakdienst')
            
            user.preferred_shift_types = shift_types
        
        # Update max consecutive days
        if 'maxConsecutiveDays' in data:
            user.max_consecutive_days = int(data['maxConsecutiveDays'])
        
        user.save()
        
        return Response({
            'message': 'Preferences updated successfully',
            'preferences': {
                'shiftTypes': {
                    'day': 'day' in user.preferred_shift_types,
                    'night': 'night' in user.preferred_shift_types,
                    'waakdienst': 'waakdienst' in user.preferred_shift_types
                },
                'maxConsecutiveDays': user.max_consecutive_days
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to update preferences: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_skill(request):
    """
    Add a new skill to current user's profile
    POST /api/v1/profile/skills/
    """
    user = request.user
    data = request.data
    
    try:
        # Validate required fields
        if not all(key in data for key in ['name', 'level', 'certification']):
            return Response(
                {'error': 'Missing required fields: name, level, certification'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or get skill
        skill_name = data['name']
        
        # For now, create a generic skill category if it doesn't exist
        category, created = SkillCategory.objects.get_or_create(
            name='General',
            defaults={'description': 'General skills category', 'color': '#6B7280'}
        )
        
        skill, created = Skill.objects.get_or_create(
            name=skill_name,
            defaults={
                'category': category,
                'description': f'Skill: {skill_name}',
                'minimum_level_required': 'basic'
            }
        )
        
        # Map proficiency level
        proficiency_mapping = {
            'Beginner': 'basic',
            'Intermediate': 'intermediate', 
            'Advanced': 'advanced',
            'Expert': 'expert'
        }
        proficiency_level = proficiency_mapping.get(data['level'], 'basic')
        
        # Create user skill if not exists
        user_skill, created = UserSkill.objects.get_or_create(
            user=user,
            skill=skill,
            defaults={
                'proficiency_level': proficiency_level,
                'is_certified': data['certification'] == 'Certified'
            }
        )
        
        if not created:
            # Update existing skill
            user_skill.proficiency_level = proficiency_level
            user_skill.is_certified = data['certification'] == 'Certified'
            user_skill.save()
        
        return Response({
            'message': 'Skill added successfully',
            'skill': {
                'id': user_skill.id,
                'name': skill.name,
                'level': data['level'],
                'certification': data['certification'],
                'proficiency': int(data.get('proficiency', 50))
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to add skill: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_skill(request, skill_id):
    """
    Update an existing user skill
    PUT /api/v1/profile/skills/{skill_id}/
    """
    user = request.user
    data = request.data
    
    try:
        user_skill = UserSkill.objects.get(id=skill_id, user=user)
        
        # Map proficiency level
        proficiency_mapping = {
            'Beginner': 'basic',
            'Intermediate': 'intermediate',
            'Advanced': 'advanced', 
            'Expert': 'expert'
        }
        
        if 'level' in data:
            user_skill.proficiency_level = proficiency_mapping.get(data['level'], 'basic')
        
        if 'certification' in data:
            user_skill.is_certified = data['certification'] == 'Certified'
        
        user_skill.save()
        
        return Response({
            'message': 'Skill updated successfully',
            'skill': {
                'id': user_skill.id,
                'name': user_skill.skill.name,
                'level': data.get('level', user_skill.proficiency_level.title()),
                'certification': 'Certified' if user_skill.is_certified else 'Not Certified'
            }
        })
        
    except UserSkill.DoesNotExist:
        return Response(
            {'error': 'Skill not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to update skill: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_skill(request, skill_id):
    """
    Delete a user skill
    DELETE /api/v1/profile/skills/{skill_id}/
    """
    user = request.user
    
    try:
        user_skill = UserSkill.objects.get(id=skill_id, user=user)
        skill_name = user_skill.skill.name
        user_skill.delete()
        
        return Response({
            'message': f'Skill "{skill_name}" removed successfully'
        })
        
    except UserSkill.DoesNotExist:
        return Response(
            {'error': 'Skill not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to delete skill: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )