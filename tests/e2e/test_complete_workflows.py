# -*- coding: utf-8 -*-
"""
Testes end-to-end para workflows completos do Camunda
"""

import pytest
import requests
import time
from typing import Dict, Any, Optional


@pytest.mark.e2e
@pytest.mark.requires_camunda
@pytest.mark.requires_worker
@pytest.mark.slow
class TestHelloWorldWorkflow:
    """Testes end-to-end do workflow Hello World"""
    
    def test_complete_hello_world_workflow(self, test_config, camunda_client):
        """Testa workflow completo do Hello World"""
        # 1. Verificar se o processo está deployado
        process_check_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}"
        process_response = camunda_client.get(process_check_url, timeout=test_config['timeout'])
        
        if process_response.status_code != 200:
            pytest.skip(f"Processo {test_config['process_key']} não está deployado")
        
        # 2. Iniciar instância do processo
        start_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}/start"
        
        test_name = "E2ETestUser"
        process_data = {
            "variables": {
                "name": {"value": test_name, "type": "String"}
            }
        }
        
        start_response = camunda_client.post(start_url, json=process_data, timeout=test_config['timeout'])
        assert start_response.status_code == 200
        
        instance_data = start_response.json()
        instance_id = instance_data['id']
        
        # 3. Aguardar processamento pelo worker
        max_wait_time = 30  # 30 segundos máximo
        wait_interval = 2   # Verificar a cada 2 segundos
        waited = 0
        
        workflow_completed = False
        final_variables = None
        
        while waited < max_wait_time:
            time.sleep(wait_interval)
            waited += wait_interval
            
            # Verificar status da instância
            instance_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}"
            instance_response = camunda_client.get(instance_url, timeout=test_config['timeout'])
            
            if instance_response.status_code == 404:
                # Instância completada
                workflow_completed = True
                
                # Buscar variáveis do histórico  
                history_url = f"{test_config['camunda_url']}/camunda/engine-rest/history/variable-instance"
                history_params = {"processInstanceId": instance_id}
                history_response = camunda_client.get(history_url, params=history_params, timeout=test_config['timeout'])
                
                if history_response.status_code == 200:
                    history_vars = history_response.json()
                    final_variables = {var['name']: var['value'] for var in history_vars}
                
                break
            elif instance_response.status_code == 200:
                # Ainda ativa, verificar variáveis atuais
                vars_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}/variables"
                vars_response = camunda_client.get(vars_url, timeout=test_config['timeout'])
                
                if vars_response.status_code == 200:
                    current_vars = vars_response.json()
                    if 'greeting' in current_vars:
                        # Worker já processou, mas processo ainda não finalizou
                        final_variables = {name: var['value'] for name, var in current_vars.items()}
        
        # 4. Verificar resultados
        if not workflow_completed and final_variables is None:
            pytest.fail(f"Workflow não completou em {max_wait_time}s ou worker não está processando")
        
        # Verificar se o greeting foi gerado corretamente
        assert final_variables is not None, "Nenhuma variável foi encontrada"
        assert 'greeting' in final_variables, "Variável 'greeting' não foi criada pelo worker"
        
        expected_greeting = f"Hello, {test_name}!"
        actual_greeting = final_variables['greeting']
        assert actual_greeting == expected_greeting, f"Greeting incorreto: esperado '{expected_greeting}', recebido '{actual_greeting}'"
        
        print(f"✅ Workflow completado com sucesso! Greeting: '{actual_greeting}'")
    
    def test_multiple_concurrent_workflows(self, test_config, camunda_client):
        """Testa múltiplos workflows concorrentes"""
        # Verificar se o processo está deployado
        process_check_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}"
        process_response = camunda_client.get(process_check_url, timeout=test_config['timeout'])
        
        if process_response.status_code != 200:
            pytest.skip(f"Processo {test_config['process_key']} não está deployado")
        
        # Iniciar múltiplas instâncias
        test_cases = ["User1", "User2", "User3"]
        instance_ids = []
        
        start_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition/key/{test_config['process_key']}/start"
        
        for name in test_cases:
            process_data = {
                "variables": {
                    "name": {"value": name, "type": "String"}
                }
            }
            
            response = camunda_client.post(start_url, json=process_data, timeout=test_config['timeout'])
            assert response.status_code == 200
            
            instance_data = response.json()
            instance_ids.append((instance_data['id'], name))
        
        # Aguardar processamento de todas as instâncias
        max_wait_time = 45  # Mais tempo para múltiplas instâncias
        wait_interval = 3
        waited = 0
        
        completed_workflows = {}
        
        while waited < max_wait_time and len(completed_workflows) < len(test_cases):
            time.sleep(wait_interval)
            waited += wait_interval
            
            for instance_id, expected_name in instance_ids:
                if instance_id in completed_workflows:
                    continue  # Já processada
                
                # Verificar status
                instance_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}"
                instance_response = camunda_client.get(instance_url, timeout=test_config['timeout'])
                
                if instance_response.status_code == 404:
                    # Completada, buscar no histórico
                    history_url = f"{test_config['camunda_url']}/camunda/engine-rest/history/variable-instance"
                    history_params = {"processInstanceId": instance_id}
                    history_response = camunda_client.get(history_url, params=history_params, timeout=test_config['timeout'])
                    
                    if history_response.status_code == 200:
                        history_vars = history_response.json()
                        variables = {var['name']: var['value'] for var in history_vars}
                        completed_workflows[instance_id] = (expected_name, variables)
                        
                elif instance_response.status_code == 200:
                    # Ainda ativa, verificar se tem greeting
                    vars_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-instance/{instance_id}/variables"
                    vars_response = camunda_client.get(vars_url, timeout=test_config['timeout'])
                    
                    if vars_response.status_code == 200:
                        current_vars = vars_response.json()
                        if 'greeting' in current_vars:
                            variables = {name: var['value'] for name, var in current_vars.items()}
                            completed_workflows[instance_id] = (expected_name, variables)
        
        # Verificar resultados
        assert len(completed_workflows) == len(test_cases), f"Apenas {len(completed_workflows)}/{len(test_cases)} workflows completaram"
        
        for instance_id, (expected_name, variables) in completed_workflows.items():
            assert 'greeting' in variables, f"Greeting não encontrado para {expected_name}"
            
            expected_greeting = f"Hello, {expected_name}!"
            actual_greeting = variables['greeting']
            assert actual_greeting == expected_greeting, f"Greeting incorreto para {expected_name}"
        
        print(f"✅ {len(completed_workflows)} workflows concorrentes completados com sucesso!")

