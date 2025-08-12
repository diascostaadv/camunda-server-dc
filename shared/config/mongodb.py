"""
MongoDB configuration module
Supports both local MongoDB and MongoDB Atlas
"""

from typing import Optional, Dict, Any
from pydantic import Field, validator, root_validator
from urllib.parse import quote_plus, urlparse
from .base import BaseConfig, Environment


class MongoDBConfig(BaseConfig):
    """MongoDB configuration with support for local and Atlas"""
    
    # External Services Mode
    EXTERNAL_SERVICES_MODE: bool = Field(
        default=False,
        description="Use external MongoDB (Atlas) instead of local container"
    )
    
    # MongoDB Connection
    MONGODB_URI: Optional[str] = Field(
        default=None,
        description="MongoDB connection URI (for Atlas or custom connection)"
    )
    
    # Local MongoDB Configuration
    MONGO_HOST: str = Field(
        default="localhost",
        description="MongoDB host for local connection"
    )
    MONGO_PORT: int = Field(
        default=27017,
        ge=1,
        le=65535,
        description="MongoDB port for local connection"
    )
    MONGO_USERNAME: Optional[str] = Field(
        default=None,
        description="MongoDB username"
    )
    MONGO_PASSWORD: Optional[str] = Field(
        default=None,
        description="MongoDB password"
    )
    
    # Database Configuration
    MONGODB_DATABASE: str = Field(
        default="worker_gateway",
        description="MongoDB database name"
    )
    MONGODB_AUTH_SOURCE: str = Field(
        default="admin",
        description="MongoDB authentication database"
    )
    
    # Connection Pool Configuration
    MONGODB_MAX_POOL_SIZE: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum connection pool size"
    )
    MONGODB_MIN_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Minimum connection pool size"
    )
    MONGODB_MAX_IDLE_TIME_MS: int = Field(
        default=30000,
        ge=1000,
        description="Maximum idle time for connections in milliseconds"
    )
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = Field(
        default=5000,
        ge=1000,
        description="Server selection timeout in milliseconds"
    )
    MONGODB_SOCKET_TIMEOUT_MS: int = Field(
        default=20000,
        ge=1000,
        description="Socket timeout in milliseconds"
    )
    
    # SSL/TLS Configuration
    MONGODB_SSL: bool = Field(
        default=False,
        description="Enable SSL/TLS for MongoDB connection"
    )
    MONGODB_SSL_CERT_REQS: Optional[str] = Field(
        default=None,
        description="SSL certificate requirements (none, optional, required)"
    )
    
    # Retry Configuration
    MONGODB_RETRY_WRITES: bool = Field(
        default=True,
        description="Enable retryable writes"
    )
    MONGODB_RETRY_READS: bool = Field(
        default=True,
        description="Enable retryable reads"
    )
    
    # Write Concern
    MONGODB_WRITE_CONCERN: str = Field(
        default="majority",
        description="Write concern level"
    )
    MONGODB_READ_CONCERN: str = Field(
        default="majority",
        description="Read concern level"
    )
    
    # Collection Names
    COLLECTION_TASKS: str = Field(
        default="tasks",
        description="Tasks collection name"
    )
    COLLECTION_LOTES: str = Field(
        default="lotes",
        description="Lotes collection name"
    )
    COLLECTION_PUBLICACOES_BRONZE: str = Field(
        default="publicacoes_bronze",
        description="Bronze publications collection name"
    )
    COLLECTION_PUBLICACOES_PRATA: str = Field(
        default="publicacoes_prata",
        description="Silver publications collection name"
    )
    COLLECTION_HASHES: str = Field(
        default="hashes",
        description="Hashes collection name"
    )
    
    @validator("EXTERNAL_SERVICES_MODE", pre=True)
    def set_external_mode_from_env(cls, v, values):
        """Auto-detect external services mode based on environment"""
        if v is None and "ENVIRONMENT" in values:
            env = values["ENVIRONMENT"]
            # Use external services for Atlas and Production
            if env in [Environment.ATLAS, Environment.PRODUCTION]:
                return True
        return v
    
    @validator("MONGODB_SSL", pre=True)
    def set_ssl_from_uri(cls, v, values):
        """Auto-enable SSL for MongoDB Atlas URIs"""
        uri = values.get("MONGODB_URI")
        if uri and "mongodb+srv://" in uri:
            return True
        return v
    
    @root_validator
    def validate_mongodb_config(cls, values):
        """Validate MongoDB configuration based on mode"""
        external_mode = values.get("EXTERNAL_SERVICES_MODE")
        mongodb_uri = values.get("MONGODB_URI")
        
        if external_mode:
            # External mode requires URI
            if not mongodb_uri:
                raise ValueError("MONGODB_URI is required when EXTERNAL_SERVICES_MODE is True")
        else:
            # Local mode - build URI if not provided
            if not mongodb_uri:
                host = values.get("MONGO_HOST", "localhost")
                port = values.get("MONGO_PORT", 27017)
                username = values.get("MONGO_USERNAME")
                password = values.get("MONGO_PASSWORD")
                auth_source = values.get("MONGODB_AUTH_SOURCE", "admin")
                
                if username and password:
                    # Escape special characters
                    username = quote_plus(username)
                    password = quote_plus(password)
                    mongodb_uri = f"mongodb://{username}:{password}@{host}:{port}/?authSource={auth_source}"
                else:
                    mongodb_uri = f"mongodb://{host}:{port}/"
                
                values["MONGODB_URI"] = mongodb_uri
        
        # Validate pool sizes
        max_pool = values.get("MONGODB_MAX_POOL_SIZE", 50)
        min_pool = values.get("MONGODB_MIN_POOL_SIZE", 5)
        if min_pool > max_pool:
            raise ValueError("MONGODB_MIN_POOL_SIZE cannot be greater than MONGODB_MAX_POOL_SIZE")
        
        return values
    
    def get_connection_string(self) -> str:
        """
        Get MongoDB connection string
        
        Returns:
            MongoDB connection URI
        """
        return self.MONGODB_URI
    
    def get_connection_options(self) -> Dict[str, Any]:
        """
        Get MongoDB connection options for PyMongo
        
        Returns:
            Dictionary of connection options
        """
        options = {
            "maxPoolSize": self.MONGODB_MAX_POOL_SIZE,
            "minPoolSize": self.MONGODB_MIN_POOL_SIZE,
            "maxIdleTimeMS": self.MONGODB_MAX_IDLE_TIME_MS,
            "serverSelectionTimeoutMS": self.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            "socketTimeoutMS": self.MONGODB_SOCKET_TIMEOUT_MS,
            "retryWrites": self.MONGODB_RETRY_WRITES,
            "retryReads": self.MONGODB_RETRY_READS,
        }
        
        # Add SSL options if enabled
        if self.MONGODB_SSL:
            options["ssl"] = True
            if self.MONGODB_SSL_CERT_REQS:
                options["ssl_cert_reqs"] = self.MONGODB_SSL_CERT_REQS
        
        # Add write/read concern for production
        if self.is_production():
            options["w"] = self.MONGODB_WRITE_CONCERN
            options["readConcern"] = {"level": self.MONGODB_READ_CONCERN}
        
        return options
    
    def get_database_name(self) -> str:
        """Get database name"""
        return self.MONGODB_DATABASE
    
    def get_collection_names(self) -> Dict[str, str]:
        """Get all collection names"""
        return {
            "tasks": self.COLLECTION_TASKS,
            "lotes": self.COLLECTION_LOTES,
            "publicacoes_bronze": self.COLLECTION_PUBLICACOES_BRONZE,
            "publicacoes_prata": self.COLLECTION_PUBLICACOES_PRATA,
            "hashes": self.COLLECTION_HASHES
        }
    
    def is_atlas(self) -> bool:
        """Check if using MongoDB Atlas"""
        return self.MONGODB_URI and "mongodb+srv://" in self.MONGODB_URI
    
    def is_replica_set(self) -> bool:
        """Check if connected to a replica set"""
        if self.MONGODB_URI:
            parsed = urlparse(self.MONGODB_URI)
            query_params = parsed.query
            return "replicaSet=" in query_params or self.is_atlas()
        return False
    
    def validate_connection(self) -> bool:
        """
        Validate MongoDB connection settings
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if self.is_production():
            # Production requirements
            if not self.MONGODB_SSL and not self.is_local():
                raise ValueError("SSL must be enabled for production MongoDB connections")
            
            if self.MONGODB_WRITE_CONCERN not in ["majority", "acknowledged"]:
                raise ValueError("Production requires write concern of 'majority' or 'acknowledged'")
        
        return True
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get configuration for health checks"""
        return {
            "uri": self.get_connection_string(),
            "database": self.MONGODB_DATABASE,
            "timeout_ms": self.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            "is_atlas": self.is_atlas(),
            "is_replica_set": self.is_replica_set()
        }
    
    def __str__(self) -> str:
        """String representation (hides connection details)"""
        info = {
            "environment": self.ENVIRONMENT,
            "external_mode": self.EXTERNAL_SERVICES_MODE,
            "database": self.MONGODB_DATABASE,
            "is_atlas": self.is_atlas(),
            "is_replica_set": self.is_replica_set(),
            "ssl_enabled": self.MONGODB_SSL
        }
        return f"MongoDBConfig({info})"