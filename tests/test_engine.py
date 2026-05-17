from unittest.mock import patch

import pytest

from prompttree import PromptTree


@pytest.fixture
def engine(tmp_path):
    return PromptTree(storage=tmp_path)


def test_save_and_get_prompt_by_label(engine):
    engine.save("Analyze {{component}} in drawing {{drawing}}", name="pid-analyzer", label="prod")
    prompt = engine.get_prompt("pid-analyzer", label="prod", vars={"component": "valve", "drawing": "GAD_05"})
    assert prompt == "Analyze valve in drawing GAD_05"


def test_get_prompt_latest_by_name(engine):
    engine.save("v1 prompt", name="pid-analyzer")
    engine.save("v2 prompt", name="pid-analyzer")
    assert engine.get_prompt("pid-analyzer") == "v2 prompt"


def test_get_prompt_by_id(engine):
    node = engine.save("Hello {{x}}")
    assert engine.get_prompt(node.id, by="id", vars={"x": "world"}) == "Hello world"


def test_get_prompt_missing_raises(engine):
    with pytest.raises(KeyError):
        engine.get_prompt("nonexistent")


def test_get_prompt_missing_label_raises(engine):
    engine.save("a prompt", name="pid-analyzer")
    with pytest.raises(KeyError):
        engine.get_prompt("pid-analyzer", label="nonexistent")


def test_lock_unlock(engine):
    engine.save("secret content", name="my-prompt", label="prod")
    engine.lock("mykey")
    node_id = engine.get_labels()["my-prompt"]["prod"]
    node = engine.get_node(node_id)
    assert node.metadata.encrypted is True

    locked_engine = PromptTree(storage=engine._storage)
    with pytest.raises(ValueError, match="no key was provided"):
        locked_engine.get_prompt("my-prompt", label="prod")

    keyed_engine = PromptTree(storage=engine._storage, key="mykey")
    assert keyed_engine.get_prompt("my-prompt", label="prod") == "secret content"


def test_promote(tmp_path):
    engine = PromptTree(storage=tmp_path)
    with patch("prompttree.llm.client.LLMClient.complete", return_value="ok"):
        with engine.lab_session() as lab:
            exp = lab.run(prompt_text="Draft prompt for {{drawing}}")

    node = engine.promote(exp.id, name="my-prompt", label="draft", model="gpt-4o", temperature=0.5)
    assert node.content == "Draft prompt for {{drawing}}"
    assert engine.get_labels()["my-prompt"]["draft"] == node.id
    assert engine.get_prompt("my-prompt", label="draft", vars={"drawing": "GAD_01"}) == "Draft prompt for GAD_01"


def test_promote_label_without_name_raises(tmp_path):
    engine = PromptTree(storage=tmp_path)
    with patch("prompttree.llm.client.LLMClient.complete", return_value="ok"):
        with engine.lab_session() as lab:
            exp = lab.run(prompt_text="some prompt")

    with pytest.raises(ValueError, match="'name' is required"):
        engine.promote(exp.id, label="draft")


def test_list_nodes(engine):
    engine.save("node a")
    engine.save("node b")
    assert len(engine.list_nodes()) == 2


def test_get_labels(engine):
    node = engine.save("x", name="my-prompt", label="alpha")
    labels = engine.get_labels()
    assert labels["my-prompt"]["alpha"] == node.id


def test_delete_family(engine):
    engine.save("v1", name="pid-analyzer", label="prod")
    engine.save("v2", name="pid-analyzer")
    engine.save("other", name="report-gen", label="prod")

    count = engine.delete_family("pid-analyzer")

    assert count == 2
    assert engine.get_nodes_by_name("pid-analyzer") == []
    assert "pid-analyzer" not in engine.get_labels()
    assert engine.get_nodes_by_name("report-gen") != []
    assert "report-gen" in engine.get_labels()


def test_delete_family_nonexistent(engine):
    assert engine.delete_family("ghost") == 0


def test_reset(engine):
    engine.save("a", name="family-a", label="prod")
    engine.save("b", name="family-b")

    count = engine.reset()

    assert count == 2
    assert engine.list_nodes() == []
    assert engine.get_labels() == {}


def test_labels_scoped_per_name(engine):
    n1 = engine.save("prompt a", name="family-a", label="prod")
    n2 = engine.save("prompt b", name="family-b", label="prod")
    labels = engine.get_labels()
    assert labels["family-a"]["prod"] == n1.id
    assert labels["family-b"]["prod"] == n2.id
    assert engine.get_prompt("family-a", label="prod") == "prompt a"
    assert engine.get_prompt("family-b", label="prod") == "prompt b"
