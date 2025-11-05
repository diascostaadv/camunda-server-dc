"""
CPJ-3C Authentication Manager
Gerencia autenticação JWT com cache e renovação automática
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class CPJAuthManager:
    """
    Gerenciador de autenticação para API CPJ-3C

    Responsabilidades:
    - Gerenciar tokens JWT
    - Cache de tokens (in-memory)
    - Renovação automática antes da expiração
    """

    def __init__(self, base_url: str, username: str, password: str):
        """
        Inicializa o gerenciador de autenticação

        Args:
            base_url: URL base da API CPJ-3C
            username: Usuário API
            password: Senha API
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password

        # Cache in-memory (pode ser substituído por Redis depois)
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        logger.info(f"CPJAuthManager inicializado para {self.base_url}")

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Obtém token JWT válido (com cache)

        Args:
            force_refresh: Força novo login mesmo com token válido

        Returns:
            Token JWT válido
        """
        # Verificar cache
        if not force_refresh and self._is_token_valid():
            logger.debug("✅ Usando token JWT do cache")
            return self._token

        # Token expirado ou não existe - fazer login
        logger.info("🔐 Token expirado ou ausente, realizando login...")
        return self._login()

    def _is_token_valid(self) -> bool:
        """
        Verifica se o token em cache ainda é válido

        Returns:
            True se token válido, False caso contrário
        """
        if not self._token or not self._token_expiry:
            return False

        # Considerar válido se expira em mais de 5 minutos
        now = datetime.now()
        expires_soon = self._token_expiry - timedelta(minutes=5)

        if now >= expires_soon:
            logger.debug("⏰ Token próximo de expirar")
            return False

        return True

    def _login(self) -> str:
        """
        Realiza login na API CPJ-3C e obtém novo token

        Returns:
            Token JWT

        Raises:
            Exception: Se login falhar
        """
        import requests

        url = f"{self.base_url}/login"
        payload = {
            "login": self.username,
            "password": self.password
        }

        try:
            logger.info(f"📤 POST {url}")

            response = requests.post(
                url,
                json=payload,
                timeout=10,
                verify=False  # TODO: Verificar SSL em produção
            )
            response.raise_for_status()

            data = response.json()
            token = data.get("token")

            if not token:
                raise ValueError("Token não retornado pela API CPJ-3C")

            # Cachear token (default: 23 horas)
            self._token = token
            self._token_expiry = datetime.now() + timedelta(hours=23)

            logger.info(f"✅ Login realizado com sucesso")
            logger.info(f"🕒 Token expira em: {self._token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")

            return token

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro no login CPJ-3C: {e}")
            raise Exception(f"Falha na autenticação CPJ-3C: {str(e)}")

    def clear_cache(self):
        """Limpa cache de token (forçar novo login)"""
        self._token = None
        self._token_expiry = None
        logger.info("🗑️  Cache de token limpo")

    def get_headers(self) -> dict:
        """
        Retorna headers HTTP com autenticação

        Returns:
            Dict com headers incluindo Authorization
        """
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
