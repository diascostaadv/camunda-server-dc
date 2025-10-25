"""
Configurações e fixtures compartilhadas para testes
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient


# ============ FIXTURES DE CONFIGURAÇÃO ============

@pytest.fixture
def cpj_config():
    """Configurações mock do CPJ"""
    return {
        "base_url": "https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2",
        "login": "test_user",
        "password": "test_password",
        "token_expiry_minutes": 30,
    }


@pytest.fixture
def mock_settings(cpj_config):
    """Mock de Settings com configurações CPJ"""
    settings = Mock()
    settings.CPJ_BASE_URL = cpj_config["base_url"]
    settings.CPJ_LOGIN = cpj_config["login"]
    settings.CPJ_PASSWORD = cpj_config["password"]
    settings.CPJ_TOKEN_EXPIRY_MINUTES = cpj_config["token_expiry_minutes"]
    settings.MONGODB_DATABASE = "test_db"
    settings.MONGODB_CONNECTION_STRING = "mongodb://localhost:27017"
    settings.N8N_WEBHOOK_URL = "https://test.n8n.cloud/webhook/test"
    settings.N8N_TIMEOUT = 120
    return settings


# ============ FIXTURES DE RESPOSTAS HTTP ============

@pytest.fixture
def mock_cpj_auth_success():
    """Resposta mock de autenticação bem-sucedida no CPJ"""
    return {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token",
        "expires_in": 1800,
        "user": {
            "id": 1,
            "login": "test_user",
            "name": "Test User",
        },
    }


@pytest.fixture
def mock_cpj_auth_error():
    """Resposta mock de erro de autenticação no CPJ"""
    return {
        "error": "Invalid credentials",
        "status_code": 401,
    }


@pytest.fixture
def mock_cpj_processo_encontrado():
    """Resposta mock de processo encontrado no CPJ"""
    return [
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


@pytest.fixture
def mock_cpj_processo_nao_encontrado():
    """Resposta mock de processo não encontrado no CPJ"""
    return []


@pytest.fixture
def mock_cpj_processo_single():
    """Resposta mock de único processo encontrado"""
    return [
        {
            "id": 99999,
            "numero_processo": "1234567-89.2023.8.13.0024",
            "tribunal": "TJMG",
            "comarca": "Belo Horizonte",
            "vara": "5ª Vara da Fazenda Pública",
            "data_distribuicao": "2023-05-10",
            "valor_causa": "R$ 100.000,00",
            "ultima_movimentacao": "2024-10-24",
            "status": "Em andamento",
        }
    ]


# ============ FIXTURES DE REQUEST PAYLOADS ============

@pytest.fixture
def cpj_request_valid():
    """Request válido para verificar processo CNJ"""
    return {"numero_cnj": "0000036-58.2019.8.16.0033"}


@pytest.fixture
def cpj_request_with_variables():
    """Request com formato de worker (variables)"""
    return {
        "task_id": "task_123",
        "variables": {"numero_cnj": "0000036-58.2019.8.16.0033"},
    }


@pytest.fixture
def cpj_request_invalid_missing_numero():
    """Request inválido sem numero_cnj"""
    return {"foo": "bar"}


@pytest.fixture
def cpj_request_alternative_field():
    """Request com campo alternativo numero_processo"""
    return {"numero_processo": "0000036-58.2019.8.16.0033"}


# ============ FIXTURES DE TEMPO ============

@pytest.fixture
def mock_datetime_now():
    """Mock de datetime.now() para controle de tempo em testes"""
    return datetime(2024, 10, 24, 22, 25, 53)


@pytest.fixture
def mock_datetime_expired():
    """Mock de datetime para token expirado (1 hora atrás)"""
    return datetime(2024, 10, 24, 21, 25, 53)


@pytest.fixture
def mock_token_expiry(mock_datetime_now):
    """Data de expiração do token (30 minutos no futuro)"""
    return mock_datetime_now + timedelta(minutes=30)


# ============ FIXTURES DE TESTE CLIENT ============

@pytest.fixture
def test_client():
    """Cliente de teste FastAPI"""
    from main import app

    return TestClient(app)


@pytest.fixture
def mock_cpj_service():
    """Mock do CPJService"""
    service = MagicMock()
    service.is_authenticated.return_value = True
    service.get_token_info.return_value = {
        "has_token": True,
        "expires_at": "2024-10-24T22:55:53.869918",
        "is_valid": True,
    }
    return service


# ============ FIXTURES DE EXCEPTIONS ============

@pytest.fixture
def mock_timeout_error():
    """Mock de erro de timeout"""
    import requests

    return requests.exceptions.Timeout("Connection timed out after 30 seconds")


@pytest.fixture
def mock_connection_error():
    """Mock de erro de conexão"""
    import requests

    return requests.exceptions.ConnectionError("Failed to establish connection")


@pytest.fixture
def mock_http_error():
    """Mock de erro HTTP genérico"""
    import requests

    response = Mock()
    response.status_code = 500
    response.text = "Internal Server Error"
    return requests.exceptions.HTTPError(response=response)


# ============ HELPERS ============

def create_mock_response(status_code: int, json_data: Dict[str, Any] = None, text: str = ""):
    """
    Helper para criar mock de resposta HTTP

    Args:
        status_code: Código HTTP
        json_data: Dados JSON da resposta
        text: Texto da resposta

    Returns:
        Mock de requests.Response
    """
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text or str(json_data)
    response.raise_for_status = Mock()

    if status_code >= 400:
        import requests
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=response
        )

    return response


@pytest.fixture
def create_response():
    """Fixture factory para criar mock responses"""
    return create_mock_response
