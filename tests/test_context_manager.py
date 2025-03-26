import os
import json
import tempfile
import pytest
from clippypour.context_manager import ContextManager

@pytest.fixture
def temp_storage_file():
    """Create a temporary file for context storage."""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.unlink(path)

def test_context_manager_init(temp_storage_file):
    """Test that the ContextManager initializes correctly."""
    manager = ContextManager(temp_storage_file)
    assert manager.context == {}
    assert manager.storage_path == temp_storage_file

def test_context_manager_set_get(temp_storage_file):
    """Test setting and getting values from the context."""
    manager = ContextManager(temp_storage_file)
    manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"
    assert manager.get("nonexistent_key") is None
    assert manager.get("nonexistent_key", "default") == "default"

def test_context_manager_update(temp_storage_file):
    """Test updating multiple values in the context."""
    manager = ContextManager(temp_storage_file)
    manager.update({"key1": "value1", "key2": "value2"})
    assert manager.get("key1") == "value1"
    assert manager.get("key2") == "value2"

def test_context_manager_delete(temp_storage_file):
    """Test deleting a key from the context."""
    manager = ContextManager(temp_storage_file)
    manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"
    manager.delete("test_key")
    assert manager.get("test_key") is None

def test_context_manager_clear(temp_storage_file):
    """Test clearing all context data."""
    manager = ContextManager(temp_storage_file)
    manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"
    manager.clear()
    assert manager.context == {}

def test_context_manager_persistence(temp_storage_file):
    """Test that the context is persisted to disk."""
    manager1 = ContextManager(temp_storage_file)
    manager1.set("test_key", "test_value")
    
    # Create a new manager with the same storage path
    manager2 = ContextManager(temp_storage_file)
    assert manager2.get("test_key") == "test_value"