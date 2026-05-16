from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Optional


class ArtifactStore:
    def __init__(self, storage: Path) -> None:
        self._root = storage / ".artifacts"
        self._root.mkdir(parents=True, exist_ok=True)

    def _owner_dir(self, owner_id: str) -> Path:
        return self._root / owner_id

    def _meta_path(self, owner_id: str) -> Path:
        return self._owner_dir(owner_id) / "meta.json"

    def save(
        self,
        owner_id: str,
        source_path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Path:
        dest_dir = self._owner_dir(owner_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        if metadata is not None:
            meta_path = self._meta_path(owner_id)
            existing: dict[str, Any] = (
                json.loads(meta_path.read_text()) if meta_path.exists() else {}
            )
            existing[src.name] = metadata
            meta_path.write_text(json.dumps(existing, indent=2))
        return dest

    def list(self, owner_id: str) -> dict[str, dict[str, Any]]:
        owner_dir = self._owner_dir(owner_id)
        if not owner_dir.exists():
            return {}
        meta_path = self._meta_path(owner_id)
        metadata: dict[str, Any] = (
            json.loads(meta_path.read_text()) if meta_path.exists() else {}
        )
        return {
            f.name: {"path": str(f), "metadata": metadata.get(f.name, {})}
            for f in owner_dir.iterdir()
            if f.name != "meta.json"
        }

    def relink(self, from_id: str, to_id: str) -> None:
        """Copy an artifact folder to a new owner (used during Lab → Registry promotion)."""
        src_dir = self._owner_dir(from_id)
        if not src_dir.exists():
            return
        dest_dir = self._owner_dir(to_id)
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)
