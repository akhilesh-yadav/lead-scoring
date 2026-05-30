"""
Abstract base classes for pipeline stages.

Implements the Template Method pattern: each stage defines a common interface
(validate → execute → report), and concrete stages override the core logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from src.pipeline.logging_config import logger


@dataclass
class StageResult:
    """Standard output wrapper from any pipeline stage."""
    data: Any
    metrics: Dict[str, Any] = field(default_factory=dict)
    stage_name: str = ""


class PipelineStage(ABC):
    """Base class for all pipeline stages (Template Method pattern).

    Subclasses implement:
        - `_validate_input` — pre-condition checks
        - `_execute` — core transformation logic
        - `stage_name` property — human-readable name for logging
    """

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Human-readable name for logging."""
        ...

    def run(self, input_data: Any) -> StageResult:
        """Template method: validate → execute → report."""
        logger.info(f"[{self.stage_name}] Starting...")
        self._validate_input(input_data)
        result = self._execute(input_data)
        logger.info(f"[{self.stage_name}] Complete. Metrics: {result.metrics}")
        return result

    @abstractmethod
    def _validate_input(self, input_data: Any) -> None:
        """Pre-condition checks. Raise ValueError on bad input."""
        ...

    @abstractmethod
    def _execute(self, input_data: Any) -> StageResult:
        """Core transformation logic."""
        ...
