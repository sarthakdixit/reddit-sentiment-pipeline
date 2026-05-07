# AGENT.md

> Instructions for AI coding assistants (Claude, Cursor, Copilot, etc.) working on this repository.
> This file is loaded into every prompt. Treat its rules as non-negotiable.

---

## 1. Project context

This is a portfolio-grade data engineering pipeline. It ingests Reddit posts, scores their sentiment, models them into a star schema, and visualises them in Power BI. The pipeline runs on Azure (Functions, ADLS, Container Apps, Postgres Flexible Server), is deployed via Bicep, and is built using hexagonal architecture with dependency injection so the same code runs locally (Docker Compose) and in the cloud.

The project optimises for three things, in order:

1. Architectural cleanliness (hexagonal, DI, testability)
2. Cost efficiency (under ₹100/month cloud spend)
3. Reproducibility (one-command local, one-click cloud)

Read `design.md` before making non-trivial changes. It is the source of truth for architecture.

---

## 2. Hard rules — never violate

These are mechanically enforced by CI. Pull requests that violate them are rejected automatically.

### 2.1 Architecture boundaries

`src/core/` is the pure domain layer. It contains business logic and `Protocol` definitions only.

The following imports are banned in `src/core/` and any subdirectory:

```
azure.*
praw
psycopg2
sqlalchemy
boto3
google.cloud.*
requests
httpx
urllib3
pyodbc
pymongo
redis
```

CI runs this check on every PR:

```
grep -rE "^(import|from) (azure|praw|psycopg2|sqlalchemy|boto3|google\.cloud|requests|httpx|urllib3|pyodbc|pymongo|redis)" src/core/ && exit 1 || exit 0
```

If a service in `src/core/` needs to talk to infrastructure, it does so through a `Protocol` defined in `src/core/ports.py`. The concrete implementation lives in `src/adapters/` and is injected at the composition root.

### 2.2 No comments

Code must be self-documenting. The following are banned:

- Inline comments (`# this does X`)
- Block comments
- Trailing comments
- TODO/FIXME/XXX markers (use GitHub issues)

The only allowed prose in source files is docstrings on public APIs (see Section 4.5).

CI runs this check:

```
ruff check --select=E501,ERA --extend-select=T201 src/
```

Plus a custom check that flags any line matching `^\s*#` outside of shebang lines, encoding declarations, and noqa directives.

If you feel the urge to add a comment, do one of the following instead:

- Rename a variable or function so its purpose is obvious
- Extract a helper function with an explanatory name
- Add a unit test that documents the behaviour
- Put the explanation in the commit message
- Open an issue for non-obvious decisions and reference it from the relevant ADR

### 2.3 Test-first development (TDD)

For all changes to `src/core/` and `src/adapters/`:

1. Write a failing test first
2. Run the test, confirm it fails for the right reason
3. Write the minimum code to make it pass
4. Refactor if needed, keeping the test green
5. Commit

Pull requests that add or modify code in `src/` without corresponding test changes are rejected.

Coverage thresholds:

- `src/core/`: minimum 80% line coverage
- `src/adapters/`: minimum 60% line coverage
- `src/composition.py`: not measured (it is wiring, not logic)

TDD does not apply to:

- Bicep modules (validated via `bicep build` and `what-if`)
- dbt models (validated via dbt tests)
- One-off scripts in `scripts/`
- Documentation

### 2.4 No secrets in code

Banned:

- Hardcoded passwords, tokens, API keys, connection strings with credentials
- `.env` files committed to git (`.env.example` is fine)
- Bicep parameters with secrets inlined

CI runs `gitleaks` on every PR.

All secrets come from environment variables, which are sourced from `.env` locally and Azure Key Vault in cloud.

### 2.5 No environment branching in business logic

The string `os.environ.get("ENV")` and equivalents (`if ENV == "local"`, etc.) may appear only in `src/composition.py`. Anywhere else is a violation.

The codebase has exactly one composition root. Services accept dependencies; they do not look them up.

### 2.6 No mutation of input arguments

Functions and methods do not mutate their inputs. They return new values. Lists, dicts, and dataclasses passed in must be untouched on return.

The single exception is adapter classes' internal state (e.g., a connection pool).

---

