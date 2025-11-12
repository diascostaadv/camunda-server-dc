"""
Serviço de integração com API DW LAW e-Protocol
Gerencia autenticação JWT e consulta processual
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from core.config import settings
from services.token_cache_service import get_token_cache

logger = logging.getLogger(__name__)


class DWLawService:
    """Serviço para integração com API DW LAW e-Protocol"""

    def __init__(self):
        self.base_url = settings.DW_LAW_BASE_URL
        self.usuario = settings.DW_LAW_USUARIO
        self.senha = settings.DW_LAW_SENHA
        self.token_expiry_minutes = settings.DW_LAW_TOKEN_EXPIRY_MINUTES

        # Cache de autenticação (em memória - fallback)
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._usuario_autenticado: Optional[str] = None

        # Cache Redis (persistente)
        self.token_cache = get_token_cache()

        logger.info(f"DWLawService inicializado - Base URL: {self.base_url}")
        logger.info(
            f"🔧 Cache Redis: {'✅ Habilitado' if self.token_cache.enabled else '❌ Desabilitado'}"
        )

    async def _ensure_authenticated(self):
        """Garante token válido, renovando se necessário"""
        # Verificar cache em memória primeiro
        if self._token and datetime.now() < self._token_expiry:
            logger.debug("✅ Token válido em memória")
            return

        # Tentar recuperar do Redis
        cached_token = self.token_cache.get_token("dw_law", self.usuario)
        if cached_token:
            self._token = cached_token.get("token")
            self._usuario_autenticado = cached_token.get("usuario")
            expires_at_str = cached_token.get("expires_at")
            if expires_at_str:
                self._token_expiry = datetime.fromisoformat(expires_at_str)
                logger.info(
                    f"♻️ Token DW LAW recuperado do cache Redis - Válido até {self._token_expiry}"
                )
                return

        # Não tem cache válido, fazer login
        await self._autenticar()

    async def _autenticar(self):
        """Autentica e obtém token JWT"""
        try:
            logger.info("🔐 Autenticando no DW LAW e-Protocol...")

            url = f"{self.base_url}/api/AUTENTICAR"
            payload = {"usuario": self.usuario, "senha": self.senha}
            logger.info(f"🔍 [DW_LAW] Payload enviado: {payload}")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()
            self._token = data.get("token")
            self._usuario_autenticado = data.get("usuario")

            # Token do DW LAW expira em tempo configurável (padrão: 2 horas conforme doc)
            self._token_expiry = datetime.now() + timedelta(
                minutes=self.token_expiry_minutes
            )

            logger.info(
                f"✅ Autenticação DW LAW bem-sucedida - Token válido até {self._token_expiry}"
            )

            # Armazenar token no Redis para persistência
            self.token_cache.set_token(
                api_name="dw_law",
                token=self._token,
                expires_at=self._token_expiry,
                usuario=self.usuario,
                extra_data={"base_url": self.base_url},
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de rede na autenticação DW LAW: {e}")
            raise Exception(f"Erro de rede na autenticação DW LAW: {e}")
        except Exception as e:
            logger.error(f"❌ Erro na autenticação DW LAW: {e}")
            raise Exception(f"Erro na autenticação DW LAW: {e}")

    # ==================== INSERIR PROCESSOS ====================

    async def inserir_processos(
        self, chave_projeto: str, processos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insere uma lista de processos em um projeto de Consulta Processual

        Args:
            chave_projeto: Chave única do projeto
            processos: Lista de processos com numero_processo, other_info_client1, other_info_client2

        Returns:
            Resultado da inserção com chaves de pesquisa criadas
        """
        try:
            await self._ensure_authenticated()

            logger.info(
                f"📤 Inserindo {len(processos)} processos no DW LAW - Projeto: {chave_projeto}"
            )

            url = f"{self.base_url}/api/consulta_processual/INSERIR_PROCESSOS"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"chave_projeto": chave_projeto, "processos": processos}

            logger.debug(f"📤 [DW_LAW] Payload enviado: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=60)

            logger.debug(f"📤 [DW_LAW] Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(
                    f"❌ [DW_LAW] Erro HTTP {response.status_code}: {response.text}"
                )
                return {
                    "success": False,
                    "retorno": f"ERRO_HTTP_{response.status_code}",
                    "obs": response.text,
                }

            response.raise_for_status()

            data = response.json()

            logger.info(
                f"✅ Inserção DW LAW concluída - Retorno: {data.get('retorno', 'SUCESSO')}"
            )

            return {"success": True, "data": data}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na inserção de processos DW LAW")
            return {
                "success": False,
                "retorno": "ERRO_TIMEOUT",
                "obs": "Timeout ao inserir processos",
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na inserção DW LAW: {e}")
            return {"success": False, "retorno": "ERRO_REDE", "obs": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na inserção DW LAW: {e}")
            return {"success": False, "retorno": "ERRO", "obs": str(e)}

    # ==================== EXCLUIR PROCESSOS ====================

    async def excluir_processos(
        self, chave_projeto: str, lista_de_processos: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Exclui uma lista de processos de um projeto de Consulta Processual

        Args:
            chave_projeto: Chave única do projeto
            lista_de_processos: Lista de processos com numero_processo

        Returns:
            Resultado da exclusão
        """
        try:
            await self._ensure_authenticated()

            logger.info(
                f"🗑️ Excluindo {len(lista_de_processos)} processos no DW LAW - Projeto: {chave_projeto}"
            )

            url = f"{self.base_url}/api/consulta_processual/EXCLUIR_PROCESSOS"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {
                "chave_projeto": chave_projeto,
                "lista_de_processos": lista_de_processos,
            }

            logger.debug(f"🗑️ [DW_LAW] Payload enviado: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=60)

            logger.debug(f"🗑️ [DW_LAW] Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(
                    f"❌ [DW_LAW] Erro HTTP {response.status_code}: {response.text}"
                )
                return {
                    "success": False,
                    "retorno": f"ERRO_HTTP_{response.status_code}",
                    "obs": response.text,
                }

            response.raise_for_status()

            data = response.json()

            logger.info(
                f"✅ Exclusão DW LAW concluída - Retorno: {data.get('retorno', 'SUCESSO')}"
            )

            return {"success": True, "data": data}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na exclusão de processos DW LAW")
            return {
                "success": False,
                "retorno": "ERRO_TIMEOUT",
                "obs": "Timeout ao excluir processos",
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na exclusão DW LAW: {e}")
            return {"success": False, "retorno": "ERRO_REDE", "obs": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na exclusão DW LAW: {e}")
            return {"success": False, "retorno": "ERRO", "obs": str(e)}

    # ==================== CONSULTAR PROCESSO ====================

    async def consultar_processo_por_chave(
        self, chave_de_pesquisa: str
    ) -> Dict[str, Any]:
        """
        Consulta processo completo por chave de pesquisa

        Args:
            chave_de_pesquisa: Chave de pesquisa retornada no INSERT

        Returns:
            Dados completos do processo (polos, movimentações, audiências, etc)
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔍 Consultando processo DW LAW - Chave: {chave_de_pesquisa}")

            url = f"{self.base_url}/api/consulta_processual/CONSULTAR_CHAVE_DE_PESQUISA"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"chave_de_pesquisa": chave_de_pesquisa}

            logger.debug(f"🔍 [DW_LAW] Payload enviado: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=120)

            logger.debug(f"🔍 [DW_LAW] Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(
                    f"❌ [DW_LAW] Erro HTTP {response.status_code}: {response.text}"
                )
                return {
                    "success": False,
                    "retorno": f"ERRO_HTTP_{response.status_code}",
                    "obs": response.text,
                }

            response.raise_for_status()

            data = response.json()

            # A API retorna uma lista com 1 elemento
            if isinstance(data, list) and len(data) > 0:
                processo_data = data[0]
                logger.info(
                    f"✅ Consulta DW LAW concluída - Processo: {processo_data.get('numero_processo', 'N/A')}"
                )

                return {"success": True, "data": processo_data}
            else:
                logger.warning(
                    f"⚠️ Processo não encontrado para chave: {chave_de_pesquisa}"
                )
                return {
                    "success": False,
                    "retorno": "ERRO_PROCESSO_NAO_ENCONTRADO",
                    "obs": "Processo não localizado",
                }

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na consulta de processo DW LAW")
            return {
                "success": False,
                "retorno": "ERRO_TIMEOUT",
                "obs": "Timeout ao consultar processo",
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta DW LAW: {e}")
            return {"success": False, "retorno": "ERRO_REDE", "obs": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta DW LAW: {e}")
            return {"success": False, "retorno": "ERRO", "obs": str(e)}

    # ==================== MÉTODOS AUXILIARES ====================

    def is_authenticated(self) -> bool:
        """Verifica se está autenticado com token válido"""
        return self._token is not None and datetime.now() < self._token_expiry

    def get_token_info(self) -> Dict[str, Any]:
        """Retorna informações do token atual"""
        return {
            "has_token": self._token is not None,
            "usuario": self._usuario_autenticado,
            "expires_at": (
                self._token_expiry.isoformat() if self._token_expiry else None
            ),
            "is_valid": self.is_authenticated(),
        }
