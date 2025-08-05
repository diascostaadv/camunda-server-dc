#!/usr/bin/env python3
"""
Worker Unificado para Processamento de Publicações
Combina funcionalidades de nova_publicacao e buscar_publicacoes em um único container
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
            
            # ETAPA 2: Verificar se Gateway está habilitado
            if not self.gateway_enabled:
                error_msg = "Worker configurado em modo direto, mas lógica de negócio deve estar no Gateway"
                log_with_context(f"❌ Configuração incorreta: {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)
            
            log_with_context("📤 Delegando processamento para Worker API Gateway", log_context)
            
            # O BaseWorker com gateway_enabled=true vai processar via Gateway
            return None
            
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
            
            # 3. Verificar se Gateway está habilitado
            if not self.gateway_enabled:
                error_msg = "Worker configurado em modo direto - processamento deve ser via Gateway"
                log_with_context(f"❌ Configuração incorreta: {error_msg}", log_context)
                return task.complete({
                    "status_busca": "error",
                    "erro_configuracao": error_msg,
                    "timestamp_processamento": start_time.isoformat(),
                    "total_encontradas": 0,
                    "instancias_criadas": 0
                })
            
            log_with_context("📤 Delegando busca para Worker API Gateway", log_context)
            
            # O BaseWorker com gateway_enabled=true vai processar via Gateway
            return None
                
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