"""
Worker API Gateway - Main Application
FastAPI application para gerenciamento centralizado de tarefas dos workers
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import sys
from typing import Optional
from datetime import datetime

from services.task_manager import TaskManager
from core.config import settings
from routes import health_router, tasks_router
from routes.dependencies import set_task_manager
from routers import buscar_publicacoes, publicacoes, marcar_publicacoes, auditoria
from routers.cpj import (
    publicacoes_router as cpj_publicacoes_router,
    pessoas_router as cpj_pessoas_router,
    processos_router as cpj_processos_router,
    pedidos_router as cpj_pedidos_router,
    envolvidos_router as cpj_envolvidos_router,
    tramitacao_router as cpj_tramitacao_router,
    documentos_router as cpj_documentos_router,
)
from routers import dw_law_router


# Configure logging
def configure_logging():
    """Configure logging for the application"""
    log_level = settings.LOG_LEVEL.upper()
    log_format = settings.LOG_FORMAT

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(getattr(logging, log_level, logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(
        getattr(logging, log_level, logging.INFO)
    )
    logging.getLogger("uvicorn.error").setLevel(
        getattr(logging, log_level, logging.INFO)
    )

    # Set app loggers
    app_loggers = ["services", "routers", "core", "routes", "models"]
    for logger_name in app_loggers:
        logging.getLogger(logger_name).setLevel(
            getattr(logging, log_level, logging.INFO)
        )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    return logger


# Task Manager global instance
task_manager: Optional[TaskManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global task_manager

    # Configure logging first
    logger = configure_logging()

    # Startup
    logger.info("🚀 Starting Worker API Gateway...")

    # Initialize Task Manager
    task_manager = TaskManager()
    await task_manager.connect()

    # Set dependencies for routes
    set_task_manager(task_manager)

    logger.info(f"✅ Worker API Gateway started on port {settings.PORT}")
    logger.info(f"📊 MongoDB connected: {settings.MONGODB_URI}")

    yield

    # Shutdown
    logger.info("⏹️ Shutting down Worker API Gateway...")
    if task_manager:
        await task_manager.disconnect()
    logger.info("👋 Worker API Gateway stopped")


# FastAPI application
app = FastAPI(
    title="Worker API Gateway",
    description="Centralized task management for Camunda workers",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(buscar_publicacoes.router)
app.include_router(publicacoes.router)
app.include_router(marcar_publicacoes.router)
app.include_router(auditoria.router)

# Include CPJ routers (7 routers = 20 endpoints)
app.include_router(cpj_publicacoes_router)
app.include_router(cpj_pessoas_router)
app.include_router(cpj_processos_router)
app.include_router(cpj_pedidos_router)
app.include_router(cpj_envolvidos_router)
app.include_router(cpj_tramitacao_router)
app.include_router(cpj_documentos_router)

# Include DW LAW router
app.include_router(dw_law_router.router)


# Custom Exception Handler for structured error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTPException to return structured error responses

    Provides consistent error format for workers to parse and handle appropriately
    """
    logger = logging.getLogger(__name__)

    # Determine if error is recoverable (should allow retry)
    retry_allowed = exc.status_code in [408, 429, 500, 502, 503, 504]

    # Map status codes to error codes
    error_code_map = {
        400: "VALIDATION_ERROR",
        404: "NOT_FOUND",
        408: "REQUEST_TIMEOUT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

    # Log error with context
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        f"❌ [{error_code}] {exc.detail} | Status: {exc.status_code} | Path: {request.url.path}",
    )

    # Return structured error response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_code": error_code,
            "error_message": str(exc.detail),
            "retry_allowed": retry_allowed,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler for unhandled exceptions

    Ensures all errors return structured responses
    """
    logger = logging.getLogger(__name__)

    error_message = str(exc)
    error_code = "INTERNAL_ERROR"

    # Log full exception with traceback
    logger.error(
        f"💥 Unhandled exception: {error_message} | Path: {request.url.path}",
        exc_info=True,
    )

    # Return structured error (retry allowed for generic errors)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": error_code,
            "error_message": error_message,
            "retry_allowed": True,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
        },
    )


if __name__ == "__main__":
    # Configure logging before starting uvicorn
    configure_logging()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
