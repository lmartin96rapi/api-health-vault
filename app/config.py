from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Project Info
    PROJECT_NAME: str = "Health Insurance API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/health_insurance.db",
        description="Database URL (SQLite or PostgreSQL)"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Database pool recycle time in seconds")
    
    # Security - JWT
    SECRET_KEY: str = Field(..., description="Secret key for JWT token generation")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration in minutes")
    
    # Security - Google OAuth2
    GOOGLE_CLIENT_ID: str = Field(..., description="Google OAuth2 Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., description="Google OAuth2 Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(..., description="Google OAuth2 Redirect URI")
    
    # Security - CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # File Storage
    UPLOAD_DIR: str = Field(default="./uploads", description="Directory for file uploads")
    MAX_FILE_SIZE: int = Field(default=10485760, description="Max file size in bytes (default 10MB)")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["application/pdf", "image/jpeg", "image/png", "image/jpg"],
        description="Allowed MIME types for file uploads"
    )
    
    # Access Links
    ACCESS_LINK_EXPIRATION_HOURS: int = Field(
        default=24,
        description="Access link expiration time in hours (configurable)"
    )
    
    # External APIs - Backend API
    BACKEND_API_URL: str = Field(..., description="Backend API base URL")
    BACKEND_API_KEY: str = Field(..., description="Backend API key for authentication")
    BACKEND_API_TIMEOUT: int = Field(default=30, description="Backend API timeout in seconds")
    BACKEND_API_RETRY_ATTEMPTS: int = Field(default=3, description="Backend API retry attempts")
    ORGANIZATION_ID: int = Field(default=305, description="Organization ID for backend API (configurable)")
    API_BASE_URL: str = Field(default="http://localhost:8111", description="Base URL for this API (used for document URLs)")
    
    # External APIs - WspApi
    WSP_API_URL: str = Field(..., description="WspApi base URL")
    WSP_API_KEY: str = Field(default="", description="WspApi API key (if required)")
    WSP_API_OAUTH_TOKEN: str = Field(default="", description="WspApi OAuth token (if required)")
    WSP_API_TIMEOUT: int = Field(default=30, description="WspApi timeout in seconds")
    WSP_API_RETRY_ATTEMPTS: int = Field(default=3, description="WspApi retry attempts")
    
    # Server Configuration
    WORKERS: int = Field(default=4, description="Number of Uvicorn workers (4-5)")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Form Configuration
    FORM_EXPIRATION_HOURS: int = Field(default=24, description="Form expiration time in hours")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    LOG_DIR: str = Field(default="./logs", description="Directory for log files")
    LOG_RETENTION_DAYS: int = Field(default=30, description="Number of days to keep log files")
    LOG_MASK_SENSITIVE: bool = Field(default=True, description="Enable sensitive data masking in logs")
    LOG_ENABLE_REQUEST_LOGGING: bool = Field(default=True, description="Enable HTTP request/response logging")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    def get_log_level(self) -> str:
        """Get log level based on environment."""
        if self.ENVIRONMENT.lower() in ["development", "dev", "test"]:
            return "DEBUG"
        return self.LOG_LEVEL.upper()


settings = Settings()

