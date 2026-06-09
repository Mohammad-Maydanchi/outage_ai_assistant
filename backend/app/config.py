"""App configuration — loads settings from the .env file.

Secrets live only in .env (git-ignored). This module reads them; it never
prints or logs their values.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Voice (filled in later)
    vapi_api_key: str = ""
    vapi_webhook_secret: str = ""
    vapi_phone_number_id: str = ""  # the Vapi number to call FROM
    vapi_assistant_id: str = ""  # the configured Vapi assistant

    # Ticketing (Utiliko) — filled in once Kartik provides API access.
    # Until utiliko_api_base + utiliko_api_key are set, the app uses the Stub.
    utiliko_api_base: str = ""
    utiliko_api_key: str = ""
    utiliko_tenant: str = ""
    utiliko_outage_category: str = "ISP Service – Unplanned Outage"

    # App
    database_url: str = "sqlite:///./outage.db"

    model_config = SettingsConfigDict(
        # Look for .env at the project root (one level above backend/).
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
