from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação MadeInLace."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MadeInLace"
    environment: str = "development"
    debug: bool = True
    port: int = 8000
    host: str = "127.0.0.1"
    secret_key: str = "madeinlace_secret_key_development_only_not_for_prod"

    # Banco de Dados MySQL Local (Aplicação)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "AntiGravity"
    db_password: str = "1234"
    db_name: str = "MADEINLACE"

    # Banco de Dados de Teste (Regra 07)
    test_db_host: str = "127.0.0.1"
    test_db_port: int = 3306
    test_db_user: str = "AntiGravity"
    test_db_password: str = "1234"
    test_db_name: str = "MADEINLACE_TEST"

    # Configurações de Envio de E-mail (Console/Mock para ambiente estudantil, SMTP TLS ou API)
    email_mode: str = "console"  # "console", "smtp", "brevo"
    email_from: str = "Made In Lace <contato@madeinlace.com>"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    brevo_api_key: str = ""
    brevo_sender_email: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def test_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.test_db_user}:{self.test_db_password}"
            f"@{self.test_db_host}:{self.test_db_port}/{self.test_db_name}?charset=utf8mb4"
        )


settings = Settings()
