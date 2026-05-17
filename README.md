<p align="center">
  <img src="https://raw.githubusercontent.com/yedhuk/prompttree/main/prompttree/ui/assets/PromptTree_Transparent.png" alt="PromptTree" height="200">
</p>

# PromptTree

**Git-native prompt engineering library.** Version and manage your LLM prompts like code — with a branching registry, Jinja2 templating, AES-256 encryption, and a visual UI.

---

## Why PromptTree

Prompts are code. They have bugs, regressions, and versions — but most teams manage them as loose strings scattered across notebooks, env files, or database rows. PromptTree brings prompts into your git workflow and makes them first-class artifacts you can review, audit, roll back, and deploy with confidence.

---

### The UI is the primary authoring surface

When iterating on prompts, use `prompttree ui` rather than calling `engine.save()` directly. The visual DAG shows you the full lineage of a prompt family — which versions branched from which, which node carries the `prod` label, and what the content of every ancestor looks like — before you write a single character of a new version.

```bash
prompttree ui   # opens http://localhost:8501
```

- **See the tree before you branch.** Branching from the wrong parent is the most common prompt-versioning mistake. The DAG makes parent selection unambiguous.
- **Edit in context.** The node detail panel shows parent content alongside the editor, so you can see exactly what you are changing relative to the previous version.
- **Assign labels without code.** Promote a node to `prod` or `staging` from the UI — the `labels.json` change is written to disk and ready to commit.
- **Rapid iteration.** Writers, product managers, and domain experts who don't write Python can own the prompt content while engineers own the application code that consumes it.

The `engine.save()` API is still useful for scripted or programmatic ingestion (bulk imports, automated prompt generation), but day-to-day iteration belongs in the UI.

---

### Team Development Workflow

When multiple engineers or AI practitioners work on the same project, PromptTree lets everyone iterate independently and merge cleanly — the same way you'd manage source code.

**How it works:**

Each prompt version is a `.yaml` file in `.prompttree/registry/nodes/`. Because every node is a plain file with a stable UUID name, concurrent changes from different team members produce independent files with no merge conflicts. `labels.json` is the only shared file — and label changes are intentional, reviewable commits.

**Typical day-to-day flow:**

```
1. Pull the latest main branch — you have the full prompt history locally.
2. Run `prompttree ui` to explore the current DAG.
3. Branch from any node in the UI, write your new version, save.
4. A new YAML file appears in .prompttree/registry/nodes/.
5. Commit it on a feature branch and open a PR.
6. Reviewers see a clean diff: exactly one new node file, nothing else.
7. After merge, promote the node to the target label in the UI and commit labels.json.
```

```bash
# After iterating in the UI
git add .prompttree/registry/
git commit -m "prompt: Summariser v3 — tighten length constraint"
git push origin alice/summariser-v3
```

Because node files are immutable once written and named by UUID, two team members working in parallel never touch the same file. The only coordination point is `labels.json` — which node is currently `prod` — and that decision is an explicit, auditable commit, not a silent database update.

Rollback is `git revert`. History is `git log`. Blame is `git blame`. No external service required.

---

### DevOps / Production Workflow

In production you want prompts to be stable, auditable, and secure. PromptTree integrates directly into CI/CD pipelines using labels for safe promotion and AES-256-GCM encryption to keep prompt content out of plaintext config.

**Resolve by label — decouple prompt versions from application deploys:**

Your application code never hardcodes a node ID. It resolves by label, so you can update the active prompt without redeploying the application.

```python
import prompttree as pt
import os

# Key injected from your secret manager (Vault, AWS SSM, GitHub Secrets, etc.)
engine = pt.PromptTree(key=os.environ["PT_KEY"])

# Always returns the node currently labelled "prod" for this family
prompt = engine.get_prompt("Summariser", label="prod", vars={"text": document_text})
```

**Encrypt before deploy (CI step):**

Commit plaintext prompts in your repo for readability and review. Lock them in CI so only ciphertext reaches production.

```yaml
# .github/workflows/deploy.yml (excerpt)
- name: Lock prompt registry
  run: prompttree lock --key ${{ secrets.PT_KEY }}

- name: Deploy application
  run: ./deploy.sh
```

```bash
# Locally — decrypt to plaintext for development
prompttree unlock --key $PT_KEY
```

The `content` field in each node YAML is encrypted in-place; `metadata`, `name`, and `parent_id` remain readable so git history and the DAG structure are preserved.

