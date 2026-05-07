# Project Batches

> The project is split into 8 batches. Each batch ends with a working demo, green CI, and a git tag. Do not start a batch until the previous one's "Done" checklist is fully ticked.

---

## Batching philosophy

This project uses **vertical thin slicing**. Instead of building all of one layer before the next, each batch produces a working end-to-end (or as close to it as possible) pipeline. The pipeline starts trivially thin — one fake post, no transforms, no warehouse — and is thickened batch by batch until it matches the full design.

Why this approach:

- Something demoable exists from week 1
- Architecture flaws surface immediately, not at the end
- Motivation stays high (each Sunday you have something new to show)
- If you stop at any batch, the project still tells a coherent story
- It mirrors how production teams actually ship

Cloud deployment is deliberately late. Five of the eight batches happen entirely on your Linux machine. This keeps spend at zero during the high-iteration phase.

---

## Batch overview

| #   | Batch               | Goal                                       | Duration | Cloud?  |
| --- | ------------------- | ------------------------------------------ | -------- | ------- |
| 1   | Foundation          | Repo + tooling + CI scaffolding            | 2 days   | No      |
| 2   | Walking skeleton    | Fake post flows end-to-end through fakes   | 2 days   | No      |
| 3   | Real ingestion      | Real Reddit posts land in Azurite bronze   | 2 days   | No      |
| 4   | Real transform      | Sentiment-scored Parquet in Azurite silver | 2 days   | No      |
| 5   | Real warehouse      | dbt-built star schema in local Postgres    | 3 days   | No      |
| 6   | Cloud foundation    | Bicep authored; persistent infra deployed  | 2 days   | Partial |
| 7   | Full cloud pipeline | One-click cloud run with auto-destroy      | 3 days   | Yes     |
| 8   | Polish              | Power BI, README, ADRs, demo video         | 5 days   | Yes     |

**Total: ~21 days of evening/weekend work.**

---

## Batch 1: Foundation

**Tag:** `v0.1.0-foundation`

### Goal

Set up the repository, local development environment, CI pipeline, and architectural enforcement. Write zero business logic. End the batch with a repo that lints itself, runs an empty test suite, and rejects PRs that violate the architecture rules.

### Why first

Tooling debt compounds. Setting up linters, type checking, and the architecture-boundary check before any code exists means every line ever written is held to the standard. If you skip this and add it later, you'll spend a weekend fixing violations.

### Tasks

1. `git init`, push to GitHub, configure branch protection on `main`
2. Write `pyproject.toml` (Python 3.13, dependencies, dev dependencies, ruff/black/mypy/pytest config)
3. Write `docker-compose.yml` (Azurite + Postgres)
4. Write `Makefile` with targets: `up`, `down`, `lint`, `test`, `check-architecture`, `clean`
5. Write `.env.example` with documented placeholders
6. Write `.gitignore` (Python, IDE, `.env`, `local-data/`, `.venv`)
7. Write `.pre-commit-config.yaml` (black, ruff, mypy, sqlfluff, gitleaks)
8. Create empty package structure: `src/core/__init__.py`, `src/adapters/__init__.py`, etc.
9. Add `tests/unit/__init__.py` and `tests/integration/__init__.py` with one trivial passing test in each
10. Write `.github/workflows/ci.yml`: lint → typecheck → architecture-boundary check → test
11. Drop `design.md` and `AGENT.md` into the repo
12. Write a README skeleton (just the title, one-line pitch, and "under construction")
13. Open a placeholder PR and verify CI works end-to-end

### Demo

```
git clone <repo>
docker compose up -d
make lint
make test
make check-architecture
```

All four commands exit 0. The PR shows green CI badges.

### Done when

- [ ] Repo is on GitHub with branch protection
- [ ] `docker compose up -d` brings up Azurite and Postgres
- [ ] `make lint` passes
- [ ] `make test` passes (with one trivial test)
- [ ] `make check-architecture` passes (no violations because no code)
- [ ] Pre-commit hooks installed and working
- [ ] CI runs on every PR and is green
- [ ] `AGENT.md` and `design.md` committed
- [ ] `.env.example` covers all required variables (even if empty)

