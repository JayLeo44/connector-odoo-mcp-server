"""Tools MCP genéricas de chatter (mail.message)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_message_delete(message_id: int) -> dict[str, Any]:
        """Elimina un mensaje del chatter (mail.message) por su ID.

        Útil para corregir un mensaje mal publicado (ej. tipo o
        formato incorrecto) volviendo a publicarlo después.

        Args:
            message_id: ID del mail.message a eliminar (lo devuelve
                odoo_project_post_message al crearlo).
        """
        ok = client.unlink("mail.message", [message_id])
        return {"message_id": message_id, "deleted": ok}
