import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List

from db import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables(conn: sqlite3.Connection):
    with conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT,
            data JSON,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_tasks (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            task_type TEXT,
            task_order INTEGER,
            status TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS task_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            result JSON,
            created_at TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES job_tasks(id)
        );

        CREATE TABLE IF NOT EXISTS current_task_versions (
            task_id TEXT PRIMARY KEY,
            version_id INTEGER,
            result JSON,
            FOREIGN KEY (task_id) REFERENCES job_tasks(id),
            FOREIGN KEY (version_id) REFERENCES task_versions(id)
        );

        CREATE TABLE IF NOT EXISTS task_dependencies (
            dependent_task_id TEXT,
            dependency_task_id TEXT,
            PRIMARY KEY (dependent_task_id, dependency_task_id),
            FOREIGN KEY (dependent_task_id) REFERENCES job_tasks(id),
            FOREIGN KEY (dependency_task_id) REFERENCES job_tasks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_job_tasks_job_id ON job_tasks(job_id);
        CREATE INDEX IF NOT EXISTS idx_task_versions_task_id ON task_versions(task_id);
        CREATE INDEX IF NOT EXISTS idx_task_versions_created_at ON task_versions(created_at);
        CREATE INDEX IF NOT EXISTS idx_task_dependencies_dependent ON task_dependencies(dependent_task_id);
        CREATE INDEX IF NOT EXISTS idx_task_dependencies_dependency ON task_dependencies(dependency_task_id);
        """)


def execute_query(conn: sqlite3.Connection, query: str, params: Any = None):
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.fetchall()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise


def get_job(job_id: str) -> Dict[str, Any]:
    with db_manager.get_db("jobs") as conn:
        row = execute_query(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))
        return dict(row[0]) if row else None


def get_job_tasks(job_id: str) -> List[Dict[str, Any]]:
    with db_manager.get_db("jobs") as conn:
        rows = execute_query(
            conn,
            "SELECT * FROM job_tasks WHERE job_id = ? ORDER BY task_order",
            (job_id,),
        )
        return [dict(row) for row in rows]


def get_task_versions(task_id: str) -> List[Dict[str, Any]]:
    with db_manager.get_db("jobs") as conn:
        rows = execute_query(
            conn,
            "SELECT * FROM task_versions WHERE task_id = ? ORDER BY id",
            (task_id,),
        )
        return [dict(row) for row in rows]


def get_current_task_version(task_id: str) -> Dict[str, Any]:
    with db_manager.get_db("jobs") as conn:
        row = execute_query(
            conn, "SELECT * FROM current_task_versions WHERE task_id = ?", (task_id,)
        )
        return dict(row[0]) if row else None


def get_task_dependencies(task_id: str) -> List[str]:
    with db_manager.get_db("jobs") as conn:
        rows = execute_query(
            conn,
            "SELECT dependency_task_id FROM task_dependencies WHERE dependent_task_id = ?",
            (task_id,),
        )
        return [row["dependency_task_id"] for row in rows]


def get_task_dependents(task_id: str) -> List[str]:
    with db_manager.get_db("jobs") as conn:
        rows = execute_query(
            conn,
            "SELECT dependent_task_id FROM task_dependencies WHERE dependency_task_id = ?",
            (task_id,),
        )
        return [row["dependent_task_id"] for row in rows]


def add_task_dependency(dependent_task_id: str, dependency_task_id: str):
    with db_manager.get_db("jobs") as conn:
        execute_query(
            conn,
            """
            INSERT OR IGNORE INTO task_dependencies (dependent_task_id, dependency_task_id)
            VALUES (?, ?)
        """,
            (dependent_task_id, dependency_task_id),
        )


def update_job_status(job_id: str, status: str):
    with db_manager.get_db("jobs") as conn:
        execute_query(
            conn,
            """
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
        """,
            (status, datetime.now(timezone.utc).isoformat(), job_id),
        )


def update_task_status(task_id: str, status: str):
    with db_manager.get_db("jobs") as conn:
        execute_query(
            conn,
            """
            UPDATE job_tasks
            SET status = ?, updated_at = ?
            WHERE id = ?
        """,
            (status, datetime.now(timezone.utc).isoformat(), task_id),
        )


def create_task_version(task_id: str, result: Any) -> int:
    with db_manager.get_db("jobs") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO task_versions (task_id, result, created_at)
            VALUES (?, ?, ?)
        """,
            (task_id, json.dumps(result), datetime.now(timezone.utc).isoformat()),
        )
        version_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT OR REPLACE INTO current_task_versions (task_id, version_id, result)
            VALUES (?, ?, ?)
        """,
            (task_id, version_id, json.dumps(result)),
        )

        conn.commit()
        return version_id
