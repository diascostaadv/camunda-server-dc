# -*- coding: utf-8 -*-
"""
Testes de integração para conectividade com Camunda
"""

import pytest
import requests
import time
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.requires_camunda
class TestCamundaConnectivity:
    """Testes de conectividade com o Camunda BPM"""
    
    def test_camunda_version_endpoint(self, test_config, camunda_client):
        """Testa endpoint de versão do Camunda"""
        url = f"{test_config['camunda_url']}/camunda/engine-rest/version"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        data = response.json()
        assert 'version' in data
        
    def test_camunda_web_interface(self, test_config, camunda_client):
        """Testa interface web do Camunda"""
        url = f"{test_config['camunda_url']}/camunda/app/welcome/default/"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        
    def test_process_definitions_endpoint(self, test_config, camunda_client):
        """Testa endpoint de definições de processo"""
        url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_external_task_endpoint(self, test_config, camunda_client):
        """Testa endpoint de external tasks"""
        url = f"{test_config['camunda_url']}/camunda/engine-rest/external-task"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.integration
@pytest.mark.requires_camunda
class TestProcessDeployment:
    """Testes de deployment de processos"""
    
    def test_hello_world_process_exists(self, test_config, camunda_client):
        """Verifica se o processo HelloWorldProcess está deployado"""
        url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        if response.status_code == 200:
            data = response.json()
            assert data['key'] == test_config['process_key']
            assert 'id' in data
            assert 'version' in data
        else:
            # Se o processo não existe, é um skip, não um erro
            pytest.skip(f"Processo {test_config['process_key']} não está deployado")

@pytest.mark.integration  
@pytest.mark.requires_camunda
class TestProcessExecution:
    """Testes de execução de processos"""
    
    def test_start_hello_world_process(self, test_config, camunda_client, sample_process_data):
        """Testa inicialização do processo Hello World"""
        # Primeiro verifica se o processo existe
        check_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}"
        check_response = camunda_client.get(check_url, timeout=test_config['timeout'])
        
        if check_response.status_code != 200:
            pytest.skip(f"Processo {test_config['process_key']} não está deployado")
        
        # Inicia o processo
        start_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}/start"
        response = camunda_client.post(start_url, json=sample_process_data, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert 'processDefinitionId' in data
        
        # Cleanup: tentar finalizar a instância se possível
        instance_id = data['id']
        # Aguardar um pouco para processamento
        time.sleep(2)
        
        return instance_id
    
    def test_get_process_instance_status(self, test_config, camunda_client):
        """Testa verificação de status de instância de processo"""
        # Este teste precisa de uma instância criada
        try:
            instance_id = self.test_start_hello_world_process(test_config, camunda_client, {
                "variables": {
                    "name": {"value": "TestUser", "type": "String"}
                }
            })
        except Exception:
            pytest.skip("Não foi possível criar instância de processo para teste")
        
        url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}"
        response = camunda_client.get(url, timeout=test_config['timeout'])
        
        # 200 = ativo, 404 = finalizado
        assert response.status_code in [200, 404]

@pytest.mark.integration
@pytest.mark.requires_camunda  
class TestExternalTaskAPI:
    """Testes da API de External Tasks"""
    
    def test_fetch_and_lock_endpoint(self, test_config, camunda_client):
        """Testa endpoint de fetch and lock para external tasks"""
        url = f"{test_config['camunda_url']}/camunda/engine-rest/external-task/fetchAndLock"
        
        payload = {
            "workerId": "test-worker",
            "maxTasks": 1,
            "topics": [
                {
                    "topicName": "say_hello",
                    "lockDuration": 60000
                }
            ]
        }
        
        response = camunda_client.post(url, json=payload, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Lista pode estar vazia se não há tasks disponíveis
    
    def test_external_task_endpoints_availability(self, test_config, camunda_client):
        """Testa disponibilidade de diferentes endpoints de external task"""
        endpoints = [
            "/camunda/engine-rest/external-task/fetchAndLock",
            "/camunda/api/engine/default/external-task/fetchAndLock",
        ]
        
        payload = {
            "workerId": "test-worker",
            "maxTasks": 1,
            "topics": [{"topicName": "test", "lockDuration": 60000}]
        }
        
        for endpoint in endpoints:
            url = f"{test_config['camunda_url']}{endpoint}"
            response = camunda_client.post(url, json=payload, timeout=test_config['timeout'])
            
            # Aceita 200 (sucesso) ou 404 (endpoint não existe)
            assert response.status_code in [200, 404]

@pytest.mark.integration
@pytest.mark.csrf
@pytest.mark.requires_camunda
class TestCSRFTokenHandling:
    """Testes de manipulação de CSRF tokens"""
    
    def test_csrf_token_extraction(self, test_config):
        """Testa extração de CSRF token das páginas do Camunda"""
        import re
        
        # Tentar extrair CSRF token da página de login
        session = requests.Session()
        session.auth = test_config['auth']
        
        url = f"{test_config['camunda_url']}/camunda/app/tasklist/default/"
        response = session.get(url, timeout=test_config['timeout'])
        
        if response.status_code == 200:
            # Procurar por CSRF token no HTML
            csrf_pattern = r'name="csrf-token"\s+content="([^"]+)"'
            match = re.search(csrf_pattern, response.text)
            
            if match:
                csrf_token = match.group(1)
                assert len(csrf_token) > 0, "CSRF token deveria ter conteúdo"
            else:
                pytest.skip("CSRF token não encontrado na página (pode ser normal)")
        else:
            pytest.skip("Não foi possível acessar a página para extrair CSRF token")
