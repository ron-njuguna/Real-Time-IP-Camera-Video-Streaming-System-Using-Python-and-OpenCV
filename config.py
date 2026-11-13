"""Configuration: everything secret or machine-specific lives outside the code.

Values are read from environment variables. For convenience a local `.env`
file (listed in .gitignore, never committed) is loaded first; real environment
variables always win over the file.
"""
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """The configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    camera_url: str
    camera_name: str = "Camera 1"
    display_width: int = 960
    max_reconnects: int = 5
    reconnect_delay: float = 1.0       # first wait; doubles each attempt
    reconnect_max_delay: float = 8.0   # cap on a single wait
    max_failed_reads: int = 5          # consecutive bad reads before "connection lost"
    screenshots_dir: str = "screenshots"
    recordings_dir: str = "recordings"


def load_dotenv(path=".env"):
    """Minimal .env reader (KEY=VALUE per line). Existing env vars are kept."""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _number(name, default, cast, minimum):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got '{raw}'.")
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value}.")
    return value


def load_config(env_file=".env"):
    load_dotenv(env_file)
    url = os.environ.get("CAMERA_URL", "").strip()
    if not url:
        raise ConfigError(
            "CAMERA_URL is not set. Copy .env.example to .env and put your "
            "camera's stream URL in it (or set the CAMERA_URL environment variable)."
        )
    return Config(
        camera_url=url,
        camera_name=os.environ.get("CAMERA_NAME", "Camera 1").strip() or "Camera 1",
        display_width=_number("DISPLAY_WIDTH", 960, int, 160),
        max_reconnects=_number("MAX_RECONNECTS", 5, int, 0),
        reconnect_delay=_number("RECONNECT_DELAY", 1.0, float, 0.1),
        max_failed_reads=_number("MAX_FAILED_READS", 5, int, 1),
    )
