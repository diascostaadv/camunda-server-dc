"""
Health check routes
Endpoints for monitoring application health and status
"""

from fastapi import APIRouter, Depends

from .dependencies import get_task_manager, get_task_manager_connection_status
from services.task_manager import TaskManager


router = APIRouter(
    tags=["health"],
    responses={
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)


@router.get("/")
async def root():
    """
    Root endpoint - Basic service information

    Returns:
        dict: Service name, status and version
    """
    return {"service": "Worker API Gateway", "status": "running", "version": "1.0.0"}


@router.get("/health")
async def health_check(
    mongodb_connected: bool = Depends(get_task_manager_connection_status),
    task_manager: TaskManager = Depends(get_task_manager),
):
    """
    Detailed health check endpoint

    Returns:
        dict: Detailed health status including database connections
    """
    mongodb_status = "connected" if mongodb_connected else "disconnected"

    return {
        "status": "healthy" if mongodb_connected else "unhealthy",
        "mongodb": mongodb_status,
        "timestamp": task_manager.get_timestamp(),
    }
