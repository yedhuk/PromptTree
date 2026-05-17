import pytest

from prompttree.core.registry import Registry
from prompttree.models.node import NodeMetadata, RegistryNode


@pytest.fixture
def registry(tmp_path):
    return Registry(tmp_path)


def test_save_and_get(registry):
    node = RegistryNode(content="Hello {{name}}")
    registry.save(node)
    loaded = registry.get(node.id)
    assert loaded is not None
    assert loaded.content == "Hello {{name}}"


def test_get_missing_returns_none(registry):
    assert registry.get("nonexistent") is None


def test_labels(registry):
    node = RegistryNode(content="prod prompt", name="my-prompt")
    registry.save(node)
    registry.set_label("my-prompt", "prod", node.id)
    found = registry.get_by_label("my-prompt", "prod")
    assert found is not None
    assert found.id == node.id


def test_label_missing_returns_none(registry):
    assert registry.get_by_label("missing", "prod") is None


def test_remove_label(registry):
    node = RegistryNode(content="x", name="my-prompt")
    registry.save(node)
    registry.set_label("my-prompt", "alpha", node.id)
    registry.remove_label("my-prompt", "alpha")
    assert registry.get_by_label("my-prompt", "alpha") is None


def test_children(registry):
    parent = RegistryNode(content="parent")
    child1 = RegistryNode(content="child1", parent_id=parent.id)
    child2 = RegistryNode(content="child2", parent_id=parent.id)
    registry.save(parent)
    registry.save(child1)
    registry.save(child2)
    children = registry.children(parent.id)
    assert {c.id for c in children} == {child1.id, child2.id}


def test_lock_unlock(registry):
    node = RegistryNode(content="secret prompt")
    registry.save(node)
    registry.lock("mykey")
    locked = registry.get(node.id)
    assert locked.metadata.encrypted is True
    assert locked.content != "secret prompt"

    registry.unlock("mykey")
    unlocked = registry.get(node.id)
    assert unlocked.metadata.encrypted is False
    assert unlocked.content == "secret prompt"


def test_lock_count(registry):
    registry.save(RegistryNode(content="a"))
    registry.save(RegistryNode(content="b"))
    count = registry.lock("k")
    assert count == 2


def test_persistence(tmp_path):
    r1 = Registry(tmp_path)
    node = RegistryNode(content="persisted", name="my-prompt")
    r1.save(node)
    r1.set_label("my-prompt", "prod", node.id)

    r2 = Registry(tmp_path)
    assert r2.get(node.id) is not None
    assert r2.get_by_label("my-prompt", "prod").id == node.id


def test_delete(registry):
    node = RegistryNode(content="to delete")
    registry.save(node)
    registry.delete(node.id)
    assert registry.get(node.id) is None


def test_delete_family(registry):
    n1 = RegistryNode(content="v1", name="my-prompt")
    n2 = RegistryNode(content="v2", name="my-prompt")
    other = RegistryNode(content="other", name="other-prompt")
    registry.save(n1)
    registry.save(n2)
    registry.save(other)
    registry.set_label("my-prompt", "prod", n2.id)

    count = registry.delete_family("my-prompt")

    assert count == 2
    assert registry.get(n1.id) is None
    assert registry.get(n2.id) is None
    assert registry.get(other.id) is not None
    assert "my-prompt" not in registry.get_labels()


def test_delete_family_nonexistent(registry):
    assert registry.delete_family("ghost") == 0


def test_reset(registry):
    registry.save(RegistryNode(content="a", name="family-a"))
    registry.save(RegistryNode(content="b", name="family-b"))
    registry.set_label("family-a", "prod", registry.all_nodes()[0].id)

    count = registry.reset()

    assert count == 2
    assert registry.all_nodes() == []
    assert registry.get_labels() == {}
