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

    leads = client.search_read("crm.lead", limit=1)
    print(f"OK — acceso a datos confirmado (crm.lead: {len(leads)} registro(s) leído(s)).")
    print("\nTodo funcionando correctamente.")


if __name__ == "__main__":
    main()
