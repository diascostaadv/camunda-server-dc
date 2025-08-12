"""
Main environment configuration module
Combines all configuration components into unified settings
"""

from typing import Optional, Dict, Any, List
from pydantic import Field, validator, root_validator
import os
from pathlib import Path

from .base import BaseConfig, Environment
from .mongodb import MongoDBConfig
from .rabbitmq import RabbitMQConfig
from .camunda import CamundaConfig


class GatewayConfig(BaseConfig):
    """Worker API Gateway specific configuration"""
    
    # Gateway Server Configuration
    GATEWAY_HOST: str = Field(
        default="0.0.0.0",
        description="Gateway server host"
    )
    GATEWAY_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Gateway server port"
    )
    GATEWAY_REPLICAS: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of gateway replicas"
    )
    
    # API Configuration
    API_PREFIX: str = Field(
        default="/api",
        description="API route prefix"
    )
    API_VERSION: str = Field(
        default="v1",
        description="API version"
    )
    CORS_ENABLED: bool = Field(
        default=True,
        description="Enable CORS"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Task Processing
    TASK_QUEUE_SIZE: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum task queue size"
    )
    TASK_WORKER_THREADS: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of worker threads for task processing"
    )
    
    # Health Check Configuration
    HEALTH_CHECK_ENABLED: bool = Field(
        default=True,
        description="Enable health check endpoints"
    )
    HEALTH_CHECK_PATH: str = Field(
        default="/health",
        description="Health check endpoint path"
    )
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(
        default=False,
        description="Enable rate limiting"
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        ge=1,
        description="Maximum requests per period"
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=60,
        ge=1,
        description="Rate limit period in seconds"
    )
    
    @root_validator
    def validate_gateway_config(cls, values):
        """Validate gateway configuration"""
        env = values.get("ENVIRONMENT")
        
        if env == Environment.PRODUCTION:
            # Production requirements
            if values.get("CORS_ORIGINS") == ["*"]:
                raise ValueError("CORS must be restricted in production")
            
            if not values.get("RATE_LIMIT_ENABLED"):
                raise ValueError("Rate limiting should be enabled in production")
            
            if values.get("GATEWAY_REPLICAS", 1) < 2:
                raise ValueError("Production should have at least 2 gateway replicas")
        
        return values


class WorkerPlatformConfig(BaseConfig):
    """Worker Platform specific configuration"""
    
    # Worker Scaling Configuration
    WORKER_HELLO_REPLICAS: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of hello worker replicas"
    )
    WORKER_PUBLICACAO_REPLICAS: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of publicacao worker replicas"
    )
    WORKER_PUBLICACAO_UNIFIED_REPLICAS: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Number of unified publicacao worker replicas"
    )
    
    # External API Configuration
    INTIMATION_USER: Optional[str] = Field(
        default=None,
        description="Intimation API username"
    )
    INTIMATION_PASSWORD: Optional[str] = Field(
        default=None,
        description="Intimation API password"
    )
    INTIMATION_API_URL: str = Field(
        default="http://localhost:3000/api",
        description="Intimation API URL"
    )
    
    # Worker Discovery
    AUTO_DISCOVER_WORKERS: bool = Field(
        default=True,
        description="Automatically discover worker modules"
    )
    WORKERS_PATH: str = Field(
        default="workers",
        description="Path to workers directory"
    )
    
    # Performance Tuning
    WORKER_CONCURRENCY: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Worker concurrency level"
    )
    WORKER_PREFETCH_COUNT: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of tasks to prefetch"
    )


