"""
This module contains jobs to be queued up as part of a product offering
for a given client.

FIXME: Figure out how to handle a job invoker specifying the model to use
    - This may need to be specifiable as either a single model for the
    entire job, or a model for each prompt, a model for prompts 1-3, and
    a different model for prompts 4-6, etc.

Anatomy of a typical job:
    - Analyze input data and how it relates to the stock description in the job itself
    - Take that analysis and iterate on it a couple times
    - Use the final, iterated analysis to generate specific guidelines for each step in the job
    - Taking all of that as input, go through the steps in that specific job

Does having this much prior analysis justify coding a kind of "job runner" that takes an array
of prompt strings with their I/O variables (similar to HDL?) and then go through it all?
    - inputs must pre-exist
    - outputs can be new or can overwrite/append/prepend existing values
    - job function args would be variables available to be inputs for these prompt definitions
    - maybe jobs create an object that holds all of these inputs and outputs?
        - that would let me just output all of the outputs at the end of the job
        - this means it'd be easier to store the job record in a database
    - {
        "prompt": "string",
        "inputs": {
            "input1": "type",
            "input2": "type"
        },
        "outputs": {
            "output1": "type",
            "output2": "type"
        }
    }
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

import keywords
from db import db_manager
from keywords.embedding import embedding_service
from .tasks import TaskType

logger = logging.getLogger(__name__)


def serialize_job_data(data: dict) -> dict:
    """Recursively convert Pydantic Url objects to strings."""
    for key, value in data.items():
        if isinstance(value, BaseModel):
            data[key] = serialize_job_data(value.dict())
        elif isinstance(value, dict):
            data[key] = serialize_job_data(value)
        elif hasattr(value, "__str__"):  # This will catch Url objects
            data[key] = str(value)
    return data


class VersionManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def create_version(self, task_id: str, result: Any) -> int:
        logger.debug(f"Creating version for task {task_id}")
        with self.db_manager.get_db("jobs") as conn:
            cursor = conn.cursor()
            try:
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
                logger.info(f"Successfully created version {version_id} for task {task_id}")
                return version_id
            except Exception as e:
                logger.error(f"Error creating version for task {task_id}: {str(e)}")
                conn.rollback()
                raise

    async def get_version(self, task_id: str, version_id: int = None) -> Any:
        logger.debug(f"Getting version for task {task_id}, version_id: {version_id}")
        with self.db_manager.get_db("jobs") as conn:
            if version_id is None:
                row = conn.execute(
                    """
                    SELECT result
                    FROM current_task_versions
                    WHERE task_id = ?
                """,
                    (task_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT result
                    FROM task_versions
                    WHERE id = ? AND task_id = ?
                """,
                    (version_id, task_id),
                ).fetchone()

            if row is None or row["result"] is None:
                logger.warning(f"No result found for task {task_id}, version_id: {version_id}")
                return None

            try:
                return json.loads(row["result"])
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for task {task_id}, version_id: {version_id}")
                return None

    async def list_versions(self, task_id: str) -> List[Dict[str, Any]]:
        logger.debug(f"Listing versions for task {task_id}")
        with self.db_manager.get_db("jobs") as conn:
            rows = conn.execute(
                """
                SELECT id, task_id, created_at
                FROM task_versions
                WHERE task_id = ?
                ORDER BY id
            """,
                (task_id,),
            ).fetchall()

        versions = [dict(row) for row in rows]
        logger.debug(f"Versions for task {task_id}: {json.dumps(versions, indent=2)}")
        return versions

    async def compare_versions(
        self, task_id: str, version_id1: int, version_id2: int
    ) -> Dict[str, Any]:
        version1 = await self.get_version(task_id, version_id1)
        version2 = await self.get_version(task_id, version_id2)

        # Implement your comparison logic here
        # This is a simple example, you might want to use a more sophisticated diff algorithm
        differences = {}
        all_keys = set(version1.keys()) | set(version2.keys())
        for key in all_keys:
            if key not in version1:
                differences[key] = {"old": None, "new": version2[key]}
            elif key not in version2:
                differences[key] = {"old": version1[key], "new": None}
            elif version1[key] != version2[key]:
                differences[key] = {"old": version1[key], "new": version2[key]}

        return differences

    async def get_latest_version(self, task_id: str) -> Dict[str, Any]:
        with self.db_manager.get_db("jobs") as conn:
            row = conn.execute(
                """
                SELECT tv.*
                FROM task_versions tv
                JOIN current_task_versions ctv ON tv.id = ctv.version_id
                WHERE ctv.task_id = ?
                """,
                (task_id,)
            ).fetchone()
            return dict(row) if row else None


class JobManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.task_types = [
            TaskType.PROCESS_INITIAL_INPUT,
            TaskType.GENERATE_SIMILAR_KEYWORDS,
            TaskType.SELECT_BEST_KEYWORDS,
            TaskType.GENERATE_CLUSTERS,
            TaskType.SELECT_BEST_CLUSTER,
            TaskType.GENERATE_HTML,
        ]
        self.version_manager = VersionManager(db_manager)
        self.latest_versions = {}

    async def create_job(self, job_data: Dict[str, Any]) -> str:
        job_id = str(uuid4())
        logger.info(f"Creating new job with ID: {job_id}")
        
        with self.db_manager.get_db("jobs") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (id, status, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    "pending",
                    json.dumps(job_data),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        
        await self.create_tasks_for_job(job_id, job_data)
        
        logger.info(f"Job {job_id} created successfully")
        return job_id

    async def create_tasks_for_job(self, job_id: str, job_data: Dict[str, Any]):
        for order, task_type in enumerate(self.task_types):
            task_id = str(uuid4())
            with self.db_manager.get_db("jobs") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO job_tasks (id, job_id, task_type, task_order, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        job_id,
                        task_type.name,
                        order,
                        "pending",
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            logger.debug(f"Created task: {task_id} of type {task_type.name} for job {job_id}")

    async def process_tasks(self):
        logger.info("Starting task processing loop")
        while True:
            try:
                task = await self.get_next_pending_task()
                if not task:
                    await asyncio.sleep(1)
                    continue

                logger.info(f"Processing task: {task['id']} of type {task['task_type']} for job {task['job_id']}")
                await self.log_job_state(task['job_id'])
                try:
                    result = await self.execute_task(task)
                    await self.update_task_result(task, result)

                    if task["task_type"] != self.task_types[-1].name:
                        await self.prepare_next_task(task)
                    else:
                        await self.check_job_completion(task["job_id"])
                except Exception as e:
                    logger.exception(f"Error processing task: {str(e)}")
                    await self.update_task_status(task["job_id"], task["id"], "failed")
                    # Continue with the next task instead of sleeping
                    continue

            except Exception as e:
                logger.exception(f"Unexpected error in process_tasks: {str(e)}")
                await asyncio.sleep(5)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def execute_task(self, task):
        logger.info(f"Executing task: {json.dumps(task, indent=2)}")
        task_type = TaskType[task["task_type"]]
        handler = getattr(self, f"handle_{task_type.name.lower()}", None)
        if not handler:
            raise ValueError(f"No handler for task type: {task['task_type']}")

        result = await handler(task["job_id"], task["id"])
        version_id = await self.version_manager.create_version(task["id"], result)
        self.latest_versions[task["id"]] = version_id
        await self.update_task_status(task["job_id"], task["id"], "completed")
        await self.update_task_current_version(task["id"], version_id)

        # Log the full job state
        try:
            full_job_state = await self.get_job_with_tasks_and_versions(task["job_id"])
            logger.info(f"Full job state after task {task['id']} completion: {json.dumps(full_job_state, indent=2)}")
        except Exception as e:
            logger.error(f"Failed to get full job state: {str(e)}")

        return result

    async def update_task_result(self, task, result):
        version_id = await self.version_manager.create_version(task["id"], result)
        self.latest_versions[task["id"]] = version_id
        await self.update_task_status(task["job_id"], task["id"], "completed")
        await self.update_task_current_version(task["id"], version_id)

    async def prepare_next_task(self, current_task):
        next_task = await self.get_next_task(current_task["job_id"], current_task["task_order"])
        if next_task:
            await self.update_task_status(next_task["job_id"], next_task["id"], "pending")

    async def rollback_job(self, job_id):
        with db_manager.get_db("jobs") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM job_tasks WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        logger.info(f"Rolled back job {job_id} due to disk full error")

    async def get_job_data(self, job_id: str) -> Dict[str, Any]:
        with db_manager.get_db("jobs") as conn:
            job = conn.execute(
                "SELECT data FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            return json.loads(job["data"]) if job else None

    async def get_next_pending_task(self):
        logger.debug("Fetching next pending task")
        with self.db_manager.get_db("jobs") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, job_id, task_type, task_order
                FROM job_tasks
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            task = cursor.fetchone()
            
        if task:
            logger.debug(f"Found pending task: {task[0]}")
            return {
                "id": task[0],
                "job_id": task[1],
                "task_type": task[2],
                "task_order": task[3],
            }
        else:
            logger.debug("No pending tasks found")
            return None

    async def get_next_task(self, job_id: str, current_task_order: int):
        with db_manager.get_db("jobs") as conn:
            return conn.execute(
                """
                SELECT * FROM job_tasks
                WHERE job_id = ? AND task_order = ?
            """,
                (job_id, current_task_order + 1),
            ).fetchone()

    async def update_task_status(self, job_id: str, task_id: str, status: str):
        with self.db_manager.get_db("jobs") as conn:
            conn.execute(
                """
                UPDATE job_tasks
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, datetime.now(timezone.utc).isoformat(), task_id),
            )
            conn.commit()

    async def check_job_completion(self, job_id: str):
        with db_manager.get_db("jobs") as conn:
            incomplete_tasks = conn.execute(
                """
                SELECT COUNT(*) FROM job_tasks
                WHERE job_id = ? AND status != 'completed'
            """,
                (job_id,),
            ).fetchone()[0]

            if incomplete_tasks == 0:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'completed', updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now(timezone.utc).isoformat(), job_id),
                )
                logger.info(f"Job {job_id} completed")

    async def get_detailed_job_status(self, job_id: str) -> Dict[str, Any]:
        with db_manager.get_db("jobs") as conn:
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not job:
                logger.warning(f"No job found with id {job_id}")
                return None

            tasks = conn.execute(
                """
                SELECT jt.id, jt.task_type, jt.status, tv.result
                FROM job_tasks jt
                LEFT JOIN current_task_versions ctv ON jt.id = ctv.task_id
                LEFT JOIN task_versions tv ON ctv.version_id = tv.id
                WHERE jt.job_id = ?
                ORDER BY jt.task_order
            """,
                (job_id,),
            ).fetchall()

        logger.debug(f"Raw tasks data for job {job_id}: {json.dumps([dict(t) for t in tasks], indent=2)}")

        return {
            "job_id": job_id,
            "status": job["status"],
            "tasks": [
                {
                    "id": t["id"],
                    "type": t["task_type"],
                    "status": t["status"],
                    "data": json.loads(t["result"]) if t["result"] else None,
                }
                for t in tasks
            ],
        }

    async def rerun_task(self, task_id: str):
        with db_manager.get_db("jobs") as conn:
            task = conn.execute(
                "SELECT * FROM job_tasks WHERE id = ?", (task_id,)
            ).fetchone()

        if not task:
            raise ValueError(f"No task found with id: {task_id}")

        handler = getattr(self, f"handle_{task['task_type']}", None)
        if not handler:
            raise ValueError(f"No handler for task type: {task['task_type']}")

        result = await handler(task["job_id"], task["id"])
        version_id = await self.version_manager.create_version(task["id"], result)
        self.latest_versions[task["id"]] = version_id
        await self.update_task_status(task["job_id"], task["id"], "completed")
        await self.update_task_current_version(task["id"], version_id)

    async def update_task_current_version(self, task_id: str, version_id: int):
        with db_manager.get_db("jobs") as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO current_task_versions (task_id, version_id)
                VALUES (?, ?)
            """,
                (task_id, version_id),
            )
        logger.info(f"Updated current version for task {task_id} to {version_id}")

    async def get_task_current_version(self, task_id: str):
        return self.latest_versions.get(task_id)

    async def get_previous_task_data(self, job_id: str, task_type: str):
        logger.info(f"Attempting to get previous task data for job {job_id}, task type {task_type}")
        detailed_status = await self.get_detailed_job_status(job_id)
        for task in detailed_status['tasks']:
            if task['type'] == task_type:
                logger.info(f"Found previous task {task['id']} with status {task['status']}")
                if task['status'] == 'completed':
                    versions = await self.version_manager.list_versions(task['id'])
                    logger.info(f"Versions for task {task['id']}: {versions}")
                    if versions:
                        latest_version = max(versions, key=lambda v: v['id'])
                        result = await self.version_manager.get_version(task['id'], latest_version['id'])
                        if result is not None:
                            logger.info(f"Retrieved result for task {task['id']}, version {latest_version['id']}")
                            return result
                        else:
                            logger.warning(f"No result found for task {task['id']}, version {latest_version['id']}")
                    else:
                        logger.warning(f"No versions found for completed task {task['id']}")
                else:
                    logger.warning(f"Previous task {task['id']} of type {task_type} for job {job_id} has status: {task['status']}")
        logger.error(f"No completed task of type {task_type} found for job {job_id}")
        return None

    # Handler methods

    async def handle_process_initial_input(self, job_id: str, task_id: str):
        def parse_json_or_list(value):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return [value]
            return [str(value)]
        try:
            job_data = await self.get_job_data(job_id)
            if not job_data:
                raise ValueError(f"No job data found for job {job_id}")

            # Process the input data
            processed_data = {
                "company_string": f"Basic company profile: \n Name: {job_data['companyName']}\n Description: {job_data['companyDescription']}\n Website: {job_data['companyUrl']}",
                "page_string": f"Page to generate:\n URL: {job_data['current_page']['url']}\n Title: {job_data['current_page']['title']}\n Info: {job_data['current_page']['info']}\n USP: {job_data['current_page']['usp']}\n Is New Page: {job_data['current_page']['is_new']}",
                "locations": parse_json_or_list(job_data["locations"]),
                "seed_keywords": parse_json_or_list(job_data["seedKeywords"]),
                "page_type": job_data["pageType"],
            }
            
            logger.info(f"Processed data for job {job_id}: {processed_data}")
            
            # Store the processed data
            version_id = await self.version_manager.create_version(task_id, processed_data)
            logger.info(f"Stored processed data for task {task_id}, version {version_id}")
            
            return processed_data
        except Exception as e:
            logger.error(f"Error in handle_process_initial_input for job {job_id}: {str(e)}")
            raise

    async def handle_generate_similar_keywords(self, job_id: str, task_id: str):
        try:
            logger.info(f"Starting handle_generate_similar_keywords for job {job_id}")
            previous_task_data = await self.get_previous_task_data(job_id, TaskType.PROCESS_INITIAL_INPUT.name)
            if not previous_task_data:
                logger.error(f"Previous task data not found for job {job_id}")
                raise ValueError("Previous task data not found")

            locations = previous_task_data.get("locations", [])
            seed_keywords = previous_task_data.get("seed_keywords", [])

            if not locations or not seed_keywords:
                logger.error(f"Invalid previous task data for job {job_id}: locations or seed_keywords missing")
                raise ValueError("Invalid previous task data")

            logger.info(f"Generating similar keywords for job {job_id}")
            logger.info(f"Locations: {locations}")
            logger.info(f"Seed keywords: {seed_keywords}")

            similar_kw_dict = {}
            full_kw_list = []

            for loc in locations:
                results = await keywords.get_similar_multi(seed_keywords, loc)
                similar_kw_dict[loc] = results
                for kw in results:
                    full_kw_list.extend(results[kw])

            # Remove duplicates
            full_kw_list = list(set(full_kw_list))

            result = {
                "similar_kw_dict": similar_kw_dict,
                "full_kw_list": full_kw_list,
            }

            logger.info(f"Generated similar keywords for job {job_id}")
            await self.version_manager.create_version(task_id, result)
            logger.info(f"Stored similar keywords for task {task_id}")

            return result
        except Exception as e:
            logger.error(f"Error in handle_generate_similar_keywords for job {job_id}: {str(e)}")
            raise

    async def handle_select_best_keywords(self, job_id: str, task_id: str) -> Dict[str, List[str]]:
        previous_data = await self.get_previous_task_data(job_id, TaskType.GENERATE_SIMILAR_KEYWORDS.name)
        if not previous_data:
            raise ValueError("Previous task data not found")
        full_kw_list = previous_data["full_kw_list"]
        initial_input_data = await self.get_previous_task_data(job_id, TaskType.PROCESS_INITIAL_INPUT.name)
        if not initial_input_data:
            raise ValueError("Initial input data not found")
        seed_keywords = initial_input_data["seed_keywords"]

        bucketed = {}
        for kw in seed_keywords:
            bucketed[kw] = embedding_service.bucket_cosine(
                kw, full_kw_list, center_type="keyword"
            )

        centroid = embedding_service.get_centroid(seed_keywords)
        bucketed["seed centroid"] = embedding_service.bucket_cosine(
            centroid, full_kw_list, center_type="embedding"
        )

        best_keywords = {}
        for page in bucketed:
            temp = []
            for bucket, kw_list in bucketed[page].items():
                if float(bucket) >= 0.69:
                    temp.extend(kw_list)
            best_keywords[page] = temp

        await self.version_manager.create_version(task_id, best_keywords)
        return best_keywords

    async def handle_generate_clusters(self, job_id: str, task_id: str) -> List[Dict[str, Any]]:
        previous_data = await self.get_previous_task_data(job_id, TaskType.GENERATE_SIMILAR_KEYWORDS.name)
        if not previous_data:
            raise ValueError("Previous task data not found")
        full_kw_list = previous_data["full_kw_list"]
        initial_input_data = await self.get_previous_task_data(job_id, TaskType.PROCESS_INITIAL_INPUT.name)
        if not initial_input_data:
            raise ValueError("Initial input data not found")
        seed_keywords = initial_input_data["seed_keywords"]

        clustered = embedding_service.hierarchical_clustering(
            full_kw_list, len(seed_keywords)
        )

        clusters = [
            {"cluster_id": i, "keywords": cluster}
            for i, cluster in enumerate(clustered)
        ]
        await self.version_manager.create_version(task_id, clusters)
        return clusters

    async def handle_select_best_cluster(self, job_id: str, task_id: str):
        previous_data = await self.get_previous_task_data(job_id, TaskType.GENERATE_CLUSTERS.name)
        if not previous_data:
            raise ValueError("Previous task data not found")
        clusters = previous_data
        initial_input_data = await self.get_previous_task_data(job_id, TaskType.PROCESS_INITIAL_INPUT.name)
        if not initial_input_data:
            raise ValueError("Initial input data not found")
        page_string = initial_input_data["page_string"]

        # Here, you might want to implement a more sophisticated cluster selection method
        # For now, we'll just select the cluster with the highest similarity to the page_string
        best_cluster = max(clusters, key=lambda c: embedding_service.cosine_similarity(page_string, " ".join(c["keywords"])))
        result = {"best_cluster": best_cluster}
        await self.version_manager.create_version(task_id, result)
        return result

    async def handle_generate_html(self, job_id: str, task_id: str):
        best_cluster = await self.get_previous_task_data(job_id, TaskType.SELECT_BEST_CLUSTER.name)
        if not best_cluster:
            raise ValueError("Best cluster data not found")
        initial_data = await self.get_previous_task_data(job_id, TaskType.PROCESS_INITIAL_INPUT.name)
        if not initial_data:
            raise ValueError("Initial data not found")
        company_info = initial_data.get("company_string", "")
        page_info = initial_data.get("page_string", "")

        # Here, you might want to use a language model to generate the HTML content
        # For now, we'll create a simple HTML structure
        html = f"""
        <html>
        <head>
            <title>{initial_data['page_type']} Page</title>
        </head>
        <body>
            <h1>{initial_data['page_type']} Page</h1>
            <h2>Company Information</h2>
            <p>{company_info}</p>
            <h2>Page Information</h2>
            <p>{page_info}</p>
            <h2>Keywords</h2>
            <ul>
                {"".join(f"<li>{keyword}</li>" for keyword in best_cluster['best_cluster']['keywords'])}
            </ul>
        </body>
        </html>
        """

        result = {"generated_html": html}
        await self.version_manager.create_version(task_id, result)
        return result

    async def get_job_with_tasks_and_versions(self, job_id: str) -> Dict[str, Any]:
        job_data = await self.get_job_data(job_id)
        if not job_data:
            logger.warning(f"No job data found for job {job_id}")
            return None

        detailed_status = await self.get_detailed_job_status(job_id)
        logger.debug(f"Detailed status for job {job_id}: {json.dumps(detailed_status, indent=2)}")
        
        tasks_with_versions = []
        for task in detailed_status['tasks']:
            logger.debug(f"Processing task in get_job_with_tasks_and_versions: {json.dumps(task, indent=2)}")
            task_versions = await self.version_manager.list_versions(task['id'])
            logger.debug(f"Versions for task {task['id']}: {json.dumps(task_versions, indent=2)}")
            task_with_versions = {
                'id': task['id'],
                'type': task['type'],
                'status': task['status'],
                'versions': []
            }
            for version in task_versions:
                version_result = await self.version_manager.get_version(task['id'], version['id'])
                if version_result is not None:
                    task_with_versions['versions'].append({
                        'id': version['id'],
                        'created_at': version['created_at'],
                        'result': version_result
                    })
                else:
                    logger.warning(f"No result found for task {task['id']}, version {version['id']}")
            tasks_with_versions.append(task_with_versions)

        return {
            'job_id': job_id,
            'status': detailed_status['status'],
            'data': job_data,
            'tasks': tasks_with_versions
        }

    async def log_job_state(self, job_id: str):
        job_data = await self.get_job_data(job_id)
        detailed_status = await self.get_detailed_job_status(job_id)
        full_job_state = await self.get_job_with_tasks_and_versions(job_id)
        
        logger.info(f"Current state of job {job_id}:")
        logger.info(f"Job data: {json.dumps(job_data, indent=2)}")
        logger.info(f"Detailed status: {json.dumps(detailed_status, indent=2)}")
        logger.info(f"Full job state: {json.dumps(full_job_state, indent=2)}")


job_manager = JobManager(db_manager)


async def start_job_processing():
    await job_manager.process_tasks()


if __name__ == "__main__":
    asyncio.run(start_job_processing())
