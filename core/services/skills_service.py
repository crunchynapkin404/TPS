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
        Based on simplified skill system with only 4 skills:
        - Incident (incident response)
        - Projects (daily default work)
        - Changes (daily default work)
        - Waakdienst (on-call duty)
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
        
        # Map shift categories to required skills
        category_skill_mapping = {
            'WAAKDIENST': 'Waakdienst',
            'INCIDENT': 'Incident',
            'CHANGES': 'Changes',
            'PROJECTS': 'Projects'
        }
        
        required_skill_name = category_skill_mapping.get(shift_template.category.name)
        if not required_skill_name:
            logger.warning(f"No skill mapping found for category: {shift_template.category.name}")
            return base_users.none()
        
        # Get the required skill
        try:
            required_skill = Skill.objects.get(name=required_skill_name, is_active=True)
        except Skill.DoesNotExist:
            logger.warning(f"Required skill not found: {required_skill_name}")
            return base_users.none()
        
        # Filter users who have the required skill
        qualified_user_ids = UserSkill.objects.filter(
            skill=required_skill,
            user__in=base_users
        ).values_list('user_id', flat=True)
        
        return User.objects.filter(id__in=qualified_user_ids).order_by('last_name')
    
    def calculate_skill_score(self, user: User, shift_template: ShiftTemplate) -> float:
        """
        Calculate skill score for user assignment based on simplified skill system
        
        Load balancing rules:
        - Projects and Changes have no value (score = 0 for load balancing)
        - Only incident shifts count when balancing incident workload
        - Only waakdienst shifts count when balancing waakdienst workload
        """
        # Projects and Changes are daily default work and have no value for load balancing
        if shift_template.category.name in ['PROJECTS', 'CHANGES']:
            return 0.0
        
        # Map shift categories to required skills
        category_skill_mapping = {
            'WAAKDIENST': 'Waakdienst',
            'INCIDENT': 'Incident'
        }
        
        required_skill_name = category_skill_mapping.get(shift_template.category.name)
        if not required_skill_name:
            return 0.0
        
        # Check if user has the required skill
        try:
            user_skill = UserSkill.objects.get(
                user=user,
                skill__name=required_skill_name,
                skill__is_active=True
            )
        except UserSkill.DoesNotExist:
            return 0.0
        
        # Base score for having the skill
        score = 10.0
        
        # Proficiency level weights (simplified)
        proficiency_weights = {
            'learning': 1.0,
            'basic': 2.0,
            'intermediate': 3.0,
            'advanced': 4.0,
            'expert': 5.0
        }
        
        proficiency_score = proficiency_weights.get(user_skill.proficiency_level, 2.0)
        score += proficiency_score
        
        # Bonus for certification (especially important for Waakdienst)
        if user_skill.is_certified and user_skill.skill.name == 'Waakdienst':
            score += 5.0
        elif user_skill.is_certified:
            score += 2.0
            
        # Bonus for recent usage
        if user_skill.last_used_date:
            days_since_use = (timezone.now().date() - user_skill.last_used_date).days
            if days_since_use < 30:  # Used in last month
                score += 2.0
            elif days_since_use < 90:  # Used in last 3 months
                score += 1.0
        
        # Load balancing factor based on current YTD workload
        if shift_template.category.name == 'WAAKDIENST':
            # Lower score for users with higher waakdienst workload
            ytd_waakdienst = user.ytd_waakdienst_weeks or 0
            score -= (ytd_waakdienst * 2.0)  # Reduce score by 2 for each week worked
        elif shift_template.category.name == 'INCIDENT':
            # Lower score for users with higher incident workload  
            ytd_incident = user.ytd_incident_weeks or 0
            score -= (ytd_incident * 1.0)  # Reduce score by 1 for each week worked
        
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
        Simplified for the 4-skill system
        """
        # Map shift categories to required skills
        category_skill_mapping = {
            'WAAKDIENST': 'Waakdienst',
            'INCIDENT': 'Incident',
            'CHANGES': 'Changes', 
            'PROJECTS': 'Projects'
        }
        
        required_skill_name = category_skill_mapping.get(shift_template.category.name)
        if not required_skill_name:
            return {'missing_skills': [], 'users_needing_training': [], 'certification_gaps': []}
        
        try:
            required_skill = Skill.objects.get(name=required_skill_name, is_active=True)
        except Skill.DoesNotExist:
            return {'missing_skills': [required_skill_name], 'users_needing_training': [], 'certification_gaps': []}
        
        # Get team members
        team_members = self._get_team_members()
        
        skill_gaps = {
            'missing_skills': [],
            'users_needing_training': [],
            'certification_gaps': []
        }
        
        # Check how many team members have this skill
        qualified_count = UserSkill.objects.filter(
            user__in=team_members,
            skill=required_skill
        ).count()
        
        # Minimum requirements based on skill type
        min_required = 3 if required_skill_name in ['Waakdienst', 'Incident'] else 2
        
        if qualified_count < min_required:
            skill_gaps['missing_skills'].append({
                'skill_name': required_skill.name,
                'qualified_count': qualified_count,
                'required_minimum': min_required
            })
        
        # Check certification gaps (important for Waakdienst)
        if required_skill.requires_certification:
            certified_count = UserSkill.objects.filter(
                user__in=team_members,
                skill=required_skill,
                is_certified=True,
                certification_expiry__gt=timezone.now().date()
            ).count()
            
            min_certified = 2 if required_skill_name == 'Waakdienst' else 1
            if certified_count < min_certified:
                skill_gaps['certification_gaps'].append({
                    'skill_name': required_skill.name,
                    'certified_count': certified_count,
                    'required_minimum': min_certified
                })
        
        # Identify users who need this skill
        users_without_skill = []
        for user in team_members:
            has_skill = UserSkill.objects.filter(
                user=user,
                skill=required_skill
            ).exists()
            
            if not has_skill:
                users_without_skill.append({
                    'user_name': user.get_full_name(),
                    'user_id': user.id,
                    'missing_skill': required_skill.name
                })
        
        # Show up to 5 users needing training
        skill_gaps['users_needing_training'] = users_without_skill[:5]
        
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
        Recommend users for a shift based on simplified skill matching
        Returns ranked list of recommendations with load balancing
        """
        qualified_users = self.get_qualified_users(shift_template)
        recommendations = []
        
        # Map shift categories to required skills
        category_skill_mapping = {
            'WAAKDIENST': 'Waakdienst',
            'INCIDENT': 'Incident',
            'CHANGES': 'Changes',
            'PROJECTS': 'Projects'
        }
        
        required_skill_name = category_skill_mapping.get(shift_template.category.name)
        
        for user in qualified_users:
            skill_score = self.calculate_skill_score(user, shift_template)
            
            # Get user's skill details for this shift
            skill_details = []
            if required_skill_name:
                try:
                    user_skill = UserSkill.objects.get(
                        user=user,
                        skill__name=required_skill_name
                    )
                    skill_details.append({
                        'skill_name': user_skill.skill.name,
                        'proficiency': user_skill.proficiency_level,
                        'certified': user_skill.is_certified
                    })
                except UserSkill.DoesNotExist:
                    pass
            
            # Calculate load balancing weight
            load_balancing_weight = 0
            if shift_template.category.name == 'WAAKDIENST':
                # For waakdienst, consider only waakdienst workload
                load_balancing_weight = user.ytd_waakdienst_weeks or 0
            elif shift_template.category.name == 'INCIDENT':
                # For incident, consider only incident workload
                load_balancing_weight = user.ytd_incident_weeks or 0
            # Projects and Changes don't contribute to load balancing
            
            recommendations.append({
                'user': user,
                'user_id': user.id,
                'name': user.get_full_name(),
                'skill_score': skill_score,
                'skill_details': skill_details,
                'ytd_waakdienst_weeks': user.ytd_waakdienst_weeks or 0,
                'ytd_incident_weeks': user.ytd_incident_weeks or 0,
                'load_balancing_weight': load_balancing_weight,
                'shift_category': shift_template.category.name
            })
        
        # Sort by skill score (descending) then by load balancing weight (ascending for fairness)
        # Projects and Changes are sorted only by skill score since they don't count for load balancing
        if shift_template.category.name in ['PROJECTS', 'CHANGES']:
            recommendations.sort(key=lambda x: -x['skill_score'])
        else:
            recommendations.sort(key=lambda x: (-x['skill_score'], x['load_balancing_weight']))
        
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