**Safe rollback in production:**

Because every node is immutable and labels are the only mutable pointer, rolling back is a one-line label change — made in the UI or in code:

```python
engine.set_label("Summariser", "prod", previous_node_id)
```

Commit the `labels.json` change and push — no data loss, no service restart required if your application resolves the label at request time.

**Staging / canary environments:**

Use multiple labels to manage environments independently:

```json
{
  "Summariser": {
    "prod":    "a1b2c3...",
    "staging": "d4e5f6...",
    "canary":  "g7h8i9..."
  }
}
```

```python
label = os.environ.get("PROMPT_ENV", "prod")   # injected per deployment
prompt = engine.get_prompt("Summariser", label=label, vars={...})
```

---

### Self-hosted alternative to SaaS prompt management platforms

Platforms like LangFuse and LangSmith offer prompt management, but they require sending prompt content and model metadata to an external cloud service. In regulated industries — finance, healthcare, government, defence — that is often a non-starter: data governance policies, air-gapped networks, or legal restrictions on data residency make SaaS tools unavailable regardless of their technical merit.

PromptTree is a viable self-hosted alternative for these environments:

| Capability | SaaS platforms | PromptTree |
|---|---|---|
| Prompt versioning | Cloud database | Git — your existing infrastructure |
| Lineage / history | Web UI, vendor-hosted | Visual DAG + `git log`, self-hosted |
| Environment promotion | Dashboard (cloud) | Labels in `labels.json`, committed to your repo |
| Access control | Vendor IAM | Your Git host (GitHub Enterprise, GitLab, Bitbucket) |
| Encryption at rest | Vendor-managed | AES-256-GCM, your key, your secrets manager |
| Auditability | Vendor logs | Native git history — immutable, signable with GPG |
| Network requirement | Outbound HTTPS to vendor | None — runs entirely offline |
| Cost | Per-seat or usage-based SaaS fee | Zero — MIT licensed, no telemetry |

**What PromptTree does not currently cover:** runtime tracing, LLM call logging, and evaluation dashboards are outside its v1.0 scope. For those capabilities in a restricted environment, a self-hosted LangFuse instance or an internal observability stack (OpenTelemetry + your existing APM) can sit alongside PromptTree — they operate on different layers (prompt storage vs. runtime observability) and do not overlap.

**Practical enterprise setup:**

```
Git host (GitHub Enterprise / GitLab self-managed)
  └── .prompttree/registry/         ← prompt source of truth, access-controlled like any repo
       ├── nodes/                   ← immutable YAML per version, diff-able in PRs
       └── labels.json              ← prod/staging/canary pointers, changed via PR + approval

CI/CD pipeline
  └── prompttree lock --key $PT_KEY ← encrypts content before artefact is built

Production runtime
  └── PromptTree(key=os.environ["PT_KEY"])
      └── get_prompt(..., label="prod")  ← decrypts in-memory, no plaintext on disk
```

Secrets management (Vault, AWS SSM Parameter Store, Azure Key Vault) holds `PT_KEY`. The repo holds the encrypted ciphertext. Neither alone is sufficient to read a prompt — standard defence-in-depth for sensitive IP.

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
# Recommendation (prompttree ui) : Use UI for saving rapid prompt iterations
node = engine.save(
    content="Summarise the following in {{language}}: {{text}}",
    name="Summariser",
    display_name="v1",
    model="gpt-4o",
    temperature=0.7,
    label="prod",
)

# Resolve by label (scoped to the prompt family name)
prompt = engine.get_prompt("Summariser", label="prod", vars={"language": "French", "text": "the quarterly report"})
print(prompt)
# → "Summarise the following in French: the quarterly report"

# Resolve latest node in the family (no label needed)
prompt = engine.get_prompt("Summariser", vars={"language": "Spanish", "text": "the quarterly report"})

# Resolve directly by node ID
prompt = engine.get_prompt(node.id, by="id", vars={...})
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


<p>
  <img src="https://raw.githubusercontent.com/yedhuk/prompttree/main/docs/images/new_prompt_new_branch.png" alt="New Prompt/Branch">
</p>

<p>
  <img src="https://raw.githubusercontent.com/yedhuk/prompttree/main/docs/images/prompt_iteration.png" alt="Prompt Iteration">
</p>

---

## Core Concepts

### Registry

The Registry is the versioned store for your prompts. Each prompt is saved as a **node** — a YAML file containing the content, model settings, and a pointer to its parent node.

