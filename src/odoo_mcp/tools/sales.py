"""Tools MCP para Ventas (sale.order)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient

SALE_ORDER_FIELDS = [
    "id", "name", "partner_id", "date_order", "amount_total",
    "state", "user_id", "invoice_status",
]


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_sales_list_orders(
        customer: str | None = None,
        state: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista cotizaciones y pedidos de venta (sale.order).

        Args:
            customer: filtra por nombre de cliente (partner).
            state: filtra por estado ('draft', 'sent', 'sale', 'done', 'cancel').
            limit: máximo de registros a devolver (default 20).
        """
        domain: list = []
        if customer:
            domain.append(("partner_id.name", "ilike", customer))
        if state:
            domain.append(("state", "=", state))
        return client.search_read("sale.order", domain, SALE_ORDER_FIELDS, limit=limit, order="date_order desc")

    @mcp.tool()
    def odoo_sales_create_order(
        customer_id: int,
        order_lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Crea una cotización/pedido de venta (sale.order) con sus líneas.

        Args:
            customer_id: ID del partner (res.partner) cliente.
            order_lines: lista de líneas, cada una como
                {"product_id": <int>, "product_uom_qty": <float>}.
        """
        line_commands = [
            (0, 0, {"product_id": line["product_id"], "product_uom_qty": line.get("product_uom_qty", 1)})
            for line in order_lines
        ]
        new_id = client.create(
            "sale.order",
            {"partner_id": customer_id, "order_line": line_commands},
        )
        return {"id": new_id, "status": "created"}
