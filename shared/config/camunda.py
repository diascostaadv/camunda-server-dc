"""
Camunda BPM configuration module
Configuration for Camunda Engine and External Task Workers
"""

from typing import Optional, Dict, Any, List, Tuple
from pydantic import Field, validator, root_validator
from .base import BaseConfig, Environment


class CamundaConfig(BaseConfig):
    """Camunda BPM configuration for engine and workers"""
    
    # Camunda Engine Configuration
    CAMUNDA_URL: str = Field(
        default="http://localhost:8080/engine-rest",
        description="Camunda REST API URL"
    )
    CAMUNDA_USERNAME: Optional[str] = Field(
        default="demo",
        description="Camunda username for authentication"
    )
    CAMUNDA_PASSWORD: Optional[str] = Field(
        default="demo",
        description="Camunda password for authentication"
    )
    
    # Worker Configuration
    WORKER_ID: Optional[str] = Field(
        default=None,
        description="Unique worker identifier (auto-generated if not set)"
    )
    MAX_TASKS: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of tasks to fetch at once"
    )
    LOCK_DURATION: int = Field(
        default=60000,
        ge=10000,
        le=600000,
        description="Lock duration in milliseconds"
    )
    ASYNC_RESPONSE_TIMEOUT: int = Field(
        default=30000,
        ge=5000,
        le=300000,
        description="Async response timeout in milliseconds"
    )
    POLLING_INTERVAL: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Polling interval in seconds"
    )
    
    # Retry Configuration
    RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Default number of retries for failed tasks"
    )
    RETRY_TIMEOUT: int = Field(
        default=5000,
        ge=1000,
        le=60000,
        description="Retry timeout in milliseconds"
    )
    RETRY_BACKOFF_FACTOR: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff factor for retries"
    )
    
    # Topics Configuration
    TOPICS: List[str] = Field(
        default_factory=list,
        description="List of topics this worker subscribes to"
    )
    TOPIC_LOCK_DURATION: Optional[Dict[str, int]] = Field(
        default=None,
        description="Per-topic lock duration overrides"
    )
    
    # Process Configuration
    DEFAULT_PROCESS_KEY: str = Field(
        default="default_process",
        description="Default process definition key"
    )
    PROCESS_VARIABLES_PREFIX: str = Field(
        default="",
        description="Prefix for process variables"
    )
    
    # HTTP Client Configuration
    HTTP_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=300,
        description="HTTP request timeout in seconds"
    )
    HTTP_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum HTTP request retries"
    )
    HTTP_VERIFY_SSL: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )
    
    # Worker Mode Configuration
    WORKERS_MODE: str = Field(
        default="separated",
        description="Worker deployment mode (separated, embedded, unified)"
    )
    
    # Gateway Integration
    GATEWAY_ENABLED: bool = Field(
        default=False,
        description="Enable API Gateway integration for task processing"
    )
    GATEWAY_URL: Optional[str] = Field(
        default=None,
        description="Worker API Gateway URL"
    )
    GATEWAY_COMMUNICATION_MODE: str = Field(
        default="http",
        description="Gateway communication mode (http, rabbitmq)"
    )
    GATEWAY_HTTP_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Gateway HTTP timeout in seconds"
    )
    
    # Deployment Configuration
    AUTO_DEPLOY_RESOURCES: bool = Field(
        default=False,
        description="Automatically deploy BPMN resources on startup"
    )
    BPMN_RESOURCES_PATH: Optional[str] = Field(
        default=None,
        description="Path to BPMN resource files"
    )
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable Camunda metrics collection"
    )
    METRICS_INTERVAL: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Metrics collection interval in seconds"
    )
    
    @validator("WORKERS_MODE")
    def validate_workers_mode(cls, v):
        """Validate workers mode"""
        valid_modes = ["separated", "embedded", "unified"]
        if v not in valid_modes:
            raise ValueError(f"Invalid workers mode: {v}. Must be one of {valid_modes}")
        return v
    
    @validator("GATEWAY_COMMUNICATION_MODE")
    def validate_gateway_mode(cls, v):
        """Validate gateway communication mode"""
        valid_modes = ["http", "rabbitmq"]
        if v not in valid_modes:
            raise ValueError(f"Invalid gateway mode: {v}. Must be one of {valid_modes}")
        return v
    
    @validator("WORKER_ID", pre=True, always=True)
    def generate_worker_id(cls, v):
        """Generate worker ID if not provided"""
        if not v:
            import socket
            import uuid
            hostname = socket.gethostname()
            unique_id = str(uuid.uuid4())[:8]
            return f"{hostname}-{unique_id}"
        return v
    
    @root_validator
    def validate_camunda_config(cls, values):
        """Validate Camunda configuration"""
        gateway_enabled = values.get("GATEWAY_ENABLED")
        gateway_url = values.get("GATEWAY_URL")
        
        if gateway_enabled and not gateway_url:
            raise ValueError("GATEWAY_URL is required when GATEWAY_ENABLED is True")
        
        # Validate authentication for production
        env = values.get("ENVIRONMENT")
        if env == Environment.PRODUCTION:
            if not values.get("CAMUNDA_USERNAME") or not values.get("CAMUNDA_PASSWORD"):
                raise ValueError("Camunda authentication is required in production")
            
            if not values.get("HTTP_VERIFY_SSL"):
                raise ValueError("SSL verification must be enabled in production")
        
        # Validate lock duration vs async timeout
        lock_duration = values.get("LOCK_DURATION", 60000)
        async_timeout = values.get("ASYNC_RESPONSE_TIMEOUT", 30000)
        if async_timeout >= lock_duration:
            raise ValueError("ASYNC_RESPONSE_TIMEOUT must be less than LOCK_DURATION")
        
        return values
    
    def get_auth(self) -> Optional[Tuple[str, str]]:
        """
        Get authentication tuple for Camunda
        
        Returns:
            Tuple of (username, password) or None
        """
        if self.CAMUNDA_USERNAME and self.CAMUNDA_PASSWORD:
            return (self.CAMUNDA_USERNAME, self.CAMUNDA_PASSWORD)
        return None
    
    def get_worker_config(self) -> Dict[str, Any]:
        """
        Get worker configuration for Camunda client
        
        Returns:
            Dictionary of worker configuration
        """
        config = {
            "worker_id": self.WORKER_ID,
            "max_tasks": self.MAX_TASKS,
            "lock_duration": self.LOCK_DURATION,
            "async_response_timeout": self.ASYNC_RESPONSE_TIMEOUT,
            "topics": self.TOPICS,
            "polling_interval": self.POLLING_INTERVAL,
            "retries": self.RETRIES,
            "retry_timeout": self.RETRY_TIMEOUT
        }
        
        # Add per-topic lock durations if configured
        if self.TOPIC_LOCK_DURATION:
            config["topic_lock_duration"] = self.TOPIC_LOCK_DURATION
        
        return config
    
    def get_http_config(self) -> Dict[str, Any]:
        """Get HTTP client configuration"""
        return {
            "timeout": self.HTTP_TIMEOUT,
            "max_retries": self.HTTP_MAX_RETRIES,
            "verify": self.HTTP_VERIFY_SSL,
            "auth": self.get_auth()
        }
    
    def get_gateway_config(self) -> Dict[str, Any]:
        """Get gateway integration configuration"""
        if not self.GATEWAY_ENABLED:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "url": self.GATEWAY_URL,
            "mode": self.GATEWAY_COMMUNICATION_MODE,
            "timeout": self.GATEWAY_HTTP_TIMEOUT
        }
    
    def get_engine_url(self, endpoint: str = "") -> str:
        """
        Get full Camunda engine URL for an endpoint
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL
        """
        base_url = self.CAMUNDA_URL.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}" if endpoint else base_url
    
    def get_external_task_url(self) -> str:
        """Get external task API URL"""
        return self.get_engine_url("external-task")
    
    def get_process_definition_url(self) -> str:
        """Get process definition API URL"""
        return self.get_engine_url("process-definition")
    
    def get_process_instance_url(self) -> str:
        """Get process instance API URL"""
        return self.get_engine_url("process-instance")
    
    def get_deployment_url(self) -> str:
        """Get deployment API URL"""
        return self.get_engine_url("deployment")
    
    def is_embedded_mode(self) -> bool:
        """Check if workers are in embedded mode"""
        return self.WORKERS_MODE == "embedded"
    
    def is_separated_mode(self) -> bool:
        """Check if workers are in separated mode"""
        return self.WORKERS_MODE == "separated"
    
    def is_unified_mode(self) -> bool:
        """Check if workers are in unified mode"""
        return self.WORKERS_MODE == "unified"
    
    def is_gateway_enabled(self) -> bool:
        """Check if gateway integration is enabled"""
        return self.GATEWAY_ENABLED
    
    def validate_connection(self) -> bool:
        """
        Validate Camunda connection settings
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.CAMUNDA_URL:
            raise ValueError("CAMUNDA_URL is required")
        
        if self.is_production():
            if "localhost" in self.CAMUNDA_URL or "127.0.0.1" in self.CAMUNDA_URL:
                raise ValueError("Production cannot use localhost URLs")
        
        return True
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get configuration for health checks"""
        return {
            "url": self.CAMUNDA_URL,
            "auth": self.get_auth() is not None,
            "worker_id": self.WORKER_ID,
            "topics": self.TOPICS,
            "gateway_enabled": self.GATEWAY_ENABLED,
            "workers_mode": self.WORKERS_MODE
        }
    
    def __str__(self) -> str:
        """String representation (hides credentials)"""
        info = {
            "environment": self.ENVIRONMENT,
            "camunda_url": self.CAMUNDA_URL,
            "worker_id": self.WORKER_ID,
            "topics": len(self.TOPICS),
            "gateway_enabled": self.GATEWAY_ENABLED,
            "workers_mode": self.WORKERS_MODE
        }
        return f"CamundaConfig({info})"