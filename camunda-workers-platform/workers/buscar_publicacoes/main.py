#!/usr/bin/env python3
"""
Worker para busca automatizada de publicações
Orquestra busca de publicações via API SOAP e disparo de processos Camunda
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context

logger = logging.getLogger(__name__)


class BuscarPublicacoesWorker(BaseWorker):
    """
    Worker orquestrador para busca automatizada de publicações
    
    RESPONSABILIDADES (seguindo padrão arquitetural):
    - Receber tasks de busca agendadas do Camunda
    - Validar parâmetros de busca
    - Submeter para Worker API Gateway para processamento
    - Monitorar status e retornar resultados para Camunda
    
    IMPORTANTE: Este worker NÃO contém lógica de negócio!
    Toda lógica de busca e processamento está no Worker API Gateway.
    
    Fluxo:
    1. Recebe tarefa 'BuscarPublicacoes' do Camunda (via timer ou manual)
    2. Valida parâmetros de entrada
    3. Delega para Gateway endpoint /buscar-publicacoes/processar-task
    4. Processa resposta e retorna variáveis para Camunda
    """

    def __init__(self):
        super().__init__(
            worker_id="buscar-publicacoes-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Configuração para modo Gateway (orquestração)
        self.gateway_enabled = os.getenv('GATEWAY_ENABLED', 'true').lower() == 'true'
        
        if not self.gateway_enabled:
            self.logger.warning("⚠️ Worker em modo direto - recomenda-se GATEWAY_ENABLED=true")
        else:
            self.logger.info("✅ Worker configurado em modo orquestrador (Gateway)")
        
        # Subscribe ao tópico de busca de publicações
        self.subscribe(Topics.BUSCAR_PUBLICACOES, self.processar_busca_publicacoes)
        
        self.logger.info("🔍 BuscarPublicacoesWorker iniciado e aguardando tarefas")

    def processar_busca_publicacoes(self, task: ExternalTask):
        """
        Orquestra a busca de publicações e disparo de processos
        
        Parâmetros esperados (variáveis da tarefa):
        - cod_grupo: int (default: 5)
        - data_inicial: str (opcional, formato YYYY-MM-DD)
        - data_final: str (opcional, formato YYYY-MM-DD)
        - limite_publicacoes: int (default: 50)
        - timeout_soap: int (default: 90)
        """
        start_time = datetime.now()
        
        log_with_context(
            self.logger.info,
            f"🔍 Iniciando busca de publicações",
            task_id=task.get_task_id(),
            business_key=task.get_business_key(),
            process_instance_id=task.get_process_instance_id()
        )
        
        try:
            # 1. Extrair e validar variáveis da tarefa
            variables = task.get_variables()
            
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
                log_with_context(
                    self.logger.error,
                    error_msg,
                    task_id=task.get_task_id()
                )
                
                return task.complete({
                    "status_busca": "error",
                    "erro_validacao": error_msg,
                    "timestamp_processamento": start_time.isoformat(),
                    "total_encontradas": 0,
                    "instancias_criadas": 0
                })
            
            # 2. Log dos parâmetros validados
            log_with_context(
                self.logger.info,
                f"📋 Parâmetros validados - Grupo: {cod_grupo}, Limite: {limite_publicacoes}",
                task_id=task.get_task_id(),
                cod_grupo=cod_grupo,
                limite=limite_publicacoes
            )
            
            # 3. Preparar dados para Gateway
            if self.gateway_enabled:
                # Modo Gateway: delegar processamento
                gateway_response = self._process_via_gateway(task, {
                    'cod_grupo': cod_grupo,
                    'data_inicial': data_inicial,
                    'data_final': data_final,
                    'limite_publicacoes': limite_publicacoes,
                    'timeout_soap': timeout_soap
                })
                
                if gateway_response:
                    return gateway_response
                else:
                    # Fallback se Gateway falhar
                    return self._handle_gateway_error(task, start_time)
            else:
                # Modo direto (não recomendado)
                return self._process_direct_mode(task, start_time)
                
        except Exception as e:
            log_with_context(
                self.logger.error,
                f"💥 Erro inesperado durante busca de publicações: {e}",
                task_id=task.get_task_id(),
                error=str(e)
            )
            
            return task.complete({
                "status_busca": "error",
                "erro_processamento": str(e),
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

    def _process_via_gateway(self, task: ExternalTask, parameters: Dict[str, Any]) -> Optional[Any]:
        """Processa busca via Worker API Gateway"""
        
        log_with_context(
            self.logger.info,
            "🌐 Delegando processamento para Worker API Gateway",
            task_id=task.get_task_id()
        )
        
        # Preparar dados da tarefa para o Gateway
        task_data = {
            "task_id": task.get_task_id(),
            "process_instance_id": task.get_process_instance_id(),
            "business_key": task.get_business_key(),
            "variables": parameters,
            "topic_name": Topics.BUSCAR_PUBLICACOES,
            "worker_id": self.worker_id
        }
        
        try:
            # Usar método do BaseWorker para comunicar com Gateway
            gateway_response = self._send_to_gateway(
                endpoint="/buscar-publicacoes/processar-task",
                data=task_data,
                task=task
            )
            
            if gateway_response and gateway_response.get("status") == "success":
                # Sucesso: extrair dados da resposta do Gateway
                log_with_context(
                    self.logger.info,
                    f"✅ Gateway processou com sucesso - {gateway_response.get('instancias_criadas', 0)} instâncias criadas",
                    task_id=task.get_task_id(),
                    instancias_criadas=gateway_response.get('instancias_criadas', 0)
                )
                
                # Retornar variáveis para Camunda
                return task.complete({
                    "status_busca": "success",
                    "total_encontradas": gateway_response.get("total_encontradas", 0),
                    "total_processadas": gateway_response.get("total_processadas", 0),
                    "instancias_criadas": gateway_response.get("instancias_criadas", 0),
                    "instancias_com_erro": gateway_response.get("instancias_com_erro", 0),
                    "duracao_segundos": gateway_response.get("duracao_segundos", 0),
                    "timestamp_processamento": gateway_response.get("timestamp"),
                    "mensagem": gateway_response.get("message", "Processamento concluído")
                })
            else:
                # Erro no Gateway
                error_msg = gateway_response.get("message", "Erro desconhecido do Gateway") if gateway_response else "Gateway não respondeu"
                
                log_with_context(
                    self.logger.error,
                    f"❌ Gateway retornou erro: {error_msg}",
                    task_id=task.get_task_id()
                )
                
                return task.complete({
                    "status_busca": "error",
                    "erro_gateway": error_msg,
                    "timestamp_processamento": datetime.now().isoformat(),
                    "total_encontradas": 0,
                    "instancias_criadas": 0
                })
                
        except Exception as e:
            log_with_context(
                self.logger.error,
                f"💥 Erro na comunicação com Gateway: {e}",
                task_id=task.get_task_id(),
                error=str(e)
            )
            return None

    def _handle_gateway_error(self, task: ExternalTask, start_time: datetime) -> Any:
        """Trata erro de comunicação com Gateway"""
        error_msg = "Falha na comunicação com Worker API Gateway"
        
        log_with_context(
            self.logger.error,
            error_msg,
            task_id=task.get_task_id()
        )
        
        return task.complete({
            "status_busca": "error",
            "erro_gateway": error_msg,
            "timestamp_processamento": start_time.isoformat(),
            "total_encontradas": 0,
            "instancias_criadas": 0
        })

    def _process_direct_mode(self, task: ExternalTask, start_time: datetime) -> Any:
        """Modo direto (não recomendado - apenas para fallback)"""
        
        log_with_context(
            self.logger.warning,
            "⚠️ Processando em modo direto - não recomendado para produção",
            task_id=task.get_task_id()
        )
        
        # Em modo direto, apenas simular processamento
        # Na prática, toda lógica deveria estar no Gateway
        return task.complete({
            "status_busca": "success",
            "total_encontradas": 0,
            "total_processadas": 0,
            "instancias_criadas": 0,
            "instancias_com_erro": 0,
            "duracao_segundos": 1.0,
            "timestamp_processamento": start_time.isoformat(),
            "mensagem": "Processamento em modo direto - nenhuma ação executada"
        })

    def _send_to_gateway(self, endpoint: str, data: Dict[str, Any], task: ExternalTask) -> Optional[Dict[str, Any]]:
        """
        Envia dados para o Worker API Gateway
        
        Args:
            endpoint: Endpoint do Gateway
            data: Dados a enviar
            task: Tarefa do Camunda
            
        Returns:
            Resposta do Gateway ou None em caso de erro
        """
        try:
            import requests
            
            # URL do Gateway
            gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:8001')
            full_url = f"{gateway_url}{endpoint}"
            
            # Headers
            headers = {
                'Content-Type': 'application/json',
                'X-Worker-ID': self.worker_id,
                'X-Task-ID': task.get_task_id()
            }
            
            # Timeout configurável
            timeout = int(os.getenv('GATEWAY_TIMEOUT', '300'))  # 5 minutos
            
            log_with_context(
                self.logger.debug,
                f"🌐 Enviando para Gateway: {full_url}",
                task_id=task.get_task_id(),
                url=full_url
            )
            
            # Fazer request
            response = requests.post(
                full_url,
                json=data,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log_with_context(
                    self.logger.error,
                    f"Gateway retornou HTTP {response.status_code}: {response.text}",
                    task_id=task.get_task_id(),
                    status_code=response.status_code
                )
                return {"status": "error", "message": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            log_with_context(
                self.logger.error,
                "Gateway timeout - operação demorou muito para responder",
                task_id=task.get_task_id()
            )
            return {"status": "error", "message": "Gateway timeout"}
            
        except requests.exceptions.ConnectionError:
            log_with_context(
                self.logger.error,
                "Erro de conexão com Gateway - serviço indisponível",
                task_id=task.get_task_id()
            )
            return {"status": "error", "message": "Gateway indisponível"}
            
        except Exception as e:
            log_with_context(
                self.logger.error,
                f"Erro inesperado na comunicação com Gateway: {e}",
                task_id=task.get_task_id(),
                error=str(e)
            )
            return {"status": "error", "message": f"Erro de comunicação: {str(e)}"}


def main():
    """Função principal para executar o worker"""
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        
        logger.info("🚀 Iniciando BuscarPublicacoesWorker...")
        
        # Validar configuração
        WorkerConfig.validate_config()
        
        # Log de configuração
        env_info = WorkerConfig.get_environment_info()
        logger.info(f"🔧 Configuração: {env_info}")
        
        # Criar e executar worker
        worker = BuscarPublicacoesWorker()
        
        logger.info("✅ Worker iniciado com sucesso")
        logger.info("🔍 Aguardando tarefas de busca de publicações...")
        
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