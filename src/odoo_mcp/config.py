"""Carga de configuración desde variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env por ruta absoluta (raíz del proyecto), no por directorio de
# trabajo: cuando Claude Desktop lanza este proceso (ej. vía wsl.exe), el cwd
# no necesariamente es la carpeta del proyecto.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Falta configuración requerida en el entorno/.env."""


@dataclass(frozen=True)
class OdooConfig:
    url: str
    db: str
    username: str
    api_key: str = ""
    password: str = ""
    timeout: int = 30
    verify_ssl: bool = True

    @property
    def auth_secret(self) -> str:
        """Credencial usada para authenticate()/execute_kw(): API key si existe,
        si no cae a password. Odoo acepta ambas en el mismo parámetro."""
        return self.api_key or self.password

    @classmethod
    def from_env(cls) -> "OdooConfig":
        url = os.environ.get("ODOO_URL", "").rstrip("/")
        db = os.environ.get("ODOO_DB", "")
        username = os.environ.get("ODOO_USERNAME", "")
        api_key = os.environ.get("ODOO_API_KEY", "")
        password = os.environ.get("ODOO_PASSWORD", "")
        timeout = int(os.environ.get("ODOO_TIMEOUT", "30"))
        verify_ssl = os.environ.get("ODOO_VERIFY_SSL", "true").strip().lower() not in ("false", "0", "no")

        missing = [
            name
            for name, val in (
                ("ODOO_URL", url),
                ("ODOO_DB", db),
                ("ODOO_USERNAME", username),
            )
            if not val
        ]
        if not api_key and not password:
            missing.append("ODOO_API_KEY o ODOO_PASSWORD")
        if missing:
            raise ConfigError(
                "Faltan variables de entorno requeridas: "
                + ", ".join(missing)
                + ". Copia .env.example a .env y complétalo."
            )

        return cls(
            url=url, db=db, username=username, api_key=api_key,
            password=password, timeout=timeout, verify_ssl=verify_ssl,
        )
