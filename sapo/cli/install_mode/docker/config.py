"""Docker configuration models for Artifactory."""

import secrets
import string
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator


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
    output_dir: Path | None = Field(default=None)
    joinkey: str | None = Field(default=None)
    _passwords: dict[str, str] = {}

    @model_validator(mode="after")
    def set_default_output_dir(self) -> Self:
        """Set default output_dir based on data_dir if not provided."""
        if self.output_dir is None:
            self.output_dir = self.data_dir / "docker"
        return self

    def generate_password(self, key: str) -> str:
        """Generate a secure random password and store it.

        Args:
            key: Identifier for the password

        Returns:
            str: The generated password
        """
        if key not in self._passwords:
            # Generate a strong password with Docker/YAML-safe characters
            letters = string.ascii_letters
            digits = string.digits
            # Use only Docker/YAML-safe special characters
            # Avoiding YAML-problematic chars: #, :, [, ], {, }, , and /
            special_chars = "!@%^&*()-_=+.<>|;"
            charset = letters + digits + special_chars

            # Start with a base of minimum required characters (one of each type)
            base_password = [
                secrets.choice(string.ascii_uppercase),  # at least one uppercase letter
                secrets.choice(string.ascii_lowercase),  # at least one lowercase letter
                secrets.choice(digits),  # at least one digit
                secrets.choice(special_chars),  # at least one special
            ]

            # Fill the rest randomly from all chars (16 more to get 20 total)
            remaining_chars = [secrets.choice(charset) for _ in range(16)]

            # Combine and shuffle the full password
            password_chars = base_password + remaining_chars
            secrets.SystemRandom().shuffle(password_chars)

            # Convert to string and store
            self._passwords[key] = "".join(password_chars)
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
