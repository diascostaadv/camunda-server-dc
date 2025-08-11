#!/usr/bin/env python3
"""
Worker Unificado para Processamento de Publicações
Combina funcionalidades de nova_publicacao e buscar_publicacoes em um único container
"""

import sys
import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context

logger = logging.getLogger(__name__)


class PublicacaoUnifiedWorker(BaseWorker):
    """
    Worker unificado para processamento de publicações judiciais
    
    RESPONSABILIDADES:
    1. Processar movimentações judiciais individuais (nova_publicacao)
    2. Orquestrar busca automatizada de publicações (BuscarPublicacoes)
    
    PADRÃO ARQUITETURAL:
    - Worker orquestrador (NÃO contém lógica de negócio)
    - Toda lógica de processamento está no Worker API Gateway
    - Validação básica no worker, processamento no Gateway
    
    TÓPICOS SUPORTADOS:
    - nova_publicacao: Processamento individual de movimentações
    - BuscarPublicacoes: Busca automatizada e disparo de processos
    """

    def __init__(self):
        super().__init__(
            worker_id="publicacao-unified-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Configuração para modo Gateway (orquestração)
        self.gateway_enabled = os.getenv('GATEWAY_ENABLED', 'true').lower() == 'true'
        
        if not self.gateway_enabled:
            self.logger.warning("⚠️ Worker em modo direto - recomenda-se GATEWAY_ENABLED=true")
        else:
            self.logger.info("✅ Worker configurado em modo orquestrador (Gateway)")
        
        # Subscribe a múltiplos tópicos usando o novo método
        self.subscribe_multiple({
            Topics.NOVA_PUBLICACAO: self.handle_nova_publicacao,
            Topics.BUSCAR_PUBLICACOES: self.handle_buscar_publicacoes
        })
        
        self.logger.info("🔍 PublicacaoUnifiedWorker iniciado - aguardando tarefas nos tópicos:")
        self.logger.info(f"  • {Topics.NOVA_PUBLICACAO} - Processamento individual")
        self.logger.info(f"  • {Topics.BUSCAR_PUBLICACOES} - Busca automatizada")

    def handle_nova_publicacao(self, task: ExternalTask):
        """
        Manipula tarefas de processamento individual de movimentações judiciais
        
        CAMPOS OBRIGATÓRIOS DO PAYLOAD:
        - numero_processo: string
        - data_publicacao: string (dd/mm/yyyy)  
        - texto_publicacao: string
        - fonte: "dw" | "manual" | "escavador"
        - tribunal: string (ex: "tjmg")
        - instancia: string (ex: "1")
        """
        
        # Contexto de logging
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "nova_publicacao"
        }
        
        log_with_context("🔄 Iniciando orquestração de movimentação judicial", log_context)
        
        try:
            # ETAPA 1: Validação básica de campos obrigatórios
            variables = task.get_variables()
            required_fields = ['numero_processo', 'data_publicacao', 'texto_publicacao', 'fonte', 'tribunal', 'instancia']
            
            # Validação de presença dos campos
            missing_fields = []
            for field in required_fields:
                if not variables.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.fail_task(
                    task, 
                    error_msg,
                    f"Worker {self.worker_id} - validação de entrada",
                    retries=0  # Não retry para erro de validação
                )
            
            # Validação de formato básico
            fonte = variables.get('fonte')
            if fonte not in ['dw', 'manual', 'escavador']:
                error_msg = f"Fonte inválida: {fonte}. Deve ser 'dw', 'manual' ou 'escavador'"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)
                
            # Validação básica de data (formato)
            data_publicacao = variables.get('data_publicacao')
            if len(data_publicacao) != 10 or data_publicacao.count('/') != 2:
                error_msg = f"Formato de data inválido: {data_publicacao}. Use dd/mm/yyyy"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)
            
            log_with_context(f"✅ Validação básica concluída - Processo: {variables.get('numero_processo')}", log_context)
            
            # ETAPA 2: Processar de acordo com o modo configurado
            if self.gateway_enabled:
                log_with_context("📤 Processamento será delegado ao Gateway pelo BaseWorker", log_context)
                # Não retornar nada aqui - deixar o BaseWorker processar via Gateway
                # O retorno será tratado pelo unified_handler no BaseWorker
                return
            else:
                # Modo direto - processar localmente
                log_with_context("⚙️ Processando em modo direto (sem Gateway)", log_context)
                
                # Em modo direto, simplesmente completar a tarefa com sucesso
                # (a lógica de negócio real estaria no Gateway)
                result = {
                    "status": "processed",
                    "modo": "direto",
                    "numero_processo": variables.get('numero_processo'),
                    "data_publicacao": variables.get('data_publicacao'),
                    "fonte": variables.get('fonte'),
                    "tribunal": variables.get('tribunal'),
                    "instancia": variables.get('instancia'),
                    "timestamp_processamento": datetime.now().isoformat(),
                    "worker_id": self.worker_id
                }
                
                log_with_context(f"✅ Tarefa processada em modo direto", log_context)
                return self.complete_task(task, result)
            
        except Exception as e:
            error_msg = f"Erro na orquestração: {str(e)}"
            log_with_context(f"❌ Exceção no worker: {error_msg}", log_context)
            return self.fail_task(
                task,
                error_msg,
                f"Worker {self.worker_id} - erro de orquestração",
                retries=3
            )

    def handle_buscar_publicacoes(self, task: ExternalTask):
        """
        Manipula tarefas de busca automatizada de publicações
        
        Parâmetros esperados (variáveis da tarefa):
        - cod_grupo: int (default: 5)
        - data_inicial: str (opcional, formato YYYY-MM-DD)
        - data_final: str (opcional, formato YYYY-MM-DD)
        - limite_publicacoes: int (default: 50)
        - timeout_soap: int (default: 90)
        """
        start_time = datetime.now()
        
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "buscar_publicacoes"
        }
        
        log_with_context("🔍 Iniciando busca automatizada de publicações", log_context)
        
        try:
            # 1. Extrair e validar variáveis da tarefa
            variables = task.get_variables()
            
            # Fallback para mock se variáveis não estiverem disponíveis (desenvolvimento)
            if not variables:
                variables = {
                    "cod_grupo": 5,
                    "data_inicial": "2023-01-01",
                    "data_final": "2024-12-31",
                    "limite_publicacoes": 100,
                    "timeout_soap": 120,
                }
            
            # Parâmetros com valores padrão
            cod_grupo = variables.get('cod_grupo', 5)
            data_inicial = variables.get('data_inicial')
            data_final = variables.get('data_final')
            limite_publicacoes = variables.get('limite_publicacoes', 50)
            timeout_soap = variables.get('timeout_soap', 90)
            
            # Validações básicas
            validation_errors = self._validate_busca_parameters(
                cod_grupo, data_inicial, data_final, limite_publicacoes, timeout_soap
            )
            
            if validation_errors:
                error_msg = f"Parâmetros inválidos: {', '.join(validation_errors)}"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                
                return task.complete({
                    "status_busca": "error",
                    "erro_validacao": error_msg,
                    "timestamp_processamento": start_time.isoformat(),
                    "total_encontradas": 0,
                    "instancias_criadas": 0
                })
            
            # 2. Log dos parâmetros validados
            log_with_context(
                f"📋 Parâmetros validados - Grupo: {cod_grupo}, Limite: {limite_publicacoes}",
                {**log_context, "cod_grupo": cod_grupo, "limite": limite_publicacoes}
            )
            
            # 3. Processar de acordo com o modo configurado
            if not self.gateway_enabled:
                # Modo direto - processar localmente (simulação)
                log_with_context("⚙️ Processando busca em modo direto (sem Gateway)", log_context)
                
                # Simular processamento direto
                result_data = {
                    "status_busca": "success",
                    "modo": "direto",
                    "timestamp_processamento": start_time.isoformat(),
                    "timestamp_fim": datetime.now().isoformat(),
                    "duracao_segundos": (datetime.now() - start_time).total_seconds(),
                    "total_encontradas": 0,  # Em modo direto, apenas simular
                    "instancias_criadas": 0,
                    "cod_grupo": cod_grupo,
                    "limite_publicacoes": limite_publicacoes,
                    "message": "Busca processada em modo direto (simulação)",
                    "worker_id": self.worker_id
                }
                
                log_with_context(f"✅ Busca concluída em modo direto", log_context)
                return task.complete(result_data)
            
            # 4. Chamar Gateway diretamente para processamento
            log_with_context("📤 Enviando tarefa para Worker API Gateway", log_context)
            
            gateway_response = self._call_gateway_buscar_publicacoes(task, variables, log_context)
            
            # 5. Processar resposta do Gateway e completar tarefa
            return self._complete_task_with_gateway_response(task, gateway_response, start_time, log_context)
                
        except Exception as e:
            error_msg = f"Erro inesperado durante busca de publicações: {e}"
            log_with_context(f"💥 Exceção no worker: {error_msg}", log_context)
            
            return task.complete({
                "status_busca": "error",
                "erro_processamento": error_msg,
                "timestamp_processamento": start_time.isoformat(),
                "total_encontradas": 0,
                "instancias_criadas": 0
            })

    def _validate_busca_parameters(self, cod_grupo: int, data_inicial: str, 
                                  data_final: str, limite_publicacoes: int, 
                                  timeout_soap: int) -> list:
        """Valida parâmetros de busca"""
        errors = []
        
        # Validar cod_grupo
        if not isinstance(cod_grupo, int) or cod_grupo < 0:
            errors.append("cod_grupo deve ser um inteiro não negativo")
        
        # Validar datas se fornecidas
        if data_inicial:
            try:
                datetime.strptime(data_inicial, '%Y-%m-%d')
            except ValueError:
                errors.append("data_inicial deve estar no formato YYYY-MM-DD")
                
        if data_final:
            try:
                datetime.strptime(data_final, '%Y-%m-%d')
            except ValueError:
                errors.append("data_final deve estar no formato YYYY-MM-DD")
        
        # Validar limite
        if not isinstance(limite_publicacoes, int) or limite_publicacoes < 1 or limite_publicacoes > 1000:
            errors.append("limite_publicacoes deve ser entre 1 e 1000")
        
        # Validar timeout
        if not isinstance(timeout_soap, int) or timeout_soap < 30 or timeout_soap > 300:
            errors.append("timeout_soap deve ser entre 30 e 300 segundos")
        
        return errors

    def get_validation_summary(self, variables: dict) -> dict:
        """
        Gera resumo da validação para logging/debugging
        
        Args:
            variables: Variáveis da task
            
        Returns:
            dict: Resumo da validação
        """
        return {
            "numero_processo": variables.get('numero_processo', 'AUSENTE'),
            "data_publicacao": variables.get('data_publicacao', 'AUSENTE'),
            "fonte": variables.get('fonte', 'AUSENTE'),
            "tribunal": variables.get('tribunal', 'AUSENTE'),
            "instancia": variables.get('instancia', 'AUSENTE'),
            "texto_length": len(variables.get('texto_publicacao', '')) if variables.get('texto_publicacao') else 0,
            "total_fields": len([k for k, v in variables.items() if v]),
            "timestamp": datetime.now().isoformat()
        }
    
    def _call_gateway_buscar_publicacoes(self, task: ExternalTask, variables: Dict[str, Any], log_context: Dict[str, str]) -> Dict[str, Any]:
        """
        Chama o Worker API Gateway para processar busca de publicações
        
        Args:
            task: Tarefa do Camunda
            variables: Variáveis validadas da tarefa
            log_context: Contexto de log
            
        Returns:
            dict: Resposta do Gateway
        """
        try:
            # URL do Gateway (configurável via environment)
            gateway_base_url = os.getenv('GATEWAY_BASE_URL', 'http://localhost:8000')
            gateway_url = f"{gateway_base_url}/buscar-publicacoes/processar-task"
            
            # Preparar payload para o Gateway
            payload = {
                "task_id": task.get_task_id(),
                "process_instance_id": task.get_process_instance_id(),
                "variables": variables
            }
            
            log_with_context(f"🌐 Chamando Gateway: {gateway_url}", log_context)
            
            # Fazer chamada HTTP com timeout
            timeout_seconds = variables.get('timeout_soap', 90) + 30  # Buffer adicional
            
            response = requests.post(
                gateway_url,
                json=payload,
                timeout=timeout_seconds,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()  # Lança exceção se status HTTP for erro
            
            gateway_response = response.json()
            log_with_context(f"✅ Gateway respondeu: {gateway_response.get('status', 'unknown')}", log_context)
            
            return gateway_response
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout na chamada do Gateway (>{timeout_seconds}s)"
            log_with_context(f"⏱️ {error_msg}", log_context)
            return {"status": "error", "message": error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro de rede ao chamar Gateway: {e}"
            log_with_context(f"🌐❌ {error_msg}", log_context)
            return {"status": "error", "message": error_msg}
            
        except Exception as e:
            error_msg = f"Erro inesperado ao chamar Gateway: {e}"
            log_with_context(f"💥 {error_msg}", log_context)
            return {"status": "error", "message": error_msg}
    
    def _complete_task_with_gateway_response(
        self, 
        task: ExternalTask, 
        gateway_response: Dict[str, Any], 
        start_time: datetime, 
        log_context: Dict[str, str]
    ):
        """
        Completa a tarefa do Camunda com base na resposta do Gateway
        
        Args:
            task: Tarefa do Camunda
            gateway_response: Resposta do Worker API Gateway
            start_time: Timestamp de início da tarefa
            log_context: Contexto de log
        """
        timestamp_fim = datetime.now()
        duracao = (timestamp_fim - start_time).total_seconds()
        
        if gateway_response.get("status") == "success":
            # Sucesso - extrair dados da resposta do Gateway
            result_data = {
                "status_busca": "success",
                "timestamp_processamento": start_time.isoformat(),
                "timestamp_fim": timestamp_fim.isoformat(),
                "duracao_segundos": duracao,
                "total_encontradas": gateway_response.get("total_encontradas", 0),
                "total_processadas": gateway_response.get("total_processadas", 0),
                "instancias_criadas": gateway_response.get("instancias_criadas", 0),
                "instancias_com_erro": gateway_response.get("instancias_com_erro", 0),
                "gateway_task_id": gateway_response.get("task_id"),
                "message": gateway_response.get("message", "Busca processada com sucesso")
            }
            
            log_with_context(
                f"✅ Busca concluída: {result_data['instancias_criadas']} instâncias criadas em {duracao:.2f}s", 
                log_context
            )
            
        else:
            # Erro - preparar dados de erro
            result_data = {
                "status_busca": "error",
                "timestamp_processamento": start_time.isoformat(),
                "timestamp_fim": timestamp_fim.isoformat(),
                "duracao_segundos": duracao,
                "total_encontradas": 0,
                "instancias_criadas": 0,
                "erro_gateway": gateway_response.get("message", "Erro desconhecido no Gateway"),
                "gateway_task_id": gateway_response.get("task_id")
            }
            
            log_with_context(
                f"❌ Busca falhou após {duracao:.2f}s: {result_data['erro_gateway']}", 
                log_context
            )
        
        return task.complete(result_data)


def main():
    """Função principal para executar o worker unificado"""
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        
        logger.info("🚀 Iniciando PublicacaoUnifiedWorker...")
        
        # Validar configuração
        WorkerConfig.validate_config()
        
        # Log de configuração
        env_info = WorkerConfig.get_environment_info()
        logger.info(f"🔧 Configuração: {env_info}")
        
        # Criar e executar worker
        worker = PublicacaoUnifiedWorker()
        
        logger.info("✅ Worker unificado iniciado com sucesso")
        logger.info(f"🔍 Aguardando tarefas nos tópicos: {Topics.NOVA_PUBLICACAO}, {Topics.BUSCAR_PUBLICACOES}")
        
        # Executar worker (loop infinito)
        worker.start()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Worker interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal no worker: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()