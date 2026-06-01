from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_host:     str = "localhost"
    db_port:     int = 3306
    db_name:     str = "lpg_distribution"   # <- was "booking_restrictions" — fixed
    db_user:     str = "root"
    db_password: str = "11362"

    secret_key:       str = "change-me"
    qr_validity_days: int = 7
    app_host:         str = "0.0.0.0"
    app_port:         int = 8000


settings = Settings()