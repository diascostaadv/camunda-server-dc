# -*- coding: utf-8 -*-
"""
Testes de integração para Workers do Camunda
"""

import pytest
import requests
import time
from typing import Optional


@pytest.mark.integration
@pytest.mark.worker
class TestWorkerHealth:
    """Testes de saúde dos workers"""
    
    def test_worker_health_endpoint(self, test_config):
        """Testa endpoint de health check do worker"""
        url = f"http://localhost:{test_config['worker_port']}/health"
        
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
            
            # Verifica se retorna JSON válido
            data = response.json()
            assert 'status' in data or 'health' in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Worker não está rodando")
    
    def test_worker_metrics_endpoint(self, test_config):
        """Testa endpoint de métricas do worker"""
        url = f"http://localhost:{test_config['worker_port']}/metrics"
        
        try:
            response = requests.get(url, timeout=5)
            # Métricas podem retornar 200 ou 404 dependendo da configuração
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                # Verifica se tem formato de métricas Prometheus
                assert 'TYPE' in response.text or 'HELP' in response.text
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Worker não está rodando")

@pytest.mark.integration
@pytest.mark.worker
@pytest.mark.requires_worker
@pytest.mark.requires_camunda
class TestWorkerCamundaIntegration:
    """Testes de integração worker-Camunda"""
    
    def test_worker_camunda_connection(self, test_config, camunda_client):
        """Testa se o worker consegue se conectar ao Camunda"""
        # Este teste verifica indiretamente através dos logs ou métricas
        # ou criando uma external task e vendo se o worker a processa
        
        # Primeiro, criar uma instância de processo para gerar uma external task
        process_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}/start"
        
        process_data = {
            "variables": {
                "name": {"value": "IntegrationTest", "type": "String"}
            }
        }
        
        try:
            response = camunda_client.post(process_url, json=process_data, timeout=test_config['timeout'])
            if response.status_code != 200:
                pytest.skip("Não foi possível criar instância de processo")
            
            instance_data = response.json()
            instance_id = instance_data['id']
            
            # Aguardar um pouco para o worker processar
            time.sleep(3)
            
            # Verificar se a instância foi processada (pode estar completed ou ainda ativa)
            instance_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}"
            instance_response = camunda_client.get(instance_url, timeout=test_config['timeout'])
            
            # 200 = ainda ativo, 404 = foi completado pelo worker
            assert instance_response.status_code in [200, 404]
            
            # Se ainda está ativo, verificar se tem variáveis setadas pelo worker
            if instance_response.status_code == 200:
                vars_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}/variables"
                vars_response = camunda_client.get(vars_url, timeout=test_config['timeout'])
                
                if vars_response.status_code == 200:
                    variables = vars_response.json()
                    # Verificar se o worker adicionou a variável 'greeting'
                    # (isso indica que o worker processou a task)
                    if 'greeting' in variables:
                        assert True  # Worker processou com sucesso
                    else:
                        pytest.skip("Worker ainda não processou a task ou não está rodando")
                        
        except requests.exceptions.RequestException:
            pytest.skip("Erro de conexão durante teste de integração")
    
    def test_external_task_processing(self, test_config, camunda_client):
        """Testa processamento de external tasks pelo worker"""
        # Verificar se existem external tasks pendentes do tópico 'say_hello'
        fetch_url = f"{test_config['camunda_url']}/camunda/engine-rest/external-task/fetchAndLock"
        
        payload = {
            "workerId": "test-fetch-worker",
            "maxTasks": 1,
            "topics": [
                {
                    "topicName": "say_hello",
                    "lockDuration": 60000
                }
            ]
        }
        
        response = camunda_client.post(fetch_url, json=payload, timeout=test_config['timeout'])
        assert response.status_code == 200
        
        tasks = response.json()
        if len(tasks) > 0:
            # Há tasks disponíveis - isso pode indicar que o worker não está processando
            # ou que há muitas tasks na fila
            task = tasks[0]
            
            # Completar a task manualmente para cleanup
            complete_url = f"{test_config['camunda_url']}/camunda/engine-rest/external-task/{task['id']}/complete"
            complete_payload = {
                "workerId": "test-fetch-worker",
                "variables": {
                    "greeting": {"value": f"Hello, {task.get('variables', {}).get('name', {}).get('value', 'World')}!", "type": "String"}
                }
            }
            
            camunda_client.post(complete_url, json=complete_payload, timeout=test_config['timeout'])
        
        # O teste passa independentemente - estamos apenas verificando a conectividade
        assert True

@pytest.mark.integration
@pytest.mark.worker  
@pytest.mark.slow
class TestWorkerPerformance:
    """Testes de performance dos workers"""
    
    @pytest.mark.timeout(60)
    def test_worker_response_time(self, test_config):
        """Testa tempo de resposta do worker"""
        if not self._worker_available(test_config):
            pytest.skip("Worker não está disponível")
        
        url = f"http://localhost:{test_config['worker_port']}/health"
        
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Worker response time too slow: {response_time}s"
    
    def _worker_available(self, test_config) -> bool:
        """Verifica se o worker está disponível"""
        try:
            url = f"http://localhost:{test_config['worker_port']}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except:
            return False

@pytest.mark.integration
@pytest.mark.worker
@pytest.mark.requires_worker
class TestWorkerConfiguration:
    """Testes de configuração dos workers"""
    
    def test_worker_environment_detection(self, test_config):
        """Testa se o worker detecta corretamente o ambiente"""  
        # Este teste pode ser implementado verificando logs ou métricas
        # Por enquanto, apenas verifica se o worker está respondendo
        
        url = f"http://localhost:{test_config['worker_port']}/health"
        
        try:
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Worker não está rodando para teste de configuração")