### Estimated time

2 days. Day 1: repo, Docker, Python tooling. Day 2: CI, pre-commit, architecture check.

### Watch out for

- Do not skip the architecture-boundary grep in CI. It is the most valuable line in this batch.
- Do not commit a `.env` file. Test it: `git check-ignore .env` should print `.env`.
- The trivial test in `tests/unit/` should call `assert True`. The trivial test in `tests/integration/` should be marked with `@pytest.mark.integration` and skipped if Docker is down.

---

## Batch 2: Walking skeleton

**Tag:** `v0.2.0-walking-skeleton`

### Goal

Get a fake post to flow through every architectural layer using only fakes — no Reddit, no real Azure SDK, no real Postgres. Prove that the hexagonal architecture wires up correctly and that the composition root works.

### Why second

This is the cheapest possible end-to-end test of your architecture. If `IngestionService` can't accept a `FakeRedditAdapter` and `InMemoryStorageAdapter`, your ports are wrong. Better to find out now with no SDK noise than later with cloud bills.

### Tasks

1. Define `RedditClient` and `StorageClient` Protocols in `src/core/ports.py`
2. Define `Post` dataclass in `src/core/models.py`
3. Write `tests/unit/test_ingestion.py` with the AAA-style test from `AGENT.md` Section 5.4
4. Write `tests/unit/fakes.py` with `FakeRedditAdapter` and `InMemoryStorageAdapter`
5. Implement `IngestionService` in `src/core/ingestion.py` to make the test pass
6. Write `src/composition.py` with `build_ingestion_service` (still using fakes for now, gated by an env var)
7. Write `src/cli.py` exposing `python -m src.cli ingest --subreddit technology`
8. Add `make ingest` target that calls the CLI
9. Run the full pipeline locally: `make ingest` produces a fake post in the in-memory storage and prints a confirmation

### Demo

```
make ingest
# Output: "Ingested 3 fake posts into bronze (in-memory)"
```

The composition root reads `APP_MODE=walking-skeleton` from `.env` and wires up fakes. End-to-end works.

### Done when

- [ ] `tests/unit/test_ingestion.py` passes in <100ms
- [ ] `IngestionService` has zero infrastructure imports
- [ ] `make ingest` runs end-to-end with fakes
- [ ] `make check-architecture` still passes
- [ ] Coverage on `src/core/ingestion.py` is ≥80%
- [ ] CI is green
- [ ] Test count ≥3

### Estimated time

2 days. Day 1: ports, models, failing test. Day 2: implementation, CLI, composition root.

### Watch out for

- Do not import `praw` anywhere yet
- Do not import `azure.storage` anywhere yet
- The `Post` dataclass should be `frozen=True, slots=True`
- Keep the test list flat — three tests for ingestion is plenty for now

---

## Batch 3: Real ingestion

**Tag:** `v0.3.0-real-ingestion`

### Goal

Replace the `FakeRedditAdapter` with a real `PRAWAdapter` and the `InMemoryStorageAdapter` with a real `AzureBlobAdapter` pointing at Azurite. Real Reddit posts land in local Azurite bronze storage as JSON.

### Why third

Now that the architecture is proven, swap in real adapters one at a time. If something breaks, the architecture isn't to blame — only the adapter is. This is the first batch that connects to the outside world.

### Tasks

1. Write `tests/integration/test_reddit_praw.py` (skipped if `REDDIT_CLIENT_ID` is unset)
2. Implement `PRAWAdapter` in `src/adapters/reddit_praw.py`
3. Write `tests/integration/test_storage_azure.py` (skipped if Azurite is down)
4. Implement `AzureBlobAdapter` in `src/adapters/storage_azure.py` (works for both Azurite and ADLS — same SDK)
5. Update `src/composition.py`: `build_ingestion_service` now reads `STORAGE_CONNECTION_STRING` and Reddit creds from env
6. Create a Reddit script app, populate `.env` locally
7. Run `make ingest --subreddit technology` and verify JSON appears in Azurite at `bronze/raw/dt=YYYY-MM-DD/run=<id>/posts.json`
8. Add a `scripts/inspect_bronze.py` helper that lists blobs in Azurite for debugging

