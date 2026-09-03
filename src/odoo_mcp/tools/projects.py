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

    @mcp.tool()
    def odoo_project_post_message(
        task_id: int, body: str, as_note: bool = False
    ) -> dict[str, Any]:
        """Publica un mensaje en el chatter (mail.thread) de una tarea.

        Usa message_post, NO el campo description -- es el hilo de
        seguimiento/bitácora de la tarea, no su descripción.

        Args:
            task_id: ID de la tarea (project.task) donde publicar.
            body: texto del mensaje (soporta HTML simple, ej. <br/> para
                saltos de línea).
            as_note: True para registrarlo como "Nota" interna (no
                notifica a los seguidores) en vez de "Mensaje" (default
                False), igual que el botón "Registrar nota" del chatter.
        """
        kwargs: dict[str, Any] = {"body": body}
        if as_note:
            kwargs["message_type"] = "comment"
            kwargs["subtype_xmlid"] = "mail.mt_note"
        message_id = client.execute_kw(
            "project.task", "message_post", [[task_id]], kwargs
        )
        return {"task_id": task_id, "message_id": message_id}

    @mcp.tool()
    def odoo_message_delete(message_id: int) -> dict[str, Any]:
        """Elimina un mensaje del chatter (mail.message) por su ID.

        Útil para corregir un mensaje mal publicado (ej. tipo o
        formato incorrecto) volviendo a publicarlo después.

        Args:
            message_id: ID del mail.message a eliminar (lo devuelve
                odoo_project_post_message al crearlo).
        """
        ok = client.unlink("mail.message", [message_id])
        return {"message_id": message_id, "deleted": ok}

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
