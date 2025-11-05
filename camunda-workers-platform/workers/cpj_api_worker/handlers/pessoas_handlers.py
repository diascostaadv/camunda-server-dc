"""
Handlers para operações de Pessoas (API CPJ-3C)
"""

import logging
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context
from validators import validar_cpf_cnpj

logger = logging.getLogger(__name__)


class PessoasHandlers:
    """Handlers para operações CRUD de Pessoas"""

    def __init__(self, worker):
        self.worker = worker
        self.logger = logger

    def handle_consultar_pessoa(self, task: ExternalTask):
        """
        Consultar pessoas com filtros

        Tópico Camunda: cpj_consultar_pessoa
        API CPJ: POST /api/v2/pessoa
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": "cpj_consultar_pessoa",
            "HANDLER": "consultar_pessoa"
        }

        try:
            variables = task.get_variables()
            filter_data = variables.get("filter", {})

            log_with_context(
                f"🔍 Consultando pessoas - filtros: {list(filter_data.keys())}",
                log_context
            )

            # Processar via Gateway
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task=task,
                    endpoint="/cpj/pessoas/consultar",
                    timeout=30
                )
            else:
                # Modo direto (desenvolvimento)
                result = {
                    "status": "success",
                    "total_encontrados": 0,
                    "pessoas": [],
                    "modo": "direto"
                }
                return self.worker.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao consultar pessoa: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.worker.fail_task(task, error_msg, retries=3)

    def handle_cadastrar_pessoa(self, task: ExternalTask):
        """
        Cadastrar nova pessoa

        Tópico Camunda: cpj_cadastrar_pessoa
        API CPJ: POST /api/v2/pessoa/inserir
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": "cpj_cadastrar_pessoa",
            "HANDLER": "cadastrar_pessoa"
        }

        try:
            variables = task.get_variables()

            # Validações obrigatórias
            required = ["nome", "categoria", "fisica_juridica"]
            missing = [f for f in required if not variables.get(f)]

            if missing:
                error_msg = f"Campos obrigatórios ausentes: {', '.join(missing)}"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.worker.fail_task(task, error_msg, retries=0)

            # Validar CPF/CNPJ se fornecido
            cpf_cnpj = variables.get("cpf_cnpj")
            if cpf_cnpj and not validar_cpf_cnpj(cpf_cnpj):
                error_msg = f"CPF/CNPJ inválido: {cpf_cnpj}"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.worker.fail_task(task, error_msg, retries=0)

            # Validar fisica_juridica
            fisica_juridica = variables.get("fisica_juridica")
            if fisica_juridica not in [1, 2]:
                error_msg = f"fisica_juridica inválido: {fisica_juridica}. Deve ser 1 (Física) ou 2 (Jurídica)"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.worker.fail_task(task, error_msg, retries=0)

            log_with_context(
                f"➕ Cadastrando pessoa: {variables.get('nome')}",
                log_context
            )

            # Processar via Gateway
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task=task,
                    endpoint="/cpj/pessoas/cadastrar",
                    timeout=30
                )
            else:
                # Modo direto (desenvolvimento)
                result = {
                    "status": "success",
                    "codigo": 999,  # Mock
                    "nome": variables.get("nome"),
                    "modo": "direto",
                    "message": "Pessoa cadastrada (modo desenvolvimento)"
                }
                return self.worker.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao cadastrar pessoa: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.worker.fail_task(task, error_msg, retries=3)

    def handle_atualizar_pessoa(self, task: ExternalTask):
        """
        Atualizar dados de pessoa existente

        Tópico Camunda: cpj_atualizar_pessoa
        API CPJ: POST /api/v2/pessoa/atualizar/:codigo
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": "cpj_atualizar_pessoa",
            "HANDLER": "atualizar_pessoa"
        }

        try:
            variables = task.get_variables()

            # Validar campos obrigatórios para atualização
            codigo = variables.get("codigo")
            update_data_hora = variables.get("update_data_hora")
            update_usuario = variables.get("update_usuario")

            if not all([codigo, update_data_hora, update_usuario]):
                error_msg = "Campos obrigatórios: codigo, update_data_hora, update_usuario"
                log_with_context(f"❌ {error_msg}", log_context)
                return self.worker.fail_task(task, error_msg, retries=0)

            log_with_context(
                f"✏️  Atualizando pessoa {codigo}",
                log_context
            )

            # Processar via Gateway
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task=task,
                    endpoint=f"/cpj/pessoas/atualizar/{codigo}",
                    timeout=30
                )
            else:
                # Modo direto (desenvolvimento)
                result = {
                    "status": "success",
                    "codigo": codigo,
                    "modo": "direto",
                    "message": "Pessoa atualizada (modo desenvolvimento)"
                }
                return self.worker.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao atualizar pessoa: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.worker.fail_task(task, error_msg, retries=3)
