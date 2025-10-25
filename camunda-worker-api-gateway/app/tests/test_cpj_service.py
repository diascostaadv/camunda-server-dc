"""
Testes unitários para CPJService
Testa integração com API CPJ (autenticação e busca de processos)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from services.cpj_service import CPJService


class TestCPJServiceInit:
    """Testes de inicialização do CPJService"""

    def test_init_with_default_settings(self, mock_settings):
        """Testa inicialização com settings padrão"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            assert service.base_url == mock_settings.CPJ_BASE_URL
            assert service.login == mock_settings.CPJ_LOGIN
            assert service.password == mock_settings.CPJ_PASSWORD
            assert service.token_expiry_minutes == mock_settings.CPJ_TOKEN_EXPIRY_MINUTES
            assert service._token is None
            assert service._token_expiry is None

    def test_init_loads_config_correctly(self, cpj_config):
        """Testa que configuração é carregada corretamente"""
        with patch("services.cpj_service.settings") as mock_settings:
            mock_settings.CPJ_BASE_URL = cpj_config["base_url"]
            mock_settings.CPJ_LOGIN = cpj_config["login"]
            mock_settings.CPJ_PASSWORD = cpj_config["password"]
            mock_settings.CPJ_TOKEN_EXPIRY_MINUTES = cpj_config["token_expiry_minutes"]

            service = CPJService()

            assert service.base_url == cpj_config["base_url"]
            assert service.login == cpj_config["login"]


