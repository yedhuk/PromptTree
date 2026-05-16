# PromptTree

**Git-native prompt engineering library.** Version and manage your LLM prompts like code — with a branching registry, Jinja2 templating, AES-256 encryption, and a visual UI.

---

## Install

```bash
pip install prompttree          # core library + CLI
pip install "prompttree[ui]"    # with Streamlit UI
```

Requires Python 3.10+.

---

## Quick Start

```bash
prompttree init    # creates .prompttree/ workspace in current directory
```

```python
import prompttree as pt

engine = pt.PromptTree()

# Save a prompt and label it
node = engine.save(
    content="Analyze {{component}} in drawing {{drawing}}.",
    name="P&ID Analyzer",
    display_name="v1",
    model="gpt-4o",
    temperature=0.7,
    label="prod",
)

# Render it with variables
prompt = engine.get_prompt("prod", vars={"component": "valve", "drawing": "GAD_05"})
print(prompt)
# → "Analyze valve in drawing GAD_05."
```

---

## Core Concepts

### Registry

The Registry is the versioned store for your prompts. Each prompt is saved as a **node** — a YAML file containing the content, model settings, and a pointer to its parent node.

Nodes form a **DAG (directed acyclic graph)**: you branch from any existing node to create a new version, preserving the full lineage.

```
P&ID Analyzer
├── v1  ←  label: prod
├── v2  (branched from v1)
└── v3  (branched from v1)
```

All nodes live in `.prompttree/registry/nodes/` and are **git-tracked** — diffs, history, and blame work out of the box.

### Labels

Labels are human-readable aliases that point to a specific node. Use them to decouple your application code from node IDs.

```python
engine.set_label("prod", node.id)
engine.set_label("dev", other_node.id)

engine.get_prompt("prod", vars={...})   # always resolves to the labelled node
```

Labels are stored in `.prompttree/registry/labels.json`.

### Jinja2 Templating

Prompt content supports Jinja2 `{{ variable }}` syntax. Variables are injected at render time via `get_prompt()`.

```python
node = engine.save("Summarise {{text}} in {{language}}.", name="Summariser")
prompt = engine.get_prompt(node.id, vars={"text": "the report", "language": "French"})
```

---

## API Reference

### `PromptTree(storage, key)`

| Parameter | Default | Description |
|---|---|---|
| `storage` | `".prompttree"` | Path to workspace directory |
| `key` | `None` | AES-256 decryption key (only needed for encrypted registries) |

### Methods

```python
engine.save(content, name, display_name, model, temperature, parent_id, tags, label) → RegistryNode
engine.get_prompt(label_or_id, vars) → str
engine.get_node(node_id) → RegistryNode | None
engine.list_nodes() → list[RegistryNode]
engine.list_names() → list[str]
engine.get_labels() → dict[str, str]
engine.set_label(label, node_id)
engine.lock(key) → int
engine.unlock(key) → int
```

---

## Branching Versions

Branch from any node by passing `parent_id`:

```python
v1 = engine.save("Analyze {{component}}.", name="Analyzer", label="prod")

v2 = engine.save(
    "Analyze {{component}} and flag anomalies.",
    name="Analyzer",
    display_name="v2",
    parent_id=v1.id,
)

# Promote v2 to prod when ready
engine.set_label("prod", v2.id)
```

---

## Encryption

Encrypt all registry nodes before deploying to CI/production:

```bash
prompttree lock --key $PT_KEY      # encrypts all nodes in-place
prompttree unlock --key $PT_KEY    # decrypts back to plaintext
```

Decryption happens **in-memory** at render time — the encrypted YAML is never modified:

```python
engine = pt.PromptTree(key="my-secret-key")
prompt = engine.get_prompt("prod", vars={...})   # decrypts on the fly
```

Uses **AES-256-GCM** with a random nonce per encryption. The key is SHA-256 hashed so any string length is accepted.

---

## CLI

```bash
prompttree init                        # initialise workspace + update .gitignore
prompttree list                        # list all nodes and labels
prompttree lock --key $PT_KEY          # encrypt registry
prompttree unlock --key $PT_KEY        # decrypt registry
prompttree ui                          # launch the visual UI
prompttree ui --port 8080              # on a custom port
```

---

## Visual UI

Launch a browser-based DAG explorer to create, browse, and branch prompts:

```bash
prompttree ui
```

Opens at `http://localhost:8501`.

- Browse all prompt families from the dropdown
- Click any node in the DAG to inspect its content and metadata
- Branch directly from any node
- Assign labels to nodes

---

## Workspace Layout

```
.prompttree/
├── registry/
│   ├── nodes/          # one YAML file per prompt node (git-tracked)
│   └── labels.json     # label → node ID map (git-tracked)
```

`.prompttree/.lab/` and `.prompttree/.artifacts/` are local-only and automatically added to `.gitignore` by `prompttree init`.

---

## Node YAML Format

```yaml
id: "a1b2c3d4..."
parent_id: null
name: "P&ID Analyzer"
display_name: "v1"
metadata:
  encrypted: false
  model: "gpt-4o"
  temperature: 0.7
  created_at: "2024-01-01T00:00:00+00:00"
  tags: []
content: "Analyze {{component}} in drawing {{drawing}}."
```

---

## Development

```bash
git clone https://github.com/yedhuk/prompttree
cd prompttree
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ui]"

pytest          # run tests
ruff check prompttree/
mypy prompttree/
```

---

## License

MIT © [Yedhu Krishna](https://github.com/yedhuk)
