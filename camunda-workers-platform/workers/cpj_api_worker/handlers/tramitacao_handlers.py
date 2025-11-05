"""Handlers para Tramitação - Andamentos e Tarefas (API CPJ-3C)"""
import logging
from camunda.external_task.external_task import ExternalTask

logger = logging.getLogger(__name__)

class TramitacaoHandlers:
    def __init__(self, worker):
        self.worker = worker

    def handle_cadastrar_andamento(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            pj = variables.get("pj")
            if not pj or not variables.get("evento"):
                return self.worker.fail_task(task, "pj/evento ausentes", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/tramitacao/andamento/{pj}", 30)
            return self.worker.complete_task(task, {"status": "success", "id_tramitacao": 1})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_cadastrar_tarefa(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            pj = variables.get("pj")
            if not pj or not variables.get("evento"):
                return self.worker.fail_task(task, "pj/evento ausentes", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/tramitacao/tarefa/{pj}", 30)
            return self.worker.complete_task(task, {"status": "success", "id_tramitacao": 1})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_atualizar_tarefa(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            id_tram = variables.get("id_tramitacao")
            if not id_tram:
                return self.worker.fail_task(task, "id_tramitacao ausente", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/tramitacao/tarefa/{id_tram}", 30)
            return self.worker.complete_task(task, {"status": "success"})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)
