# Developer Guide

Setup, development workflow, and release checklist for PromptTree.

---

## Local Setup

```bash
git clone https://github.com/yedhuk/prompttree
cd prompttree

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev,ui]"
```

This installs the package in editable mode with all dev and UI dependencies.

---

## Project Structure

```
prompttree/
├── core/
│   ├── engine.py       # PromptTree — top-level public API
│   ├── registry.py     # Registry — DAG loader, YAML CRUD, lock/unlock
│   ├── lab.py          # LabSession [v1.1, not exported]
│   ├── artifacts.py    # ArtifactStore [v1.1, not exported]
│   └── crypto.py       # AES-256-GCM encrypt/decrypt
├── models/
│   ├── node.py         # RegistryNode + NodeMetadata (Pydantic v2)
│   └── experiment.py   # LabExperiment [v1.1, not exported]
├── llm/
│   └── client.py       # LiteLLM wrapper
├── ui/
│   ├── app.py          # Streamlit UI
│   └── assets/         # Logo and static assets
└── cli.py              # Click CLI
docs/
tests/
pyproject.toml
README.md
```

---

## Daily Development

### Running tests

```bash
# Run all active tests (lab and artifacts excluded)
pytest

# Verbose output
pytest -v

# Single file
pytest tests/test_registry.py

# Single test
pytest tests/test_registry.py::test_persistence

# With coverage report
pytest --cov=prompttree --cov-report=term-missing
```

> `test_lab.py` and `test_artifacts.py` are excluded via `addopts` in `pyproject.toml` until v1.1.

### Lint

```bash
ruff check prompttree/

# Auto-fix safe issues
ruff check prompttree/ --fix
```

### Type check

```bash
mypy prompttree/
```

### Run the UI locally

```bash
prompttree init           # only needed once per project
prompttree ui             # opens http://localhost:8501
prompttree ui --port 8080 # custom port
```

---

## Adding a New Feature

1. Add implementation under `prompttree/core/` or `prompttree/models/`
2. Add tests under `tests/`
3. If it's part of the public API, export it in `prompttree/__init__.py` and `prompttree/models/__init__.py`
4. Update `CLAUDE.md` if the architecture changes
5. Update `README.md` if user-facing behaviour changes

---

## Release Checklist

Follow these steps in order every time you publish a new version.

### 1. Update version

Bump `version` in `pyproject.toml`:

```toml
[project]
version = "1.0.1"   # patch / minor / major as appropriate
```

### 2. Run tests

```bash
pytest
```

All tests must pass. No skips allowed on release.

### 3. Lint

```bash
ruff check prompttree/
```

Must produce zero errors.

### 4. Type check

```bash
mypy prompttree/
```

Must produce zero errors.

### 5. Clean previous builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 6. Build the package

```bash
python -m build
```

Produces:
```
dist/
  prompttree-x.y.z.tar.gz
  prompttree-x.y.z-py3-none-any.whl
```

### 7. Verify the package

```bash
twine check dist/*
```

Must output `PASSED` for both files.

### 8. Test on TestPyPI

```bash
twine upload --repository testpypi dist/*
```

Install from TestPyPI and smoke-test:

```bash
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  prompttree
python -c "import prompttree; print(prompttree.__version__)"
```

> `--extra-index-url` is required because TestPyPI only hosts a small subset of packages. Dependencies like `pydantic` and `litellm` are pulled from real PyPI via the fallback.

### 9. Publish to PyPI

```bash
twine upload dist/*
```

Use your PyPI API token when prompted:
```
username: __token__
password: pypi-xxxxxxxxxxxx
```

### 10. Tag the release

```bash
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin v1.0.0
```
Tag after commit.

### 11. Verify on PyPI

```bash
pip install prompttree==1.0.0
python -c "import prompttree; print(prompttree.__version__)"
```

---

## Release Checklist Summary

| Step | Command | Must pass |
|---|---|---|
| Tests | `pytest` | All 20 pass |
| Lint | `ruff check prompttree/` | Zero errors |
| Type check | `mypy prompttree/` | Zero errors |
| Clean | `rm -rf dist/ build/` | — |
| Build | `python -m build` | Two files in `dist/` |
| Verify | `twine check dist/*` | PASSED |
| TestPyPI | `twine upload --repository testpypi dist/*` | Installs cleanly |
| PyPI | `twine upload dist/*` | — |
| Git tag | `git tag vX.Y.Z && git push origin vX.Y.Z` | — |

---

## PyPI Credentials Setup

Create a `.pypirc` file in your home directory to avoid entering credentials each time:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-xxxxxxxxxxxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxxxxxxxxxxx
```

```bash
chmod 600 ~/.pypirc
```

---

## v1.1 Release — Enabling Lab & Artifacts

When ready to ship Lab and Artifacts:

1. Re-export in `prompttree/__init__.py`:
```python
from .core.lab import LabSession
from .core.artifacts import ArtifactStore
from .models.experiment import LabExperiment

__all__ = ["PromptTree", "RegistryNode", "NodeMetadata", "LabSession", "ArtifactStore", "LabExperiment"]
```

2. Re-export in `prompttree/models/__init__.py`:
```python
from .experiment import LabExperiment
__all__ = ["NodeMetadata", "RegistryNode", "LabExperiment"]
```

3. Re-enable tests in `pyproject.toml` — remove the `addopts` ignore lines:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

4. Run the full 32-test suite and confirm all pass before releasing.
