from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Protocol

from pydantic import Field

from ..model import StrictModel
from ..v2 import AgentWorkOrder


class AgentRunStatus(str, Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PERMISSION_VIOLATION = "PERMISSION_VIOLATION"


class AgentExecution(StrictModel):
    status: AgentRunStatus
    provider: str
    model: str
    version: str
    summary: str = ""
    exit_code: int | None = None
    tool_activity: list[str] = Field(default_factory=list)


class AgentAdapter(Protocol):
    provider: str

    def execute(self, work_order: AgentWorkOrder, workspace: Path, configuration: dict[str, str]) -> AgentExecution: ...
