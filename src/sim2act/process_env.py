"""Explicit environment boundaries for application subprocesses."""

import os
from collections.abc import Mapping

from sim2act.config import Settings

SYSTEM_VARIABLES = (
    "PATH",
    "SystemRoot",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
    "PYTHONUNBUFFERED",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def system_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Keep OS/encoding and explicit TLS/proxy configuration; no generic credential inheritance."""
    source = os.environ if source is None else source
    return {key: source[key] for key in SYSTEM_VARIABLES if key in source}


def application_environment(
    settings: Settings, source: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Serialize validated application settings, never test-owner or CI environment values."""
    result = system_environment(source)
    result.update(
        {
            "SIM2ACT_DATABASE_URL": settings.database_url,
            "SIM2ACT_DATA_DIR": str(settings.data_dir),
            "SIM2ACT_MODEL_MODE": settings.mode,
            "SIM2ACT_LIVE_ENABLED": str(settings.live_enabled).lower(),
            "SIM2ACT_MODEL": settings.model,
            "SIM2ACT_QUOTA_SUBJECT": settings.quota_subject,
            "SIM2ACT_RPM": str(settings.rpm),
        }
    )
    for name in (
        "max_requests",
        "max_tools",
        "max_repairs",
        "max_total_tokens",
        "max_output_tokens",
        "run_seconds",
    ):
        result["SIM2ACT_" + name.upper()] = str(getattr(settings, name))
    if settings.mode == "live" and settings.live_enabled:
        result["SIM2ACT_INTERN_TOKEN"] = settings.token
    return result
