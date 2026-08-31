# odoo-mcp-server

Servidor MCP (Model Context Protocol) que conecta **Claude** — Desktop, Cowork o Claude Code — con **Odoo ERP** vía XML-RPC, sin necesidad de instalar ningún módulo dentro de Odoo.

Pensado especialmente para usarse con **tareas programadas de Cowork**: que Claude cree leads, mueva tareas de proyecto o consulte stock de forma autónoma, en horario definido.

## Características

- Conexión estándar por XML-RPC (`/xmlrpc/2/common` y `/xmlrpc/2/object`), compatible con Odoo Community y Enterprise, self-hosted u Odoo.sh/Odoo Online.
- Autenticación por API Key (no expone tu contraseña).
- Tools organizadas por área:
  - **CRM y Ventas**: leads/oportunidades, cotizaciones y pedidos de venta.
  - **Proyectos y Tareas**: proyectos, tareas, asignación de responsables, cambio de etapa.
  - **Inventario y Compras**: stock de productos, órdenes de compra.
- Configuración de credenciales 100% vía `.env` (nunca hardcodeadas ni versionadas).

## Instalación

Requiere Python 3.10+.

```bash
git clone <url-del-repo>
cd odoo-mcp-server
pip install -e .
```

## Configuración

1. Copia el archivo de ejemplo:

   ```bash
   cp .env.example .env
   ```

2. Completa `.env` con los datos de tu instancia. Hay **dos formas de autenticar**, elige una:

   **Opción A — API Key (recomendada)**

   ```
   ODOO_URL=https://tuinstancia.odoo.com
   ODOO_DB=nombre_de_tu_bd
   ODOO_USERNAME=usuario@tuempresa.com
   ODOO_API_KEY=tu_api_key_aqui
   ```

   La API Key se genera en Odoo desde **Ajustes → Usuarios → (tu usuario) → pestaña "Seguridad de la cuenta" → Claves API → Nueva clave API**. Es revocable sin tocar tu contraseña de login, y es la forma recomendada para producción.

   **Opción B — Password (si no tienes acceso para generar una API Key)**

   ```
   ODOO_URL=https://tuinstancia.odoo.com
   ODOO_DB=nombre_de_tu_bd
   ODOO_USERNAME=usuario@tuempresa.com
   ODOO_PASSWORD=tu_password
   ```

   Deja `ODOO_API_KEY` vacío o sin definir. Funciona igual (Odoo acepta password en el mismo parámetro de autenticación XML-RPC), pero es menos seguro: revocar el acceso implica cambiar tu contraseña de login, y si el password se filtra, compromete la cuenta completa (no solo el conector). Útil sobre todo para probar rápido contra una instancia local/dev, como en este mismo repo lo hicimos durante el desarrollo.

   Si ambas variables están presentes, `ODOO_API_KEY` tiene prioridad.

   **Instancia local con certificado self-signed o sin HTTPS real:** revisa también `ODOO_VERIFY_SSL` y la nota sobre `http://` vs `https://` en [Troubleshooting](#troubleshooting) — es el error más común al conectar contra una instancia local.

3. `.env` ya está en `.gitignore` — nunca se sube al repositorio.

## Uso con Claude Desktop / Cowork

Agrega el servidor a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "odoo-mcp-server"
    }
  }
}
```

O, si prefieres no instalarlo globalmente, apuntando al intérprete del entorno virtual:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/ruta/a/tu/venv/bin/odoo-mcp-server"
    }
  }
}
```

Reinicia Claude Desktop (cierra la app desde el ícono de la bandeja del sistema con **Quit/Salir** — cerrar solo la ventana no recarga la configuración) y el conector debería aparecer disponible.

### Windows + WSL

