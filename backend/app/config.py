"""Configuración del backend — lee de variables de entorno / .env."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Busca .env en la raíz del repo (un nivel arriba de backend/)
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # ── OCR ──────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # ── Base de datos ────────────────────────────────────
    # postgresql://user:pass@host:port/dbname  (Supabase Connection string)
    database_url: str = ""

    # ── CORS ─────────────────────────────────────────────
    # URLs del frontend separadas por coma (Vercel, localhost)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