### Demo

```
docker compose up -d
make ingest -- --subreddit technology
python scripts/inspect_bronze.py
# Output: bronze/raw/dt=2026-05-06/run=abc123/posts.json (147 KB)
```

You can open the file with `az storage blob download` (against Azurite) and see real Reddit JSON.

### Done when

- [ ] `PRAWAdapter` implements the `RedditClient` Protocol exactly
- [ ] `AzureBlobAdapter` implements the `StorageClient` Protocol exactly
- [ ] Integration tests pass against Docker services
- [ ] Unit tests still pass and run in <100ms (no Docker dependency)
- [ ] `make ingest` produces real Reddit data in Azurite
- [ ] CI is green (integration tests skipped when no credentials present)
- [ ] No `azure` or `praw` imports leaked into `src/core/`
- [ ] `make check-architecture` still passes

### Estimated time

2 days. Day 1: PRAWAdapter + integration test + Reddit credentials. Day 2: AzureBlobAdapter + integration test + end-to-end run.

### Watch out for

- Azurite uses a well-known dummy connection string — copy it from the Azurite docs, do not invent your own
- Reddit's PRAW expects a `user_agent` string with your username; failing to set this causes confusing errors
- If you see "Reddit API returned 429", you've hit the rate limit; back off and retry in a minute
- The first time you run against real Reddit, the JSON will be bigger than expected; that's fine
- Do not commit the `.env` file (run `git status` to confirm)

---

## Batch 4: Real transform

**Tag:** `v0.4.0-real-transform`

### Goal

Read bronze JSON from Azurite, score each post with VADER sentiment, and write a Parquet file to silver. Run inside a Docker container (the same image will later run as a Container Apps Job in Azure).

### Why fourth

Transform is the most interesting service from a "real DE work" perspective. Doing it in a Docker container locally means the cloud version is just a deployment change — no code change.

### Tasks

1. Define `SentimentScorer` Protocol in `src/core/ports.py`
2. Write `tests/unit/test_transform.py` with a `FakeSentimentScorer`
3. Implement `TransformService` in `src/core/transform.py` to make the test pass
4. Implement `VADERSentimentAdapter` in `src/adapters/sentiment_vader.py`
5. Write `tests/integration/test_sentiment_vader.py` (no Docker dependency, just the VADER lexicon)
6. Write `transforms/Dockerfile` (Python 3.11-slim base, copies `src/`, runs `transforms/entrypoint.py`)
7. Write `transforms/entrypoint.py` that calls `build_transform_service` and runs it
8. Add `make transform` target that runs the Docker image with `.env` mounted
9. Update `src/composition.py` with `build_transform_service`
10. Run `make ingest && make transform`; verify Parquet appears in Azurite silver

### Demo

```
make ingest -- --subreddit technology
make transform
python scripts/inspect_silver.py
# Output: silver/posts/dt=2026-05-06/posts.parquet (89 KB, 100 rows, 11 columns)
```

You can `pip install pyarrow` and read the Parquet to confirm sentiment scores are populated.

### Done when

- [ ] `TransformService` has zero infrastructure imports
- [ ] `VADERSentimentAdapter` is the only file that imports `vaderSentiment`
- [ ] Docker image builds in <2 minutes
- [ ] `make transform` runs the container against Azurite and produces silver Parquet
- [ ] Unit tests still <100ms total
- [ ] CI is green
- [ ] Coverage on `src/core/transform.py` is ≥80%

### Estimated time

2 days. Day 1: TransformService + VADER + tests. Day 2: Dockerfile + container run + silver verification.

### Watch out for

- VADER's lexicon download happens at first run; bake it into the Dockerfile to avoid a cold-start delay
- Pandas + PyArrow is the right combo for Parquet at this scale; do not bring in PySpark
- The Docker container needs network access to talk to Azurite on the host; use `host.docker.internal` or run on the same Docker network as `docker-compose`
- Schema on the silver Parquet should match the schema in `design.md` Section 12.2 exactly — test it

