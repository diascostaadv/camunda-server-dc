"""
Configuration module for Camunda workers
Centralizes all configuration and environment variables
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file based on ENVIRONMENT
environment = os.getenv('ENVIRONMENT', 'local')
env_file = f'.env.{environment}'

# Try to load environment-specific file, fallback to .env
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()  # fallback to .env or system environment


class WorkerConfig:
    """Configuration class for Camunda workers"""
    
    # Environment Configuration
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'local')
    WORKERS_MODE: str = os.getenv('WORKERS_MODE', 'separated')
    
    # Camunda Engine Configuration  
    # For external workers connecting to standalone Camunda instance
    CAMUNDA_URL: str = os.getenv('CAMUNDA_URL', 'http://localhost:8080/engine-rest')
    CAMUNDA_USERNAME: Optional[str] = os.getenv('CAMUNDA_USERNAME', 'demo')
    CAMUNDA_PASSWORD: Optional[str] = os.getenv('CAMUNDA_PASSWORD', 'demo')
    
    # Worker Configuration
    MAX_TASKS: int = int(os.getenv('MAX_TASKS', '1'))
    LOCK_DURATION: int = int(os.getenv('LOCK_DURATION', '60000'))  # ms
    ASYNC_RESPONSE_TIMEOUT: int = int(os.getenv('ASYNC_RESPONSE_TIMEOUT', '30000'))  # ms
    RETRIES: int = int(os.getenv('RETRIES', '3'))
    RETRY_TIMEOUT: int = int(os.getenv('RETRY_TIMEOUT', '5000'))  # ms
    SLEEP_SECONDS: int = int(os.getenv('SLEEP_SECONDS', '30'))
    
    # Metrics Configuration
    METRICS_PORT: int = int(os.getenv('METRICS_PORT', '8000'))
    METRICS_ENABLED: bool = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH: str = os.getenv('LOG_FILE_PATH', '/var/log')
    
    # External APIs Configuration
    NOTIFICATION_API_URL: str = os.getenv('NOTIFICATION_API_URL', 'http://localhost:3000/api')
    NOTIFICATION_API_KEY: Optional[str] = os.getenv('NOTIFICATION_API_KEY')
    
    # Data Processing Configuration
    DATA_PROCESSING_TIMEOUT: int = int(os.getenv('DATA_PROCESSING_TIMEOUT', '300'))  # seconds
    MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB in bytes
    
    # Database Configuration (if needed)
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL')
    
    @classmethod
    def get_camunda_config(cls) -> Dict[str, Any]:
        """Get Camunda worker configuration"""
        return {
            "maxTasks": cls.MAX_TASKS,
            "lockDuration": cls.LOCK_DURATION,
            "asyncResponseTimeout": cls.ASYNC_RESPONSE_TIMEOUT,
            "retries": cls.RETRIES,
            "retryTimeout": cls.RETRY_TIMEOUT,
            "sleepSeconds": cls.SLEEP_SECONDS
        }
    
    @classmethod
    def get_auth(cls) -> Optional[tuple]:
        """Get authentication tuple if configured"""
        if cls.CAMUNDA_USERNAME and cls.CAMUNDA_PASSWORD:
            return (cls.CAMUNDA_USERNAME, cls.CAMUNDA_PASSWORD)
        return None
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            'CAMUNDA_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required configuration: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return cls.ENVIRONMENT.lower() == 'production'
    
    @classmethod
    def is_local(cls) -> bool:
        """Check if running in local environment"""
        return cls.ENVIRONMENT.lower() == 'local'
    
    @classmethod
    def is_embedded_mode(cls) -> bool:
        """Check if workers are running in embedded mode"""
        return cls.WORKERS_MODE.lower() == 'embedded'
    
    @classmethod
    def is_separated_mode(cls) -> bool:
        """Check if workers are running in separated mode"""
        return cls.WORKERS_MODE.lower() == 'separated'
    
    @classmethod
    def get_environment_info(cls) -> Dict[str, str]:
        """Get environment information for logging"""
        return {
            'environment': cls.ENVIRONMENT,
            'workers_mode': cls.WORKERS_MODE,
            'camunda_url': cls.CAMUNDA_URL,
            'metrics_enabled': str(cls.METRICS_ENABLED)
        }


# Topics Configuration
class Topics:
    """Centralized topic names for external tasks"""
    
    # Simple Hello World topic
    SAY_HELLO = "say_hello"
    
    # Topicos DC
    NOVA_PUBLICACAO = "nova_publicacao"
    
    # Complex workflow topics (archived)
    VALIDATE_DOCUMENT = "validate_document"
    PROCESS_DATA = "process_data" 
    PUBLISH_CONTENT = "publish_content"
    SEND_NOTIFICATION = "send_notification"
    HANDLE_VALIDATION_ERROR = "handle_validation_error"


# Validation configuration
VALIDATION_RULES = {
    'document_types': ['pdf', 'docx', 'txt'],
    'max_file_size': WorkerConfig.MAX_FILE_SIZE,
    'required_fields': ['title', 'content', 'author']
}