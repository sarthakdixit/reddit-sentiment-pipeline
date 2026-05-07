# Reddit Sentiment Analytics Pipeline — Design Document

> **Status:** Approved | **Version:** 2.0 | **Owner:** [Your Name]

A cost-optimised, on-demand data engineering pipeline that ingests Reddit posts, scores their sentiment, models them into a star schema, and visualises them in Power BI — all on Azure, deployed via Bicep, for under ₹100/month. Built with hexagonal architecture and dependency injection so the same code runs locally and in the cloud with a single environment-variable change.

---

## Table of Contents

1. [Elevator Pitch](#1-elevator-pitch)
2. [Project Goals](#2-project-goals)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Out of Scope](#5-out-of-scope)
6. [High-Level Architecture](#6-high-level-architecture)
7. [Tech Stack](#7-tech-stack)
8. [Architecture & DI Strategy](#8-architecture--di-strategy)
9. [Local Development Environment](#9-local-development-environment)
10. [Folder Structure](#10-folder-structure)
11. [Bicep Module Design](#11-bicep-module-design)
12. [Data Model](#12-data-model)
13. [Run Sequence](#13-run-sequence)
14. [Cost Analysis](#14-cost-analysis)
15. [Failure Modes & Recovery](#15-failure-modes--recovery)
16. [Security](#16-security)
17. [Implementation Phases](#17-implementation-phases)
18. [Success Criteria](#18-success-criteria)
19. [Architecture Decision Records](#19-architecture-decision-records)
20. [Open Questions](#20-open-questions)

---

## 1. Elevator Pitch

> *Build an on-demand Reddit sentiment analytics pipeline on Azure using Bicep IaC, with Functions for ingestion, ADLS for the lake, Container Apps for transforms, Postgres for the warehouse, dbt for modelling, GitHub Actions for orchestration, and a Power BI dashboard committed as a static artifact. The codebase uses hexagonal architecture with dependency injection so the same business logic runs against local Docker services or live Azure with a single env-var change. Built locally first, deployed to cloud second, stays under ₹100/month via deploy-on-demand-then-destroy.*

This project demonstrates the full data engineering lifecycle (ingest → store → transform → model → quality → serve) while solving three real engineering constraints simultaneously: extreme cost-efficiency, Linux-first development, and clean separation between business logic and infrastructure.

---

## 2. Project Goals

| Goal | Why it matters |
|---|---|
| Showcase end-to-end DE skills for a job-ready portfolio | Recruiters scan portfolios for breadth across the DE lifecycle |
| Build hands-on Azure data services experience | Azure is a major cloud for DE roles, especially in consulting/enterprise |
| Operate within a ₹100/month hard budget | Forces real-world architectural trade-offs that mirror startup constraints |
| Practice IaC discipline with Bicep | Bicep is Azure-native; signals infra fluency to recruiters |
| Demonstrate clean architecture & testability | Hexagonal + DI signals software-engineering maturity beyond just "wires services together" |
| Develop locally first, then promote to cloud | Reflects how professional teams actually work; faster iteration; ₹0 dev cost |
| Produce a polished, reproducible artifact | A repo that runs cleanly with one command beats an impressive but broken one |

---

## 3. Functional Requirements

### FR1. Data Source
- **Source:** Reddit (single subreddit, configurable via parameter)
- **Library:** PRAW (Python Reddit API Wrapper)
- **Default subreddit:** `r/technology` (configurable via env var)
- **Data captured per run:** Top 100 hot posts + each post's top 25 comments
- **Authentication:** OAuth via Reddit script app (credentials in `.env` locally, Key Vault in cloud)

### FR2. Pipeline Trigger
- **Mode:** Manual only via GitHub Actions `workflow_dispatch`
- **Operator action:** Click "Run workflow" on `deploy-and-run.yml`
- **No schedules, no cron, no event triggers** — fully on-demand

### FR3. Pipeline Stages (Medallion Architecture)
| Layer | Format | Storage | Purpose |
|---|---|---|---|
| Bronze | Raw JSON | Azurite (local) / ADLS Gen2 (cloud) | Immutable record of API response |
| Silver | Parquet (partitioned by date) | Azurite (local) / ADLS Gen2 (cloud) | Cleaned, deduplicated, sentiment-scored |
| Gold | Star schema tables | Postgres in Docker (local) / Postgres Flexible Server (cloud) | Analytics-ready, BI-friendly |

### FR4. Data Retention
- **Bronze + Silver:** 7-day rolling window in storage, enforced via lifecycle management policy in cloud (manual cleanup script locally)
- **Gold:** Refreshed on every run (full rebuild from current Silver snapshot)
- **Power BI snapshot:** Latest export retained indefinitely in storage for offline dashboard use

### FR5. Visualization
- **Tool:** Power BI Desktop (free, used one-time on a Windows VM/loaner machine)
- **Artifact:** `.pbix` file committed to `/viz/powerbi/dashboard.pbix`
- **Documentation:** 4–6 high-quality PNG screenshots embedded in `README.md`
- **Dashboard pages:**
  1. Overview — KPIs (total posts, avg sentiment, top author)
  2. Sentiment trend — daily sentiment line chart with rolling 24h average
  3. Top topics — word frequency / topic visual
  4. Author activity — leaderboard + post-volume distribution
  5. Anomaly view — sentiment spikes vs baseline

### FR6. Orchestration
- **Tool:** GitHub Actions (free for public repos)
- **Workflows:**
  - `ci.yml` — runs on every PR: lint Python, lint SQL, validate Bicep, run unit tests
  - `deploy-and-run.yml` — manual: full deploy → run → destroy cycle
  - `destroy.yml` — manual: emergency teardown only

---

## 4. Non-Functional Requirements

### NFR1. Cost
- **Hard cap:** ₹100/month total cloud spend
- **Strategy:** On-demand provisioning; only persistent resources stay between runs (~₹2–5/mo)
- **Local dev cost:** ₹0 (Docker Compose only)
- **Guardrails:**
  - Azure budget alert at ₹50 (email notification)
  - GitHub Actions includes mandatory `bicep destroy` step in `if: always()` block
  - No always-on resources permitted in `main.bicep`

### NFR2. Architecture
- **Pattern:** Hexagonal (Ports and Adapters)
- **DI mechanism:** Plain Python `typing.Protocol` — no DI framework
- **Composition root:** Single function (`composition.py::build_*_service`) reads env vars and wires dependencies
- **Core domain isolation:** No `azure.*`, `praw`, or `psycopg2` imports in `src/core/`
- **Environments:** Two only — `local` (Docker Compose) and `cloud` (Azure)

### NFR3. Infrastructure as Code
- **Tool:** Bicep (Azure-native)
- **Structure:** Modular — one file per logical resource group
- **Parameters:** Environment-specific via `.bicepparam` files
- **Validation:** `bicep build` runs in CI on every PR

### NFR4. CI/CD
- **Linting:** black, ruff (Python); sqlfluff (SQL); `bicep build` (IaC)
- **Tests:** pytest unit tests for core domain (no Docker required); integration tests against Docker services
- **Pre-commit hooks:** All linters run before commit
- **Branch protection:** Main branch requires green CI

### NFR5. Code Quality
- **Python:** Type hints required; black formatting; ruff linting; mypy strict on `src/core/`
- **SQL:** dbt tests on every model (not_null, unique, accepted_values, custom)
- **Bicep:** No hardcoded secrets; all sensitive values from Key Vault
- **Test coverage target:** ≥80% for `src/core/` (high standard since core has no external deps); ≥60% for `src/adapters/`

### NFR6. Documentation
- **README.md** — portfolio-facing; pitch, architecture diagram, screenshots, run instructions, cost evidence
- **design.md** — this document
- **docs/adr/** — Architecture Decision Records for key choices
- **docs/runbook.md** — operational guide for running and debugging
- **docs/cost-analysis.md** — actual vs estimated cost breakdown with screenshots

### NFR7. Reproducibility
- A reviewer cloning the repo must be able to:
  1. Run `docker compose up -d` and have local services ready
  2. Run `make ingest && make transform && make model` and see data flow end-to-end locally
  3. Set 4 GitHub secrets and click "Run workflow" once for cloud deployment
  4. View the resulting dashboard via committed `.pbix` and screenshots

---

## 5. Out of Scope

Explicitly **not** in v1 — listed in README as "v2 enhancements":

- Real-time streaming (Event Hubs, Kafka, Stream Analytics)
- Multiple subreddits or cross-subreddit comparisons
- ML models beyond VADER sentiment (e.g., topic modeling, transformer-based sentiment)
- Always-on dashboards (Power BI Service publishing requires paid license)
- Multi-environment promotion (dev/staging/prod) — single environment only
- Data catalog / lineage tooling (Microsoft Purview, OpenLineage)
- User-facing API or webhook delivery
- Authentication for the dashboard (it's a static `.pbix`)
- Pure-filesystem storage adapter (Azure Blob SDK works for both Azurite and ADLS — no need for a third)

---

## 6. High-Level Architecture

### 6.1 The two environments

The same codebase runs in two modes selected by environment variables:

| Concern | Local mode | Cloud mode |
|---|---|---|
| Storage connection string | Azurite default | ADLS Gen2 connection |
| Postgres URL | `localhost:5432` | Azure Flexible Server FQDN |
| Reddit credentials | `.env` file | Key Vault references |
| Compute trigger | `make` / direct invocation | GitHub Actions → Functions/Container Apps |
| Bicep | Not used | Provisions everything |

Crucially: **the Python code does not branch on environment.** Adapters are constructed in one place from env vars; everything downstream uses interface types.

### 6.2 The flow

```
[Reddit API] → [Function: ingest] → [Bronze JSON storage]
                                          ↓
                            [Container Job: transform]
                                          ↓
                                  [Silver Parquet storage]
                                          ↓
                            [dbt run + test → Postgres]
                                          ↓
                                    [Gold star schema]
                                          ↓
                            [Great Expectations validation]
                                          ↓
                            [Export gold to storage]
                                          ↓
                            [Power BI Desktop reads gold offline]
```

In cloud mode, this is bracketed by `bicep deploy` (start) and `bicep destroy` (end).

In local mode, all services are already running via Docker Compose; just run the Python steps.

---

## 7. Tech Stack

| Layer | Technology | Justification |
|---|---|---|
| Source | Reddit API via PRAW | Free, well-documented, generous rate limits |
| Trigger (cloud) | GitHub Actions `workflow_dispatch` | Free for public repos; YAML in repo is documentation |
| Trigger (local) | `make` targets / direct CLI | Zero overhead, fastest dev loop |
| IaC | Bicep | Azure-native; cleaner than ARM JSON |
| Ingestion compute | Azure Functions (Python, Consumption) | 1M free executions/month; right-sized for small batch |
| Local storage emulator | Azurite (Microsoft's official emulator, in Docker) | Same Blob/ADLS API as cloud; zero cost |
| Cloud lake storage | ADLS Gen2 (LRS, Hot tier) | Cheapest persistent Azure storage; lifecycle policies |
| Transformation compute | Container Apps Job (Pandas in Docker) | Free tier covers 180k vCPU-sec/month; PySpark unnecessary at this scale |
| Local warehouse | Postgres 16 in Docker | Identical SQL to Azure Postgres; runs offline |
| Cloud warehouse | Postgres Flexible Server (B1ms, stop-when-idle) | Cheap when stopped; same SQL |
| Modeling | dbt-core (Postgres adapter) | Industry-standard SQL transformation framework + tests |
| Quality | Great Expectations | Recognised quality framework; complements dbt tests |
| Visualization | Power BI Desktop (free, one-time use on Windows VM) | Industry standard; PBIX committed to repo |
| Secrets (local) | `.env` file (gitignored) | Standard pattern; well understood |
| Secrets (cloud) | Azure Key Vault + GitHub Secrets | Proper separation of secrets from code |
| Monitoring | Azure budget alerts + App Insights free tier | Cost guardrail + operational visibility |
| Languages | Python 3.11, SQL, Bicep, YAML | Standard DE toolkit |
| DI mechanism | Python stdlib `typing.Protocol` | No external dependency; structural typing |
| Dev tooling | black, ruff, sqlfluff, pytest, pre-commit, mypy | Code quality enforcement |

---

## 8. Architecture & DI Strategy

### 8.1 Hexagonal Architecture (Ports and Adapters)

The codebase is split into three concentric layers:

**Inner layer — `src/core/`:** Pure business logic. Contains:
- `ports.py` — `Protocol` definitions describing what we need (e.g., a thing that can write JSON)
- `ingestion.py`, `transform.py`, `quality.py` — services that operate on ports
- `models.py` — domain dataclasses (Post, SentimentScore, etc.)

**No core file imports `azure.*`, `praw`, `psycopg2`, or any infrastructure SDK.** This layer is plain Python that runs anywhere — laptop, container, lambda — and is fully unit-testable in milliseconds.

**Outer layer — `src/adapters/`:** Infrastructure implementations. One concrete class per port. Each adapter knows about exactly one technology.

**Wiring layer — `src/composition.py`:** The single file that knows about environments. Reads env vars, instantiates adapters, hands them to services. Nothing else does this.

### 8.2 Why DI matters here

Without DI:
```python
def ingest(subreddit):
    reddit = praw.Reddit(...)
    posts = reddit.subreddit(subreddit).hot()
    blob = BlobServiceClient.from_connection_string(...)
    blob.upload_blob(json.dumps(posts))
```

This code is impossible to test without Reddit and Azurite running. It's also impossible to swap to S3 without rewriting it.

With DI:
```python
class IngestionService:
    def __init__(self, reddit: RedditClient, storage: StorageClient):
        self._reddit = reddit
        self._storage = storage

    def ingest(self, subreddit: str) -> int:
        posts = self._reddit.fetch_hot(subreddit, limit=100)
        self._storage.write_json("bronze", path_for(subreddit), posts)
        return len(posts)
```

This code:
- Tests in milliseconds with fakes
- Doesn't care if storage is Azurite, ADLS, or future-S3
- Has zero env-checking branches
- Has one job and does it well

### 8.3 Why plain `Protocol`, not a DI library

`typing.Protocol` is Python's structural typing primitive. Any class with the right methods *is* a `StorageClient` — no inheritance required. This gives us:

- Type-checked interfaces (mypy enforces them)
- Zero external dependencies
- No "magic" — wiring is a plain function call
- ~20 lines for the entire DI setup

DI frameworks like `punq` and `dependency-injector` shine when you have 50+ services with complex lifecycle requirements (singletons, scoped, transient). For ~5 services, they add ceremony without value. **Choosing not to use them is itself a senior signal.**

### 8.4 Concrete example

`src/core/ports.py`:
```python
from typing import Protocol

class RedditClient(Protocol):
    def fetch_hot(self, subreddit: str, limit: int) -> list[dict]: ...

class StorageClient(Protocol):
    def write_json(self, container: str, path: str, data: list[dict]) -> None: ...
    def read_json(self, container: str, path: str) -> list[dict]: ...
    def list_paths(self, container: str, prefix: str) -> list[str]: ...

class WarehouseClient(Protocol):
    def execute(self, sql: str) -> None: ...
    def fetch_all(self, sql: str) -> list[tuple]: ...
```

`src/adapters/storage_azure.py` — one adapter, two modes (Azurite via local connection string, ADLS via cloud):
```python
from azure.storage.blob import BlobServiceClient
import json

class AzureBlobAdapter:
    def __init__(self, connection_string: str):
        self._client = BlobServiceClient.from_connection_string(connection_string)

    def write_json(self, container: str, path: str, data: list[dict]) -> None:
        blob = self._client.get_blob_client(container=container, blob=path)
        blob.upload_blob(json.dumps(data), overwrite=True)
```

`src/composition.py` — the entire wiring:
```python
import os
from .core.ingestion import IngestionService
from .adapters.storage_azure import AzureBlobAdapter
from .adapters.reddit_praw import PRAWAdapter

def build_ingestion_service() -> IngestionService:
    storage = AzureBlobAdapter(os.environ["STORAGE_CONNECTION_STRING"])
    reddit = PRAWAdapter(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="reddit-pipeline/1.0",
    )
    return IngestionService(reddit=reddit, storage=storage)
```

That's the whole DI setup. No env-checking. The connection string itself decides whether the SDK talks to Azurite or ADLS.

### 8.5 Testing pattern

Unit tests construct services directly with fakes:
```python
class FakeRedditAdapter:
    def __init__(self, fixtures): self._fixtures = fixtures
    def fetch_hot(self, subreddit, limit): return self._fixtures[:limit]

class InMemoryStorageAdapter:
    def __init__(self): self.contents = {}
    def write_json(self, container, path, data):
        self.contents.setdefault(container, {})[path] = data

def test_ingestion_writes_to_storage():
    fake_reddit = FakeRedditAdapter([{"id": "a"}, {"id": "b"}])
    fake_storage = InMemoryStorageAdapter()
    service = IngestionService(reddit=fake_reddit, storage=fake_storage)

    count = service.ingest("technology", limit=2)

    assert count == 2
    assert "bronze" in fake_storage.contents
```

No Docker. No network. Tests run in milliseconds.

### 8.6 Local-to-cloud "migration"

This is the entire migration:

```
# .env (local)
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;...;BlobEndpoint=http://localhost:10000/devstoreaccount1;
POSTGRES_URL=postgresql://dbtuser:localdev@localhost:5432/reddit_warehouse

# Cloud (GitHub Actions secrets)
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=stredditpipedev;...
POSTGRES_URL=postgresql://admin:<keyvault-ref>@psql-redditpipe.postgres.database.azure.com:5432/reddit_warehouse
```

Same Python code. Same Docker images. Different env vars.

---

## 9. Local Development Environment

### 9.1 Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| Docker + Docker Compose | Run all local services | `apt install docker.io docker-compose-plugin` |
| Python 3.11 + venv | Application runtime | `apt install python3.11 python3.11-venv` |
| Azure Functions Core Tools v4 | Run Functions locally | `npm install -g azure-functions-core-tools@4` |
| Azure CLI + Bicep CLI | Bicep linting (deploys later) | `apt install azure-cli && az bicep install` |
| `make` | Task runner | usually preinstalled |

### 9.2 Local services (`docker-compose.yml`)

```yaml
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite
    ports: ["10000:10000", "10001:10001", "10002:10002"]
    volumes: ["./local-data/azurite:/data"]
    command: azurite --blobHost 0.0.0.0 --location /data

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: dbtuser
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: reddit_warehouse
    ports: ["5432:5432"]
    volumes: ["./local-data/postgres:/var/lib/postgresql/data"]
```

One command — `docker compose up -d` — starts both services. Total disk: ~500MB. Total RAM: ~300MB idle.

### 9.3 Local run loop

```bash
make ingest      # runs IngestionService locally → Azurite
make transform   # runs TransformService → Azurite (silver)
make model       # runs dbt → local Postgres
make quality     # runs Great Expectations
make all         # all of the above
```

Total local pipeline run: ~30 seconds.

### 9.4 The local-to-cloud guarantee

To migrate from local to cloud, only **two** things change:

1. **Env vars** — connection strings point at Azure resources instead of localhost
2. **Compute trigger** — Functions/Container Apps invoke entry points instead of `make`

The Python code, dbt project, Docker image, and SQL are byte-for-byte identical.

---

## 10. Folder Structure

```
reddit-sentiment-pipeline/
├── README.md
├── design.md
├── LICENSE
├── .gitignore
├── .env.example
├── .pre-commit-config.yaml
├── Makefile
├── docker-compose.yml
├── pyproject.toml
│
├── src/
│   ├── core/                          # Pure business logic — no infra imports
│   │   ├── __init__.py
│   │   ├── ports.py                   # Protocol definitions
│   │   ├── models.py                  # Domain dataclasses
│   │   ├── ingestion.py               # IngestionService
│   │   ├── transform.py               # TransformService
│   │   └── quality.py                 # QualityService
│   │
│   ├── adapters/                      # Infrastructure implementations
│   │   ├── __init__.py
│   │   ├── storage_azure.py           # Works for Azurite + ADLS
│   │   ├── reddit_praw.py             # Real Reddit
│   │   ├── warehouse_postgres.py      # Works for local + cloud Postgres
│   │   └── sentiment_vader.py         # VADER sentiment scorer
│   │
│   ├── composition.py                 # The wiring — only file with env logic
│   ├── function_app.py                # Azure Function entry point
│   └── cli.py                         # Local CLI entry point
│
├── transforms/
│   ├── Dockerfile                     # For Container Apps Job
│   └── entrypoint.py                  # Calls into src.core via composition
│
├── infra/
│   ├── main.bicep
│   ├── modules/
│   │   ├── storage.bicep
│   │   ├── functions.bicep
│   │   ├── containerapp.bicep
│   │   ├── postgres.bicep
│   │   └── keyvault.bicep
│   ├── parameters/
│   │   └── dev.bicepparam
│   └── README.md
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml.template
│   ├── models/
│   │   ├── staging/stg_reddit_posts.sql
│   │   ├── intermediate/int_posts_enriched.sql
│   │   └── marts/
│   │       ├── fct_posts.sql
│   │       ├── dim_author.sql
│   │       ├── dim_subreddit.sql
│   │       └── dim_date.sql
│   ├── tests/
│   │   └── assert_sentiment_in_range.sql
│   └── seeds/
│       └── dim_date_seed.csv
│
├── quality/
│   ├── expectations/
│   │   └── reddit_posts_suite.json
│   └── run_checks.py
│
├── viz/
│   └── powerbi/
│       ├── dashboard.pbix
│       └── screenshots/
│
├── tests/
│   ├── unit/                          # Tests src/core/ with fakes — milliseconds, no Docker
│   │   ├── test_ingestion.py
│   │   ├── test_transform.py
│   │   └── fakes.py                   # FakeRedditAdapter, InMemoryStorageAdapter
│   └── integration/                   # Tests adapters against real Docker services
│       ├── test_azurite.py
│       └── test_postgres.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-and-run.yml
│       └── destroy.yml
│
└── docs/
    ├── adr/
    │   ├── 0001-on-demand-pattern.md
    │   ├── 0002-functions-over-databricks.md
    │   ├── 0003-postgres-over-synapse.md
    │   ├── 0004-pandas-over-spark.md
    │   ├── 0005-power-bi-static-artifact.md
    │   ├── 0006-hexagonal-architecture-with-di.md
    │   └── 0007-local-first-development.md
    ├── cost-analysis.md
    └── runbook.md
```

**Key structural rule:** if you `grep -r "import azure\|import praw\|import psycopg2" src/core/` you should get zero results. This is mechanically enforced by a CI check.

---

## 11. Bicep Module Design

### 11.1 Module Catalog

| Module | Resources | Persistence | Approx Lines |
|---|---|---|---|
| `storage.bicep` | Storage account, ADLS containers (bronze/silver/gold), lifecycle policy | Persistent | ~50 |
| `keyvault.bicep` | Key Vault, RBAC, secret references | Persistent | ~40 |
| `functions.bicep` | Function App, Consumption plan, App Insights, Storage binding | Ephemeral | ~60 |
| `containerapp.bicep` | Container Apps Environment, Job definition, image reference | Ephemeral | ~50 |
| `postgres.bicep` | Postgres Flexible Server (B1ms), firewall, database, admin secret | Ephemeral | ~45 |

### 11.2 Orchestrator Pattern

`main.bicep` accepts a single boolean parameter:

```bicep
param deployEphemeral bool = true
```

When `true`, all modules deploy. When `false`, only persistent modules deploy — Bicep treats the missing ephemeral resources as deletes. This is how `destroy.yml` works without `az group delete`.

### 11.3 Naming Convention

```
<resource-type>-<project>-<env>-<region>
```

Example: `st-redditpipe-dev-cin` (storage account, project `redditpipe`, dev env, Central India region).

---

## 12. Data Model

### 12.1 Bronze Layer

**Format:** Raw JSON, one file per ingestion run
**Path:** `bronze/raw/dt={YYYY-MM-DD}/run={run_id}/posts.json`
**Schema:** Whatever PRAW returns — no transformation, no cleanup

### 12.2 Silver Layer

**Format:** Parquet, partitioned by date
**Path:** `silver/posts/dt={YYYY-MM-DD}/posts.parquet`

**Schema:**
| Column | Type | Notes |
|---|---|---|
| `post_id` | string | Reddit's `t3_xxxx` ID |
| `subreddit` | string | Lowercase name |
| `author` | string | Username (or `[deleted]`) |
| `title` | string | Cleaned of unicode artifacts |
| `selftext` | string | Body, may be empty |
| `score` | int | Upvotes minus downvotes at fetch time |
| `num_comments` | int | Comment count at fetch time |
| `created_utc` | timestamp | Post creation time, UTC |
| `sentiment_score` | float | VADER compound score, range [-1, 1] |
| `sentiment_label` | string | One of `positive`, `neutral`, `negative` |
| `ingested_at` | timestamp | When this row was processed |

### 12.3 Gold Layer (Star Schema)

**`fct_posts`** — fact table, grain = one Reddit post

| Column | Type | Description |
|---|---|---|
| `post_id` | string | PK |
| `author_key` | string | FK → dim_author |
| `subreddit_key` | string | FK → dim_subreddit |
| `date_key` | int | FK → dim_date (YYYYMMDD) |
| `score` | int | Measure |
| `num_comments` | int | Measure |
| `sentiment_score` | float | Measure |
| `sentiment_label` | string | Degenerate dimension |
| `created_utc` | timestamp | Native timestamp |

**`dim_author`** — author dimension

| Column | Type | Description |
|---|---|---|
| `author_key` | string | PK (hashed username) |
| `username` | string | Display name |
| `first_seen` | timestamp | First time seen in our data |
| `total_posts` | int | Cumulative post count |

**`dim_subreddit`** — subreddit dimension (1 row in v1, scales to N)

**`dim_date`** — date dimension (generated, not derived)

### 12.4 dbt Tests

Built-in tests on every model: `not_null`, `unique`, `relationships`, `accepted_values` on `sentiment_label`.

Custom test:
```sql
SELECT * FROM {{ ref('fct_posts') }}
WHERE sentiment_score < -1 OR sentiment_score > 1
```

---

## 13. Run Sequence

### 13.1 Local run

```bash
docker compose up -d         # azurite + postgres ready
source .venv/bin/activate
make all                     # ingest → transform → model → quality
```

Total time: ~30 seconds. Cost: ₹0.

### 13.2 Cloud run

| Step | Action | Tool | Approx Duration |
|---|---|---|---|
| 1 | Operator clicks "Run workflow" | GitHub UI | — |
| 2 | `bicep deploy --parameters deployEphemeral=true` | GitHub Actions | 3–5 min |
| 3 | Trigger Function via HTTP — Reddit → Bronze | Function App | 30–60 s |
| 4 | Trigger Container Apps Job — Bronze → Silver | Container Apps | 1–2 min |
| 5 | `dbt run && dbt test` — Silver → Gold | GitHub Actions runner | 1–2 min |
| 6 | Run Great Expectations checks | GitHub Actions runner | 30 s |
| 7 | Export gold tables to Parquet in storage | GitHub Actions runner | 30 s |
| 8 | `bicep deploy --parameters deployEphemeral=false` (destroys ephemeral) | GitHub Actions | 2–3 min |

**Total run time:** ~10–15 minutes
**Cost per run:** Estimated ₹0.50–1.00

### 13.3 Operator flow

```bash
# One-time setup
git clone <repo>
cp .env.example .env
docker compose up -d
.venv/bin/pip install -e .

# Local development loop
make all

# Cloud deployment (one-time)
gh secret set AZURE_CREDENTIALS < azure-sp.json
gh secret set REDDIT_CLIENT_ID --body "..."
gh secret set REDDIT_CLIENT_SECRET --body "..."

# Every cloud run
gh workflow run deploy-and-run.yml

# Emergency teardown
gh workflow run destroy.yml
```

---

## 14. Cost Analysis

### 14.1 Local development

**₹0.** Docker on existing Linux machine. No cloud spend until cloud deployment phase.

### 14.2 Per-run cost in cloud

| Resource | Time during run | Rate | Cost |
|---|---|---|---|
| Postgres B1ms | ~15 min | ~₹1.5/hour | ₹0.40 |
| Function App (Consumption) | <1 min | Free tier | ₹0 |
| Container Apps Job | ~2 min | Free tier (180k vCPU-sec/mo) | ₹0 |
| ADLS operations | trivial | ₹0.04 / 10k operations | <₹0.10 |
| Networking (egress) | <100MB | ₹6.65/GB after 5GB free | ₹0 |
| **Total per run** | | | **~₹0.50–1.00** |

### 14.3 Always-on cost (idle, cloud)

| Resource | Monthly cost |
|---|---|
| Storage account (LRS, <1GB) | ₹2–5 |
| Key Vault (operations only) | <₹1 |
| App Insights (90-day retention, low volume) | ₹0 (free tier) |
| **Idle baseline** | **~₹3–6/month** |

### 14.4 Monthly total at 4 cloud runs/week

```
Idle baseline:        ₹5
Runs (16/month × ₹1): ₹16
Buffer:               ₹10
Total:                ₹31
Headroom:             ₹69 under cap
```

### 14.5 Guardrails

1. Azure budget alert configured at ₹50 (email)
2. `destroy.yml` workflow always available
3. GitHub Actions step `if: always()` runs destroy even on prior failures
4. Cost dashboard screenshot in `docs/cost-analysis.md` updated monthly

---

## 15. Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Bicep deploy fails | GitHub Actions step exits non-zero | Auto-trigger `destroy.yml` via `if: always()` |
| Reddit API rate limit | PRAW raises `TooManyRequests` | Exponential backoff (3 attempts), then fail loudly |
| Function timeout (5 min Consumption limit) | App Insights logs | Reduce batch size; only switch to Premium if necessary |
| Container Apps Job OOM | Exit code 137 | Reduce partition size; bump memory to 2GB (still free tier) |
| dbt test failure | dbt exits non-zero | **Skip destroy** — keep Postgres up for debugging |
| Great Expectations failure | GE exits non-zero | Same as dbt — preserve state for inspection |
| `bicep destroy` itself fails | Subsequent run can't deploy | `az group delete -g rg-redditpipe-dev` as nuclear option |
| Postgres connection timeout | dbt connection error | Verify firewall rule allows GitHub Actions IP range |
| ADLS quota exceeded | Storage write fails | Lifecycle policy should prevent; manual cleanup via runbook |
| Local Docker not running | `docker compose ps` shows no services | `docker compose up -d` |

---

## 16. Security

### 16.1 Secrets management

| Secret | Local storage | Cloud storage | Access |
|---|---|---|---|
| Reddit Client ID | `.env` (gitignored) | GitHub Secret + Key Vault | Function App via managed identity (cloud) |
| Reddit Client Secret | `.env` | GitHub Secret + Key Vault | Function App via managed identity (cloud) |
| Postgres password | `.env` | Generated by Bicep, stored in Key Vault | Container Job + dbt via Key Vault reference (cloud) |
| Azure Service Principal | n/a | GitHub Secret `AZURE_CREDENTIALS` | GitHub Actions only |

**No secrets in code, parameter files, or commit history.** `.env` is in `.gitignore`. CI runs `gitleaks` to enforce.

### 16.2 Network

- Postgres firewall: allow GitHub Actions IP ranges + temporary `0.0.0.0/0` (acceptable for ephemeral, public-data project; would never do this in prod)
- ADLS: private container access; SAS tokens generated per-run
- Function App: HTTPS-only, function key required

### 16.3 Identity

- Azure Service Principal for GitHub Actions has scope limited to one resource group
- Function App uses system-assigned managed identity to read Key Vault
- Container Apps Job uses system-assigned managed identity to read Key Vault + ADLS

---

## 17. Implementation Phases

### Phase 1 — Local foundation (Days 1–2)
- Install Docker, Functions Core Tools, Python 3.11
- Write `docker-compose.yml`, `pyproject.toml`, `.env.example`
- Verify Azurite + Postgres start cleanly
- Set up `src/core/` with empty `ports.py` and `models.py`
- Write `Makefile` skeleton

**Deliverable:** Local services run; Python imports work.

### Phase 2 — Local ingestion (Days 3–4)
- Define `RedditClient` and `StorageClient` ports
- Implement `PRAWAdapter` and `AzureBlobAdapter`
- Implement `IngestionService` in core
- Write `composition.py`
- Write unit tests with fakes
- Wire CLI entry point — `make ingest` works against Azurite

**Deliverable:** Bronze layer populated locally; tests pass in <1s.

### Phase 3 — Local transform (Days 5–6)
- Define `SentimentScorer` port
- Implement `VADERSentimentAdapter`
- Implement `TransformService` in core
- Write `Dockerfile` for transform job
- Build image, run with `docker run` against Azurite
- Unit tests for transform logic

**Deliverable:** Silver layer populated locally; image builds.

### Phase 4 — Local modeling (Days 7–8)
- Initialize dbt project pointing at local Postgres
- Write staging + marts models
- Add dbt tests + custom test
- Add `dim_date` seed
- `make model` runs dbt against local Postgres

**Deliverable:** Gold star schema populated locally; all dbt tests pass.

### Phase 5 — Local quality + viz (Days 9–10)
- Add Great Expectations suite
- Wire `make quality`
- Build initial Power BI dashboard against local Postgres (during local run)
- Capture screenshots, commit `.pbix`

**Deliverable:** Full local pipeline runs end-to-end; dashboard exists.

### Phase 6 — Bicep authoring (Days 11–12)
- Write all Bicep modules locally
- `az bicep build` validates syntax
- `az deployment group what-if` previews against Azure subscription
- Do not deploy yet

**Deliverable:** Cloud infrastructure modeled in code, validated.

### Phase 7 — First cloud deployment (Days 13–14)
- Deploy persistent infra (storage + Key Vault) — leave running, costs ~₹5/mo
- Test: run pipeline locally but pointing at cloud storage (just swap connection string)
- Verify same code works against ADLS as it did against Azurite

**Deliverable:** Local code, cloud storage. The DI architecture pays off.

### Phase 8 — Full cloud deployment (Days 15–16)
- Deploy ephemeral resources via GitHub Actions
- End-to-end run in cloud
- Verify destroy works
- Capture cost screenshot

**Deliverable:** One-click cloud pipeline; cost ≤ ₹100/mo.

### Phase 9 — Polish (Days 17–21)
- Write all 7 ADRs
- Write `cost-analysis.md` with real Azure billing screenshots
- Write `runbook.md`
- Polish README with architecture diagrams, screenshots, demo video link
- Record 2–3 minute Loom demo
- Post on LinkedIn

**Deliverable:** Portfolio-ready project.

**Total: ~3 weeks (was 7 in v1).** Local-first compresses the timeline because most issues surface before any cloud touches happen.

---

## 18. Success Criteria

| Criterion | Measurable as |
|---|---|
| Local pipeline works | `docker compose up && make all` runs to green on fresh clone |
| One-command cloud deployment | `gh workflow run deploy-and-run.yml` runs to green without intervention |
| One-command teardown | `gh workflow run destroy.yml` removes all ephemeral resources |
| Budget compliance | Azure Cost Management shows ≤ ₹100 in any 30-day window |
| Code quality | CI is green; `pytest` coverage ≥80% on core, ≥60% on adapters |
| Architectural enforcement | `grep -r "import azure\|import praw\|import psycopg2" src/core/` returns zero matches |
| Data quality | All dbt tests pass; all Great Expectations suites pass |
| Documentation | README opens cleanly, screenshots load, ADRs explain key choices |
| Visualization | 5 Power BI pages, all readable as PNGs in README |
| Reproducibility | Fresh clone + 4 secrets + 1 click = working pipeline |

---

## 19. Architecture Decision Records

### ADR-0001: Use on-demand provisioning pattern
- **Decision:** Deploy ephemeral resources via Bicep at run-start; destroy at run-end
- **Why:** Hard ₹100/month budget makes always-on Postgres + Functions unaffordable
- **Trade-off:** ~5 minutes deploy + 3 minutes destroy added to every run; no live dashboard

### ADR-0002: Use Azure Functions + Container Apps over Databricks
- **Decision:** Skip Databricks entirely; use Functions for ingestion, Container Apps Job for transforms
- **Why:** Databricks has no meaningful free tier; data volume doesn't require Spark
- **Trade-off:** Lose "Databricks" keyword on resume; gain authentic right-sizing story

### ADR-0003: Use Postgres Flexible Server over Synapse
- **Decision:** Postgres B1ms with stop-when-idle pattern
- **Why:** Synapse minimum spend is hundreds of USD/month; Postgres can stop and cost ₹0
- **Trade-off:** Lose enterprise data warehouse keyword; gain real cost-engineering story

### ADR-0004: Use Pandas over PySpark
- **Decision:** Transform layer is Pandas in a Container Apps Job
- **Why:** <100MB data per run; Pandas is ~10x faster than Spark at this scale
- **Trade-off:** Lose Spark keyword; gain credibility (using the right tool for the size)

### ADR-0005: Power BI as static artifact, not live service
- **Decision:** Commit `.pbix` + PNG screenshots; do not publish to Power BI Service
- **Why:** Power BI Service licensing (~₹840/user/month) blows the budget
- **Trade-off:** No live dashboard URL; gain budget compliance + Linux-friendly workflow

### ADR-0006: Hexagonal architecture with plain-Python DI
- **Decision:** Ports and Adapters with `typing.Protocol`; no DI library
- **Why:** Decouples business logic from infrastructure, enables fast unit tests, makes local→cloud trivial; a DI library adds ceremony for ~5 services
- **Trade-off:** Slightly more boilerplate than ad-hoc construction; recruiters less familiar with hexagonal might want explanation in README

### ADR-0007: Local-first development
- **Decision:** Build everything against Docker Compose services; deploy to cloud only after local pipeline works end-to-end
- **Why:** Zero cost during development; faster iteration; surfaces bugs without burning Azure credits; aligns with how production teams actually work
- **Trade-off:** Requires upfront Docker setup; a few cloud-specific bugs (managed identity, network) surface later than they would otherwise

---

## 20. Open Questions

These are explicitly deferred decisions to revisit during implementation:

1. **Subreddit choice** — `r/technology` is the default; could swap based on which dashboard tells the most interesting story
2. **GitHub Actions runner egress IP range** — must be added to Postgres firewall; the range is large and changes; alternative is `0.0.0.0/0` for the run window only
3. **Power BI VM strategy** — Windows 365 free trial vs local VirtualBox vs borrowed laptop; pick during Phase 5
4. **Is Great Expectations worth it given dbt tests already exist?** — Decide after Phase 4; may downgrade to dbt-only if GE adds little value
5. **Container Apps Job vs Azure Function for transforms** — At v1 data scale, a second Function would also work; Container Apps Job picked for the resume signal but reconsider if Docker complexity becomes a blocker

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| ADLS | Azure Data Lake Storage (Gen2) — hierarchical namespace storage |
| Adapter | Concrete implementation of a port (e.g., `PRAWAdapter` implements `RedditClient`) |
| Bicep | Azure-native domain-specific language for ARM template authoring |
| Bronze/Silver/Gold | Medallion architecture layers — raw, cleaned, modeled |
| Composition root | The single function/file responsible for wiring up dependencies |
| dbt | Data Build Tool — SQL transformation framework |
| DI | Dependency Injection — passing dependencies to a service instead of constructing them inside |
| Great Expectations | Open-source data quality and validation framework |
| Hexagonal architecture | Pattern (a.k.a. Ports and Adapters) that isolates business logic from infrastructure |
| Port | Abstract interface (Python `Protocol`) describing what a service needs from infrastructure |
| PRAW | Python Reddit API Wrapper |
| Protocol | Python's structural typing primitive (`typing.Protocol`) |
| VADER | Valence Aware Dictionary and sEntiment Reasoner — rule-based sentiment library |

---

*Document maintained in repo. Last updated: 2026-05-06.*
