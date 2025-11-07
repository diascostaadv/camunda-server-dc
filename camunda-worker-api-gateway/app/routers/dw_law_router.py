"""
Router FastAPI para integração DW LAW e-Protocol
Endpoints para processar tasks Camunda e receber callbacks
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from pymongo import MongoClient

from core.config import settings
from models.dw_law import (
    InserirProcessosRequest,
    ExcluirProcessosRequest,
    ConsultarProcessoRequest,
    DWLawResponse,
    ProcessoDWLaw,
    ConsultaProcessoDWLaw,
    CallbackDWLaw
)
from services.dw_law_service import DWLawService
from services.camunda_message_service import CamundaMessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dw-law", tags=["DW LAW e-Protocol"])

# MongoDB client (será inicializado no startup)
db_client: MongoClient = None
db = None


# ==================== DEPENDENCY INJECTION ====================

def get_dw_law_service() -> DWLawService:
    """Dependency para obter serviço DW LAW"""
    return DWLawService()


def get_camunda_service() -> CamundaMessageService:
    """Dependency para obter serviço Camunda"""
    return CamundaMessageService()


def get_database():
    """Dependency para obter database MongoDB"""
    global db
    if db is None:
        global db_client
        db_client = MongoClient(
            settings.MONGODB_URI,
            **settings.get_mongodb_connection_options()
        )
        db = db_client[settings.MONGODB_DATABASE]
    return db


# ==================== ENDPOINTS DE PROCESSAMENTO ====================

@router.post("/inserir-processos", response_model=DWLawResponse)
async def inserir_processos(
    request: InserirProcessosRequest,
    dw_service: DWLawService = Depends(get_dw_law_service),
    database = Depends(get_database)
):
    """
    Insere processos no DW LAW e-Protocol

    Este endpoint é chamado pelo worker Camunda para inserir processos
    no sistema de consulta processual DW LAW.
    """
    try:
        logger.info(f"📤 Recebendo requisição para inserir {len(request.processos)} processos")

        # Prepara lista de processos para DW LAW
        processos_dw = [
            {
                "numero_processo": p.numero_processo,
                "other_info_client1": p.other_info_client1,
                "other_info_client2": p.other_info_client2
            }
            for p in request.processos
        ]

        # Chama API DW LAW
        result = await dw_service.inserir_processos(
            chave_projeto=request.chave_projeto,
            processos=processos_dw
        )

        if not result.get("success"):
            return DWLawResponse(
                success=False,
                error="DW_LAW_ERROR",
                message=result.get("obs", "Erro ao inserir processos"),
                data=result
            )

        # Extrai dados retornados
        data = result.get("data", {})
        processos_retornados = data.get("processos", [])

        # Salva processos no MongoDB
        collection = database["dw_law_processos"]
        processos_salvos = []

        for proc in processos_retornados:
            processo_doc = ProcessoDWLaw(
                chave_projeto=request.chave_projeto,
                numero_processo=proc.get("numero_processo"),
                chave_de_pesquisa=proc.get("chave_de_pesquisa"),
                tribunal=proc.get("tribunal"),
                sistema=proc.get("sistema"),
                instancia=proc.get("instancia"),
                status="inserido",
                timestamp_insercao=datetime.now(),
                camunda_instance_id=request.camunda_instance_id,
                camunda_business_key=request.camunda_business_key
            )

            # Insere no MongoDB
            doc_dict = processo_doc.dict()
            inserted = collection.insert_one(doc_dict)
            doc_dict["_id"] = str(inserted.inserted_id)
            processos_salvos.append(doc_dict)

        logger.info(f"✅ {len(processos_salvos)} processos inseridos e salvos no MongoDB")

        return DWLawResponse(
            success=True,
            message=f"{len(processos_salvos)} processos inseridos com sucesso",
            data={
                "chave_projeto": request.chave_projeto,
                "total_inseridos": len(processos_salvos),
                "processos": processos_retornados,
                "retorno": data.get("retorno"),
                "obs": data.get("obs")
            }
        )

    except Exception as e:
        logger.error(f"💥 Erro ao processar inserção de processos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/excluir-processos", response_model=DWLawResponse)
async def excluir_processos(
    request: ExcluirProcessosRequest,
    dw_service: DWLawService = Depends(get_dw_law_service),
    database = Depends(get_database)
):
    """
    Exclui processos do DW LAW e-Protocol

    Este endpoint é chamado pelo worker Camunda para excluir processos
    do monitoramento no DW LAW.
    """
    try:
        logger.info(f"🗑️ Recebendo requisição para excluir {len(request.lista_de_processos)} processos")

        # Chama API DW LAW
        result = await dw_service.excluir_processos(
            chave_projeto=request.chave_projeto,
            lista_de_processos=request.lista_de_processos
        )

        if not result.get("success"):
            return DWLawResponse(
                success=False,
                error="DW_LAW_ERROR",
                message=result.get("obs", "Erro ao excluir processos"),
                data=result
            )

        # Atualiza status no MongoDB
        collection = database["dw_law_processos"]
        numeros_processo = [p["numero_processo"] for p in request.lista_de_processos]

        update_result = collection.update_many(
            {
                "chave_projeto": request.chave_projeto,
                "numero_processo": {"$in": numeros_processo}
            },
            {
                "$set": {
                    "status": "excluido",
                    "timestamp_exclusao": datetime.now()
                }
            }
        )

        logger.info(f"✅ {update_result.modified_count} processos marcados como excluídos no MongoDB")

        data = result.get("data", {})

        return DWLawResponse(
            success=True,
            message=f"{len(numeros_processo)} processos excluídos com sucesso",
            data={
                "chave_projeto": request.chave_projeto,
                "total_excluidos": len(numeros_processo),
                "processos": data.get("lista_de_processos", []),
                "retorno": data.get("retorno"),
                "obs": data.get("obs")
            }
        )

    except Exception as e:
        logger.error(f"💥 Erro ao processar exclusão de processos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consultar-processo", response_model=DWLawResponse)
async def consultar_processo(
    request: ConsultarProcessoRequest,
    dw_service: DWLawService = Depends(get_dw_law_service),
    database = Depends(get_database)
):
    """
    Consulta processo completo por chave de pesquisa

    Este endpoint é chamado pelo worker Camunda para consultar
    dados completos de um processo no DW LAW.
    """
    try:
        logger.info(f"🔍 Recebendo requisição para consultar processo - Chave: {request.chave_de_pesquisa}")

        # Chama API DW LAW
        result = await dw_service.consultar_processo_por_chave(
            chave_de_pesquisa=request.chave_de_pesquisa
        )

        if not result.get("success"):
            return DWLawResponse(
                success=False,
                error="DW_LAW_ERROR",
                message=result.get("obs", "Erro ao consultar processo"),
                data=result
            )

        # Extrai dados do processo
        processo_data = result.get("data", {})

        # Salva consulta no MongoDB
        collection_consultas = database["dw_law_consultas"]

        consulta_doc = ConsultaProcessoDWLaw(
            **processo_data,
            timestamp_consulta=datetime.now(),
            camunda_instance_id=request.camunda_instance_id
        )

        # Insere no MongoDB
        doc_dict = consulta_doc.dict()
        inserted = collection_consultas.insert_one(doc_dict)

        # Atualiza status do processo
        collection_processos = database["dw_law_processos"]
        collection_processos.update_one(
            {"chave_de_pesquisa": request.chave_de_pesquisa},
            {
                "$set": {
                    "status": "consultado",
                    "timestamp_ultima_consulta": datetime.now()
                }
            }
        )

        logger.info(f"✅ Consulta realizada e salva no MongoDB - ID: {inserted.inserted_id}")

        return DWLawResponse(
            success=True,
            message="Processo consultado com sucesso",
            data=processo_data
        )

    except Exception as e:
        logger.error(f"💥 Erro ao processar consulta de processo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINT DE CALLBACK ====================

@router.post("/callback", response_model=DWLawResponse)
async def receber_callback(
    request: Request,
    database = Depends(get_database),
    camunda_service: CamundaMessageService = Depends(get_camunda_service)
):
    """
    Recebe callback do DW LAW e-Protocol

    Este endpoint é chamado pelo DW LAW quando há atualizações
    de processos. O callback é salvo no MongoDB e uma mensagem
    BPMN é enviada ao Camunda para correlacionar com processos em execução.
    """
    try:
        # Recebe payload completo
        payload = await request.json()

        logger.info(f"📨 Callback DW LAW recebido - Chave: {payload.get('chave_de_pesquisa', 'N/A')}")
        logger.debug(f"📨 Payload completo: {payload}")

        # Extrai campos principais
        chave_de_pesquisa = payload.get("chave_de_pesquisa")
        numero_processo = payload.get("numero_processo")
        status_pesquisa = payload.get("status_pesquisa")
        descricao_status = payload.get("descricao_status_pesquisa")

        if not chave_de_pesquisa:
            raise HTTPException(
                status_code=400,
                detail="Campo 'chave_de_pesquisa' obrigatório"
            )

        # Salva callback no MongoDB
        collection_callbacks = database["dw_law_callbacks"]

        callback_doc = CallbackDWLaw(
            payload_completo=payload,
            chave_de_pesquisa=chave_de_pesquisa,
            numero_processo=numero_processo or "N/A",
            status_pesquisa=status_pesquisa or "N/A",
            descricao_status_pesquisa=descricao_status or "N/A",
            timestamp_recebimento=datetime.now()
        )

        doc_dict = callback_doc.dict()
        inserted = collection_callbacks.insert_one(doc_dict)
        callback_id = str(inserted.inserted_id)

        logger.info(f"✅ Callback salvo no MongoDB - ID: {callback_id}")

        # Busca processo no MongoDB para obter business_key
        collection_processos = database["dw_law_processos"]
        processo = collection_processos.find_one({"chave_de_pesquisa": chave_de_pesquisa})

        business_key = None
        if processo:
            business_key = processo.get("camunda_business_key") or processo.get("numero_processo")
        else:
            # Se não encontrou, usa o número do processo do callback
            business_key = numero_processo or chave_de_pesquisa

        logger.info(f"🔑 Business Key determinado: {business_key}")

        # Envia mensagem BPMN para Camunda
        mensagem_resultado = camunda_service.send_dw_law_callback_message(
            business_key=business_key,
            chave_de_pesquisa=chave_de_pesquisa,
            numero_processo=numero_processo or "N/A",
            status_pesquisa=status_pesquisa or "N/A",
            descricao_status=descricao_status or "N/A",
            dados_processo=payload
        )

        # Atualiza callback com resultado do envio da mensagem
        collection_callbacks.update_one(
            {"_id": inserted.inserted_id},
            {
                "$set": {
                    "mensagem_camunda_enviada": mensagem_resultado.get("success", False),
                    "camunda_business_key": business_key,
                    "mensagem_camunda_resultado": mensagem_resultado,
                    "processado": True,
                    "timestamp_processamento": datetime.now()
                }
            }
        )

        if mensagem_resultado.get("success"):
            logger.info(f"✅ Mensagem BPMN enviada ao Camunda com sucesso")
        else:
            logger.warning(
                f"⚠️ Falha ao enviar mensagem BPMN: {mensagem_resultado.get('message')}"
            )

        return DWLawResponse(
            success=True,
            message="Callback processado com sucesso",
            data={
                "callback_id": callback_id,
                "chave_de_pesquisa": chave_de_pesquisa,
                "numero_processo": numero_processo,
                "business_key": business_key,
                "mensagem_camunda_enviada": mensagem_resultado.get("success", False)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Erro ao processar callback DW LAW: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE UTILIDADE ====================

@router.get("/health")
async def health_check():
    """Health check do router DW LAW"""
    return {
        "status": "healthy",
        "service": "DW LAW e-Protocol Integration",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/test-connection")
async def test_connection(
    dw_service: DWLawService = Depends(get_dw_law_service),
    camunda_service: CamundaMessageService = Depends(get_camunda_service)
):
    """
    Testa conexões com DW LAW e Camunda
    """
    try:
        # Testa DW LAW
        dw_auth = dw_service.is_authenticated()
        if not dw_auth:
            await dw_service._autenticar()

        dw_token_info = dw_service.get_token_info()

        # Testa Camunda
        camunda_test = camunda_service.test_connection()

        return {
            "success": True,
            "dw_law": {
                "authenticated": dw_service.is_authenticated(),
                "token_info": dw_token_info
            },
            "camunda": camunda_test
        }

    except Exception as e:
        logger.error(f"💥 Erro ao testar conexões: {e}")
        return {
            "success": False,
            "error": str(e)
        }
