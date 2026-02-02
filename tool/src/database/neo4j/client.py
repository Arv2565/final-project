"""
Neo4j client utilities for GraphRAG.

Reads connection details from environment variables:
- NEO4J_URI (e.g., bolt://localhost:7687)
- NEO4J_USER
- NEO4J_PASSWORD
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from neo4j import GraphDatabase, Driver, Session

_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise RuntimeError("NEO4J_PASSWORD env var not set")
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


@contextmanager
def neo4j_session(database: Optional[str] = None) -> Iterator[Session]:
    driver = get_neo4j_driver()
    session = driver.session(database=database) if database else driver.session()
    try:
        yield session
    finally:
        session.close()


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
