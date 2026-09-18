import uuid
import json
from typing import Dict, Any, List, Optional
from app.data.database import connect, initialize_database
from backend.services.knowledge_graph import KnowledgeGraphService


class ProjectMemoryService:
    def __init__(self):
        initialize_database()
        self.graph = KnowledgeGraphService()

    def set_project_state(
        self,
        project_id: str,
        name: str,
        description: str = "",
        current_version: str = "10.1",
        architecture: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        with connect() as c:
            c.execute(
                """
                INSERT INTO project_states (project_id, name, description, current_version, status, architecture, metadata, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    current_version=excluded.current_version,
                    architecture=excluded.architecture,
                    metadata=excluded.metadata,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (project_id, name, description, current_version, architecture, json.dumps(metadata, ensure_ascii=False))
            )

        # Ingest into knowledge graph
        p_node = self.graph.add_node(name=f"Project:{name}", node_type="project", metadata={"project_id": project_id})
        v_node = self.graph.add_node(name=f"Version:{current_version}", node_type="version")
        if p_node and v_node:
            self.graph.add_edge(p_node, v_node, relation="HAS_VERSION", weight=1.0)

        techs = metadata.get("technologies", [])
        for tech in techs:
            t_node = self.graph.add_node(name=f"Tech:{tech}", node_type="technology")
            if p_node and t_node:
                self.graph.add_edge(p_node, t_node, relation="USES_TECHNOLOGY", weight=1.0)

        return self.get_project_state(project_id) or {}

    def get_project_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        with connect() as c:
            row = c.execute("SELECT * FROM project_states WHERE project_id=?", (project_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.get("metadata") or "{}")
            return d

    def add_project_version(self, project_id: str, version: str, summary: str = "") -> str:
        id_str = f"pv_{uuid.uuid4().hex[:12]}"
        with connect() as c:
            c.execute(
                "INSERT INTO project_versions (id_str, project_id, version, summary) VALUES (?, ?, ?, ?)",
                (id_str, project_id, version, summary)
            )
            # Update current version in state
            c.execute(
                "UPDATE project_states SET current_version=?, updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                (version, project_id)
            )

        state = self.get_project_state(project_id)
        p_name = state["name"] if state else project_id
        p_node = self.graph.add_node(name=f"Project:{p_name}", node_type="project")
        v_node = self.graph.add_node(name=f"Version:{version}", node_type="version", metadata={"summary": summary})
        if p_node and v_node:
            self.graph.add_edge(p_node, v_node, relation="HAS_VERSION", weight=1.0)

        return id_str

    def add_project_issue(self, project_id: str, title: str, priority: str = "medium") -> str:
        issue_id = f"pi_{uuid.uuid4().hex[:12]}"
        with connect() as c:
            c.execute(
                "INSERT INTO project_issues (issue_id, project_id, title, status, priority) VALUES (?, ?, ?, 'open', ?)",
                (issue_id, project_id, title, priority)
            )

        state = self.get_project_state(project_id)
        p_name = state["name"] if state else project_id
        p_node = self.graph.add_node(name=f"Project:{p_name}", node_type="project")
        i_node = self.graph.add_node(name=f"Issue:{title[:40]}", node_type="issue", metadata={"issue_id": issue_id})
        if p_node and i_node:
            self.graph.add_edge(p_node, i_node, relation="HAS_ISSUE", weight=1.0)

        return issue_id

    def add_project_task(self, project_id: str, title: str, status: str = "pending") -> str:
        task_id = f"pt_{uuid.uuid4().hex[:12]}"
        with connect() as c:
            c.execute(
                "INSERT INTO project_tasks (task_id, project_id, title, status) VALUES (?, ?, ?, ?)",
                (task_id, project_id, title, status)
            )

        state = self.get_project_state(project_id)
        p_name = state["name"] if state else project_id
        p_node = self.graph.add_node(name=f"Project:{p_name}", node_type="project")
        t_node = self.graph.add_node(name=f"Task:{title[:40]}", node_type="task", metadata={"task_id": task_id})
        if p_node and t_node:
            self.graph.add_edge(p_node, t_node, relation="HAS_FUTURE_TASK", weight=1.0)

        return task_id

    def get_project_history(self, project_id: str) -> Dict[str, Any]:
        state = self.get_project_state(project_id)
        with connect() as c:
            versions = [dict(r) for r in c.execute("SELECT * FROM project_versions WHERE project_id=? ORDER BY id ASC", (project_id,)).fetchall()]
            issues = [dict(r) for r in c.execute("SELECT * FROM project_issues WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()]
            tasks = [dict(r) for r in c.execute("SELECT * FROM project_tasks WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()]

        return {
            "state": state,
            "versions": versions,
            "issues": issues,
            "tasks": tasks
        }
