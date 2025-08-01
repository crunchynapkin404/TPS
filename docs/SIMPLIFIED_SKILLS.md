# TPS Simplified Skill System

## Overview

The TPS skill system has been simplified from a complex multi-category system with 49+ skills down to a streamlined 4-skill system that directly supports the orchestrator requirements.

## Core Skills

The system now has exactly 4 skills in a single "Operations" category:

1. **Incidenten** - Incident response and handling
2. **Projects** - Project work and development (daily default work)  
3. **Changes** - Change management and implementation (daily default work)
4. **Waakdienst** - On-call duty and emergency response

## Load Balancing Rules

The system implements specific load balancing rules as requested:

### No Value Skills
- **Projects** and **Changes** have **score 0.0** for load balancing
- These are considered daily default work and do not block engineers from planning
- They do not contribute to workload calculations

### Workload Separation
- **Waakdienst shifts**: Only count waakdienst weeks for load balancing
- **Incident shifts**: Only count incident weeks for load balancing  
- **Projects/Changes**: Do not count for any load balancing

### Fairness Algorithm
- Users with fewer YTD weeks in a category get higher priority
- Load balancing penalties reduce scores for users with higher workloads
- Skill proficiency and certifications still factor into scoring

## Team Structure

### Operationeel Team
- **Engineers**: Incidenten, Projects, Changes
- **Planners**: Incidenten, Projects, Changes, Waakdienst  
- **Team Leads**: Incidenten, Projects, Changes, Waakdienst

### Tactisch Team
- **Team Leads**: Projects, Changes, Waakdienst
- **Planners**: Projects, Changes, Waakdienst, Incidenten
- **Engineers**: Projects, Changes, Waakdienst

## Management Commands

### List Users and Skills
```bash
python manage.py manage_user_skills --list-users
```

### Assign Skills to Specific User
```bash
python manage.py manage_user_skills --user user1 --skills "Incidenten,Projects,Changes"
python manage.py manage_user_skills --user user1 --skills "Waakdienst" --proficiency intermediate
```

### Bulk Assignment Based on Teams
```bash
python manage.py manage_user_skills --bulk-assign
```

### Interactive Assignment
```bash
python manage.py manage_user_skills --assign
```

## Database Changes

The migration `0004_simplify_skill_system.py` performs the following:

1. **Removes** all existing skills and skill categories
2. **Creates** single "Operations" skill category
3. **Creates** the 4 core skills with appropriate settings:
   - Waakdienst requires intermediate proficiency and certification
   - Others require basic proficiency
4. **Preserves** user skill assignments where possible

## API Changes

The skills API continues to work but now returns the simplified skill set:

- `/api/v1/skills/categories/` - Returns single Operations category
- `/api/v1/skills/` - Returns 4 core skills
- `/api/v1/users/{id}/skills/` - Returns user's simplified skills

## Service Updates

### SkillsService
- Updated qualification logic for simplified skill mapping
- Implements load balancing rules in scoring
- Simplified skill gap analysis
- Recommendation system respects workload rules

### PlanningOrchestrator  
- Updated skill validation for simplified system
- Works with new qualification logic
- Maintains existing API compatibility

## Testing

Run the integration test to verify the system:

```bash
python test_simplified_skills.py
```

This test verifies:
- ✅ Only 4 skills exist
- ✅ Load balancing rules work correctly
- ✅ Team skill assignments are appropriate
- ✅ Skill management system functions

## Benefits

1. **Simplified Management**: Easy to understand and assign 4 skills vs 49+
2. **Clear Load Balancing**: Explicit rules for fair workload distribution
3. **Orchestrator Focus**: Skills directly map to orchestrator requirements
4. **Easy Assignment**: Command-line tools for bulk and individual assignment
5. **Maintainable**: Reduced complexity in codebase and database

## Migration Path

For existing installations:

1. **Backup** existing skill data if needed
2. **Run migration**: `python manage.py migrate accounts`
3. **Assign skills**: Use `manage_user_skills` command to set up users  
4. **Test system**: Run integration tests to verify functionality

The system maintains backward compatibility with existing APIs while providing the simplified functionality requested.