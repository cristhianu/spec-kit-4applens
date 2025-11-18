"""Configuration module for FastAPI application"""
import os
from typing import Optional

class Settings:
    """Application settings loaded from environment"""
    
    # Azure Cosmos DB
    COSMOS_ENDPOINT: str = os.getenv("COSMOS_ENDPOINT", "")
    COSMOS_KEY: str = os.getenv("COSMOS_KEY", "")
    COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "products-db")
    
    # Azure Service Bus
    SERVICEBUS_NAMESPACE: str = os.getenv("SERVICEBUS_NAMESPACE", "")
    SERVICEBUS_CONNECTION_STRING: str = os.getenv("SERVICEBUS_CONNECTION_STRING", "")
    
    # Azure Key Vault
    KEYVAULT_URL: str = os.getenv("KEYVAULT_URL", "")
    KEYVAULT_NAME: str = os.getenv("KEYVAULT_NAME", "")
    
    # API Configuration
    API_TITLE: str = "Python FastAPI"
    API_VERSION: str = "1.0.0"
    API_SECRET: str = os.getenv("API_SECRET", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
