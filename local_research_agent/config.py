from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = field(default=None, repr=False)
    llm_timeout_seconds: float = 45.0
    max_agent_steps: int = 6

    @property
    def knowledge_dir(self) -> Path:
        return self.data_dir / "knowledge"

    @property
    def model_enabled(self) -> bool:
        return bool(self.llm_base_url and self.llm_model)

    @property
    def model_is_remote(self) -> bool:
        if not self.llm_base_url:
            return False
        hostname = urlsplit(self.llm_base_url).hostname or ""
        if hostname.casefold() == "localhost" or hostname.casefold().endswith(".localhost"):
            return False
        try:
            return not ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return True

    @property
    def model_mode(self) -> str:
        if not self.model_enabled:
            return "offline"
        return "remote" if self.model_is_remote else "local"


def load_settings(
    environ: Mapping[str, str] | None = None,
    project_root: Path | None = None,
) -> Settings:
    root = (project_root or PROJECT_ROOT).resolve()
    if environ is None:
        load_dotenv(root / ".env", override=False)
        values: Mapping[str, str] = os.environ
    else:
        values = environ

    raw_data_dir = values.get("LOCAL_RESEARCH_DATA_DIR", str(root / ".local_data"))
    data_dir = Path(raw_data_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = root / data_dir

    base_url = values.get("LOCAL_RESEARCH_LLM_BASE_URL", "").strip().rstrip("/")
    model = values.get("LOCAL_RESEARCH_LLM_MODEL", "").strip()
    api_key = values.get("LOCAL_RESEARCH_LLM_API_KEY", "").strip() or None
    if bool(base_url) != bool(model):
        raise ValueError(
            "Set both LOCAL_RESEARCH_LLM_BASE_URL and LOCAL_RESEARCH_LLM_MODEL, or neither."
        )
    if base_url:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("LOCAL_RESEARCH_LLM_BASE_URL must be a clean HTTP(S) base URL.")
        if parsed.scheme != "https" and not _is_loopback_host(parsed.hostname):
            raise ValueError("Non-local model endpoints must use HTTPS.")

    host = values.get("LOCAL_RESEARCH_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _bounded_int(values.get("LOCAL_RESEARCH_PORT", "8000"), "port", 1, 65535)
    max_steps = _bounded_int(values.get("LOCAL_RESEARCH_MAX_STEPS", "6"), "max steps", 1, 20)
    try:
        timeout = float(values.get("LOCAL_RESEARCH_LLM_TIMEOUT_SECONDS", "45"))
    except ValueError as error:
        raise ValueError("LOCAL_RESEARCH_LLM_TIMEOUT_SECONDS must be a number.") from error
    if not 3 <= timeout <= 180:
        raise ValueError("LOCAL_RESEARCH_LLM_TIMEOUT_SECONDS must be between 3 and 180.")

    return Settings(
        data_dir=data_dir.resolve(),
        host=host,
        port=port,
        llm_base_url=base_url or None,
        llm_model=model or None,
        llm_api_key=api_key,
        llm_timeout_seconds=timeout,
        max_agent_steps=max_steps,
    )


def _bounded_int(value: str, label: str, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer.") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number


def _is_loopback_host(hostname: str) -> bool:
    if hostname.casefold() == "localhost" or hostname.casefold().endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False
