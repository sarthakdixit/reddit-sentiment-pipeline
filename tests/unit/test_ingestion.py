from __future__ import annotations

import pytest

from src.core.ingestion import IngestionService
from tests.unit.fakes import FakeRedditAdapter, InMemoryStorageAdapter


def test_ingest_writes_posts_to_bronze_container() -> None:
    fake_reddit = FakeRedditAdapter(fixtures=[{"id": "a"}, {"id": "b"}, {"id": "c"}])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    count = service.ingest(subreddit="technology", limit=3)

    assert count == 3
    assert "bronze" in fake_storage.contents
    written_paths = list(fake_storage.contents["bronze"].keys())
    assert len(written_paths) == 1


def test_ingest_returns_zero_when_reddit_returns_nothing() -> None:
    fake_reddit = FakeRedditAdapter(fixtures=[])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    count = service.ingest(subreddit="empty", limit=10)

    assert count == 0


def test_ingest_passes_subreddit_and_limit_to_reddit_client() -> None:
    fake_reddit = FakeRedditAdapter(fixtures=[{"id": "a"}, {"id": "b"}])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    service.ingest(subreddit="python", limit=2)

    assert fake_reddit.calls == [("python", 2)]


def test_ingest_writes_under_partitioned_path() -> None:
    fake_reddit = FakeRedditAdapter(fixtures=[{"id": "a"}])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    service.ingest(subreddit="news", limit=1)

    paths = list(fake_storage.contents["bronze"].keys())
    assert paths[0].startswith("raw/dt=")
    assert paths[0].endswith("/posts.json")


def test_ingest_writes_exact_payload_received_from_reddit() -> None:
    fixtures = [{"id": "x", "title": "hello"}, {"id": "y", "title": "world"}]
    fake_reddit = FakeRedditAdapter(fixtures=fixtures)
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    service.ingest(subreddit="any", limit=2)

    written = next(iter(fake_storage.contents["bronze"].values()))
    assert written == fixtures


def test_ingest_rejects_zero_or_negative_limit() -> None:
    fake_reddit = FakeRedditAdapter(fixtures=[])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    with pytest.raises(ValueError):
        service.ingest(subreddit="any", limit=0)

    with pytest.raises(ValueError):
        service.ingest(subreddit="any", limit=-1)
