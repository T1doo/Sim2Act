import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    data_dir: Path
    mode: str = "mock"
    live_enabled: bool = False
    model: str = "intern-s2"
    token: str = ""
    quota_subject: str = "default-intern-account"
    rpm: int = 30
    max_requests: int = 4
    max_tools: int = 4
    max_repairs: int = 1
    max_total_tokens: int = 64000
    max_output_tokens: int = 1024
    run_seconds: int = 300
    lease_seconds: int = 30

    @classmethod
    def from_env(cls):
        # Deliberately no automatic dotenv/credential discovery.
        url = os.environ.get("SIM2ACT_DATABASE_URL", "")
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("Configure a PostgreSQL application-role URL")
        s = cls(
            database_url=url,
            data_dir=Path(os.environ.get("SIM2ACT_DATA_DIR", ".sim2act")).resolve(),
            mode=os.environ.get("SIM2ACT_MODEL_MODE", "mock"),
            live_enabled=os.environ.get("SIM2ACT_LIVE_ENABLED", "false").lower() == "true",
            model=os.environ.get("SIM2ACT_MODEL", "intern-s2"),
            # A nonempty dedicated value wins; an empty template value permits the alias.
            token=os.environ.get("SIM2ACT_INTERN_TOKEN", "")
            or os.environ.get("INTERN_API_TOKEN", ""),
            quota_subject=os.environ.get("SIM2ACT_QUOTA_SUBJECT", "default-intern-account"),
            rpm=int(os.environ.get("SIM2ACT_RPM", "30")),
            **{
                k: int(os.environ.get("SIM2ACT_" + k.upper(), str(v)))
                for k, v in {
                    "max_requests": 4,
                    "max_tools": 4,
                    "max_repairs": 1,
                    "max_total_tokens": 64000,
                    "max_output_tokens": 1024,
                    "run_seconds": 300,
                }.items()
            },
        )
        if s.mode not in {"mock", "live"} or s.model != "intern-s2":
            raise ValueError("Only explicit mock or intern-s2 live is supported in F1")
        if not 1 <= s.rpm <= 30 or not s.quota_subject:
            raise ValueError("Unverified quota must be between 1 and 30 RPM")
        bounds = [
            (s.max_requests, 4),
            (s.max_tools, 4),
            (s.max_total_tokens, 64000),
            (s.max_output_tokens, 1024),
            (s.run_seconds, 300),
        ]
        if any(not 1 <= n <= cap for n, cap in bounds) or not 0 <= s.max_repairs <= 1:
            raise ValueError("Budget may only tighten F1 platform limits")
        return s
