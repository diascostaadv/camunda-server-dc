"""
Handlers para operações de Autenticação (API CPJ-3C)
"""

import logging
from camunda.external_task.external_task import ExternalTask
from camunda.utils.log_utils import log_with_context

logger = logging.getLogger(__name__)


class AuthHandlers:
    """Handlers para autenticação JWT na API CPJ-3C"""

    def __init__(self, worker, cpj_auth):
        """
        Inicializa AuthHandlers

        Args:
            worker: Instância do BaseWorker
            cpj_auth: Instância do CPJAuthManager
        """
        self.worker = worker
        self.cpj_auth = cpj_auth
        self.logger = logger

    def handle_login(self, task: ExternalTask):
        """
        Handler para obter token JWT

        Tópico Camunda: cpj_login
        API CPJ: POST /api/v2/login

        Variáveis esperadas:
        - login: string (opcional, usa env)
        - password: string (opcional, usa env)
        - force_refresh: bool (default: false)
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": "cpj_login",
            "HANDLER": "login"
        }

        try:
            log_with_context("🔐 Obtendo token JWT CPJ-3C", log_context)

            variables = task.get_variables()
            force_refresh = variables.get("force_refresh", False)

            # Obter token (usa cache se disponível)
            token = self.cpj_auth.get_token(force_refresh=force_refresh)

            # Retornar token
            result = {
                "status": "success",
                "token": token,
                "token_type": "Bearer",
                "expires_in_hours": 23,
                "message": "Token JWT obtido com sucesso"
            }

            log_with_context("✅ Token JWT obtido", log_context)
            return self.worker.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao obter token: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.worker.fail_task(task, error_msg, retries=3)

    def handle_refresh_token(self, task: ExternalTask):
        """
        Handler para renovar token JWT

        Tópico Camunda: cpj_refresh_token
        """
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC": "cpj_refresh_token",
            "HANDLER": "refresh_token"
        }

        try:
            log_with_context("🔄 Renovando token JWT", log_context)

            # Forçar novo login
            token = self.cpj_auth.get_token(force_refresh=True)

            result = {
                "status": "success",
                "token": token,
                "token_type": "Bearer",
                "expires_in_hours": 23,
                "message": "Token renovado com sucesso"
            }

            log_with_context("✅ Token renovado", log_context)
            return self.worker.complete_task(task, result)

        except Exception as e:
            error_msg = f"Erro ao renovar token: {str(e)}"
            log_with_context(f"❌ {error_msg}", log_context)
            return self.worker.fail_task(task, error_msg, retries=3)
