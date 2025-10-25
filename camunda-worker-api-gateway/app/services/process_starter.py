"""
Process Starter Service
Serviço para iniciar instâncias de processo no Camunda via REST API
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ProcessStarterError(Exception):
    """Exceção customizada para erros do ProcessStarter"""

    pass


class ProcessStarter:
    """
    Cliente para iniciar instâncias de processo no Camunda

    Responsabilidades:
    - Conectar com Camunda REST API
    - Iniciar instâncias de processo com variáveis
    - Tratar erros e retry automático
    - Monitorar status das instâncias criadas
    """

    def __init__(
        self,
        camunda_url: str = "http://localhost:8080",
        username: str = None,
        password: str = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Inicializa o ProcessStarter

        Args:
            camunda_url: URL base do Camunda (ex: http://localhost:8080)
            username: Usuário para autenticação básica
            password: Senha para autenticação básica
            timeout: Timeout em segundos para requests
            max_retries: Número máximo de tentativas em caso de erro
        """
        self.camunda_url = camunda_url.rstrip("/")
        self.engine_rest_url = f"{self.camunda_url}/engine-rest"
        self.timeout = timeout

        # Configurar sessão HTTP com retry automático
        self.session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=1,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configurar autenticação se fornecida
        if username and password:
            self.session.auth = (username, password)

        # Headers padrão
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        logger.info(f"ProcessStarter configurado para {self.camunda_url}")

    def test_connection(self) -> bool:
        """
        Testa conexão com o Camunda

        Returns:
            bool: True se conexão bem-sucedida
        """
        try:
            response = self.session.get(
                f"{self.engine_rest_url}/engine", timeout=self.timeout
            )

            if response.status_code == 200:
                engines = response.json()
                logger.info(f"Conexão OK - {len(engines)} engine(s) disponível(is)")
                return True
            else:
                logger.error(f"Erro na conexão: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Falha na conexão com Camunda: {e}")
            return False

    def _format_variables_for_camunda(
        self, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formata variáveis para o formato esperado pelo Camunda

        Args:
            variables: Dicionário de variáveis simples

        Returns:
            Dict formatado para Camunda REST API
        """
        camunda_variables = {}

        for key, value in variables.items():
            if isinstance(value, str):
                camunda_variables[key] = {"value": value, "type": "String"}
            elif isinstance(value, int):
                camunda_variables[key] = {"value": value, "type": "Integer"}
            elif isinstance(value, float):
                camunda_variables[key] = {"value": value, "type": "Double"}
            elif isinstance(value, bool):
                camunda_variables[key] = {"value": value, "type": "Boolean"}
            elif isinstance(value, (dict, list)):
                camunda_variables[key] = {"value": json.dumps(value), "type": "Json"}
            elif value is None:
                camunda_variables[key] = {"value": None, "type": "Null"}
            else:
                # Fallback para string
                camunda_variables[key] = {"value": str(value), "type": "String"}

        return camunda_variables

    def start_process_instance(
        self,
        process_key: str,
        variables: Dict[str, Any] = None,
        business_key: str = None,
    ) -> Optional[str]:
        """
        Inicia uma nova instância de processo

        Args:
            process_key: Chave do processo a ser iniciado
            variables: Variáveis para passar ao processo
            business_key: Chave de negócio opcional

        Returns:
            str: ID da instância criada ou None em caso de erro
        """
        variables = variables or {}

        try:
            # Formatar variáveis
            camunda_variables = self._format_variables_for_camunda(variables)

            # Preparar payload
            payload = {"variables": camunda_variables}

            if business_key:
                payload["businessKey"] = business_key

            # Fazer request
            url = f"{self.engine_rest_url}/process-definition/key/{process_key}/start"

            logger.debug(f"Iniciando processo {process_key} com payload: {payload}")

            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                instance_info = response.json()
                instance_id = instance_info["id"]

                logger.info(
                    f"Processo {process_key} iniciado com sucesso - Instance ID: {instance_id}"
                )

                if business_key:
                    logger.info(f"Business Key: {business_key}")

                return instance_id

            else:
                error_msg = f"Erro ao iniciar processo {process_key}: HTTP {response.status_code}"
                logger.error(f"{error_msg} - Resposta: {response.text}")
                raise ProcessStarterError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Erro de rede ao iniciar processo {process_key}: {e}"
            logger.error(error_msg)
            raise ProcessStarterError(error_msg)
        except Exception as e:
            error_msg = f"Erro inesperado ao iniciar processo {process_key}: {e}"
            logger.error(error_msg)
            raise ProcessStarterError(error_msg)

    def start_movimentacao_process(
        self, movimentacao_data: Dict[str, Any], business_key: str = None
    ) -> Optional[str]:
        """
        Inicia processo específico para movimentação judicial

        Args:
            movimentacao_data: Dados da movimentação no formato MovimentacaoJudicial
            business_key: Chave de negócio (ex: número do processo)

        Returns:
            str: ID da instância criada
        """
        # Validar campos obrigatórios
        required_fields = [
            "numero_processo",
            "data_publicacao",
            "texto_publicacao",
            "fonte",
            "tribunal",
            "instancia",
        ]

        missing_fields = [
            field for field in required_fields if not movimentacao_data.get(field)
        ]
        if missing_fields:
            raise ProcessStarterError(f"Campos obrigatórios ausentes: {missing_fields}")

        # Usar número do processo como business key se não fornecida
        if not business_key:
            business_key = f"mov_{movimentacao_data['numero_processo']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return self.start_process_instance(
            process_key="processar_movimentacao_judicial",
            variables=movimentacao_data,
            business_key=business_key,
        )

    def start_multiple_processes(
        self,
        process_key: str,
        variables_list: List[Dict[str, Any]],
        business_key_field: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Inicia múltiplas instâncias de processo em lote

        Args:
            process_key: Chave do processo
            variables_list: Lista de variáveis para cada instância
            business_key_field: Campo a usar como business key

        Returns:
            List[Dict]: Lista com resultados de cada start
        """
        results = []

        for i, variables in enumerate(variables_list):
            try:
                # Determinar business key
                business_key = None
                if business_key_field and business_key_field in variables:
                    business_key = f"{variables[business_key_field]}_{i}"

                instance_id = self.start_process_instance(
                    process_key=process_key,
                    variables=variables,
                    business_key=business_key,
                )

                results.append(
                    {
                        "index": i,
                        "status": "success",
                        "instance_id": instance_id,
                        "business_key": business_key,
                        "variables": variables,
                    }
                )

            except Exception as e:
                logger.error(f"Erro ao iniciar processo {i}: {e}")
                results.append(
                    {
                        "index": i,
                        "status": "error",
                        "error": str(e),
                        "variables": variables,
                    }
                )

        # Log summary
        success_count = len([r for r in results if r["status"] == "success"])
        error_count = len([r for r in results if r["status"] == "error"])

        logger.info(
            f"Lote processado: {success_count} sucessos, {error_count} erros de {len(variables_list)} total"
        )

        return results

    def start_movimentacoes_batch(
        self, movimentacoes_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Inicia múltiplas instâncias do processo de movimentação judicial

        Args:
            movimentacoes_list: Lista de dados de movimentações

        Returns:
            List[Dict]: Resultados do processamento em lote
        """
        return self.start_multiple_processes(
            process_key="processar_movimentacao_judicial",
            variables_list=movimentacoes_list,
            business_key_field="numero_processo",
        )

    def get_process_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém status de uma instância de processo

        Args:
            instance_id: ID da instância

        Returns:
            Dict com informações da instância ou None se não encontrada
        """
        try:
            response = self.session.get(
                f"{self.engine_rest_url}/process-instance/{instance_id}",
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "not_found_or_completed"}
            else:
                logger.error(
                    f"Erro ao obter status da instância {instance_id}: HTTP {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Erro ao obter status da instância {instance_id}: {e}")
            return None

    def get_process_statistics(self, process_key: str = None) -> Dict[str, Any]:
        """
        Obtém estatísticas de processos

        Args:
            process_key: Chave do processo específico (opcional)

        Returns:
            Dict com estatísticas
        """
        try:
            params = {}
            if process_key:
                params["processDefinitionKey"] = process_key

            # Instâncias ativas
            response_active = self.session.get(
                f"{self.engine_rest_url}/process-instance",
                params=params,
                timeout=self.timeout,
            )

            active_count = (
                len(response_active.json()) if response_active.status_code == 200 else 0
            )

            # Estatísticas históricas (últimas 24h)
            from datetime import datetime, timedelta

            yesterday = (datetime.now() - timedelta(days=1)).isoformat()

            history_params = params.copy()
            history_params["startedAfter"] = yesterday

            response_history = self.session.get(
                f"{self.engine_rest_url}/history/process-instance",
                params=history_params,
                timeout=self.timeout,
            )

            history_data = (
                response_history.json() if response_history.status_code == 200 else []
            )

            completed_count = len(
                [h for h in history_data if h.get("state") == "COMPLETED"]
            )
            terminated_count = len(
                [
                    h
                    for h in history_data
                    if h.get("state")
                    in ["EXTERNALLY_TERMINATED", "INTERNALLY_TERMINATED"]
                ]
            )

            return {
                "process_key": process_key,
                "timestamp": datetime.now().isoformat(),
                "active_instances": active_count,
                "completed_24h": completed_count,
                "terminated_24h": terminated_count,
                "total_started_24h": len(history_data),
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}


# Instância singleton para uso global
_process_starter_instance = None


def get_process_starter(
    camunda_url: str = None, username: str = None, password: str = None
) -> ProcessStarter:
    """
    Factory function para obter instância do ProcessStarter

    Args:
        camunda_url: URL do Camunda (opcional, usa padrão se None)
        username: Usuário (opcional)
        password: Senha (opcional)

    Returns:
        ProcessStarter: Instância configurada
    """
    global _process_starter_instance

    if _process_starter_instance is None:
        import os

        # Usar valores padrão do ambiente se não fornecidos
        camunda_url = camunda_url or os.getenv("CAMUNDA_URL", "http://localhost:8080")
        username = username or os.getenv("CAMUNDA_USERNAME")
        password = password or os.getenv("CAMUNDA_PASSWORD")

        _process_starter_instance = ProcessStarter(
            camunda_url=camunda_url, username=username, password=password
        )

    return _process_starter_instance