class TestCPJServiceLogin:
    """Testes de autenticação no CPJ"""

    @pytest.mark.asyncio
    async def test_login_success(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa login bem-sucedido"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            mock_response = create_response(200, mock_cpj_auth_success)

            with patch("requests.post", return_value=mock_response) as mock_post:
                await service._login()

                # Verifica chamada HTTP
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                assert args[0] == f"{mock_settings.CPJ_BASE_URL}/login"
                assert kwargs["json"] == {
                    "login": mock_settings.CPJ_LOGIN,
                    "password": mock_settings.CPJ_PASSWORD,
                }
                assert kwargs["headers"]["Content-Type"] == "application/json"
                assert kwargs["timeout"] == 30

                # Verifica token foi armazenado
                assert service._token == mock_cpj_auth_success["token"]
                assert service._token_expiry is not None
                assert service._token_expiry > datetime.now()

    @pytest.mark.asyncio
    async def test_login_sets_expiry_correctly(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa que expiração do token é calculada corretamente"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            mock_response = create_response(200, mock_cpj_auth_success)

            before_login = datetime.now()

            with patch("requests.post", return_value=mock_response):
                await service._login()

            after_login = datetime.now()

            # Token deve expirar em ~30 minutos
            expected_min = before_login + timedelta(
                minutes=mock_settings.CPJ_TOKEN_EXPIRY_MINUTES - 1
            )
            expected_max = after_login + timedelta(
                minutes=mock_settings.CPJ_TOKEN_EXPIRY_MINUTES + 1
            )

            assert expected_min <= service._token_expiry <= expected_max

    @pytest.mark.asyncio
    async def test_login_http_error(self, mock_settings, create_response):
        """Testa erro HTTP durante login (401 Unauthorized)"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            mock_response = create_response(
                401, {"error": "Invalid credentials"}, "Unauthorized"
            )

            with patch("requests.post", return_value=mock_response):
                with pytest.raises(Exception) as exc_info:
                    await service._login()

                assert "Erro de rede na autenticação CPJ" in str(exc_info.value)
                assert service._token is None

    @pytest.mark.asyncio
    async def test_login_timeout_error(self, mock_settings, mock_timeout_error):
        """Testa timeout durante login"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            with patch("requests.post", side_effect=mock_timeout_error):
                with pytest.raises(Exception) as exc_info:
                    await service._login()

                assert "Erro de rede na autenticação CPJ" in str(exc_info.value)
                assert service._token is None

    @pytest.mark.asyncio
    async def test_login_connection_error(self, mock_settings, mock_connection_error):
        """Testa erro de conexão durante login"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            with patch("requests.post", side_effect=mock_connection_error):
                with pytest.raises(Exception) as exc_info:
                    await service._login()

                assert "Erro de rede na autenticação CPJ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_login_generic_error(self, mock_settings):
        """Testa erro genérico durante login"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            with patch("requests.post", side_effect=ValueError("Unexpected error")):
                with pytest.raises(Exception) as exc_info:
                    await service._login()

                assert "Erro na autenticação CPJ" in str(exc_info.value)


class TestCPJServiceEnsureAuthenticated:
    """Testes de garantia de autenticação válida"""

    @pytest.mark.asyncio
    async def test_ensure_authenticated_when_no_token(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa que faz login quando não tem token"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            mock_response = create_response(200, mock_cpj_auth_success)

            assert service._token is None

            with patch("requests.post", return_value=mock_response):
                await service._ensure_authenticated()

            assert service._token is not None

    @pytest.mark.asyncio
    async def test_ensure_authenticated_when_token_expired(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa que renova token quando expirado"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            mock_response = create_response(200, mock_cpj_auth_success)

            # Simula token expirado
            service._token = "old_token"
            service._token_expiry = datetime.now() - timedelta(minutes=1)

            with patch("requests.post", return_value=mock_response):
                await service._ensure_authenticated()

            # Token deve ser renovado
            assert service._token == mock_cpj_auth_success["token"]
            assert service._token != "old_token"

    @pytest.mark.asyncio
    async def test_ensure_authenticated_when_token_valid(
        self, mock_settings, mock_cpj_auth_success
    ):
        """Testa que não faz login quando token ainda válido"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            # Simula token válido
            service._token = "valid_token"
            service._token_expiry = datetime.now() + timedelta(minutes=15)

            with patch("requests.post") as mock_post:
                await service._ensure_authenticated()

                # Não deve chamar API
                mock_post.assert_not_called()
                assert service._token == "valid_token"


class TestCPJServiceBuscarProcesso:
    """Testes de busca de processo por número CNJ"""

    @pytest.mark.asyncio
    async def test_buscar_processo_success_multiple_results(
        self,
        mock_settings,
        mock_cpj_auth_success,
        mock_cpj_processo_encontrado,
        create_response,
    ):
        """Testa busca bem-sucedida retornando múltiplos processos"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            # Mock de autenticação
            auth_response = create_response(200, mock_cpj_auth_success)
            # Mock de busca
            search_response = create_response(200, mock_cpj_processo_encontrado)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                resultado = await service.buscar_processo_por_numero(
                    "0000036-58.2019.8.16.0033"
                )

                # Verifica resultado
                assert isinstance(resultado, list)
                assert len(resultado) == 2
                assert resultado[0]["numero_processo"] == "0000036-58.2019.8.16.0033"
                assert resultado[0]["tribunal"] == "TJPR"
                assert resultado[0]["comarca"] == "Curitiba"

                # Verifica segunda chamada (busca)
                assert mock_post.call_count == 2
                _, kwargs = mock_post.call_args
                assert kwargs["json"]["filter"]["_and"][0]["numero_processo"]["_eq"] == "0000036-58.2019.8.16.0033"
                assert "Authorization" in kwargs["headers"]
                assert kwargs["headers"]["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_buscar_processo_success_single_result(
        self,
        mock_settings,
        mock_cpj_auth_success,
        mock_cpj_processo_single,
        create_response,
    ):
        """Testa busca retornando único processo"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)
            search_response = create_response(200, mock_cpj_processo_single)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                resultado = await service.buscar_processo_por_numero(
                    "1234567-89.2023.8.13.0024"
                )

                assert len(resultado) == 1
                assert resultado[0]["tribunal"] == "TJMG"
                assert resultado[0]["comarca"] == "Belo Horizonte"

    @pytest.mark.asyncio
    async def test_buscar_processo_not_found(
        self,
        mock_settings,
        mock_cpj_auth_success,
        mock_cpj_processo_nao_encontrado,
        create_response,
    ):
        """Testa busca sem resultados"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)
            search_response = create_response(200, mock_cpj_processo_nao_encontrado)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                resultado = await service.buscar_processo_por_numero("9999999-99.9999.9.99.9999")

                assert resultado == []

    @pytest.mark.asyncio
    async def test_buscar_processo_uses_cached_token(
        self, mock_settings, mock_cpj_processo_encontrado, create_response
    ):
        """Testa que usa token em cache ao buscar processo"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            # Simula token já autenticado
            service._token = "cached_token"
            service._token_expiry = datetime.now() + timedelta(minutes=20)

            search_response = create_response(200, mock_cpj_processo_encontrado)

            with patch("requests.post", return_value=search_response) as mock_post:
                await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                # Deve fazer apenas 1 chamada (busca), não autentica
                assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_buscar_processo_timeout(
        self, mock_settings, mock_cpj_auth_success, mock_timeout_error, create_response
    ):
        """Testa timeout na busca de processo"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, mock_timeout_error]

                with pytest.raises(Exception) as exc_info:
                    await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                assert "Timeout na busca CPJ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_buscar_processo_http_error(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa erro HTTP na busca de processo"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)
            error_response = create_response(500, {"error": "Internal Server Error"})

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, error_response]

                with pytest.raises(Exception) as exc_info:
                    await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                assert "Erro de rede na busca CPJ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_buscar_processo_connection_error(
        self, mock_settings, mock_cpj_auth_success, mock_connection_error, create_response
    ):
        """Testa erro de conexão na busca"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, mock_connection_error]

                with pytest.raises(Exception) as exc_info:
                    await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                assert "Erro de rede na busca CPJ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_buscar_processo_generic_error(
        self, mock_settings, mock_cpj_auth_success, create_response
    ):
        """Testa erro genérico na busca"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [
                    auth_response,
                    ValueError("Unexpected error"),
                ]

                with pytest.raises(Exception) as exc_info:
                    await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                assert "Erro inesperado na busca CPJ" in str(exc_info.value)


