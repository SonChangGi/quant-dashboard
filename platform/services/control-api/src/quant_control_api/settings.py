from __future__ import annotations

import os
from dataclasses import dataclass


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _integer(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _supabase_server_key() -> str:
    secret = os.getenv("QUANT_CONTROL_SUPABASE_SECRET_KEY", "").strip()
    legacy = os.getenv(
        "QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY",
        "",
    ).strip()
    if secret and legacy and secret != legacy:
        raise ValueError(
            "Set only QUANT_CONTROL_SUPABASE_SECRET_KEY or the legacy "
            "QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY"
        )
    return secret or legacy


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    provider: str = "disabled"
    store_backend: str = "memory"
    github_enabled: bool = False
    github_token: str = ""
    github_owner: str = "SonChangGi"
    github_repo: str = "best-factor"
    github_workflow: str = "update-dashboard.yml"
    github_ref: str = "main"
    momentum_github_owner: str = "SonChangGi"
    momentum_github_repo: str = "momentum-factor-lab"
    momentum_github_workflow: str = "controlled-analysis.yml"
    momentum_github_ref: str = "main"
    run_api_token: str = ""
    worker_callback_token: str = ""
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://sonchanggi.github.io",
    )
    supabase_dual_write_enabled: bool = False
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    dispatch_pump_enabled: bool = False
    dispatch_lease_seconds: int = 30
    dispatch_max_attempts: int = 5
    dispatch_retry_base_seconds: int = 2
    dispatch_retry_max_seconds: int = 300
    dispatch_poll_milliseconds: int = 1000
    dispatch_batch_size: int = 4
    worker_result_timeout_seconds: int = 14400
    worker_expiry_scan_seconds: int = 30
    worker_expiry_batch_size: int = 20

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            environment=os.getenv("QUANT_CONTROL_ENV", "development").strip().lower(),
            provider=os.getenv("QUANT_CONTROL_PROVIDER", "disabled").strip().lower(),
            store_backend=os.getenv("QUANT_CONTROL_STORE", "memory").strip().lower(),
            github_enabled=_boolean("QUANT_CONTROL_GITHUB_ENABLED"),
            github_token=os.getenv("QUANT_CONTROL_GITHUB_TOKEN", "").strip(),
            github_owner=os.getenv("QUANT_CONTROL_GITHUB_OWNER", "SonChangGi").strip(),
            github_repo=os.getenv("QUANT_CONTROL_GITHUB_REPO", "best-factor").strip(),
            github_workflow=os.getenv("QUANT_CONTROL_GITHUB_WORKFLOW", "update-dashboard.yml").strip(),
            github_ref=os.getenv("QUANT_CONTROL_GITHUB_REF", "main").strip(),
            momentum_github_owner=os.getenv(
                "QUANT_CONTROL_MOMENTUM_GITHUB_OWNER",
                "SonChangGi",
            ).strip(),
            momentum_github_repo=os.getenv(
                "QUANT_CONTROL_MOMENTUM_GITHUB_REPO",
                "momentum-factor-lab",
            ).strip(),
            momentum_github_workflow=os.getenv(
                "QUANT_CONTROL_MOMENTUM_GITHUB_WORKFLOW",
                "controlled-analysis.yml",
            ).strip(),
            momentum_github_ref=os.getenv(
                "QUANT_CONTROL_MOMENTUM_GITHUB_REF",
                "main",
            ).strip(),
            run_api_token=os.getenv("QUANT_CONTROL_RUN_API_TOKEN", "").strip(),
            worker_callback_token=os.getenv("QUANT_CONTROL_WORKER_CALLBACK_TOKEN", "").strip(),
            allowed_origins=tuple(
                origin.strip().rstrip("/")
                for origin in os.getenv(
                    "QUANT_CONTROL_ALLOWED_ORIGINS",
                    "http://127.0.0.1:5173,http://localhost:5173,https://sonchanggi.github.io",
                ).split(",")
                if origin.strip()
            ),
            supabase_dual_write_enabled=_boolean("QUANT_CONTROL_SUPABASE_DUAL_WRITE_ENABLED"),
            supabase_url=os.getenv("QUANT_CONTROL_SUPABASE_URL", "").strip().rstrip("/"),
            supabase_service_role_key=_supabase_server_key(),
            dispatch_pump_enabled=_boolean("QUANT_CONTROL_DISPATCH_PUMP_ENABLED"),
            dispatch_lease_seconds=_integer("QUANT_CONTROL_DISPATCH_LEASE_SECONDS", 30),
            dispatch_max_attempts=_integer("QUANT_CONTROL_DISPATCH_MAX_ATTEMPTS", 5),
            dispatch_retry_base_seconds=_integer(
                "QUANT_CONTROL_DISPATCH_RETRY_BASE_SECONDS",
                2,
            ),
            dispatch_retry_max_seconds=_integer(
                "QUANT_CONTROL_DISPATCH_RETRY_MAX_SECONDS",
                300,
            ),
            dispatch_poll_milliseconds=_integer(
                "QUANT_CONTROL_DISPATCH_POLL_MILLISECONDS",
                1000,
            ),
            dispatch_batch_size=_integer("QUANT_CONTROL_DISPATCH_BATCH_SIZE", 4),
            worker_result_timeout_seconds=_integer(
                "QUANT_CONTROL_WORKER_RESULT_TIMEOUT_SECONDS",
                14400,
            ),
            worker_expiry_scan_seconds=_integer(
                "QUANT_CONTROL_WORKER_EXPIRY_SCAN_SECONDS",
                30,
            ),
            worker_expiry_batch_size=_integer(
                "QUANT_CONTROL_WORKER_EXPIRY_BATCH_SIZE",
                20,
            ),
        )

    def validate(self) -> None:
        if self.environment not in {
            "development",
            "test",
            "staging",
            "production",
        }:
            raise ValueError(
                "QUANT_CONTROL_ENV must be development, test, staging, or production"
            )
        if self.provider not in {"disabled", "github-actions"}:
            raise ValueError("QUANT_CONTROL_PROVIDER must be disabled or github-actions")
        if self.store_backend not in {"memory", "supabase"}:
            raise ValueError("QUANT_CONTROL_STORE must be memory or supabase")
        if not 5 <= self.dispatch_lease_seconds <= 300:
            raise ValueError("QUANT_CONTROL_DISPATCH_LEASE_SECONDS must be between 5 and 300")
        if not 1 <= self.dispatch_max_attempts <= 20:
            raise ValueError("QUANT_CONTROL_DISPATCH_MAX_ATTEMPTS must be between 1 and 20")
        if not 1 <= self.dispatch_retry_base_seconds <= self.dispatch_retry_max_seconds <= 3600:
            raise ValueError("dispatch retry seconds must satisfy 1 <= base <= max <= 3600")
        if not 100 <= self.dispatch_poll_milliseconds <= 60000:
            raise ValueError("QUANT_CONTROL_DISPATCH_POLL_MILLISECONDS must be between 100 and 60000")
        if not 1 <= self.dispatch_batch_size <= 50:
            raise ValueError("QUANT_CONTROL_DISPATCH_BATCH_SIZE must be between 1 and 50")
        if not 300 <= self.worker_result_timeout_seconds <= 86400:
            raise ValueError("QUANT_CONTROL_WORKER_RESULT_TIMEOUT_SECONDS must be between 300 and 86400")
        if not 5 <= self.worker_expiry_scan_seconds <= 3600:
            raise ValueError("QUANT_CONTROL_WORKER_EXPIRY_SCAN_SECONDS must be between 5 and 3600")
        if not 1 <= self.worker_expiry_batch_size <= 100:
            raise ValueError("QUANT_CONTROL_WORKER_EXPIRY_BATCH_SIZE must be between 1 and 100")
        if self.environment == "production" and self.store_backend != "supabase":
            raise ValueError("Production requires QUANT_CONTROL_STORE=supabase")
        if self.provider == "github-actions":
            if not self.github_enabled:
                raise ValueError("GitHub Actions provider requires QUANT_CONTROL_GITHUB_ENABLED=true")
            missing = [
                label
                for label, value in (
                    ("QUANT_CONTROL_GITHUB_TOKEN", self.github_token),
                    ("QUANT_CONTROL_GITHUB_OWNER", self.github_owner),
                    ("QUANT_CONTROL_GITHUB_REPO", self.github_repo),
                    ("QUANT_CONTROL_GITHUB_WORKFLOW", self.github_workflow),
                    ("QUANT_CONTROL_GITHUB_REF", self.github_ref),
                    (
                        "QUANT_CONTROL_MOMENTUM_GITHUB_OWNER",
                        self.momentum_github_owner,
                    ),
                    (
                        "QUANT_CONTROL_MOMENTUM_GITHUB_REPO",
                        self.momentum_github_repo,
                    ),
                    (
                        "QUANT_CONTROL_MOMENTUM_GITHUB_WORKFLOW",
                        self.momentum_github_workflow,
                    ),
                    (
                        "QUANT_CONTROL_MOMENTUM_GITHUB_REF",
                        self.momentum_github_ref,
                    ),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"GitHub Actions provider is missing: {', '.join(missing)}")
            if not self.run_api_token:
                raise ValueError("GitHub Actions provider requires QUANT_CONTROL_RUN_API_TOKEN")
            if not self.worker_callback_token:
                raise ValueError("GitHub Actions provider requires QUANT_CONTROL_WORKER_CALLBACK_TOKEN")
            if self.store_backend != "supabase":
                raise ValueError(
                    "GitHub Actions provider requires durable "
                    "QUANT_CONTROL_STORE=supabase"
                )
            if not self.dispatch_pump_enabled:
                raise ValueError(
                    "GitHub Actions provider requires "
                    "QUANT_CONTROL_DISPATCH_PUMP_ENABLED=true"
                )
        if self.supabase_dual_write_enabled or self.store_backend == "supabase":
            missing = [
                label
                for label, value in (
                    ("QUANT_CONTROL_SUPABASE_URL", self.supabase_url),
                    (
                        "QUANT_CONTROL_SUPABASE_SECRET_KEY (or legacy QUANT_CONTROL_SUPABASE_SERVICE_ROLE_KEY)",
                        self.supabase_service_role_key,
                    ),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"Supabase configuration is missing: {', '.join(missing)}")
