"""
Teste específico para validar o payload retornado pelo CPJService
Verifica estrutura completa da resposta para o processo 0000036-58.2019.8.16.0033
"""

import pytest
from unittest.mock import patch, Mock
from services.cpj_service import CPJService


class TestCPJPayloadValidation:
    """Testes de validação do payload retornado"""

    @pytest.mark.asyncio
    async def test_payload_structure_complete(self):
        """Testa estrutura completa do payload para processo real"""
        # Mock settings
        with patch("services.cpj_service.settings") as mock_settings:
            mock_settings.CPJ_BASE_URL = "https://test.api/v2"
            mock_settings.CPJ_LOGIN = "test"
            mock_settings.CPJ_PASSWORD = "test123"
            mock_settings.CPJ_TOKEN_EXPIRY_MINUTES = 30

            service = CPJService()

            # Mock de autenticação
            auth_response = Mock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"token": "test_token_123"}
            auth_response.raise_for_status = Mock()

            # Mock de busca - PAYLOAD REAL esperado
            expected_payload = [
                {
                    "id": 12345,
                    "numero_processo": "0000036-58.2019.8.16.0033",
                    "tribunal": "TJPR",
                    "comarca": "Curitiba",
                    "vara": "1ª Vara Cível",
                    "data_distribuicao": "2019-01-15",
                    "valor_causa": "R$ 50.000,00",
                    "partes": [
                        {
                            "tipo": "autor",
                            "nome": "João da Silva",
                            "cpf": "123.456.789-00",
                        },
                        {
                            "tipo": "reu",
                            "nome": "Maria dos Santos",
                            "cpf": "987.654.321-00",
                        },
                    ],
                    "ultima_movimentacao": "2024-10-20",
                    "status": "Em andamento",
                },
                {
                    "id": 12346,
                    "numero_processo": "0000036-58.2019.8.16.0033",
                    "tribunal": "TJPR",
                    "comarca": "Londrina",
                    "vara": "2ª Vara Cível",
                    "data_distribuicao": "2019-01-15",
                    "valor_causa": "R$ 50.000,00",
                    "partes": [
                        {
                            "tipo": "autor",
                            "nome": "João da Silva",
                            "cpf": "123.456.789-00",
                        }
                    ],
                    "ultima_movimentacao": "2024-10-22",
                    "status": "Em andamento",
                },
            ]

            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = expected_payload
            search_response.raise_for_status = Mock()

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                # Executa busca
                result = await service.buscar_processo_por_numero(
                    "0000036-58.2019.8.16.0033"
                )

                # ========== VALIDAÇÕES DO PAYLOAD ==========

                # 1. Tipo de retorno
                assert isinstance(result, list), "Deve retornar uma lista"
                assert len(result) == 2, "Deve retornar 2 processos"

                # 2. Estrutura de cada processo
                for processo in result:
                    assert isinstance(processo, dict), "Cada processo deve ser um dict"

                    # Campos obrigatórios
                    assert "id" in processo, "Deve ter campo 'id'"
                    assert (
                        "numero_processo" in processo
                    ), "Deve ter campo 'numero_processo'"
                    assert "tribunal" in processo, "Deve ter campo 'tribunal'"
                    assert "comarca" in processo, "Deve ter campo 'comarca'"
                    assert "status" in processo, "Deve ter campo 'status'"

                # 3. Validação do primeiro processo
                processo1 = result[0]
                assert processo1["id"] == 12345
                assert processo1["numero_processo"] == "0000036-58.2019.8.16.0033"
                assert processo1["tribunal"] == "TJPR"
                assert processo1["comarca"] == "Curitiba"
                assert processo1["vara"] == "1ª Vara Cível"
                assert processo1["data_distribuicao"] == "2019-01-15"
                assert processo1["valor_causa"] == "R$ 50.000,00"
                assert processo1["ultima_movimentacao"] == "2024-10-20"
                assert processo1["status"] == "Em andamento"

                # 4. Validação das partes
                assert "partes" in processo1, "Deve ter campo 'partes'"
                assert isinstance(processo1["partes"], list), "Partes deve ser lista"
                assert len(processo1["partes"]) == 2, "Deve ter 2 partes"

                # Validação do autor
                autor = processo1["partes"][0]
                assert autor["tipo"] == "autor"
                assert autor["nome"] == "João da Silva"
                assert autor["cpf"] == "123.456.789-00"

                # Validação do réu
                reu = processo1["partes"][1]
                assert reu["tipo"] == "reu"
                assert reu["nome"] == "Maria dos Santos"
                assert reu["cpf"] == "987.654.321-00"

                # 5. Validação do segundo processo
                processo2 = result[1]
                assert processo2["id"] == 12346
                assert processo2["numero_processo"] == "0000036-58.2019.8.16.0033"
                assert processo2["comarca"] == "Londrina"
                assert len(processo2["partes"]) == 1

                print("✅ PAYLOAD COMPLETO VALIDADO!")
                print(f"\n📦 Estrutura retornada:")
                print(f"  - Total de processos: {len(result)}")
                print(f"  - Processo 1: {processo1['comarca']} - {processo1['vara']}")
                print(f"  - Processo 2: {processo2['comarca']} - {processo2['vara']}")
                print(f"\n✅ Todos os campos obrigatórios presentes")
                print(f"✅ Estrutura de partes validada")
                print(f"✅ Dados do processo 0000036-58.2019.8.16.0033 corretos")

    @pytest.mark.asyncio
    async def test_payload_fields_detailed(self):
        """Testa campos detalhados do payload"""
        with patch("services.cpj_service.settings") as mock_settings:
            mock_settings.CPJ_BASE_URL = "https://test.api/v2"
            mock_settings.CPJ_LOGIN = "test"
            mock_settings.CPJ_PASSWORD = "test123"
            mock_settings.CPJ_TOKEN_EXPIRY_MINUTES = 30

            service = CPJService()

            auth_response = Mock()
            auth_response.json.return_value = {"token": "token123"}
            auth_response.raise_for_status = Mock()

            # Payload com TODOS os campos possíveis
            full_payload = [
                {
                    "id": 99999,
                    "numero_processo": "0000036-58.2019.8.16.0033",
                    "tribunal": "TJPR",
                    "comarca": "Curitiba",
                    "vara": "1ª Vara Cível",
                    "data_distribuicao": "2019-01-15",
                    "valor_causa": "R$ 50.000,00",
                    "classe": "Procedimento Comum Cível",
                    "assunto": "Dano Material",
                    "partes": [],
                    "advogados": [],
                    "ultima_movimentacao": "2024-10-24",
                    "data_criacao": "2019-01-15T10:30:00",
                    "data_atualizacao": "2024-10-24T22:25:53",
                    "status": "Em andamento",
                    "segredo_justica": False,
                    "priority": "normal",
                }
            ]

            search_response = Mock()
            search_response.json.return_value = full_payload
            search_response.raise_for_status = Mock()

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                result = await service.buscar_processo_por_numero(
                    "0000036-58.2019.8.16.0033"
                )

                # Validação de campos estendidos
                processo = result[0]

                campos_esperados = [
                    "id",
                    "numero_processo",
                    "tribunal",
                    "comarca",
                    "vara",
                    "data_distribuicao",
                    "valor_causa",
                    "classe",
                    "assunto",
                    "partes",
                    "advogados",
                    "ultima_movimentacao",
                    "status",
                ]

                for campo in campos_esperados:
                    assert campo in processo, f"Campo '{campo}' deve estar presente"

                print("\n📋 Campos validados:")
                for campo in campos_esperados:
                    valor = processo.get(campo)
                    tipo = type(valor).__name__
                    print(f"  ✅ {campo}: {tipo}")

    @pytest.mark.asyncio
    async def test_payload_request_sent(self):
        """Valida payload ENVIADO na requisição"""
        with patch("services.cpj_service.settings") as mock_settings:
            mock_settings.CPJ_BASE_URL = "https://test.api/v2"
            mock_settings.CPJ_LOGIN = "test_user"
            mock_settings.CPJ_PASSWORD = "test_pass"
            mock_settings.CPJ_TOKEN_EXPIRY_MINUTES = 30

            service = CPJService()

            auth_response = Mock()
            auth_response.json.return_value = {"token": "token123"}
            auth_response.raise_for_status = Mock()

            search_response = Mock()
            search_response.json.return_value = []
            search_response.raise_for_status = Mock()

            with patch("requests.post") as mock_post:
                mock_post.side_effect = [auth_response, search_response]

                await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

                # Verifica chamadas
                assert mock_post.call_count == 2

                # Primeira chamada: LOGIN
                login_call = mock_post.call_args_list[0]
                assert login_call[0][0] == "https://test.api/v2/login"
                assert login_call[1]["json"] == {
                    "login": "test_user",
                    "password": "test_pass",
                }

                # Segunda chamada: BUSCA
                search_call = mock_post.call_args_list[1]
                assert search_call[0][0] == "https://test.api/v2/processo"

                # Valida payload da busca
                search_payload = search_call[1]["json"]
                assert "filter" in search_payload
                assert "_and" in search_payload["filter"]
                assert search_payload["filter"]["_and"][0] == {
                    "numero_processo": {"_eq": "0000036-58.2019.8.16.0033"}
                }

                # Valida headers
                headers = search_call[1]["headers"]
                assert headers["Content-Type"] == "application/json"
                assert headers["Authorization"] == "Bearer token123"

                print("\n📤 Payload ENVIADO validado:")
                print(f"  ✅ URL: {search_call[0][0]}")
                print(f"  ✅ Filter: {search_payload['filter']}")
                print(f"  ✅ Authorization: Bearer token123")
