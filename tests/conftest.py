# -*- coding: utf-8 -*-
"""
Configuração global para os testes do projeto Camunda
"""

import os
import sys
import pytest
from typing import Dict, Any
from pathlib import Path

# Adicionar o diretório do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "camunda-swarm"))
sys.path.insert(0, str(project_root / "camunda-swarm" / "workers"))

# Configurações globais para testes
CAMUNDA_TEST_URL = os.getenv('CAMUNDA_TEST_URL', 'http://localhost:8080')
WORKER_TEST_PORT = int(os.getenv('WORKER_TEST_PORT', '8001'))
TEST_TIMEOUT = int(os.getenv('TEST_TIMEOUT', '30'))
TEST_PROCESS_KEY = os.getenv('TEST_PROCESS_KEY', 'HelloWorldProcess')

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Configuração global para todos os testes"""
    return {
        'camunda_url': CAMUNDA_TEST_URL,
        'worker_port': WORKER_TEST_PORT,
        'timeout': TEST_TIMEOUT,
        'process_key': TEST_PROCESS_KEY,
        'auth': ('demo', 'demo'),
        'test_data_dir': project_root / "tests" / "data",
        'reports_dir': project_root / "reports"
    }

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(test_config):
    """Setup inicial do ambiente de testes"""
    # Criar diretórios necessários
    test_config['test_data_dir'].mkdir(exist_ok=True)
    test_config['reports_dir'].mkdir(exist_ok=True)
    
    # Verificar se o Camunda está disponível (apenas aviso)
    import requests
    try:
        response = requests.get(f"{test_config['camunda_url']}/camunda/engine-rest/version", 
                              auth=test_config['auth'], timeout=5)
        if response.status_code == 200:
            print(f"✅ Camunda disponível em {test_config['camunda_url']}")
        else:
            print(f"⚠️  Camunda respondeu com status {response.status_code}")
    except Exception as e:
        print(f"⚠️  Camunda não está disponível: {e}")
        print("   Os testes de integração serão pulados automaticamente")

@pytest.fixture
def camunda_client(test_config):
    """Cliente HTTP para interagir com Camunda"""
    import requests
    
    session = requests.Session()
    session.auth = test_config['auth']
    session.headers.update({'Content-Type': 'application/json'})
    
    return session

@pytest.fixture
def sample_process_data():
    """Dados de exemplo para testes de processo"""
    return {
        "variables": {
            "name": {"value": "TestUser", "type": "String"},
            "document_type": {"value": "test", "type": "String"},
            "document_content": {"value": "Test content", "type": "String"}
        }
    }

@pytest.fixture
def worker_health_check(test_config):
    """Verifica se o worker está saudável"""
    import requests
    
    def _check_worker(port: int = None) -> bool:
        check_port = port or test_config['worker_port']
        try:
            response = requests.get(f"http://localhost:{check_port}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    return _check_worker

# Skip markers para testes que requerem serviços externos
def pytest_configure(config):
    """Configuração adicional do pytest"""
    config.addinivalue_line(
        "markers", "requires_camunda: mark test as requiring Camunda to be running"
    )
    config.addinivalue_line(
        "markers", "requires_worker: mark test as requiring worker to be running"
    )

def pytest_runtest_setup(item):
    """Hook executado antes de cada teste"""
    # Skip testes que requerem Camunda se não estiver disponível
    if item.get_closest_marker("requires_camunda"):
        import requests
        try:
            response = requests.get(f"{CAMUNDA_TEST_URL}/camunda/engine-rest/version", 
                                  auth=('demo', 'demo'), timeout=5)
            if response.status_code != 200:
                pytest.skip("Camunda não está disponível")
        except:
            pytest.skip("Camunda não está disponível")
    
    # Skip testes que requerem worker se não estiver disponível
    if item.get_closest_marker("requires_worker"):
        import requests
        try:
            response = requests.get(f"http://localhost:{WORKER_TEST_PORT}/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("Worker não está disponível")
        except:
            pytest.skip("Worker não está disponível")
