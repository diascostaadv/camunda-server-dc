"""
Router para operações de Envolvidos CPJ-3C
Endpoints: Consultar, Cadastrar, Atualizar envolvido
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cpj/envolvidos", tags=["CPJ - Envolvidos"])


class ConsultarEnvolvidosRequest(BaseModel):
    filter: Dict[str, Any] = Field(..., description="Filtros (ex: pj)")


class CadastrarEnvolvidoRequest(BaseModel):
    qualificacao: int = Field(..., description="Código da qualificação")
    pessoa: int = Field(..., description="Código da pessoa")
    responsavel: int = Field(..., description="Código do responsável")
    observacao: str = Field(default="", description="Observação")
    per_contingenciamento: float = Field(default=0.0, description="% contingência")


class AtualizarEnvolvidoRequest(BaseModel):
    update_data_hora: str
    update_usuario: int
    qualificacao: int = None
    pessoa: int = None
    responsavel: int = None
    observacao: str = None
    per_contingenciamento: float = None


@router.post("/consultar")
async def consultar_envolvidos(request: ConsultarEnvolvidosRequest) -> Dict[str, Any]:
    """Consulta envolvidos de processos (Seção 4.13)"""
    try:
        cpj_service = CPJService()
        envolvidos = await cpj_service.consultar_envolvidos(filters=request.filter)
        return {"success": True, "total": len(envolvidos), "envolvidos": envolvidos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cadastrar/{pj}")
async def cadastrar_envolvido(
    pj: int, request: CadastrarEnvolvidoRequest
) -> Dict[str, Any]:
    """Cadastra novo envolvido (Seção 4.14)"""
    try:
        cpj_service = CPJService()
        result = await cpj_service.cadastrar_envolvido(pj, request.dict())
        if result.get("success"):
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atualizar/{pj}/{sequencia}")
async def atualizar_envolvido(
    pj: int, sequencia: int, request: AtualizarEnvolvidoRequest
) -> Dict[str, Any]:
    """Atualiza envolvido existente (Seção 4.15)"""
    try:
        cpj_service = CPJService()
        result = await cpj_service.atualizar_envolvido(
            pj, sequencia, request.dict(exclude_none=True)
        )
        if result.get("success"):
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
