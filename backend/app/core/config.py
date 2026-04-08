from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CureCompass API"
    environment: str = "development"
    api_v1_prefix: str = "/api"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/curecompass"
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:3000"

    openai_api_key: str = ""
    openai_responses_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    # After ingestion adds new research_items, start plain-language AI enrichment in the background.
    auto_enrich_after_ingest: bool = True
    # Max items to enrich per run (newest first). Use 0 for no limit (can be costly).
    auto_enrich_max_items: int = 50

    ncbi_api_key: str = ""
    ncbi_tool_name: str = "CureCompass"
    ncbi_contact_email: str = "you@example.com"
    clinical_trials_base_url: str = "https://clinicaltrials.gov/api/v2"
    pubmed_eutils_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    openfda_base_url: str = "https://api.fda.gov"

    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@curecompass.app"
    # If set, admin reports endpoint is restricted to this exact admin email.
    admin_owner_email: str = ""
    # If set, Reply-To on password-reset mail (optional).
    smtp_reply_to: str = ""
    # Reply-To for research-briefing email only. If empty, falls back to smtp_reply_to.
    # Use an address that is NOT your monitored inbox (see .env.example). Plain "Reply" targets this.
    smtp_digest_reply_to: str = ""
    password_reset_token_hours: int = 2

    # Private uploads (PDF text extraction MVP). Treat directory as sensitive; restrict filesystem permissions in production.
    private_documents_dir: str = "./data/private_documents"
    private_document_max_bytes: int = 5_242_880  # 5 MiB
    private_document_max_extracted_chars: int = 200_000

    # Skip re-running external ingestion for the same condition if a run succeeded recently (non-admin users).
    ingestion_cooldown_hours: int = 4


settings = Settings()
