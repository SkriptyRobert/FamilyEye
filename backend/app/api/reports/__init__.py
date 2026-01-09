"""
Reports API package - Modular structure for usage reporting endpoints.

This package contains split endpoints from the original monolithic reports.py:
- agent_endpoints: Agent reporting (usage, screenshots, critical events)
- device_endpoints: Device usage queries and cleanup
- stats_endpoints: Advanced statistics and trends
- summary_endpoint: Device summary with Smart Insights (main dashboard data)
"""
from fastapi import APIRouter

from .agent_endpoints import router as agent_router
from .device_endpoints import router as device_router
from .stats_endpoints import router as stats_router
from .summary_endpoint import router as summary_router

# Create combined router
router = APIRouter()

# Include all sub-routers
router.include_router(agent_router)
router.include_router(device_router)
router.include_router(stats_router)
router.include_router(summary_router)

# Re-export running processes cache for backward compatibility
from .device_endpoints import running_processes_cache, get_running_processes_cache, set_running_processes_cache

__all__ = [
    'router',
    'running_processes_cache',
    'get_running_processes_cache', 
    'set_running_processes_cache'
]