@pytest.mark.e2e
@pytest.mark.smoke  
@pytest.mark.requires_camunda
class TestSystemHealth:
    """Testes de saúde do sistema completo"""
    
    def test_all_components_healthy(self, test_config):
        """Verifica se todos os componentes estão saudáveis"""
        results = {}
        
        # 1. Camunda Engine
        try:
            camunda_url = f"{test_config['camunda_url']}/camunda/engine-rest/version"
            response = requests.get(camunda_url, auth=test_config['auth'], timeout=10)
            results['camunda_engine'] = response.status_code == 200
        except:
            results['camunda_engine'] = False
        
        # 2. Camunda Web Interface
        try:
            web_url = f"{test_config['camunda_url']}/camunda/app/welcome/default/"
            response = requests.get(web_url, auth=test_config['auth'], timeout=10)
            results['camunda_web'] = response.status_code == 200
        except:
            results['camunda_web'] = False
        
        # 3. Worker Health
        try:
            worker_url = f"http://localhost:{test_config['worker_port']}/health"
            response = requests.get(worker_url, timeout=5)
            results['worker_health'] = response.status_code == 200
        except:
            results['worker_health'] = False
        
        # Relatório
        print("\n🏥 HEALTH CHECK REPORT:")
        print("=" * 30)
        for component, healthy in results.items():
            status = "✅ OK" if healthy else "❌ FAIL"
            print(f"  {component:20}: {status}")
        
        # O teste passa se pelo menos Camunda está funcionando
        assert results['camunda_engine'], "Camunda Engine deve estar funcionando"
        
        # Warnings para componentes opcionais
        if not results['camunda_web']:
            print("⚠️  Camunda Web Interface não está disponível")
        
        if not results['worker_health']:
            print("⚠️  Worker não está disponível - testes de integração serão pulados")

@pytest.mark.e2e
@pytest.mark.process
@pytest.mark.requires_camunda
class TestProcessLifecycle:
    """Testes do ciclo de vida completo de processos"""
    
    def test_process_definition_lifecycle(self, test_config, camunda_client):
        """Testa ciclo de vida da definição de processo"""
        # 1. Listar definições disponíveis
        definitions_url = f"{test_config['camunda_url']}/camunda/engine-rest/process-definition"
        response = camunda_client.get(definitions_url, timeout=test_config['timeout'])
        
        assert response.status_code == 200
        definitions = response.json()
        assert isinstance(definitions, list)
        
        # 2. Verificar se o processo de teste está presente
        hello_world_found = False
        for definition in definitions:
            if definition.get('key') == test_config['process_key']:
                hello_world_found = True
                assert 'id' in definition
                assert 'version' in definition
                assert 'name' in definition
                break
        
        if not hello_world_found:
            pytest.skip(f"Processo {test_config['process_key']} não foi encontrado")
        
        print(f"✅ Processo {test_config['process_key']} encontrado e validado!")
