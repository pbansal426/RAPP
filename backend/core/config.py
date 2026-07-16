from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings parses .env into the Settings object below, but doesn't
# populate os.environ for other consumers. genai.Client() is meant to pick up
# GEMINI_API_KEY from the environment automatically (per google-genai's own
# convention), so we load .env into the process environment explicitly.
load_dotenv()

# Environments where magic-link auth must actually deliver email rather than
# falling back to handing the link back in the API response -- see
# backend/routers/auth.py's request_link() and Settings._require_resend_key_outside_dev
# below.
EMAIL_REQUIRED_ENVIRONMENTS = frozenset({"staging", "production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "rapp-backend"
    debug: bool = False
    port: int = 8000
    host: str = "127.0.0.1"

    # Environment: "development" (default), "test", "staging", or
    # "production". Used to force mock VectorStore/Gemini behavior so
    # CI/test runs never dial out over the network, regardless of what
    # secrets happen to be present -- and (see the model_validator below)
    # to require real email delivery to be configured before a
    # staging/production process is allowed to start at all.
    environment: str = "development"

    # API endpoints and URLs
    nhtsa_base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles"
    # Separate host from nhtsa_base_url -- vpic.nhtsa.dot.gov (VIN decode)
    # and api.nhtsa.gov (recalls/complaints) are different NHTSA services.
    nhtsa_safety_api_base: str = "https://api.nhtsa.gov"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Keys / Secrets (Stubbed / optional)
    gemini_api_key: str | None = None
    # PostHog product analytics. Unset by default -- backend/services/analytics.py
    # and the frontend wrapper both no-op entirely when the key is absent, so
    # events only flow once a human adds the keys in a deployed environment.
    posthog_api_key: str | None = None
    posthog_host: str = "https://us.i.posthog.com"
    # Magic-link auth email delivery (Resend). Unset by default -- see
    # backend/services/email.py: request_link() falls back to returning the
    # link directly in the API response (dev-mode), so auth works with zero
    # setup and zero cost until this is configured. Resend's free tier
    # (3,000 emails/mo) only lets the unverified onboarding@resend.dev
    # sender deliver to the account's own registered email; sending to
    # arbitrary real users requires verifying a custom domain in Resend.
    resend_api_key: str | None = None
    email_from: str = "RAPP <onboarding@resend.dev>"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_single: str = "price_xxx"
    stripe_price_vin_pass: str = "price_xxx"

    # Polar Merchant of Record (MoR) Settings
    polar_access_token: str | None = None
    polar_webhook_secret: str | None = None
    polar_product_id_tier_1: str = "prod_tier1"
    polar_product_id_tier_2: str = "prod_tier2"
    polar_product_id_tier_3: str = "prod_tier3"
    polar_product_id_annual: str = "prod_annual"
    # Amazon Associates tracking ID (e.g. "rapp-20"). Unset by default -- see
    # backend/pricing.py's _search_url(), which only appends the `tag` param
    # when this is configured. Purely additive revenue: doesn't touch
    # payment processing, doesn't cost anything to leave unset.
    amazon_associate_tag: str | None = None

    # RAG settings
    vector_store: str = "chromadb"
    chroma_db_path: str = "./data/chroma_db"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3099"

    # Logging
    log_format: str = "dev"

    # Database & Authentication (SQLite for local dev; point at a Postgres
    # URL in production). jwt_secret_key's default is local-dev only --
    # always set a real secret via the environment in any deployed environment.
    database_url: str | None = None
    jwt_secret_key: str = "supersecretkeyforlocaldev"

    @model_validator(mode="after")
    def _require_resend_key_outside_dev(self) -> "Settings":
        if self.environment in EMAIL_REQUIRED_ENVIRONMENTS:
            if not self.resend_api_key:
                raise ValueError(
                    f"RESEND_API_KEY must be set when ENVIRONMENT={self.environment!r} -- "
                    "magic-link auth is not allowed to fall back to leaking the sign-in "
                    "link in the API response outside development/test."
                )
            if "resend.dev" in self.email_from:
                raise ValueError(
                    f"email_from is still Resend's sandbox address ({self.email_from!r}) "
                    f"in ENVIRONMENT={self.environment!r} -- Resend's sandbox sender only "
                    "delivers to the account owner's own inbox, so every real user's "
                    "magic-link email would silently fail. Verify a custom domain with "
                    "Resend and set EMAIL_FROM to an address on that domain before deploying."
                )
        return self

    @property
    def is_test_mode(self) -> bool:
        """True in CI or explicit test runs. Callers use this to force mock
        VectorStore/Gemini behavior so no live network call happens even if
        GEMINI_API_KEY or a real VECTOR_STORE value is set in the environment."""
        import os

        return self.environment == "test" or os.environ.get("CI", "").lower() == "true"


settings = Settings()
