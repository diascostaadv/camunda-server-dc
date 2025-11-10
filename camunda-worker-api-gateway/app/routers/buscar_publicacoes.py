"""
Router para busca de publicações
Endpoint para processar tarefas de busca automatizada de publicações
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends

from pymongo import MongoClient
from bson import ObjectId

from models.buscar_request import (
    BuscarPublicacoesRequest,
    BuscarPublicacoesResponse,
    TaskDataRequest,
    PublicacaoParaProcessamento,
    PublicacaoProcessingResult,
    BuscarPublicacoesStatus,
)
from models.publicacao import Lote
from services.process_starter import get_process_starter, ProcessStarter
from services.intimation_service import get_intimation_client, IntimationService
from services.lote_service import LoteService
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/buscar-publicacoes", tags=["Buscar Publicações"])

# Storage simples para status de operações (em produção usar Redis/DB)
_operations_status: Dict[str, BuscarPublicacoesStatus] = {}

# Configurações
settings = get_settings()


def get_mongo_client() -> MongoClient:
    """Obtém cliente MongoDB"""
    return MongoClient(settings.MONGODB_CONNECTION_STRING)


def get_lote_service(
    client: MongoClient = Depends(get_mongo_client),
    intimation_service: IntimationService = Depends(get_intimation_client),
) -> LoteService:
    """Obtém serviço de lotes com marcação automática configurável via .env"""
    return LoteService(
        client,
        intimation_service=intimation_service,
        database_name=settings.MONGODB_DATABASE,
        marcar_automaticamente=settings.MARCAR_AUTOMATICAMENTE,  # Lê do .env
    )


@router.post("/processar", response_model=BuscarPublicacoesResponse)
async def processar_busca_publicacoes(
    request: BuscarPublicacoesRequest,
    process_starter: ProcessStarter = Depends(get_process_starter),
    soap_client: IntimationService = Depends(get_intimation_client),
):
    """
    Processa busca de publicações e inicia processos Camunda

    Fluxo:
    1. Busca publicações via SOAP API
    2. Converte para formato MovimentacaoJudicial
    3. Inicia instância de processo para cada publicação
    4. Retorna estatísticas do processamento
    """
    timestamp_inicio = datetime.now()
    operation_id = f"busca_{timestamp_inicio.strftime('%Y%m%d_%H%M%S')}"

    logger.info(f"Iniciando busca de publicações - Operation ID: {operation_id}")

    # Criar status inicial
    status = BuscarPublicacoesStatus(
        operacao_id=operation_id,
        status="running",
        timestamp_inicio=timestamp_inicio,
        etapa_atual="Conectando com API SOAP",
    )
    _operations_status[operation_id] = status

    try:
        # 1. Cliente SOAP já disponível via dependency injection

        # Testar conexão
        if not soap_client.test_connection():
            raise HTTPException(status_code=503, detail="Falha na conexão com API SOAP")

        status.atualizar_progresso(0, 0, 0, "Buscando publicações via SOAP")

        # 2. Buscar publicações
        publicacoes = []

        if request.apenas_nao_exportadas:
            logger.info(
                f"Buscando publicações não exportadas - Grupo: {request.cod_grupo}"
            )
            publicacoes = soap_client.get_publicacoes_nao_exportadas(
                cod_grupo=request.cod_grupo
            )
        elif request.data_inicial and request.data_final:
            logger.info(
                f"Buscando por período: {request.data_inicial} a {request.data_final}"
            )
            publicacoes = soap_client.get_publicacoes_periodo_safe(
                data_inicial=request.data_inicial,
                data_final=request.data_final,
                cod_grupo=request.cod_grupo,
                timeout_override=request.timeout_soap,
            )
        else:
            # Buscar não exportadas como fallback
            publicacoes = soap_client.get_publicacoes_nao_exportadas(
                cod_grupo=request.cod_grupo
            )

        total_encontradas = len(publicacoes)
        logger.info(f"Encontradas {total_encontradas} publicações")

        if total_encontradas == 0:
            timestamp_fim = datetime.now()
            return BuscarPublicacoesResponse(
                timestamp_inicio=timestamp_inicio,
                timestamp_fim=timestamp_fim,
                duracao_segundos=(timestamp_fim - timestamp_inicio).total_seconds(),
                total_encontradas=0,
                total_processadas=0,
                total_filtradas=0,
                instancias_criadas=0,
                instancias_com_erro=0,
                instancias_ignoradas=0,
                taxa_sucesso=1.0,
                configuracao_utilizada=request.to_dict(),
            )

        # 3. Aplicar limite
        publicacoes_para_processar = publicacoes[: request.limite_publicacoes]
        total_filtradas = total_encontradas - len(publicacoes_para_processar)

        status.total_esperado = len(publicacoes_para_processar)
        status.atualizar_progresso(0, 0, 0, "Convertendo publicações")

        # 4. Converter publicações
        publicacoes_convertidas = []
        for pub in publicacoes_para_processar:
            try:
                pub_convertida = PublicacaoParaProcessamento.from_soap_publicacao(
                    pub, fonte="dw"
                )
                publicacoes_convertidas.append(pub_convertida)
            except Exception as e:
                logger.error(f"Erro ao converter publicação {pub.cod_publicacao}: {e}")

        status.atualizar_progresso(0, 0, 0, "Iniciando processos Camunda")

        # 5. Processar em lote via ProcessStarter
        movimentacoes_data = [
            pub.to_movimentacao_dict() for pub in publicacoes_convertidas
        ]

        logger.info(f"Iniciando {len(movimentacoes_data)} processos Camunda")
        results_batch = process_starter.start_movimentacoes_batch(movimentacoes_data)

        # 6. Processar resultados
        resultados_detalhados = []
        instancias_criadas = 0
        instancias_com_erro = 0
        publicacoes_por_tribunal = {}
        publicacoes_por_fonte = {}

        for i, result in enumerate(results_batch):
            pub_convertida = publicacoes_convertidas[i]

            # Contadores por tribunal e fonte
            tribunal = pub_convertida.tribunal
            fonte = pub_convertida.fonte
            publicacoes_por_tribunal[tribunal] = (
                publicacoes_por_tribunal.get(tribunal, 0) + 1
            )
            publicacoes_por_fonte[fonte] = publicacoes_por_fonte.get(fonte, 0) + 1

            if result["status"] == "success":
                instancias_criadas += 1
                resultado = PublicacaoProcessingResult(
                    cod_publicacao=pub_convertida.cod_publicacao,
                    numero_processo=pub_convertida.numero_processo,
                    status="success",
                    instance_id=result["instance_id"],
                    business_key=result.get("business_key"),
                )
            else:
                instancias_com_erro += 1
                resultado = PublicacaoProcessingResult(
                    cod_publicacao=pub_convertida.cod_publicacao,
                    numero_processo=pub_convertida.numero_processo,
                    status="error",
                    error_message=result.get("error", "Erro desconhecido"),
                )

            resultados_detalhados.append(resultado)

            # Atualizar progresso
            status.atualizar_progresso(
                i + 1,
                instancias_criadas,
                instancias_com_erro,
                f"Processando {i+1}/{len(results_batch)}",
            )

        # 7. Calcular estatísticas finais
        timestamp_fim = datetime.now()
        duracao = (timestamp_fim - timestamp_inicio).total_seconds()
        total_processadas = len(publicacoes_convertidas)
        taxa_sucesso = (
            instancias_criadas / total_processadas if total_processadas > 0 else 0.0
        )

        # 8. Criar resposta final
        response = BuscarPublicacoesResponse(
            timestamp_inicio=timestamp_inicio,
            timestamp_fim=timestamp_fim,
            duracao_segundos=duracao,
            total_encontradas=total_encontradas,
            total_processadas=total_processadas,
            total_filtradas=total_filtradas,
            instancias_criadas=instancias_criadas,
            instancias_com_erro=instancias_com_erro,
            instancias_ignoradas=0,
            taxa_sucesso=taxa_sucesso,
            resultados_detalhados=resultados_detalhados,
            configuracao_utilizada=request.to_dict(),
            publicacoes_por_tribunal=publicacoes_por_tribunal,
            publicacoes_por_fonte=publicacoes_por_fonte,
        )

        # Atualizar status final
        status.status = "completed"
        status.resultado_final = response
        status.atualizar_progresso(
            total_processadas,
            instancias_criadas,
            instancias_com_erro,
            "Concluído",
            response.resumo_textual,
        )

        logger.info(f"Busca concluída: {response.resumo_textual}")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Erro durante busca de publicações: {e}")

        # Atualizar status com erro
        status.status = "error"
        status.atualizar_progresso(
            status.total_processado,
            status.sucessos,
            status.erros,
            "Erro",
            f"Erro durante processamento: {str(e)}",
        )

        raise HTTPException(
            status_code=500, detail=f"Erro interno durante busca: {str(e)}"
        )


@router.post("/processar-task", response_model=Dict[str, Any])
async def processar_task_camunda(
    task_data: TaskDataRequest,
    soap_client: IntimationService = Depends(get_intimation_client),
):
    """
    Endpoint específico para processar tarefas vindas do Camunda worker

    Este endpoint é chamado pelo BuscarPublicacoesWorker quando
    uma tarefa do tópico 'BuscarPublicacoes' é recebida.
    """
    logger.info(f"Processando tarefa Camunda - Task ID: {task_data.task_id}")

    try:
        # Converter dados da tarefa para request
        buscar_request = task_data.get_buscar_request()

        # Processar usando endpoint principal
        # Note: Em produção, considerar usar background tasks para tarefas longas
        process_starter = get_process_starter()

        # Simular chamada ao endpoint principal
        # Em uma implementação real, isso seria feito via chamada interna
        timestamp_inicio = datetime.now()

        # Cliente SOAP já disponível via dependency injection

        if not soap_client.test_connection():
            return {
                "status": "error",
                "message": "Falha na conexão com API SOAP",
                "task_id": task_data.task_id,
                "timestamp": timestamp_inicio.isoformat(),
            }

        # Buscar publicações
        publicacoes = soap_client.get_publicacoes_nao_exportadas(
            cod_grupo=buscar_request.cod_grupo
        )

        if not publicacoes:
            return {
                "status": "success",
                "message": "Nenhuma publicação encontrada",
                "task_id": task_data.task_id,
                "total_encontradas": 0,
                "instancias_criadas": 0,
                "timestamp": timestamp_inicio.isoformat(),
            }

        # Processar limitado
        publicacoes_limitadas = publicacoes[: buscar_request.limite_publicacoes]

        # Converter e iniciar processos
        movimentacoes_data = []
        for pub in publicacoes_limitadas:
            try:
                pub_convertida = PublicacaoParaProcessamento.from_soap_publicacao(
                    pub, fonte="dw"
                )
                movimentacoes_data.append(pub_convertida.to_movimentacao_dict())
            except Exception as e:
                logger.error(f"Erro ao converter publicação {pub.cod_publicacao}: {e}")

        # Iniciar processos em lote
        if movimentacoes_data:
            results = process_starter.start_movimentacoes_batch(movimentacoes_data)
            sucessos = len([r for r in results if r["status"] == "success"])
            erros = len([r for r in results if r["status"] == "error"])
        else:
            sucessos = 0
            erros = 0

        timestamp_fim = datetime.now()
        duracao = (timestamp_fim - timestamp_inicio).total_seconds()

        logger.info(
            f"Tarefa {task_data.task_id} processada: {sucessos} sucessos, {erros} erros"
        )

        return {
            "status": "success",
            "message": f"Processamento concluído em {duracao:.2f}s",
            "task_id": task_data.task_id,
            "process_instance_id": task_data.process_instance_id,
            "total_encontradas": len(publicacoes),
            "total_processadas": len(movimentacoes_data),
            "instancias_criadas": sucessos,
            "instancias_com_erro": erros,
            "duracao_segundos": duracao,
            "timestamp": timestamp_fim.isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro ao processar tarefa {task_data.task_id}: {e}")
        return {
            "status": "error",
            "message": f"Erro durante processamento: {str(e)}",
            "task_id": task_data.task_id,
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/status/{operation_id}", response_model=BuscarPublicacoesStatus)
async def obter_status_operacao(operation_id: str):
    """Obtém status de uma operação de busca"""
    if operation_id not in _operations_status:
        raise HTTPException(
            status_code=404, detail=f"Operação {operation_id} não encontrada"
        )

    return _operations_status[operation_id]


@router.get("/status", response_model=List[BuscarPublicacoesStatus])
async def listar_operacoes():
    """Lista todas as operações de busca"""
    return list(_operations_status.values())


@router.delete("/status/{operation_id}")
async def limpar_status_operacao(operation_id: str):
    """Remove status de uma operação específica"""
    if operation_id in _operations_status:
        del _operations_status[operation_id]
        return {"message": f"Status da operação {operation_id} removido"}
    else:
        raise HTTPException(
            status_code=404, detail=f"Operação {operation_id} não encontrada"
        )


@router.post("/test-soap")
async def testar_conexao_soap(
    soap_client: IntimationService = Depends(get_intimation_client),
):
    """Testa conexão com API SOAP"""
    try:
        # Cliente SOAP já disponível via dependency injection

        if soap_client.test_connection():
            return {
                "status": "success",
                "message": "Conexão SOAP OK",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "error",
                "message": "Falha na conexão SOAP",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro ao testar SOAP: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/processar-task-v2", response_model=Dict[str, Any])
async def processar_task_camunda_v2(
    task_data: TaskDataRequest,
    soap_client: IntimationService = Depends(get_intimation_client),
    lote_service: LoteService = Depends(get_lote_service),
    mongo_client: MongoClient = Depends(get_mongo_client),
):
    """
    Versão 2: Processa tarefa seguindo o fluxo BPMN correto

    Fluxo:
    1. Busca publicações via SOAP
    2. Cria execução no MongoDB
    3. Cria lote e salva publicações bronze
    4. Retorna lote_id para processamento posterior

    Este endpoint é chamado pelo worker quando recebe uma tarefa
    do tópico 'BuscarPublicacoes' e segue o padrão Bronze/Prata.
    """
    logger.info(f"Processando tarefa Camunda V2 - Task ID: {task_data.task_id}")

    timestamp_inicio = datetime.now()
    db = mongo_client[settings.MONGODB_DATABASE]

    try:
        # 1. Converter dados da tarefa para request
        buscar_request = task_data.get_buscar_request()

        # 2. Testar conexão SOAP
        if not soap_client.test_connection():
            return {
                "status": "error",
                "message": "Falha na conexão com API SOAP",
                "task_id": task_data.task_id,
                "timestamp": timestamp_inicio.isoformat(),
            }

        # 3. Criar execução no MongoDB
        execucao = db.execucoes.insert_one(
            {
                "data_inicio": timestamp_inicio,
                "data_fim": None,
                "status": "running",
                "total_encontradas": 0,
                "total_processadas": 0,
                "configuracao": {
                    "cod_grupo": buscar_request.cod_grupo,
                    "limite_publicacoes": buscar_request.limite_publicacoes,
                    "task_id": task_data.task_id,
                    "process_instance_id": task_data.process_instance_id,
                },
            }
        )
        execucao_id = str(execucao.inserted_id)

        logger.info(f"Execução criada: {execucao_id}")
        logger.info(f"Request: {buscar_request}")
        logger.info(
            f"Request details - apenas_nao_exportadas: {buscar_request.apenas_nao_exportadas}, data_inicial: {buscar_request.data_inicial}, data_final: {buscar_request.data_final}"
        )

        # 4. Buscar publicações via SOAP
        publicacoes = []

        if buscar_request.apenas_nao_exportadas:
            logger.info(
                f"Branch 1: Buscando publicações não exportadas - Grupo: {buscar_request.cod_grupo}"
            )
            publicacoes = soap_client.get_publicacoes_nao_exportadas(
                cod_grupo=buscar_request.cod_grupo
            )
            logger.info(f"Branch 1 result: {len(publicacoes)} publicações encontradas")
        elif buscar_request.data_inicial and buscar_request.data_final:
            logger.info(
                f"Branch 2: Buscando por período: {buscar_request.data_inicial} a {buscar_request.data_final}"
            )

            # Validar período máximo para evitar timeouts no servidor SOAP
            from datetime import timedelta
            PERIODO_MAXIMO_DIAS = 90

            data_inicial_dt = datetime.strptime(buscar_request.data_inicial, "%Y-%m-%d")
            data_final_dt = datetime.strptime(buscar_request.data_final, "%Y-%m-%d")
            dias_periodo = (data_final_dt - data_inicial_dt).days

            if dias_periodo > PERIODO_MAXIMO_DIAS:
                erro_msg = (
                    f"Período muito grande: {dias_periodo} dias. "
                    f"Máximo permitido: {PERIODO_MAXIMO_DIAS} dias. "
                    f"Por favor, divida em consultas menores."
                )
                logger.error(erro_msg)
                raise ValueError(erro_msg)

            logger.info(f"Período validado: {dias_periodo} dias (máximo: {PERIODO_MAXIMO_DIAS} dias)")

            publicacoes = soap_client.get_publicacoes_periodo_safe(
                data_inicial=buscar_request.data_inicial,
                data_final=buscar_request.data_final,
                cod_grupo=buscar_request.cod_grupo,
                timeout_override=buscar_request.timeout_soap,
            )
            logger.info(f"Branch 2 result: {len(publicacoes)} publicações encontradas")
        else:
            # Usar período dos últimos 180 dias quando datas não são fornecidas
            # Baseado em testes: Fevereiro/2025 teve 232 publicações
            from datetime import timedelta

            hoje = datetime.now()
            # Buscar últimos 180 dias (~6 meses) para capturar período com dados
            data_inicial_obj = hoje - timedelta(days=180)

            data_inicial_padrao = data_inicial_obj.strftime("%Y-%m-%d")
            data_final_padrao = hoje.strftime("%Y-%m-%d")

            logger.info(
                f"Branch 3: Nenhum critério de busca fornecido, buscando últimos 180 dias: {data_inicial_padrao} a {data_final_padrao}"
            )
            publicacoes = soap_client.get_publicacoes_periodo_safe(
                data_inicial=data_inicial_padrao,
                data_final=data_final_padrao,
                cod_grupo=buscar_request.cod_grupo,
                timeout_override=buscar_request.timeout_soap,
            )
            logger.info(f"Branch 3 result: {len(publicacoes)} publicações encontradas")

        total_encontradas = len(publicacoes)
        logger.info(f"📊 Encontradas {total_encontradas} publicações no total")

        # 5. Se não encontrou publicações, finalizar
        if total_encontradas == 0:
            timestamp_fim = datetime.now()

            # Atualizar execução
            db.execucoes.update_one(
                {"_id": ObjectId(execucao_id)},
                {
                    "$set": {
                        "data_fim": timestamp_fim,
                        "status": "completed",
                        "total_encontradas": 0,
                        "total_processadas": 0,
                    }
                },
            )

            return {
                "status": "success",
                "message": "Nenhuma publicação encontrada",
                "task_id": task_data.task_id,
                "execucao_id": execucao_id,
                "total_encontradas": 0,
                "lote_id": None,
                "publicacoes_ids": [],  # CRÍTICO: Array vazio para Multi-Instance Loop
                "timestamp": timestamp_fim.isoformat(),
            }

        # 6. Aplicar limite se configurado (0 = sem limite)
        if buscar_request.limite_publicacoes > 0:
            publicacoes_para_processar = publicacoes[: buscar_request.limite_publicacoes]
            if len(publicacoes) > buscar_request.limite_publicacoes:
                logger.info(
                    f"⚠️ Limite aplicado: processando {len(publicacoes_para_processar)} de {total_encontradas} publicações"
                )
        else:
            publicacoes_para_processar = publicacoes
            logger.info(
                f"✅ Sem limite: processando todas as {total_encontradas} publicações"
            )

        # 7. Converter publicações para formato bronze (com filtro de rejeição)
        logger.info(f"🔄 Convertendo {len(publicacoes_para_processar)} publicações...")
        publicacoes_bronze = []
        publicacoes_rejeitadas = 0  # Contador de publicações rejeitadas

        for pub in publicacoes_para_processar:
            try:
                pub_convertida = PublicacaoParaProcessamento.from_soap_publicacao(
                    pub, fonte="dw"
                )

                # Se chegou aqui, publicação tem numero_processo válido
                publicacoes_bronze.append(
                    {
                        "cod_publicacao": pub_convertida.cod_publicacao,
                        "numero_processo": pub_convertida.numero_processo,
                        "data_publicacao": pub_convertida.data_publicacao,
                        "texto_publicacao": pub_convertida.texto_publicacao,
                        "fonte": pub_convertida.fonte,
                        "tribunal": pub_convertida.tribunal,
                        "instancia": pub_convertida.instancia,
                        "descricao_diario": pub_convertida.descricao_diario,
                        "uf_publicacao": pub_convertida.uf_publicacao,
                        # Novos campos
                        "ano_publicacao": pub_convertida.ano_publicacao,
                        "edicao_diario": pub_convertida.edicao_diario,
                        "pagina_inicial": pub_convertida.pagina_inicial,
                        "pagina_final": pub_convertida.pagina_final,
                        "data_divulgacao": pub_convertida.data_divulgacao,
                        "data_cadastro": pub_convertida.data_cadastro,
                        "cidade_publicacao": pub_convertida.cidade_publicacao,
                        "orgao_descricao": pub_convertida.orgao_descricao,
                        "vara_descricao": pub_convertida.vara_descricao,
                        "despacho_publicacao": pub_convertida.despacho_publicacao,
                        "processo_publicacao": pub_convertida.processo_publicacao,
                        "publicacao_corrigida": pub_convertida.publicacao_corrigida,
                        "cod_vinculo": pub_convertida.cod_vinculo,
                        "nome_vinculo": pub_convertida.nome_vinculo,
                        "oab_numero": pub_convertida.oab_numero,
                        "oab_estado": pub_convertida.oab_estado,
                        "diario_sigla_wj": pub_convertida.diario_sigla_wj,
                        "anexo": pub_convertida.anexo,
                        "cod_integracao": pub_convertida.cod_integracao,
                        "publicacao_exportada": pub_convertida.publicacao_exportada,
                        "cod_grupo": pub_convertida.cod_grupo,
                    }
                )

            except ValueError as ve:
                # Publicação rejeitada por numero_processo inválido
                publicacoes_rejeitadas += 1
                logger.warning(f"❌ {str(ve)}")

            except Exception as e:
                # Outros erros de conversão
                publicacoes_rejeitadas += 1
                logger.error(f"❌ Erro ao converter publicação cod={pub.cod_publicacao}: {e}")

        # Log resumo de conversão
        total_validas = len(publicacoes_bronze)
        total_processadas = len(publicacoes_para_processar)

        logger.info(
            f"✅ Conversão concluída: {total_validas} válidas, {publicacoes_rejeitadas} rejeitadas "
            f"de {total_processadas} publicações"
        )

        if publicacoes_rejeitadas > 0:
            percentual = (publicacoes_rejeitadas / total_processadas) * 100
            logger.warning(
                f"⚠️ ATENÇÃO: {publicacoes_rejeitadas} publicações ({percentual:.1f}%) "
                f"foram REJEITADAS (sem numero_processo válido)"
            )

        # Se não há publicações válidas, retornar erro
        if total_validas == 0:
            timestamp_fim = datetime.now()
            db.execucoes.update_one(
                {"_id": ObjectId(execucao_id)},
                {
                    "$set": {
                        "data_fim": timestamp_fim,
                        "status": "error",
                        "total_encontradas": total_encontradas,
                        "total_processadas": 0,
                        "total_rejeitadas": publicacoes_rejeitadas,
                        "erro": f"Todas as {publicacoes_rejeitadas} publicações foram rejeitadas (sem numero_processo válido)",
                    }
                },
            )

            return {
                "status": "error",
                "message": f"Todas as {publicacoes_rejeitadas} publicações foram rejeitadas (sem numero_processo válido)",
                "task_id": task_data.task_id,
                "execucao_id": execucao_id,
                "total_encontradas": total_encontradas,
                "total_rejeitadas": publicacoes_rejeitadas,
                "lote_id": None,
                "publicacoes_ids": [],
                "timestamp": timestamp_fim.isoformat(),
            }

        # 8. Criar lote usando LoteService com chunking
        logger.info(
            f"💾 Criando lote com {len(publicacoes_bronze)} publicações (chunk_size={buscar_request.chunk_size})"
        )
        lote_id = lote_service.criar_lote(
            execucao_id=execucao_id,
            publicacoes=publicacoes_bronze,
            cod_grupo=buscar_request.cod_grupo,
            data_inicial=buscar_request.data_inicial,
            data_final=buscar_request.data_final,
            chunk_size=buscar_request.chunk_size,
        )

        logger.info(f"✅ Lote criado: {lote_id} com {len(publicacoes_bronze)} publicações")

        # 9. Atualizar execução com sucesso
        timestamp_fim = datetime.now()
        db.execucoes.update_one(
            {"_id": ObjectId(execucao_id)},
            {
                "$set": {
                    "data_fim": timestamp_fim,
                    "status": "completed",
                    "total_encontradas": total_encontradas,
                    "total_processadas": len(publicacoes_bronze),
                    "lote_id": lote_id,
                }
            },
        )

        duracao = (timestamp_fim - timestamp_inicio).total_seconds()

        # 10. Buscar IDs das publicações do lote para o Multi-Instance Loop
        lote_doc = db.lotes.find_one({"_id": ObjectId(lote_id)})
        publicacoes_ids = []
        if lote_doc and "publicacoes_ids" in lote_doc:
            publicacoes_ids = lote_doc["publicacoes_ids"]

        logger.info(
            f"🔄 Preparando {len(publicacoes_ids)} IDs para Multi-Instance Loop do BPMN"
        )

        # 11. Retornar resultado com lote_id E publicacoes_ids
        # NOTA: Marcação como exportada deve ser feita pelo tópico dedicado
        #       'marcar_publicacao_exportada_webjur' no BPMN (não aqui)
        return {
            "status": "success",
            "message": f"Lote criado com {len(publicacoes_bronze)} publicações",
            "task_id": task_data.task_id,
            "process_instance_id": task_data.process_instance_id,
            "execucao_id": execucao_id,
            "lote_id": lote_id,
            "total_encontradas": total_encontradas,
            "total_processadas": len(publicacoes_bronze),
            "publicacoes_ids": publicacoes_ids,  # CRÍTICO: Array de IDs para Multi-Instance Loop
            "duracao_segundos": duracao,
            "timestamp": timestamp_fim.isoformat(),
        }

    except Exception as e:
        logger.error(f"Erro ao processar tarefa V2 {task_data.task_id}: {e}")

        # Atualizar execução com erro
        if "execucao_id" in locals():
            db.execucoes.update_one(
                {"_id": ObjectId(execucao_id)},
                {
                    "$set": {
                        "data_fim": datetime.now(),
                        "status": "error",
                        "erro": str(e),
                    }
                },
            )

        return {
            "status": "error",
            "message": f"Erro durante processamento: {str(e)}",
            "task_id": task_data.task_id,
            "timestamp": datetime.now().isoformat(),
        }


@router.post("/test-camunda")
async def testar_conexao_camunda():
    """Testa conexão com Camunda"""
    try:
        process_starter = get_process_starter()

        if process_starter.test_connection():
            stats = process_starter.get_process_statistics(
                "processar_movimentacao_judicial"
            )
            return {
                "status": "success",
                "message": "Conexão Camunda OK",
                "statistics": stats,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "error",
                "message": "Falha na conexão Camunda",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro ao testar Camunda: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
