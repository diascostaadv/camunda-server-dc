"""
Router para endpoints de publicações judiciais
Implementa a API REST para o fluxo de publicações conforme BPMN
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pymongo import MongoClient
from bson import ObjectId

from core.config import Settings, get_settings
from models.publicacao import (
    ProcessamentoPublicacaoRequest,
    ProcessamentoLoteRequest,
    ProcessamentoLoteResponse,
    PublicacaoBronze,
    PublicacaoPrata,
    Lote,
    ResultadoDeduplicacao,
)
from models.buscar_request import TaskDataRequest
from services.publicacao_service import PublicacaoService
from services.deduplicacao_service import DeduplicacaoService
from services.lote_service import LoteService
from services.process_starter import ProcessStarter
from services.cpj_service import CPJService

logger = logging.getLogger(__name__)

# Criar router
router = APIRouter(
    prefix="/publicacoes",
    tags=["publicacoes"],
    responses={404: {"description": "Not found"}},
)

# Dependências globais
settings = get_settings()


def get_mongo_client() -> MongoClient:
    """Obtém cliente MongoDB"""
    return MongoClient(settings.MONGODB_CONNECTION_STRING)


def get_publicacao_service() -> PublicacaoService:
    """Obtém serviço de publicações"""
    return PublicacaoService()


def get_deduplicacao_service(
    client: MongoClient = Depends(get_mongo_client),
) -> DeduplicacaoService:
    """Obtém serviço de deduplicação"""
    return DeduplicacaoService(client, settings.MONGODB_DATABASE)


def get_lote_service(client: MongoClient = Depends(get_mongo_client)) -> LoteService:
    """Obtém serviço de lotes"""
    publicacao_service = PublicacaoService()
    deduplicacao_service = DeduplicacaoService(client, settings.MONGODB_DATABASE)
    return LoteService(
        client, publicacao_service, deduplicacao_service, settings.MONGODB_DATABASE
    )


def get_process_starter() -> ProcessStarter:
    """Obtém iniciador de processos"""
    return ProcessStarter(
        base_url=settings.CAMUNDA_URL,
        username=settings.CAMUNDA_USERNAME,
        password=settings.CAMUNDA_PASSWORD,
    )


def get_cpj_service() -> CPJService:
    """Obtém serviço CPJ"""
    return CPJService()


@router.post("/processar-lote", response_model=ProcessamentoLoteResponse)
async def processar_lote(
    request: ProcessamentoLoteRequest,
    lote_service: LoteService = Depends(get_lote_service),
    process_starter: ProcessStarter = Depends(get_process_starter),
):
    """
    Processa um lote de publicações

    Fluxo:
    1. Busca publicações bronze do lote
    2. Higieniza cada publicação (Bronze → Prata)
    3. Verifica duplicatas
    4. Classifica publicações
    5. Inicia processos no Camunda se solicitado
    """
    try:
        logger.info(f"Processando lote {request.lote_id}")

        # Processa lote
        resultado = lote_service.processar_lote(
            lote_id=request.lote_id,
            processar_em_paralelo=request.processar_em_paralelo,
            max_paralelo=request.max_paralelo,
            continuar_em_erro=request.continuar_em_erro,
            executar_classificacao=request.executar_classificacao,
            executar_deduplicacao=request.executar_deduplicacao,
        )

        # Inicia processos no Camunda se solicitado
        if request.iniciar_processos_camunda and resultado.publicacoes_prata_ids:
            logger.info(
                f"Iniciando {len(resultado.publicacoes_prata_ids)} processos no Camunda"
            )

            # Busca publicações prata processadas
            client = get_mongo_client()
            db = client[settings.MONGODB_DATABASE]

            for prata_id in resultado.publicacoes_prata_ids[
                :10
            ]:  # Limita para evitar sobrecarga
                try:
                    # Busca publicação prata
                    pub_prata = db.publicacoes_prata.find_one(
                        {"_id": ObjectId(prata_id)}
                    )
                    if pub_prata and pub_prata.get("status") != "repetida":
                        # Prepara variáveis para o processo
                        variables = {
                            "publicacao_id": str(pub_prata["_id"]),
                            "numero_processo": pub_prata["numero_processo"],
                            "data_publicacao": pub_prata["data_publicacao_original"],
                            "texto_publicacao": pub_prata["texto_original"],
                            "fonte": pub_prata["fonte"],
                            "tribunal": pub_prata["tribunal"],
                            "instancia": pub_prata["instancia"],
                            "status": pub_prata["status"],
                            "score_similaridade": pub_prata.get(
                                "score_similaridade", 0
                            ),
                            "classificacao": pub_prata.get("classificacao", {}),
                        }

                        # Inicia processo
                        instance = process_starter.start_process_with_variables(
                            process_key="processar_publicacao_individual",
                            variables=variables,
                            business_key=f"pub_{pub_prata['numero_processo']}_{prata_id}",
                        )

                        # Atualiza publicação com ID da instância
                        if instance:
                            db.publicacoes_prata.update_one(
                                {"_id": ObjectId(prata_id)},
                                {"$set": {"camunda_instance_id": instance["id"]}},
                            )

                except Exception as e:
                    logger.error(
                        f"Erro ao iniciar processo para publicação {prata_id}: {e}"
                    )

        return resultado

    except Exception as e:
        logger.error(f"Erro ao processar lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processar-publicacao")
async def processar_publicacao_individual(
    request: ProcessamentoPublicacaoRequest,
    publicacao_service: PublicacaoService = Depends(get_publicacao_service),
    deduplicacao_service: DeduplicacaoService = Depends(get_deduplicacao_service),
    client: MongoClient = Depends(get_mongo_client),
):
    """
    Processa uma publicação individual

    Fluxo:
    1. Busca publicação bronze
    2. Higieniza (Bronze → Prata)
    3. Verifica duplicatas se solicitado
    4. Classifica se solicitado
    5. Salva resultado
    """
    try:
        db = client[settings.MONGODB_DATABASE]

        # Busca publicação bronze
        pub_bronze_doc = db.publicacoes_bronze.find_one(
            {"_id": ObjectId(request.publicacao_bronze_id)}
        )

        if not pub_bronze_doc:
            raise HTTPException(
                status_code=404, detail="Publicação bronze não encontrada"
            )

        # Converte para modelo
        pub_bronze = PublicacaoBronze(**pub_bronze_doc)

        # Higieniza publicação
        pub_prata = publicacao_service.higienizar_publicacao(pub_bronze)

        # Verifica duplicatas se solicitado
        if request.executar_deduplicacao:
            resultado_dedup = deduplicacao_service.verificar_duplicata(
                pub_prata, request.score_minimo_similaridade
            )
            pub_prata.status = resultado_dedup.status_recomendado
            pub_prata.score_similaridade = resultado_dedup.score_similaridade
            pub_prata.publicacoes_similares = resultado_dedup.publicacoes_similares

        # Classifica se solicitado
        if request.executar_classificacao:
            tipo, confianca = publicacao_service.identificar_tipo_publicacao(
                pub_prata.texto_limpo
            )
            urgente, prazo = publicacao_service.calcular_urgencia(
                pub_prata.texto_limpo, tipo
            )
            entidades = publicacao_service.extrair_entidades(pub_prata.texto_limpo)

            pub_prata.classificacao = {
                "tipo": tipo,
                "urgente": urgente,
                "prazo_dias": prazo,
                "confianca": confianca,
                "entidades": entidades,
            }

        # Salva publicação prata
        result = db.publicacoes_prata.insert_one(pub_prata.dict())

        # Registra hash se não for duplicata
        if pub_prata.status != "repetida":
            deduplicacao_service.registrar_hash(pub_prata)

        # Atualiza status da publicação bronze
        db.publicacoes_bronze.update_one(
            {"_id": ObjectId(request.publicacao_bronze_id)},
            {"$set": {"status": "processada"}},
        )

        return {
            "success": True,
            "publicacao_prata_id": str(result.inserted_id),
            "status": pub_prata.status,
            "score_similaridade": pub_prata.score_similaridade,
            "classificacao": pub_prata.classificacao,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar publicação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verificar-duplicata", response_model=ResultadoDeduplicacao)
async def verificar_duplicata(
    publicacao_prata_id: str = Body(..., description="ID da publicação prata"),
    score_minimo: float = Body(70.0, description="Score mínimo de similaridade"),
    deduplicacao_service: DeduplicacaoService = Depends(get_deduplicacao_service),
    client: MongoClient = Depends(get_mongo_client),
):
    """
    Verifica se uma publicação é duplicata

    Retorna resultado da análise com score e publicações similares
    """
    try:
        db = client[settings.MONGODB_DATABASE]

        # Busca publicação prata
        pub_prata_doc = db.publicacoes_prata.find_one(
            {"_id": ObjectId(publicacao_prata_id)}
        )

        if not pub_prata_doc:
            raise HTTPException(
                status_code=404, detail="Publicação prata não encontrada"
            )

        # Converte para modelo
        pub_prata = PublicacaoPrata(**pub_prata_doc)

        # Verifica duplicata
        resultado = deduplicacao_service.verificar_duplicata(pub_prata, score_minimo)

        # Atualiza publicação com resultado
        db.publicacoes_prata.update_one(
            {"_id": ObjectId(publicacao_prata_id)},
            {
                "$set": {
                    "status": resultado.status_recomendado,
                    "score_similaridade": resultado.score_similaridade,
                    "publicacoes_similares": resultado.publicacoes_similares,
                }
            },
        )

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar duplicata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buscar-lote/{lote_id}")
async def buscar_lote_por_id(
    lote_id: str,
    incluir_publicacoes: bool = Query(False, description="Incluir publicações do lote"),
    lote_service: LoteService = Depends(get_lote_service),
):
    """
    Busca um lote por ID

    Retorna dados do lote e opcionalmente suas publicações
    """
    try:
        lote = lote_service.buscar_lote_por_id(lote_id)

        if not lote:
            raise HTTPException(status_code=404, detail="Lote não encontrado")

        if not incluir_publicacoes:
            # Remove publicações se não solicitadas
            lote.pop("publicacoes", None)

        return lote

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processar-task-lote")
async def processar_task_buscar_lote(
    task_data: TaskDataRequest, lote_service: LoteService = Depends(get_lote_service)
):
    """
    Processa task de buscar lote por ID vinda do Camunda

    Este endpoint é chamado pelo worker quando recebe uma task
    do tópico 'buscar_lote_por_id'
    """
    try:
        logger.info(f"Processando task buscar_lote: {task_data.task_id}")

        # Extrai lote_id das variáveis
        lote_id = task_data.variables.get("lote_id")

        if not lote_id:
            return {
                "status": "error",
                "message": "lote_id não fornecido nas variáveis",
                "task_id": task_data.task_id,
            }

        # Busca lote com publicações
        lote = lote_service.buscar_lote_por_id(lote_id)

        if not lote:
            return {
                "status": "error",
                "message": f"Lote {lote_id} não encontrado",
                "task_id": task_data.task_id,
            }

        # Prepara lista de IDs das publicações
        publicacoes_ids = []
        if "publicacoes" in lote:
            publicacoes_ids = [str(pub["_id"]) for pub in lote["publicacoes"]]

        return {
            "status": "success",
            "task_id": task_data.task_id,
            "lote_id": lote_id,
            "total_publicacoes": lote.get("total_publicacoes", 0),
            "publicacoes_ids": publicacoes_ids,
            "status_lote": lote.get("status", "desconhecido"),
            "message": f"Lote {lote_id} encontrado com {len(publicacoes_ids)} publicações",
        }

    except Exception as e:
        logger.error(f"Erro ao processar task buscar_lote: {e}")
        return {"status": "error", "message": str(e), "task_id": task_data.task_id}


@router.post("/processar-task-publicacao")
async def processar_task_tratar_publicacao(
    task_data: TaskDataRequest,
    publicacao_service: PublicacaoService = Depends(get_publicacao_service),
    deduplicacao_service: DeduplicacaoService = Depends(get_deduplicacao_service),
    client: MongoClient = Depends(get_mongo_client),
):
    """
    Processa task de tratar publicação vinda do Camunda

    Este endpoint é chamado pelo worker quando recebe uma task
    do tópico 'tratar_publicacao'
    """
    try:
        logger.info(f"Processando task tratar_publicacao: {task_data.task_id}")

        db = client[settings.MONGODB_DATABASE]

        # Extrai publicacao_id das variáveis
        publicacao_id = task_data.variables.get("publicacao_id")

        if not publicacao_id:
            return {
                "status": "error",
                "message": "publicacao_id não fornecido nas variáveis",
                "task_id": task_data.task_id,
            }

        # Busca publicação bronze
        pub_bronze_doc = db.publicacoes_bronze.find_one(
            {"_id": ObjectId(publicacao_id)}
        )

        if not pub_bronze_doc:
            return {
                "status": "error",
                "message": f"Publicação {publicacao_id} não encontrada",
                "task_id": task_data.task_id,
            }

        # Processa publicação
        pub_bronze = PublicacaoBronze(**pub_bronze_doc)
        pub_prata = publicacao_service.higienizar_publicacao(pub_bronze)

        # Verifica duplicatas
        resultado_dedup = deduplicacao_service.verificar_duplicata(pub_prata)
        pub_prata.status = resultado_dedup.status_recomendado
        pub_prata.score_similaridade = resultado_dedup.score_similaridade
        pub_prata.publicacoes_similares = resultado_dedup.publicacoes_similares

        # Classifica
        tipo, confianca = publicacao_service.identificar_tipo_publicacao(
            pub_prata.texto_limpo
        )
        urgente, prazo = publicacao_service.calcular_urgencia(
            pub_prata.texto_limpo, tipo
        )

        pub_prata.classificacao = {
            "tipo": tipo,
            "urgente": urgente,
            "prazo_dias": prazo,
            "confianca": confianca,
        }

        # Salva publicação prata
        result = db.publicacoes_prata.insert_one(pub_prata.dict())

        # Registra hash se não for duplicata
        if pub_prata.status != "repetida":
            deduplicacao_service.registrar_hash(pub_prata)

        # Atualiza publicação bronze
        db.publicacoes_bronze.update_one(
            {"_id": ObjectId(publicacao_id)}, {"$set": {"status": "processada"}}
        )

        return {
            "status": "success",
            "task_id": task_data.task_id,
            "publicacao_prata_id": str(result.inserted_id),
            "status_publicacao": pub_prata.status,
            "score_similaridade": pub_prata.score_similaridade,
            "classificacao": pub_prata.classificacao,
            "publicacoes_similares": pub_prata.publicacoes_similares,
            "message": f"Publicação processada com status: {pub_prata.status}",
        }

    except Exception as e:
        logger.error(f"Erro ao processar task tratar_publicacao: {e}")
        return {"status": "error", "message": str(e), "task_id": task_data.task_id}


@router.post("/classificar")
async def classificar_publicacao(
    request: Dict[str, Any] = Body(..., description="Request body with publicacao_id"),
    publicacao_service: PublicacaoService = Depends(get_publicacao_service),
    client: MongoClient = Depends(get_mongo_client),
):
    """
    Classifica uma publicação prata individual

    Endpoint para classificar uma publicação que já foi higienizada
    e está no formato prata (Bronze → Prata)
    """
    try:
        # Extrai publicacao_id do request
        publicacao_id = request.get("publicacao_id")
        if not publicacao_id:
            raise HTTPException(status_code=400, detail="publicacao_id é obrigatório")

        logger.info(f"Classificando publicação: {publicacao_id}")

        db = client[settings.MONGODB_DATABASE]

        # Busca publicação prata
        pub_prata_doc = db.publicacoes_prata.find_one({"_id": ObjectId(publicacao_id)})

        if not pub_prata_doc:
            raise HTTPException(
                status_code=404, detail="Publicação prata não encontrada"
            )

        # Converte para modelo
        pub_prata = PublicacaoPrata(**pub_prata_doc)

        # Classifica publicação
        tipo, confianca = publicacao_service.identificar_tipo_publicacao(
            pub_prata.texto_limpo
        )
        urgente, prazo = publicacao_service.calcular_urgencia(
            pub_prata.texto_limpo, tipo
        )
        entidades = publicacao_service.extrair_entidades(pub_prata.texto_limpo)

        classificacao = {
            "tipo": tipo,
            "urgente": urgente,
            "prazo_dias": prazo,
            "confianca": confianca,
            "entidades": entidades,
        }

        # Atualiza publicação com classificação
        db.publicacoes_prata.update_one(
            {"_id": ObjectId(publicacao_id)},
            {
                "$set": {
                    "classificacao": classificacao,
                    "status": "classificada",
                    "timestamps.classificada_em": datetime.utcnow().isoformat(),
                }
            },
        )

        logger.info(
            f"✅ Publicação {publicacao_id} classificada como {tipo} (confiança: {confianca:.2f})"
        )

        return {
            "success": True,
            "publicacao_id": publicacao_id,
            "classificacao": classificacao,
            "status": "classificada",
            "message": f"Publicação classificada como {tipo} com {confianca:.2f}% de confiança",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao classificar publicação {publicacao_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estatisticas")
async def obter_estatisticas(client: MongoClient = Depends(get_mongo_client)):
    """
    Obtém estatísticas gerais do sistema de publicações
    """
    try:
        db = client[settings.MONGODB_DATABASE]

        # Conta documentos
        total_lotes = db.lotes.count_documents({})
        total_bronze = db.publicacoes_bronze.count_documents({})
        total_prata = db.publicacoes_prata.count_documents({})
        total_hashes = db.hashes.count_documents({})

        # Estatísticas por status
        status_bronze = list(
            db.publicacoes_bronze.aggregate(
                [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
            )
        )

        status_prata = list(
            db.publicacoes_prata.aggregate(
                [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
            )
        )

        # Estatísticas por classificação
        tipos_publicacao = list(
            db.publicacoes_prata.aggregate(
                [{"$group": {"_id": "$classificacao.tipo", "count": {"$sum": 1}}}]
            )
        )

        return {
            "totais": {
                "lotes": total_lotes,
                "publicacoes_bronze": total_bronze,
                "publicacoes_prata": total_prata,
                "hashes_registradas": total_hashes,
            },
            "status_bronze": {
                item["_id"]: item["count"] for item in status_bronze if item["_id"]
            },
            "status_prata": {
                item["_id"]: item["count"] for item in status_prata if item["_id"]
            },
            "tipos_publicacao": {
                item["_id"]: item["count"] for item in tipos_publicacao if item["_id"]
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verificar-processo-cnj")
async def verificar_processo_cnj(
    request: Dict[str, Any] = Body(...),
    cpj_service: CPJService = Depends(get_cpj_service),
):
    """
    Verifica se processo existe no CPJ por número CNJ

    Request body: {"numero_cnj": "0000000-00.0000.0.00.0000"}
    Response: {
        "status": "success",
        "processos": [...],
        "total_encontrados": int
    }
    """
    try:
        # Extrai numero_cnj do request
        numero_cnj = request.get("numero_cnj")
        if not numero_cnj:
            raise HTTPException(status_code=400, detail="numero_cnj é obrigatório")

        logger.info(f"🔍 Verificando processo {numero_cnj} no CPJ...")

        # Busca processo no CPJ
        processos = await cpj_service.buscar_processo_por_numero(numero_cnj)

        logger.info(f"✅ Busca CPJ concluída - {len(processos)} processos encontrados")

        return {
            "status": "success",
            "numero_cnj": numero_cnj,
            "processos": processos,
            "total_encontrados": len(processos),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar processo CPJ: {e}")
        raise HTTPException(status_code=500, detail=str(e))
