"""
TPS V1.4 - Skills API Views
Django REST Framework views for skills management
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.models import Skill, SkillCategory, UserSkill
from api.serializers.user_serializers import (
    SkillSerializer, SkillCategorySerializer, UserSkillSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_categories(request):
    """
    Get all skill categories
    GET /api/v1/skills/categories/
    """
    categories = SkillCategory.objects.filter(is_active=True).order_by('name')
    serializer = SkillCategorySerializer(categories, many=True)
    
    return Response({
        'success': True,
        'categories': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skills_list(request):
    """
    Get all skills, optionally filtered by category
    GET /api/v1/skills/?category_id=1
    """
    skills = Skill.objects.filter(is_active=True).select_related('category')
    
    # Filter by category if specified
    category_id = request.query_params.get('category_id')
    if category_id:
        skills = skills.filter(category_id=category_id)
    
    skills = skills.order_by('category__name', 'name')
    serializer = SkillSerializer(skills, many=True)
    
    return Response({
        'success': True,
        'skills': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_skills(request, user_id):
    """
    Get skills for a specific user
    GET /api/v1/users/{user_id}/skills/
    """
    try:
        user_skills = UserSkill.objects.filter(
            user_id=user_id
        ).select_related('skill', 'skill__category').order_by('skill__category__name', 'skill__name')
        
        serializer = UserSkillSerializer(user_skills, many=True)
        
        return Response({
            'success': True,
            'user_id': user_id,
            'skills': serializer.data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user_skill(request):
    """
    Add a skill to a user
    POST /api/v1/user-skills/
    """
    try:
        serializer = UserSkillSerializer(data=request.data)
        
        if serializer.is_valid():
            # Check if user already has this skill
            user_id = serializer.validated_data['user_id']
            skill_id = serializer.validated_data['skill_id']
            
            if UserSkill.objects.filter(user_id=user_id, skill_id=skill_id).exists():
                return Response({
                    'success': False,
                    'error': 'User already has this skill'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_skill = serializer.save()
            response_serializer = UserSkillSerializer(user_skill)
            
            return Response({
                'success': True,
                'user_skill': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': 'Invalid data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_skill(request, user_skill_id):
    """
    Update a user's skill proficiency
    PUT /api/v1/user-skills/{user_skill_id}/
    """
    try:
        user_skill = UserSkill.objects.get(id=user_skill_id)
        serializer = UserSkillSerializer(user_skill, data=request.data, partial=True)
        
        if serializer.is_valid():
            user_skill = serializer.save()
            response_serializer = UserSkillSerializer(user_skill)
            
            return Response({
                'success': True,
                'user_skill': response_serializer.data
            })
        
        return Response({
            'success': False,
            'error': 'Invalid data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except UserSkill.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User skill not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_skill(request, user_skill_id):
    """
    Remove a skill from a user
    DELETE /api/v1/user-skills/{user_skill_id}/
    """
    try:
        user_skill = UserSkill.objects.get(id=user_skill_id)
        user_skill.delete()
        
        return Response({
            'success': True,
            'message': 'User skill removed successfully'
        })
        
    except UserSkill.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User skill not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)