## 3. Architecture patterns

### 3.1 The composition root pattern

`src/composition.py` is the only file that:

- Reads environment variables
- Imports concrete adapter classes
- Constructs adapters with their config
- Wires adapters into services

Every other file imports from `src/core/` or `src/adapters/` and accepts dependencies through constructors.

### 3.2 Adding a new service to `src/core/`

Workflow:

1. Define the ports it needs in `src/core/ports.py` (or extend existing ones)
2. Write `tests/unit/test_<service>.py` with fakes implementing those ports
3. Implement the service in `src/core/<service>.py`
4. Run tests until green
5. Add a `build_<service>` function to `src/composition.py`
6. Add a CLI entry in `src/cli.py` if appropriate

The service must:

- Accept all infrastructure dependencies via `__init__`
- Use only types from `src/core/ports.py` and `src/core/models.py` in signatures
- Have no module-level state
- Have no I/O (logging via injected logger is fine)

### 3.3 Adding a new adapter to `src/adapters/`

Workflow:

1. Identify the port it implements in `src/core/ports.py`
2. Write `tests/integration/test_<adapter>.py` against the real backing service (Docker)
3. Implement the adapter in `src/adapters/<adapter>.py`
4. Run integration tests against Docker Compose
5. Wire it into `src/composition.py`

The adapter must:

- Implement exactly one `Protocol` from `src/core/ports.py`
- Accept its configuration through `__init__` (connection strings, credentials)
- Be a class, not a module-level function set
- Not import anything from `src/core/` except types

### 3.4 Domain models

`src/core/models.py` contains domain dataclasses. Rules:

- Use `@dataclass(frozen=True, slots=True)` by default
- Fields are typed
- No methods that perform I/O
- Methods that derive values are pure functions
- Use `from __future__ import annotations` at the top of every file in `src/core/`

### 3.5 Errors

Define domain-specific exceptions in `src/core/errors.py`. Adapters wrap library-specific exceptions into domain ones.

Example:

```
class IngestionError(Exception): ...
class RedditUnavailableError(IngestionError): ...
class StorageWriteError(IngestionError): ...
```

Catching `Exception` in business code is banned. Catch the specific domain error.

---

## 4. Python style

### 4.1 Version

Python 3.11. Use modern syntax.

### 4.2 Type hints

Required everywhere. Functions, methods, class attributes, dataclass fields.

```
def fetch_hot(self, subreddit: str, limit: int) -> list[dict]: ...
```

Use built-in generics (`list`, `dict`, `tuple`) — not `typing.List`. Use `X | None` — not `Optional[X]`. Use `from __future__ import annotations` for forward references.

`mypy --strict` runs on `src/core/` in CI.

### 4.3 Dataclasses over dicts

For domain types, use `@dataclass(frozen=True, slots=True)`. Do not pass dicts around between services.

```
@dataclass(frozen=True, slots=True)
class Post:
    id: str
    subreddit: str
    author: str
    score: int
    created_utc: datetime
```

`TypedDict` is acceptable only for representing external API responses at the adapter boundary.

### 4.4 Pathlib over os.path

```
from pathlib import Path
config = Path("config") / "settings.yaml"
```

Never `os.path.join`. Never string concatenation for paths.

### 4.5 Docstrings

Public functions, methods, and classes get a one-line docstring stating what they return or do. Private (`_`-prefixed) members do not.

```
def fetch_hot(self, subreddit: str, limit: int) -> list[dict]:
    """Return the top N hot posts for a subreddit as raw dicts."""
```

No examples, no Args/Returns sections, no multi-paragraph docstrings. If more explanation is needed, the function is doing too much — split it.

### 4.6 Naming

- Modules: `snake_case`
- Classes: `PascalCase`
- Functions, methods, variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Protocol classes: noun describing capability (`StorageClient`, `RedditClient`, `SentimentScorer`)
- Adapter classes: `<Tech>Adapter` (`PRAWAdapter`, `AzureBlobAdapter`)
- Service classes: `<Domain>Service` (`IngestionService`, `TransformService`)
- Test files: `test_<module>.py`
- Test functions: `test_<scenario>` describing behaviour, not implementation

### 4.7 Imports

Order: stdlib, third-party, first-party. Within each group, alphabetical.

