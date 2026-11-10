"""Application configuration and secret handling.

Usage:
    config = AppConfig()  # loads from .env automatically
    verifier = NtsPublicApiVerifier(service_key=config.nts_api_key)
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv  # type: ignore[import]


class SecretStr:
    """A string that redacts itself in repr/str to prevent accidental key leakage.

    Use get_secret_value() to access the actual value only when needed.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretStr(***)"

    def __str__(self) -> str:
        return "***"

    # Prevent accidental exposure via format() or f-strings by going through __str__
    def __format__(self, format_spec: str) -> str:
        return "***"


_PLACEHOLDER = "여기에_발급받은_인증키_입력"


class AppConfig:
    """Loads application secrets from environment variables or a .env file.

    Raises ValueError with a clear message if required secrets are missing.
    """

    def __init__(self, env_file: Path | str | None = None) -> None:
        target = Path(env_file) if env_file else Path(__file__).parent / ".env"
        load_dotenv(target, override=False)

        raw_key = os.environ.get("NTS_API_KEY", "").strip()
        if not raw_key or raw_key == _PLACEHOLDER:
            raise ValueError(
                "NTS_API_KEY가 설정되지 않았습니다.\n"
                "  1. cp .env.example .env\n"
                "  2. .env 파일을 열어 NTS_API_KEY=발급받은키 형식으로 입력하세요."
            )

        self.nts_api_key = SecretStr(raw_key)
