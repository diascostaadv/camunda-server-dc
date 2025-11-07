"""
Serviço de integração com Camunda REST API
Envia mensagens BPMN para correlacionar com processos em execução
"""

import logging
import requests
import base64
from typing import Dict, Any, Optional
from core.config import settings

logger = logging.getLogger(__name__)


class CamundaMessageService:
    """Serviço para envio de mensagens BPMN para Camunda"""

    def __init__(self):
        self.camunda_rest_url = settings.CAMUNDA_REST_URL
        self.camunda_user = settings.CAMUNDA_REST_USER
        self.camunda_password = settings.CAMUNDA_REST_PASSWORD

        # Cria Basic Auth header
        credentials = f"{self.camunda_user}:{self.camunda_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"

        logger.info(f"CamundaMessageService inicializado - URL: {self.camunda_rest_url}")

    def send_message(
        self,
        message_name: str,
        business_key: str,
        process_variables: Dict[str, Any],
        correlation_keys: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem BPMN para Camunda

        Args:
            message_name: Nome da mensagem BPMN (ex: 'retorno_api_externa')
            business_key: Business key do processo
            process_variables: Variáveis do processo no formato {name: {value, type}}
            correlation_keys: Chaves de correlação adicionais (opcional)
            tenant_id: ID do tenant (opcional, multi-tenancy)

        Returns:
            Resultado do envio da mensagem
        """
        try:
            logger.info(f"📨 Enviando mensagem BPMN '{message_name}' para Camunda - Business Key: {business_key}")

            url = f"{self.camunda_rest_url}/message"
            headers = {
                "Content-Type": "application/json",
                "Authorization": self.auth_header
            }

            # Formata variáveis no padrão Camunda
            formatted_variables = {}
            for var_name, var_data in process_variables.items():
                if isinstance(var_data, dict) and "value" in var_data:
                    # Já está no formato correto
                    formatted_variables[var_name] = var_data
                else:
                    # Converte para formato Camunda
                    formatted_variables[var_name] = {
                        "value": var_data,
                        "type": self._infer_type(var_data)
                    }

            # Monta payload
            payload = {
                "messageName": message_name,
                "businessKey": business_key,
                "processVariables": formatted_variables
            }

            # Adiciona correlation keys se fornecidas
            if correlation_keys:
                payload["correlationKeys"] = correlation_keys

            # Adiciona tenant ID se fornecido
            if tenant_id:
                payload["tenantId"] = tenant_id

            logger.debug(f"📨 [CAMUNDA] Payload: {payload}")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            logger.debug(f"📨 [CAMUNDA] Status: {response.status_code}")

            if response.status_code == 200:
                logger.info(f"✅ Mensagem BPMN enviada com sucesso - '{message_name}'")
                return {
                    "success": True,
                    "message": "Mensagem enviada com sucesso",
                    "response": response.json() if response.text else None
                }
            elif response.status_code == 204:
                # 204 No Content - mensagem enviada mas nenhuma subscrição ativa
                logger.warning(
                    f"⚠️ Mensagem enviada mas nenhuma subscrição ativa para '{message_name}'"
                )
                return {
                    "success": True,
                    "message": "Mensagem enviada, mas nenhuma subscrição ativa",
                    "warning": "NO_SUBSCRIPTION"
                }
            elif response.status_code == 400:
                logger.error(f"❌ Bad Request ao enviar mensagem: {response.text}")
                return {
                    "success": False,
                    "error": "BAD_REQUEST",
                    "message": response.text
                }
            else:
                logger.error(
                    f"❌ Erro HTTP {response.status_code} ao enviar mensagem: {response.text}"
                )
                return {
                    "success": False,
                    "error": f"HTTP_{response.status_code}",
                    "message": response.text
                }

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout ao enviar mensagem para Camunda")
            return {
                "success": False,
                "error": "TIMEOUT",
                "message": "Timeout ao enviar mensagem para Camunda"
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede ao enviar mensagem: {e}")
            return {
                "success": False,
                "error": "NETWORK_ERROR",
                "message": str(e)
            }

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao enviar mensagem: {e}")
            return {
                "success": False,
                "error": "UNEXPECTED_ERROR",
                "message": str(e)
            }

    def send_dw_law_callback_message(
        self,
        business_key: str,
        chave_de_pesquisa: str,
        numero_processo: str,
        status_pesquisa: str,
        descricao_status: str,
        dados_processo: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Método helper para enviar mensagem específica de callback DW LAW

        Args:
            business_key: Business key do processo Camunda
            chave_de_pesquisa: Chave de pesquisa DW LAW
            numero_processo: Número do processo CNJ
            status_pesquisa: Status da pesquisa (S, A, R, E)
            descricao_status: Descrição do status
            dados_processo: Dados completos do processo (opcional)

        Returns:
            Resultado do envio da mensagem
        """
        process_variables = {
            "dw_law_chave_pesquisa": {
                "value": chave_de_pesquisa,
                "type": "String"
            },
            "dw_law_numero_processo": {
                "value": numero_processo,
                "type": "String"
            },
            "dw_law_status_pesquisa": {
                "value": status_pesquisa,
                "type": "String"
            },
            "dw_law_descricao_status": {
                "value": descricao_status,
                "type": "String"
            },
            "dw_law_timestamp_callback": {
                "value": self._get_current_iso_timestamp(),
                "type": "String"
            }
        }

        # Adiciona dados completos se fornecidos
        if dados_processo:
            process_variables["dw_law_dados_processo"] = {
                "value": str(dados_processo),  # Serializa para JSON string
                "type": "String"
            }

        return self.send_message(
            message_name="retorno_dw_law",
            business_key=business_key,
            process_variables=process_variables
        )

    def _infer_type(self, value: Any) -> str:
        """
        Infere o tipo Camunda a partir do valor Python

        Args:
            value: Valor a analisar

        Returns:
            Tipo Camunda (String, Integer, Boolean, Json, etc)
        """
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "Integer"
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, (dict, list)):
            return "Json"
        else:
            return "String"

    def _get_current_iso_timestamp(self) -> str:
        """Retorna timestamp atual no formato ISO 8601"""
        from datetime import datetime
        return datetime.now().isoformat()

    def test_connection(self) -> Dict[str, Any]:
        """
        Testa conexão com Camunda REST API

        Returns:
            Resultado do teste de conexão
        """
        try:
            logger.info("🔍 Testando conexão com Camunda REST API...")

            url = f"{self.camunda_rest_url}/version"
            headers = {
                "Authorization": self.auth_header
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"✅ Conexão com Camunda OK - Versão: {version_info.get('version', 'N/A')}")
                return {
                    "success": True,
                    "version": version_info
                }
            else:
                logger.error(f"❌ Erro ao conectar com Camunda: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP_{response.status_code}",
                    "message": response.text
                }

        except Exception as e:
            logger.error(f"💥 Erro ao testar conexão com Camunda: {e}")
            return {
                "success": False,
                "error": "CONNECTION_ERROR",
                "message": str(e)
            }