```
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from azure.storage.blob import BlobServiceClient

from src.core.ports import StorageClient
```

Banned:

- `from x import *`
- Relative imports beyond one level (`from ..foo` is allowed, `from ...foo` is not)
- Importing from `src/core/` into `src/adapters/` of anything other than `ports`, `models`, `errors`

### 4.8 Function size

Functions over 20 lines or with cyclomatic complexity over 8 are rejected by `ruff`. Split them.

### 4.9 Logging

Use `structlog`. Inject the logger into services through their constructor. Do not call `logging.getLogger(__name__)` in business code.

```
class IngestionService:
    def __init__(self, reddit: RedditClient, storage: StorageClient, logger: BoundLogger):
        ...
```

In adapters, module-level `logger = structlog.get_logger(__name__)` is acceptable.

### 4.10 String formatting

f-strings only. No `%`-formatting, no `.format()`, no string concatenation in loops.

### 4.11 Booleans and conditions

Use truthiness only for the obvious cases (`if posts:` for non-empty list). For domain conditions, write explicit predicates with descriptive names.

```
if has_reached_rate_limit(response):
    raise RedditRateLimitError(...)
```

---

## 5. Testing

### 5.1 Layout

```
tests/
├── unit/                  # Tests src/core/ — fakes only, no Docker
│   ├── conftest.py
│   ├── fakes.py           # FakeRedditAdapter, InMemoryStorageAdapter
│   ├── test_ingestion.py
│   ├── test_transform.py
│   └── test_quality.py
└── integration/           # Tests src/adapters/ against real Docker services
    ├── conftest.py
    ├── test_storage_azure.py
    ├── test_reddit_praw.py
    └── test_warehouse_postgres.py
```

### 5.2 Unit test rules

- Every test in `tests/unit/` runs in under 100ms
- No network calls
- No filesystem writes (use `tmp_path` if needed)
- No Docker
- Fakes live in `tests/unit/fakes.py` and implement the same `Protocol`s as real adapters
- Use `pytest`, not `unittest`
- Use plain `assert`, not `self.assertEqual`

### 5.3 Integration test rules

- Run against `docker compose up -d` services
- Tagged with `@pytest.mark.integration`
- Skipped automatically if Docker is not running (use a `conftest.py` skip marker)
- Test exactly one adapter at a time
- Clean up after themselves (truncate tables, delete blobs)

### 5.4 Naming and structure (AAA)

```
def test_ingest_writes_posts_to_bronze_storage():
    fake_reddit = FakeRedditAdapter(fixtures=[{"id": "a"}, {"id": "b"}])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    count = service.ingest("technology", limit=2)

    assert count == 2
    assert "bronze" in fake_storage.contents
```

Three blocks separated by blank lines: arrange, act, assert. No comments labelling the blocks (the structure speaks for itself).

### 5.5 Fixtures

Shared fixtures go in `conftest.py`. Test-specific data lives in the test. Avoid `pytest.fixture` for things that can be plain function calls.

### 5.6 Parametrize aggressively

When a behaviour has multiple cases, use `@pytest.mark.parametrize`. One test function, many cases.

```
@pytest.mark.parametrize("score,label", [
    (-0.8, "negative"),
    (0.0, "neutral"),
    (0.8, "positive"),
])
def test_sentiment_label_for_score(score, label):
    assert classify_sentiment(score) == label
```

---

## 6. SQL & dbt

### 6.1 Style

- Lowercase keywords (`select`, not `SELECT`)
- Trailing commas
- One column per line in `select` lists
- Table aliases are short (`p`, `a`, `s`) for fact and dim tables
- CTEs over subqueries

`sqlfluff` enforces this; CI fails on violations.

### 6.2 dbt model layout

```
dbt/models/
├── staging/       # One per source table; light cleanup only
├── intermediate/  # Joins and enrichment; never exposed
└── marts/         # Final fact and dim tables; analytics-facing
```

### 6.3 dbt model rules

- Every model has a YAML schema definition
- Every model has at minimum: `not_null` on PKs, `unique` on PKs, `relationships` on FKs
- `accepted_values` on every enumerated column (e.g., `sentiment_label`)
- Custom tests live in `dbt/tests/`
- Materializations: staging is `view`, intermediate is `ephemeral`, marts is `table`

