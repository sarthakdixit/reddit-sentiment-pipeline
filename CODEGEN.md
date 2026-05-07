# CODEGEN.md

> Rules for **how** AI coding assistants (Claude, Cursor, Copilot, etc.) deliver code in this repository.
> `AGENT.md` defines *what* the code must look like. This file defines *how* it gets produced and presented.
> Both files are loaded into every prompt. Treat these rules as non-negotiable.

---

## 1. Why this file exists

Generating an entire batch of files in one shot — or worse, a tarball — looks productive but produces three real problems:

1. **No review gate.** A single broken file blocks the whole batch and you only find out at the end.
2. **No mental absorption.** You can't actually understand 20 files dropped at once.
3. **No verification.** Linters, tests, and architecture checks don't run, so quality drift is invisible.

This file enforces the opposite: small chunks, each visible, each verified, each reviewable before the next chunk starts.

---

## 2. The four core rules

These rules apply to **every batch** described in `batches.md`.

### Rule 1 — Files generated one at a time

Each file is produced and presented individually. No tarballs. No zip files. No "here are 20 files" dumps. The file's contents must be visible in chat, in a code block, before the next file begins.

### Rule 2 — Chunks of four

Files are generated in groups of **four**. After the fourth file in a chunk, generation stops. The assistant must wait for the human to type `continue` (or equivalent) before producing files 5–8. Then files 9–12. And so on.

If a batch's total file count is not a multiple of four, the final chunk may have 1–4 files. State this explicitly: *"Final chunk — 2 files."*

### Rule 3 — Verify after every chunk

After the fourth file in a chunk is shown, the assistant runs a verification step appropriate to what was just produced:

- **Python files** → `ruff check`, `black --check`, `mypy`, and (if tests exist) `pytest`
- **Shell scripts** → `bash -n` (syntax check) and run them if they're idempotent
- **Bicep files** → `bicep build`
- **YAML/TOML/Markdown** → parse to confirm validity
- **Architecture-touching files** → run `scripts/check_architecture.sh` and `scripts/check_no_comments.sh`

Verification output (pass or fail) is shown before the assistant says "ready for next chunk." If verification fails, the assistant **does not** continue — it fixes the problem and re-verifies.

### Rule 4 — Each file gets a header

Before the file's contents, the assistant writes a short header with three things:

```
File N/M: <relative/path/to/file>
Purpose: <one sentence>
Why now: <why this file is in this position in the chunk>
```

No long preamble. No multi-paragraph explanation. The code itself is the deliverable; the header is just orientation.

---

## 3. File ordering within a batch

Files are produced in **dependency order, leaf files first**. By the time a file appears that imports from another, the imported file has already been shown.

For Batch 1 the order was already established (and is the canonical reference for future batches):

1. Project metadata (`pyproject.toml`, `.gitignore`, `.env.example`)
2. Local services (`docker-compose.yml`)
3. Task runner (`Makefile`)
4. Quality-gate scripts (`scripts/check_architecture.sh`, `scripts/check_no_comments.sh`)
5. Empty package skeletons (`src/core/__init__.py`, etc.)
6. Tests (`tests/unit/test_scaffold.py`, `tests/integration/test_scaffold.py`)
7. Pre-commit config (`.pre-commit-config.yaml`)
8. CI workflow (`.github/workflows/ci.yml`)
9. README and LICENSE
10. Project docs (copied: `design.md`, `AGENT.md`, `batches.md`)

For subsequent batches, the same principle applies:

- Ports before services (services import from ports)
- Models before services (services use models)
- Fakes before tests that use fakes
- Tests before implementations (TDD; see `AGENT.md` Section 2.3)
- Implementations before composition root (composition imports concrete adapters)
- Composition root before CLI/entrypoints (entry points call composition)

When in doubt, ask: "what does this file import from?" Anything it imports from must already exist.

---

## 4. The chunk-of-four protocol — explicit script

Here is the exact sequence the assistant follows. Deviations are not allowed without explicit human approval.

### 4.1 Start of batch

The assistant announces:

```
Starting Batch <N>: <name>.
Estimated total files: <count>.
Estimated chunks: <count / 4 rounded up>.

I will produce files 1–4, verify them, then wait for "continue".
```

### 4.2 During a chunk

For each file 1 through 4:

1. Show the header (file N/M, purpose, why now)
2. Produce the file
3. Display its full contents in a code block
4. Confirm it was written to the workspace

After file 4: run the verification step from Rule 3.

### 4.3 End of chunk

The assistant ends with one of two messages:

**If verification passed:**

```
Chunk complete (files 1–4 of <total>).
Verification: PASSED.
- ruff: clean
- black: clean
- pytest: <result>
- check-architecture: clean

Reply "continue" for files 5–8, or "stop" to pause the batch.
```

**If verification failed:**

```
Chunk complete (files 1–4 of <total>).
Verification: FAILED on <which check>.

<exact error output>

I will fix this before proceeding. Do not reply yet.
```

The assistant then fixes, re-verifies, and only after green does it ask for `continue`.

### 4.4 End of batch

After the last chunk verifies green:

```
Batch <N> complete.
Total files: <count>.
All "Done when" criteria from batches.md met:
- [x] <criterion>
- [x] <criterion>
...

Suggested commit message:
feat: batch <N> - <name>

<body>

Suggested tag: v0.<N>.0-<short-name>
```

