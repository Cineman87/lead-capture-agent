"""
Context compression for the Hermes AI agent.

When the running token estimate crosses `threshold` of `context_limit`,
HermesContextManager:
  1. Calls Claude to produce a structured markdown summary of the conversation
     and all job logs (model-engine events + Hermes self-logs).
  2. Writes the summary as a timestamped note to the configured Obsidian vault.
  3. Resets the conversation to a two-turn resumption stub so work continues
     without exceeding the model's context window.

Usage:
    from hermes import HermesContextManager

    ctx = HermesContextManager(vault_path="/path/to/vault/Hermes Sessions")

    # Conversation turns
    ctx.add_message("user", "What leads came in today?")
    ctx.add_message("assistant", "Three leads arrived: ...")

    # Job logs (call these whenever Hermes or its engine emits data)
    ctx.log_model_engine({"tokens_used": 1820, "latency_ms": 340, "model": "claude-sonnet-4-6"})
    ctx.log_self({"task": "lead_analysis", "status": "complete", "leads_found": 3})

    # Compression is automatic on add_message; or force it:
    note_path = ctx.compress()
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

logger = logging.getLogger("hermes.context")

_CHARS_PER_TOKEN = 4  # rough estimate used only for threshold checks


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _log_entry(source: str, data: Any) -> dict:
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "data": data,
    }


def _estimate_tokens(messages: list, logs: list) -> int:
    raw = (
        json.dumps(messages, ensure_ascii=False)
        + json.dumps(logs, ensure_ascii=False)
    )
    return len(raw) // _CHARS_PER_TOKEN


def _extract_section(markdown: str, heading: str) -> str:
    """Return the body of the first section whose heading contains *heading*."""
    lines = markdown.splitlines()
    collecting, out = False, []
    for line in lines:
        if not collecting and heading.lower() in line.lower() and line.startswith("#"):
            collecting = True
            continue
        if collecting:
            if line.startswith("#"):
                break
            out.append(line)
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class HermesContextManager:
    """
    Manages conversation history and job logs for the Hermes agent.

    Parameters
    ----------
    vault_path:
        Directory inside the Obsidian vault where compression notes are saved.
        Created automatically if it does not exist.
    context_limit:
        Approximate token ceiling for the model being used (default 200 000,
        suitable for claude-sonnet-4-6 / claude-opus-4-8).
    threshold:
        Fraction of context_limit at which auto-compression fires (default 0.80).
    api_key:
        Anthropic API key.  Falls back to the ANTHROPIC_API_KEY env var.
    summary_model:
        Claude model used to generate compression summaries.
    """

    _SUMMARY_MODEL = "claude-sonnet-4-6"
    _SUMMARY_MAX_TOKENS = 4096

    def __init__(
        self,
        vault_path: str,
        context_limit: int = 200_000,
        threshold: float = 0.80,
        api_key: str | None = None,
        summary_model: str | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.context_limit = context_limit
        self.threshold = threshold
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        if summary_model:
            self._SUMMARY_MODEL = summary_model

        self.messages: list[dict] = []
        self.job_logs: list[dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.compression_count = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str) -> bool:
        """
        Append a conversation turn (role: 'user' | 'assistant').
        Returns True if auto-compression was triggered.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")

        self.messages.append(_msg(role, content))

        if self._over_threshold():
            logger.info(
                "Token estimate %d/%d — triggering compression.",
                self.token_estimate,
                self.context_limit,
            )
            self.compress()
            return True
        return False

    def log_model_engine(self, data: Any) -> None:
        """
        Record a log entry from the underlying model engine.

        Typical data: token counts, latency, model name, tool calls,
        finish reason, API response metadata.
        """
        self.job_logs.append(_log_entry("model_engine", data))

    def log_self(self, data: Any) -> None:
        """
        Record a log entry from Hermes itself.

        Typical data: task status, decisions, errors, state changes,
        file paths written, external API results.
        """
        self.job_logs.append(_log_entry("hermes", data))

    def compress(self) -> Path:
        """
        Force a compression cycle immediately, regardless of current size.
        Useful at natural session boundaries or before a known context spike.

        Returns the Path of the Obsidian note that was written.
        """
        if not self.messages and not self.job_logs:
            raise RuntimeError("Nothing to compress — messages and job_logs are both empty.")

        self.compression_count += 1
        logger.info("Compression #%d starting (session %s).", self.compression_count, self.session_id)

        summary_md = self._generate_summary()
        note_path = self._write_obsidian_note(summary_md)
        self._reset_context(summary_md)

        logger.info("Compression #%d complete → %s", self.compression_count, note_path)
        return note_path

    @property
    def token_estimate(self) -> int:
        """Rough estimate of current context size in tokens."""
        return _estimate_tokens(self.messages, self.job_logs)

    # ------------------------------------------------------------------
    # Internal: summarisation
    # ------------------------------------------------------------------

    def _over_threshold(self) -> bool:
        return self.token_estimate >= int(self.context_limit * self.threshold)

    def _generate_summary(self) -> str:
        prompt = self._build_prompt()
        response = self._client.messages.create(
            model=self._SUMMARY_MODEL,
            max_tokens=self._SUMMARY_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _build_prompt(self) -> str:
        convo_lines = "\n".join(
            f"[{m['role'].upper()}]: {m['content']}" for m in self.messages
        ) or "(no conversation recorded)"

        log_lines = (
            "\n".join(
                f"[{e['ts']}] [{e['source'].upper()}] {json.dumps(e['data'], ensure_ascii=False)}"
                for e in self.job_logs
            )
            or "(no job logs recorded)"
        )

        return f"""\
You are the memory compression module for Hermes, an AI agent that captures \
and analyses leads.  Your job is to distil the session below into a concise \
markdown document that Hermes can read at the start of its next session to \
resume without losing any critical context.

=== CONVERSATION ===
{convo_lines}

=== JOB LOGS (model engine + Hermes self-logs) ===
{log_lines}

Output ONLY the markdown document — no code fences, no preamble.
Use exactly these section headings (keep the ## prefix):

## Session Overview
Two or three sentences describing what this session accomplished.

## Key Points
Bullet list of the most important facts, values, file paths, names, or IDs \
that must survive into the next session.

## Decisions Made
Bullet list of every significant decision and its rationale.

## Job Log Summary
Bullet list of notable model-engine events (token spikes, errors, latency), \
Hermes state changes, and any anomalies worth flagging.

## Next Actions
Numbered list of pending tasks in priority order.

## Resumption Context
One paragraph (3–5 sentences) that Hermes can use verbatim as a system \
message stub to orient itself at the start of the next session.
"""

    # ------------------------------------------------------------------
    # Internal: Obsidian note writing
    # ------------------------------------------------------------------

    def _write_obsidian_note(self, summary_md: str) -> Path:
        self.vault_path.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"hermes-{self.session_id}-c{self.compression_count:02d}-{ts}.md"
        note_path = self.vault_path / filename

        frontmatter = (
            "---\n"
            f"created: {datetime.now().isoformat(timespec='seconds')}\n"
            "agent: hermes\n"
            "type: context-compression\n"
            f"session: {self.session_id}\n"
            f"compression: {self.compression_count}\n"
            f"messages_archived: {len(self.messages)}\n"
            f"job_logs_archived: {len(self.job_logs)}\n"
            "---\n\n"
        )

        note_path.write_text(frontmatter + summary_md, encoding="utf-8")
        return note_path

    # ------------------------------------------------------------------
    # Internal: context reset
    # ------------------------------------------------------------------

    def _reset_context(self, summary_md: str) -> None:
        """Replace the full history with a minimal two-turn resumption stub."""
        resumption = _extract_section(summary_md, "Resumption Context")
        if not resumption:
            # Fallback: first 600 chars of the whole summary
            resumption = summary_md[:600]

        self.messages = [
            _msg(
                "user",
                f"[CONTEXT RESTORED — compression #{self.compression_count}, "
                f"session {self.session_id}]\n\n{resumption}",
            ),
            _msg("assistant", "Context restored. Continuing from where we left off."),
        ]
        self.job_logs = []
