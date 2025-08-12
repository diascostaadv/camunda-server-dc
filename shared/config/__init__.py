"""
Shared configuration module for Camunda BPM Ecosystem
Provides unified configuration management using Pydantic
"""

from .base import BaseConfig, Environment
from .mongodb import MongoDBConfig
from .rabbitmq import RabbitMQConfig
from .camunda import CamundaConfig
from .environment import GatewayConfig, WorkerPlatformConfig, UnifiedConfig

# Version
__version__ = "1.0.0"

# Default configuration instance
_config_instance = None


def get_config(environment: str = None, reload: bool = False) -> UnifiedConfig:
    """
    Get the unified configuration instance
    
    Args:
        environment: Optional environment to load (local, atlas, production)
        reload: Force reload configuration
        
    Returns:
        UnifiedConfig instance
    """
    global _config_instance
    
    if _config_instance is None or reload:
        _config_instance = UnifiedConfig.load_for_environment(environment)
    
    return _config_instance


def get_mongodb_config() -> MongoDBConfig:
    """Get MongoDB configuration"""
    config = get_config()
    return MongoDBConfig(**config.dict())


def get_rabbitmq_config() -> RabbitMQConfig:
    """Get RabbitMQ configuration"""
    config = get_config()
    return RabbitMQConfig(**config.dict())


def get_camunda_config() -> CamundaConfig:
    """Get Camunda configuration"""
    config = get_config()
    return CamundaConfig(**config.dict())


def get_gateway_config() -> GatewayConfig:
    """Get Gateway configuration"""
    config = get_config()
    return GatewayConfig(**config.dict())


def get_worker_config() -> WorkerPlatformConfig:
    """Get Worker Platform configuration"""
    config = get_config()
    return WorkerPlatformConfig(**config.dict())


# Export main classes and functions
__all__ = [
    # Base classes
    "BaseConfig",
    "Environment",
    
    # Component configurations
    "MongoDBConfig",
    "RabbitMQConfig",
    "CamundaConfig",
    "GatewayConfig",
    "WorkerPlatformConfig",
    
    # Unified configuration
    "UnifiedConfig",
    
    # Helper functions
    "get_config",
    "get_mongodb_config",
    "get_rabbitmq_config",
    "get_camunda_config",
    "get_gateway_config",
    "get_worker_config"
]


# Topics centralized definition
class Topics:
    """Centralized topic names for external tasks"""
    
    # Simple topics
    SAY_HELLO = "say_hello"
    
    # Publication topics
    NOVA_PUBLICACAO = "nova_publicacao"
    BUSCAR_PUBLICACOES = "buscar_publicacoes"
    BUSCAR_LOTE_POR_ID = "buscar_lote_por_id"
    TRATAR_PUBLICACAO = "tratar_publicacao"
    CLASSIFICAR_PUBLICACAO = "classificar_publicacao"
    
    # Workflow topics
    VALIDATE_DOCUMENT = "validate_document"
    PROCESS_DATA = "process_data"
    PUBLISH_CONTENT = "publish_content"
    SEND_NOTIFICATION = "send_notification"
    HANDLE_VALIDATION_ERROR = "handle_validation_error"
    
    @classmethod
    def get_all_topics(cls) -> list:
        """Get all available topics"""
        return [
            value for key, value in cls.__dict__.items()
            if not key.startswith("_") and isinstance(value, str)
        ]
    
    @classmethod
    def get_publication_topics(cls) -> list:
        """Get publication-related topics"""
        return [
            cls.NOVA_PUBLICACAO,
            cls.BUSCAR_PUBLICACOES,
            cls.BUSCAR_LOTE_POR_ID,
            cls.TRATAR_PUBLICACAO,
            cls.CLASSIFICAR_PUBLICACAO
        ]


# Validation rules centralized
VALIDATION_RULES = {
    'document_types': ['pdf', 'docx', 'txt', 'xml', 'json'],
    'max_file_size': 10485760,  # 10MB
    'required_fields': ['title', 'content', 'author'],
    'date_formats': ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'],
    'process_number_pattern': r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
}


# Status definitions
TASK_STATUSES = {
    "pending": "Task is pending",
    "em_andamento": "Task is being processed",
    "aguardando": "Task is waiting for external dependency",
    "sucesso": "Task completed successfully",
    "erro": "Task failed with error",
    "cancelado": "Task was cancelled"
}


# Error codes
ERROR_CODES = {
    "CONFIG_ERROR": 1001,
    "CONNECTION_ERROR": 1002,
    "VALIDATION_ERROR": 1003,
    "TASK_ERROR": 2001,
    "WORKER_ERROR": 2002,
    "GATEWAY_ERROR": 2003,
    "DATABASE_ERROR": 3001,
    "QUEUE_ERROR": 3002,
    "EXTERNAL_API_ERROR": 4001
}