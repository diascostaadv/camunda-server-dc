"""
Router para operações de Processos CPJ-3C
Endpoints: Consultar, Cadastrar, Atualizar processo
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cpj/processos", tags=["CPJ - Processos"])


# ==================== MODELS ====================


class ConsultarProcessosRequest(BaseModel):
    """Request para consultar processos"""

    filter: Dict[str, Any] = Field(..., description="Filtros de busca")
    sort: str = Field(default="ficha", description="Campo para ordenação")


class CadastrarProcessoRequest(BaseModel):
    """Request para cadastrar processo"""

    entrada: str = Field(..., description="Data de entrada (ISO)")
    materia: int = Field(..., description="Código da matéria")
    acao: str = Field(..., description="Sigla da ação")
    numero_processo: str = Field(..., description="Número do processo CNJ")
    juizo: str = Field(..., description="Sigla do juízo")
    oj_numero: int = Field(..., description="Número do órgão julgador")
    oj_sigla: str = Field(..., description="Sigla do órgão julgador")
    grau_risco: int = Field(..., description="Grau de risco", ge=0, le=100)
    acao_ativa_passiva: int = Field(..., description="Polo: 1=Ativa, 2=Passiva")
    valor_causa: Optional[float] = None
    valor_estimado: Optional[float] = None
    # Campos adicionais conforme doc...
    envolvidos: Optional[List[Dict[str, Any]]] = Field(None, description="Envolvidos")
    pedidos: Optional[List[Dict[str, Any]]] = Field(None, description="Pedidos")


class AtualizarProcessoRequest(BaseModel):
    """Request para atualizar processo"""

    update_data_hora: str = Field(..., description="Data/hora do registro")
    update_usuario: int = Field(..., description="ID do usuário")
    numero_processo: Optional[str] = Field(
        None, description="Número processo (só se nulo)"
    )
    fase: Optional[int] = None
    grau_risco: Optional[int] = Field(None, ge=0, le=100)
    valor_causa: Optional[float] = None
    valor_estimado: Optional[float] = None


# ==================== ENDPOINTS ====================


@router.post("/consultar")
async def consultar_processos(request: ConsultarProcessosRequest) -> Dict[str, Any]:
    """
    Consulta processos com filtros avançados (Seção 4.7)

    **Filtros suportados**:
    - pj: Número PJ
    - numero_processo: Número CNJ
    - nome_1, nome_2: Partes
    - ficha: Número da ficha
    """
    try:
        logger.info(f"🔍 Consultando processos - Filtros: {list(request.filter.keys())}")

        cpj_service = CPJService()
        processos = await cpj_service.consultar_processos(
            filters=request.filter, sort=request.sort
        )

        logger.info(f"✅ Encontrados {len(processos)} processos")
        return {"success": True, "total": len(processos), "processos": processos}

    except Exception as e:
        logger.error(f"❌ Erro ao consultar processos: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar processos: {str(e)}"
        )


@router.post("/cadastrar")
async def cadastrar_processo(request: CadastrarProcessoRequest) -> Dict[str, Any]:
    """Cadastra novo processo (Seção 4.8)"""
    try:
        logger.info(f"➕ Cadastrando processo: {request.numero_processo}")

        cpj_service = CPJService()
        result = await cpj_service.cadastrar_processo(request.dict(exclude_none=True))

        if result.get("success"):
            logger.info(f"✅ Processo cadastrado - PJ: {result.get('pj')}")
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Erro ao cadastrar processo"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao cadastrar processo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao cadastrar processo: {str(e)}"
        )


@router.post("/atualizar/{pj}")
async def atualizar_processo(
    pj: int, request: AtualizarProcessoRequest
) -> Dict[str, Any]:
    """Atualiza processo existente (Seção 4.9)"""
    try:
        logger.info(f"✏️ Atualizando processo PJ {pj}")

        cpj_service = CPJService()
        result = await cpj_service.atualizar_processo(
            pj, request.dict(exclude_none=True)
        )

        if result.get("success"):
            logger.info(f"✅ Processo PJ {pj} atualizado")
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Erro ao atualizar processo"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar processo: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao atualizar processo: {str(e)}"
        )
