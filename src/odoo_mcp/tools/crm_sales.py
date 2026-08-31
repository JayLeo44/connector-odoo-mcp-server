"""Tools MCP para CRM (crm.lead) y Ventas (sale.order)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient

LEAD_FIELDS = [
    "id", "name", "partner_name", "email_from", "phone",
    "stage_id", "user_id", "team_id", "expected_revenue",
    "probability", "type", "create_date",
]

SALE_ORDER_FIELDS = [
    "id", "name", "partner_id", "date_order", "amount_total",
    "state", "user_id", "invoice_status",
]


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_crm_list_leads(
        stage: str | None = None,
        salesperson: str | None = None,
        only_opportunities: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lista leads/oportunidades de CRM (crm.lead) en Odoo.

        Args:
            stage: filtra por nombre de etapa (ej. "New", "Won").
            salesperson: filtra por nombre del vendedor asignado.
            only_opportunities: si True, solo trae oportunidades (type='opportunity'),
                excluyendo leads sin calificar.
            limit: máximo de registros a devolver (default 20).
        """
        domain: list = []
        if stage:
            domain.append(("stage_id.name", "ilike", stage))
        if salesperson:
            domain.append(("user_id.name", "ilike", salesperson))
        if only_opportunities:
            domain.append(("type", "=", "opportunity"))
        return client.search_read("crm.lead", domain, LEAD_FIELDS, limit=limit)

    @mcp.tool()
    def odoo_crm_create_lead(
        name: str,
        partner_name: str | None = None,
        email_from: str | None = None,
        phone: str | None = None,
        expected_revenue: float | None = None,
        type_: str = "lead",
    ) -> dict[str, Any]:
        """Crea un nuevo lead u oportunidad en el CRM de Odoo.

        Args:
            name: título/asunto del lead (requerido).
            partner_name: nombre de la empresa/contacto.
            email_from: email de contacto.
            phone: teléfono de contacto.
            expected_revenue: ingreso esperado, si aplica.
            type_: "lead" o "opportunity" (default "lead").
        """
        values: dict[str, Any] = {"name": name, "type": type_}
        if partner_name:
            values["partner_name"] = partner_name
        if email_from:
            values["email_from"] = email_from
        if phone:
            values["phone"] = phone
        if expected_revenue is not None:
            values["expected_revenue"] = expected_revenue
        new_id = client.create("crm.lead", values)
        return {"id": new_id, "status": "created"}

    @mcp.tool()
    def odoo_crm_update_lead(lead_id: int, values: dict[str, Any]) -> dict[str, Any]:
        """Actualiza campos de un lead/oportunidad existente.

        Args:
            lead_id: ID del registro crm.lead a modificar.
            values: diccionario de campo->valor a actualizar
                (ej. {"probability": 80, "expected_revenue": 5000}).
        """
        ok = client.write("crm.lead", [lead_id], values)
        return {"id": lead_id, "updated": ok}

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
