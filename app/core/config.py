from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobs.db"
    whatsapp_verify_token: str = "change-me"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_app_secret: str = ""
    enable_scheduler: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
