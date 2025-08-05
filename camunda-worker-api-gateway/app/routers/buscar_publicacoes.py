"""
Router para busca de publicações
Endpoint para processar tarefas de busca automatizada de publicações
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from models.buscar_request import (
    BuscarPublicacoesRequest,
    BuscarPublicacoesResponse,
    TaskDataRequest,
    PublicacaoParaProcessamento,
    PublicacaoProcessingResult,
    BuscarPublicacoesStatus
)
from services.process_starter import get_process_starter, ProcessStarter
from services.intimation_service import get_intimation_client, IntimationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/buscar-publicacoes", tags=["Buscar Publicações"])

# Storage simples para status de operações (em produção usar Redis/DB)
_operations_status: Dict[str, BuscarPublicacoesStatus] = {}




@router.post("/processar", response_model=BuscarPublicacoesResponse)
async def processar_busca_publicacoes(
    request: BuscarPublicacoesRequest,
    background_tasks: BackgroundTasks,
    process_starter: ProcessStarter = Depends(get_process_starter),
    soap_client: IntimationService = Depends(get_intimation_client)
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
        etapa_atual="Conectando com API SOAP"
    )
    _operations_status[operation_id] = status
    
    try:
        # 1. Cliente SOAP já disponível via dependency injection
        
        # Testar conexão
        if not soap_client.test_connection():
            raise HTTPException(
                status_code=503,
                detail="Falha na conexão com API SOAP"
            )
        
        status.atualizar_progresso(0, 0, 0, "Buscando publicações via SOAP")
        
        # 2. Buscar publicações
        publicacoes = []
        
        if request.apenas_nao_exportadas:
            logger.info(f"Buscando publicações não exportadas - Grupo: {request.cod_grupo}")
            publicacoes = soap_client.get_publicacoes_nao_exportadas(
                cod_grupo=request.cod_grupo
            )
        elif request.data_inicial and request.data_final:
            logger.info(f"Buscando por período: {request.data_inicial} a {request.data_final}")
            publicacoes = soap_client.get_publicacoes_periodo_safe(
                data_inicial=request.data_inicial,
                data_final=request.data_final,
                cod_grupo=request.cod_grupo,
                timeout_override=request.timeout_soap
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
                configuracao_utilizada=request.to_dict()
            )
        
        # 3. Aplicar limite
        publicacoes_para_processar = publicacoes[:request.limite_publicacoes]
        total_filtradas = total_encontradas - len(publicacoes_para_processar)
        
        status.total_esperado = len(publicacoes_para_processar)
        status.atualizar_progresso(0, 0, 0, "Convertendo publicações")
        
        # 4. Converter publicações
        publicacoes_convertidas = []
        for pub in publicacoes_para_processar:
            try:
                pub_convertida = PublicacaoParaProcessamento.from_soap_publicacao(pub, fonte="dw")
                publicacoes_convertidas.append(pub_convertida)
            except Exception as e:
                logger.error(f"Erro ao converter publicação {pub.cod_publicacao}: {e}")
        
        status.atualizar_progresso(0, 0, 0, "Iniciando processos Camunda")
        
        # 5. Processar em lote via ProcessStarter
        movimentacoes_data = [pub.to_movimentacao_dict() for pub in publicacoes_convertidas]
        
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
            publicacoes_por_tribunal[tribunal] = publicacoes_por_tribunal.get(tribunal, 0) + 1
            publicacoes_por_fonte[fonte] = publicacoes_por_fonte.get(fonte, 0) + 1
            
            if result["status"] == "success":
                instancias_criadas += 1
                resultado = PublicacaoProcessingResult(
                    cod_publicacao=pub_convertida.cod_publicacao,
                    numero_processo=pub_convertida.numero_processo,
                    status="success",
                    instance_id=result["instance_id"],
                    business_key=result.get("business_key")
                )
            else:
                instancias_com_erro += 1
                resultado = PublicacaoProcessingResult(
                    cod_publicacao=pub_convertida.cod_publicacao,
                    numero_processo=pub_convertida.numero_processo,
                    status="error",
                    error_message=result.get("error", "Erro desconhecido")
                )
            
            resultados_detalhados.append(resultado)
            
            # Atualizar progresso
            status.atualizar_progresso(
                i + 1, 
                instancias_criadas, 
                instancias_com_erro,
                f"Processando {i+1}/{len(results_batch)}"
            )
        
        # 7. Calcular estatísticas finais
        timestamp_fim = datetime.now()
        duracao = (timestamp_fim - timestamp_inicio).total_seconds()
        total_processadas = len(publicacoes_convertidas)
        taxa_sucesso = instancias_criadas / total_processadas if total_processadas > 0 else 0.0
        
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
            publicacoes_por_fonte=publicacoes_por_fonte
        )
        
        # Atualizar status final
        status.status = "completed"
        status.resultado_final = response
        status.atualizar_progresso(
            total_processadas, 
            instancias_criadas, 
            instancias_com_erro,
            "Concluído",
            response.resumo_textual
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
            f"Erro durante processamento: {str(e)}"
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno durante busca: {str(e)}"
        )


@router.post("/processar-task", response_model=Dict[str, Any])
async def processar_task_camunda(
    task_data: TaskDataRequest,
    soap_client: IntimationService = Depends(get_intimation_client)
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
                "timestamp": timestamp_inicio.isoformat()
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
                "timestamp": timestamp_inicio.isoformat()
            }
        
        # Processar limitado
        publicacoes_limitadas = publicacoes[:buscar_request.limite_publicacoes]
        
        # Converter e iniciar processos
        movimentacoes_data = []
        for pub in publicacoes_limitadas:
            try:
                pub_convertida = PublicacaoParaProcessamento.from_soap_publicacao(pub, fonte="dw")
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
        
        logger.info(f"Tarefa {task_data.task_id} processada: {sucessos} sucessos, {erros} erros")
        
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
            "timestamp": timestamp_fim.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar tarefa {task_data.task_id}: {e}")
        return {
            "status": "error",
            "message": f"Erro durante processamento: {str(e)}",
            "task_id": task_data.task_id,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/status/{operation_id}", response_model=BuscarPublicacoesStatus)
async def obter_status_operacao(operation_id: str):
    """Obtém status de uma operação de busca"""
    if operation_id not in _operations_status:
        raise HTTPException(
            status_code=404,
            detail=f"Operação {operation_id} não encontrada"
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
            status_code=404,
            detail=f"Operação {operation_id} não encontrada"
        )


@router.post("/test-soap")
async def testar_conexao_soap(soap_client: IntimationService = Depends(get_intimation_client)):
    """Testa conexão com API SOAP"""
    try:
        # Cliente SOAP já disponível via dependency injection
        
        if soap_client.test_connection():
            return {
                "status": "success",
                "message": "Conexão SOAP OK",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error", 
                "message": "Falha na conexão SOAP",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro ao testar SOAP: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.post("/test-camunda")
async def testar_conexao_camunda():
    """Testa conexão com Camunda"""
    try:
        process_starter = get_process_starter()
        
        if process_starter.test_connection():
            stats = process_starter.get_process_statistics("processar_movimentacao_judicial")
            return {
                "status": "success",
                "message": "Conexão Camunda OK",
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Falha na conexão Camunda",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro ao testar Camunda: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }