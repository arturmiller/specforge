from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .protocol import AgentExecution, AgentRunStatus
from ..v2 import AgentWorkOrder


class CodexAdapter:
    provider = "openai-codex"

    def execute(self, work_order: AgentWorkOrder, workspace: Path, configuration: dict[str, str]) -> AgentExecution:
        command = configuration.get("command", "codex")
        model = configuration.get("model", "configured-default")
        payload = {
            "instruction": "Implement this immutable work order. Read the resolved spec and selected pattern definitions from the listed read-only project paths. Do not modify protected paths.",
            "work_order": work_order.model_dump(mode="json"),
            "resolved_spec": f"generated/{work_order.product['id']}/resolved-spec.json",
            "selected_patterns": work_order.guidance,
        }
        prompt = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        args = [
            command,
            "exec",
            "--json",
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(workspace),
            "-c",
            "sandbox_workspace_write.network_access=false",
        ]
        if "model" in configuration:
            args.extend(["--model", model])
        args.append("-")
        completed = subprocess.run(
            args,
            cwd=workspace,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=int(configuration.get("timeout_seconds", "900")),
            check=False,
        )
        return AgentExecution(
            status=AgentRunStatus.COMPLETED if completed.returncode == 0 else AgentRunStatus.FAILED,
            provider=self.provider,
            model=model,
            version=configuration.get("version", "unknown"),
            summary=completed.stdout[-4000:],
            exit_code=completed.returncode,
            tool_activity=[line for line in completed.stdout.splitlines() if line.strip()][-100:],
        )
