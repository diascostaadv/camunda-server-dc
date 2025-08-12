"""
RabbitMQ configuration module
Supports both local RabbitMQ and cloud-based message brokers
"""

from typing import Optional, Dict, Any, List
from pydantic import Field, validator, root_validator
from urllib.parse import quote_plus, urlparse
from .base import BaseConfig, Environment


class RabbitMQConfig(BaseConfig):
    """RabbitMQ configuration with support for local and cloud deployments"""
    
    # External Services Mode
    EXTERNAL_SERVICES_MODE: bool = Field(
        default=False,
        description="Use external RabbitMQ instead of local container"
    )
    
    # RabbitMQ Connection
    RABBITMQ_URL: Optional[str] = Field(
        default=None,
        description="RabbitMQ connection URL (AMQP URI)"
    )
    
    # Local RabbitMQ Configuration
    RABBITMQ_HOST: str = Field(
        default="localhost",
        description="RabbitMQ host for local connection"
    )
    RABBITMQ_PORT: int = Field(
        default=5672,
        ge=1,
        le=65535,
        description="RabbitMQ port for AMQP connection"
    )
    RABBITMQ_MGMT_PORT: int = Field(
        default=15672,
        ge=1,
        le=65535,
        description="RabbitMQ management UI port"
    )
    RABBITMQ_USER: str = Field(
        default="guest",
        description="RabbitMQ username"
    )
    RABBITMQ_PASSWORD: str = Field(
        default="guest",
        description="RabbitMQ password"
    )
    RABBITMQ_VHOST: str = Field(
        default="/",
        description="RabbitMQ virtual host"
    )
    
    # Exchange and Queue Configuration
    RABBITMQ_EXCHANGE: str = Field(
        default="worker_gateway",
        description="Default exchange name"
    )
    RABBITMQ_EXCHANGE_TYPE: str = Field(
        default="topic",
        description="Exchange type (direct, topic, fanout, headers)"
    )
    RABBITMQ_EXCHANGE_DURABLE: bool = Field(
        default=True,
        description="Make exchange durable"
    )
    RABBITMQ_QUEUE_PREFIX: str = Field(
        default="task",
        description="Prefix for queue names"
    )
    RABBITMQ_QUEUE_DURABLE: bool = Field(
        default=True,
        description="Make queues durable"
    )
    RABBITMQ_QUEUE_AUTO_DELETE: bool = Field(
        default=False,
        description="Auto-delete queues when unused"
    )
    
    # Connection Pool Configuration
    RABBITMQ_CONNECTION_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of connection attempts"
    )
    RABBITMQ_RETRY_DELAY: int = Field(
        default=2,
        ge=1,
        le=60,
        description="Delay between connection attempts in seconds"
    )
    RABBITMQ_HEARTBEAT: int = Field(
        default=600,
        ge=0,
        description="Heartbeat interval in seconds (0 to disable)"
    )
    RABBITMQ_BLOCKED_CONNECTION_TIMEOUT: int = Field(
        default=300,
        ge=0,
        description="Timeout for blocked connections in seconds"
    )
    RABBITMQ_SOCKET_TIMEOUT: int = Field(
        default=5,
        ge=1,
        description="Socket timeout in seconds"
    )
    
    # Consumer Configuration
    RABBITMQ_PREFETCH_COUNT: int = Field(
        default=1,
        ge=0,
        description="Consumer prefetch count (0 for unlimited)"
    )
    RABBITMQ_AUTO_ACK: bool = Field(
        default=False,
        description="Automatically acknowledge messages"
    )
    
    # Publisher Configuration
    RABBITMQ_CONFIRM_DELIVERY: bool = Field(
        default=True,
        description="Enable publisher confirms"
    )
    RABBITMQ_MANDATORY: bool = Field(
        default=True,
        description="Return unroutable messages"
    )
    RABBITMQ_PERSISTENT_MESSAGES: bool = Field(
        default=True,
        description="Make messages persistent"
    )
    
    # SSL/TLS Configuration
    RABBITMQ_SSL: bool = Field(
        default=False,
        description="Enable SSL/TLS for RabbitMQ connection"
    )
    RABBITMQ_SSL_CERT: Optional[str] = Field(
        default=None,
        description="Path to SSL certificate"
    )
    RABBITMQ_SSL_KEY: Optional[str] = Field(
        default=None,
        description="Path to SSL key"
    )
    RABBITMQ_SSL_CA: Optional[str] = Field(
        default=None,
        description="Path to CA certificate"
    )
    
    # Dead Letter Configuration
    RABBITMQ_ENABLE_DLX: bool = Field(
        default=True,
        description="Enable dead letter exchange"
    )
    RABBITMQ_DLX_NAME: str = Field(
        default="dlx_worker_gateway",
        description="Dead letter exchange name"
    )
    RABBITMQ_DLX_TTL: int = Field(
        default=86400000,  # 24 hours in ms
        ge=0,
        description="Message TTL in dead letter queue (milliseconds)"
    )
    
    @validator("RABBITMQ_EXCHANGE_TYPE")
    def validate_exchange_type(cls, v):
        """Validate exchange type"""
        valid_types = ["direct", "topic", "fanout", "headers"]
        if v not in valid_types:
            raise ValueError(f"Invalid exchange type: {v}. Must be one of {valid_types}")
        return v
    
    @root_validator
    def validate_rabbitmq_config(cls, values):
        """Validate RabbitMQ configuration based on mode"""
        external_mode = values.get("EXTERNAL_SERVICES_MODE")
        rabbitmq_url = values.get("RABBITMQ_URL")
        
        if external_mode:
            # External mode requires URL
            if not rabbitmq_url:
                raise ValueError("RABBITMQ_URL is required when EXTERNAL_SERVICES_MODE is True")
        else:
            # Local mode - build URL if not provided
            if not rabbitmq_url:
                host = values.get("RABBITMQ_HOST", "localhost")
                port = values.get("RABBITMQ_PORT", 5672)
                user = values.get("RABBITMQ_USER", "guest")
                password = values.get("RABBITMQ_PASSWORD", "guest")
                vhost = values.get("RABBITMQ_VHOST", "/")
                
                # Escape special characters
                user = quote_plus(user)
                password = quote_plus(password)
                vhost = quote_plus(vhost) if vhost != "/" else ""
                
                rabbitmq_url = f"amqp://{user}:{password}@{host}:{port}/{vhost}"
                values["RABBITMQ_URL"] = rabbitmq_url
        
        # Validate SSL configuration
        if values.get("RABBITMQ_SSL"):
            env = values.get("ENVIRONMENT")
            if env == Environment.PRODUCTION and not values.get("RABBITMQ_SSL_CERT"):
                raise ValueError("SSL certificate configuration required for production")
        
        return values
    
    def get_connection_url(self) -> str:
        """
        Get RabbitMQ connection URL
        
        Returns:
            AMQP connection URI
        """
        return self.RABBITMQ_URL
    
    def get_connection_parameters(self) -> Dict[str, Any]:
        """
        Get RabbitMQ connection parameters for pika
        
        Returns:
            Dictionary of connection parameters
        """
        params = {
            "heartbeat": self.RABBITMQ_HEARTBEAT,
            "blocked_connection_timeout": self.RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,
            "socket_timeout": self.RABBITMQ_SOCKET_TIMEOUT,
            "connection_attempts": self.RABBITMQ_CONNECTION_ATTEMPTS,
            "retry_delay": self.RABBITMQ_RETRY_DELAY,
        }
        
        # Add SSL parameters if enabled
        if self.RABBITMQ_SSL:
            ssl_options = {}
            if self.RABBITMQ_SSL_CERT:
                ssl_options["certfile"] = self.RABBITMQ_SSL_CERT
            if self.RABBITMQ_SSL_KEY:
                ssl_options["keyfile"] = self.RABBITMQ_SSL_KEY
            if self.RABBITMQ_SSL_CA:
                ssl_options["ca_certs"] = self.RABBITMQ_SSL_CA
            params["ssl_options"] = ssl_options
        
        return params
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """Get exchange configuration"""
        return {
            "exchange": self.RABBITMQ_EXCHANGE,
            "exchange_type": self.RABBITMQ_EXCHANGE_TYPE,
            "durable": self.RABBITMQ_EXCHANGE_DURABLE,
            "auto_delete": False,
            "internal": False
        }
    
    def get_queue_config(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get queue configuration
        
        Args:
            queue_name: Optional specific queue name
            
        Returns:
            Queue configuration dictionary
        """
        config = {
            "durable": self.RABBITMQ_QUEUE_DURABLE,
            "auto_delete": self.RABBITMQ_QUEUE_AUTO_DELETE,
            "exclusive": False
        }
        
        if queue_name:
            config["queue"] = queue_name
        
        # Add dead letter configuration if enabled
        if self.RABBITMQ_ENABLE_DLX:
            config["arguments"] = {
                "x-dead-letter-exchange": self.RABBITMQ_DLX_NAME,
                "x-message-ttl": self.RABBITMQ_DLX_TTL
            }
        
        return config
    
    def get_consumer_config(self) -> Dict[str, Any]:
        """Get consumer configuration"""
        return {
            "prefetch_count": self.RABBITMQ_PREFETCH_COUNT,
            "auto_ack": self.RABBITMQ_AUTO_ACK,
            "exclusive": False,
            "consumer_tag": None
        }
    
    def get_publisher_config(self) -> Dict[str, Any]:
        """Get publisher configuration"""
        properties = {}
        
        if self.RABBITMQ_PERSISTENT_MESSAGES:
            properties["delivery_mode"] = 2  # Persistent
        
        return {
            "mandatory": self.RABBITMQ_MANDATORY,
            "properties": properties,
            "confirm_delivery": self.RABBITMQ_CONFIRM_DELIVERY
        }
    
    def get_task_routing_key(self, topic: str, action: str = "submit") -> str:
        """
        Generate RabbitMQ routing key for tasks
        
        Args:
            topic: Task topic
            action: Action type (submit, result, error)
            
        Returns:
            Routing key string
        """
        return f"{self.RABBITMQ_QUEUE_PREFIX}.{action}.{topic}"
    
    def get_worker_queue_name(self, worker_id: str) -> str:
        """
        Generate worker-specific queue name
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            Queue name string
        """
        return f"{self.RABBITMQ_QUEUE_PREFIX}.result.{worker_id}"
    
    def get_dlx_queue_name(self, original_queue: str) -> str:
        """
        Generate dead letter queue name
        
        Args:
            original_queue: Original queue name
            
        Returns:
            Dead letter queue name
        """
        return f"dlx.{original_queue}"
    
    def get_management_url(self) -> str:
        """Get RabbitMQ management UI URL"""
        if self.EXTERNAL_SERVICES_MODE:
            # Try to extract from connection URL
            parsed = urlparse(self.RABBITMQ_URL)
            host = parsed.hostname or "localhost"
            return f"http://{host}:{self.RABBITMQ_MGMT_PORT}"
        else:
            return f"http://{self.RABBITMQ_HOST}:{self.RABBITMQ_MGMT_PORT}"
    
    def validate_connection(self) -> bool:
        """
        Validate RabbitMQ connection settings
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if self.is_production():
            # Production requirements
            if not self.RABBITMQ_CONFIRM_DELIVERY:
                raise ValueError("Publisher confirms must be enabled in production")
            
            if self.RABBITMQ_AUTO_ACK:
                raise ValueError("Auto-acknowledgment should be disabled in production")
            
            if not self.RABBITMQ_PERSISTENT_MESSAGES:
                raise ValueError("Messages must be persistent in production")
        
        return True
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get configuration for health checks"""
        return {
            "url": self.get_connection_url(),
            "vhost": self.RABBITMQ_VHOST,
            "heartbeat": self.RABBITMQ_HEARTBEAT,
            "timeout": self.RABBITMQ_SOCKET_TIMEOUT,
            "ssl_enabled": self.RABBITMQ_SSL
        }
    
    def __str__(self) -> str:
        """String representation (hides connection details)"""
        info = {
            "environment": self.ENVIRONMENT,
            "external_mode": self.EXTERNAL_SERVICES_MODE,
            "exchange": self.RABBITMQ_EXCHANGE,
            "vhost": self.RABBITMQ_VHOST,
            "ssl_enabled": self.RABBITMQ_SSL,
            "dlx_enabled": self.RABBITMQ_ENABLE_DLX
        }
        return f"RabbitMQConfig({info})"