---

## Batch 5: Real warehouse

**Tag:** `v0.5.0-real-warehouse`

### Goal

Initialize a dbt project pointing at local Postgres, build the gold star schema (`fct_posts`, `dim_author`, `dim_subreddit`, `dim_date`), and add data-quality tests. Add a Great Expectations suite as a second-line check.

### Why fifth

This is the largest batch but it's the heart of the project for a DE portfolio. Recruiters look for dbt + dimensional modeling. Spend the time.

### Tasks

1. Define `WarehouseClient` Protocol in `src/core/ports.py` (used to load silver Parquet into Postgres staging)
2. Implement `PostgresAdapter` in `src/adapters/warehouse_postgres.py`
3. Write `src/core/loader.py` with a `LoaderService` that reads silver Parquet and bulk-inserts to a `raw_posts` Postgres table
4. Tests for the loader (unit + integration)
5. Add `make load` target
6. Initialize dbt: `dbt init` inside `dbt/`, configure `profiles.yml.template`
7. Write `dbt/models/staging/stg_reddit_posts.sql`
8. Write `dbt/models/intermediate/int_posts_enriched.sql`
9. Write `dbt/models/marts/fct_posts.sql`, `dim_author.sql`, `dim_subreddit.sql`, `dim_date.sql`
10. Write the `dim_date` seed CSV
11. Add YAML schema files with `not_null`, `unique`, `relationships`, `accepted_values` tests
12. Write the custom test `dbt/tests/assert_sentiment_in_range.sql`
13. Add `make model` target (`dbt run && dbt test`)
14. Add `make quality` target running Great Expectations against `fct_posts`
15. Add `make all` running the full local pipeline: `up → ingest → transform → load → model → quality`

### Demo

```
make all
psql postgresql://dbtuser:localdev@localhost:5433/reddit_warehouse
warehouse=> select count(*), avg(sentiment_score) from gold.fct_posts;
 count | avg
-------+------
   100 | 0.12
```

The full local pipeline runs in under a minute.

### Done when

- [ ] dbt project compiles and `dbt run` succeeds
- [ ] All dbt tests pass
- [ ] `dim_date` is populated for at least the next 5 years
- [ ] Great Expectations suite runs and passes
- [ ] `make all` runs the full pipeline end-to-end
- [ ] sqlfluff passes on all SQL files
- [ ] Star schema matches `design.md` Section 12.3 exactly
- [ ] CI is green

### Estimated time

3 days. Day 1: loader service. Day 2: dbt staging + intermediate + marts. Day 3: tests + Great Expectations + `make all`.

### Watch out for

- Use a `gold` schema in Postgres for marts, `staging` for raw and staged. dbt does this naturally if configured.
- The `dim_author` table needs careful handling because the same username appears across many runs; use `merge`/upsert semantics.
- Do not over-engineer the date dimension; a simple Python script that emits CSV is fine.
- Great Expectations has a steep learning curve; aim for 5 simple expectations, not 50.

---

## Batch 6: Cloud foundation

**Tag:** `v0.6.0-cloud-foundation`

### Goal

Author all Bicep modules. Deploy only the _persistent_ resources (Storage + Key Vault) to Azure. Verify the same code that worked against Azurite now works against ADLS by changing one env var.

### Why sixth

This is the moment hexagonal architecture pays off. You will _not_ edit Python code in this batch. You will only change connection strings and confirm everything still works.

### Tasks

1. Sign up for Azure (free tier or Azure for Students if available)
2. Install Azure CLI, log in (`az login`)
3. Create a service principal scoped to one resource group; save credentials
4. Write `infra/main.bicep` orchestrator with `deployEphemeral` parameter
5. Write `infra/modules/storage.bicep` (ADLS Gen2, three containers, lifecycle policy)
6. Write `infra/modules/keyvault.bicep` (Key Vault, secrets for Reddit credentials)
7. Write `infra/parameters/dev.bicepparam`
8. Run `az deployment group what-if` to preview
9. Run `az deployment group create` to deploy persistent resources
10. Get the ADLS connection string; populate it in `.env` (commented next to the Azurite one)
11. Manually swap the `STORAGE_CONNECTION_STRING` and run `make ingest && make transform`
12. Verify silver Parquet now appears in real ADLS instead of Azurite
13. Swap back to Azurite for daily dev

