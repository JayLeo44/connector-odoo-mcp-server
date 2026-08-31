"""Tools MCP para Inventario (product.*) y Compras (purchase.order)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient

PRODUCT_FIELDS = ["id", "name", "default_code", "qty_available", "virtual_available", "list_price", "type"]
PURCHASE_FIELDS = ["id", "name", "partner_id", "date_order", "amount_total", "state"]


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

    @mcp.tool()
    def odoo_purchase_list_orders(
        supplier: str | None = None,
        state: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista órdenes de compra (purchase.order).

        Args:
            supplier: filtra por nombre del proveedor.
            state: filtra por estado ('draft', 'sent', 'purchase', 'done', 'cancel').
            limit: máximo de registros a devolver (default 20).
        """
        domain: list = []
        if supplier:
            domain.append(("partner_id.name", "ilike", supplier))
        if state:
            domain.append(("state", "=", state))
        return client.search_read("purchase.order", domain, PURCHASE_FIELDS, limit=limit, order="date_order desc")

    @mcp.tool()
    def odoo_purchase_create_order(
        supplier_id: int,
        order_lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Crea una orden de compra (purchase.order) con sus líneas.

        Args:
            supplier_id: ID del partner (res.partner) proveedor.
            order_lines: lista de líneas, cada una como
                {"product_id": <int>, "product_qty": <float>, "price_unit": <float>}.
        """
        line_commands = [
            (0, 0, {
                "product_id": line["product_id"],
                "product_qty": line.get("product_qty", 1),
                "price_unit": line.get("price_unit", 0),
                "name": line.get("name", ""),
            })
            for line in order_lines
        ]
        new_id = client.create(
            "purchase.order",
            {"partner_id": supplier_id, "order_line": line_commands},
        )
        return {"id": new_id, "status": "created"}
