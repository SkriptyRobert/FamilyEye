"""Device management endpoints - modular structure."""
from fastapi import APIRouter
from . import crud, pairing, actions, settings

router = APIRouter()

# Include all sub-routers
router.include_router(crud.router, tags=["devices"])
router.include_router(pairing.router, prefix="/pairing", tags=["pairing"])
router.include_router(actions.router, tags=["devices"])
router.include_router(settings.router, tags=["devices"])

# Export verify_device_api_key for backward compatibility
# Other modules should import from .devices.utils directly to avoid circular imports
from .utils import verify_device_api_key
