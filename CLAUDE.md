# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PromptTree v1.0 is a Python library for prompt engineering using a **Git-Native Registry** architecture. It stores versioned prompts as a DAG in `.prompttree/registry/`, supports Jinja2 templating, AES-256-GCM encryption, a Click CLI, and a Streamlit visual UI.

**Release scope:** v1.0 ships core Registry functionality only. Lab and Artifacts features are implemented but deferred to v1.1 — they are not publicly exported.

## Commands

```bash
# Activate venv (required before any command)
source .venv/bin/activate

# Install in editable mode with all dependencies
pip install -e ".[dev,ui]"

# Run tests (test_artifacts.py and test_lab.py are excluded via pyproject.toml)
pytest

# Run a single test file
pytest tests/test_registry.py

# Run a single test
pytest tests/test_registry.py::test_persistence

# Lint
ruff check prompttree/

# Type check
mypy prompttree/

# Build package
python -m build

# Check built package before publishing
twine check dist/*

# CLI commands
prompttree init                        # initialise .prompttree workspace
prompttree lock --key $PT_KEY          # encrypt registry (run in CI)
prompttree unlock --key $PT_KEY        # decrypt registry
prompttree list                        # list all nodes + labels
prompttree delete-family <NAME>        # delete all nodes + labels for a prompt family
prompttree delete-family <NAME> --yes  # skip confirmation
prompttree reset                       # wipe entire registry
prompttree reset --yes                 # skip confirmation
prompttree ui                          # launch Streamlit UI (port 8501)
prompttree ui --port 8080              # launch on custom port
```

## Architecture: The Dual-State Model

The core design separates data by lifecycle stage:

### Registry (Git-Tracked) — v1.0
- Lives in `.prompttree/registry/`
- `nodes/` — one UUID-named `.yaml` file per prompt node
- `labels.json` — name-scoped alias map (`{"family-name": {"prod": "node_hex_id"}}`)
- Nodes form a DAG via the `parent_id` field in each YAML
- On startup `Registry` scans `nodes/` and builds an in-memory `dict[id, RegistryNode]`

### Lab (Local-Only, `.gitignore`d) — deferred to v1.1
- Lives in `.prompttree/.lab/`
- `experiments.jsonl` — append-only log; one JSON line per `lab.run()` call
- `LabSession` is returned by `engine.lab_session()` and is reusable across multiple `run()` calls

### Artifacts (Local-Only, `.gitignore`d) — deferred to v1.1
- Lives in `.prompttree/.artifacts/{owner_id}/`
- Stores binary files (image crops) plus `meta.json` per owner
- `owner_id` is a Lab experiment ID (`lab_xxxxxxxx`) or a Registry node ID

## Key Data Flows

**Production path:** `engine.get_prompt(name, label=..., by=..., vars=...)` resolves the node via one of three modes (see below) → decrypts if `key` was provided → Jinja2-renders with vars → returns string.

**Prompt resolution modes:**
- `get_prompt("My Prompt", label="prod")` — resolves the `prod` label scoped to that family
- `get_prompt("My Prompt")` — returns the most recently created node in the family (`created_at` descending)
- `get_prompt(node_id, by="id")` — resolves the exact node by ID

**Experiment path (v1.1):** `engine.lab_session()` → `lab.run(prompt_text, model, images, vars)` → Jinja2-renders → LiteLLM call → appends `LabExperiment` to `experiments.jsonl` → returns experiment object.

**Promotion path (v1.1):** `engine.promote(lab_id, name, parent_id, label)` → reads experiment from JSONL → creates `RegistryNode` → `registry.save()` → `artifacts.relink(lab_id, node.id)` → optionally sets label (requires `name` when `label` is set).

**Lock/Unlock (CI):** `prompttree lock --key $PT_KEY` walks all nodes, AES-256-GCM encrypts `content` in-place, sets `metadata.encrypted = true`. Decryption happens in-memory inside `get_prompt` when `PromptTree(key=...)` is set.

## Module Layout

