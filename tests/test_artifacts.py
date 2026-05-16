import json

import pytest

from prompttree.core.artifacts import ArtifactStore


@pytest.fixture
def store(tmp_path):
    return ArtifactStore(tmp_path)


@pytest.fixture
def sample_image(tmp_path):
    p = tmp_path / "crop_01.png"
    p.write_bytes(b"fake png data")
    return str(p)


def test_save_and_list(store, sample_image):
    dest = store.save("owner_1", sample_image, metadata={"box": [0, 0, 50, 50]})
    assert dest.exists()
    listing = store.list("owner_1")
    assert "crop_01.png" in listing
    assert listing["crop_01.png"]["metadata"] == {"box": [0, 0, 50, 50]}


def test_save_without_metadata(store, sample_image):
    store.save("owner_2", sample_image)
    listing = store.list("owner_2")
    assert "crop_01.png" in listing
    assert listing["crop_01.png"]["metadata"] == {}


def test_list_missing_owner(store):
    assert store.list("nobody") == {}


def test_relink(store, sample_image):
    store.save("lab_abc", sample_image, metadata={"src": "lab"})
    store.relink("lab_abc", "node_xyz")
    listing = store.list("node_xyz")
    assert "crop_01.png" in listing
    assert listing["crop_01.png"]["metadata"]["src"] == "lab"
