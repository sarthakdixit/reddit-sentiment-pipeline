from __future__ import annotations

from typing import Any, Protocol


class RedditClient(Protocol):
    """Read posts from a Reddit-like source."""

    def fetch_hot(self, subreddit: str, limit: int) -> list[dict[str, Any]]: ...


class StorageClient(Protocol):
    """Write and read JSON blobs to a key-value object store."""

    def write_json(self, container: str, path: str, data: list[dict[str, Any]]) -> None: ...

    def read_json(self, container: str, path: str) -> list[dict[str, Any]]: ...

    def list_paths(self, container: str, prefix: str) -> list[str]: ...
