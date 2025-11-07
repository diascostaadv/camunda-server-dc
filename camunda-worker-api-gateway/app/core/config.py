"""
Configuration module for Worker API Gateway
Centralized settings management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application Configuration
    APP_NAME: str = "Worker API Gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # MongoDB Configuration (External Cluster)
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI",
        "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/",  # Hardcoded for production
    )
    MONGODB_CONNECTION_STRING: str = os.getenv(
        "MONGODB_CONNECTION_STRING",
        os.getenv("MONGODB_URI", "mongodb://localhost:27017"),  # Alias for MONGODB_URI
    )
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "worker_gateway")
    MONGODB_COLLECTION_TASKS: str = "tasks"

    # Redis Configuration (Redis Cloud - Token Cache)
    REDIS_URI: str = os.getenv(
        "REDIS_URI",
        "redis://default:n79sTZdBLtqjCdgIisW7rSyMqrFFBq3J@redis-15796.c62.us-east-1-4.ec2.redns.redis-cloud.com:15796"
    )

    # Task Processing Configuration
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 minutes
    TASK_RETRY_LIMIT: int = int(os.getenv("TASK_RETRY_LIMIT", "3"))
    TASK_RETRY_DELAY: int = int(os.getenv("TASK_RETRY_DELAY", "60"))  # seconds

    # Supported Task Topics
    SUPPORTED_TOPICS: list = [
        "nova_publicacao",
        "say_hello",
        "validate_document",
        "process_data",
        "publish_content",
        "send_notification",
    ]

    # Status Configuration
    TASK_STATUSES: dict = {
        "em_andamento": "Task is being processed",
        "aguardando": "Task is waiting for external dependency",
        "sucesso": "Task completed successfully",
        "erro": "Task failed with error",
    }

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Security Configuration (future use)
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    API_KEY_HEADER: str = "X-API-Key"

    # Metrics Configuration
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9000"))

    # Environment Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

    # CPJ API Configuration
    CPJ_BASE_URL: str = os.getenv(
        "CPJ_BASE_URL", "https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2"
    )
    CPJ_LOGIN: str = os.getenv("CPJ_LOGIN", "api")
    CPJ_PASSWORD: str = os.getenv("CPJ_PASSWORD", "2025")
    CPJ_TOKEN_EXPIRY_MINUTES: int = int(os.getenv("CPJ_TOKEN_EXPIRY_MINUTES", "30"))

    # N8N Integration Configuration
    N8N_WEBHOOK_URL: str = os.getenv(
        "N8N_WEBHOOK_URL",
        "https://nutec.app.n8n.cloud/webhook/1e5790e3-8efd-4246-88c1-fbb0ef3c68a7"
    )
    N8N_TIMEOUT: int = int(os.getenv("N8N_TIMEOUT", "120"))  # 2 minutes timeout

    # DW LAW e-Protocol API Configuration
    DW_LAW_BASE_URL: str = os.getenv(
        "DW_LAW_BASE_URL",
        "https://web-eprotocol-integration-cons-qa.azurewebsites.net"
    )
    DW_LAW_USUARIO: str = os.getenv("DW_LAW_USUARIO", "integ_dias_cons@dwlaw.com.br")
    DW_LAW_SENHA: str = os.getenv("DW_LAW_SENHA", "DC@Dwlaw2025")
    DW_LAW_TOKEN_EXPIRY_MINUTES: int = int(os.getenv("DW_LAW_TOKEN_EXPIRY_MINUTES", "120"))  # 2 hours default
    DW_LAW_TIMEOUT: int = int(os.getenv("DW_LAW_TIMEOUT", "120"))  # 2 minutes timeout
    DW_LAW_CHAVE_PROJETO: str = os.getenv("DW_LAW_CHAVE_PROJETO", "diascostacitacaoconsultaunica")  # Chave padrão do projeto

    # Camunda REST API Configuration
    CAMUNDA_REST_URL: str = os.getenv(
        "CAMUNDA_REST_URL",
        "http://201.23.67.197:8080/engine-rest"
    )
    CAMUNDA_REST_USER: str = os.getenv("CAMUNDA_REST_USER", "admin")
    CAMUNDA_REST_PASSWORD: str = os.getenv("CAMUNDA_REST_PASSWORD", "DiasCosta@!!2025")

    # Marcação Automática de Publicações
    MARCAR_AUTOMATICAMENTE: bool = os.getenv("MARCAR_AUTOMATICAMENTE", "true").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() in ["local", "development", "dev"]

    def get_mongodb_connection_options(self) -> dict:
        """Get MongoDB connection options"""
        options = {
            "maxPoolSize": 50,
            "minPoolSize": 5,
            "maxIdleTimeMS": 30000,
            "serverSelectionTimeoutMS": 5000,
            "socketTimeoutMS": 20000,
        }

        if self.is_production():
            options.update(
                {
                    "retryWrites": True,
                    "w": "majority",
                    "ssl": True,
                }
            )

        return options


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings


# Validation
def validate_settings():
    """Validate required settings"""
    required_vars = []

    if not settings.MONGODB_URI or settings.MONGODB_URI == "mongodb://localhost:27017":
        if settings.is_production():
            required_vars.append("MONGODB_URI")

    # RABBITMQ_URL validation removed - no longer used

    if required_vars:
        raise ValueError(
            f"Missing required production configuration: {', '.join(required_vars)}"
        )

    return True


# Validate on import
if settings.is_production():
    validate_settings()