### 6.4 Naming

- Staging: `stg_<source>_<entity>` (`stg_reddit_posts`)
- Intermediate: `int_<entity>_<verb>` (`int_posts_enriched`)
- Marts: `fct_<entity>` for facts, `dim_<entity>` for dimensions

---

## 7. Bicep

### 7.1 Module rules

- One Bicep file per logical resource group
- Files are under 100 lines
- Parameters are explicit and typed
- Outputs are minimal — only what other modules need
- No hardcoded values; everything goes through parameters or variables

### 7.2 Naming convention

`<resource-type>-<project>-<env>-<region>` — `st-redditpipe-dev-cin`, `psql-redditpipe-dev-cin`.

### 7.3 Validation

`bicep build` runs in CI. `bicep lint` warnings are treated as errors.

### 7.4 Secrets

Never inline secrets in `.bicep` or `.bicepparam` files. Use Key Vault references:

```
@secure()
param postgresAdminPassword string
```

passed in from a Key Vault secret reference at deploy time.

---

## 8. Git & commits

### 8.1 Branching

- `main` is protected; deploys from there
- Feature branches: `feat/<short-description>`
- Fix branches: `fix/<short-description>`
- Docs branches: `docs/<short-description>`

### 8.2 Commit message format

Conventional Commits:

```
feat(ingestion): add reddit comment fetching to PRAW adapter

The IngestionService now optionally fetches top-25 comments per post.
Closes #42.
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`.

The body explains the *why* (since the code has no comments). The header explains the *what*.

### 8.3 PR requirements

A PR is mergeable when:

- CI is green (all checks pass)
- Coverage thresholds are met
- The architecture boundary check passes
- The `gitleaks` scan passes
- At least one human-readable description is in the PR body
- Linked to an issue if it implements one

---

## 9. Workflow for AI assistants

When asked to add or change code, follow this exact sequence:

1. Read `design.md` if the change touches architecture
2. Read this file (`AGENT.md`) — done if you're seeing this
3. Identify which layer the change belongs in (`core`, `adapter`, `composition`, `infra`, `dbt`)
4. If `core` or `adapter`: write the failing test first
5. Run the test to confirm it fails
6. Implement the minimum to pass
7. Run the full test suite
8. Run linters (`ruff`, `black`, `mypy`, `sqlfluff`, `bicep build` as applicable)
9. Run the architecture boundary grep
10. Commit with a Conventional Commit message
11. Output a one-line summary for the human

When in doubt about a design choice, ask the human before coding. Do not invent patterns not listed in this document.

---

## 10. What "done" looks like

A change is done when:

- [ ] Tests pass locally (`pytest`)
- [ ] Linters pass (`make lint`)
- [ ] mypy passes on `src/core/` (`mypy --strict src/core/`)
- [ ] Architecture boundary check passes (`make check-architecture`)
- [ ] Coverage threshold met
- [ ] No secrets committed
- [ ] No comments added
- [ ] No environment branching outside `composition.py`
- [ ] Commit message follows Conventional Commits
- [ ] PR description explains the *why*

If any item is unchecked, the change is not done. Do not push.

---

## 11. Things you must never suggest

- Adding `requests` or `httpx` to `src/core/`
- "Just for now" inline comments
- Try/except `Exception` in business code
- Hardcoded connection strings
- Singleton pattern via module-level state
- Adding a DI library (`punq`, `dependency-injector`, etc.) — see ADR-0006
- Adding a pure-filesystem storage adapter — see "Out of scope" in design.md
- Streaming, Kafka, Event Hubs — see "Out of scope"
- Unit tests that depend on Docker
- Integration tests that don't clean up
- Renaming services or ports without updating `design.md`

---

## 12. Things you should suggest

- Extract a helper when a function exceeds 20 lines
- Add a port if a service starts taking concrete adapter types
- Add a dataclass if a service starts passing dicts around
- Add a test if you spot a bug
- Add an ADR if a non-trivial architectural choice is being made
- Update `design.md` if scope changes
- Update this file (`AGENT.md`) if a rule needs to evolve

---

*Last updated: 2026-05-06. Edit this file when conventions change.*
