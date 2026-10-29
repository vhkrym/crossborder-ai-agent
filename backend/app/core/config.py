from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = 'sqlite:///' + (ROOT / 'local.db').as_posix()
    environment: str = 'development'

@lru_cache
def get_settings() -> Settings:
    return Settings()
