"""
TPS V1.4 - Async View Optimizations
Implements async views for heavy operations to improve performance
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from asgiref.sync import sync_to_async
import asyncio
import json

from core.services.query_optimization_service import QueryOptimizationService
from core.services.cache_service import CacheService
from apps.teams.models import Team


@login_required
@require_http_methods(["GET"])
async def async_dashboard_data(request):
    """
    Async endpoint for dashboard data - loads heavy operations in parallel
    PERFORMANCE: Executes multiple independent queries concurrently
    """
    user = request.user
    
    try:
        # Check cache first (sync operation)
        cached_data = await sync_to_async(CacheService.get_dashboard_data)(
            user.id, f"async_{user.role}"
        )
        if cached_data:
            return JsonResponse(cached_data)
        
        # Execute multiple heavy operations concurrently
        tasks = []
        
        # Task 1: Get user dashboard data
        tasks.append(
            sync_to_async(QueryOptimizationService.get_user_dashboard_data)(user)
        )
        
        # Task 2: Get system health metrics (if admin/manager)
        if user.is_manager() or user.is_admin():
            tasks.append(
                sync_to_async(QueryOptimizationService.get_system_health_metrics)()
            )
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0)))  # No-op task
        
        # Task 3: Get user teams
        tasks.append(
            sync_to_async(QueryOptimizationService.get_user_teams_optimized)(user.id)
        )
        
        # Task 4: Get workload analysis
        tasks.append(
            sync_to_async(QueryOptimizationService.get_user_workload_analysis)(
                user.id, days=30
            )
        )
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        user_dashboard_data = results[0] if not isinstance(results[0], Exception) else {}
        system_health = results[1] if not isinstance(results[1], Exception) else {}
        user_teams = results[2] if not isinstance(results[2], Exception) else []
        workload_analysis = results[3] if not isinstance(results[3], Exception) else {}
        
        # Combine response
        response_data = {
            'user_dashboard': user_dashboard_data,
            'user_teams': [{'id': team.id, 'name': team.name} for team in user_teams],
            'workload_analysis': workload_analysis,
            'loaded_async': True,
            'cache_miss': True,
        }
        
        # Add system health for managers/admins
        if user.is_manager() or user.is_admin():
            response_data['system_health'] = system_health
        
        # Cache the result
        await sync_to_async(CacheService.set_dashboard_data)(
            user.id, f"async_{user.role}", response_data
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to load dashboard data: {str(e)}',
            'loaded_async': True,
        }, status=500)


@login_required
@require_http_methods(["GET"])
async def async_team_workload_stats(request):
    """
    Async endpoint for team workload statistics
    PERFORMANCE: Loads multiple team stats concurrently
    """
    try:
        # Get team IDs from request
        team_ids_str = request.GET.get('team_ids', '')
        if not team_ids_str:
            # Get user's teams
            user_teams = await sync_to_async(
                QueryOptimizationService.get_user_teams_optimized
            )(request.user.id)
            team_ids = [team.id for team in user_teams]
        else:
            team_ids = [int(id.strip()) for id in team_ids_str.split(',') if id.strip()]
        
        if not team_ids:
            return JsonResponse({'teams': [], 'message': 'No teams found'})
        
        # Create concurrent tasks for different time periods
        tasks = []
        
        # Current month
        tasks.append(
            sync_to_async(QueryOptimizationService.get_team_workload_stats)(
                team_ids, None  # Default date range
            )
        )
        
        # Last month  
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()
        last_month_start = today - timedelta(days=60)
        last_month_end = today - timedelta(days=30)
        
        tasks.append(
            sync_to_async(QueryOptimizationService.get_team_workload_stats)(
                team_ids, (last_month_start, last_month_end)
            )
        )
        
        # Execute concurrently
        current_stats, last_month_stats = await asyncio.gather(*tasks)
        
        # Get team names
        teams = await sync_to_async(lambda: list(
            Team.objects.filter(id__in=team_ids).values('id', 'name')
        ))()
        
        team_names = {team['id']: team['name'] for team in teams}
        
        # Combine results
        combined_stats = []
        for team_id in team_ids:
            current = current_stats.get(team_id, {})
            last_month = last_month_stats.get(team_id, {})
            
            combined_stats.append({
                'team_id': team_id,
                'team_name': team_names.get(team_id, f'Team {team_id}'),
                'current_period': current,
                'previous_period': last_month,
                'trend': {
                    'assignments_change': (
                        current.get('total_assignments', 0) - 
                        last_month.get('total_assignments', 0)
                    ),
                    'success_rate_change': (
                        current.get('success_rate', 0) - 
                        last_month.get('success_rate', 0)
                    ),
                }
            })
        
        return JsonResponse({
            'teams': combined_stats,
            'loaded_async': True,
            'processing_time_saved': 'Concurrent loading of multiple time periods'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to load team stats: {str(e)}',
            'loaded_async': True,
        }, status=500)


@login_required  
@require_http_methods(["POST"])
async def async_bulk_operations(request):
    """
    Async endpoint for bulk operations that benefit from concurrent processing
    """
    try:
        data = json.loads(request.body)
        operation = data.get('operation')
        
        if operation == 'bulk_user_analysis':
            user_ids = data.get('user_ids', [])
            if not user_ids:
                return JsonResponse({'error': 'No user IDs provided'}, status=400)
            
            # Create concurrent tasks for user workload analysis
            tasks = [
                sync_to_async(QueryOptimizationService.get_user_workload_analysis)(
                    user_id, data.get('days', 30)
                )
                for user_id in user_ids
            ]
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            user_analyses = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    user_analyses.append({
                        'user_id': user_ids[i],
                        'error': str(result)
                    })
                else:
                    user_analyses.append({
                        'user_id': user_ids[i],
                        'analysis': result
                    })
            
            return JsonResponse({
                'operation': 'bulk_user_analysis',
                'results': user_analyses,
                'processed_concurrently': len(user_ids),
                'loaded_async': True,
            })
        
        else:
            return JsonResponse({
                'error': f'Unknown operation: {operation}'
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': f'Bulk operation failed: {str(e)}',
            'loaded_async': True,
        }, status=500)