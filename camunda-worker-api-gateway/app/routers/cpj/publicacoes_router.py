"""
Router para operações de Publicações CPJ-3C
Endpoints: Buscar publicações não vinculadas, Atualizar publicação
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cpj/publicacoes", tags=["CPJ - Publicações"])


# ==================== MODELS ====================


class BuscarPublicacoesRequest(BaseModel):
    """Request para buscar publicações não vinculadas"""

    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Filtros customizados (opcional)"
    )
    sort: str = Field(default="data_publicacao", description="Campo para ordenação")
    limit: int = Field(default=100, ge=1, le=1000, description="Limite de resultados")


class AtualizarPublicacaoRequest(BaseModel):
    """Request para atualizar publicação"""

    update_usuario: int = Field(..., description="ID do usuário que está atualizando")
    update_data_hora: str = Field(..., description="Data/hora atual do registro (ISO)")
    id_pessoa_atribuida: Optional[int] = Field(
        None, description="ID da pessoa atribuída"
    )
    id_motivo: Optional[int] = Field(None, description="ID do motivo")
    atr: Optional[Dict[str, Any]] = Field(
        None, description="Atributos customizados para workflow"
    )


# ==================== ENDPOINTS ====================


@router.post("/nao-vinculadas")
async def buscar_publicacoes_nao_vinculadas(
    request: BuscarPublicacoesRequest,
) -> Dict[str, Any]:
    """
    Busca publicações não vinculadas a processos (Seção 4.2 da API CPJ)

    **Critérios padrão**:
    - Situação do evento_tarefa = 0 (pendente)
    - id_processo da tramitação pai = nulo
    - Fluxo do evento pai = publicação

    **Returns**:
    - publicacoes: Lista de publicações encontradas
    - total: Total de publicações
    """
    try:
        logger.info(
            f"🔍 Buscando publicações não vinculadas - Limite: {request.limit}"
        )

        cpj_service = CPJService()
        publicacoes = await cpj_service.buscar_publicacoes_nao_vinculadas(
            filters=request.filters, sort=request.sort, limit=request.limit
        )

        logger.info(f"✅ Encontradas {len(publicacoes)} publicações não vinculadas")

        return {
            "success": True,
            "total": len(publicacoes),
            "publicacoes": publicacoes,
            "limit": request.limit,
            "sort": request.sort,
        }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar publicações não vinculadas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar publicações não vinculadas: {str(e)}",
        )


@router.post("/atualizar/{id_tramitacao}")
async def atualizar_publicacao(
    id_tramitacao: int, request: AtualizarPublicacaoRequest
) -> Dict[str, Any]:
    """
    Atualiza publicação existente (Seção 4.3 da API CPJ)

    **Permite atualizar**:
    - Pessoa atribuída
    - Motivo
    - Atributos customizados do workflow

    **Requisitos**:
    - Situação deve estar como "pendente"
    - Motivo deve estar nulo (para poder atualizar)

    **Returns**:
    - success: Se atualização foi bem-sucedida
    - message: Mensagem de retorno
    """
    try:
        logger.info(f"🔄 Atualizando publicação {id_tramitacao}")

        cpj_service = CPJService()

        # Montar dados de atualização
        update_data = {
            "update_usuario": request.update_usuario,
            "update_data_hora": request.update_data_hora,
        }

        if request.id_pessoa_atribuida is not None:
            update_data["id_pessoa_atribuida"] = request.id_pessoa_atribuida

        if request.id_motivo is not None:
            update_data["id_motivo"] = request.id_motivo

        if request.atr is not None:
            update_data["atr"] = request.atr

        result = await cpj_service.atualizar_publicacao(id_tramitacao, update_data)

        if result.get("success"):
            logger.info(f"✅ Publicação {id_tramitacao} atualizada com sucesso")
            return result
        else:
            logger.error(f"❌ Falha ao atualizar publicação: {result.get('message')}")
            raise HTTPException(
                status_code=400, detail=result.get("message", "Erro desconhecido")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar publicação {id_tramitacao}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao atualizar publicação: {str(e)}"
        )
