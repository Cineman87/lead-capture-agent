#!/bin/bash
# Installs the Obsidian compression plugin into Hermes and patches config.yaml.

set -e

HERMES_DIR="$HOME/.hermes/hermes-agent"
PLUGIN_SRC="$(cd "$(dirname "$0")/hermes_obsidian_plugin" && pwd)"
PLUGIN_DST="$HERMES_DIR/plugins/context_engine/obsidian_compressor"
CONFIG="$HOME/.hermes/config.yaml"

SOUL_SRC="$(cd "$(dirname "$0")/hermes_vault" && pwd)/SOUL.md"
VAULT_CORE="$HOME/Desktop/Vault/MR Smith's Vault/Core"
SOUL_DST="$VAULT_CORE/SOUL.md"

echo "Installing Obsidian compression plugin..."

# Copy plugin
cp -r "$PLUGIN_SRC" "$PLUGIN_DST"
echo "  Plugin copied to $PLUGIN_DST"

# Copy SOUL.md into vault
if [ -f "$SOUL_SRC" ]; then
    mkdir -p "$VAULT_CORE"
    cp "$SOUL_SRC" "$SOUL_DST"
    echo "  SOUL.md copied to $SOUL_DST"
else
    echo "  WARNING: hermes_vault/SOUL.md not found — skipping."
fi

# Patch config.yaml — add context.engine block if not already present
if grep -q "engine: obsidian_compressor" "$CONFIG" 2>/dev/null; then
    echo "  config.yaml already has obsidian_compressor — skipping."
else
    printf '\ncontext:\n  engine: obsidian_compressor\n' >> "$CONFIG"
    echo "  config.yaml updated with context engine."
fi

# Patch config.yaml — set system_prompt_file to SOUL.md
SOUL_ESCAPED=$(echo "$SOUL_DST" | sed 's/[\/&]/\\&/g')
if grep -q "system_prompt_file:" "$CONFIG" 2>/dev/null; then
    sed -i '' "s|system_prompt_file:.*|system_prompt_file: $SOUL_DST|" "$CONFIG"
    echo "  system_prompt_file updated to $SOUL_DST"
else
    printf '\nagent:\n  system_prompt_file: %s\n' "$SOUL_DST" >> "$CONFIG"
    echo "  system_prompt_file added to config.yaml"
fi

echo ""
echo "Done. Set your vault path if you haven't already:"
echo "  export OBSIDIAN_VAULT_PATH=\"\$HOME/Desktop/Vault/Hermes Sessions\""
echo ""
echo "Then restart Hermes. Compression notes will appear in your vault automatically."
echo "SOUL.md is live at: $SOUL_DST"
