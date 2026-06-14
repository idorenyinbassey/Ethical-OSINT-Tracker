from abc import ABC, abstractmethod


class BasePlugin(ABC):
    name: str = ""
    label: str = ""
    description: str = ""
    input_label: str = "Query"
    input_placeholder: str = "Enter a value"
    category: str = "General"

    @abstractmethod
    def run(self, query: str) -> dict:
        """Execute the plugin. Return dict with at minimum a 'result' or 'error' key."""
        ...
