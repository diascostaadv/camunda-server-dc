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

        # Trabalha diretamente com dicionário (sem validação Pydantic)
        # Higieniza publicação
        pub_prata = publicacao_service.higienizar_publicacao(pub_bronze_doc)

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

        # Processa publicação (trabalha diretamente com dicionário)
        pub_prata = publicacao_service.higienizar_publicacao(pub_bronze_doc)

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

        # Garante que numero_processo sempre tenha um valor válido
        numero_processo_final = (
            pub_prata.numero_processo
            or pub_bronze_doc.get("numero_processo")
            or f"SEM_NUMERO_{publicacao_id}"
        )

        logger.info(
            f"✅ Publicação processada: {numero_processo_final} (prata: {pub_prata.numero_processo}, bronze: {pub_bronze_doc.get('numero_processo')})"
        )

        return {
            "status": "success",
            "task_id": task_data.task_id,
            "publicacao_id": str(
                result.inserted_id
            ),  # ID da publicação prata para próximos processos
            "publicacao_prata_id": str(result.inserted_id),
            "status_publicacao": pub_prata.status,
            "score_similaridade": pub_prata.score_similaridade,
            "classificacao": pub_prata.classificacao,
            "publicacoes_similares": pub_prata.publicacoes_similares,
            "message": f"Publicação processada com status: {pub_prata.status}",
            "numero_processo": numero_processo_final,
        }

    except Exception as e:
        logger.error(f"Erro ao processar task tratar_publicacao: {e}")
        return {"status": "error", "message": str(e), "task_id": task_data.task_id}


