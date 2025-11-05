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

    # ==================== PUBLICAÇÕES ====================

    async def buscar_publicacoes_nao_vinculadas(
        self, filters: Optional[Dict[str, Any]] = None, sort: str = "data_publicacao", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Busca publicações não vinculadas a processos (Seção 4.2)

        Args:
            filters: Filtros de busca (opcional)
            sort: Campo para ordenação (padrão: data_publicacao)
            limit: Limite de resultados (padrão: 100)

        Returns:
            Lista de publicações não vinculadas
        """
        try:
            await self._ensure_authenticated()

            logger.info("🔍 Buscando publicações não vinculadas no CPJ...")

            url = f"{self.base_url}/publicacao"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            # Payload padrão: publicações pendentes sem vínculo
            default_filters = {
                "_and": [
                    {"evento_tarefa": {"_eq": "VINC"}},
                    {"motivo": {"_null": True}},
                ]
            }

            payload = {
                "filter": filters if filters else default_filters,
                "sort": sort,
                "limit": limit,
            }

            logger.debug(f"🔍 [CPJ] Payload publicações: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            publicacoes = data if isinstance(data, list) else []

            logger.info(
                f"✅ Busca de publicações CPJ concluída - {len(publicacoes)} encontradas"
            )

            return publicacoes

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na busca de publicações CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na busca de publicações CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na busca de publicações CPJ: {e}")
            return []

    async def atualizar_publicacao(
        self, id_tramitacao: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza publicação (Seção 4.3)

        Args:
            id_tramitacao: ID da tramitação
            data: Dados para atualização (deve incluir update_usuario, update_data_hora)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando publicação {id_tramitacao} no CPJ...")

            url = f"{self.base_url}/publicacao/atualizar/{id_tramitacao}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Publicação {id_tramitacao} atualizada com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na atualização de publicação {id_tramitacao}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de publicação: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de publicação: {e}")
            return {"success": False, "message": str(e)}

    # ==================== PESSOAS ====================

    async def consultar_pessoa(
        self, filters: Dict[str, Any], sort: str = "nome"
    ) -> List[Dict[str, Any]]:
        """
        Consulta pessoa (Seção 4.4)

        Args:
            filters: Filtros de busca (ex: {"codigo": {"_eq": 1}})
            sort: Campo para ordenação (padrão: nome)

        Returns:
            Lista de pessoas encontradas
        """
        try:
            await self._ensure_authenticated()

            logger.info("🔍 Consultando pessoa no CPJ...")

            url = f"{self.base_url}/pessoa"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"filter": filters, "sort": sort}

            logger.debug(f"🔍 [CPJ] Payload pessoa: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 404:
                logger.warning("⚠️ [CPJ] Pessoa não encontrada")
                return []

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            pessoas = data if isinstance(data, list) else []

            logger.info(f"✅ Consulta pessoa CPJ concluída - {len(pessoas)} encontradas")

            return pessoas

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na consulta de pessoa CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta de pessoa CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta de pessoa CPJ: {e}")
            return []

    async def cadastrar_pessoa(self, pessoa_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cadastra nova pessoa (Seção 4.5)

        Args:
            pessoa_data: Dados da pessoa (nome, cpf_cnpj, categoria, etc)

        Returns:
            Resultado do cadastro com código da pessoa
        """
        try:
            await self._ensure_authenticated()

            logger.info("➕ Cadastrando pessoa no CPJ...")

            url = f"{self.base_url}/pessoa/inserir"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=pessoa_data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            codigo = result.get("codigo")
            logger.info(f"✅ Pessoa cadastrada com sucesso - Código: {codigo}")

            return {"success": True, "codigo": codigo, "data": result}

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout no cadastro de pessoa CPJ")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de pessoa CPJ: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de pessoa CPJ: {e}")
            return {"success": False, "message": str(e)}

    async def atualizar_pessoa(
        self, codigo: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza pessoa existente (Seção 4.6)

        Args:
            codigo: Código da pessoa
            data: Dados para atualização (deve incluir update_usuario, update_data_hora)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando pessoa {codigo} no CPJ...")

            url = f"{self.base_url}/pessoa/atualizar/{codigo}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Pessoa {codigo} atualizada com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na atualização de pessoa {codigo}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de pessoa: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de pessoa: {e}")
            return {"success": False, "message": str(e)}

    # ==================== PROCESSOS ====================

    async def consultar_processos(
        self, filters: Dict[str, Any], sort: str = "ficha"
    ) -> List[Dict[str, Any]]:
        """
        Consulta processos com filtros avançados (Seção 4.7)

        Args:
            filters: Filtros de busca (ex: {"pj": {"_eq": 1}})
            sort: Campo para ordenação (padrão: ficha)

        Returns:
            Lista de processos encontrados (inclui envolvidos e pedidos)
        """
        try:
            await self._ensure_authenticated()

            logger.info("🔍 Consultando processos no CPJ...")

            url = f"{self.base_url}/processo"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"filter": filters, "sort": sort}

            logger.debug(f"🔍 [CPJ] Payload processos: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            processos = data if isinstance(data, list) else []

            logger.info(
                f"✅ Consulta processos CPJ concluída - {len(processos)} encontrados"
            )

            return processos

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na consulta de processos CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta de processos CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta de processos CPJ: {e}")
            return []

    async def cadastrar_processo(
        self, processo_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cadastra novo processo (Seção 4.8)

        Args:
            processo_data: Dados do processo (numero_processo, materia, acao, etc)

        Returns:
            Resultado do cadastro com PJ do processo
        """
        try:
            await self._ensure_authenticated()

            logger.info("➕ Cadastrando processo no CPJ...")

            url = f"{self.base_url}/processo/inserir"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(
                url, json=processo_data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            pj = result.get("pj")
            logger.info(f"✅ Processo cadastrado com sucesso - PJ: {pj}")

            return {"success": True, "pj": pj, "data": result}

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout no cadastro de processo CPJ")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de processo CPJ: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de processo CPJ: {e}")
            return {"success": False, "message": str(e)}

    async def atualizar_processo(self, pj: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza processo existente (Seção 4.9)

        Args:
            pj: Número do PJ do processo
            data: Dados para atualização (deve incluir update_usuario, update_data_hora)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando processo PJ {pj} no CPJ...")

            url = f"{self.base_url}/processo/atualizar/{pj}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Processo PJ {pj} atualizado com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na atualização de processo PJ {pj}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de processo: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de processo: {e}")
            return {"success": False, "message": str(e)}

    # ==================== PEDIDOS ====================

    async def consultar_pedidos(
        self, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Consulta pedidos de processos (Seção 4.10)

        Args:
            filters: Filtros de busca (ex: {"pj": {"_eq": 10}})

        Returns:
            Lista de pedidos encontrados
        """
        try:
            await self._ensure_authenticated()

            logger.info("🔍 Consultando pedidos no CPJ...")

            url = f"{self.base_url}/pedido"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"filter": filters}

            logger.debug(f"🔍 [CPJ] Payload pedidos: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            pedidos = data if isinstance(data, list) else []

            logger.info(
                f"✅ Consulta pedidos CPJ concluída - {len(pedidos)} encontrados"
            )

            return pedidos

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na consulta de pedidos CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta de pedidos CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta de pedidos CPJ: {e}")
            return []

    async def cadastrar_pedido(
        self, pj: int, pedidos_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Cadastra novo(s) pedido(s) em processo (Seção 4.11)

        Args:
            pj: Número do PJ do processo
            pedidos_data: Lista de pedidos a cadastrar

        Returns:
            Resultado do cadastro com sequência do pedido
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"➕ Cadastrando pedido(s) no processo PJ {pj} no CPJ...")

            url = f"{self.base_url}/processo/pedido/inserir/{pj}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(
                url, json=pedidos_data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            sequencia = result.get("sequencia")
            logger.info(f"✅ Pedido cadastrado com sucesso - Sequência: {sequencia}")

            return {"success": True, "sequencia": sequencia, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no cadastro de pedido PJ {pj}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de pedido: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de pedido: {e}")
            return {"success": False, "message": str(e)}

    async def atualizar_pedido(
        self, pj: int, sequencia: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza pedido existente (Seção 4.12)

        Args:
            pj: Número do PJ do processo
            sequencia: Sequência do pedido
            data: Dados para atualização (deve incluir update_usuario, update_data_hora)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando pedido PJ {pj} seq {sequencia} no CPJ...")

            url = f"{self.base_url}/processo/pedido/atualizar/{pj}/{sequencia}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Pedido PJ {pj} seq {sequencia} atualizado com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na atualização de pedido PJ {pj} seq {sequencia}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de pedido: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de pedido: {e}")
            return {"success": False, "message": str(e)}

    # ==================== ENVOLVIDOS ====================

    async def consultar_envolvidos(
        self, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Consulta envolvidos de processos (Seção 4.13)

        Args:
            filters: Filtros de busca (ex: {"pj": {"_eq": 10}})

        Returns:
            Lista de envolvidos encontrados
        """
        try:
            await self._ensure_authenticated()

            logger.info("🔍 Consultando envolvidos no CPJ...")

            url = f"{self.base_url}/envolvido"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            payload = {"filter": filters}

            logger.debug(f"🔍 [CPJ] Payload envolvidos: {payload}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            envolvidos = data if isinstance(data, list) else []

            logger.info(
                f"✅ Consulta envolvidos CPJ concluída - {len(envolvidos)} encontrados"
            )

            return envolvidos

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na consulta de envolvidos CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta de envolvidos CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta de envolvidos CPJ: {e}")
            return []

    async def cadastrar_envolvido(
        self, pj: int, envolvido_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cadastra novo envolvido em processo (Seção 4.14)

        Args:
            pj: Número do PJ do processo
            envolvido_data: Dados do envolvido (qualificacao, pessoa, responsavel, etc)

        Returns:
            Resultado do cadastro com sequência do envolvido
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"➕ Cadastrando envolvido no processo PJ {pj} no CPJ...")

            url = f"{self.base_url}/processo/envolvido/inserir/{pj}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(
                url, json=envolvido_data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            sequencia = result.get("sequencia")
            logger.info(f"✅ Envolvido cadastrado com sucesso - Sequência: {sequencia}")

            return {"success": True, "sequencia": sequencia, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no cadastro de envolvido PJ {pj}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de envolvido: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de envolvido: {e}")
            return {"success": False, "message": str(e)}

    async def atualizar_envolvido(
        self, pj: int, sequencia: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza envolvido existente (Seção 4.15)

        Args:
            pj: Número do PJ do processo
            sequencia: Sequência do envolvido
            data: Dados para atualização (deve incluir update_usuario, update_data_hora)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando envolvido PJ {pj} seq {sequencia} no CPJ...")

            url = f"{self.base_url}/processo/envolvido/atualizar/{pj}/{sequencia}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Envolvido PJ {pj} seq {sequencia} atualizado com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(
                f"⏱️ Timeout na atualização de envolvido PJ {pj} seq {sequencia}"
            )
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de envolvido: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de envolvido: {e}")
            return {"success": False, "message": str(e)}

    # ==================== TRAMITAÇÃO (ANDAMENTOS E TAREFAS) ====================

    async def cadastrar_andamento(
        self, pj: int, andamento_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cadastra novo andamento em processo (Seção 4.16)

        Args:
            pj: Número do PJ do processo
            andamento_data: Dados do andamento (evento, texto, data_hora_lan, interno)

        Returns:
            Resultado do cadastro com id_tramitacao do andamento
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"➕ Cadastrando andamento no processo PJ {pj} no CPJ...")

            url = f"{self.base_url}/processo/andamento/inserir/{pj}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(
                url, json=andamento_data, headers=headers, timeout=30
            )

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            id_tramitacao = result.get("id_tramitacao")
            logger.info(
                f"✅ Andamento cadastrado com sucesso - ID Tramitação: {id_tramitacao}"
            )

            return {"success": True, "id_tramitacao": id_tramitacao, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no cadastro de andamento PJ {pj}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de andamento: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de andamento: {e}")
            return {"success": False, "message": str(e)}

    async def cadastrar_tarefa(
        self, pj: int, tarefa_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cadastra nova tarefa em processo (Seção 4.17)

        Args:
            pj: Número do PJ do processo
            tarefa_data: Dados da tarefa (evento, texto, id_pessoa_solicitada, id_pessoa_atribuida, ag_data_hora)

        Returns:
            Resultado do cadastro com id_tramitacao da tarefa
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"➕ Cadastrando tarefa no processo PJ {pj} no CPJ...")

            url = f"{self.base_url}/processo/tarefa/inserir/{pj}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=tarefa_data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            id_tramitacao = result.get("id_tramitacao")
            logger.info(
                f"✅ Tarefa cadastrada com sucesso - ID Tramitação: {id_tramitacao}"
            )

            return {"success": True, "id_tramitacao": id_tramitacao, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no cadastro de tarefa PJ {pj}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de tarefa: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de tarefa: {e}")
            return {"success": False, "message": str(e)}

    async def atualizar_tarefa(
        self, id_tramitacao: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza tarefa existente (Seção 4.18)

        Args:
            id_tramitacao: ID da tramitação da tarefa
            data: Dados para atualização (deve incluir update_usuario, update_data_hora, id_tramitacao_motivo, id_tramitacao_situacao)

        Returns:
            Resultado da atualização
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"🔄 Atualizando tarefa {id_tramitacao} no CPJ...")

            url = f"{self.base_url}/processo/tarefa/atualizar/{id_tramitacao}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Tarefa {id_tramitacao} atualizada com sucesso")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout na atualização de tarefa {id_tramitacao}")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na atualização de tarefa: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado na atualização de tarefa: {e}")
            return {"success": False, "message": str(e)}

    # ==================== DOCUMENTOS ====================

    async def consultar_documentos(
        self, origem: str, id_origem: int
    ) -> List[Dict[str, Any]]:
        """
        Consulta documentos por módulo de origem (Seção 4.19)

        Args:
            origem: Módulo do sistema (ex: 'processo', 'pessoa')
            id_origem: Código do recurso onde documento está vinculado

        Returns:
            Lista de documentos encontrados
        """
        try:
            await self._ensure_authenticated()

            logger.info(
                f"🔍 Consultando documentos no CPJ - origem: {origem}, id: {id_origem}..."
            )

            url = f"{self.base_url}/documento/{origem}/{id_origem}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return []

            response.raise_for_status()

            data = response.json()
            documentos = data if isinstance(data, list) else []

            logger.info(
                f"✅ Consulta documentos CPJ concluída - {len(documentos)} encontrados"
            )

            return documentos

        except requests.exceptions.Timeout:
            logger.error("⏱️ Timeout na consulta de documentos CPJ")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede na consulta de documentos CPJ: {e}")
            return []

        except Exception as e:
            logger.error(f"💥 Erro inesperado na consulta de documentos CPJ: {e}")
            return []

    async def baixar_documento(self, id_ged: int) -> Optional[bytes]:
        """
        Baixa documento pelo ID GED (Seção 4.20)

        Args:
            id_ged: ID do documento no GED

        Returns:
            Conteúdo binário do documento ou None em caso de erro
        """
        try:
            await self._ensure_authenticated()

            logger.info(f"📥 Baixando documento GED {id_ged} do CPJ...")

            url = f"{self.base_url}/documento/baixar/{id_ged}"
            headers = {
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.get(url, headers=headers, timeout=60, stream=True)

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return None

            response.raise_for_status()

            content = response.content
            logger.info(
                f"✅ Documento GED {id_ged} baixado com sucesso - {len(content)} bytes"
            )

            return content

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no download de documento GED {id_ged}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no download de documento: {e}")
            return None

        except Exception as e:
            logger.error(f"💥 Erro inesperado no download de documento: {e}")
            return None

    async def cadastrar_documento(
        self, origem: str, id_origem: int, documento_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cadastra novo documento (Seção 4.21)

        Args:
            origem: Módulo do sistema (ex: 'processo', 'pessoa')
            id_origem: Código do recurso onde documento será vinculado
            documento_data: Dados do documento (path, texto, interno, versao, file_64 ou file_link, etc)

        Returns:
            Resultado do cadastro
        """
        try:
            await self._ensure_authenticated()

            logger.info(
                f"➕ Cadastrando documento no CPJ - origem: {origem}, id: {id_origem}..."
            )

            url = f"{self.base_url}/documentos/inserir/{origem}/{id_origem}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }

            response = requests.post(
                url, json=documento_data, headers=headers, timeout=60
            )

            if response.status_code != 200:
                logger.error(
                    f"❌ [CPJ] Erro HTTP {response.status_code}: {response.text}"
                )
                return {"success": False, "message": response.text}

            response.raise_for_status()

            result = response.json()
            logger.info("✅ Documento cadastrado com sucesso no CPJ")

            return {"success": True, "data": result}

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout no cadastro de documento")
            return {"success": False, "message": "Timeout"}

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐❌ Erro de rede no cadastro de documento: {e}")
            return {"success": False, "message": str(e)}

        except Exception as e:
            logger.error(f"💥 Erro inesperado no cadastro de documento: {e}")
            return {"success": False, "message": str(e)}
