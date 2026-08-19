"""Shared W&B run-tracking helper.

Every phase's script starts its wandb run through here, so the naming
scheme and the required per-run fields (docs/DECISIONS.md D10,
PLAN-DAY-01.md Block 7) can't be silently skipped or reinvented per script.

Naming scheme: {phase}-{model}-{split}-{promptver}-{date}-{githash7}
e.g. eval-qwen3.5-4b-cuaddev-v1-260819-7892478
"""
from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal

import wandb
from pydantic import BaseModel, Field

PROJECT = "legalpsy"
ENTITY = "joshi0494"

Phase = Literal["eval", "base", "sft", "yarn", "grpo", "abl", "quant"]


def _git_sha(short: int = 7) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"--short={short}", "HEAD"], text=True
    ).strip()


def file_sha256(path: str | Path) -> str:
    """Hash a file's exact bytes. Use for prompt_hash / split_manifest_hash
    so they're pinned to real file contents rather than typed by hand."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RunMeta(BaseModel):
    """The fields D10 requires on every run, regardless of phase. Nothing
    here is Optional — a run missing one of these fails to construct."""

    phase: Phase
    model_token: str  # short form used in the run name, e.g. "qwen3.5-4b"
    model_id: str  # real HF id, e.g. "Qwen/Qwen3.5-4B-Base"
    split: str  # e.g. "cuaddev"
    prompt_version: str  # e.g. "v1" — matches configs/prompts/v1.yaml
    prompt_hash: str
    split_manifest_hash: str
    git_sha: str = Field(default_factory=_git_sha)

    def run_name(self) -> str:
        date = datetime.now().strftime("%y%m%d")
        return f"{self.phase}-{self.model_token}-{self.split}-{self.prompt_version}-{date}-{self.git_sha}"

    def tags(self) -> list[str]:
        return [self.phase, self.model_token, self.split, self.prompt_version]


def start_run(meta: RunMeta, extra_config: dict | None = None) -> wandb.Run:
    """Starts a wandb run named and tagged per D10, with `meta` folded into
    the resolved config so model id / prompt hash / split manifest hash /
    git SHA are logged on every run without each script repeating the list.
    """
    config = meta.model_dump()
    if extra_config:
        config.update(extra_config)
    return wandb.init(
        entity=ENTITY,
        project=PROJECT,
        name=meta.run_name(),
        tags=meta.tags(),
        config=config,
    )


def log_table(run: wandb.Run, key: str, rows: list[dict], columns: list[str]) -> None:
    """Logs `rows` as a wandb Table under `key` (e.g. "generations" or
    "metrics") — PLAN.md §9: "log generations, not just scalars." The
    column set is decided per call site; this just does the Table plumbing
    once so every phase logs tables the same way."""
    table = wandb.Table(columns=columns, data=[[row.get(c) for c in columns] for row in rows])
    run.log({key: table})
