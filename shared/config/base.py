"""
Base configuration module using Pydantic
Provides common configuration patterns and validation
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseSettings, Field, validator, root_validator
from pathlib import Path
import os


class Environment(str, Enum):
    """Supported environment types"""
    LOCAL = "local"
    ATLAS = "atlas"
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    STAGING = "staging"


class BaseConfig(BaseSettings):
    """
    Base configuration class with common settings
    All configuration classes should inherit from this
    """
    
    # Environment Configuration
    ENVIRONMENT: Environment = Field(
        default=Environment.LOCAL,
        description="Current environment (local, atlas, production, etc)"
    )
    
    # Debug Configuration
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    LOG_FILE_PATH: Optional[Path] = Field(
        default=None,
        description="Path for log files"
    )
    
    # Metrics Configuration
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    METRICS_PORT: int = Field(
        default=9000,
        ge=1024,
        le=65535,
        description="Port for metrics endpoint"
    )
    
    # Security Configuration
    SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for encryption/signing"
    )
    API_KEY_HEADER: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    
    # Performance Configuration
    TIMEOUT: int = Field(
        default=300,
        ge=1,
        description="Default timeout in seconds"
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries"
    )
    RETRY_DELAY: int = Field(
        default=60,
        ge=0,
        description="Delay between retries in seconds"
    )
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        use_enum_values = True
        
        # Allow extra fields for flexibility
        extra = "allow"
        
        # Customize field names
        fields = {
            "ENVIRONMENT": {"env": ["ENVIRONMENT", "ENV"]}
        }
    
    @validator("ENVIRONMENT", pre=True)
    def validate_environment(cls, v):
        """Validate and normalize environment value"""
        if isinstance(v, str):
            v = v.lower()
            # Map common variations
            if v in ["dev", "development"]:
                return Environment.DEVELOPMENT
            elif v in ["prod", "production"]:
                return Environment.PRODUCTION
            elif v in ["local", "localhost"]:
                return Environment.LOCAL
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v
    
    @validator("DEBUG", pre=True)
    def set_debug_from_env(cls, v, values):
        """Set debug mode based on environment"""
        if v is None and "ENVIRONMENT" in values:
            env = values["ENVIRONMENT"]
            # Auto-enable debug for local/development
            if env in [Environment.LOCAL, Environment.DEVELOPMENT]:
                return True
        return v
    
    @root_validator
    def validate_production_settings(cls, values):
        """Ensure production settings are secure"""
        env = values.get("ENVIRONMENT")
        
        if env == Environment.PRODUCTION:
            # Ensure debug is off in production
            if values.get("DEBUG"):
                raise ValueError("DEBUG must be False in production")
            
            # Ensure secret key is set in production
            if not values.get("SECRET_KEY"):
                raise ValueError("SECRET_KEY must be set in production")
            
            # Ensure appropriate log level
            if values.get("LOG_LEVEL") == "DEBUG":
                raise ValueError("LOG_LEVEL should not be DEBUG in production")
        
        return values
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    def is_local(self) -> bool:
        """Check if running locally"""
        return self.ENVIRONMENT in [Environment.LOCAL, Environment.DEVELOPMENT]
    
    def is_atlas(self) -> bool:
        """Check if using Atlas configuration"""
        return self.ENVIRONMENT == Environment.ATLAS
    
    def get_env_file(self) -> str:
        """Get the appropriate env file for current environment"""
        env_mapping = {
            Environment.LOCAL: ".env.local",
            Environment.ATLAS: ".env.atlas",
            Environment.PRODUCTION: ".env.production",
            Environment.DEVELOPMENT: ".env.development",
            Environment.STAGING: ".env.staging"
        }
        return env_mapping.get(self.ENVIRONMENT, ".env")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for logging"""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "log_level": self.LOG_LEVEL,
            "metrics_enabled": self.METRICS_ENABLED,
            "is_production": self.is_production(),
            "is_local": self.is_local()
        }
    
    def validate_required_fields(self, required_fields: List[str]) -> bool:
        """
        Validate that required fields are set
        
        Args:
            required_fields: List of field names that must be set
            
        Returns:
            bool: True if all required fields are set
            
        Raises:
            ValueError: If any required field is not set
        """
        missing_fields = []
        for field in required_fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        return True
    
    @classmethod
    def load_from_env(cls, env_file: Optional[str] = None):
        """
        Load configuration from environment file
        
        Args:
            env_file: Path to env file (optional)
            
        Returns:
            Instance of configuration class
        """
        if env_file and os.path.exists(env_file):
            # Load specific env file
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
        
        return cls()
    
    def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
        """
        Convert configuration to dictionary
        
        Args:
            exclude_secrets: Whether to exclude sensitive fields
            
        Returns:
            Dictionary representation of configuration
        """
        data = self.dict()
        
        if exclude_secrets:
            # Remove sensitive fields
            sensitive_fields = ["SECRET_KEY", "PASSWORD", "TOKEN", "API_KEY"]
            for field in data.keys():
                if any(sensitive in field.upper() for sensitive in sensitive_fields):
                    data[field] = "***HIDDEN***"
        
        return data
    
    def __str__(self) -> str:
        """String representation (hides sensitive data)"""
        return f"{self.__class__.__name__}({self.to_dict(exclude_secrets=True)})"
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"<{self.__class__.__name__} environment={self.ENVIRONMENT}>"