---

## 5. What counts as "one file"

A file is the contents of a single path. Examples:

- `pyproject.toml` is one file
- `src/core/ports.py` is one file
- `tests/unit/test_ingestion.py` is one file
- A directory and its contents is **not** one file — count each file inside

Empty `__init__.py` files **do** count toward the chunk-of-four limit. They are real files, even if their content is empty.

`.gitkeep` placeholder files do not count if they exist only to commit empty directories — those are scaffolding overhead, not content.

---

## 6. Exceptions and edge cases

### 6.1 Trivial fixes

If the human asks for a one-line change to a single existing file, the four-file chunking does not apply. The change is made directly with verification, no chunking ceremony.

### 6.2 Documentation-only changes

When changing only Markdown documentation (`README.md`, `design.md`, ADRs) and no code: chunking still applies, but verification is reduced to "the file parses as valid Markdown." No tests, no linters, no architecture check.

### 6.3 Generated files

Files produced by code generators (`bicep build` outputs, dbt-compiled SQL, Python wheels) are not subject to this protocol. Only hand-authored source files are.

### 6.4 Configuration files that depend on each other

`pyproject.toml` and `.pre-commit-config.yaml` both reference Python tools. If a tool version changes in one, the other may need to update too. In this case, both files appear in the same chunk and verification runs after both are written.

### 6.5 The "continue" keyword

The human can use any of these to advance to the next chunk:

- `continue`
- `next`
- `go`
- `proceed`
- `next chunk`

Anything else is treated as a question or an instruction, not as advancement.

---

## 7. Verification commands by file type

The exact commands the assistant runs after each chunk, listed for reference.

| File type | Command(s) |
|---|---|
| Python source (`src/`) | `ruff check src tests scripts && black --check src tests scripts && mypy src && bash scripts/check_architecture.sh && bash scripts/check_no_comments.sh` |
| Python tests (`tests/`) | All of the above plus `pytest tests/unit -v` |
| Shell scripts (`scripts/`) | `bash -n scripts/<file>.sh && shellcheck scripts/<file>.sh` (if shellcheck is installed) |
| Bicep modules (`infra/`) | `bicep build infra/main.bicep` |
| dbt models (`dbt/`) | `cd dbt && dbt parse && sqlfluff lint .` |
| YAML/TOML | parse with `python -c "import yaml; yaml.safe_load(open('<file>'))"` or equivalent |
| Markdown | `python -c "import markdown; markdown.markdown(open('<file>').read())"` (smoke test) |
| `Makefile` | `make -n <target>` (dry run) for a representative target |
| `docker-compose.yml` | `docker compose config --quiet` |
| `.pre-commit-config.yaml` | `pre-commit validate-config` |
| GitHub Actions | `actionlint .github/workflows/<file>.yml` (if installed) else YAML parse |

If the verification tool is not available locally, the assistant says so explicitly and falls back to a syntax-only check. It does not silently skip verification.

---

## 8. What the human commits to

For this protocol to work, the human must:

- **Wait for the chunk to finish before commenting.** Mid-chunk interruptions break the flow and force re-verification.
- **Type `continue` (or equivalent) when ready.** Silence is not the same as approval.
- **Flag problems early.** If file 2 of a chunk looks wrong, say so before file 4 is produced.
- **Trust the verification.** If the assistant says "ruff: clean" don't ask "are you sure?" — re-running on the human's machine is the next step, not a debate.

---

## 9. What this protocol prevents

- **Tarball dumps** that are impossible to review meaningfully
- **Silent quality drift** because nothing is verified between files
- **Late-batch surprises** where file 19 reveals a problem in file 3
- **Ambiguous "is it done?" moments** because every chunk has explicit start/end
- **AI overconfidence** that produces 30 plausible-looking files, half of which don't compile

---

## 10. Things the assistant must never do

- Produce more than four files in a single response without a `continue`
- Skip verification because "it should work"
- Produce a tarball, zip, or any archive format
- Produce file contents inside an attachment instead of in chat
- Produce file contents only as a description ("create a file called X with contents Y") rather than the actual file
- Continue past a failed verification step
- Use `present_files` for normal batch generation — only at end of batch if requested

---

## 11. Things the assistant should do

- Pause and ask if the human's intent is unclear
- Suggest reordering within a chunk if dependency order is wrong
- Flag when a file is unusually large (>200 lines) and propose splitting
- Note when a chunk completes ahead of expectations (smaller batch than estimated)
- Reference `AGENT.md` and `design.md` rule numbers when relevant ("per AGENT.md Section 2.1, ...")

---

## 12. Workflow summary diagram

```
┌─────────────────────────────────────────────┐
│  Start of batch                             │
│  → announce file count and chunk count      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Chunk start                                │
│  → file 1 (header + content)                │
│  → file 2 (header + content)                │
│  → file 3 (header + content)                │
│  → file 4 (header + content)                │
│  → verification commands                    │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   verification          verification
   PASSED                FAILED
        │                     │
        ▼                     ▼
   wait for             fix → re-verify
   "continue"               │
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
       (next chunk, repeat)
                  │
                  ▼
       last chunk verifies
                  │
                  ▼
       end-of-batch summary
       suggested commit + tag
```

---

*Last updated: 2026-05-07. Edit this file when the delivery protocol needs to change.*
