"""
Testes de integração para endpoint /publicacoes/verificar-processo-cnj
Testa a API REST que integra com CPJService
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from datetime import datetime


class TestVerificarProcessoCNJEndpoint:
    """Testes do endpoint POST /publicacoes/verificar-processo-cnj"""

    @pytest.mark.asyncio
    async def test_endpoint_success_with_numero_cnj(
        self, mock_cpj_processo_encontrado, cpj_request_valid
    ):
        """Testa request válido com numero_cnj retorna processos"""
        from routers.publicacoes import verificar_processo_cnj

        # Mock do CPJService
        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=cpj_request_valid, cpj_service=mock_service
            )

            # Verifica estrutura da resposta
            assert response["status"] == "success"
            assert response["numero_cnj"] == "0000036-58.2019.8.16.0033"
            assert response["total_encontrados"] == 2
            assert len(response["processos"]) == 2
            assert "timestamp" in response

            # Verifica que chamou o service
            mock_service.buscar_processo_por_numero.assert_called_once_with(
                "0000036-58.2019.8.16.0033"
            )

    @pytest.mark.asyncio
    async def test_endpoint_success_with_numero_processo(
        self, mock_cpj_processo_encontrado, cpj_request_alternative_field
    ):
        """Testa request com campo alternativo numero_processo"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=cpj_request_alternative_field, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["numero_cnj"] == "0000036-58.2019.8.16.0033"
            mock_service.buscar_processo_por_numero.assert_called_once_with(
                "0000036-58.2019.8.16.0033"
            )

    @pytest.mark.asyncio
    async def test_endpoint_success_with_variables_format(
        self, mock_cpj_processo_encontrado, cpj_request_with_variables
    ):
        """Testa request com formato de worker (variables.numero_cnj)"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=cpj_request_with_variables, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["numero_cnj"] == "0000036-58.2019.8.16.0033"

    @pytest.mark.asyncio
    async def test_endpoint_missing_numero_cnj_raises_400(
        self, cpj_request_invalid_missing_numero
    ):
        """Testa que request sem numero_cnj retorna erro 400"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(
                request=cpj_request_invalid_missing_numero, cpj_service=mock_service
            )

        assert exc_info.value.status_code == 400
        assert "numero_cnj é obrigatório" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_endpoint_empty_results(self, mock_cpj_processo_nao_encontrado):
        """Testa resposta quando não encontra processos"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_nao_encontrado
        )

        request = {"numero_cnj": "9999999-99.9999.9.99.9999"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["total_encontrados"] == 0
            assert response["processos"] == []

    @pytest.mark.asyncio
    async def test_endpoint_single_result(self, mock_cpj_processo_single):
        """Testa resposta com único processo encontrado"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_single
        )

        request = {"numero_cnj": "1234567-89.2023.8.13.0024"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["total_encontrados"] == 1
            assert len(response["processos"]) == 1
            assert response["processos"][0]["tribunal"] == "TJMG"

    @pytest.mark.asyncio
    async def test_endpoint_service_raises_exception(self):
        """Testa que exceção do service é propagada como HTTPException 500"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.side_effect = Exception(
            "CPJ Service Error"
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 500
        assert "CPJ Service Error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_endpoint_response_structure(self, mock_cpj_processo_encontrado):
        """Testa estrutura completa da resposta"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            # Verifica campos obrigatórios
            assert "status" in response
            assert "numero_cnj" in response
            assert "processos" in response
            assert "total_encontrados" in response
            assert "timestamp" in response

            # Verifica valores
            assert response["status"] == "success"
            assert isinstance(response["processos"], list)
            assert isinstance(response["total_encontrados"], int)
            assert response["total_encontrados"] == len(response["processos"])

            # Verifica timestamp é ISO format
            datetime.fromisoformat(response["timestamp"])

    @pytest.mark.asyncio
    async def test_endpoint_preserves_numero_cnj_format(self):
        """Testa que formato do numero_cnj é preservado na resposta"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = []

        # Testa diferentes formatos
        formatos = [
            "0000036-58.2019.8.16.0033",
            "1234567-89.2023.8.13.0024",
            "não informado",
        ]

        for formato in formatos:
            request = {"numero_cnj": formato}

            with patch(
                "routers.publicacoes.get_cpj_service", return_value=mock_service
            ):
                response = await verificar_processo_cnj(
                    request=request, cpj_service=mock_service
                )

                assert response["numero_cnj"] == formato

    @pytest.mark.asyncio
    async def test_endpoint_logs_request_details(
        self, mock_cpj_processo_encontrado, caplog
    ):
        """Testa que endpoint loga detalhes do request"""
        from routers.publicacoes import verificar_processo_cnj
        import logging

        caplog.set_level(logging.INFO)

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        # Verifica logs
        assert any("CPJ" in record.message for record in caplog.records)
        assert any("0000036-58.2019.8.16.0033" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_endpoint_handles_real_processo_format(
        self, mock_cpj_processo_encontrado
    ):
        """Testa que endpoint aceita número de processo no formato real CNJ"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        # Formato real do log fornecido pelo usuário
        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["numero_cnj"] == "0000036-58.2019.8.16.0033"
            assert response["total_encontrados"] == 2

            # Verifica dados dos processos encontrados
            processo1 = response["processos"][0]
            assert processo1["numero_processo"] == "0000036-58.2019.8.16.0033"
            assert processo1["tribunal"] == "TJPR"
            assert "partes" in processo1
            assert "ultima_movimentacao" in processo1


class TestVerificarProcessoCNJEdgeCases:
    """Testes de casos extremos e edge cases"""

    @pytest.mark.asyncio
    async def test_endpoint_numero_cnj_with_spaces(self):
        """Testa numero_cnj com espaços extras"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = []

        request = {"numero_cnj": "  0000036-58.2019.8.16.0033  "}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            # Endpoint deve aceitar e processar normalmente
            assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_endpoint_numero_cnj_special_value_nao_informado(self):
        """Testa valor especial 'não informado'"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = []

        request = {"numero_cnj": "não informado"}

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            assert response["status"] == "success"
            assert response["numero_cnj"] == "não informado"
            mock_service.buscar_processo_por_numero.assert_called_once_with(
                "não informado"
            )

    @pytest.mark.asyncio
    async def test_endpoint_request_with_extra_fields(
        self, mock_cpj_processo_encontrado
    ):
        """Testa request com campos extras (deve ignorar)"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        request = {
            "numero_cnj": "0000036-58.2019.8.16.0033",
            "extra_field": "should be ignored",
            "another_field": 123,
        }

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            assert response["status"] == "success"
            # Campos extras não devem afetar processamento

    @pytest.mark.asyncio
    async def test_endpoint_multiple_numero_fields_precedence(
        self, mock_cpj_processo_encontrado
    ):
        """Testa precedência quando múltiplos campos de número estão presentes"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        # numero_cnj tem precedência sobre numero_processo
        request = {
            "numero_cnj": "0000036-58.2019.8.16.0033",
            "numero_processo": "9999999-99.9999.9.99.9999",
        }

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            # Deve usar numero_cnj
            mock_service.buscar_processo_por_numero.assert_called_once_with(
                "0000036-58.2019.8.16.0033"
            )

    @pytest.mark.asyncio
    async def test_endpoint_variables_precedence_over_direct(
        self, mock_cpj_processo_encontrado
    ):
        """Testa precedência de variables.numero_cnj vs numero_cnj direto"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.return_value = (
            mock_cpj_processo_encontrado
        )

        # Quando ambos presentes, numero_cnj direto tem precedência
        request = {
            "numero_cnj": "0000036-58.2019.8.16.0033",
            "variables": {"numero_cnj": "9999999-99.9999.9.99.9999"},
        }

        with patch(
            "routers.publicacoes.get_cpj_service", return_value=mock_service
        ):
            response = await verificar_processo_cnj(
                request=request, cpj_service=mock_service
            )

            # Deve usar campo direto
            mock_service.buscar_processo_por_numero.assert_called_once_with(
                "0000036-58.2019.8.16.0033"
            )


class TestVerificarProcessoCNJErrorHandling:
    """Testes de tratamento de erros"""

    @pytest.mark.asyncio
    async def test_endpoint_cpj_service_timeout(self):
        """Testa timeout no CPJService"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.side_effect = Exception(
            "Timeout na busca CPJ para processo 0000036-58.2019.8.16.0033"
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 500
        assert "Timeout" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_endpoint_cpj_service_auth_error(self):
        """Testa erro de autenticação propagado do CPJService"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.side_effect = Exception(
            "Erro de rede na autenticação CPJ"
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 500
        assert "autenticação CPJ" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_endpoint_cpj_service_connection_error(self):
        """Testa erro de conexão propagado do CPJService"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()
        mock_service.buscar_processo_por_numero.side_effect = Exception(
            "Erro de rede na busca CPJ"
        )

        request = {"numero_cnj": "0000036-58.2019.8.16.0033"}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 500
        assert "rede" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_endpoint_empty_dict_request(self):
        """Testa request com dicionário vazio"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()

        request = {}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_endpoint_null_numero_cnj(self):
        """Testa request com numero_cnj = None"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()

        request = {"numero_cnj": None}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_endpoint_empty_string_numero_cnj(self):
        """Testa request com numero_cnj vazio"""
        from routers.publicacoes import verificar_processo_cnj

        mock_service = AsyncMock()

        request = {"numero_cnj": ""}

        with pytest.raises(HTTPException) as exc_info:
            await verificar_processo_cnj(request=request, cpj_service=mock_service)

        assert exc_info.value.status_code == 400
