"""Central configuration: model routing, paths, caps, gates and policy.

Secrets come only from environment / `.env`. Gate B (human approval of every
application) is hard-coded: there is never auto-apply.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]

# USD per 1M tokens.
PRICES: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
}

# Not configurable on purpose: submission code requires APPROVED status.
GATE_B_ALWAYS_REQUIRED = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore",
        protected_namespaces=(),
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Model routing per agent
    discovery_model: str = "claude-haiku-4-5"
    extraction_model: str = "claude-haiku-4-5"
    extraction_model_heavy: str = "claude-sonnet-4-6"
    fit_model: str = "claude-sonnet-4-6"
    tailor_model: str = "claude-opus-4-8"
    assembly_model: str = "claude-sonnet-4-6"
    cover_model: str = "claude-opus-4-8"

    # Limits
    fit_threshold: int = 60
    extraction_heavy_chars: int = 12_000
    max_tokens_default: int = 16_000
    spend_cap_usd: float = 5.00
    daily_application_cap: int = 20
    per_company_cap: int = 1

    # Gates (B is always on — see GATE_B_ALWAYS_REQUIRED)
    gate_a_enabled: bool = True
    gate_d_enabled: bool = True
    gate_c_enabled: bool = False          # browser automation needs consent
    browser_headless: bool = True
    browser_auto_submit: bool = False     # never clicks "submit" by default

    # Discovery sources
    greenhouse_boards: list[str] = Field(default_factory=list)
    lever_companies: list[str] = Field(default_factory=list)
    ashby_boards: list[str] = Field(default_factory=list)

    # ATS submission
    greenhouse_api_key: str | None = Field(default=None, alias="GREENHOUSE_API_KEY")

    # Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str | None = None

    # Autopilot policy (prepares for approval; NEVER submits)
    policy_min_score: int = 75
    policy_require_full_must: bool = True
    policy_block_open_questions: bool = True
    policy_salary_floor: float | None = None
    policy_company_allowlist: list[str] = Field(default_factory=list)
    policy_company_blocklist: list[str] = Field(default_factory=list)
    autopilot_max: int = 10

    kill_switch: bool = False             # or create data/STOP
    cover_letter_default: bool = False

    log_level: str = "WARNING"
    llm_fallbacks: dict[str, str] = Field(default_factory=lambda: {
        "claude-opus-4-8": "claude-sonnet-4-6",
        "claude-sonnet-4-6": "claude-haiku-4-5",
    })

    data_dir: Path = REPO_ROOT / "data"

    @property
    def profile_dir(self) -> Path:
        return self.data_dir / "profile"

    @property
    def profile_path(self) -> Path:
        return self.profile_dir / "master.yaml"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "crm.sqlite"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def outbox_dir(self) -> Path:
        return self.data_dir / "outbox"

    @property
    def stop_file(self) -> Path:
        return self.data_dir / "STOP"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.profile_dir, self.output_dir, self.outbox_dir):
            d.mkdir(parents=True, exist_ok=True)

    def model_for(self, agent: str) -> str:
        return {
            "discovery": self.discovery_model,
            "extraction": self.extraction_model,
            "extraction_heavy": self.extraction_model_heavy,
            "fit": self.fit_model,
            "tailor": self.tailor_model,
            "assembly": self.assembly_model,
            "cover": self.cover_model,
        }[agent]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
