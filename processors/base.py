# processors/base.py
from abc import ABC, abstractmethod
from typing import Optional

class ProcessorResult:
    def __init__(self, name: str, success: bool = True, details: dict = None):
        self.name = name
        self.success = success
        self.details = details or {}

    def __repr__(self):
        return f"ProcessorResult(name={self.name!r}, success={self.success}, details={self.details})"

class Processor(ABC):
    """
    Subclass this to create a processor. Provide `run(specific_day=None, dry_run=False)`.
    """
    def __init__(self, gemini, excel, config: dict = None):
        self.gemini = gemini
        self.excel = excel
        self.config = config or {}

    @abstractmethod
    def run(self, specific_day=None, dry_run: bool = False) -> ProcessorResult:
        pass
