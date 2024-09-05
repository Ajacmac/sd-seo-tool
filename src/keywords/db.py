"""
This file contains all of the db management for the keyword cache.

When a keyword is requested, the cache is checked first. If the keyword is
not in the cache, the keyword is fetched from the provider and then stored.

FIXME: Probably needs to have the db connection be opened and closed in main.py
and passed in as a parameter to the functions here.

TODO: Also, the db_manager.get_db_connection function needs to be implemented or forgotten or something

FIXME: Make sure the upsert is good

TODO: Should the db be checked for/removing old keyword data on startup?
    - Would keep the cache from getting too big
    - Might not be needed. It'll depend on how many keywords we end up researching.
"""

import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from db import db_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def create_table(conn: sqlite3.Connection):
    """
    Creates the keywords table in the database if it does not already exist

    Each keyword is stored as a row in the table with the keyword as the primary key
    """

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    location TEXT NOT NULL,
                    search_volume INTEGER DEFAULT 0,
                    cpc REAL DEFAULT -1,
                    has_cpc BOOLEAN DEFAULT 0,
                    competition REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    appearance_count INTEGER DEFAULT 1,
                    UNIQUE(keyword, location)
                );
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_keyword ON keywords(keyword);"
            )
            logger.info("keywords table initialized successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize keywords table: {e}")


def create_similar_keywords_table(conn: sqlite3.Connection):
    """
    FIXME: Finish this

    Creates the similar keywords table in the database if it does not already exist
    """

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS similar_keyword_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                location TEXT NOT NULL,
                response_json TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                search_count INTEGER DEFAULT 1,
                UNIQUE(keyword, location)
            );""")

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_search_phrase ON similar_keyword_searches(keyword);"
            )
            logger.info("similar_keyword_searched table initialized successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize similar_keyword_searched table: {e}")


def drop_table(table_name):
    """
    Drops a table from the database
    """

    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            logger.info(f"Dropped table: {table_name}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to drop table: {table_name} - {e}")


def validate_keyword_data(data):
    """
    Validates the keyword data before inserting it into the database
    """

    required_fields = ["keyword", "search_volume", "cpc", "has_cpc", "competition"]
    if not all(field in data for field in required_fields):
        data_str = json.dumps(data)
        logger.error(f"Missing required fields in keyword data: {data_str}")
        logger.error(f"Required fields: {required_fields}")
        raise ValueError("Missing required fields in keyword data.")
    if not isinstance(data["search_volume"], int) or data["search_volume"] < 0:
        raise ValueError("Invalid search volume")
    if not isinstance(data["cpc"], (int, float)):
        raise ValueError("Invalid CPC")
    if not isinstance(data["has_cpc"], bool):
        raise ValueError("Invalid has_cpc value")
    if (
        not isinstance(data["competition"], (int, float))
        or not 0 <= data["competition"] <= 1
    ):
        raise ValueError("Invalid competition value")


def get_keyword(keyword: str, location) -> Dict[str, Any]:
    """
    Fetches a keyword from the database
    Returns the keyword data if it exists and is less than 3 months old, otherwise None
    """

    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM keywords WHERE keyword = ? AND location = ?;",
                (keyword, location),
            )
            row = cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Database error in get_keyword: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_keyword: {e}")
        return None

    if row:
        return {
            "keyword": row[1],
            "location": row[2],
            "search_volume": row[3],
            "cpc": None if not row[5] else row[4],  # Return None if has_cpc is False
            "competition": row[6],
            "timestamp": row[7],
            "last_updated": row[8],
            "appearance_count": row[9],
        }
    else:
        return None


def get_similar_keyword_search(keyword: str, location: str) -> Dict[str, Any]:
    """
    Fetches similar keywords for a given keyword and location from the database
    Returns the data if it exists and is less than 3 months old, otherwise None
    """

    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM similar_keyword_searches WHERE keyword = ? AND location = ?;",
                (keyword, location),
            )
            row = cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Database error in get_similar_keyword_search: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_similar_keyword_search: {e}")
        return None

    if row:
        last_updated = datetime.fromisoformat(row[4]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_updated < timedelta(days=90):
            return {
                "keyword": row[1],
                "location": row[2],
                "response_json": row[3],
                "timestamp": row[4],
                "last_updated": row[5],
                "search_count": row[6],
            }
    return None


def insert_similar_keyword_search(
    keyword: str, data: Dict[str, Any], location: str
):  # FIXME: Handle location data
    """
    Inserts similar keywords for a given keyword into the database

    If the keyword already exists, the data is updated
    """

    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO similar_keyword_searches (keyword, location, response_json, last_updated, search_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(keyword, location) DO UPDATE SET
                    response_json = excluded.response_json,
                    last_updated = CURRENT_TIMESTAMP,
                    search_count = search_count + 1
            """,
                (keyword, location, json.dumps(data), datetime.now(timezone.utc)),
            )
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error in insert_similar_keyword_search: {e}")
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in insert_similar_keyword_search: {e}")
        return False


def insert_keyword(keyword: str, keyword_data: Dict[str, Any], location: str):
    """
    Inserts a keyword and its data into the database

    If the keyword already exists, the data is updated
    """

    try:
        cpc_value = keyword_data.get("cpc")
        has_cpc = cpc_value not in (None, "", "-1")
        has_sv = keyword_data.get("search volume") not in (None, "", "-1")
        transformed_data = {
            "keyword": keyword,
            "search_volume": int(keyword_data.get("search volume", 0)) if has_sv else 0,
            "cpc": float(cpc_value) if has_cpc else -1,
            "has_cpc": has_cpc,
            "competition": float(keyword_data.get("paid competition", 0.0)),
        }
        validate_keyword_data(transformed_data)
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO keywords (keyword, location, search_volume, cpc, has_cpc, competition, last_updated, appearance_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(keyword, location) DO UPDATE SET
                    search_volume = excluded.search_volume,
                    cpc = CASE WHEN excluded.has_cpc THEN excluded.cpc ELSE keywords.cpc END,
                    has_cpc = CASE WHEN excluded.has_cpc THEN 1 ELSE keywords.has_cpc END,
                    competition = excluded.competition,
                    last_updated = CURRENT_TIMESTAMP,
                    appearance_count = appearance_count + 1
            """,
                (
                    keyword,
                    location,
                    transformed_data["search_volume"],
                    transformed_data["cpc"],
                    transformed_data["has_cpc"],
                    transformed_data["competition"],
                    datetime.now(timezone.utc),
                ),
            )
            # force_checkpoint()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(
            f"Database error in insert_keyword for keyword: {keyword}\nError: {e}"
        )
        raise
    except Exception as e:
        conn.rollback()
        logger.error(
            f"Unexpected error in insert_keyword for keyword: {keyword}\nError: {e}"
        )
        raise


def force_checkpoint():
    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA wal_checkpoint(FULL);")
            logger.info("Forced a full WAL checkpoint")
    except sqlite3.Error as e:
        logger.error(f"SQLite error occurred while forcing a checkpoint: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred while forcing a checkpoint: {e}")


def manual_search(sql_string: str):
    """
    Allows manual SQL queries to be run on the database
    """

    try:
        with db_manager.get_db("keyword_cache") as conn:
            cursor = conn.cursor()
            cursor.execute(sql_string)
            rows = cursor.fetchall()
            return rows
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error in manual_search: {e}")
        return None
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in manual_search: {e}")
        return None
