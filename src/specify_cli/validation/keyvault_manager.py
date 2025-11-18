"""
Azure Key Vault manager for secure secret storage.

Handles storing application secrets in Azure Key Vault using
Managed Identity authentication and RBAC.
"""

import logging
import re
from typing import List, Dict, Optional
import asyncio

from azure.identity.aio import DefaultAzureCredential

try:
    from azure.keyvault.secrets.aio import SecretClient
    from azure.core.exceptions import ResourceNotFoundError, AzureError
    AZURE_KEYVAULT_AVAILABLE = True
except ImportError:
    AZURE_KEYVAULT_AVAILABLE = False
    # Define placeholder exceptions for when SDK is not available
    class ResourceNotFoundError(Exception):
        pass
    class AzureError(Exception):
        pass
    class SecretClient:
        pass

from specify_cli.validation import KeyVaultError, AppSetting

logger = logging.getLogger(__name__)


class KeyVaultManager:
    """
    Manages secrets in Azure Key Vault.
    
    Features:
    - Managed Identity authentication (RBAC)
    - Azure naming conventions for secrets
    - Batch secret operations
    - Key Vault reference generation for App Service
    """
    
    def __init__(self, vault_url: str):
        """
        Initialize Key Vault manager.
        
        Args:
            vault_url: Azure Key Vault URL (https://<vault-name>.vault.azure.net/)
        
        Raises:
            ImportError: If azure-keyvault-secrets is not installed
        """
        if not AZURE_KEYVAULT_AVAILABLE:
            raise ImportError(
                "azure-keyvault-secrets is not installed. "
                "Install it with: pip install azure-keyvault-secrets"
            )
        
        self.vault_url = vault_url
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)
        
        logger.info(f"Initialized KeyVaultManager for: {vault_url}")
    
    async def store_secret(
        self,
        secret_name: str,
        secret_value: str,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store a secret in Key Vault.
        
        Args:
            secret_name: Secret name (will be formatted for Azure)
            secret_value: Secret value
            tags: Optional tags for the secret
            
        Returns:
            Secret identifier (URI)
            
        Raises:
            KeyVaultError: If storage fails
        """
        # Format secret name for Azure Key Vault
        formatted_name = self._format_secret_name(secret_name)
        
        try:
            logger.debug(f"Storing secret: {formatted_name}")
            
            secret = await self.client.set_secret(
                name=formatted_name,
                value=secret_value,
                tags=tags or {}
            )
            
            logger.info(f"Secret stored: {formatted_name}")
            return secret.id
            
        except AzureError as e:
            raise KeyVaultError(f"Failed to store secret {formatted_name}: {e}")
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from Key Vault.
        
        Args:
            secret_name: Secret name
            
        Returns:
            Secret value or None if not found
            
        Raises:
            KeyVaultError: If retrieval fails
        """
        formatted_name = self._format_secret_name(secret_name)
        
        try:
            secret = await self.client.get_secret(formatted_name)
            return secret.value
            
        except ResourceNotFoundError:
            logger.warning(f"Secret not found: {formatted_name}")
            return None
            
        except AzureError as e:
            raise KeyVaultError(f"Failed to get secret {formatted_name}: {e}")
    
    async def store_multiple_secrets(
        self,
        secrets: Dict[str, str],
        environment: str = "test"
    ) -> Dict[str, str]:
        """
        Store multiple secrets in parallel.
        
        Args:
            secrets: Dictionary of secret name -> value
            environment: Environment name for tagging
            
        Returns:
            Dictionary of secret name -> secret ID
            
        Raises:
            KeyVaultError: If any storage fails
        """
        logger.info(f"Storing {len(secrets)} secrets in Key Vault")
        
        tasks = []
        names = []
        
        for name, value in secrets.items():
            tags = {"environment": environment, "managed-by": "specify-validate"}
            tasks.append(self.store_secret(name, value, tags))
            names.append(name)
        
        try:
            results = await asyncio.gather(*tasks)
            return dict(zip(names, results))
            
        except Exception as e:
            raise KeyVaultError(f"Failed to store multiple secrets: {e}")
    
    async def store_app_settings(
        self,
        app_settings: List[AppSetting],
        environment: str = "test"
    ) -> Dict[str, str]:
        """
        Store secure app settings in Key Vault.
        
        Args:
            app_settings: List of app settings
            environment: Environment name
            
        Returns:
            Dictionary of setting name -> Key Vault reference
        """
        secure_settings = [s for s in app_settings if s.is_secure]
        
        if not secure_settings:
            logger.info("No secure settings to store")
            return {}
        
        logger.info(f"Storing {len(secure_settings)} secure settings")
        
        # Store secrets
        secrets = {
            setting.name: setting.value or ""
            for setting in secure_settings
        }
        
        secret_ids = await self.store_multiple_secrets(secrets, environment)
        
        # Build Key Vault references
        references = {}
        for setting in secure_settings:
            if setting.name in secret_ids:
                ref = self.build_app_setting_reference(setting.name)
                references[setting.name] = ref
        
        return references
    
    def build_app_setting_reference(
        self,
        secret_name: str
    ) -> str:
        """
        Build Key Vault reference for App Service app setting.
        
        Format: @Microsoft.KeyVault(VaultName=<vault>;SecretName=<secret>)
        
        Args:
            secret_name: Secret name
            
        Returns:
            Key Vault reference string
        """
        formatted_name = self._format_secret_name(secret_name)
        vault_name = self._extract_vault_name()
        
        reference = (
            f"@Microsoft.KeyVault(VaultName={vault_name};"
            f"SecretName={formatted_name})"
        )
        
        return reference
    
    def _format_secret_name(self, name: str) -> str:
        """
        Format secret name according to Azure Key Vault conventions.
        
        Rules:
        - Only alphanumeric characters and hyphens
        - Maximum 127 characters
        - Lowercase
        - Replace colons with double hyphens (ASP.NET convention)
        - Replace underscores with hyphens
        
        Args:
            name: Original secret name
            
        Returns:
            Formatted secret name
        """
        # Convert to lowercase
        formatted = name.lower()
        
        # Replace colons with double hyphens (for ASP.NET config keys)
        formatted = formatted.replace(":", "--")
        
        # Replace underscores with hyphens
        formatted = formatted.replace("_", "-")
        
        # Remove any non-alphanumeric characters except hyphens
        formatted = re.sub(r'[^a-z0-9-]', '', formatted)
        
        # Ensure max 127 characters
        if len(formatted) > 127:
            formatted = formatted[:127]
        
        # Remove leading/trailing hyphens
        formatted = formatted.strip("-")
        
        return formatted
    
    def _extract_vault_name(self) -> str:
        """
        Extract vault name from vault URL.
        
        Returns:
            Vault name
        """
        # URL format: https://<vault-name>.vault.azure.net/
        if "://" in self.vault_url:
            domain = self.vault_url.split("://")[1]
            vault_name = domain.split(".")[0]
            return vault_name
        
        return "unknown"
    
    async def delete_secret(self, secret_name: str) -> None:
        """
        Delete a secret from Key Vault.
        
        Args:
            secret_name: Secret name
            
        Raises:
            KeyVaultError: If deletion fails
        """
        formatted_name = self._format_secret_name(secret_name)
        
        try:
            await self.client.begin_delete_secret(formatted_name)
            logger.info(f"Secret deleted: {formatted_name}")
            
        except ResourceNotFoundError:
            logger.warning(f"Secret not found for deletion: {formatted_name}")
            
        except AzureError as e:
            raise KeyVaultError(f"Failed to delete secret {formatted_name}: {e}")
    
    async def close(self) -> None:
        """Close the Key Vault client and credential"""
        await self.client.close()
        await self.credential.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
