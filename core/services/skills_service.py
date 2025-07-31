"""
Skills Service for TPS V1.4
Handles skill matching, qualification validation, and skill scoring
"""

import logging
from typing import List, Dict, Optional
from django.db.models import QuerySet, Q
from django.utils import timezone

from apps.accounts.models import User, Skill, UserSkill
from apps.scheduling.models import ShiftTemplate
from apps.teams.models import Team, TeamMembership

logger = logging.getLogger(__name__)


class SkillsService:
    """
    Service for managing skills and qualifications
    """
    
    def __init__(self, team: Team):
        self.team = team
    
    def get_qualified_users(self, shift_template: ShiftTemplate) -> QuerySet[User]:
        """
        Get users qualified for a specific shift template
        Based on skills, proficiency levels, and certifications
        """
        # Get team members
        team_member_ids = TeamMembership.objects.filter(
            team=self.team, is_active=True
        ).values_list('user_id', flat=True)
        
        # Base queryset of active team members
        base_users = User.objects.filter(
            id__in=team_member_ids,
            is_active=True
        )
        
        # Get required skills for this shift category
        category_skills = Skill.objects.filter(
            category__name__icontains=shift_template.category,
            is_active=True
        )
        
        if not category_skills.exists():
            logger.warning(f"No skills defined for category: {shift_template.category}")
            return base_users.none()
        
        # Filter users who have at least one relevant skill with adequate proficiency
        qualified_user_ids = []
        
        for user in base_users:
            user_skills = UserSkill.objects.filter(
                user=user,
                skill__in=category_skills,
                proficiency_level__in=['intermediate', 'advanced', 'expert']
            )
            
            # Check if user has required certifications
            if self._has_required_certifications(user, user_skills):
                qualified_user_ids.append(user.id)
        
        return User.objects.filter(id__in=qualified_user_ids).order_by('last_name')
    
    def calculate_skill_score(self, user: User, shift_template: ShiftTemplate) -> float:
        """
        Calculate skill score for user assignment
        Higher score = better qualified
        """
        score = 0.0
        
        # Proficiency level weights
        proficiency_weights = {
            'learning': 1.0,
            'basic': 2.0,
            'intermediate': 3.0,
            'advanced': 4.0,
            'expert': 5.0
        }
        
        # Get user's skills for this shift category
        category_skills = UserSkill.objects.filter(
            user=user,
            skill__category__name__icontains=shift_template.category,
            skill__is_active=True
        )
        
        for user_skill in category_skills:
            # Add proficiency score
            proficiency_score = proficiency_weights.get(user_skill.proficiency_level, 1.0)
            score += proficiency_score
            
            # Bonus for certification
            if user_skill.is_certified:
                score += 1.0
                
            # Bonus for recent usage
            if user_skill.last_used_date:
                days_since_use = (timezone.now().date() - user_skill.last_used_date).days
                if days_since_use < 30:  # Used in last month
                    score += 0.5
                elif days_since_use < 90:  # Used in last 3 months
                    score += 0.2
        
        # Penalty for missing required skills
        required_skills = Skill.objects.filter(
            category__name__icontains=shift_template.category,
            required_proficiency_level__in=['intermediate', 'advanced', 'expert'],
            is_active=True
        )
        
        for required_skill in required_skills:
            user_has_skill = category_skills.filter(skill=required_skill).exists()
            if not user_has_skill:
                score -= 2.0  # Penalty for missing required skill
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def validate_certifications(self, user: User, required_certs: List[str]) -> bool:
        """
        Validate that user has all required certifications
        """
        if not required_certs:
            return True
            
        for cert_name in required_certs:
            # Find user skill with this certification requirement
            user_skill = UserSkill.objects.filter(
                user=user,
                skill__name__icontains=cert_name,
                skill__requires_certification=True,
                is_certified=True
            ).first()
            
            if not user_skill:
                logger.debug(f"User {user.get_full_name()} missing certification: {cert_name}")
                return False
                
            # Check certification expiry
            if user_skill.certification_expiry:
                if user_skill.certification_expiry < timezone.now().date():
                    logger.debug(f"User {user.get_full_name()} has expired certification: {cert_name}")
                    return False
                    
        return True
    
    def get_skill_gaps(self, shift_template: ShiftTemplate) -> Dict[str, List[str]]:
        """
        Identify skill gaps for a shift template across the team
        Returns dict with 'missing_skills' and 'users_needing_training'
        """
        # Get required skills for this shift
        required_skills = Skill.objects.filter(
            category__name__icontains=shift_template.category,
            is_active=True
        )
        
        # Get team members
        team_members = self._get_team_members()
        
        skill_gaps = {
            'missing_skills': [],
            'users_needing_training': [],
            'certification_gaps': []
        }
        
        for skill in required_skills:
            # Check how many team members have this skill
            qualified_count = UserSkill.objects.filter(
                user__in=team_members,
                skill=skill,
                proficiency_level__in=['intermediate', 'advanced', 'expert']
            ).count()
            
            # If less than 3 people have the skill, it's a gap
            if qualified_count < 3:
                skill_gaps['missing_skills'].append({
                    'skill_name': skill.name,
                    'qualified_count': qualified_count,
                    'required_minimum': 3
                })
            
            # Check certification gaps
            if skill.requires_certification:
                certified_count = UserSkill.objects.filter(
                    user__in=team_members,
                    skill=skill,
                    is_certified=True,
                    certification_expiry__gt=timezone.now().date()
                ).count()
                
                if certified_count < 2:  # Need at least 2 certified users
                    skill_gaps['certification_gaps'].append({
                        'skill_name': skill.name,
                        'certified_count': certified_count,
                        'required_minimum': 2
                    })
        
        # Identify users who need training
        for user in team_members:
            user_skills = UserSkill.objects.filter(
                user=user,
                skill__in=required_skills
            )
            
            if user_skills.count() < required_skills.count() / 2:  # Has less than half required skills
                skill_gaps['users_needing_training'].append({
                    'user_name': user.get_full_name(),
                    'user_id': user.id,
                    'current_skills': user_skills.count(),
                    'required_skills': required_skills.count()
                })
        
        return skill_gaps
    
    def get_skill_matrix(self) -> Dict[str, Dict]:
        """
        Generate skill matrix for the team showing all users' proficiencies
        """
        team_members = self._get_team_members()
        all_skills = Skill.objects.filter(is_active=True).order_by('category__name', 'name')
        
        skill_matrix = {
            'users': [],
            'skills': [],
            'matrix': {}
        }
        
        # Build skills list
        for skill in all_skills:
            skill_matrix['skills'].append({
                'id': skill.id,
                'name': skill.name,
                'category': skill.category.name,
                'requires_certification': skill.requires_certification
            })
        
        # Build user skills matrix
        for user in team_members:
            user_data = {
                'id': user.id,
                'name': user.get_full_name(),
                'skills': {}
            }
            
            user_skills = UserSkill.objects.filter(user=user).select_related('skill')
            
            for user_skill in user_skills:
                user_data['skills'][user_skill.skill.id] = {
                    'proficiency_level': user_skill.proficiency_level,
                    'is_certified': user_skill.is_certified,
                    'certification_expiry': user_skill.certification_expiry.isoformat() if user_skill.certification_expiry else None,
                    'last_used': user_skill.last_used_date.isoformat() if user_skill.last_used_date else None
                }
            
            skill_matrix['users'].append(user_data)
            skill_matrix['matrix'][user.id] = user_data['skills']
        
        return skill_matrix
    
    def recommend_skill_assignments(self, shift_template: ShiftTemplate) -> List[Dict]:
        """
        Recommend users for a shift based on skill matching
        Returns ranked list of recommendations
        """
        qualified_users = self.get_qualified_users(shift_template)
        recommendations = []
        
        for user in qualified_users:
            skill_score = self.calculate_skill_score(user, shift_template)
            
            # Get user's specific skills for this shift
            user_skills = UserSkill.objects.filter(
                user=user,
                skill__category__name__icontains=shift_template.category
            ).select_related('skill')
            
            skill_details = []
            for user_skill in user_skills:
                skill_details.append({
                    'skill_name': user_skill.skill.name,
                    'proficiency': user_skill.proficiency_level,
                    'certified': user_skill.is_certified
                })
            
            recommendations.append({
                'user': user,
                'user_id': user.id,
                'name': user.get_full_name(),
                'skill_score': skill_score,
                'skill_details': skill_details,
                'ytd_waakdienst_weeks': user.ytd_waakdienst_weeks or 0,
                'ytd_incident_weeks': user.ytd_incident_weeks or 0
            })
        
        # Sort by skill score (descending) then by YTD workload (ascending)
        recommendations.sort(key=lambda x: (-x['skill_score'], x.get('ytd_waakdienst_weeks', 0) + x.get('ytd_incident_weeks', 0)))
        
        return recommendations
    
    def _has_required_certifications(self, user: User, user_skills: QuerySet[UserSkill]) -> bool:
        """Check if user has all required certifications for their skills"""
        for user_skill in user_skills:
            if user_skill.skill.requires_certification:
                if not user_skill.is_certified:
                    return False
                    
                # Check expiry
                if user_skill.certification_expiry:
                    if user_skill.certification_expiry < timezone.now().date():
                        return False
                        
        return True
    
    def _get_team_members(self) -> QuerySet[User]:
        """Get active team members"""
        member_ids = TeamMembership.objects.filter(
            team=self.team, is_active=True
        ).values_list('user_id', flat=True)
        
        return User.objects.filter(id__in=member_ids, is_active=True)
