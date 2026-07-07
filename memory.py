"""Cognee semantic memory integration for Vagus Graph."""

from __future__ import annotations

import importlib
import os
from types import ModuleType


REQUIRED_COGNEE_ENV_VARS = (
    "GRAPH_DATABASE_PROVIDER",
    "GRAPH_DATABASE_URL",
    "GRAPH_DATABASE_USERNAME",
    "GRAPH_DATABASE_PASSWORD",
    "LLM_API_KEY",
)


def load_dotenv_if_available() -> None:
    """Load local .env values when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


load_dotenv_if_available()


class MemoryConfigurationError(RuntimeError):
    """Raised when Cognee or its environment is not ready."""


def validate_cognee_environment() -> None:
    """Validate environment needed for Cognee backed by Neo4j Aura."""
    missing = [key for key in REQUIRED_COGNEE_ENV_VARS if not os.environ.get(key)]
    if missing:
        joined = ", ".join(missing)
        raise MemoryConfigurationError(f"Missing Cognee environment variables: {joined}")


def load_cognee() -> ModuleType:
    """Load Cognee after environment validation."""
    validate_cognee_environment()
    try:
        return importlib.import_module("cognee")
    except ImportError as exc:
        raise MemoryConfigurationError("The cognee package is not installed.") from exc


async def persist_cognitive_correlation(
    task_title: str,
    metabolic_state: str,
) -> None:
    """Persist a cognitive fatigue correlation in Cognee semantic memory."""
    cognee = load_cognee()
    context = (
        f"Task '{task_title}' causes intense executive fatigue when "
        f"physiological state is {metabolic_state}."
    )
    try:
        await cognee.add(context)
        await cognee.cognify()
    except Exception as exc:
        raise MemoryConfigurationError(
            "Failed to persist cognitive correlation with Cognee.",
        ) from exc
