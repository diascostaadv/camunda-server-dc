"""
Routes package initialization
Exports all routers for the FastAPI application
"""

from .health import router as health_router
from .tasks import router as tasks_router

__all__ = ["health_router", "tasks_router"]