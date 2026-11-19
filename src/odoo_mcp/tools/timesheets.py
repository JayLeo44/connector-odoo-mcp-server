"""Tools MCP para Hojas de horas (account.analytic.line)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_timesheet_create(
        task_id: int,
        name: str,
        unit_amount: float,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Crea una línea de hoja de horas (account.analytic.line) sobre una tarea.

        El project_id se resuelve automáticamente desde la tarea. El
        empleado/usuario que registra las horas lo determina Odoo según
        las credenciales de autenticación del conector (ODOO_USERNAME).

        Args:
            task_id: ID de la tarea (project.task) a la que se imputan las horas.
            name: descripción breve de lo realizado.
            unit_amount: cantidad de horas (ej. 2.5).
            date: fecha en formato YYYY-MM-DD (default: hoy, según Odoo).
        """
        task = client.read("project.task", [task_id], ["project_id"])
        if not task or not task[0].get("project_id"):
            raise ValueError(
                f"No se encontró la tarea {task_id} o no tiene project_id."
            )
        project_id = task[0]["project_id"][0]

        values: dict[str, Any] = {
            "task_id": task_id,
            "project_id": project_id,
            "name": name,
            "unit_amount": unit_amount,
        }
        if date:
            values["date"] = date
        new_id = client.create("account.analytic.line", values)
        return {"id": new_id, "task_id": task_id, "project_id": project_id, "status": "created"}
