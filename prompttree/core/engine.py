from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..models.node import NodeMetadata, RegistryNode
from .artifacts import ArtifactStore
from .lab import LabSession
from .registry import Registry


class PromptTree:
    """Top-level public API for PromptTree v1.0.

    Parameters
    ----------
    storage:
        Path to the ``.prompttree`` directory.  Created if it does not exist.
    key:
        AES-256 decryption key.  Required only when the registry has been
        locked via ``prompttree lock``.
    """

    def __init__(self, storage: str | Path = ".prompttree", key: Optional[str] = None) -> None:
        self._storage = Path(storage)
        self._storage.mkdir(parents=True, exist_ok=True)
        self._key = key
        self._registry = Registry(self._storage)
        self._artifacts = ArtifactStore(self._storage)
        self._lab = LabSession(self._storage, self._artifacts)

    # ------------------------------------------------------------------
    # Production API
    # ------------------------------------------------------------------

    def get_prompt(
        self,
        label_or_id: str,
        vars: Optional[dict[str, Any]] = None,
    ) -> str:
        """Resolve a label or node ID to a rendered prompt string.

        Decrypts content in-memory if the engine was initialised with a key.
        """
        from jinja2 import Template

        node = self._registry.get_by_label(label_or_id) or self._registry.get(label_or_id)
        if node is None:
            raise KeyError(f"No node found for label/id '{label_or_id}'")

        content = node.content
        if node.metadata.encrypted:
            if self._key is None:
                raise ValueError(
                    f"Node '{node.id}' is encrypted but no key was provided to PromptTree()."
                )
            from .crypto import decrypt
            content = decrypt(content, self._key)

        return Template(content).render(**(vars or {}))

    def save(
        self,
        content: str,
        name: str = "",
        display_name: str = "",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        parent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        label: Optional[str] = None,
    ) -> RegistryNode:
        """Create and persist a new Registry node."""
        node = RegistryNode(
            parent_id=parent_id,
            name=name,
            display_name=display_name,
            content=content,
            metadata=NodeMetadata(
                model=model,
                temperature=temperature,
                tags=tags or [],
            ),
        )
        self._registry.save(node)
        if label:
            self._registry.set_label(label, node.id)
        return node

    def list_names(self) -> list[str]:
        """Return sorted list of distinct prompt family names."""
        return sorted({n.name for n in self._registry.all_nodes() if n.name})

    def get_nodes_by_name(self, name: str) -> list[RegistryNode]:
        """Return all nodes belonging to a prompt family."""
        return [n for n in self._registry.all_nodes() if n.name == name]

    def set_label(self, label: str, node_id: str) -> None:
        self._registry.set_label(label, node_id)

    def get_node(self, node_id: str) -> Optional[RegistryNode]:
        return self._registry.get(node_id)

    def list_nodes(self) -> list[RegistryNode]:
        return self._registry.all_nodes()

    def get_labels(self) -> dict[str, str]:
        return self._registry.get_labels()

    # ------------------------------------------------------------------
    # Lab API
    # ------------------------------------------------------------------

    def lab_session(self) -> LabSession:
        """Return the active LabSession (reuse across multiple ``with`` blocks)."""
        return self._lab

    def promote(
        self,
        lab_id: str,
        parent_id: Optional[str] = None,
        label: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> RegistryNode:
        """Promote a Lab experiment to the Registry.

        Copies the prompt to a new Registry node, relinks artifacts, and
        optionally assigns a label.
        """
        exp = self._lab.get(lab_id)
        if exp is None:
            raise KeyError(f"Lab experiment '{lab_id}' not found.")

        node = RegistryNode(
            parent_id=parent_id,
            content=exp.prompt_text,
            metadata=NodeMetadata(
                model=model or exp.model,
                temperature=temperature if temperature is not None else exp.temperature,
            ),
        )
        self._registry.save(node)

        if label:
            self._registry.set_label(label, node.id)

        self._artifacts.relink(lab_id, node.id)
        return node

    # ------------------------------------------------------------------
    # Encryption helpers (also exposed via CLI)
    # ------------------------------------------------------------------

    def lock(self, key: str) -> int:
        """Encrypt all plaintext nodes. Returns count of nodes locked."""
        return self._registry.lock(key)

    def unlock(self, key: str) -> int:
        """Decrypt all encrypted nodes. Returns count of nodes unlocked."""
        return self._registry.unlock(key)
