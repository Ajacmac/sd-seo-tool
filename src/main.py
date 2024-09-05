import argparse
import asyncio
import logging
import os
import sqlite3
from contextlib import asynccontextmanager

import uvicorn
from config import CORS_ORIGINS, DEBUG, SECRET_KEY
from db import db_manager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jobs import job_manager
from starlette.middleware.sessions import SessionMiddleware
from web.routes import router as api_router


def check_schema(db_manager):
    with db_manager.get_db("jobs") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        # logger.info("Current 'jobs' table schema:")
        for column in columns:
            logger.info(f"- {column[1]} ({column[2]})")


REINITIALIZE_DB = os.environ.get("REINITIALIZE_DB", "false").lower() == "true"


def table_exists(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    return cursor.fetchone() is not None


def initialize_database(db_manager):
    with db_manager.get_db("jobs") as conn:
        try:
            conn.execute("BEGIN TRANSACTION")

            tables_to_drop = ["jobs", "job_tasks", "task_versions"]
            for table in tables_to_drop:
                if table_exists(conn, table):
                    logger.info(f"Dropping table: {table}")
                    conn.execute(f"DROP TABLE {table}")
                else:
                    logger.info(f"Table {table} does not exist, skipping drop")
            logger.info("Tables dropped successfully")

            logger.info("Creating new tables")
            create_tables_sql = """
                CREATE TABLE jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT,
                    data JSON,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                );
                
                CREATE TABLE job_tasks (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    task_id TEXT,
                    task_type TEXT,
                    task_order INTEGER,
                    status TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    selected_version_id TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );
                
                CREATE TABLE task_versions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    version_number INTEGER,
                    result TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES job_tasks(id)
                );
            """
            conn.executescript(create_tables_sql)
            logger.info("New tables created successfully")

            conn.commit()
            logger.info("Transaction committed")

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"An error occurred: {e}")
            raise

        finally:
            logger.info("Verifying 'jobs' table schema:")
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(jobs)")
            columns = cursor.fetchall()
            for column in columns:
                logger.info(f"- {column[1]} ({column[2]})")

        logger.info("Database initialization complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager.initialize_connections()
    initialize_database(db_manager)
    db_manager.initialize_tables()
    check_schema(db_manager)

    task = asyncio.create_task(job_manager.process_tasks())
    logger.info("Job processing task created")

    yield

    logger.info("Server shutdown")
    task.cancel()  # Cancel the task on shutdown
    try:
        await task  # Wait for the task to be cancelled
    except asyncio.CancelledError:
        logger.info("Job processing task cancelled")
    db_manager.close_all_db()


app = FastAPI(
    title="SEO Tool API",
    description="API for SEO Tool",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600,  # or however long you want sessions to last
    same_site="lax",  # or "strict" depending on your security requirements
    https_only=True,  # if you're using HTTPS (recommended)
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
    ],
)

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"message": "An unexpected error occurred."}
    )


def start(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI server")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on"
    )
    args = parser.parse_args()

    start(host=args.host, port=args.port)
