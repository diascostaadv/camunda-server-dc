"""
Serviço de integração com API CPJ
Gerencia autenticação JWT e busca de processos
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from core.config import settings

logger = logging.getLogger(__name__)


class CPJService:
    """Serviço para integração com API CPJ"""

    def __init__(self):
        self.base_url = settings.CPJ_BASE_URL
        self.login = settings.CPJ_LOGIN
        self.password = settings.CPJ_PASSWORD
        self.token_expiry_minutes = settings.CPJ_TOKEN_EXPIRY_MINUTES

        # Cache de autenticação
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        logger.info(f"CPJService inicializado - Base URL: {self.base_url}")

    async def _ensure_authenticated(self):
        """Garante token válido, renovando se necessário"""
        if not self._token or datetime.now() >= self._token_expiry:
            await self._login()

    async def _login(self):
        """Autentica e obtém token JWT"""
        try:
            logger.info("🔐 Autenticando no CPJ...")

            url = f"{self.base_url}/login"
            payload = {"login": self.login, "password": self.password}

            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()
            self._token = data.get("token")
            self._token_expiry = datetime.now() + timedelta(
                minutes=self.token_expiry_minutes
            )

            logger.info(
                f"✅ Autenticação CPJ bem-sucedida - Token válido até {self._token_expiry}"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de rede na autenticação CPJ: {e}")
            raise Exception(f"Erro de rede na autenticação CPJ: {e}")
        except Exception as e:
            logger.error(f"❌ Erro na autenticação CPJ: {e}")
            raise Exception(f"Erro na autenticação CPJ: {e}")

    async def buscar_processo_por_numero(self, numero_cnj: str) -> List[Dict[str, Any]]:
        """
        Busca processo no CPJ por número CNJ

        Args:
            numero_cnj: Número do processo CNJ

        Returns:
            Lista de processos encontrados
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔍 Buscando processo {numero_cnj} no CPJ...")

            url = f"{self.base_url}/processo"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            # Payload mais robusto com validação
            payload = {
                "filter": {"_and": [{"numero_processo": {"_eq": numero_cnj.strip()}}]}
            }

            logger.debug(f"🔍 [CPJ] Payload enviado: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            # Log detalhado da resposta para debug
            logger.debug(f"🔍 [CPJ] Status: {response.status_code}")
            logger.debug(f"🔍 [CPJ] Headers: {dict(response.headers)}")

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                # Para erro 400, retornar lista vazia em vez de falhar
                if response.status_code == 400:
                    logger.warning(
                        f"⚠️ [CPJ] Bad Request para '{numero_cnj}' - retornando lista vazia"
                    )
                    return []

            response.raise_for_status()

            data = response.json()
            processos = data if isinstance(data, list) else []

            logger.info(
                f"✅ Busca CPJ concluída - {len(processos)} processos encontrados"
            )

            return processos

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na busca CPJ para processo {numero_cnj}")
            # Para timeout, retornar lista vazia em vez de falhar
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na busca CPJ: {e}")
            # Para erros de rede, retornar lista vazia em vez de falhar
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na busca CPJ: {e}")
            # Para erros inesperados, retornar lista vazia em vez de falhar
            return []

    def is_authenticated(self) -> bool:
        """Verifica se está autenticado com token válido"""
        return self._token is not None and datetime.now() < self._token_expiry

    def get_token_info(self) -> Dict[str, Any]:
        """Retorna informações do token atual"""
        return {
            "has_token": self._token is not None,
            "expires_at": (
                self._token_expiry.isoformat() if self._token_expiry else None
            ),
            "is_valid": self.is_authenticated(),
        }
