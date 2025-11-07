#!/usr/bin/env python3
"""
Worker para integração DW LAW e-Protocol
Orquestra operações de consulta processual no DW LAW
"""

import sys
import os
import logging

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.base_worker import BaseWorker
from common.config import WorkerConfig
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context

logger = logging.getLogger(__name__)


# Define tópicos específicos do DW LAW
class DWLawTopics:
    """Tópicos Camunda para DW LAW e-Protocol"""
    INSERIR_PROCESSOS = "INSERIR_PROCESSOS_DW_LAW"
    EXCLUIR_PROCESSOS = "EXCLUIR_PROCESSOS_DW_LAW"
    CONSULTAR_PROCESSO = "CONSULTAR_PROCESSO_DW_LAW"


class DWLawWorker(BaseWorker):
    """
    Worker para integração com DW LAW e-Protocol

    RESPONSABILIDADES:
    1. Inserir processos no monitoramento DW LAW
    2. Excluir processos do monitoramento DW LAW
    3. Consultar dados completos de processos por chave de pesquisa

    PADRÃO ARQUITETURAL:
    - Worker orquestrador (NÃO contém lógica de negócio)
    - Toda lógica de processamento está no Worker API Gateway
    - Validação básica no worker, processamento no Gateway

    TÓPICOS SUPORTADOS:
    - INSERIR_PROCESSOS_DW_LAW: Insere lista de processos
    - EXCLUIR_PROCESSOS_DW_LAW: Exclui lista de processos
    - CONSULTAR_PROCESSO_DW_LAW: Consulta processo por chave
    """

    def __init__(self):
        super().__init__(
            worker_id="dw-law-worker",
            base_url=WorkerConfig.CAMUNDA_URL,
            auth=WorkerConfig.get_auth(),
        )

        # Configuração para modo Gateway (orquestração)
        self.gateway_enabled = os.getenv("GATEWAY_ENABLED", "true").lower() == "true"

        if not self.gateway_enabled:
            self.logger.warning(
                "⚠️ Worker em modo direto - recomenda-se GATEWAY_ENABLED=true"
            )
        else:
            self.logger.info("✅ Worker configurado em modo orquestrador (Gateway)")

        # Subscribe a múltiplos tópicos
        self.subscribe_multiple(
            {
                DWLawTopics.INSERIR_PROCESSOS: self.handle_inserir_processos,
                DWLawTopics.EXCLUIR_PROCESSOS: self.handle_excluir_processos,
                DWLawTopics.CONSULTAR_PROCESSO: self.handle_consultar_processo,
            }
        )

        self.logger.info(
            "🔍 DWLawWorker iniciado - aguardando tarefas nos tópicos:"
        )
        self.logger.info(f"  • {DWLawTopics.INSERIR_PROCESSOS} - Inserir processos")
        self.logger.info(f"  • {DWLawTopics.EXCLUIR_PROCESSOS} - Excluir processos")
        self.logger.info(f"  • {DWLawTopics.CONSULTAR_PROCESSO} - Consultar processo")

    def handle_inserir_processos(self, task: ExternalTask):
        """
        Manipula tarefas de inserção de processos no DW LAW

        CAMPOS OBRIGATÓRIOS DO PAYLOAD:
        - chave_projeto: string (chave única do projeto DW LAW)
        - processos: array de objetos com:
          - numero_processo: string (formato CNJ: 9999999-99.9999.9.99.9999)
          - other_info_client1: string (opcional)
          - other_info_client2: string (opcional)
        """

        # Contexto de logging
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "inserir_processos",
        }

        log_with_context(
            "🔄 Iniciando orquestração de inserção de processos DW LAW", log_context
        )

        try:
            # ETAPA 1: Validação básica de campos obrigatórios
            variables = task.get_variables()

            # Validar chave_projeto
            chave_projeto = variables.get("chave_projeto")
            if not chave_projeto:
                error_msg = "Campo obrigatório ausente: chave_projeto"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            # Validar processos
            processos = variables.get("processos")
            if not processos or not isinstance(processos, list):
                error_msg = "Campo 'processos' obrigatório e deve ser uma lista"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            if len(processos) == 0:
                error_msg = "Lista de processos não pode estar vazia"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            # Validar cada processo na lista
            for idx, proc in enumerate(processos):
                if not isinstance(proc, dict):
                    error_msg = f"Processo no índice {idx} deve ser um objeto"
                    log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                    return self.bpmn_error(
                        task,
                        error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                        error_message=error_msg,
                    )

                if not proc.get("numero_processo"):
                    error_msg = f"Processo no índice {idx} não possui numero_processo"
                    log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                    return self.bpmn_error(
                        task,
                        error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                        error_message=error_msg,
                    )

            log_with_context(
                f"✅ Validação concluída - {len(processos)} processos para inserir",
                log_context,
            )

            # ETAPA 2: Processar via Gateway
            if self.gateway_enabled:
                log_with_context("📤 Processando via Worker API Gateway", log_context)
                return self.process_via_gateway(
                    task=task,
                    endpoint="/dw-law/inserir-processos",
                    timeout=90,
                )
            else:
                # Modo direto não suportado para DW LAW
                error_msg = "Modo direto não suportado para DW LAW - configure GATEWAY_ENABLED=true"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_CONFIGURACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = f"Erro na orquestração: {str(e)}"
            log_with_context(f"❌ Exceção no worker: {error_msg}", log_context)
            return self.bpmn_error(
                task,
                error_code="ERRO_PROCESSAMENTO_INTEGRACAO_DW",
                error_message=error_msg,
            )

    def handle_excluir_processos(self, task: ExternalTask):
        """
        Manipula tarefas de exclusão de processos do DW LAW

        CAMPOS OBRIGATÓRIOS DO PAYLOAD:
        - chave_projeto: string (chave única do projeto DW LAW)
        - lista_de_processos: array de objetos com:
          - numero_processo: string (formato CNJ)
        """

        # Contexto de logging
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "excluir_processos",
        }

        log_with_context(
            "🔄 Iniciando orquestração de exclusão de processos DW LAW", log_context
        )

        try:
            # ETAPA 1: Validação básica de campos obrigatórios
            variables = task.get_variables()

            # Validar chave_projeto
            chave_projeto = variables.get("chave_projeto")
            if not chave_projeto:
                error_msg = "Campo obrigatório ausente: chave_projeto"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            # Validar lista_de_processos
            lista_de_processos = variables.get("lista_de_processos")
            if not lista_de_processos or not isinstance(lista_de_processos, list):
                error_msg = "Campo 'lista_de_processos' obrigatório e deve ser uma lista"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            if len(lista_de_processos) == 0:
                error_msg = "Lista de processos não pode estar vazia"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            # Validar cada processo na lista
            for idx, proc in enumerate(lista_de_processos):
                if not isinstance(proc, dict):
                    error_msg = f"Processo no índice {idx} deve ser um objeto"
                    log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                    return self.bpmn_error(
                        task,
                        error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                        error_message=error_msg,
                    )

                if not proc.get("numero_processo"):
                    error_msg = f"Processo no índice {idx} não possui numero_processo"
                    log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                    return self.bpmn_error(
                        task,
                        error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                        error_message=error_msg,
                    )

            log_with_context(
                f"✅ Validação concluída - {len(lista_de_processos)} processos para excluir",
                log_context,
            )

            # ETAPA 2: Processar via Gateway
            if self.gateway_enabled:
                log_with_context("📤 Processando via Worker API Gateway", log_context)
                return self.process_via_gateway(
                    task=task,
                    endpoint="/dw-law/excluir-processos",
                    timeout=90,
                )
            else:
                # Modo direto não suportado para DW LAW
                error_msg = "Modo direto não suportado para DW LAW - configure GATEWAY_ENABLED=true"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_CONFIGURACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = f"Erro na orquestração: {str(e)}"
            log_with_context(f"❌ Exceção no worker: {error_msg}", log_context)
            return self.bpmn_error(
                task,
                error_code="ERRO_PROCESSAMENTO_INTEGRACAO_DW",
                error_message=error_msg,
            )

    def handle_consultar_processo(self, task: ExternalTask):
        """
        Manipula tarefas de consulta de processo no DW LAW

        CAMPOS OBRIGATÓRIOS DO PAYLOAD:
        - chave_de_pesquisa: string (retornado na inserção do processo)
        """

        # Contexto de logging
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "consultar_processo",
        }

        log_with_context(
            "🔄 Iniciando orquestração de consulta de processo DW LAW", log_context
        )

        try:
            # ETAPA 1: Validação básica de campos obrigatórios
            variables = task.get_variables()

            # Validar chave_de_pesquisa
            chave_de_pesquisa = variables.get("chave_de_pesquisa")
            if not chave_de_pesquisa:
                error_msg = "Campo obrigatório ausente: chave_de_pesquisa"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_VALIDACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

            log_with_context(
                f"✅ Validação concluída - Chave: {chave_de_pesquisa}",
                log_context,
            )

            # ETAPA 2: Processar via Gateway
            if self.gateway_enabled:
                log_with_context("📤 Processando via Worker API Gateway", log_context)
                return self.process_via_gateway(
                    task=task,
                    endpoint="/dw-law/consultar-processo",
                    timeout=120,  # Maior timeout para consultas completas
                )
            else:
                # Modo direto não suportado para DW LAW
                error_msg = "Modo direto não suportado para DW LAW - configure GATEWAY_ENABLED=true"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.bpmn_error(
                    task,
                    error_code="ERRO_CONFIGURACAO_INTEGRACAO_DW",
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = f"Erro na orquestração: {str(e)}"
            log_with_context(f"❌ Exceção no worker: {error_msg}", log_context)
            return self.bpmn_error(
                task,
                error_code="ERRO_PROCESSAMENTO_INTEGRACAO_DW",
                error_message=error_msg,
            )


if __name__ == "__main__":
    """Entry point do worker"""
    worker = DWLawWorker()
    worker.run()
