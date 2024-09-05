import sqlite3
from contextlib import contextmanager
from typing import Any, Dict


class DBManager:
    def __init__(self):
        self.connections: Dict[str, sqlite3.Connection] = {}

    def initialize_connections(self):
        self.init_db("/volume/db/keyword_cache.db", "keyword_cache")
        self.init_db("/volume/db/jobs.db", "jobs")

    def init_db(self, db_path: str, db_name: str):
        """Initialize a new database connection."""
        if db_name in self.connections:
            raise ValueError(f"Database '{db_name}' is already initialized.")

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self.connections[db_name] = conn

        # Enable WAL mode
        with conn:
            conn.execute("PRAGMA journal_mode=WAL;")

    def initialize_tables(self):
        """Initialize all tables across all modules."""
        from jobs.db import create_tables as create_job_tables
        from keywords.db import create_similar_keywords_table
        from keywords.db import create_table as create_keyword_table

        # Jobs module tables
        with self.get_db("jobs") as conn:
            create_job_tables(conn)

        # Keywords module tables
        with self.get_db("keyword_cache") as conn:
            create_keyword_table(conn)
            create_similar_keywords_table(conn)

    def close_db(self, db_name: str):
        """Close a specific database connection."""
        if db_name in self.connections:
            self.connections[db_name].close()
            del self.connections[db_name]

    def close_all_db(self):
        """Close all database connections."""
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()

    @contextmanager
    def get_db(self, db_name: str):
        if db_name not in self.connections:
            self.connections[db_name] = sqlite3.connect(
                f"/path/to/{db_name}.db", check_same_thread=False
            )
            self.connections[db_name].row_factory = sqlite3.Row

        conn = self.connections[db_name]
        try:
            yield conn
        except sqlite3.Error:
            conn.rollback()
            raise
        else:
            conn.commit()

    def execute_query(self, db_name: str, query: str, params: Any = None):
        """Execute a query on a specific database."""
        with self.get_db(db_name) as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def execute_many(self, db_name: str, query: str, params: list):
        """Execute a query with multiple parameter sets on a specific database."""
        with self.get_db(db_name) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params)


# Create a single instance of DBManager
db_manager = DBManager()
