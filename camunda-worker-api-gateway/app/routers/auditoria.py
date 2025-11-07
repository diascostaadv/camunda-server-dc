"""
Router para consulta de logs de auditoria de marcação de publicações
Endpoints para visualizar histórico completo de tentativas de marcação
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pymongo import MongoClient

from models.auditoria import (
    ConsultaLogRequest,
    ConsultaLogResponse,
    LogMarcacaoPublicacao,
    StatusMarcacao,
)
from services.auditoria_service import AuditoriaService
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])

# Configurações
settings = get_settings()


def get_mongo_client() -> MongoClient:
    """Obtém cliente MongoDB"""
    return MongoClient(settings.MONGODB_CONNECTION_STRING)


def get_auditoria_service(
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> AuditoriaService:
    """Obtém serviço de auditoria"""
    return AuditoriaService(mongo_client, database_name=settings.MONGODB_DATABASE)


@router.get("/marcacoes", response_model=ConsultaLogResponse)
async def consultar_logs_marcacao(
    cod_publicacao: Optional[int] = Query(None, description="Código da publicação"),
    lote_id: Optional[str] = Query(None, description="ID do lote"),
    status: Optional[StatusMarcacao] = Query(None, description="Status da marcação"),
    data_inicio: Optional[datetime] = Query(
        None, description="Data inicial (ISO format)"
    ),
    data_fim: Optional[datetime] = Query(None, description="Data final (ISO format)"),
    apenas_falhas: bool = Query(False, description="Retornar apenas falhas"),
    limite: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    auditoria_service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Consulta logs de marcação com filtros

    Permite filtrar por:
    - Código de publicação específica
    - Lote específico
    - Status (sucesso, falha_webjur, etc.)
    - Intervalo de datas
    - Apenas falhas

    Retorna logs com estatísticas agregadas.
    """
    try:
        filtros = ConsultaLogRequest(
            cod_publicacao=cod_publicacao,
            lote_id=lote_id,
            status=status,
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_falhas=apenas_falhas,
            limite=limite,
            offset=offset,
        )

        resultado = auditoria_service.consultar_logs(filtros)

        logger.info(
            f"Consulta de logs: {resultado.total_registros} registros encontrados"
        )
        return resultado

    except Exception as e:
        logger.error(f"Erro ao consultar logs: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar logs: {str(e)}")


@router.get("/marcacoes/publicacao/{cod_publicacao}", response_model=LogMarcacaoPublicacao)
async def obter_log_publicacao(
    cod_publicacao: int,
    auditoria_service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Obtém o log mais recente de uma publicação específica

    Útil para verificar rapidamente o status de marcação de uma publicação.
    """
    try:
        log = auditoria_service.obter_log_por_publicacao(cod_publicacao)

        if not log:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum log de marcação encontrado para publicação {cod_publicacao}",
            )

        return log

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter log da publicação {cod_publicacao}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter log: {str(e)}"
        )


@router.get("/marcacoes/lote/{lote_id}/estatisticas")
async def obter_estatisticas_lote(
    lote_id: str,
    auditoria_service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Obtém estatísticas de marcação de um lote específico

    Retorna:
    - Total de publicações
    - Sucessos
    - Falhas
    - Total de tentativas
    - Duração total

    Útil para dashboards e relatórios.
    """
    try:
        estatisticas = auditoria_service.obter_estatisticas_lote(lote_id)

        if not estatisticas or estatisticas.get("total_publicacoes", 0) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma estatística encontrada para lote {lote_id}",
            )

        return {
            "lote_id": lote_id,
            "estatisticas": estatisticas,
            "timestamp_consulta": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do lote {lote_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}"
        )


@router.get("/marcacoes/resumo")
async def obter_resumo_geral(
    data_inicio: Optional[datetime] = Query(
        None, description="Data inicial (ISO format)"
    ),
    data_fim: Optional[datetime] = Query(None, description="Data final (ISO format)"),
    auditoria_service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Obtém resumo geral de marcações

    Estatísticas agregadas para um período específico:
    - Total de marcações
    - Taxa de sucesso
    - Distribuição por status
    - Duração média
    """
    try:
        filtros = ConsultaLogRequest(
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=1,  # Não precisamos dos logs, apenas estatísticas
        )

        resultado = auditoria_service.consultar_logs(filtros)

        # Calcular métricas adicionais
        estatisticas = resultado.estatisticas
        por_status = estatisticas.get("por_status", {})

        total = estatisticas.get("total_registros", 0)
        sucessos = por_status.get("sucesso", {}).get("count", 0)
        taxa_sucesso = (sucessos / total * 100) if total > 0 else 0

        return {
            "total_marcacoes": total,
            "sucessos": sucessos,
            "falhas": total - sucessos,
            "taxa_sucesso_percentual": round(taxa_sucesso, 2),
            "distribuicao_por_status": por_status,
            "periodo": {
                "data_inicio": data_inicio.isoformat() if data_inicio else None,
                "data_fim": data_fim.isoformat() if data_fim else None,
            },
            "timestamp_consulta": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro ao obter resumo geral: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter resumo: {str(e)}"
        )


@router.get("/marcacoes/falhas/recentes")
async def obter_falhas_recentes(
    limite: int = Query(50, ge=1, le=500, description="Limite de resultados"),
    auditoria_service: AuditoriaService = Depends(get_auditoria_service),
):
    """
    Obtém falhas de marcação mais recentes

    Útil para monitoramento e alertas.
    Retorna apenas marcações que falharam, ordenadas por data mais recente.
    """
    try:
        filtros = ConsultaLogRequest(apenas_falhas=True, limite=limite, offset=0)

        resultado = auditoria_service.consultar_logs(filtros)

        return {
            "total_falhas": resultado.total_registros,
            "falhas_recentes": [
                {
                    "cod_publicacao": log.cod_publicacao,
                    "lote_id": log.lote_id,
                    "status": log.status_atual,
                    "total_tentativas": log.total_tentativas,
                    "timestamp_ultima_tentativa": log.timestamp_ultima_tentativa,
                    "ultima_mensagem_erro": (
                        log.tentativas[-1].mensagem_erro if log.tentativas else None
                    ),
                }
                for log in resultado.logs
            ],
            "timestamp_consulta": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro ao obter falhas recentes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter falhas: {str(e)}"
        )