class TestCPJServiceHelpers:
    """Testes de métodos auxiliares do CPJService"""

    def test_is_authenticated_with_valid_token(self, mock_settings):
        """Testa is_authenticated com token válido"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            service._token = "valid_token"
            service._token_expiry = datetime.now() + timedelta(minutes=10)

            assert service.is_authenticated() is True

    def test_is_authenticated_with_expired_token(self, mock_settings):
        """Testa is_authenticated com token expirado"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            service._token = "expired_token"
            service._token_expiry = datetime.now() - timedelta(minutes=1)

            assert service.is_authenticated() is False

    def test_is_authenticated_without_token(self, mock_settings):
        """Testa is_authenticated sem token"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            assert service.is_authenticated() is False

    def test_get_token_info_with_valid_token(self, mock_settings):
        """Testa get_token_info com token válido"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            expiry = datetime.now() + timedelta(minutes=15)
            service._token = "test_token"
            service._token_expiry = expiry

            info = service.get_token_info()

            assert info["has_token"] is True
            assert info["expires_at"] == expiry.isoformat()
            assert info["is_valid"] is True

    def test_get_token_info_without_token(self, mock_settings):
        """Testa get_token_info sem token"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            info = service.get_token_info()

            assert info["has_token"] is False
            assert info["expires_at"] is None
            assert info["is_valid"] is False

    def test_get_token_info_with_expired_token(self, mock_settings):
        """Testa get_token_info com token expirado"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()
            expiry = datetime.now() - timedelta(minutes=5)
            service._token = "expired_token"
            service._token_expiry = expiry

            info = service.get_token_info()

            assert info["has_token"] is True
            assert info["expires_at"] == expiry.isoformat()
            assert info["is_valid"] is False


class TestCPJServiceIntegrationFlow:
    """Testes de fluxo completo de integração"""

    @pytest.mark.asyncio
    async def test_full_flow_first_request(
        self,
        mock_settings,
        mock_cpj_auth_success,
        mock_cpj_processo_encontrado,
        create_response,
    ):
        """Testa fluxo completo: autenticação + busca na primeira requisição"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            auth_response = create_response(200, mock_cpj_auth_success)
            search_response = create_response(200, mock_cpj_processo_encontrado)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                # Primeira busca deve autenticar
                resultado1 = await service.buscar_processo_por_numero(
                    "0000036-58.2019.8.16.0033"
                )

                assert len(resultado1) == 2
                assert mock_post.call_count == 2  # Auth + Search

                # Segunda busca deve reusar token
                mock_post.reset_mock()
                mock_post.side_effect = [search_response]

                resultado2 = await service.buscar_processo_por_numero(
                    "0000036-58.2019.8.16.0033"
                )

                assert len(resultado2) == 2
                assert mock_post.call_count == 1  # Apenas Search

    @pytest.mark.asyncio
    async def test_full_flow_token_renewal(
        self,
        mock_settings,
        mock_cpj_auth_success,
        mock_cpj_processo_single,
        create_response,
    ):
        """Testa renovação automática de token expirado"""
        with patch("services.cpj_service.settings", mock_settings):
            service = CPJService()

            # Primeira autenticação
            auth_response1 = create_response(200, mock_cpj_auth_success)
            search_response1 = create_response(200, mock_cpj_processo_single)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response1, search_response1]

                await service.buscar_processo_por_numero("1234567-89.2023.8.13.0024")

                # Simula expiração do token
                service._token_expiry = datetime.now() - timedelta(minutes=1)

                # Segunda requisição deve renovar token
                auth_response2 = create_response(
                    200,
                    {
                        "token": "new_token_after_renewal",
                        "expires_in": 1800,
                    },
                )
                search_response2 = create_response(200, mock_cpj_processo_single)

                mock_post.reset_mock()
                mock_post.side_effect = [auth_response2, search_response2]

                await service.buscar_processo_por_numero("1234567-89.2023.8.13.0024")

                # Deve ter autenticado novamente
                assert mock_post.call_count == 2
                assert service._token == "new_token_after_renewal"