### Demo

```
az storage blob list --account-name stredditpipedev --container silver --auth-mode key
# Lists silver/posts/dt=2026-05-06/posts.parquet from real Azure
```

### Done when

- [ ] All five Bicep modules are written and `bicep build` clean
- [ ] Persistent resources deployed to Azure
- [ ] Cost dashboard shows ~₹3-5/month for idle storage
- [ ] Pipeline runs locally against ADLS by changing one env var (no Python code change)
- [ ] CI lints Bicep on every PR
- [ ] Service principal credentials stored as GitHub Secret `AZURE_CREDENTIALS`
- [ ] Reddit credentials uploaded to Key Vault

### Estimated time

2 days. Day 1: Bicep authoring + first deploy. Day 2: connection-string swap test + Key Vault.

### Watch out for

- Do not deploy Postgres or Functions yet — they're ephemeral and shouldn't be running idle
- Azure budget alert: set this up _before_ deploying anything; alert at ₹50
- Bicep parameter files should not contain secrets; use Key Vault references
- ADLS Gen2 hierarchical namespace must be enabled; default is off — make sure your storage module sets it

---

## Batch 7: Full cloud pipeline

**Tag:** `v0.7.0-cloud-pipeline`

### Goal

Add Functions and Container Apps Bicep modules. Wire up GitHub Actions workflow that does deploy → ingest → transform → load → model → quality → destroy in one click.

### Why seventh

This is the marquee demo. After this batch, you can show a recruiter "I run my entire pipeline in the cloud, end to end, with one click, and it tears itself down to save cost."

### Tasks

1. Write `infra/modules/functions.bicep` (Function App, Consumption plan, App Insights)
2. Write `infra/modules/containerapp.bicep` (Container Apps Environment, Job)
3. Write `infra/modules/postgres.bicep` (Flexible Server B1ms, firewall, database)
4. Update `main.bicep` to conditionally deploy ephemeral resources
5. Adapt `src/function_app.py` for Azure Functions Python runtime
6. Push the transform Docker image to GitHub Container Registry
7. Write `.github/workflows/deploy-and-run.yml`:
   - `bicep deploy --parameters deployEphemeral=true`
   - Trigger Function via HTTP
   - Trigger Container Apps Job via az CLI
   - Run dbt (using GitHub Actions runner with Postgres connection)
   - Run Great Expectations
   - Export gold to ADLS as Parquet
   - `bicep deploy --parameters deployEphemeral=false` in `if: always()` block
8. Write `.github/workflows/destroy.yml` (manual emergency teardown)
9. Test end-to-end via `gh workflow run deploy-and-run.yml`
10. Capture cost screenshot after one run
11. Add the Postgres firewall rule for GitHub Actions IP range (or 0.0.0.0/0 for run window)

### Demo

```
gh workflow run deploy-and-run.yml
gh run watch
# After ~12 minutes: green checkmark
gh run view --log
# Shows: "Bicep destroy: removed 3 resources"
```

Cost dashboard shows ~₹1 spent for the run.

### Done when

- [ ] `gh workflow run deploy-and-run.yml` completes green
- [ ] After completion, only persistent resources exist in Azure
- [ ] One full run costs less than ₹2
- [ ] `destroy.yml` works as emergency fallback
- [ ] Failure of any step still triggers destroy (`if: always()`)
- [ ] Total monthly cost over 4 runs ≤ ₹50
- [ ] CI is green

### Estimated time

3 days. Day 1: ephemeral Bicep modules + first manual deploy. Day 2: GitHub Actions workflow. Day 3: end-to-end test + destroy verification.

### Watch out for

