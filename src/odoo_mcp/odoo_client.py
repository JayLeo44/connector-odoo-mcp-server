"""Cliente XML-RPC para Odoo.

Usa los endpoints estándar que cualquier instancia Odoo (Community o
Enterprise, self-hosted o Odoo.sh/Odoo Online) expone sin necesidad de
instalar ningún módulo adicional:

    /xmlrpc/2/common  -> autenticación
    /xmlrpc/2/object  -> execute_kw (CRUD genérico sobre cualquier modelo)

Referencia: https://www.odoo.com/documentation/latest/developer/reference/external_api.html
"""

from __future__ import annotations

import ssl
import xmlrpc.client
from typing import Any, Iterable

from .config import OdooConfig


class OdooAuthError(RuntimeError):
    """Falló la autenticación contra Odoo."""


class OdooClient:
    def __init__(self, config: OdooConfig):
        self._config = config
        context = None
        if config.url.startswith("https://") and not config.verify_ssl:
            # Solo para instancias locales/dev con certificado self-signed.
            # NUNCA desactivar verify_ssl contra una instancia de producción.
            context = ssl._create_unverified_context()
        self._common = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/common", allow_none=True, context=context
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{config.url}/xmlrpc/2/object", allow_none=True, context=context
        )
        self._uid: int | None = None

    def version(self) -> dict[str, Any]:
        return self._common.version()

    def _authenticate(self) -> int:
        if self._uid is not None:
            return self._uid
        uid = self._common.authenticate(
            self._config.db, self._config.username, self._config.auth_secret, {}
        )
        if not uid:
            raise OdooAuthError(
                "Autenticación rechazada por Odoo. Verifica ODOO_DB, "
                "ODOO_USERNAME y ODOO_API_KEY en tu .env."
            )
        self._uid = uid
        return uid

    def execute_kw(
        self,
        model: str,
        method: str,
        args: Iterable[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        uid = self._authenticate()
        return self._models.execute_kw(
            self._config.db,
            uid,
            self._config.auth_secret,
            model,
            method,
            list(args or []),
            kwargs or {},
        )

    # --- Helpers CRUD genéricos, usados por todos los grupos de tools ---

    def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"limit": limit, "offset": offset}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search_read", [domain or []], kwargs)

    def read(self, model: str, ids: list[int], fields: list[str] | None = None) -> list[dict[str, Any]]:
        kwargs = {"fields": fields} if fields else {}
        return self.execute_kw(model, "read", [ids], kwargs)

    def create(self, model: str, values: dict[str, Any]) -> int:
        return self.execute_kw(model, "create", [values])

    def write(self, model: str, ids: list[int], values: dict[str, Any]) -> bool:
        return self.execute_kw(model, "write", [ids, values])

    def unlink(self, model: str, ids: list[int]) -> bool:
        return self.execute_kw(model, "unlink", [ids])
