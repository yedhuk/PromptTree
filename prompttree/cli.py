from __future__ import annotations

from pathlib import Path

import click

from .core.engine import PromptTree


@click.group()
def cli() -> None:
    """PromptTree — Git-native prompt engineering toolkit."""


@cli.command()
@click.option("--storage", default=".prompttree", show_default=True, help="Storage directory.")
def init(storage: str) -> None:
    """Initialise a .prompttree workspace in the current project."""
    PromptTree(storage=storage)
    click.echo(f"Initialised PromptTree workspace at '{storage}'.")

    gitignore = Path(".gitignore")
    entries = [".prompttree/.lab/", ".prompttree/.artifacts/"]
    if gitignore.exists():
        existing = gitignore.read_text()
        missing = [e for e in entries if e not in existing]
        if missing:
            with open(gitignore, "a") as f:
                f.write("\n# PromptTree local-only data\n")
                for entry in missing:
                    f.write(entry + "\n")
            click.echo(f"Added {len(missing)} entries to .gitignore.")
    else:
        click.echo(
            "No .gitignore found — create one and add "
            ".prompttree/.lab/ and .prompttree/.artifacts/"
        )


@cli.command()
@click.option("--storage", default=".prompttree", show_default=True)
@click.option("--key", envvar="PT_KEY", required=True, help="Encryption key (or set PT_KEY).")
def lock(storage: str, key: str) -> None:
    """Encrypt all plaintext Registry nodes (run in CI before deploy)."""
    pt = PromptTree(storage=storage)
    count = pt.lock(key)
    click.echo(f"Locked {count} node(s).")


@cli.command()
@click.option("--storage", default=".prompttree", show_default=True)
@click.option("--key", envvar="PT_KEY", required=True, help="Decryption key (or set PT_KEY).")
def unlock(storage: str, key: str) -> None:
    """Decrypt all encrypted Registry nodes."""
    pt = PromptTree(storage=storage)
    count = pt.unlock(key)
    click.echo(f"Unlocked {count} node(s).")


@cli.command()
@click.option("--storage", default=".prompttree", show_default=True, help="Storage directory.")
@click.option("--port", default=8501, show_default=True, help="Port to serve the UI on.")
def ui(storage: str, port: int) -> None:
    """Launch the PromptTree Streamlit UI."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        raise click.ClickException(
            "Streamlit is not installed. Run: pip install \"prompttree[ui]\""
        )

    import subprocess
    import sys
    from pathlib import Path as _Path

    app = _Path(__file__).parent / "ui" / "app.py"
    env = {**__import__("os").environ, "PROMPTTREE_STORAGE": storage}
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(port)],
        env=env,
    )


@cli.command("list")
@click.option("--storage", default=".prompttree", show_default=True)
def list_nodes(storage: str) -> None:
    """List all Registry nodes and labels."""
    pt = PromptTree(storage=storage)
    labels = pt.get_labels()
    reversed_labels: dict[str, list[str]] = {}
    for label, node_id in labels.items():
        reversed_labels.setdefault(node_id, []).append(label)

    nodes = pt.list_nodes()
    if not nodes:
        click.echo("Registry is empty.")
        return

    for node in sorted(nodes, key=lambda n: n.metadata.created_at):
        node_labels = reversed_labels.get(node.id, [])
        label_str = f"  [{', '.join(node_labels)}]" if node_labels else ""
        encrypted_str = " (encrypted)" if node.metadata.encrypted else ""
        line = (
            f"{node.id[:12]}  {node.metadata.model}"
            f"  {node.metadata.created_at:%Y-%m-%d}{label_str}{encrypted_str}"
        )
        click.echo(line)
