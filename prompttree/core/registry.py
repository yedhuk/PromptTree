from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml

from ..models.node import RegistryNode


class Registry:
    def __init__(self, storage: Path) -> None:
        self._nodes_dir = storage / "registry" / "nodes"
        self._labels_file = storage / "registry" / "labels.json"
        self._nodes_dir.mkdir(parents=True, exist_ok=True)
        if not self._labels_file.exists():
            self._labels_file.write_text("{}")
        self._nodes: dict[str, RegistryNode] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._nodes = {}
        for path in self._nodes_dir.glob("*.yaml"):
            with open(path) as f:
                data = yaml.safe_load(f)
            node = RegistryNode.model_validate(data)
            self._nodes[node.id] = node

    def _node_path(self, node_id: str) -> Path:
        return self._nodes_dir / f"{node_id}.yaml"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, node: RegistryNode) -> RegistryNode:
        with open(self._node_path(node.id), "w") as f:
            yaml.dump(node.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
        self._nodes[node.id] = node
        return node

    def get(self, node_id: str) -> Optional[RegistryNode]:
        return self._nodes.get(node_id)

    def delete(self, node_id: str) -> None:
        path = self._node_path(node_id)
        if path.exists():
            path.unlink()
        self._nodes.pop(node_id, None)

    def all_nodes(self) -> list[RegistryNode]:
        return list(self._nodes.values())

    def children(self, node_id: str) -> list[RegistryNode]:
        return [n for n in self._nodes.values() if n.parent_id == node_id]

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def get_by_label(self, label: str) -> Optional[RegistryNode]:
        labels = self._read_labels()
        node_id = labels.get(label)
        return self._nodes.get(node_id) if node_id else None

    def set_label(self, label: str, node_id: str) -> None:
        labels = self._read_labels()
        labels[label] = node_id
        self._labels_file.write_text(json.dumps(labels, indent=2))

    def remove_label(self, label: str) -> None:
        labels = self._read_labels()
        labels.pop(label, None)
        self._labels_file.write_text(json.dumps(labels, indent=2))

    def get_labels(self) -> dict[str, str]:
        return self._read_labels()

    def _read_labels(self) -> dict[str, str]:
        result: dict[str, str] = json.loads(self._labels_file.read_text())
        return result

    # ------------------------------------------------------------------
    # Bulk encrypt / decrypt (called by CLI `lock` / `unlock`)
    # ------------------------------------------------------------------

    def lock(self, key: str) -> int:
        from .crypto import encrypt

        count = 0
        for node in list(self._nodes.values()):
            if not node.metadata.encrypted:
                node.content = encrypt(node.content, key)
                node.metadata.encrypted = True
                self.save(node)
                count += 1
        return count

    def unlock(self, key: str) -> int:
        from .crypto import decrypt

        count = 0
        for node in list(self._nodes.values()):
            if node.metadata.encrypted:
                node.content = decrypt(node.content, key)
                node.metadata.encrypted = False
                self.save(node)
                count += 1
        return count
