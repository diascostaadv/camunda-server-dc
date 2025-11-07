"""
Serviço de Cache de Tokens usando Redis
Gerencia tokens JWT de APIs externas com expiração automática
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from redis import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from core.config import settings

logger = logging.getLogger(__name__)


class TokenCacheService:
    """Serviço centralizado de cache de tokens usando Redis"""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.enabled = True
        self._initialize_redis()

    def _initialize_redis(self):
        """Inicializa conexão com Redis"""
        try:
            # Parse Redis URI
            redis_uri = settings.REDIS_URI

            logger.info(f"🔌 Conectando ao Redis: {redis_uri}")

            # Criar cliente Redis
            self.redis_client = Redis.from_url(
                redis_uri,
                decode_responses=True,  # Retorna strings em vez de bytes
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Testar conexão
            self.redis_client.ping()

            logger.info("✅ Conexão Redis estabelecida com sucesso")
            self.enabled = True

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"❌ Erro ao conectar no Redis: {e}")
            logger.warning("⚠️ Cache de tokens DESABILITADO - autenticação será feita a cada request")
            self.enabled = False
            self.redis_client = None

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao inicializar Redis: {e}")
            self.enabled = False
            self.redis_client = None

    def _get_cache_key(self, api_name: str, usuario: str = None) -> str:
        """
        Gera chave de cache padronizada

        Args:
            api_name: Nome da API (cpj, dw_law, etc)
            usuario: Usuário específico (opcional)

        Returns:
            Chave de cache no formato: token:{api}:{usuario}
        """
        if usuario:
            return f"token:{api_name}:{usuario}"
        return f"token:{api_name}"

    def get_token(self, api_name: str, usuario: str = None) -> Optional[Dict[str, Any]]:
        """
        Recupera token do cache

        Args:
            api_name: Nome da API
            usuario: Usuário específico (opcional)

        Returns:
            Dict com token e metadados ou None se não existir/expirado
        """
        if not self.enabled or not self.redis_client:
            logger.debug("🔕 Cache desabilitado - retornando None")
            return None

        try:
            cache_key = self._get_cache_key(api_name, usuario)

            # Buscar no Redis
            cached_data = self.redis_client.get(cache_key)

            if not cached_data:
                logger.debug(f"🔍 Token não encontrado no cache: {cache_key}")
                return None

            # Parse JSON
            token_data = json.loads(cached_data)

            # Verificar se token expirou (validação adicional)
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() >= expires_at:
                    logger.warning(f"⏰ Token expirado no cache: {cache_key}")
                    self.delete_token(api_name, usuario)
                    return None

            logger.info(f"✅ Token recuperado do cache: {cache_key}")
            return token_data

        except json.JSONDecodeError as e:
            logger.error(f"💥 Erro ao decodificar JSON do cache: {e}")
            self.delete_token(api_name, usuario)
            return None

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"❌ Erro ao buscar token no Redis: {e}")
            return None

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao buscar token: {e}")
            return None

    def set_token(
        self,
        api_name: str,
        token: str,
        expires_at: datetime,
        usuario: str = None,
        extra_data: Dict[str, Any] = None
    ) -> bool:
        """
        Armazena token no cache com expiração

        Args:
            api_name: Nome da API
            token: Token JWT
            expires_at: Data/hora de expiração do token
            usuario: Usuário específico (opcional)
            extra_data: Dados adicionais para armazenar (opcional)

        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        if not self.enabled or not self.redis_client:
            logger.debug("🔕 Cache desabilitado - token não será armazenado")
            return False

        try:
            cache_key = self._get_cache_key(api_name, usuario)

            # Preparar dados para cache
            token_data = {
                "token": token,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat(),
                "api_name": api_name,
                "usuario": usuario
            }

            # Adicionar dados extras se fornecidos
            if extra_data:
                token_data.update(extra_data)

            # Calcular TTL (Time To Live) do Redis
            # Subtrair 1 minuto para margem de segurança
            ttl_seconds = int((expires_at - datetime.now()).total_seconds())

            if ttl_seconds <= 0:
                logger.warning(f"⚠️ Token já expirado, não será armazenado: {cache_key}")
                return False

            # Reduzir 60 segundos para margem de segurança
            ttl_seconds = max(ttl_seconds - 60, 60)

            # Armazenar no Redis com expiração automática
            self.redis_client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(token_data)
            )

            logger.info(
                f"💾 Token armazenado no cache: {cache_key} (TTL: {ttl_seconds}s / ~{ttl_seconds//60}min)"
            )
            return True

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"❌ Erro ao armazenar token no Redis: {e}")
            return False

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao armazenar token: {e}")
            return False

    def delete_token(self, api_name: str, usuario: str = None) -> bool:
        """
        Remove token do cache

        Args:
            api_name: Nome da API
            usuario: Usuário específico (opcional)

        Returns:
            True se removido com sucesso, False caso contrário
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._get_cache_key(api_name, usuario)
            result = self.redis_client.delete(cache_key)

            if result > 0:
                logger.info(f"🗑️ Token removido do cache: {cache_key}")
                return True
            else:
                logger.debug(f"🔍 Token não encontrado para remover: {cache_key}")
                return False

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"❌ Erro ao remover token do Redis: {e}")
            return False

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao remover token: {e}")
            return False

    def get_token_info(self, api_name: str, usuario: str = None) -> Dict[str, Any]:
        """
        Retorna informações do token sem o valor do token

        Args:
            api_name: Nome da API
            usuario: Usuário específico (opcional)

        Returns:
            Dict com metadados do token (sem o token em si)
        """
        token_data = self.get_token(api_name, usuario)

        if not token_data:
            return {
                "cached": False,
                "api_name": api_name,
                "usuario": usuario
            }

        return {
            "cached": True,
            "api_name": api_name,
            "usuario": usuario,
            "expires_at": token_data.get("expires_at"),
            "created_at": token_data.get("created_at"),
            "has_token": True
        }

    def clear_all_tokens(self, api_name: str = None) -> int:
        """
        Remove todos os tokens do cache

        Args:
            api_name: Se fornecido, remove apenas tokens desta API

        Returns:
            Número de tokens removidos
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            if api_name:
                # Remover tokens de uma API específica
                pattern = f"token:{api_name}:*"
            else:
                # Remover todos os tokens
                pattern = "token:*"

            # Buscar chaves que correspondem ao padrão
            keys = list(self.redis_client.scan_iter(match=pattern))

            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🗑️ {deleted} tokens removidos do cache (padrão: {pattern})")
                return deleted
            else:
                logger.debug(f"🔍 Nenhum token encontrado para remover (padrão: {pattern})")
                return 0

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"❌ Erro ao limpar tokens do Redis: {e}")
            return 0

        except Exception as e:
            logger.error(f"💥 Erro inesperado ao limpar tokens: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da conexão Redis

        Returns:
            Dict com status da conexão
        """
        if not self.redis_client:
            return {
                "healthy": False,
                "enabled": self.enabled,
                "message": "Redis client not initialized"
            }

        try:
            # Ping Redis
            self.redis_client.ping()

            # Contar tokens em cache
            token_count = len(list(self.redis_client.scan_iter(match="token:*", count=100)))

            return {
                "healthy": True,
                "enabled": self.enabled,
                "message": "Redis connection OK",
                "tokens_cached": token_count
            }

        except (RedisError, RedisConnectionError) as e:
            return {
                "healthy": False,
                "enabled": self.enabled,
                "message": f"Redis error: {str(e)}"
            }

        except Exception as e:
            return {
                "healthy": False,
                "enabled": self.enabled,
                "message": f"Unexpected error: {str(e)}"
            }


# Instância global (singleton)
_token_cache_instance: Optional[TokenCacheService] = None


def get_token_cache() -> TokenCacheService:
    """
    Retorna instância singleton do TokenCacheService

    Returns:
        Instância do TokenCacheService
    """
    global _token_cache_instance

    if _token_cache_instance is None:
        _token_cache_instance = TokenCacheService()

    return _token_cache_instance
