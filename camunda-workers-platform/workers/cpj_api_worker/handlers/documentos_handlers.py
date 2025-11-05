"""Handlers para Documentos/GED (API CPJ-3C)"""
import logging
from camunda.external_task.external_task import ExternalTask

logger = logging.getLogger(__name__)

class DocumentosHandlers:
    def __init__(self, worker):
        self.worker = worker

    def handle_consultar_documentos(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            origem = variables.get("origem")
            id_origem = variables.get("id_origem")
            if not origem or not id_origem:
                return self.worker.fail_task(task, "origem/id_origem ausentes", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/documentos/consultar/{origem}/{id_origem}", 30)
            return self.worker.complete_task(task, {"status": "success", "documentos": []})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_baixar_documento(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            id_ged = variables.get("id_ged")
            if not id_ged:
                return self.worker.fail_task(task, "id_ged ausente", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/documentos/baixar/{id_ged}", 60)
            return self.worker.complete_task(task, {"status": "success"})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_cadastrar_documento(self, task: ExternalTask):
        try:
            variables = task.get_variables()
            origem = variables.get("origem")
            id_origem = variables.get("id_origem")
            if not origem or not id_origem:
                return self.worker.fail_task(task, "origem/id_origem ausentes", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/documentos/cadastrar/{origem}/{id_origem}", 40)
            return self.worker.complete_task(task, {"status": "success", "id_ged": 1})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)
