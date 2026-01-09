"""
Reports API package - Modular structure for usage reporting endpoints.

This package contains split endpoints from the original monolithic reports.py:
- agent_endpoints: Agent reporting (usage, screenshots, critical events)
- device_endpoints: Device summary and usage queries  
- stats_endpoints: Advanced statistics and trends

The original reports.py still exists for backward compatibility during transition.
"""
from fastapi import APIRouter

# Create the main router for this package
router = APIRouter()

# Note: During transition, keep using the original reports.py router
# After full migration, uncomment below and deprecate the original file:
# 
# from .agent_endpoints import router as agent_router
# from .device_endpoints import router as device_router
# from .stats_endpoints import router as stats_router
# 
# router.include_router(agent_router, tags=["agent"])
# router.include_router(device_router, tags=["device"])
# router.include_router(stats_router, tags=["statistics"])
