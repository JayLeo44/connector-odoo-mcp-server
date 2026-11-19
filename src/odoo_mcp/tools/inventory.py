"""Tools MCP para Inventario (product.product / stock)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient

PRODUCT_FIELDS = ["id", "name", "default_code", "qty_available", "virtual_available", "list_price", "type"]


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_inventory_list_products(
        name: str | None = None,
        only_low_stock: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista productos y su disponibilidad en stock (product.product).

        Args:
            name: filtra por nombre o referencia interna (búsqueda parcial).
            only_low_stock: si True, solo trae productos con qty_available <= 0.
            limit: máximo de registros a devolver (default 20).
        """
        domain: list = []
        if name:
            domain.append("|")
            domain.append(("name", "ilike", name))
            domain.append(("default_code", "ilike", name))
        if only_low_stock:
            domain.append(("qty_available", "<=", 0))
        return client.search_read("product.product", domain, PRODUCT_FIELDS, limit=limit)
