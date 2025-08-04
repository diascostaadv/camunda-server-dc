# -*- coding: utf-8 -*-
"""
Testes unitários para configuração dos workers
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Adicionar caminho para importar os módulos
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "camunda-swarm" / "workers"))

@pytest.mark.unit
class TestWorkerConfig:
    """Testes para a classe WorkerConfig"""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_default_configuration(self):
        """Testa configuração padrão quando não há variáveis de ambiente"""
        # Import após limpar o ambiente
        from common.config import WorkerConfig
        
        assert WorkerConfig.ENVIRONMENT == 'local'
        assert WorkerConfig.WORKERS_MODE == 'separated'
        assert WorkerConfig.MAX_TASKS == 1
        assert WorkerConfig.CAMUNDA_USERNAME == 'demo'
        assert WorkerConfig.CAMUNDA_PASSWORD == 'demo'
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'WORKERS_MODE': 'embedded',
        'MAX_TASKS': '5',
        'CAMUNDA_USERNAME': 'admin',
        'CAMUNDA_PASSWORD': 'secret'
    })
    def test_environment_configuration(self):
        """Testa configuração através de variáveis de ambiente"""
        # Reload do módulo para pegar novas env vars
        import importlib
        import common.config
        importlib.reload(common.config)
        
        from common.config import WorkerConfig
        
        assert WorkerConfig.ENVIRONMENT == 'production'
        assert WorkerConfig.WORKERS_MODE == 'embedded'
        assert WorkerConfig.MAX_TASKS == 5
        assert WorkerConfig.CAMUNDA_USERNAME == 'admin'
        assert WorkerConfig.CAMUNDA_PASSWORD == 'secret'
    
    def test_get_camunda_config(self):
        """Testa geração da configuração do Camunda"""
        from common.config import WorkerConfig
        
        config = WorkerConfig.get_camunda_config()
        
        required_keys = ['maxTasks', 'lockDuration', 'asyncResponseTimeout', 
                        'retries', 'retryTimeout', 'sleepSeconds']
        
        for key in required_keys:
            assert key in config
            assert isinstance(config[key], int)
    
    def test_get_auth_with_credentials(self):
        """Testa autenticação quando credenciais estão configuradas"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'CAMUNDA_USERNAME', 'user'):
            with patch.object(WorkerConfig, 'CAMUNDA_PASSWORD', 'pass'):
                auth = WorkerConfig.get_auth()
                assert auth == ('user', 'pass')
    
    def test_get_auth_without_credentials(self):
        """Testa autenticação quando credenciais não estão configuradas"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'CAMUNDA_USERNAME', None):
            with patch.object(WorkerConfig, 'CAMUNDA_PASSWORD', None):
                auth = WorkerConfig.get_auth()
                assert auth is None
    
    def test_is_production(self):
        """Testa verificação de ambiente de produção"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'ENVIRONMENT', 'production'):
            assert WorkerConfig.is_production() is True
        
        with patch.object(WorkerConfig, 'ENVIRONMENT', 'local'):
            assert WorkerConfig.is_production() is False
    
    def test_is_separated_mode(self):
        """Testa verificação do modo separado"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'WORKERS_MODE', 'separated'):
            assert WorkerConfig.is_separated_mode() is True
        
        with patch.object(WorkerConfig, 'WORKERS_MODE', 'embedded'):
            assert WorkerConfig.is_separated_mode() is False
    
    def test_validate_config_success(self):
        """Testa validação de configuração com sucesso"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'CAMUNDA_URL', 'http://localhost:8080'):
            assert WorkerConfig.validate_config() is True
    
    def test_validate_config_failure(self):
        """Testa validação de configuração com falha"""
        from common.config import WorkerConfig
        
        with patch.object(WorkerConfig, 'CAMUNDA_URL', None):
            with pytest.raises(ValueError, match="Missing required configuration"):
                WorkerConfig.validate_config()

@pytest.mark.unit
class TestTopics:
    """Testes para a classe Topics"""
    
    def test_topic_constants(self):
        """Testa se todos os tópicos estão definidos"""
        from common.config import Topics
        
        assert hasattr(Topics, 'SAY_HELLO')
        assert Topics.SAY_HELLO == 'say_hello'
        
        # Tópicos do workflow complexo (arquivados)
        assert hasattr(Topics, 'VALIDATE_DOCUMENT')
        assert hasattr(Topics, 'PROCESS_DATA')
        assert hasattr(Topics, 'PUBLISH_CONTENT')
        assert hasattr(Topics, 'SEND_NOTIFICATION')

@pytest.mark.unit  
class TestValidationRules:
    """Testes para as regras de validação"""
    
    def test_validation_rules_structure(self):
        """Testa estrutura das regras de validação"""
        from common.config import VALIDATION_RULES
        
        assert 'document_types' in VALIDATION_RULES
        assert 'max_file_size' in VALIDATION_RULES
        assert 'required_fields' in VALIDATION_RULES
        
        assert isinstance(VALIDATION_RULES['document_types'], list)
        assert isinstance(VALIDATION_RULES['max_file_size'], int)
        assert isinstance(VALIDATION_RULES['required_fields'], list)
