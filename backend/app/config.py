import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./legallens.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def llm_provider(self) -> str:
        if self.ANTHROPIC_API_KEY:
            return "anthropic"
        elif self.OPENAI_API_KEY:
            return "openai"
        elif self.GEMINI_API_KEY:
            return "gemini"
        return "demo"

    def __init__(self):
        self._validate()

    def _validate(self):
        dev_secret = "legallens-dev-secret-change-in-production"
        if self.ENVIRONMENT == "production":
            if not self.JWT_SECRET or self.JWT_SECRET == dev_secret:
                raise ValueError(
                    "JWT_SECRET must be set to a secure value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            if not self.llm_provider or self.llm_provider == "demo":
                import logging
                logging.warning(
                    "No LLM API key configured. Analysis will fall back to demo mode. "
                    "Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY for full functionality."
                )
        if self.ENVIRONMENT not in ("development", "staging", "production"):
            raise ValueError(f"ENVIRONMENT must be one of: development, staging, production. Got: {self.ENVIRONMENT}")


settings = Settings()
