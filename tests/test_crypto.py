import pytest

from prompttree.core.crypto import decrypt, encrypt


def test_roundtrip():
    key = "test-secret-key"
    plaintext = "Analyze this P&ID drawing for {{component}}."
    assert decrypt(encrypt(plaintext, key), key) == plaintext


def test_wrong_key_raises():
    ct = encrypt("hello", "correct-key")
    with pytest.raises(Exception):
        decrypt(ct, "wrong-key")


def test_different_nonces():
    key = "key"
    msg = "same message"
    assert encrypt(msg, key) != encrypt(msg, key)
