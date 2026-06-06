"""Obsidian-saving context engine plugin for Hermes.

Wraps the built-in ContextCompressor and saves a markdown note to an
Obsidian vault every time compression fires.

Install
-------
Copy (or symlink) this directory into Hermes's plugin tree:

    cp -r ~/lead-capture-agent/hermes_obsidian_plugin \
          ~/.hermes/hermes-agent/plugins/context_engine/obsidian_compressor

Activate in ~/.hermes/cli-config.yaml:

    context:
      engine: obsidian_compressor

Configure vault path (pick one):
    - Set env var:  export OBSIDIAN_VAULT_PATH="/path/to/vault/Hermes Sessions"
    - Or add to cli-config.yaml:
        obsidian:
          vault_path: /path/to/vault/Hermes Sessions
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_VAULT_PATH = os.path.expanduser("~/Documents/Obsidian/Hermes Sessions")


class ObsidianContextCompressor:
    """ContextCompressor that also saves each summary to an Obsidian vault.

    Inherits from ContextCompressor at import time so the plugin stays
    compatible even if Hermes internals move around.
    """

    @property
    def name(self) -> str:
        return "obsidian_compressor"

    def __init__(self, vault_path: str | None = None):
        super().__init__()
        self._vault_path = Path(
            vault_path
            or os.environ.get("OBSIDIAN_VAULT_PATH", _DEFAULT_VAULT_PATH)
        )
        self._compression_count = 0

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int = None,
        focus_topic: str = None,
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        result = super().compress(
            messages,
            current_tokens=current_tokens,
            focus_topic=focus_topic,
            force=force,
        )
        summary = _extract_summary(result)
        if summary:
            self._compression_count += 1
            _save_to_obsidian(
                summary,
                vault_path=self._vault_path,
                compression_count=self._compression_count,
                model=getattr(self, "model", "unknown"),
            )
        return result


def _extract_summary(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Return the plain markdown body of the compression summary, if present."""
    try:
        from agent.context_compressor import SUMMARY_PREFIX, LEGACY_SUMMARY_PREFIX
        prefixes = (SUMMARY_PREFIX, LEGACY_SUMMARY_PREFIX)
    except Exception:
        prefixes = ("[CONTEXT COMPACTION", "[CONTEXT SUMMARY]:")

    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        for prefix in prefixes:
            if content.startswith(prefix):
                return content[len(prefix):].strip()
    return None


def _save_to_obsidian(
    summary: str,
    *,
    vault_path: Path,
    compression_count: int,
    model: str,
) -> None:
    try:
        vault_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        note_path = vault_path / f"hermes-compression-{timestamp}.md"
        frontmatter = (
            f"---\n"
            f"date: {datetime.now().isoformat()}\n"
            f"compression_index: {compression_count}\n"
            f"model: {model}\n"
            f"tags: [hermes, context-compression]\n"
            f"---\n\n"
        )
        note_path.write_text(frontmatter + summary, encoding="utf-8")
        logger.info("Obsidian compression note saved: %s", note_path)
    except Exception as exc:
        logger.warning("Obsidian vault save failed: %s", exc)


def _make_engine_class() -> type:
    """Build ObsidianContextCompressor with ContextCompressor as a real base."""
    from agent.context_compressor import ContextCompressor
    return type(
        "ObsidianContextCompressor",
        (ObsidianContextCompressor, ContextCompressor),
        {},
    )


def register(ctx) -> None:
    Engine = _make_engine_class()
    ctx.register_context_engine(Engine())