- Functions on Consumption plan have a 5-minute timeout; if your ingest takes longer, batch it or move to Container Apps Job
- Postgres takes 3-5 minutes to provision; budget for it in workflow timing
- The `if: always()` block on destroy is critical; without it, a mid-run failure leaves resources running
- Test the destroy path by deliberately failing a step (e.g., bad SQL in dbt) and confirming destroy still runs
- Rotating the service principal secret periodically is good hygiene; document it in the runbook

---

## Batch 8: Polish

**Tag:** `v1.0.0`

### Goal

Make the project portfolio-ready. Power BI dashboard, README, ADRs, demo video, LinkedIn post.

### Why last

Polish before functionality is bikeshedding. Polish _after_ functionality is professional. Now is the time.

### Tasks

1. Borrow/spin up a Windows machine for Power BI Desktop
2. Connect Power BI to Azure Postgres during a run window
3. Build five dashboard pages (overview, sentiment trend, top topics, authors, anomalies)
4. Export each page as a 1920×1080 PNG
5. Save `.pbix`; commit to `viz/powerbi/dashboard.pbix`
6. Write all 7 ADRs in `docs/adr/`
7. Write `docs/cost-analysis.md` with real billing screenshots
8. Write `docs/runbook.md` (how to run, how to debug, how to recover)
9. Polish `README.md`:
   - Hero section with the elevator pitch
   - Architecture diagram (export from `design.md`)
   - "Try it yourself" section with the four-step quickstart
   - All five dashboard PNGs embedded
   - Cost evidence
   - Tech stack badges
   - Link to demo video
10. Record a 2-3 minute Loom demo: clone → docker compose up → make all → screenshots
11. Post on LinkedIn with the demo link
12. Tag `v1.0.0`, write a release note

### Demo

The repo. Send it to a friend; they should `git clone`, follow the README, and have a working pipeline in 15 minutes.

### Done when

- [ ] `.pbix` committed
- [ ] 5 high-quality PNGs in README
- [ ] All 7 ADRs written
- [ ] `cost-analysis.md` shows actual Azure bills under ₹100
- [ ] `runbook.md` covers happy path + 3 failure modes
- [ ] Demo video under 3 minutes, link in README
- [ ] LinkedIn post live with engagement (comments, shares)
- [ ] At least one friend has run it from a fresh clone successfully
- [ ] `v1.0.0` tag pushed
- [ ] Repo pinned on your GitHub profile

### Estimated time

5 days. Day 1: Power BI. Day 2: ADRs + cost-analysis. Day 3: runbook + README polish. Day 4: demo video + recording. Day 5: friend test + LinkedIn post.

### Watch out for

- Power BI screenshots should _show data_ — empty dashboards look amateurish
- The README is what recruiters read; spend more time on it than feels reasonable
- The Loom demo should focus on the architecture story, not just clicking through screens
- If your friend test reveals friction, fix it before pushing v1.0.0
- After v1.0.0, resist the urge to immediately add v2 features; let the project breathe and gather feedback

---

## Skip-ahead policy

Batches are sequential. Do not skip ahead. If you find yourself in batch 4 wanting to start on Bicep, that's a signal to slow down and finish batch 4 first. The reason: each batch's "Done" checklist is what keeps technical debt out. Skipping ahead leaves debt that compounds.

The one exception: if a batch is taking more than 1.5x its estimated time, stop and reassess. Either the scope is wrong (split the batch) or you're stuck (ask for help). Do not power through silently.

---

## Optional v1.1 batches (post-portfolio)

If you want to keep building after v1.0.0, here are interesting next steps:

| Batch | Goal                                                                  |
| ----- | --------------------------------------------------------------------- |
| 9     | Add comment-level sentiment (not just post-level)                     |
| 10    | Multiple subreddits with cross-subreddit comparison dashboards        |
| 11    | Replace VADER with a transformer-based sentiment model (Hugging Face) |
| 12    | Add streaming via Event Hubs (kills the budget — be warned)           |
| 13    | Add Microsoft Fabric integration as an alternative warehouse          |
| 14    | Add OpenLineage for data lineage tracking                             |

These are explicitly out of scope for v1. Do them only if you've finished v1 and still have appetite.

---

_Document maintained in repo. Last updated: 2026-05-06._