@router.post("/classificar")
async def classificar_publicacao(
    request: Dict[str, Any] = Body(
        ..., description="Request body with publicacao_id or task data"
    ),
    client: MongoClient = Depends(get_mongo_client),
):
    """
    Classifica uma publicação prata individual via integração N8N

    Endpoint para classificar uma publicação que já foi higienizada
    e está no formato prata (Bronze → Prata)

    Aceita dois formatos:
    1. {"publicacao_id": "..."}  - Chamada direta
    2. {"variables": {"publicacao_id": "..."}, ...}  - Chamada via worker

    Processo:
    1. Busca publicação prata no MongoDB
    2. Envia dados para N8N webhook para classificação via LLM
    3. Retorna resposta no formato esperado pelo BPMN (variável n8n_processing)
    """
    import httpx

    publicacao_id = None
    try:
        # Extrai publicacao_id do request (suporta ambos os formatos)
        publicacao_id = request.get("publicacao_id")

        # Se não encontrou diretamente, tenta em variables (formato do worker)
        if not publicacao_id and "variables" in request:
            publicacao_id = request.get("variables", {}).get("publicacao_id")

        if not publicacao_id:
            logger.error(f"publicacao_id não fornecido. Request: {request}")
            raise HTTPException(status_code=400, detail="publicacao_id é obrigatório")

        logger.info(f"🏷️ Classificando publicação: {publicacao_id}")

        db = client[settings.MONGODB_DATABASE]

        # Busca publicação prata
        pub_prata_doc = db.publicacoes_prata.find_one({"_id": ObjectId(publicacao_id)})

        if not pub_prata_doc:
            logger.error(
                f"❌ Publicação prata {publicacao_id} não encontrada no MongoDB"
            )
            raise HTTPException(
                status_code=404, detail="Publicação prata não encontrada"
            )

        # Converte para modelo
        pub_prata = PublicacaoPrata(**pub_prata_doc)

        # Busca publicação bronze para pegar texto original completo da Webjur
        pub_bronze_doc = db.publicacoes_bronze.find_one(
            {"cod_publicacao": pub_prata.publicacao_bronze_id}
        )

        logger.info(
            f"📤 Enviando publicação {publicacao_id} para N8N webhook: {settings.N8N_WEBHOOK_URL}"
        )

        # Prepara payload para N8N
        # Usa processo_publicacao do bronze (campo da Webjur com texto completo)
        # Fallback: texto_publicacao > texto_original se processo_publicacao não existir
        texto_para_classificar = (
            pub_bronze_doc.get("processo_publicacao")
            if pub_bronze_doc
            else (
                pub_bronze_doc.get("texto_publicacao")
                if pub_bronze_doc
                else pub_prata.texto_original or ""
            )
        )

        # Log de debug do campo usado
        logger.info(
            f"📝 Campo usado: processo_publicacao, tamanho: {len(texto_para_classificar)} chars"
        )

        n8n_payload = {
            "publicacao_prata_id": publicacao_id,  # Nome correto esperado pelo N8N
            "publicacao_id": publicacao_id,  # Mantido para retrocompatibilidade
            # ========= CAMPOS JÁ EXTRAÍDOS =========
            "numero_processo": pub_prata.numero_processo,  # Já limpo e validado
            "data_publicacao": (
                pub_prata.data_publicacao_original
                if hasattr(pub_prata, "data_publicacao_original")
                else str(pub_prata.data_publicacao)
            ),
            "fonte": pub_prata.fonte,
            "tribunal": pub_prata.tribunal,
            "diario_nome": pub_prata_doc.get("diario_nome", ""),
            # ========= TEXTOS PARA ANÁLISE =========
            "texto_publicacao": texto_para_classificar,
            "texto_original": pub_prata.texto_original,
            # ========= METADADOS =========
            "texto_length": len(texto_para_classificar),
            "campos_pre_extraidos": {
                "numero_processo": True,  # Indicar que já foi extraído
                "data_publicacao": True,
                "tribunal": True,
                "fonte": True,
            },
        }

        # LOG detalhado
        logger.info(f"📤 [N8N] Enviando payload:")
        logger.info(f"  - numero_processo: '{n8n_payload['numero_processo']}'")
        logger.info(f"  - texto_length: {n8n_payload['texto_length']} chars")
        logger.info(f"  - campos_pre_extraidos: {n8n_payload['campos_pre_extraidos']}")

        # Chama N8N webhook com timeout configurado
        async with httpx.AsyncClient(timeout=settings.N8N_TIMEOUT) as http_client:
            n8n_response = await http_client.post(
                settings.N8N_WEBHOOK_URL,
                json=n8n_payload,
                headers={"Content-Type": "application/json"},
            )
            n8n_response.raise_for_status()

            # Log da resposta para debug
            response_text = n8n_response.text
            logger.info(
                f"📥 N8N response ({len(response_text)} chars): {response_text[:500]}"
            )

            # Parse JSON
            if not response_text or response_text.strip() == "":
                logger.warning("⚠️ N8N retornou resposta vazia")
                n8n_data = {
                    "status": "error",
                    "status_code": 200,
                    "data": {"output": {}},
                    "error": "N8N retornou resposta vazia",
                }
            else:
                # Empacota resposta N8N na estrutura esperada pelo BPMN
                n8n_response_json = n8n_response.json()

                # N8N pode retornar array ou objeto - normaliza
                if isinstance(n8n_response_json, list) and len(n8n_response_json) > 0:
                    n8n_response_json = n8n_response_json[0]

                # ============ CORREÇÃO: Detectar formato N8N ============
                # Verificar se N8N já retorna no formato {"output": {...}}
                if "output" in n8n_response_json:
                    # N8N já retornou com "output", não duplicar
                    logger.info(
                        "📦 N8N retornou com estrutura 'output' - usando diretamente"
                    )
                    n8n_data = {
                        "status": "success",
                        "status_code": n8n_response.status_code,
                        "data": n8n_response_json,  # Já tem "output"
                    }
                else:
                    # N8N retornou objeto flat, empacotar em "output"
                    logger.info("📦 N8N retornou objeto flat - empacotando em 'output'")
                    n8n_data = {
                        "status": "success",
                        "status_code": n8n_response.status_code,
                        "data": {
                            "output": n8n_response_json  # Empacota resposta flat em data.output
                        },
                    }
                # ========================================================

                logger.info(
                    f"📦 Estrutura n8n_data criada: status={n8n_data['status']}, tem data.output={bool(n8n_data.get('data', {}).get('output'))}"
                )

        logger.info(f"✅ N8N processou publicação {publicacao_id} com sucesso")

        # Atualiza publicação com dados do N8N
        if n8n_data.get("data", {}).get("output"):
            output = n8n_data["data"]["output"]

            # ========= USAR CAMPOS PRÉ-EXTRAÍDOS SE N8N FALHAR =========
            # Se N8N retornou "não identificado", usar o que já temos
            numero_processo_final = output.get("numero_processo")
            if numero_processo_final in ["não identificado", "não informado", None, ""]:
                logger.warning(
                    f"⚠️ N8N não conseguiu extrair numero_processo, "
                    f"usando valor pré-extraído: '{pub_prata.numero_processo}'"
                )
                numero_processo_final = pub_prata.numero_processo

            # Aplicar mesmo fallback para outros campos críticos
            classificacao_final = output.get("classificacao") or "não classificada"
            nome_cliente_final = output.get("nome_cliente")
            if nome_cliente_final in ["não identificado", "não informado", None, ""]:
                nome_cliente_final = "não identificado"

            db.publicacoes_prata.update_one(
                {"_id": ObjectId(publicacao_id)},
                {
                    "$set": {
                        "numero_processo_n8n": output.get(
                            "numero_processo"
                        ),  # Salvar o que N8N retornou
                        "numero_processo": numero_processo_final,  # Usar melhor valor disponível
                        "classificacao": classificacao_final,
                        "justificativa_classificacao": output.get(
                            "justificativa_classificacao"
                        ),
                        "nome_cliente": nome_cliente_final,
                        "advogado_habilitado": output.get("advogado_habilitado"),
                        "status": "classificada",
                        "timestamps.classificada_em": datetime.utcnow().isoformat(),
                        "n8n_response": n8n_data,  # Salva resposta completa do N8N
                    }
                },
            )

            logger.info(
                f"✅ Publicação {publicacao_id} atualizada com classificação: {output.get('classificacao')}"
            )

        # Validar estrutura antes de retornar ao Camunda
        if not n8n_data.get("data"):
            logger.error(f"❌ ERRO: n8n_data.data é null: {n8n_data}")
            raise HTTPException(
                status_code=500, detail="Estrutura inválida: missing 'data' field"
            )

        if not n8n_data.get("data", {}).get("output"):
            logger.error(f"❌ ERRO: n8n_data.data.output é null: {n8n_data}")
            raise HTTPException(
                status_code=500,
                detail="Estrutura inválida: missing 'data.output' field",
            )

        logger.info(
            f"✅ Estrutura validada - retornando n8n_processing com {len(n8n_data['data']['output'])} campos"
        )

        # Retorna no formato esperado pelo BPMN
        return {
            "status": "success",
            "n8n_processing": n8n_data,  # Variável esperada pelo BPMN
            "publicacao_id": publicacao_id,
        }

    except httpx.TimeoutException:
        error_msg = f"Timeout ao chamar N8N webhook após {settings.N8N_TIMEOUT}s"
        logger.error(f"❌ {error_msg} - publicacao_id: {publicacao_id}")
        raise HTTPException(status_code=504, detail=error_msg)

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"N8N webhook retornou erro: {e.response.status_code} - {e.response.text}"
        )
        logger.error(f"❌ {error_msg} - publicacao_id: {publicacao_id}")
        raise HTTPException(status_code=502, detail=error_msg)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Erro ao classificar publicação {publicacao_id}: {e}")
        import traceback

        traceback.print_exc()
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
        "existe": bool,
        "total_encontradas": int
    }
    """
    try:
        # LOG DO REQUEST COMPLETO
        logger.info(f"🔍 [CPJ] Request recebido")
        logger.info(f"🔍 [CPJ] Request type: {type(request)}")
        logger.info(f"🔍 [CPJ] Request keys: {list(request.keys())}")
        logger.info(f"🔍 [CPJ] Request content: {request}")

        # Extrai numero_cnj do request (tentar múltiplos formatos)
        numero_cnj = (
            request.get("numero_cnj")
            or request.get("numero_processo")
            or request.get("variables", {}).get("numero_cnj")
            or request.get("variables", {}).get("numero_processo")
        )

        # LOG DO VALOR EXTRAÍDO
        logger.info(
            f"🔍 [CPJ] numero_cnj extraído: '{numero_cnj}' (type: {type(numero_cnj)})"
        )

        if not numero_cnj:
            logger.warning(
                f"⚠️ [CPJ] numero_cnj não fornecido. Request completo: {request} - retornando resultado vazio"
            )
            return {
                "status": "success",
                "numero_cnj": None,
                "processos": [],
                "existe": False,
                "total_encontradas": 0,
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"🔍 Verificando processo {numero_cnj} no CPJ...")

        # Busca processo no CPJ
        try:
            processos = await cpj_service.buscar_processo_por_numero(numero_cnj)
            logger.info(
                f"✅ Busca CPJ concluída - {len(processos)} processos encontrados"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Erro na busca CPJ para '{numero_cnj}': {e} - retornando lista vazia"
            )
            processos = []

        total_encontradas = len(processos)

        return {
            "status": "success",
            "numero_cnj": numero_cnj,
            "processos": processos,
            "existe": total_encontradas > 0,
            "total_encontradas": total_encontradas,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao verificar processo CPJ: {e}")
        raise HTTPException(status_code=500, detail=str(e))
