"""Docker configuration models for Artifactory."""

from pathlib import Path
from typing import Optional, Dict
import secrets
import string
from enum import Enum

from pydantic import BaseModel, Field, validator


class DatabaseType(str, Enum):
    """Database types supported by Artifactory."""

    POSTGRESQL = "postgresql"
    DERBY = "derby"


class DockerConfig(BaseModel):
    """Docker deployment configuration.

    Attributes:
        version: Artifactory version
        port: HTTP port
        data_dir: Data directory
        database_type: Type of database to use
        postgres_user: PostgreSQL username
        postgres_db: PostgreSQL database name
        output_dir: Output directory for generated files
        joinkey: Security join key for Artifactory
    """

    version: str
    port: int = Field(default=8082)
    data_dir: Path = Field(default=Path.home() / ".jfrog" / "artifactory")
    database_type: DatabaseType = Field(default=DatabaseType.POSTGRESQL)
    postgres_user: str = Field(default="artifactory")
    postgres_db: str = Field(default="artifactory")
    output_dir: Path = Field(default=None)
    joinkey: Optional[str] = Field(default=None)
    _passwords: Dict[str, str] = {}

    @validator("output_dir", pre=True, always=True)
    def set_default_output_dir(cls, v, values):
        """Set default output_dir based on data_dir if not provided."""
        if v is None and "data_dir" in values:
            return values["data_dir"] / "docker"
        return v

    def generate_password(self, key: str) -> str:
        """Generate a secure random password and store it.

        Args:
            key: Identifier for the password

        Returns:
            str: The generated password
        """
        if key not in self._passwords:
            # Generate a strong password with mixed characters
            charset = (
                string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>/?"
            )
            # Ensure at least 16 characters for security
            self._passwords[key] = "".join(secrets.choice(charset) for _ in range(20))
        return self._passwords[key]

    def get_password(self, key: str) -> str:
        """Retrieve a previously generated password.

        Args:
            key: Identifier for the password

        Returns:
            str: The stored password
        """
        if key not in self._passwords:
            return self.generate_password(key)
        return self._passwords[key]

    def generate_joinkey(self) -> str:
        """Generate a secure join key for Artifactory.

        Returns:
            str: A secure hex-encoded join key
        """
        if not self.joinkey:
            # Generate a hexadecimal join key (required by Artifactory)
            # Use secrets.token_hex to generate a secure hex string
            self.joinkey = secrets.token_hex(16)  # 32 characters of hex (16 bytes)
        return self.joinkey

    @property
    def use_derby(self) -> bool:
        """Check if Derby database is being used."""
        return self.database_type == DatabaseType.DERBY

    @property
    def use_postgres(self) -> bool:
        """Check if PostgreSQL database is being used."""
        return self.database_type == DatabaseType.POSTGRESQL
