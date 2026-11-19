"""Tools MCP para Contactos (res.partner)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_search_partner(name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca contactos/usuarios (res.partner) por nombre, para poder
        etiquetarlos/notificarlos con odoo_project_post_message
        (mention_partner_ids).

        Args:
            name: nombre (o parte) a buscar, ej. "Deysi".
            limit: máximo de resultados a devolver (default 10).
        """
        domain = [("name", "ilike", name)]
        return client.search_read(
            "res.partner", domain, ["id", "name", "email"], limit=limit
        )
