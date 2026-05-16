from unittest.mock import patch

import pytest

from prompttree import PromptTree


@pytest.fixture
def engine(tmp_path):
    return PromptTree(storage=tmp_path)


def test_save_and_get_prompt(engine):
    node = engine.save("Analyze {{component}} in drawing {{drawing}}", label="prod")
    prompt = engine.get_prompt("prod", vars={"component": "valve", "drawing": "GAD_05"})
    assert prompt == "Analyze valve in drawing GAD_05"


def test_get_prompt_by_id(engine):
    node = engine.save("Hello {{x}}")
    assert engine.get_prompt(node.id, vars={"x": "world"}) == "Hello world"


def test_get_prompt_missing_raises(engine):
    with pytest.raises(KeyError):
        engine.get_prompt("nonexistent")


def test_lock_unlock(engine):
    engine.save("secret content", label="prod")
    engine.lock("mykey")
    node = engine.get_node(engine.get_labels()["prod"])
    assert node.metadata.encrypted is True

    locked_engine = PromptTree(storage=engine._storage)
    with pytest.raises(ValueError, match="no key was provided"):
        locked_engine.get_prompt("prod")

    keyed_engine = PromptTree(storage=engine._storage, key="mykey")
    assert keyed_engine.get_prompt("prod") == "secret content"


def test_promote(tmp_path):
    engine = PromptTree(storage=tmp_path)
    with patch("prompttree.llm.client.LLMClient.complete", return_value="ok"):
        with engine.lab_session() as lab:
            exp = lab.run(prompt_text="Draft prompt for {{drawing}}")

    node = engine.promote(exp.id, label="draft", model="gpt-4o", temperature=0.5)
    assert node.content == "Draft prompt for {{drawing}}"
    assert engine.get_labels().get("draft") == node.id
    assert engine.get_prompt("draft", vars={"drawing": "GAD_01"}) == "Draft prompt for GAD_01"


def test_list_nodes(engine):
    engine.save("node a")
    engine.save("node b")
    assert len(engine.list_nodes()) == 2


def test_get_labels(engine):
    node = engine.save("x", label="alpha")
    labels = engine.get_labels()
    assert labels["alpha"] == node.id
