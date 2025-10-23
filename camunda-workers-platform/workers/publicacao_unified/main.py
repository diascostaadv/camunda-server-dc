#!/usr/bin/env python3
"""
Worker Unificado para Processamento de Publicações
Combina funcionalidades de nova_publicacao e buscar_publicacoes em um único container
"""

import sys
import os
import logging
from datetime import datetime

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

        # Subscribe a múltiplos tópicos usando o novo método
        self.subscribe_multiple(
            {
                Topics.NOVA_PUBLICACAO: self.handle_nova_publicacao,
                Topics.BUSCAR_PUBLICACOES: self.handle_buscar_publicacoes,
                Topics.BUSCAR_LOTE_POR_ID: self.handle_buscar_lote_por_id,
                Topics.TRATAR_PUBLICACAO: self.handle_tratar_publicacao,
                Topics.CLASSIFICAR_PUBLICACAO: self.handle_classificar_publicacao,
                Topics.VERIFICAR_PROCESSO_CNJ: self.handle_verificar_processo_cnj,
            }
        )

        self.logger.info(
            "🔍 PublicacaoUnifiedWorker iniciado - aguardando tarefas nos tópicos:"
        )
        self.logger.info(f"  • {Topics.NOVA_PUBLICACAO} - Processamento individual")
        self.logger.info(f"  • {Topics.BUSCAR_PUBLICACOES} - Busca automatizada")
        self.logger.info(f"  • {Topics.BUSCAR_LOTE_POR_ID} - Busca lote por ID")
        self.logger.info(f"  • {Topics.TRATAR_PUBLICACAO} - Tratamento e higienização")
        self.logger.info(
            f"  • {Topics.CLASSIFICAR_PUBLICACAO} - Classificação de publicações"
        )
        self.logger.info(f"  • {Topics.VERIFICAR_PROCESSO_CNJ} - Verificação no CPJ")

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
            "HANDLER": "nova_publicacao",
        }

        log_with_context(
            "🔄 Iniciando orquestração de movimentação judicial", log_context
        )

        try:
            # ETAPA 1: Validação básica de campos obrigatórios
            variables = task.get_variables()
            required_fields = [
                "numero_processo",
                "data_publicacao",
                "texto_publicacao",
                "fonte",
                "tribunal",
                "instancia",
            ]

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
                    retries=0,  # Não retry para erro de validação
                )

            # Validação de formato básico
            fonte = variables.get("fonte")
            if fonte not in ["dw", "manual", "escavador"]:
                error_msg = (
                    f"Fonte inválida: {fonte}. Deve ser 'dw', 'manual' ou 'escavador'"
                )
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            # Validação básica de data (formato)
            data_publicacao = variables.get("data_publicacao")
            if len(data_publicacao) != 10 or data_publicacao.count("/") != 2:
                error_msg = (
                    f"Formato de data inválido: {data_publicacao}. Use dd/mm/yyyy"
                )
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            log_with_context(
                f"✅ Validação básica concluída - Processo: {variables.get('numero_processo')}",
                log_context,
            )

            # ETAPA 2: Processar de acordo com o modo configurado
            if self.gateway_enabled:
                log_with_context("📤 Processando via Worker API Gateway", log_context)
                # Usar o helper para processar via Gateway
                return self.process_via_gateway(
                    task=task, endpoint="/publicacoes/processar-nova", timeout=60
                )
            else:
                # Modo direto - processar localmente
                log_with_context(
                    "⚙️ Processando em modo direto (sem Gateway)", log_context
                )

                # Em modo direto, simplesmente completar a tarefa com sucesso
                # (a lógica de negócio real estaria no Gateway)
                result = {
                    "status": "processed",
                    "modo": "direto",
                    "numero_processo": variables.get("numero_processo"),
                    "data_publicacao": variables.get("data_publicacao"),
                    "fonte": variables.get("fonte"),
                    "tribunal": variables.get("tribunal"),
                    "instancia": variables.get("instancia"),
                    "timestamp_processamento": datetime.now().isoformat(),
                    "worker_id": self.worker_id,
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
                retries=3,
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
            "HANDLER": "buscar_publicacoes",
        }

        log_with_context("🔍 Iniciando busca automatizada de publicações", log_context)
        self.logger.info(
            f"DEBUG: handle_buscar_publicacoes chamado para task {task.get_task_id()}"
        )

        try:
            # 1. Extrair e validar variáveis da tarefa
            variables = task.get_variables()

            # Fallback para mock se variáveis não estiverem disponíveis (desenvolvimento)
            if not variables:
                variables = {
                    "cod_grupo": 5,
                    "data_inicial": "2023-01-01",
                    "data_final": "2025-12-31",
                    "limite_publicacoes": 100,
                    "timeout_soap": 120,
                }

            # Parâmetros com valores padrão
            cod_grupo = variables.get("cod_grupo", 5)
            data_inicial = variables.get("data_inicial")
            data_final = variables.get("data_final")
            limite_publicacoes = variables.get("limite_publicacoes", 50)
            timeout_soap = variables.get("timeout_soap", 90)

            # Validações básicas
            validation_errors = self._validate_busca_parameters(
                cod_grupo, data_inicial, data_final, limite_publicacoes, timeout_soap
            )

            if validation_errors:
                error_msg = f"Parâmetros inválidos: {', '.join(validation_errors)}"
                log_with_context(f"❌ Validação falhou: {error_msg}", log_context)

                return self.fail_task(task, error_msg, retries=0)

            # 2. Log dos parâmetros validados
            log_with_context(
                f"📋 Parâmetros validados - Grupo: {cod_grupo}, Limite: {limite_publicacoes}",
                {**log_context, "cod_grupo": cod_grupo, "limite": limite_publicacoes},
            )

            # 3. Processar de acordo com o modo configurado
            if self.gateway_enabled:
                # Usar o helper para processar via Gateway
                log_with_context("📤 Processando via Worker API Gateway", log_context)

                # Timeout adicional para operações SOAP
                total_timeout = timeout_soap + 30

                return self.process_via_gateway(
                    task=task,
                    endpoint="/buscar-publicacoes/processar-task-v2",
                    timeout=total_timeout,
                )
            else:
                # Modo direto - processar localmente (simulação)
                log_with_context(
                    "⚙️ Processando busca em modo direto (sem Gateway)", log_context
                )

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
                    "worker_id": self.worker_id,
                }

                log_with_context(f"✅ Busca concluída em modo direto", log_context)
                return self.complete_task(task, result_data)

        except Exception as e:
            error_msg = f"Erro inesperado durante busca de publicações: {e}"
            log_with_context(f"💥 Exceção no worker: {error_msg}", log_context)

            return self.fail_task(task, error_msg, retries=3)

    def _validate_busca_parameters(
        self,
        cod_grupo: int,
        data_inicial: str,
        data_final: str,
        limite_publicacoes: int,
        timeout_soap: int,
    ) -> list:
        """Valida parâmetros de busca"""
        errors = []

        # Validar cod_grupo
        if not isinstance(cod_grupo, int) or cod_grupo < 0:
            errors.append("cod_grupo deve ser um inteiro não negativo")

        # Validar datas se fornecidas
        if data_inicial:
            try:
                datetime.strptime(data_inicial, "%Y-%m-%d")
            except ValueError:
                errors.append("data_inicial deve estar no formato YYYY-MM-DD")

        if data_final:
            try:
                datetime.strptime(data_final, "%Y-%m-%d")
            except ValueError:
                errors.append("data_final deve estar no formato YYYY-MM-DD")

        # Validar limite
        if (
            not isinstance(limite_publicacoes, int)
            or limite_publicacoes < 1
            or limite_publicacoes > 1000
        ):
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
            "numero_processo": variables.get("numero_processo", "AUSENTE"),
            "data_publicacao": variables.get("data_publicacao", "AUSENTE"),
            "fonte": variables.get("fonte", "AUSENTE"),
            "tribunal": variables.get("tribunal", "AUSENTE"),
            "instancia": variables.get("instancia", "AUSENTE"),
            "texto_length": (
                len(variables.get("texto_publicacao", ""))
                if variables.get("texto_publicacao")
                else 0
            ),
            "total_fields": len([k for k, v in variables.items() if v]),
            "timestamp": datetime.now().isoformat(),
        }

    def handle_buscar_lote_por_id(self, task: ExternalTask):
        """
        Manipula tarefas de buscar lote por ID

        Parâmetros esperados:
        - lote_id: ID do lote a buscar
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "buscar_lote_por_id",
        }

        log_with_context("🔍 Buscando lote por ID", log_context)

        try:
            variables = task.get_variables()
            lote_id = variables.get("lote_id")

            if not lote_id:
                error_msg = "lote_id não fornecido nas variáveis"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            log_with_context(f"📦 Buscando lote {lote_id}", log_context)

            if self.gateway_enabled:
                # Usar o helper para processar via Gateway
                log_with_context("📤 Processando via Gateway", log_context)
                return self.process_via_gateway(
                    task=task,
                    endpoint=f"/publicacoes/buscar-lote/{lote_id}",
                    timeout=60,
                )
            else:
                # Modo direto - apenas simula
                result = {
                    "status": "success",
                    "lote_id": lote_id,
                    "total_publicacoes": 0,
                    "publicacoes_ids": [],
                    "modo": "direto",
                    "message": "Busca simulada em modo direto",
                }
                return self.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao buscar lote: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.fail_task(task, error_msg, retries=3)

    def handle_tratar_publicacao(self, task: ExternalTask):
        """
        Manipula tarefas de tratamento de publicação

        Parâmetros esperados:
        - publicacao_id: ID da publicação a tratar
        - executar_classificacao: Se deve classificar (default: True)
        - executar_deduplicacao: Se deve verificar duplicatas (default: True)
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "tratar_publicacao",
        }

        log_with_context("🧹 Iniciando tratamento de publicação", log_context)

        try:
            variables = task.get_variables()
            publicacao_id = variables.get("publicacao_id")

            if not publicacao_id:
                error_msg = "publicacao_id não fornecido nas variáveis"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            executar_classificacao = variables.get("executar_classificacao", True)
            executar_deduplicacao = variables.get("executar_deduplicacao", True)

            log_with_context(
                f"📋 Tratando publicação {publicacao_id} - Classificar: {executar_classificacao}, Deduplicar: {executar_deduplicacao}",
                log_context,
            )

            if self.gateway_enabled:
                # Usar o helper para processar via Gateway
                log_with_context("📤 Processando via Gateway", log_context)
                return self.process_via_gateway(
                    task=task,
                    endpoint="/publicacoes/processar-task-publicacao",
                    timeout=90,
                )
            # else:
            #     # Modo direto - apenas simula
            #     result = {
            #         "status": "success",
            #         # "numero_processo": variables.get("numero_processo"),
            #         "publicacao_id": publicacao_id,
            #         "status_publicacao": "nova_publicacao_inedita",
            #         "score_similaridade": 0.0,
            #         "modo": "direto",
            #         "message": "Tratamento simulado em modo direto",
            #     }
            #     return self.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao tratar publicação: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.fail_task(task, error_msg, retries=3)

    def handle_classificar_publicacao(self, task: ExternalTask):
        """
        Manipula tarefas de classificação de publicação

        Parâmetros esperados:
        - publicacao_id: ID da publicação a classificar
        - texto_publicacao: Texto da publicação (opcional se ID fornecido)
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "classificar_publicacao",
        }

        log_with_context("📊 Iniciando classificação de publicação", log_context)

        try:
            variables = task.get_variables()
            publicacao_id = variables.get("publicacao_id")
            texto_publicacao = variables.get("texto_publicacao")

            if not publicacao_id and not texto_publicacao:
                error_msg = "publicacao_id ou texto_publicacao deve ser fornecido"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            log_with_context(
                f"🏷️ Classificando publicação {publicacao_id or 'com texto fornecido'}",
                log_context,
            )

            if self.gateway_enabled:
                # Usar o helper para processar via Gateway
                log_with_context("📤 Processando via Gateway", log_context)
                return self.process_via_gateway(
                    task=task, endpoint="/publicacoes/classificar", timeout=60
                )
            else:
                # Modo direto - apenas simula
                result = {
                    "status": "success",
                    "publicacao_id": publicacao_id,
                    "classificacao": {
                        "tipo": "outros",
                        "urgente": False,
                        "prazo_dias": None,
                        "confianca": 0.5,
                    },
                    "modo": "direto",
                    "message": "Classificação simulada em modo direto",
                }
                return self.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao classificar publicação: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.fail_task(task, error_msg, retries=3)

    def handle_verificar_processo_cnj(self, task: ExternalTask):
        """
        Verifica se processo existe no CPJ

        Parâmetros esperados:
        - numero_cnj: Número do processo CNJ (formato: 0000000-00.0000.0.00.0000)
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": task.get_topic_name(),
            "BUSINESS_KEY": task.get_business_key(),
            "HANDLER": "verificar_processo_cnj",
        }

        log_with_context("🔍 Verificando processo no CPJ", log_context)

        try:
            variables = task.get_variables()
            numero_cnj = variables.get("numero_cnj") or variables.get("numero_processo")

            if not numero_cnj:
                error_msg = "numero_cnj não fornecido"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.fail_task(task, error_msg, retries=0)

            log_with_context(f"📋 Buscando processo {numero_cnj} no CPJ", log_context)

            if self.gateway_enabled:
                return self.process_via_gateway(
                    task=task,
                    endpoint="/publicacoes/verificar-processo-cnj",
                    timeout=30,
                )
            else:
                # Modo direto - simula
                result = {
                    "status": "success",
                    "numero_cnj": numero_cnj,
                    "processos": [],
                    "total_encontrados": 0,
                    "modo": "direto",
                }
                return self.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao verificar processo CPJ: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.fail_task(task, error_msg, retries=3)


def main():
    """Função principal para executar o worker unificado"""
    try:
        # Configurar logging dinâmico
        log_level = getattr(logging, WorkerConfig.LOG_LEVEL.upper(), logging.WARNING)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
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
        logger.info(
            f"🔍 Aguardando tarefas nos tópicos: {Topics.NOVA_PUBLICACAO}, {Topics.BUSCAR_PUBLICACOES}"
        )

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
