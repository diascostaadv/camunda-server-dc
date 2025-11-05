"""
Router para marcação de publicações como exportadas no Webjur
Endpoint para marcar publicações como exportadas via SOAP API após processamento bem-sucedido
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId

from services.intimation_service import get_intimation_client, IntimationService
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marcar-publicacoes", tags=["Marcar Publicações"])

# Configurações
settings = get_settings()


def get_mongo_client() -> MongoClient:
    """Obtém cliente MongoDB"""
    return MongoClient(settings.MONGODB_CONNECTION_STRING)


# ========== Modelos Pydantic ==========


class MarcarPublicacoesRequest(BaseModel):
    """Request para marcar publicações como exportadas"""

    cod_publicacoes: List[int] = Field(
        ...,
        description="Lista de códigos de publicações (cod_publicacao) para marcar como exportadas",
        min_length=1,
        max_length=3000,  # Limite da API Webjur
    )
    atualizar_mongodb: bool = Field(
        default=True,
        description="Se deve atualizar o status no MongoDB após marcar na API Webjur",
    )


class MarcarPublicacoesResponse(BaseModel):
    """Response da marcação de publicações"""

    sucesso: bool = Field(..., description="Se a marcação foi bem-sucedida")
    total_marcadas: int = Field(..., description="Total de publicações marcadas")
    cod_publicacoes: List[int] = Field(..., description="Códigos das publicações marcadas")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp da operação"
    )
    mongodb_atualizado: bool = Field(
        default=False, description="Se o MongoDB foi atualizado"
    )
    detalhes_mongodb: Dict[str, Any] = Field(
        default_factory=dict, description="Detalhes da atualização no MongoDB"
    )
    mensagem: str = Field(default="", description="Mensagem adicional")


# ========== Endpoints ==========


@router.post("/marcar-exportadas", response_model=MarcarPublicacoesResponse)
async def marcar_publicacoes_exportadas(
    request: MarcarPublicacoesRequest,
    soap_client: IntimationService = Depends(get_intimation_client),
    mongo_client: MongoClient = Depends(get_mongo_client),
):
    """
    Marca publicações como exportadas no Webjur via SOAP API

    Fluxo:
    1. Valida códigos de publicação
    2. Chama setPublicacoes() no Webjur para marcar como exportadas
    3. (Opcional) Atualiza status no MongoDB (publicacoes_bronze)
    4. Retorna resultado da operação

    Args:
        request: Dados da requisição com códigos de publicação
        soap_client: Cliente SOAP para API Webjur
        mongo_client: Cliente MongoDB para atualização de status

    Returns:
        MarcarPublicacoesResponse: Resultado da marcação
    """
    timestamp_inicio = datetime.now()

    logger.info(
        "Iniciando marcação de %d publicações como exportadas", len(request.cod_publicacoes)
    )

    try:
        # 1. Validar que temos códigos para marcar
        if not request.cod_publicacoes:
            raise HTTPException(
                status_code=400,
                detail="Lista de códigos de publicação está vazia",
            )

        # Limite máximo da API Webjur (3000 publicações)
        if len(request.cod_publicacoes) > 3000:
            raise HTTPException(
                status_code=400,
                detail=f"Máximo de 3000 publicações por requisição. Recebido: {len(request.cod_publicacoes)}",
            )

        # 2. Marcar como exportadas no Webjur via SOAP
        logger.info(
            "Chamando setPublicacoes() para %d códigos: %s...",
            len(request.cod_publicacoes),
            request.cod_publicacoes[:5],  # Mostra apenas os 5 primeiros no log
        )

        sucesso_webjur = soap_client.set_publicacoes(request.cod_publicacoes)

        if not sucesso_webjur:
            logger.error("Falha ao marcar publicações como exportadas no Webjur")
            raise HTTPException(
                status_code=500,
                detail="Erro ao marcar publicações como exportadas na API Webjur",
            )

        logger.info(
            "✅ Sucesso ao marcar %d publicações como exportadas no Webjur",
            len(request.cod_publicacoes),
        )

        # 3. Atualizar status no MongoDB se solicitado
        mongodb_atualizado = False
        detalhes_mongodb = {}

        if request.atualizar_mongodb:
            try:
                db = mongo_client[settings.MONGODB_DATABASE]
                collection = db["publicacoes_bronze"]

                # Atualizar documentos no MongoDB
                resultado = collection.update_many(
                    {"cod_publicacao": {"$in": request.cod_publicacoes}},
                    {
                        "$set": {
                            "marcada_exportada_webjur": True,
                            "timestamp_marcacao_exportada": timestamp_inicio,
                        }
                    },
                )

                mongodb_atualizado = True
                detalhes_mongodb = {
                    "documentos_encontrados": resultado.matched_count,
                    "documentos_atualizados": resultado.modified_count,
                }

                logger.info(
                    "MongoDB atualizado: %d documentos encontrados, %d modificados",
                    resultado.matched_count,
                    resultado.modified_count,
                )

            except Exception as exc:
                logger.error("Erro ao atualizar MongoDB: %s", exc)
                # Não falha a operação se MongoDB falhar (Webjur já foi marcado)
                detalhes_mongodb = {"erro": str(exc)}

        # 4. Preparar resposta
        mensagem = f"Marcadas {len(request.cod_publicacoes)} publicações como exportadas no Webjur"
        if mongodb_atualizado:
            mensagem += f" e {detalhes_mongodb.get('documentos_atualizados', 0)} registros atualizados no MongoDB"

        return MarcarPublicacoesResponse(
            sucesso=True,
            total_marcadas=len(request.cod_publicacoes),
            cod_publicacoes=request.cod_publicacoes,
            timestamp=timestamp_inicio,
            mongodb_atualizado=mongodb_atualizado,
            detalhes_mongodb=detalhes_mongodb,
            mensagem=mensagem,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao processar marcação de publicações: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar marcação: {str(exc)}",
        ) from exc


@router.post("/marcar-por-lote/{lote_id}", response_model=MarcarPublicacoesResponse)
async def marcar_publicacoes_por_lote(
    lote_id: str,
    soap_client: IntimationService = Depends(get_intimation_client),
    mongo_client: MongoClient = Depends(get_mongo_client),
):
    """
    Marca todas as publicações de um lote específico como exportadas

    Busca todas as publicações associadas a um lote no MongoDB e marca como exportadas

    Args:
        lote_id: ID do lote (ObjectId) no MongoDB
        soap_client: Cliente SOAP para API Webjur
        mongo_client: Cliente MongoDB

    Returns:
        MarcarPublicacoesResponse: Resultado da marcação
    """
    logger.info("Marcando publicações do lote %s como exportadas", lote_id)

    try:
        # 1. Validar ObjectId
        try:
            lote_obj_id = ObjectId(lote_id)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"ID de lote inválido: {lote_id}",
            ) from exc

        # 2. Buscar publicações do lote no MongoDB
        db = mongo_client[settings.MONGODB_DATABASE]
        publicacoes_collection = db["publicacoes_bronze"]

        publicacoes_cursor = publicacoes_collection.find(
            {"lote_id": str(lote_obj_id)}, {"cod_publicacao": 1}
        )

        cod_publicacoes = [
            pub["cod_publicacao"]
            for pub in publicacoes_cursor
            if "cod_publicacao" in pub
        ]

        if not cod_publicacoes:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhuma publicação encontrada para o lote {lote_id}",
            )

        logger.info(
            "Encontradas %d publicações no lote %s", len(cod_publicacoes), lote_id
        )

        # 3. Marcar como exportadas usando endpoint principal
        request = MarcarPublicacoesRequest(
            cod_publicacoes=cod_publicacoes, atualizar_mongodb=True
        )

        return await marcar_publicacoes_exportadas(request, soap_client, mongo_client)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao processar lote %s: %s", lote_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar lote: {str(exc)}",
        ) from exc


@router.post("/processar")
async def processar_marcacao_individual(
    task_data: Dict[str, Any],
    soap_client: IntimationService = Depends(get_intimation_client),
    mongo_client: MongoClient = Depends(get_mongo_client),
):
    """
    Endpoint dedicado para worker - marca UMA publicação como exportada

    Recebe task data do Camunda worker com:
    - task_id: ID da tarefa
    - variables: { cod_publicacao: int }

    Retorna formato compatível com worker:
    - sucesso: bool
    - mensagem: str
    - timestamp_marcacao: str
    """
    logger.info("Processando task de marcação: %s", task_data.get("task_id"))

    try:
        # Extrair variáveis da tarefa
        variables = task_data.get("variables", {})
        cod_publicacao = variables.get("cod_publicacao")

        if not cod_publicacao:
            return {
                "sucesso": False,
                "mensagem": "cod_publicacao não fornecido",
                "erro_validacao": True,
            }

        # Converter para int
        try:
            cod_publicacao = int(cod_publicacao)
        except (ValueError, TypeError):
            return {
                "sucesso": False,
                "mensagem": f"cod_publicacao inválido: {cod_publicacao}",
                "erro_validacao": True,
            }

        logger.info("Marcando publicação %d como exportada", cod_publicacao)

        # Chamar setPublicacoes() da API Webjur (serviço já existe)
        sucesso_webjur = soap_client.set_publicacoes([cod_publicacao])

        if not sucesso_webjur:
            logger.warning("Falha ao marcar publicação %d no Webjur", cod_publicacao)
            return {
                "sucesso": False,
                "mensagem": "Falha na chamada setPublicacoes() do Webjur",
                "cod_publicacao": cod_publicacao,
                "erro_webjur": True,
            }

        # Atualizar MongoDB
        timestamp_marcacao = datetime.now()
        db = mongo_client[settings.MONGODB_DATABASE]

        resultado_update = db.publicacoes_bronze.update_one(
            {"cod_publicacao": cod_publicacao},
            {
                "$set": {
                    "marcada_exportada_webjur": True,
                    "timestamp_marcacao_exportada": timestamp_marcacao,
                }
            },
        )

        logger.info(
            "✅ Publicação %d marcada com sucesso (MongoDB: %d doc atualizado)",
            cod_publicacao,
            resultado_update.modified_count,
        )

        return {
            "sucesso": True,
            "mensagem": f"Publicação {cod_publicacao} marcada como exportada",
            "cod_publicacao": cod_publicacao,
            "timestamp_marcacao": timestamp_marcacao.isoformat(),
            "mongodb_atualizado": resultado_update.modified_count > 0,
        }

    except Exception as exc:
        logger.error("Erro ao processar marcação: %s", exc)
        return {
            "sucesso": False,
            "mensagem": f"Erro interno: {str(exc)}",
            "erro_exception": True,
        }


@router.get("/status-exportacao/{cod_publicacao}")
async def verificar_status_exportacao(
    cod_publicacao: int,
    mongo_client: MongoClient = Depends(get_mongo_client),
):
    """
    Verifica o status de exportação de uma publicação específica

    Args:
        cod_publicacao: Código da publicação
        mongo_client: Cliente MongoDB

    Returns:
        Dict com status da publicação
    """
    try:
        db = mongo_client[settings.MONGODB_DATABASE]
        collection = db["publicacoes_bronze"]

        publicacao = collection.find_one(
            {"cod_publicacao": cod_publicacao},
            {
                "cod_publicacao": 1,
                "numero_processo": 1,
                "marcada_exportada_webjur": 1,
                "timestamp_marcacao_exportada": 1,
                "status": 1,
            },
        )

        if not publicacao:
            raise HTTPException(
                status_code=404,
                detail=f"Publicação com código {cod_publicacao} não encontrada",
            )

        return {
            "cod_publicacao": publicacao.get("cod_publicacao"),
            "numero_processo": publicacao.get("numero_processo", ""),
            "marcada_exportada_webjur": publicacao.get("marcada_exportada_webjur", False),
            "timestamp_marcacao": publicacao.get("timestamp_marcacao_exportada"),
            "status": publicacao.get("status", "desconhecido"),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao verificar status: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Erro ao verificar status: {str(exc)}"
        ) from exc
