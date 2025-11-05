"""Handlers para Envolvidos (API CPJ-3C)"""
import logging
from camunda.external_task.external_task import ExternalTask

logger = logging.getLogger(__name__)

class EnvolvidosHandlers:
    def __init__(self, worker):
        self.worker = worker

    def handle_consultar_envolvidos(self, task: ExternalTask):
        try:
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, "/cpj/envolvidos/consultar", 30)
            return self.worker.complete_task(task, {"status": "success", "envolvidos": []})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_cadastrar_envolvido(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            pj = variables.get("pj")
            if not pj:
                return self.worker.fail_task(task, "pj ausente", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/envolvidos/cadastrar/{pj}", 30)
            return self.worker.complete_task(task, {"status": "success", "sequencia": 1})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_atualizar_envolvido(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            pj = variables.get("pj")
            seq = variables.get("sequencia")
            if not pj or not seq:
                return self.worker.fail_task(task, "pj/sequencia ausentes", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/envolvidos/atualizar/{pj}/{seq}", 30)
            return self.worker.complete_task(task, {"status": "success"})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)
