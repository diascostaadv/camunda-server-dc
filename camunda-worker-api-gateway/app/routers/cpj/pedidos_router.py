"""
Router para operações de Pedidos CPJ-3C
Endpoints: Consultar, Cadastrar, Atualizar pedido
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cpj/pedidos", tags=["CPJ - Pedidos"])


class ConsultarPedidosRequest(BaseModel):
    filter: Dict[str, Any] = Field(..., description="Filtros (ex: pj)")


class CadastrarPedidoRequest(BaseModel):
    pedidos_data: List[Dict[str, Any]] = Field(..., description="Lista de pedidos")


class AtualizarPedidoRequest(BaseModel):
    update_data_hora: str
    update_usuario: int
    valor_inicial: float = None
    valor_estimado: float = None
    risco: int = None


@router.post("/consultar")
async def consultar_pedidos(request: ConsultarPedidosRequest) -> Dict[str, Any]:
    """Consulta pedidos de processos (Seção 4.10)"""
    try:
        cpj_service = CPJService()
        pedidos = await cpj_service.consultar_pedidos(filters=request.filter)
        return {"success": True, "total": len(pedidos), "pedidos": pedidos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cadastrar/{pj}")
async def cadastrar_pedido(pj: int, request: CadastrarPedidoRequest) -> Dict[str, Any]:
    """Cadastra novo(s) pedido(s) (Seção 4.11)"""
    try:
        cpj_service = CPJService()
        result = await cpj_service.cadastrar_pedido(pj, request.pedidos_data)
        if result.get("success"):
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/atualizar/{pj}/{sequencia}")
async def atualizar_pedido(
    pj: int, sequencia: int, request: AtualizarPedidoRequest
) -> Dict[str, Any]:
    """Atualiza pedido existente (Seção 4.12)"""
    try:
        cpj_service = CPJService()
        result = await cpj_service.atualizar_pedido(
            pj, sequencia, request.dict(exclude_none=True)
        )
        if result.get("success"):
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
