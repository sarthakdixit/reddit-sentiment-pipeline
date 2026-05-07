# Reddit Sentiment Analytics Pipeline

> An on-demand Reddit sentiment analytics pipeline on Azure, deployed via Bicep, built with hexagonal architecture, running for under ₹100/month.

**Status:** Under construction. See [`batches.md`](./batches.md) for the build plan.

## Documents

- [`design.md`](./design.md) — full requirements and architecture
- [`AGENT.md`](./AGENT.md) — coding standards (loaded into AI assistants)
- [`batches.md`](./batches.md) — phased delivery plan

## Quickstart (work in progress)

```bash
git clone <repo>
cd reddit-sentiment-pipeline
cp .env.example .env
make install
make up
make test
```

A polished README with architecture diagram, dashboard screenshots, cost evidence, and demo video link will land in batch 8 (`v1.0.0`).
