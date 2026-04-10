"""
Configuration management for the Water Utility Chatbot.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration is invalid."""


class Config:
    """Application configuration."""

    def __init__(self) -> None:
        # Load .env file
        env_path = Path(__file__).resolve().parent.parent / ".env"
        # Override existing process env vars so edits to .env take effect on reload.
        # Use utf-8-sig to tolerate BOM markers (common with Windows editors).
        load_dotenv(dotenv_path=env_path, override=True, encoding="utf-8-sig")

        # Groq
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.llm_provider = "groq"
        # NOTE: Groq periodically deprecates models. Keep a modern default here.
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        # Server
        self.host = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "8000"))
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Rate limiting
        self.rate_limit_enabled = (
            os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
        )
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

        # CORS
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://127.0.0.1:8000,http://127.0.0.1:5500,http://localhost:5500",
            ).split(",")
            if origin.strip()
        ]

        # Always allow the Vite dev server origin(s) for local development,
        # even if the env var is missing or out-of-date.
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            if origin not in self.cors_origins:
                self.cors_origins.append(origin)

        self._validate()

    def _validate(self) -> None:
        errors = []

        # Groq-only enforcement
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY missing")

        if not (1 <= self.port <= 65535):
            errors.append(f"PORT must be between 1 and 65535, got {self.port}")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            errors.append(
                f"LOG_LEVEL must be one of {sorted(valid_levels)}, got {self.log_level}"
            )

        if errors:
            raise ConfigError("\n".join(errors))

    def __repr__(self) -> str:
        return (
            f"Config(host={self.host}, port={self.port}, "
            f"provider={self.llm_provider}, model={self.groq_model}, debug={self.debug})"
        )


try:
    config = Config()
except ConfigError as e:
    print(f"Configuration Error: {e}")
    raise
