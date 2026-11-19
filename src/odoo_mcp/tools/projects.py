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
        task_id: int,
        body: str,
        as_note: bool = False,
        mention_partner_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Publica un mensaje en el chatter (mail.thread) de una tarea.

        Usa message_post, NO el campo description -- es el hilo de
        seguimiento/bitácora de la tarea, no su descripción.

        Args:
            task_id: ID de la tarea (project.task) donde publicar.
            body: texto del mensaje. Se envía tal cual (texto plano con
                saltos de línea reales); esta instancia de Odoo no
                renderiza HTML embebido en el body del chatter -- las
                etiquetas aparecen literales.
            as_note: True para registrarlo como "Nota" interna (no
                notifica a los seguidores) en vez de "Mensaje" (default
                False), igual que el botón "Registrar nota" del chatter.
            mention_partner_ids: IDs de res.partner (obtenidos con
                odoo_search_partner) a etiquetar/notificar en el mensaje.
                Se agregan como destinatarios reales (partner_ids de
                message_post) y su "@Nombre" se añade al final del body.
        """
        final_body = body
        if mention_partner_ids:
            partners = client.read("res.partner", mention_partner_ids, ["id", "name"])
            names = " ".join(f"@{p['name']}" for p in partners)
            final_body = f"{body}\n\n{names}" if body else names

        kwargs: dict[str, Any] = {"body": final_body}
        if as_note:
            kwargs["message_type"] = "comment"
            kwargs["subtype_xmlid"] = "mail.mt_note"
        if mention_partner_ids:
            kwargs["partner_ids"] = mention_partner_ids
        message_id = client.execute_kw(
            "project.task", "message_post", [[task_id]], kwargs
        )
        return {
            "task_id": task_id,
            "message_id": message_id,
            "mentioned_partner_ids": mention_partner_ids or [],
        }

    @mcp.tool()
    def odoo_project_read_messages(task_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """Lee los mensajes y notas del chatter (mail.message) de una tarea.

        Útil para revisar lo ya publicado antes de agregar un nuevo
        mensaje, evitar duplicados, o hacer un review de lo reportado
        en una tarea sin salir de Claude.

        Args:
            task_id: ID de la tarea (project.task) cuyo chatter se lee.
            limit: máximo de mensajes a devolver, más recientes primero
                (default 20).
        """
        domain = [
            ("model", "=", "project.task"),
            ("res_id", "=", task_id),
            ("message_type", "!=", "notification"),
        ]
        fields = ["id", "author_id", "date", "body", "message_type", "subtype_id"]
        return client.search_read(
            "mail.message", domain, fields, limit=limit, order="date desc"
        )
