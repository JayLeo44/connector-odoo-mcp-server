"""Punto de entrada del servidor MCP odoo-mcp-server.

Arranca un servidor MCP (stdio) que expone tools para interactuar con
Odoo vía XML-RPC. Las tools están agrupadas por módulo de Odoo en
``tools/`` (CRM, Ventas, Inventario, Compras, Proyectos/Tareas, Hojas de
horas, Contactos y chatter) y se registran en ``main()``.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .config import ConfigError, OdooConfig
from .odoo_client import OdooClient
from .tools import (
    crm,
    inventory,
    mail,
    partners,
    projects,
    purchase,
    sales,
    timesheets,
)

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

    for module in (crm, sales, inventory, purchase, projects, timesheets, partners, mail):
        module.register(mcp, client)

    mcp.run()


if __name__ == "__main__":
    main()
