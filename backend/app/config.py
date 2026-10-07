from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    database_url: str = "sqlite:///./evidencehire.db"
    frontend_origin: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
