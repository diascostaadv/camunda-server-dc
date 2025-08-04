"""
Worker API Gateway - Main Application
FastAPI application para gerenciamento centralizado de tarefas dos workers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import Optional

from services.task_manager import TaskManager
from services.rabbitmq_consumer import RabbitMQConsumer
from core.config import settings
from routes import health_router, tasks_router
from routes.dependencies import set_task_manager, set_rabbitmq_consumer


# Task Manager global instance
task_manager: Optional[TaskManager] = None
rabbitmq_consumer: Optional[RabbitMQConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global task_manager, rabbitmq_consumer
    
    # Startup
    print("🚀 Starting Worker API Gateway...")
    
    # Initialize Task Manager
    task_manager = TaskManager()
    await task_manager.connect()
    
    # Initialize RabbitMQ Consumer
    rabbitmq_consumer = RabbitMQConsumer(task_manager)
    await rabbitmq_consumer.start()
    
    # Set dependencies for routes
    set_task_manager(task_manager)
    set_rabbitmq_consumer(rabbitmq_consumer)
    
    print(f"✅ Worker API Gateway started on port {settings.PORT}")
    print(f"📊 MongoDB connected: {settings.MONGODB_URI}")
    print(f"🐰 RabbitMQ connected: {settings.RABBITMQ_URL}")
    
    yield
    
    # Shutdown
    print("⏹️ Shutting down Worker API Gateway...")
    if rabbitmq_consumer:
        await rabbitmq_consumer.stop()
    if task_manager:
        await task_manager.disconnect()
    print("👋 Worker API Gateway stopped")


# FastAPI application
app = FastAPI(
    title="Worker API Gateway",
    description="Centralized task management for Camunda workers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(tasks_router)




if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )