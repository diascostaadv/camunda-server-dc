import sys
import os
from datetime import datetime

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig, Topics
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context



class PublicacaoWorker(BaseWorker):
    """
    Worker orquestrador para processamento de movimentações judiciais
    
    RESPONSABILIDADES (seguindo padrão arquitetural):
    - Receber tasks do Camunda
    - Validar campos obrigatórios de entrada  
    - Submeter para Worker API Gateway para processamento
    - Monitorar status e retornar resultados para Camunda
    
    IMPORTANTE: Este worker NÃO contém lógica de negócio!
    Toda lógica de processamento está no Worker API Gateway.
    """

    def __init__(self):
        super().__init__(
            worker_id="publicacao-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth()
        )
        
        # Configuração para modo Gateway (orquestração)
        # A lógica de negócio será processada no Gateway
        self.gateway_enabled = os.getenv('GATEWAY_ENABLED', 'true').lower() == 'true'
        
        if not self.gateway_enabled:
            self.logger.warning("⚠️ Worker em modo direto - recomenda-se GATEWAY_ENABLED=true")
        else:
            self.logger.info("✅ Worker configurado em modo orquestrador (Gateway)")
        
        self.subscribe(Topics.NOVA_PUBLICACAO, self.receive_publicacao)

    def receive_publicacao(self, task: ExternalTask):
        """
        Orquestra o processamento de movimentações judiciais
        
        PADRÃO ARQUITETURAL:
        1. Validar campos obrigatórios (apenas validação básica)
        2. Submeter para Gateway para processamento (toda lógica de negócio)
        3. Retornar resultado para Camunda
        
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
            "BUSINESS_KEY": task.get_business_key()
        }
        
        log_with_context("🔄 Iniciando orquestração de movimentação judicial", log_context)
        
        try:
            # ETAPA 1: Validação básica de campos obrigatórios (responsabilidade do worker)
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
            
            # ETAPA 3: O BaseWorker já gerencia a submissão para Gateway
            # Se chegou aqui, o BaseWorker vai:
            # - Submeter a task para o Gateway
            # - Monitorar o status
            # - Retornar o resultado quando processado
            
            log_with_context("📤 Delegando processamento para Worker API Gateway", log_context)
            
            # O BaseWorker com gateway_enabled=true vai processar via Gateway
            # Não precisamos fazer nada aqui - apenas retornamos None para continuar o ciclo
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

if __name__ == "__main__":
    worker = PublicacaoWorker()
    worker.start()