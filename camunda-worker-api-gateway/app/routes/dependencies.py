"""
Common dependencies for FastAPI routes
Provides dependency injection for services and validation
"""

from fastapi import HTTPException, Depends
from typing import Optional

from services.task_manager import TaskManager
from services.rabbitmq_consumer import RabbitMQConsumer


# Global instances (will be set during app startup)
_task_manager: Optional[TaskManager] = None
_rabbitmq_consumer: Optional[RabbitMQConsumer] = None


def set_task_manager(task_manager: TaskManager) -> None:
    """Set the global task manager instance"""
    global _task_manager
    _task_manager = task_manager


def set_rabbitmq_consumer(rabbitmq_consumer: RabbitMQConsumer) -> None:
    """Set the global RabbitMQ consumer instance"""
    global _rabbitmq_consumer
    _rabbitmq_consumer = rabbitmq_consumer


async def get_task_manager() -> TaskManager:
    """
    Dependency to get the TaskManager instance
    
    Raises:
        HTTPException: If TaskManager is not available
        
    Returns:
        TaskManager: The task manager instance
    """
    if not _task_manager:
        raise HTTPException(status_code=503, detail="Task Manager not available")
    return _task_manager


async def get_rabbitmq_consumer() -> Optional[RabbitMQConsumer]:
    """
    Dependency to get the RabbitMQ consumer instance
    
    Returns:
        Optional[RabbitMQConsumer]: The RabbitMQ consumer instance or None
    """
    return _rabbitmq_consumer


async def get_task_manager_connection_status() -> bool:
    """
    Check if TaskManager is connected
    
    Returns:
        bool: True if connected, False otherwise
    """
    return _task_manager.is_connected() if _task_manager else False


async def get_rabbitmq_connection_status() -> bool:
    """
    Check if RabbitMQ consumer is connected
    
    Returns:
        bool: True if connected, False otherwise
    """
    return _rabbitmq_consumer.is_connected() if _rabbitmq_consumer else False