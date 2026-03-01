from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Unified Auth Backend"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://app_user:app_pass@postgres:5432/app_db"

    keycloak_base_url: str = "http://keycloak:8080"
    keycloak_realm: str = "integrated-id"
    keycloak_client_id: str = "be-client"
    keycloak_client_secret: str = "be-client-secret"
    keycloak_redirect_uri: str = "http://localhost:8000/docs"

    @property
    def keycloak_token_endpoint(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/"
            f"{self.keycloak_realm}/protocol/openid-connect/token"
        )

    @property
    def keycloak_userinfo_endpoint(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/"
            f"{self.keycloak_realm}/protocol/openid-connect/userinfo"
        )

    @property
    def keycloak_auth_endpoint(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/"
            f"{self.keycloak_realm}/protocol/openid-connect/auth"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

