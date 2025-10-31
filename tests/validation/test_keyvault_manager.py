"""
Unit tests for keyvault_manager module.

Tests Key Vault secret management with mocked Azure SDK.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from azure.core.exceptions import ResourceNotFoundError, AzureError

from specify_cli.validation import KeyVaultError, AppSetting, SourceType
from specify_cli.validation.keyvault_manager import KeyVaultManager


@pytest.fixture
def mock_secret_client():
    """Mock Azure Key Vault SecretClient."""
    with patch("specify_cli.validation.keyvault_manager.SecretClient") as mock:
        client_instance = AsyncMock()
        
        # Mock set_secret
        secret_mock = Mock()
        secret_mock.id = "https://test-vault.vault.azure.net/secrets/test-secret/version"
        client_instance.set_secret = AsyncMock(return_value=secret_mock)
        
        # Mock get_secret
        secret_value_mock = Mock()
        secret_value_mock.value = "secret-value"
        client_instance.get_secret = AsyncMock(return_value=secret_value_mock)
        
        # Mock delete operations
        client_instance.begin_delete_secret = AsyncMock()
        client_instance.close = AsyncMock()
        
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_credential():
    """Mock DefaultAzureCredential."""
    with patch("specify_cli.validation.keyvault_manager.DefaultAzureCredential") as mock:
        cred_instance = AsyncMock()
        cred_instance.close = AsyncMock()
        mock.return_value = cred_instance
        yield cred_instance


@pytest.fixture
def sample_app_settings():
    """Create sample app settings."""
    return [
        AppSetting(
            setting_id="setting-1",
            name="ConnectionStrings:Database",
            value="Server=test.database.windows.net;...",
            source_type=SourceType.HARDCODED,
            is_secure=True,
            environment="test",
            keyvault_secret_name=None
        ),
        AppSetting(
            setting_id="setting-2",
            name="ApiKey",
            value="secret-api-key-12345",
            source_type=SourceType.HARDCODED,
            is_secure=True,
            environment="test",
            keyvault_secret_name=None
        ),
        AppSetting(
            setting_id="setting-3",
            name="AppName",
            value="MyApplication",
            source_type=SourceType.HARDCODED,
            is_secure=False,
            environment="test",
            keyvault_secret_name=None
        )
    ]


@pytest.mark.asyncio
class TestKeyVaultManager:
    """Test KeyVaultManager class."""
    
    async def test_initialization(self, mock_secret_client, mock_credential):
        """Test KeyVaultManager initialization."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        assert manager.vault_url == "https://test-vault.vault.azure.net/"
        assert manager.client is not None
        assert manager.credential is not None
    
    async def test_store_secret_success(self, mock_secret_client, mock_credential):
        """Test storing a secret successfully."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        secret_id = await manager.store_secret("test-secret", "secret-value")
        
        assert "test-secret" in secret_id or "test-secret" in str(mock_secret_client.set_secret.call_args)
        mock_secret_client.set_secret.assert_called_once()
    
    async def test_store_secret_with_tags(self, mock_secret_client, mock_credential):
        """Test storing a secret with tags."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        tags = {"environment": "test", "app": "myapp"}
        secret_id = await manager.store_secret("test-secret", "secret-value", tags=tags)
        
        call_args = mock_secret_client.set_secret.call_args
        assert call_args[1]["tags"] == tags
    
    async def test_store_secret_failure(self, mock_secret_client, mock_credential):
        """Test secret storage failure."""
        mock_secret_client.set_secret.side_effect = AzureError("Storage failed")
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        with pytest.raises(KeyVaultError, match="Failed to store secret"):
            await manager.store_secret("test-secret", "secret-value")
    
    async def test_get_secret_success(self, mock_secret_client, mock_credential):
        """Test retrieving a secret successfully."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        value = await manager.get_secret("test-secret")
        
        assert value == "secret-value"
        mock_secret_client.get_secret.assert_called_once()
    
    async def test_get_secret_not_found(self, mock_secret_client, mock_credential):
        """Test retrieving non-existent secret."""
        mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        value = await manager.get_secret("nonexistent-secret")
        
        assert value is None
    
    async def test_get_secret_failure(self, mock_secret_client, mock_credential):
        """Test secret retrieval failure."""
        mock_secret_client.get_secret.side_effect = AzureError("Retrieval failed")
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        with pytest.raises(KeyVaultError, match="Failed to get secret"):
            await manager.get_secret("test-secret")
    
    async def test_store_multiple_secrets(self, mock_secret_client, mock_credential):
        """Test storing multiple secrets in parallel."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        secrets = {
            "secret1": "value1",
            "secret2": "value2",
            "secret3": "value3"
        }
        
        result = await manager.store_multiple_secrets(secrets, environment="test")
        
        assert len(result) == 3
        assert all(key in result for key in secrets.keys())
        assert mock_secret_client.set_secret.call_count == 3
    
    async def test_store_multiple_secrets_with_failure(self, mock_secret_client, mock_credential):
        """Test partial failure when storing multiple secrets."""
        # Make second call fail
        call_count = [0]
        
        async def set_secret_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise AzureError("Storage failed")
            secret_mock = Mock()
            secret_mock.id = f"https://vault/secrets/{args[0]}"
            return secret_mock
        
        mock_secret_client.set_secret.side_effect = set_secret_side_effect
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        secrets = {"secret1": "value1", "secret2": "value2", "secret3": "value3"}
        
        with pytest.raises(KeyVaultError, match="Failed to store multiple secrets"):
            await manager.store_multiple_secrets(secrets)
    
    async def test_store_app_settings_secure_only(self, mock_secret_client, mock_credential, sample_app_settings):
        """Test storing only secure app settings."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        references = await manager.store_app_settings(sample_app_settings, environment="test")
        
        # Only 2 secure settings should be stored
        assert len(references) == 2
        assert "ConnectionStrings:Database" in references
        assert "ApiKey" in references
        assert "AppName" not in references
        
        # Verify references format
        for ref in references.values():
            assert ref.startswith("@Microsoft.KeyVault(VaultName=")
    
    async def test_store_app_settings_no_secure(self, mock_secret_client, mock_credential):
        """Test storing app settings with no secure values."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        non_secure_settings = [
            AppSetting("s1", "Setting1", "value1", SourceType.HARDCODED, False, "test"),
            AppSetting("s2", "Setting2", "value2", SourceType.HARDCODED, False, "test")
        ]
        
        references = await manager.store_app_settings(non_secure_settings)
        
        assert len(references) == 0
        mock_secret_client.set_secret.assert_not_called()
    
    async def test_build_app_setting_reference(self, mock_secret_client, mock_credential):
        """Test building Key Vault reference for App Service."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        reference = manager.build_app_setting_reference("MySecret")
        
        assert reference.startswith("@Microsoft.KeyVault(VaultName=")
        assert "test-vault" in reference
        assert "SecretName=mysecret" in reference  # Should be lowercase
    
    async def test_format_secret_name_basic(self, mock_secret_client, mock_credential):
        """Test basic secret name formatting."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        formatted = manager._format_secret_name("MySecret")
        assert formatted == "mysecret"
        
        formatted = manager._format_secret_name("My_Secret")
        assert formatted == "my-secret"
        
        formatted = manager._format_secret_name("MY-SECRET")
        assert formatted == "my-secret"
    
    async def test_format_secret_name_aspnet_config(self, mock_secret_client, mock_credential):
        """Test formatting ASP.NET configuration keys."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        # ASP.NET uses colons for hierarchical config
        formatted = manager._format_secret_name("ConnectionStrings:Database")
        assert formatted == "connectionstrings--database"
        
        formatted = manager._format_secret_name("Azure:Storage:ConnectionString")
        assert formatted == "azure--storage--connectionstring"
    
    async def test_format_secret_name_special_characters(self, mock_secret_client, mock_credential):
        """Test formatting with special characters."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        formatted = manager._format_secret_name("My@Secret#Key!")
        assert formatted == "mysecretkey"
        
        formatted = manager._format_secret_name("Test_Secret-Name.Value")
        assert formatted == "test-secret-namevalue"
    
    async def test_format_secret_name_length_limit(self, mock_secret_client, mock_credential):
        """Test secret name truncation at 127 characters."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        long_name = "a" * 150
        formatted = manager._format_secret_name(long_name)
        
        assert len(formatted) == 127
    
    async def test_format_secret_name_leading_trailing_hyphens(self, mock_secret_client, mock_credential):
        """Test removal of leading/trailing hyphens."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        formatted = manager._format_secret_name("--My-Secret--")
        assert not formatted.startswith("-")
        assert not formatted.endswith("-")
    
    async def test_extract_vault_name(self, mock_secret_client, mock_credential):
        """Test extracting vault name from URL."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        vault_name = manager._extract_vault_name()
        
        assert vault_name == "test-vault"
    
    async def test_extract_vault_name_different_formats(self, mock_secret_client, mock_credential):
        """Test vault name extraction with different URL formats."""
        manager1 = KeyVaultManager("https://my-vault-123.vault.azure.net/")
        assert manager1._extract_vault_name() == "my-vault-123"
        
        manager2 = KeyVaultManager("https://prod-vault.vault.azure.net")
        assert manager2._extract_vault_name() == "prod-vault"
    
    async def test_delete_secret_success(self, mock_secret_client, mock_credential):
        """Test deleting a secret successfully."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        await manager.delete_secret("test-secret")
        
        mock_secret_client.begin_delete_secret.assert_called_once()
    
    async def test_delete_secret_not_found(self, mock_secret_client, mock_credential):
        """Test deleting non-existent secret."""
        mock_secret_client.begin_delete_secret.side_effect = ResourceNotFoundError("Secret not found")
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        # Should handle gracefully (no exception)
        await manager.delete_secret("nonexistent-secret")
    
    async def test_delete_secret_failure(self, mock_secret_client, mock_credential):
        """Test secret deletion failure."""
        mock_secret_client.begin_delete_secret.side_effect = AzureError("Deletion failed")
        
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        with pytest.raises(KeyVaultError, match="Failed to delete secret"):
            await manager.delete_secret("test-secret")
    
    async def test_context_manager(self, mock_secret_client, mock_credential):
        """Test KeyVaultManager as async context manager."""
        async with KeyVaultManager("https://test-vault.vault.azure.net/") as manager:
            assert manager is not None
            assert isinstance(manager, KeyVaultManager)
        
        # Should close client and credential
        mock_secret_client.close.assert_called_once()
        mock_credential.close.assert_called_once()
    
    async def test_close(self, mock_secret_client, mock_credential):
        """Test explicit close method."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        await manager.close()
        
        mock_secret_client.close.assert_called_once()
        mock_credential.close.assert_called_once()


@pytest.mark.asyncio
class TestKeyVaultManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_empty_secret_name(self, mock_secret_client, mock_credential):
        """Test handling empty secret name."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        formatted = manager._format_secret_name("")
        assert formatted == ""
    
    async def test_empty_secret_value(self, mock_secret_client, mock_credential):
        """Test storing empty secret value."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        # Should handle empty value
        secret_id = await manager.store_secret("test-secret", "")
        assert secret_id is not None
    
    async def test_unicode_secret_name(self, mock_secret_client, mock_credential):
        """Test handling unicode characters in secret names."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        formatted = manager._format_secret_name("Mỹ-Sëcrét-Ñame")
        # Should remove non-ASCII characters
        assert all(c.isalnum() or c == '-' for c in formatted)
    
    async def test_store_app_settings_with_none_value(self, mock_secret_client, mock_credential):
        """Test storing app settings with None values."""
        manager = KeyVaultManager("https://test-vault.vault.azure.net/")
        
        settings = [
            AppSetting("s1", "Secret1", None, SourceType.HARDCODED, True, "test"),
            AppSetting("s2", "Secret2", "value", SourceType.HARDCODED, True, "test")
        ]
        
        # Should handle None value by converting to empty string
        references = await manager.store_app_settings(settings)
        
        assert len(references) == 2
