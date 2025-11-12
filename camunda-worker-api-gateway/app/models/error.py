"""
Error Response Models
Modelos padronizados para respostas de erro da API
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ErrorResponse(BaseModel):
    """
    Modelo padronizado para respostas de erro

    Utilizado em todos os endpoints para documentar erros HTTP
    e fornecer informações consistentes para retry logic
    """

    status: str = Field(
        default="error",
        description="Status da resposta (sempre 'error' para erros)"
    )

    error_code: str = Field(
        ...,
        description="Código do erro para identificação programática",
        examples=[
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "INTERNAL_ERROR",
            "SERVICE_UNAVAILABLE"
        ]
    )

    error_message: str = Field(
        ...,
        description="Mensagem descritiva do erro para debugging"
    )

    retry_allowed: bool = Field(
        ...,
        description="Indica se a operação pode ser retentada. True para erros temporários (5xx, 429, 408)"
    )

    timestamp: str = Field(
        ...,
        description="Timestamp ISO 8601 do momento do erro"
    )

    path: str = Field(
        ...,
        description="Path do endpoint que gerou o erro"
    )

    details: Optional[dict] = Field(
        default=None,
        description="Detalhes adicionais do erro (validação, campos faltantes, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "error_message": "Campo 'task_type' é obrigatório",
                    "retry_allowed": False,
                    "timestamp": "2024-01-15T10:30:00.000Z",
                    "path": "/tasks/submit",
                    "details": {
                        "field": "task_type",
                        "issue": "field required"
                    }
                },
                {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "error_message": "Task com ID 'abc123' não encontrada",
                    "retry_allowed": False,
                    "timestamp": "2024-01-15T10:35:00.000Z",
                    "path": "/tasks/abc123/status"
                },
                {
                    "status": "error",
                    "error_code": "SERVICE_UNAVAILABLE",
                    "error_message": "MongoDB connection temporarily unavailable",
                    "retry_allowed": True,
                    "timestamp": "2024-01-15T10:40:00.000Z",
                    "path": "/tasks/submit"
                }
            ]
        }
    }


class ValidationErrorResponse(BaseModel):
    """
    Modelo específico para erros de validação (422)

    Retornado automaticamente pelo FastAPI quando dados
    de entrada não passam na validação Pydantic
    """

    detail: list[dict] = Field(
        ...,
        description="Lista de erros de validação detectados"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": [
                        {
                            "type": "missing",
                            "loc": ["body", "task_type"],
                            "msg": "Field required",
                            "input": {}
                        },
                        {
                            "type": "string_type",
                            "loc": ["body", "worker_id"],
                            "msg": "Input should be a valid string",
                            "input": 12345
                        }
                    ]
                }
            ]
        }
    }


# Mapeamento de códigos HTTP para descrições de erro
HTTP_ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "**Bad Request** - Requisição inválida ou parâmetros malformados"
    },
    401: {
        "model": ErrorResponse,
        "description": "**Unauthorized** - API Key ausente ou inválida"
    },
    404: {
        "model": ErrorResponse,
        "description": "**Not Found** - Recurso não encontrado"
    },
    408: {
        "model": ErrorResponse,
        "description": "**Request Timeout** - Timeout ao processar requisição. Retry permitido."
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "**Validation Error** - Dados de entrada não passaram na validação"
    },
    429: {
        "model": ErrorResponse,
        "description": "**Rate Limit** - Limite de requisições excedido. Retry após aguardar."
    },
    500: {
        "model": ErrorResponse,
        "description": "**Internal Server Error** - Erro interno do servidor. Retry permitido."
    },
    502: {
        "model": ErrorResponse,
        "description": "**Bad Gateway** - Erro ao comunicar com serviço externo. Retry permitido."
    },
    503: {
        "model": ErrorResponse,
        "description": "**Service Unavailable** - Serviço temporariamente indisponível. Retry permitido."
    },
    504: {
        "model": ErrorResponse,
        "description": "**Gateway Timeout** - Timeout ao comunicar com serviço externo. Retry permitido."
    }
}
