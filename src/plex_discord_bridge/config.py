from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    discord_webhook_url: str
    otel_exporter_otlp_endpoint: str = "localhost:4317"
    otel_service_name: str = "plex-discord-bridge"


settings = Settings()
