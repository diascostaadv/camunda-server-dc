"""
Handlers para operações de Processos (API CPJ-3C)
"""

import logging
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context
from validators import validar_numero_cnj

logger = logging.getLogger(__name__)


class ProcessosHandlers:
    """Handlers para operações CRUD de Processos"""

    def __init__(self, worker):
        self.worker = worker
        self.logger = logger

    def handle_consultar_processos(self, task: ExternalTask):
        """Consultar processos com filtros"""
        log_context = {"TASK_ID": task.get_task_id(), "TOPIC": "cpj_consultar_processos"}

        try:
            log_with_context("🔍 Consultando processos", log_context)

            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task, "/cpj/processos/consultar", timeout=30
                )
            return self.worker.complete_task(task, {"status": "success", "processos": []})

        except Exception as e:
            return self.worker.fail_task(task, f"Erro: {str(e)}", retries=3)

    def handle_cadastrar_processo(self, task: ExternalTask):
        """Cadastrar novo processo"""
        log_context = {"TASK_ID": task.get_task_id(), "TOPIC": "cpj_cadastrar_processo"}

        try:
            variables = task.get_variables()

            # Validações
            required = ["entrada", "materia", "acao", "numero_processo"]
            missing = [f for f in required if not variables.get(f)]
            if missing:
                return self.worker.fail_task(task, f"Campos ausentes: {missing}", retries=0)

            # Validar número CNJ
            numero_processo = variables.get("numero_processo")
            if numero_processo and not validar_numero_cnj(numero_processo):
                return self.worker.fail_task(task, "Número CNJ inválido", retries=0)

            log_with_context(f"➕ Cadastrando processo: {numero_processo}", log_context)

            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task, "/cpj/processos/cadastrar", timeout=40
                )
            return self.worker.complete_task(task, {"status": "success", "pj": 999})

        except Exception as e:
            return self.worker.fail_task(task, f"Erro: {str(e)}", retries=3)

    def handle_atualizar_processo(self, task: ExternalTask):
        """Atualizar processo existente"""
        log_context = {"TASK_ID": task.get_task_id(), "TOPIC": "cpj_atualizar_processo"}

        try:
            variables = task.get_variables()
            pj = variables.get("pj")

            if not pj or not variables.get("update_data_hora"):
                return self.worker.fail_task(task, "Campos obrigatórios ausentes", retries=0)

            log_with_context(f"✏️  Atualizando processo {pj}", log_context)

            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(
                    task, f"/cpj/processos/atualizar/{pj}", timeout=30
                )
            return self.worker.complete_task(task, {"status": "success", "pj": pj})

        except Exception as e:
            return self.worker.fail_task(task, f"Erro: {str(e)}", retries=3)
