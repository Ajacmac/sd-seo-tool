from enum import Enum
from typing import NamedTuple


class TaskSpec(NamedTuple):
    description: str
    input_schema: dict
    output_schema: dict
    is_deterministic: bool


class TaskType(Enum):
    PROCESS_INITIAL_INPUT = TaskSpec(
        description="Process and validate initial user input",
        input_schema={
            "type": "object",
            "properties": {
                "client_data": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "company_description": {"type": "string"},
                        "company_url": {"type": "string"},
                        "locations": {"type": "array", "items": {"type": "string"}},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "company_name",
                        "company_description",
                        "company_url",
                        "locations",
                    ],
                }
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "company_string": {"type": "string"},
                "locations": {"type": "array", "items": {"type": "string"}},
                "client_provided_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        is_deterministic=True,
    )
    GENERATE_SIMILAR_KEYWORDS = TaskSpec(
        description="Generate similar keywords for each location",
        input_schema={
            "type": "object",
            "properties": {
                "locations": {"type": "array", "items": {"type": "string"}},
                "client_provided_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "similar_kw_dict": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "full_kw_list": {"type": "array", "items": {"type": "string"}},
            },
        },
        is_deterministic=False,
    )
    SELECT_BEST_KEYWORDS = TaskSpec(
        description="Select best keywords based on relevance",
        input_schema={
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": {"type": "array", "items": {"type": "string"}},
            },
        },
        output_schema={
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
        is_deterministic=True,
    )
    GENERATE_CLUSTERS = TaskSpec(
        description="Cluster keywords into groups",
        input_schema={
            "type": "object",
            "properties": {
                "full_kw_list": {"type": "array", "items": {"type": "string"}},
                "client_provided_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        output_schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "integer"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        is_deterministic=True,
    )
    SELECT_BEST_CLUSTER = TaskSpec(
        description="Select the best cluster based on relevance",
        input_schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "integer"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "best_cluster": {
                    "type": "object",
                    "properties": {
                        "cluster_id": {"type": "integer"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        is_deterministic=True,
    )
    GENERATE_HTML = TaskSpec(
        description="Generate HTML content based on selected keywords",
        input_schema={
            "type": "object",
            "properties": {
                "best_cluster": {
                    "type": "object",
                    "properties": {
                        "cluster_id": {"type": "integer"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "company_string": {"type": "string"},
                "page_string": {"type": "string"},
            },
        },
        output_schema={"type": "string"},
        is_deterministic=False,
    )


def validate_task_type(task_type: str) -> bool:
    return task_type in TaskType.__members__


def get_task_spec(task_type: str) -> TaskSpec:
    return TaskType[task_type].value
