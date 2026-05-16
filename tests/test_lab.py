from unittest.mock import MagicMock, patch

import pytest

from prompttree.core.artifacts import ArtifactStore
from prompttree.core.lab import LabSession
from prompttree.models.experiment import LabExperiment


@pytest.fixture
def lab(tmp_path):
    artifacts = ArtifactStore(tmp_path)
    return LabSession(tmp_path, artifacts)


def _mock_complete(response="mocked response"):
    mock = MagicMock()
    mock.return_value = response
    return mock


def test_run_success(lab, tmp_path):
    with patch("prompttree.llm.client.LLMClient.complete", _mock_complete()):
        exp = lab.run(prompt_text="Hello {{name}}", vars={"name": "World"})
    assert exp.response == "mocked response"
    assert exp.error is None
    assert exp.prompt_text == "Hello {{name}}"


def test_run_error_captured(lab):
    with patch("prompttree.llm.client.LLMClient.complete", side_effect=RuntimeError("API down")):
        exp = lab.run(prompt_text="fail")
    assert exp.error == "API down"
    assert exp.response is None


def test_history_persistence(lab):
    with patch("prompttree.llm.client.LLMClient.complete", _mock_complete()):
        lab.run(prompt_text="run 1")
        lab.run(prompt_text="run 2")
    history = lab.history()
    assert len(history) == 2
    assert history[0].prompt_text == "run 1"
    assert history[1].prompt_text == "run 2"


def test_get_by_id(lab):
    with patch("prompttree.llm.client.LLMClient.complete", _mock_complete()):
        exp = lab.run(prompt_text="find me")
    found = lab.get(exp.id)
    assert found is not None
    assert found.prompt_text == "find me"


def test_get_missing_returns_none(lab):
    assert lab.get("lab_nonexistent") is None


def test_save_artifact_requires_run(lab):
    with pytest.raises(RuntimeError, match="No active experiment"):
        lab.save_artifact("/some/path.png")


def test_save_artifact_after_run(lab, tmp_path):
    img = tmp_path / "crop.png"
    img.write_bytes(b"img")
    with patch("prompttree.llm.client.LLMClient.complete", _mock_complete()):
        lab.run(prompt_text="test")
    dest = lab.save_artifact(str(img), metadata={"box": [1, 2, 3, 4]})
    assert dest.exists()


def test_context_manager(tmp_path):
    artifacts = ArtifactStore(tmp_path)
    with LabSession(tmp_path, artifacts) as session:
        with patch("prompttree.llm.client.LLMClient.complete", _mock_complete()):
            exp = session.run(prompt_text="inside context")
    assert exp.response == "mocked response"
