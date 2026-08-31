"""Punto de entrada del servidor MCP odoo-mcp-server.

Arranca un servidor MCP (stdio) que expone tools para interactuar con
Odoo (CRM/Ventas, Proyectos/Tareas, Inventario/Compras) vía XML-RPC.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .config import ConfigError, OdooConfig
from .odoo_client import OdooClient
from .tools import crm_sales, inventory_purchase, projects

mcp = FastMCP("odoo-mcp-server")


@mcp.tool()
def odoo_ping() -> dict:
    """Verifica conectividad con la instancia Odoo configurada y devuelve su versión."""
    client = _get_client()
    return client.version()


def _get_client() -> OdooClient:
    global _client
    if _client is None:
        _client = OdooClient(OdooConfig.from_env())
    return _client


_client: OdooClient | None = None


def main() -> None:
    try:
        config = OdooConfig.from_env()
    except ConfigError as e:
        print(f"[odoo-mcp-server] Error de configuración: {e}", file=sys.stderr)
        sys.exit(1)

    client = OdooClient(config)
    global _client
    _client = client

    crm_sales.register(mcp, client)
    projects.register(mcp, client)
    inventory_purchase.register(mcp, client)

    mcp.run()


if __name__ == "__main__":
    main()