```
prompttree/
├── core/
│   ├── engine.py      # PromptTree — top-level public API
│   ├── registry.py    # Registry — DAG loader, YAML CRUD, lock/unlock
│   ├── lab.py         # LabSession — context manager, run(), save_artifact() [v1.1]
│   ├── artifacts.py   # ArtifactStore — binary file save/list/relink [v1.1]
│   └── crypto.py      # AES-256-GCM encrypt/decrypt helpers
├── models/
│   ├── node.py        # RegistryNode + NodeMetadata (Pydantic v2)
│   └── experiment.py  # LabExperiment (Pydantic v2) [v1.1, not publicly exported]
├── llm/
│   └── client.py      # LiteLLM wrapper — text + vision (base64 data URI)
├── ui/
│   ├── app.py         # Streamlit UI — DAG explorer, node detail, create/branch form
│   └── assets/        # Logo and static assets
└── cli.py             # Click CLI: init, lock, unlock, list, delete-family, reset, ui
```

## Public API Surface (v1.0)

`prompttree/__init__.py` exports:
```python
__all__ = ["PromptTree", "RegistryNode", "NodeMetadata"]
```

`LabExperiment`, `LabSession`, `ArtifactStore` are **not exported** — they exist in code but are hidden until v1.1.

### `PromptTree` public methods (v1.0)

```python
# Save & retrieve
save(content, name, display_name, model, temperature, parent_id, tags, label) → RegistryNode
get_prompt(name_or_id, label=None, by=None, vars=None) → str
get_node(node_id) → RegistryNode | None
list_nodes() → list[RegistryNode]
list_names() → list[str]
get_nodes_by_name(name) → list[RegistryNode]

# Labels  (schema: {name: {label: node_id}})
get_labels() → dict[str, dict[str, str]]
set_label(name, label, node_id)

# Bulk operations
delete_family(name) → int   # deletes all nodes where node.name == name + labels entry
reset() → int               # wipes all nodes and resets labels.json to {}

# Encryption
lock(key) → int
unlock(key) → int
```

## Node YAML Schema

```yaml
id: "a1b2c3d4..."          # uuid4 hex, no dashes
parent_id: null            # hex id of parent node, or null for root
name: "P&ID Analyzer"      # prompt family name
display_name: "v1"         # short version label shown in UI
metadata:
  encrypted: false         # true after `prompttree lock`
  model: "gpt-4o"
  temperature: 0.7
  created_at: "2024-01-01T00:00:00+00:00"
  tags: []
content: "Analyze this P&ID for {{drawing}}..."
```

## UI (Streamlit)

- Entry point: `prompttree/ui/app.py`
- Launched via `prompttree ui` CLI command or `streamlit run prompttree/ui/app.py`
- Logo loaded from `prompttree/ui/assets/PromptTree_Transparent.png` as base64 inline
- Graph nodes rendered with `streamlit-agraph` using a manual Reingold-Tilford layout
- Node colors: plain `#f1f5f9`, labeled `#dcfce7`, selected `#fef9c3`
- Font: Inter (loaded from Google Fonts)
- Full-screen prompt editor via `@st.dialog`
- Model dropdown supports predefined models + free-text "Custom…" option
- `PROMPTTREE_STORAGE` env var overrides the default `.prompttree` storage path

## Tests

- `test_crypto.py`, `test_engine.py`, `test_registry.py` — active (30 tests)
- `test_lab.py`, `test_artifacts.py` — excluded via `addopts` in `pyproject.toml` (v1.1)
- All tests use `tmp_path` fixture — no real `.prompttree/` is touched

## LiteLLM Integration

`llm/client.py` supports text-only and vision (multipart) calls. When `images` are passed to `lab.run()`, each image file is base64-encoded into a `data:<mime>;base64,...` URI and appended as an `image_url` part. Supports Azure OpenAI and local Ollama/vLLM — configure via standard LiteLLM env vars.

## v1.1 Scope (Deferred)
- Expose Lab + Artifacts public API (`LabExperiment`, `LabSession`, `ArtifactStore`)
- Re-enable `test_lab.py` and `test_artifacts.py`
- UI: Lab experiment runner, artifact gallery, streaming console
