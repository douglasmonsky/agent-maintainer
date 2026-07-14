"""Load the portable setup skill bundled with Agent Maintainer."""

from __future__ import annotations

import hashlib
from importlib import metadata, resources
from importlib.resources.abc import Traversable
from typing import Final

from agent_maintainer.skill.models import SkillBundle, SkillFile

SKILL_NAME: Final = "agent-maintainer-setup"
RESOURCE_PATHS: Final = ("SKILL.md", "agents/openai.yaml")


def load_bundle() -> SkillBundle:
    """Return the packaged portable setup skill."""

    root = resources.files("agent_maintainer.skill") / "resources" / SKILL_NAME
    files = tuple(_load_file(root, relative_path) for relative_path in RESOURCE_PATHS)
    return SkillBundle(SKILL_NAME, metadata.version("agent-maintainer"), files)


def _load_file(root: Traversable, relative_path: str) -> SkillFile:
    """Return one UTF-8 resource and its SHA-256 digest."""

    content = root.joinpath(*relative_path.split("/")).read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return SkillFile(relative_path, content, digest)
