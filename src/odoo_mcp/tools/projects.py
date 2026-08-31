"""Tools MCP para Proyectos (project.project) y Tareas (project.task).

Pensado para integrarse con tareas programadas de Cowork: permite que
Claude cree/actualice tareas en Odoo como resultado de flujos automatizados.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..odoo_client import OdooClient

PROJECT_FIELDS = ["id", "name", "user_id", "partner_id", "task_count", "date_start", "date"]
TASK_FIELDS = [
    "id", "name", "project_id", "stage_id", "user_ids",
    "date_deadline", "priority", "state", "description",
]


def register(mcp: FastMCP, client: OdooClient) -> None:

    @mcp.tool()
    def odoo_project_list_projects(name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Lista proyectos (project.project) en Odoo.

        Args:
            name: filtra por nombre del proyecto (búsqueda parcial).
            limit: máximo de registros a devolver (default 20).
        """
        domain: list = []
        if name:
            domain.append(("name", "ilike", name))
        return client.search_read("project.project", domain, PROJECT_FIELDS, limit=limit)

    @mcp.tool()
    def odoo_project_list_tasks(
        project_id: int | None = None,
        project_name: str | None = None,
        assignee: str | None = None,
        stage: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Lista tareas (project.task) de Odoo, opcionalmente filtradas.

        Args:
            project_id: ID exacto del proyecto.
            project_name: nombre del proyecto (búsqueda parcial), alternativa a project_id.
            assignee: nombre del responsable asignado.
            stage: nombre de la etapa/columna kanban (ej. "In Progress", "Done").
            limit: máximo de registros a devolver (default 30).
        """
        domain: list = []
        if project_id:
            domain.append(("project_id", "=", project_id))
        elif project_name:
            domain.append(("project_id.name", "ilike", project_name))
        if assignee:
            domain.append(("user_ids.name", "ilike", assignee))
        if stage:
            domain.append(("stage_id.name", "ilike", stage))
        return client.search_read("project.task", domain, TASK_FIELDS, limit=limit)

    @mcp.tool()
    def odoo_project_create_task(
        name: str,
        project_id: int,
        description: str | None = None,
        assignee_id: int | None = None,
        deadline: str | None = None,
        priority: str = "0",
    ) -> dict[str, Any]:
        """Crea una tarea (project.task) dentro de un proyecto Odoo.

        Útil para que una tarea programada de Cowork registre trabajo
        pendiente directamente en Odoo.

        Args:
            name: título de la tarea (requerido).
            project_id: ID del proyecto donde se crea.
            description: descripción/detalle de la tarea.
            assignee_id: ID del usuario (res.users) responsable.
            deadline: fecha límite en formato YYYY-MM-DD.
            priority: "0" (normal) o "1" (alta/estrella), default "0".
        """
        values: dict[str, Any] = {"name": name, "project_id": project_id, "priority": priority}
        if description:
            values["description"] = description
        if assignee_id:
            values["user_ids"] = [(6, 0, [assignee_id])]
        if deadline:
            values["date_deadline"] = deadline
        new_id = client.create("project.task", values)
        return {"id": new_id, "status": "created"}

    @mcp.tool()
    def odoo_project_update_task(task_id: int, values: dict[str, Any]) -> dict[str, Any]:
        """Actualiza campos de una tarea existente (ej. cambiar de etapa/estado).

        Args:
            task_id: ID de la tarea (project.task) a modificar.
            values: diccionario de campo->valor a actualizar
                (ej. {"stage_id": 3} para mover de columna kanban).
        """
        ok = client.write("project.task", [task_id], values)
        return {"id": task_id, "updated": ok}
