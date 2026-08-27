from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
ENV_CANDIDATES = (BACKEND_DIR / ".env", APP_DIR / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    xbet_url: str
    xbet_login: str | None
    xbet_password: str | None
    browser_slow_mo: int
    profile_dir: Path
    diagnostics_dir: Path

    @property
    def has_credentials(self) -> bool:
        return bool(self.xbet_login and self.xbet_password)


def _read_slow_mo() -> int:
    raw_value = os.getenv("BROWSER_SLOW_MO", "200")
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("BROWSER_SLOW_MO должен быть целым числом") from exc

    if value < 0:
        raise RuntimeError("BROWSER_SLOW_MO не может быть отрицательным")
    return value


def get_settings() -> Settings:
    env_file = next((path for path in ENV_CANDIDATES if path.is_file()), ENV_CANDIDATES[0])
    load_dotenv(dotenv_path=env_file, override=False)
    return Settings(
        xbet_url=os.getenv("XBET_URL", "https://1xlite-02216.pro/ru").strip(),
        xbet_login=os.getenv("XBET_LOGIN") or None,
        xbet_password=os.getenv("XBET_PASSWORD") or None,
        browser_slow_mo=_read_slow_mo(),
        profile_dir=BACKEND_DIR / "playwright-profile",
        diagnostics_dir=BACKEND_DIR / "diagnostics",
    )
