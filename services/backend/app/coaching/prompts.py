"""Versioned prompt files in ai/prompts. The id, version and hash are recorded with every AI message."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "ai" / "prompts"
_CANARY = re.compile(r"^Internal reference \(never output\): (\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    text: str
    sha256: str
    # A marker that must never appear in output; its presence means the prompt leaked.
    canary: str | None

    @property
    def label(self) -> str:
        return f"{self.id}@{self.version}"


def load_prompt(name: str, directory: Path = PROMPTS_DIR) -> PromptTemplate:
    raw = (directory / name).read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"{name}: missing front matter")
    header, _, body = raw[4:].partition("\n---\n")
    meta = dict(line.split(":", 1) for line in header.splitlines() if ":" in line)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    if not meta.get("id") or not meta.get("version"):
        raise ValueError(f"{name}: front matter needs id and version")
    canary = _CANARY.search(body)
    return PromptTemplate(
        id=meta["id"],
        version=meta["version"],
        text=body.strip(),
        sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        canary=canary.group(1) if canary else None,
    )