class UnifiedConfig(
    MongoDBConfig,
    RabbitMQConfig,
    CamundaConfig,
    GatewayConfig,
    WorkerPlatformConfig
):
    """
    Unified configuration combining all components
    This is the main configuration class to use in applications
    """
    
    # Application Information
    APP_NAME: str = Field(
        default="Camunda BPM Ecosystem",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    # Network Configuration
    NETWORK_DRIVER: str = Field(
        default="bridge",
        description="Docker network driver (bridge, overlay, host)"
    )
    EXTERNAL_NETWORK: bool = Field(
        default=False,
        description="Use external Docker network"
    )
    
    @validator("NETWORK_DRIVER")
    def validate_network_driver(cls, v):
        """Validate network driver"""
        valid_drivers = ["bridge", "overlay", "host", "none"]
        if v not in valid_drivers:
            raise ValueError(f"Invalid network driver: {v}. Must be one of {valid_drivers}")
        return v
    
    @root_validator
    def validate_unified_config(cls, values):
        """Validate the complete unified configuration"""
        env = values.get("ENVIRONMENT")
        
        # Set network driver based on environment
        if env == Environment.PRODUCTION and values.get("NETWORK_DRIVER") == "bridge":
            values["NETWORK_DRIVER"] = "overlay"  # Use overlay for production swarm
        
        # Validate external services mode consistency
        external_mode = values.get("EXTERNAL_SERVICES_MODE")
        if env == Environment.ATLAS:
            values["EXTERNAL_SERVICES_MODE"] = True  # Force external mode for Atlas
        
        # Validate gateway and worker configuration consistency
        gateway_enabled = values.get("GATEWAY_ENABLED")
        gateway_url = values.get("GATEWAY_URL")
        
        if gateway_enabled:
            # If gateway is enabled, ensure URL is configured
            if not gateway_url:
                # Auto-configure based on environment
                if env == Environment.LOCAL:
                    values["GATEWAY_URL"] = "http://localhost:8000"
                else:
                    values["GATEWAY_URL"] = "http://gateway:8000"
        
        return values
    
    @classmethod
    def load_for_environment(cls, environment: Optional[str] = None):
        """
        Load configuration for specific environment
        
        Args:
            environment: Environment name (local, atlas, production)
            
        Returns:
            Configured instance
        """
        if environment:
            os.environ["ENVIRONMENT"] = environment
        else:
            environment = os.getenv("ENVIRONMENT", "local")
        
        # Determine env file
        env_file_map = {
            "local": ".env.local",
            "atlas": ".env.atlas",
            "production": ".env.production"
        }
        
        env_file = env_file_map.get(environment, ".env")
        
        # Load env file if exists
        if os.path.exists(env_file):
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
        
        return cls()
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """
        Get configuration for specific component
        
        Args:
            component: Component name (gateway, worker, camunda, mongodb, rabbitmq)
            
        Returns:
            Component-specific configuration dictionary
        """
        component_map = {
            "mongodb": {
                "uri": self.get_connection_string(),
                "database": self.MONGODB_DATABASE,
                "options": self.get_connection_options(),
                "collections": self.get_collection_names()
            },
            "rabbitmq": {
                "url": self.get_connection_url(),
                "exchange": self.get_exchange_config(),
                "consumer": self.get_consumer_config(),
                "publisher": self.get_publisher_config()
            },
            "camunda": {
                "url": self.CAMUNDA_URL,
                "auth": self.get_auth(),
                "worker": self.get_worker_config(),
                "gateway": self.get_gateway_config()
            },
            "gateway": {
                "host": self.GATEWAY_HOST,
                "port": self.GATEWAY_PORT,
                "replicas": self.GATEWAY_REPLICAS,
                "api_prefix": self.API_PREFIX,
                "cors": {
                    "enabled": self.CORS_ENABLED,
                    "origins": self.CORS_ORIGINS
                }
            },
            "worker": {
                "replicas": {
                    "hello": self.WORKER_HELLO_REPLICAS,
                    "publicacao": self.WORKER_PUBLICACAO_REPLICAS,
                    "unified": self.WORKER_PUBLICACAO_UNIFIED_REPLICAS
                },
                "intimation": {
                    "user": self.INTIMATION_USER,
                    "url": self.INTIMATION_API_URL
                },
                "performance": {
                    "concurrency": self.WORKER_CONCURRENCY,
                    "prefetch": self.WORKER_PREFETCH_COUNT
                }
            }
        }
        
        return component_map.get(component, {})
    
    def validate_all(self) -> bool:
        """
        Validate all configuration components
        
        Returns:
            True if all validations pass
            
        Raises:
            ValueError: If any validation fails
        """
        # Validate individual components
        self.validate_connection()  # MongoDB
        RabbitMQConfig.validate_connection(self)  # RabbitMQ
        CamundaConfig.validate_connection(self)  # Camunda
        
        # Validate required fields based on environment
        if self.is_production():
            required_fields = [
                "SECRET_KEY",
                "MONGODB_URI",
                "RABBITMQ_URL",
                "CAMUNDA_USERNAME",
                "CAMUNDA_PASSWORD"
            ]
            self.validate_required_fields(required_fields)
        
        return True
    
    def print_configuration(self, show_secrets: bool = False):
        """
        Print configuration summary
        
        Args:
            show_secrets: Whether to show sensitive values
        """
        print("=" * 60)
        print(f"Configuration for Environment: {self.ENVIRONMENT}")
        print("=" * 60)
        
        config_dict = self.to_dict(exclude_secrets=not show_secrets)
        
        # Group by component
        components = {
            "General": ["APP_NAME", "APP_VERSION", "ENVIRONMENT", "DEBUG"],
            "MongoDB": [k for k in config_dict if k.startswith("MONGO")],
            "RabbitMQ": [k for k in config_dict if k.startswith("RABBIT")],
            "Camunda": [k for k in config_dict if k.startswith("CAMUNDA") or k.startswith("WORKER")],
            "Gateway": [k for k in config_dict if k.startswith("GATEWAY")],
        }
        
        for component, keys in components.items():
            if keys:
                print(f"\n{component}:")
                print("-" * 40)
                for key in sorted(keys):
                    if key in config_dict:
                        print(f"  {key}: {config_dict[key]}")
        
        print("=" * 60)
    
    def export_to_env_file(self, file_path: str, exclude_secrets: bool = False):
        """
        Export configuration to .env file format
        
        Args:
            file_path: Path to output file
            exclude_secrets: Whether to exclude sensitive values
        """
        config_dict = self.to_dict(exclude_secrets=exclude_secrets)
        
        with open(file_path, "w") as f:
            f.write(f"# Configuration for {self.APP_NAME}\n")
            f.write(f"# Environment: {self.ENVIRONMENT}\n")
            f.write(f"# Generated from UnifiedConfig\n\n")
            
            for key, value in sorted(config_dict.items()):
                if value is not None:
                    # Handle boolean values
                    if isinstance(value, bool):
                        value = str(value).lower()
                    # Handle lists
                    elif isinstance(value, list):
                        value = ",".join(map(str, value))
                    
                    f.write(f"{key}={value}\n")
    
    def __str__(self) -> str:
        """String representation"""
        return (
            f"UnifiedConfig(environment={self.ENVIRONMENT}, "
            f"app={self.APP_NAME}, "
            f"external_services={self.EXTERNAL_SERVICES_MODE}, "
            f"gateway_enabled={self.GATEWAY_ENABLED})"
        )