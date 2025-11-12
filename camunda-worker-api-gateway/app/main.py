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


# OpenAPI Tags Metadata
tags_metadata = [
    {
        "name": "health",
        "description": "Health check endpoints para monitoramento da aplicação e status dos serviços conectados (MongoDB)."
    },
    {
        "name": "tasks",
        "description": "Gerenciamento de tarefas assíncronas. Submit, acompanhamento de status e retry de tarefas processadas pelo Gateway."
    },
    {
        "name": "Buscar Publicações",
        "description": "Endpoints para busca e processamento de publicações diárias via integração SOAP com Webjur. Inclui processamento de lotes (Bronze) e transformação para camada Silver."
    },
    {
        "name": "publicacoes",
        "description": "Processamento de publicações individuais e em lote. Classificação via LLM (N8N), verificação de duplicatas e transformação Bronze → Prata → Ouro."
    },
    {
        "name": "Marcar Publicações",
        "description": "Marcação de publicações como exportadas no sistema Webjur. Suporta marcação individual, por lote e auditoria completa."
    },
    {
        "name": "Auditoria",
        "description": "Consulta de logs de auditoria para marcação de publicações. Estatísticas, análise de falhas e rastreamento completo de operações."
    },
    {
        "name": "CPJ - Publicações",
        "description": "Integração com CPJ (Agnes CPJ-3C) para envio de publicações processadas. CRUD de publicações no sistema CPJ."
    },
    {
        "name": "CPJ - Pessoas",
        "description": "Gerenciamento de pessoas (clientes, partes) no sistema CPJ. CRUD e sincronização com processos."
    },
    {
        "name": "CPJ - Processos",
        "description": "Gerenciamento de processos judiciais no CPJ. Criação, atualização e consulta de processos por número CNJ."
    },
    {
        "name": "CPJ - Pedidos",
        "description": "Gerenciamento de pedidos (demandas) associados a processos no CPJ."
    },
    {
        "name": "CPJ - Envolvidos",
        "description": "Gerenciamento de partes envolvidas (autores, réus) em processos no CPJ."
    },
    {
        "name": "CPJ - Tramitação",
        "description": "Registro e consulta de movimentações processuais no CPJ. Histórico de tramitação."
    },
    {
        "name": "CPJ - Documentos",
        "description": "Upload e gerenciamento de documentos (PDFs, anexos) associados a processos no CPJ."
    },
    {
        "name": "DW LAW e-Protocol",
        "description": "Integração com DW LAW para protocolo eletrônico. Inserção e exclusão de processos, consultas e recebimento de callbacks."
    },
]

# FastAPI application
app = FastAPI(
    title="Worker API Gateway",
    description="""
## API Gateway para Processamento de Tarefas Camunda

Gateway centralizado para processamento assíncrono de tarefas dos workers do ecossistema Camunda BPM.

### Arquitetura

Este Gateway segue o **padrão de orquestração de workers**, onde:
- **Workers** buscam tarefas do Camunda BPM
- **Workers** submetem tarefas ao Gateway para processamento
- **Gateway** processa tarefas com lógica de negócio
- **Workers** monitoram status e retornam resultados ao Camunda

### Integrações

- **Camunda BPM Platform**: Orquestração de processos BPMN
- **MongoDB**: Persistência de tarefas e auditoria
- **Redis**: Cache e controle de estado
- **Webjur SOAP API**: Busca e marcação de publicações diárias
- **CPJ (Agnes CPJ-3C)**: Sistema jurídico para gestão de processos
- **DW LAW e-Protocol**: Sistema de protocolo eletrônico
- **N8N Webhook**: Classificação de publicações via LLM

### Fluxo de Dados

```
Camunda Worker → POST /tasks/submit → Gateway processa → Worker monitora /tasks/{id}/status → Retorna ao Camunda
```

### Ambientes

- **Local**: http://localhost:8000
- **Production**: Definido em variáveis de ambiente
    """,
    version="1.0.0",
    contact={
        "name": "Equipe de Desenvolvimento - Camunda Server",
        "email": "dev@exemplo.com.br",
        "url": "https://github.com/dias-costa/camunda-server-dc",
    },
    license_info={
        "name": "Proprietário",
        "url": "https://exemplo.com.br/license",
    },
    openapi_tags=tags_metadata,
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Ambiente de desenvolvimento local"
        },
        {
            "url": "https://api.producao.exemplo.com.br",
            "description": "Ambiente de produção"
        }
    ],
    lifespan=lifespan,
)

# Custom OpenAPI schema to add security schemes
def custom_openapi():
    """Customiza o schema OpenAPI para adicionar security schemes"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = app.openapi()

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key para autenticação. Obtida através de configuração de ambiente ou gestão de credenciais."
        }
    }

    # Add security to all paths (global requirement)
    # Note: Individual endpoints can override this by specifying their own security
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "security" not in operation:
                operation["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

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
