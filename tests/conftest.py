"""Shared test fixtures for all tests."""
import pytest
import os


@pytest.fixture
def test_repo():
    """
    Return the path to the test repository.

    Can be overridden via TEST_REPO_PATH environment variable.
    """
    return os.environ.get(
        "TEST_REPO_PATH",
        r"C:\Users\Naomi\Desktop\ONNX\onnxruntime"
    )
