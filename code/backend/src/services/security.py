"""
Enterprise security services including encryption, secret management, and secure configuration
"""
import os
import json
import base64
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
import cryptography
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
import boto3
from azure.keyvault import KeyVaultClient
from azure.identity import DefaultAzureCredential
import hvac  # HashiCorp Vault client

from ..config import settings
from ..utils.exceptions import ConfigurationException, ValidationError
from .audit import audit_service

logger = logging.getLogger(__name__)


class EncryptionService:
    """Enterprise-grade encryption service with multiple key management strategies"""

    def __init__(self):
        self.key_rotation_interval = timedelta(days=30)
        self.master_key_cache: Dict[str, Dict[str, Any]] = {}
        self.data_keys: Dict[str, bytes] = {}

    def generate_master_key(self) -> bytes:
        """Generate a new master encryption key"""
        return Fernet.generate_key()

    def derive_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt_data(self, data: Union[str, bytes], key_id: str = "default") -> Dict[str, Any]:
        """Encrypt data with envelope encryption"""
        # Get or create data key
        data_key = self._get_data_key(key_id)

        # Generate DEK (Data Encryption Key)
        dek = Fernet.generate_key()
        fernet = Fernet(dek)

        # Encrypt the data
        if isinstance(data, str):
            data = data.encode()
        encrypted_data = fernet.encrypt(data)

        # Encrypt the DEK with the master key
        encrypted_dek = self._encrypt_with_master_key(dek, key_id)

        return {
            "encrypted_data": base64.b64encode(encrypted_data).decode(),
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "key_id": key_id,
            "algorithm": "AES256-GCM",
            "timestamp": datetime.utcnow().isoformat()
        }

    def decrypt_data(self, encrypted_package: Dict[str, Any]) -> bytes:
        """Decrypt data using envelope encryption"""
        key_id = encrypted_package["key_id"]

        # Decrypt the DEK
        encrypted_dek = base64.b64decode(encrypted_package["encrypted_dek"])
        dek = self._decrypt_with_master_key(encrypted_dek, key_id)

        # Decrypt the data
        fernet = Fernet(dek)
        encrypted_data = base64.b64decode(encrypted_package["encrypted_data"])

        return fernet.decrypt(encrypted_data)

    def _get_data_key(self, key_id: str) -> bytes:
        """Get or create a data key for envelope encryption"""
        if key_id not in self.data_keys:
            self.data_keys[key_id] = Fernet.generate_key()
        return self.data_keys[key_id]

    def _encrypt_with_master_key(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data with master key"""
        master_key = self._get_master_key(key_id)
        fernet = Fernet(master_key)
        return fernet.encrypt(data)

    def _decrypt_with_master_key(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data with master key"""
        master_key = self._get_master_key(key_id)
        fernet = Fernet(master_key)
        return fernet.decrypt(encrypted_data)

    def _get_master_key(self, key_id: str) -> bytes:
        """Get master key, handling rotation and caching"""
        cache_key = f"master_{key_id}"

        if cache_key in self.master_key_cache:
            cached = self.master_key_cache[cache_key]
            if datetime.utcnow() - cached["created"] < self.key_rotation_interval:
                return cached["key"]

        # Generate new master key
        new_key = self.generate_master_key()
        self.master_key_cache[cache_key] = {
            "key": new_key,
            "created": datetime.utcnow(),
            "key_id": key_id
        }

        return new_key

    def rotate_keys(self, key_id: str = None):
        """Rotate encryption keys"""
        if key_id:
            # Rotate specific key
            cache_key = f"master_{key_id}"
            if cache_key in self.master_key_cache:
                del self.master_key_cache[cache_key]
            if key_id in self.data_keys:
                del self.data_keys[key_id]
        else:
            # Rotate all keys
            self.master_key_cache.clear()
            self.data_keys.clear()

        logger.info(f"Encryption keys rotated for key_id: {key_id or 'all'}")


class SecretManager:
    """Unified secret management across multiple backends"""

    def __init__(self):
        self.backend = self._initialize_backend()
        self.encryption_service = EncryptionService()
        self.secret_cache: Dict[str, Dict[str, Any]] = {}

    def _initialize_backend(self):
        """Initialize the appropriate secret backend"""
        backend_type = os.getenv("SECRET_BACKEND", "local")

        if backend_type == "aws":
            return AWSSecretManager()
        elif backend_type == "azure":
            return AzureSecretManager()
        elif backend_type == "vault":
            return VaultSecretManager()
        else:
            return LocalSecretManager()

    async def store_secret(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> str:
        """Store a secret securely"""
        # Encrypt the secret
        encrypted_value = self.encryption_service.encrypt_data(json.dumps(value))

        # Store in backend
        secret_id = await self.backend.store_secret(key, encrypted_value, metadata)

        # Cache the secret
        self.secret_cache[key] = {
            "value": value,
            "encrypted": encrypted_value,
            "metadata": metadata or {},
            "stored_at": datetime.utcnow()
        }

        # Audit the operation
        await audit_service.log_event_async(
            audit_service.AuditEvent(
                action="secret_stored",
                resource_type="secret",
                resource_id=secret_id,
                success=True,
                metadata={"key": key}
            )
        )

        return secret_id

    async def retrieve_secret(self, key: str) -> Any:
        """Retrieve and decrypt a secret"""
        # Check cache first
        if key in self.secret_cache:
            cached = self.secret_cache[key]
            if datetime.utcnow() - cached["stored_at"] < timedelta(minutes=5):
                return cached["value"]

        # Retrieve from backend
        encrypted_value = await self.backend.retrieve_secret(key)

        # Decrypt the secret
        decrypted_data = self.encryption_service.decrypt_data(encrypted_value)
        value = json.loads(decrypted_data.decode())

        # Update cache
        self.secret_cache[key] = {
            "value": value,
            "encrypted": encrypted_value,
            "stored_at": datetime.utcnow()
        }

        return value

    async def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        success = await self.backend.delete_secret(key)

        if success:
            # Remove from cache
            self.secret_cache.pop(key, None)

            # Audit the operation
            await audit_service.log_event_async(
                audit_service.AuditEvent(
                    action="secret_deleted",
                    resource_type="secret",
                    resource_id=key,
                    success=True
                )
            )

        return success

    async def list_secrets(self, prefix: str = None) -> List[str]:
        """List available secrets"""
        return await self.backend.list_secrets(prefix)

    async def rotate_secret(self, key: str) -> bool:
        """Rotate a secret with new encryption"""
        # Get current value
        current_value = await self.retrieve_secret(key)

        # Delete old secret
        await self.delete_secret(key)

        # Store with new encryption
        await self.store_secret(key, current_value)

        # Rotate encryption keys
        self.encryption_service.rotate_keys(key)

        return True


class LocalSecretManager:
    """Local file-based secret storage for development"""

    def __init__(self):
        self.secret_dir = Path("./secrets")
        self.secret_dir.mkdir(exist_ok=True)

    async def store_secret(self, key: str, encrypted_value: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Store secret in local file"""
        secret_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        secret_file = self.secret_dir / f"{secret_id}.json"

        data = {
            "key": key,
            "encrypted_value": encrypted_value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }

        with open(secret_file, 'w') as f:
            json.dump(data, f, indent=2)

        return secret_id

    async def retrieve_secret(self, key: str) -> Dict[str, Any]:
        """Retrieve secret from local file"""
        secret_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        secret_file = self.secret_dir / f"{secret_id}.json"

        if not secret_file.exists():
            raise ValueError(f"Secret not found: {key}")

        with open(secret_file, 'r') as f:
            data = json.load(f)

        return data["encrypted_value"]

    async def delete_secret(self, key: str) -> bool:
        """Delete secret file"""
        secret_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        secret_file = self.secret_dir / f"{secret_id}.json"

        if secret_file.exists():
            secret_file.unlink()
            return True
        return False

    async def list_secrets(self, prefix: str = None) -> List[str]:
        """List secret files"""
        secrets = []
        for secret_file in self.secret_dir.glob("*.json"):
            with open(secret_file, 'r') as f:
                data = json.load(f)
                key = data["key"]
                if not prefix or key.startswith(prefix):
                    secrets.append(key)
        return secrets


class AWSSecretManager:
    """AWS Secrets Manager integration"""

    def __init__(self):
        self.client = boto3.client('secretsmanager')

    async def store_secret(self, key: str, encrypted_value: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Store secret in AWS Secrets Manager"""
        response = self.client.create_secret(
            Name=key,
            SecretString=json.dumps(encrypted_value),
            Tags=[{"Key": k, "Value": str(v)} for k, v in (metadata or {}).items()]
        )
        return response['ARN']

    async def retrieve_secret(self, key: str) -> Dict[str, Any]:
        """Retrieve secret from AWS Secrets Manager"""
        response = self.client.get_secret_value(SecretId=key)
        return json.loads(response['SecretString'])

    async def delete_secret(self, key: str) -> bool:
        """Delete secret from AWS Secrets Manager"""
        try:
            self.client.delete_secret(SecretId=key, ForceDeleteWithoutRecovery=True)
            return True
        except Exception:
            return False

    async def list_secrets(self, prefix: str = None) -> List[str]:
        """List secrets from AWS Secrets Manager"""
        secrets = []
        paginator = self.client.get_paginator('list_secrets')

        for page in paginator.paginate():
            for secret in page['SecretList']:
                name = secret['Name']
                if not prefix or name.startswith(prefix):
                    secrets.append(name)

        return secrets


class AzureSecretManager:
    """Azure Key Vault integration"""

    def __init__(self):
        vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        credential = DefaultAzureCredential()
        self.client = KeyVaultClient(credential, vault_url)

    async def store_secret(self, key: str, encrypted_value: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Store secret in Azure Key Vault"""
        secret_value = json.dumps(encrypted_value)
        result = self.client.set_secret(key, secret_value)
        return result.id

    async def retrieve_secret(self, key: str) -> Dict[str, Any]:
        """Retrieve secret from Azure Key Vault"""
        result = self.client.get_secret(key)
        return json.loads(result.value)

    async def delete_secret(self, key: str) -> bool:
        """Delete secret from Azure Key Vault"""
        try:
            self.client.delete_secret(key)
            return True
        except Exception:
            return False

    async def list_secrets(self, prefix: str = None) -> List[str]:
        """List secrets from Azure Key Vault"""
        secrets = []
        result = self.client.get_secrets()

        for secret in result:
            name = secret.id.split('/')[-1]
            if not prefix or name.startswith(prefix):
                secrets.append(name)

        return secrets


class VaultSecretManager:
    """HashiCorp Vault integration"""

    def __init__(self):
        vault_url = os.getenv("VAULT_URL", "http://localhost:8200")
        self.client = hvac.Client(url=vault_url)

        # Authenticate if token not provided
        if not self.client.is_authenticated():
            token = os.getenv("VAULT_TOKEN")
            if token:
                self.client.token = token
            else:
                # Try other auth methods
                pass

    async def store_secret(self, key: str, encrypted_value: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Store secret in HashiCorp Vault"""
        path = f"secret/{key}"
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=encrypted_value
        )
        return path

    async def retrieve_secret(self, key: str) -> Dict[str, Any]:
        """Retrieve secret from HashiCorp Vault"""
        path = f"secret/{key}"
        result = self.client.secrets.kv.v2.read_secret_version(path=path)
        return result['data']['data']

    async def delete_secret(self, key: str) -> bool:
        """Delete secret from HashiCorp Vault"""
        try:
            path = f"secret/{key}"
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
            return True
        except Exception:
            return False

    async def list_secrets(self, prefix: str = None) -> List[str]:
        """List secrets from HashiCorp Vault"""
        try:
            result = self.client.secrets.kv.v2.list_secrets_version(path="secret/")
            secrets = result['data']['keys']

            if prefix:
                secrets = [s for s in secrets if s.startswith(prefix)]

            return secrets
        except Exception:
            return []


class SecureConfigManager:
    """Secure configuration management with encryption and validation"""

    def __init__(self):
        self.secret_manager = SecretManager()
        self.encryption_service = EncryptionService()
        self.config_cache: Dict[str, Any] = {}
        self.config_validators: Dict[str, callable] = {}

    def add_validator(self, config_key: str, validator: callable):
        """Add configuration validator"""
        self.config_validators[config_key] = validator

    async def set_secure_config(self, key: str, value: Any, encrypt: bool = True) -> bool:
        """Set a configuration value securely"""
        # Validate the configuration
        if key in self.config_validators:
            try:
                self.config_validators[key](value)
            except Exception as e:
                raise ValidationError(f"Configuration validation failed for {key}: {e}")

        # Store securely
        if encrypt:
            await self.secret_manager.store_secret(f"config_{key}", value)
        else:
            # Store in environment or config file
            os.environ[f"SECURE_{key.upper()}"] = str(value)

        # Update cache
        self.config_cache[key] = value

        return True

    async def get_secure_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value securely"""
        # Check cache first
        if key in self.config_cache:
            return self.config_cache[key]

        # Try to get from secrets
        try:
            value = await self.secret_manager.retrieve_secret(f"config_{key}")
            self.config_cache[key] = value
            return value
        except Exception:
            pass

        # Try environment variable
        env_value = os.getenv(f"SECURE_{key.upper()}")
        if env_value:
            # Try to parse as JSON
            try:
                value = json.loads(env_value)
            except:
                value = env_value

            self.config_cache[key] = value
            return value

        return default

    async def rotate_config_keys(self):
        """Rotate encryption keys for all configuration values"""
        secrets = await self.secret_manager.list_secrets("config_")
        for secret_key in secrets:
            await self.secret_manager.rotate_secret(secret_key)

        # Clear cache to force reload
        self.config_cache.clear()

    def validate_database_url(self, url: str):
        """Validate database URL format"""
        if not url.startswith(('postgresql://', 'mysql://', 'sqlite:///')):
            raise ValueError("Invalid database URL format")

    def validate_api_key(self, key: str):
        """Validate API key format"""
        if not isinstance(key, str) or len(key) < 20:
            raise ValueError("API key must be at least 20 characters long")

    def validate_encryption_key(self, key: str):
        """Validate encryption key format"""
        try:
            # Try to decode as base64
            base64.b64decode(key)
        except Exception:
            raise ValueError("Invalid encryption key format")


class APIKeyManager:
    """Secure API key management with rotation and validation"""

    def __init__(self):
        self.secret_manager = SecretManager()
        self.key_rotation_days = int(os.getenv("API_KEY_ROTATION_DAYS", "90"))

    async def generate_api_key(self, name: str, permissions: List[str] = None) -> Dict[str, Any]:
        """Generate a new API key"""
        # Generate cryptographically secure key
        key = secrets.token_urlsafe(32)

        key_data = {
            "key": key,
            "name": name,
            "permissions": permissions or [],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=self.key_rotation_days)).isoformat(),
            "status": "active"
        }

        # Store securely
        secret_id = await self.secret_manager.store_secret(f"api_key_{name}", key_data)

        return {
            "id": secret_id,
            "key": key,
            "name": name,
            "expires_at": key_data["expires_at"]
        }

    async def validate_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key"""
        # Find the key in secrets
        secrets = await self.secret_manager.list_secrets("api_key_")

        for secret_name in secrets:
            try:
                key_data = await self.secret_manager.retrieve_secret(secret_name)

                if key_data["key"] == key:
                    # Check if expired
                    expires_at = datetime.fromisoformat(key_data["expires_at"])
                    if datetime.utcnow() > expires_at:
                        return None

                    # Check if active
                    if key_data.get("status") != "active":
                        return None

                    return key_data
            except Exception:
                continue

        return None

    async def rotate_api_key(self, name: str) -> Dict[str, Any]:
        """Rotate an existing API key"""
        # Get current key data
        current_data = await self.secret_manager.retrieve_secret(f"api_key_{name}")

        # Generate new key
        new_key = secrets.token_urlsafe(32)

        # Update key data
        current_data["key"] = new_key
        current_data["rotated_at"] = datetime.utcnow().isoformat()
        current_data["previous_key"] = current_data.get("key")

        # Store updated data
        await self.secret_manager.store_secret(f"api_key_{name}", current_data)

        return {
            "name": name,
            "new_key": new_key,
            "rotated_at": current_data["rotated_at"]
        }

    async def revoke_api_key(self, name: str) -> bool:
        """Revoke an API key"""
        try:
            key_data = await self.secret_manager.retrieve_secret(f"api_key_{name}")
            key_data["status"] = "revoked"
            key_data["revoked_at"] = datetime.utcnow().isoformat()

            await self.secret_manager.store_secret(f"api_key_{name}", key_data)
            return True
        except Exception:
            return False

    async def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys"""
        secrets = await self.secret_manager.list_secrets("api_key_")
        keys = []

        for secret_name in secrets:
            try:
                key_data = await self.secret_manager.retrieve_secret(secret_name)
                keys.append({
                    "name": key_data["name"],
                    "created_at": key_data["created_at"],
                    "expires_at": key_data["expires_at"],
                    "status": key_data.get("status", "unknown"),
                    "permissions": key_data.get("permissions", [])
                })
            except Exception:
                continue

        return keys


# Global instances
encryption_service = EncryptionService()
secret_manager = SecretManager()
secure_config_manager = SecureConfigManager()
api_key_manager = APIKeyManager()

# Add configuration validators
secure_config_manager.add_validator("database_url", secure_config_manager.validate_database_url)
secure_config_manager.add_validator("api_key", secure_config_manager.validate_api_key)
secure_config_manager.add_validator("encryption_key", secure_config_manager.validate_encryption_key)