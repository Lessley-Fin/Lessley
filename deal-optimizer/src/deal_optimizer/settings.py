"""Service-level configuration — the HTTP surface only.

Deliberately mirrors ``Lessley.Personalization/config/settings.py``: same variable
names, same meanings, so one .env stanza reads the same for both services.

One difference, and it is on purpose: Personalization declares ``Environment`` with
no default and refuses to boot without it. This package is *also* imported by the
CLI and by the pure-engine tests, neither of which has an environment to read, so
``Environment`` defaults here instead. The default is ``Production`` rather than
``Development`` so a missing value can only ever close the dev bypass, never open it.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # See the module docstring for why this one carries a default when
    # Personalization's does not.
    Environment: str = "Production"

    # Shared secret the edge (Caddy) stamps on every inbound request as X-Edge-Key.
    # Server-only — never shipped to a browser. Blank disables edge verification.
    Edge_ApiKey: str | None = None

    # Mode 1 escape hatch: services run locally with no Caddy in front. Only honoured
    # when Environment is also Development, so production cannot be opened by this flag
    # alone. Identity while it's active comes from decoding the Gateway's access_token
    # cookie directly (see auth.py:email_from_access_token) rather than a fixed value.
    Edge_AllowUnverified: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
