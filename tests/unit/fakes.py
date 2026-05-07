from __future__ import annotations

from typing import Any


class FakeRedditAdapter:
    def __init__(self, fixtures: list[dict[str, Any]]) -> None:
        self._fixtures = fixtures
        self.calls: list[tuple[str, int]] = []

    def fetch_hot(self, subreddit: str, limit: int) -> list[dict[str, Any]]:
        self.calls.append((subreddit, limit))
        return self._fixtures[:limit]


class InMemoryStorageAdapter:
    def __init__(self) -> None:
        self.contents: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def write_json(self, container: str, path: str, data: list[dict[str, Any]]) -> None:
        self.contents.setdefault(container, {})[path] = list(data)

    def read_json(self, container: str, path: str) -> list[dict[str, Any]]:
        return list(self.contents[container][path])

    def list_paths(self, container: str, prefix: str) -> list[str]:
        bucket = self.contents.get(container, {})
        return sorted(p for p in bucket if p.startswith(prefix))