Nodes form a **DAG (directed acyclic graph)**: you branch from any existing node to create a new version, preserving the full lineage.

```
Summariser
├── v1  ←  label: prod
├── v2  (branched from v1)
└── v3  (branched from v1)
```

All nodes live in `.prompttree/registry/nodes/` and are **git-tracked** — diffs, history, and blame work out of the box.

### Labels

Labels are human-readable aliases pointing to a specific node within a prompt family. They are **scoped to the family name**, so two families can each have their own `prod` label without conflict.

```python
engine.set_label("Summariser", "prod", v2.id)
engine.set_label("Classifier", "prod", other_node.id)  # independent — no collision

engine.get_prompt("Summariser", label="prod", vars={...})
engine.get_prompt("Classifier", label="prod", vars={...})
```

Labels are stored in `.prompttree/registry/labels.json` as a nested map:

```json
{
  "Summariser":  { "prod": "a1b2c3...", "staging": "d4e5f6..." },
  "Classifier":  { "prod": "g7h8i9..." }
}
```

### Resolving Prompts

`get_prompt` has three resolution modes:

| Call | Resolves to |
|---|---|
| `get_prompt("My Prompt", label="prod")` | Node with the `prod` label in that family |
| `get_prompt("My Prompt")` | Most recently created node in the family |
| `get_prompt(node_id, by="id")` | Exact node by ID |

### Jinja2 Templating

Prompt content supports Jinja2 `{{ variable }}` syntax. Variables are injected at render time via `get_prompt()`.

```python
node = engine.save("Translate {{text}} to {{language}}.", name="Translator")
prompt = engine.get_prompt("Translator", vars={"text": "hello world", "language": "French"})
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
# Save & retrieve
engine.save(content, name, display_name, model, temperature, parent_id, tags, label) → RegistryNode
engine.get_prompt(name_or_id, label=None, by=None, vars=None) → str
engine.get_node(node_id) → RegistryNode | None
engine.list_nodes() → list[RegistryNode]
engine.list_names() → list[str]
engine.get_nodes_by_name(name) → list[RegistryNode]

# Labels
engine.get_labels() → dict[str, dict[str, str]]   # {name: {label: node_id}}
engine.set_label(name, label, node_id)

# Bulk operations
engine.delete_family(name) → int     # deletes all nodes + labels for a family
engine.reset() → int                 # wipes the entire registry

# Encryption
engine.lock(key) → int
engine.unlock(key) → int
```

---

## Branching Versions

Branch from any node by passing `parent_id`:

```python
v1 = engine.save("Summarise {{text}} briefly.", name="Summariser", label="prod")

v2 = engine.save(
    "Summarise {{text}} briefly. Use bullet points.",
    name="Summariser",
    display_name="v2",
    parent_id=v1.id,
)

# Promote v2 to prod when ready
engine.set_label("Summariser", "prod", v2.id)
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
prompt = engine.get_prompt("Summariser", label="prod", vars={...})   # decrypts on the fly
```

Uses **AES-256-GCM** with a random nonce per encryption. The key is SHA-256 hashed so any string length is accepted.

---

## CLI

```bash
prompttree init                        # initialise workspace + update .gitignore
prompttree list                        # list all nodes and labels
prompttree lock --key $PT_KEY          # encrypt registry
prompttree unlock --key $PT_KEY        # decrypt registry
prompttree delete-family <NAME>        # delete all nodes + labels for a prompt family
prompttree delete-family <NAME> --yes  # skip confirmation prompt
prompttree reset                       # wipe the entire registry
prompttree reset --yes                 # skip confirmation prompt
prompttree ui                          # launch the visual UI
prompttree ui --port 8080              # on a custom port
```


---

## Workspace Layout

```
.prompttree/
├── registry/
│   ├── nodes/          # one YAML file per prompt node (git-tracked)
│   └── labels.json     # {name: {label: node_id}} map (git-tracked)
```

`.prompttree/.lab/` and `.prompttree/.artifacts/` are local-only and automatically added to `.gitignore` by `prompttree init`.

---

## Node YAML Format

```yaml
id: "a1b2c3d4..."
parent_id: null
name: "Summariser"
display_name: "v1"
metadata:
  encrypted: false
  model: "gpt-4o"
  temperature: 0.7
  created_at: "2024-01-01T00:00:00+00:00"
  tags: []
content: "Summarise {{text}} briefly. Use bullet points."
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
