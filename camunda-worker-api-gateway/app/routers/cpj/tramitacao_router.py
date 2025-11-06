"""
Router para operações de Tramitação CPJ-3C (Andamentos e Tarefas)
Endpoints: Cadastrar andamento, Cadastrar tarefa, Atualizar tarefa
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cpj/tramitacao", tags=["CPJ - Tramitação"])


class CadastrarAndamentoRequest(BaseModel):
    evento: str = Field(..., description="Código do evento")
    texto: str = Field(..., description="Texto do andamento")
    data_hora_lan: Optional[str] = Field(
        None, description="Data/hora lançamento (ISO)"
    )
    interno: int = Field(default=0, description="0=Não, 1=Sim", ge=0, le=1)


class CadastrarTarefaRequest(BaseModel):
    evento: str = Field(..., description="Código do evento")
    texto: str = Field(..., description="Texto da tarefa")
    id_pessoa_solicitada: int = Field(..., description="ID pessoa solicitante")
    id_pessoa_atribuida: Optional[int] = Field(None, description="ID pessoa atribuída")
    ag_data_hora: str = Field(..., description="Data/hora agendamento (ISO)")


class AtualizarTarefaRequest(BaseModel):
    update_data_hora: str = Field(..., description="Data/hora do registro")
    update_usuario: int = Field(..., description="ID do usuário")
    id_tramitacao_motivo: Optional[int] = Field(None, description="ID do motivo")
    id_tramitacao_situacao: Optional[int] = Field(None, description="ID da situação")


@router.post("/andamento/cadastrar/{pj}")
async def cadastrar_andamento(
    pj: int, request: CadastrarAndamentoRequest
) -> Dict[str, Any]:
    """
    Cadastra novo andamento em processo (Seção 4.16)

    **Marca se andamento é interno** (segue padrão do evento se não enviado)
    """
    try:
        logger.info(f"➕ Cadastrando andamento no processo PJ {pj}")

        cpj_service = CPJService()
        result = await cpj_service.cadastrar_andamento(pj, request.dict())

        if result.get("success"):
            logger.info(
                f"✅ Andamento cadastrado - ID: {result.get('id_tramitacao')}"
            )
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tarefa/cadastrar/{pj}")
async def cadastrar_tarefa(
    pj: int, request: CadastrarTarefaRequest
) -> Dict[str, Any]:
    """
    Cadastra nova tarefa em processo (Seção 4.17)

    **Se pessoa atribuída não preenchida**, segue regra de eventos/equipes
    """
    try:
        logger.info(f"➕ Cadastrando tarefa no processo PJ {pj}")

        cpj_service = CPJService()
        result = await cpj_service.cadastrar_tarefa(pj, request.dict())

        if result.get("success"):
            logger.info(f"✅ Tarefa cadastrada - ID: {result.get('id_tramitacao')}")
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tarefa/atualizar/{id_tramitacao}")
async def atualizar_tarefa(
    id_tramitacao: int, request: AtualizarTarefaRequest
) -> Dict[str, Any]:
    """
    Atualiza tarefa existente (Seção 4.18)

    **Permite atualizar motivo e situação** desde que evento/fluxo permitam
    """
    try:
        logger.info(f"✏️ Atualizando tarefa {id_tramitacao}")

        cpj_service = CPJService()
        result = await cpj_service.atualizar_tarefa(id_tramitacao, request.dict())

        if result.get("success"):
            logger.info(f"✅ Tarefa {id_tramitacao} atualizada")
            return result
        raise HTTPException(status_code=400, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
