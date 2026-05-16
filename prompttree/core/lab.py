from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Optional

from ..models.experiment import LabExperiment
from .artifacts import ArtifactStore


class LabSession:
    """Context manager for a Lab experimentation session.

    Data is appended to experiments.jsonl immediately after each run so
    nothing is lost if the session exits early.
    """

    def __init__(self, storage: Path, artifacts: ArtifactStore) -> None:
        self._lab_dir = storage / ".lab"
        self._lab_dir.mkdir(parents=True, exist_ok=True)
        self._experiments_file = self._lab_dir / "experiments.jsonl"
        self._artifacts = artifacts
        self._current: Optional[LabExperiment] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> LabSession:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        prompt_text: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        images: Optional[list[str]] = None,
        vars: Optional[dict[str, Any]] = None,
    ) -> LabExperiment:
        from jinja2 import Template

        from ..llm.client import LLMClient

        images = images or []
        vars = vars or {}
        rendered = Template(prompt_text).render(**vars)

        experiment = LabExperiment(
            prompt_text=prompt_text,
            model=model,
            temperature=temperature,
            images=images,
            vars=vars,
        )
        try:
            experiment.response = LLMClient().complete(rendered, model, temperature, images)
        except Exception as exc:
            experiment.error = str(exc)

        self._append(experiment)
        self._current = experiment
        return experiment

    def save_artifact(
        self,
        path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Path:
        if self._current is None:
            raise RuntimeError("No active experiment. Call run() first.")
        return self._artifacts.save(self._current.id, path, metadata)

    def history(self) -> list[LabExperiment]:
        if not self._experiments_file.exists():
            return []
        results = []
        for line in self._experiments_file.read_text().splitlines():
            line = line.strip()
            if line:
                results.append(LabExperiment.model_validate_json(line))
        return results

    def get(self, lab_id: str) -> Optional[LabExperiment]:
        for exp in self.history():
            if exp.id == lab_id:
                return exp
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append(self, experiment: LabExperiment) -> None:
        with open(self._experiments_file, "a") as f:
            f.write(experiment.model_dump_json() + "\n")
