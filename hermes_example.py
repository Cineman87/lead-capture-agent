"""
Minimal runnable example of HermesContextManager.

Anthropic cloud:
    export ANTHROPIC_API_KEY=sk-ant-...
    export OBSIDIAN_VAULT_PATH="/path/to/MyVault/Hermes Sessions"
    python hermes_example.py

Local server (Ollama, LM Studio, llama.cpp, etc.):
    export ANTHROPIC_BASE_URL=http://localhost:11434  # or :1234 for LM Studio
    export OBSIDIAN_VAULT_PATH="/path/to/MyVault/Hermes Sessions"
    python hermes_example.py
"""

import os
from hermes import HermesContextManager


def main() -> None:
    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "/tmp/hermes-vault/Sessions")

    # local_model is only needed when talking to a local server;
    # leave as None to use the default Claude model against the Anthropic API.
    local_model = os.environ.get("HERMES_MODEL")

    ctx = HermesContextManager(
        vault_path=vault,
        context_limit=200_000,   # tokens before compression fires
        threshold=0.80,          # fire at 80 % of the limit
        # base_url and summary_model are picked up from env vars automatically;
        # pass them explicitly here if you prefer:
        #   base_url="http://localhost:11434",
        #   summary_model="llama3",
        summary_model=local_model,
    )

    # ----------------------------------------------------------------
    # Simulate a working session
    # ----------------------------------------------------------------
    ctx.add_message("user", "Pull all leads from today and categorise by source.")
    ctx.log_model_engine({"tokens_used": 420, "latency_ms": 310, "model": "claude-sonnet-4-6"})

    ctx.add_message("assistant", "Found 7 leads: 4 from the web form, 2 from email, 1 from referral.")
    ctx.log_self({"task": "lead_fetch", "status": "complete", "count": 7})

    ctx.add_message("user", "Flag the referral lead as high-priority and draft a follow-up email.")
    ctx.log_model_engine({"tokens_used": 880, "latency_ms": 520})
    ctx.log_self({"task": "lead_flag", "lead_id": "REF-001", "priority": "high"})

    ctx.add_message(
        "assistant",
        "Flagged REF-001 as high-priority. Draft email saved to drafts/REF-001-followup.txt.",
    )
    ctx.log_self({"task": "email_draft", "file": "drafts/REF-001-followup.txt", "status": "written"})

    # ----------------------------------------------------------------
    # Force compression at a natural session boundary
    # ----------------------------------------------------------------
    print(f"Token estimate before compression: {ctx.token_estimate}")
    note_path = ctx.compress()
    print(f"Compression note written → {note_path}")
    print(f"Token estimate after  compression: {ctx.token_estimate}")

    # ----------------------------------------------------------------
    # The session continues with a slim context
    # ----------------------------------------------------------------
    ctx.add_message("user", "Good. Now do the same for yesterday's leads.")
    ctx.log_model_engine({"tokens_used": 120, "latency_ms": 200})


if __name__ == "__main__":
    main()
