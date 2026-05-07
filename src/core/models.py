from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Post:
    """A Reddit post in canonical form, used across all pipeline stages."""

    post_id: str
    subreddit: str
    author: str
    title: str
    selftext: str
    score: int
    num_comments: int
    created_utc: datetime
