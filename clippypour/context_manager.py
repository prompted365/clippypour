import os
import json
from typing import Dict, Any

class ContextManager:
    """
    Manages the context for the ClippyPour application.
    Stores and retrieves data from persistent memory (JSON).
    """
    def __init__(self, storage_path: str = "context_storage.json"):
        """
        Initialize the ContextManager.
        
        Args:
            storage_path (str): Path to the JSON file for persistent storage.
        """
        self.storage_path = storage_path
        self.context = self._load_context()
    
    def _load_context(self) -> Dict:
        """Load context from the JSON file or create a new one if it doesn't exist."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {self.storage_path}. Creating new context.")
                return {}
        return {}
    
    def save_context(self) -> None:
        """Save the current context to the JSON file."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.context, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self.context.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the context and save it."""
        self.context[key] = value
        self.save_context()
    
    def update(self, data: Dict) -> None:
        """Update multiple values in the context and save it."""
        self.context.update(data)
        self.save_context()
    
    def delete(self, key: str) -> None:
        """Delete a key from the context and save it."""
        if key in self.context:
            del self.context[key]
            self.save_context()
    
    def clear(self) -> None:
        """Clear all context data and save it."""
        self.context = {}
        self.save_context()