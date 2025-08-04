# -*- coding: utf-8 -*-
"""
Dados de teste para os testes do projeto Camunda
"""

# Dados de exemplo para testes de processo
SAMPLE_PROCESS_VARIABLES = {
    "hello_world_basic": {
        "variables": {
            "name": {"value": "TestUser", "type": "String"}
        }
    },
    
    "hello_world_extended": {
        "variables": {
            "name": {"value": "ExtendedTestUser", "type": "String"},
            "language": {"value": "pt-BR", "type": "String"},
            "timestamp": {"value": "2025-01-24T10:00:00Z", "type": "String"}
        }
    },
    
    "document_workflow": {
        "variables": {
            "document_type": {"value": "pdf", "type": "String"},
            "document_content": {"value": "Test document content", "type": "String"},
            "author": {"value": "Test Author", "type": "String"},
            "title": {"value": "Test Document", "type": "String"}
        }
    }
}

# Casos de teste para validação
TEST_CASES = [
    {
        "name": "Pedro",
        "expected_greeting": "Hello, Pedro!"
    },
    {
        "name": "Maria",
        "expected_greeting": "Hello, Maria!"
    },
    {
        "name": "João",
        "expected_greeting": "Hello, João!"
    },
    {
        "name": "Ana",
        "expected_greeting": "Hello, Ana!"
    }
]

# Configurações de teste para diferentes ambientes
TEST_ENVIRONMENTS = {
    "local": {
        "camunda_url": "http://localhost:8080",
        "worker_port": 8001,
        "timeout": 30
    },
    
    "docker": {
        "camunda_url": "http://camunda:8080",
        "worker_port": 8001,
        "timeout": 45
    },
    
    "embedded": {
        "camunda_url": "http://localhost:8080",
        "worker_port": 8000,
        "timeout": 30
    }
}

# Dados para testes de erro
ERROR_TEST_CASES = {
    "invalid_document_type": {
        "variables": {
            "document_type": {"value": "invalid", "type": "String"},
            "document_content": {"value": "Test content", "type": "String"},
            "author": {"value": "Test Author", "type": "String"}
        }
    },
    
    "missing_required_field": {
        "variables": {
            "document_type": {"value": "pdf", "type": "String"},
            "document_content": {"value": "Test content", "type": "String"}
            # Missing 'author' field
        }
    }
}

# Tópicos de external tasks
EXTERNAL_TASK_TOPICS = [
    "say_hello",
    "validate_document", 
    "process_data",
    "publish_content",
    "send_notification",
    "handle_validation_error"
]

# Métricas esperadas dos workers
EXPECTED_WORKER_METRICS = [
    "camunda_external_task_fetch_total",
    "camunda_external_task_complete_total", 
    "camunda_external_task_failure_total",
    "process_time_seconds"
]