Si instalaste el venv dentro de WSL pero Claude Desktop corre nativo en Windows, invócalo a través de `wsl.exe` apuntando directo al Python del venv (evita `bash -lc`: un shell de login puede imprimir texto extra en stdout — motd, prompts de activación, etc. — y eso rompe el protocolo MCP, que exige stdout limpio):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "wsl.exe",
      "args": [
        "-e",
        "/ruta/wsl/a/tu/proyecto/odoo-mcp-server/venv/bin/python3",
        "-m",
        "odoo_mcp.server"
      ]
    }
  }
}
```

La ruta del proyecto en formato WSL para una carpeta de Windows es `/mnt/c/Users/TuUsuario/...`.

## Verificar conexión

Con el `.env` configurado, puedes probar el arranque manualmente:

```bash
python -m odoo_mcp.server
```

Desde Claude, invoca el tool `odoo_ping` para confirmar conectividad y ver la versión de tu instancia Odoo.

## Tools disponibles

### CRM y Ventas
| Tool | Descripción |
|---|---|
| `odoo_crm_list_leads` | Lista leads/oportunidades, con filtros por etapa, vendedor y tipo. |
| `odoo_crm_create_lead` | Crea un lead u oportunidad nuevo. |
| `odoo_crm_update_lead` | Actualiza campos de un lead existente. |
| `odoo_sales_list_orders` | Lista cotizaciones/pedidos de venta. |
| `odoo_sales_create_order` | Crea una cotización con líneas de producto. |

### Proyectos y Tareas
| Tool | Descripción |
|---|---|
| `odoo_project_list_projects` | Lista proyectos. |
| `odoo_project_list_tasks` | Lista tareas, con filtros por proyecto, responsable y etapa. |
| `odoo_project_create_task` | Crea una tarea dentro de un proyecto. |
| `odoo_project_update_task` | Actualiza una tarea (ej. cambiar de etapa/kanban). |

### Inventario y Compras
| Tool | Descripción |
|---|---|
| `odoo_inventory_list_products` | Lista productos y su stock disponible. |
| `odoo_purchase_list_orders` | Lista órdenes de compra. |
| `odoo_purchase_create_order` | Crea una orden de compra con líneas. |

### General
| Tool | Descripción |
|---|---|
| `odoo_ping` | Verifica conectividad y devuelve la versión de Odoo. |

## Troubleshooting

**`SSLEOFError: UNEXPECTED_EOF_WHILE_READING`**
No es un problema de certificado: el servidor está respondiendo HTTP plano, no HTTPS, en esa URL/puerto (muy común en instancias locales o en Docker). Cambia `ODOO_URL` a `http://` en vez de `https://`.

**`Autenticación rechazada por Odoo`**
Verifica `ODOO_DB` exacto (case-sensitive), y que `ODOO_USERNAME` + `ODOO_API_KEY`/`ODOO_PASSWORD` correspondan a un usuario activo con acceso a esa base de datos.

**Error de certificado SSL contra una instancia `https://` real**
Si es una instancia local/dev con certificado self-signed, agrega `ODOO_VERIFY_SSL=false` al `.env`. Nunca lo desactives contra producción.

**`ConnectionRefusedError`**
El host/puerto no es alcanzable desde donde estás corriendo el conector. Si usas WSL contra un Odoo en Windows (o viceversa), confirma que el `localhost` se reenvía entre ambos (por defecto en WSL2 sí, pero revisa tu configuración de red si no).

**`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`**
Se instaló `mcp` 2.x, que renombró `FastMCP` a `MCPServer`. Este proyecto fija `mcp<2.0.0` en `pyproject.toml`; si ya tenías el venv creado desde antes, reinstala: `pip install "mcp<2.0.0" --force-reinstall`.

**`Server disconnected` en Claude Desktop (sin más detalle)**
Revisa los logs de MCP de la app (Settings → Developer → logs del servidor). Casi siempre es una excepción de Python al arrancar (dependencia faltante, `.env` no encontrado, credenciales inválidas) que se ve clara ahí. Evita invocar el server a través de un shell de login (`bash -lc`, `zsh -l`) — cualquier salida extra en stdout antes del JSON-RPC tumba la conexión.

## Seguridad

- Usa siempre una **API Key dedicada**, nunca tu contraseña de usuario.
- Considera crear un usuario Odoo con permisos acotados (grupo específico) para el conector, en lugar de un administrador.
- `.env` nunca debe subirse a git ni compartirse.

## Licencia

MIT
