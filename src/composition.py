from __future__ import annotations

import os

from src.core.ingestion import IngestionService
from src.core.ports import RedditClient, StorageClient


def build_ingestion_service() -> IngestionService:
    reddit = _build_reddit_client()
    storage = _build_storage_client()
    return IngestionService(reddit=reddit, storage=storage)


def _build_reddit_client() -> RedditClient:
    mode = os.environ.get("APP_MODE", "cloud")
    if mode == "walking-skeleton":
        from tests.unit.fakes import FakeRedditAdapter

        return FakeRedditAdapter(fixtures=_walking_skeleton_fixtures())
    raise NotImplementedError(
        f"Reddit client for APP_MODE={mode!r} not yet implemented; "
        "real PRAW adapter lands in batch 3."
    )


def _build_storage_client() -> StorageClient:
    mode = os.environ.get("APP_MODE", "cloud")
    if mode == "walking-skeleton":
        from tests.unit.fakes import InMemoryStorageAdapter

        return InMemoryStorageAdapter()
    raise NotImplementedError(
        f"Storage client for APP_MODE={mode!r} not yet implemented; "
        "real AzureBlobAdapter lands in batch 3."
    )


def _walking_skeleton_fixtures() -> list[dict[str, object]]:
    return [
        {"id": "fake1", "title": "Walking skeleton works", "score": 42},
        {"id": "fake2", "title": "Hexagonal architecture proven", "score": 17},
        {"id": "fake3", "title": "Ready for real adapters", "score": 8},
    ]
