"""Prueba rápida y aislada de conexión a Odoo, sin pasar por MCP.

Uso:
    python test_connection.py
"""

from odoo_mcp.config import ConfigError, OdooConfig
from odoo_mcp.odoo_client import OdooAuthError, OdooClient


def main() -> None:
    try:
        config = OdooConfig.from_env()
    except ConfigError as e:
        print(f"[config] {e}")
        return

    print(f"Conectando a {config.url} (db={config.db}, user={config.username})...")
    client = OdooClient(config)

    try:
        version = client.version()
        print("OK — versión de Odoo:", version.get("server_version"))
    except Exception as e:
        print(f"[conexión] {type(e).__name__}: {e}")
        print(
            "\nSi ves un error de certificado SSL, agrega ODOO_VERIFY_SSL=false "
            "a tu .env (solo recomendado para instancias locales/dev)."
        )
        return

    try:
        uid = client._authenticate()
        print(f"OK — autenticado como uid={uid}")
    except OdooAuthError as e:
        print(f"[auth] {e}")
        return

    partners = client.search_read("res.partner", fields=["id"], limit=1)
    print(f"OK — acceso a datos confirmado (res.partner: {len(partners)} registro(s) leído(s)).")

    # Módulos de Odoo que requieren las tools del MCP.
    required = {
        "crm": "CRM (crm.lead)",
        "sale": "Ventas (sale.order)",
        "project": "Proyectos/Tareas",
        "hr_timesheet": "Hojas de horas (odoo_timesheet_create)",
        "stock": "Inventario (qty_available)",
        "purchase": "Compras (purchase.order)",
    }
    installed = {
        m["name"]
        for m in client.search_read(
            "ir.module.module",
            [("name", "in", list(required)), ("state", "=", "installed")],
            fields=["name"],
            limit=len(required),
        )
    }
    missing = [m for m in required if m not in installed]
    for name, label in required.items():
        print(f"  {'OK' if name in installed else '--'} {name:<13} {label}")

    if missing:
        print(f"\nConexión OK, pero faltan módulos: {', '.join(missing)}. "
              "Las tools que dependen de ellos fallarán en esta base.")
    else:
        print("\nTodo funcionando correctamente.")


if __name__ == "__main__":
    main()
