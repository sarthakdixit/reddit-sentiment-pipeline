from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.core.ports import RedditClient, StorageClient


class IngestionService:
    """Fetch posts from a Reddit-like source and write them to bronze storage."""

    BRONZE_CONTAINER = "bronze"

    def __init__(self, reddit: RedditClient, storage: StorageClient) -> None:
        self._reddit = reddit
        self._storage = storage

    def ingest(self, subreddit: str, limit: int) -> int:
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        posts = self._reddit.fetch_hot(subreddit, limit)
        path = self._build_bronze_path()
        self._storage.write_json(self.BRONZE_CONTAINER, path, posts)
        return len(posts)

    @staticmethod
    def _build_bronze_path() -> str:
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        run_id = uuid4().hex[:8]
        return f"raw/dt={date}/run={run_id}/posts.json"
