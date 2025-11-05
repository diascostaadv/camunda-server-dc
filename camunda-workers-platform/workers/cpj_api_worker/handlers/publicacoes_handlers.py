"""Handlers para Publicações (API CPJ-3C)"""
import logging
from camunda.external_task.external_task import ExternalTask

logger = logging.getLogger(__name__)

class PublicacoesHandlers:
    def __init__(self, worker):
        self.worker = worker

    def handle_buscar_publicacoes(self, task: ExternalTask):
        """Buscar publicações não vinculadas"""
        try:
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, "/cpj/publicacoes/consultar", 30)
            return self.worker.complete_task(task, {"status": "success", "publicacoes": []})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)

    def handle_atualizar_publicacao(self, task: ExternalTask):
        """Atualizar publicação"""
        try:
            variables = task.get_variables()
            id_tram = variables.get("id_tramitacao")
            if not id_tram:
                return self.worker.fail_task(task, "id_tramitacao ausente", retries=0)
            
            if self.worker.gateway_enabled:
                return self.worker.process_via_gateway(task, f"/cpj/publicacoes/atualizar/{id_tram}", 30)
            return self.worker.complete_task(task, {"status": "success"})
        except Exception as e:
            return self.worker.fail_task(task, str(e), retries=3)
