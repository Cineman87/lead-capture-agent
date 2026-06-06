#!/bin/bash
# Installs the Obsidian compression plugin into Hermes and patches cli-config.yaml.

set -e

HERMES_DIR="$HOME/.hermes/hermes-agent"
PLUGIN_SRC="$(cd "$(dirname "$0")/hermes_obsidian_plugin" && pwd)"
PLUGIN_DST="$HERMES_DIR/plugins/context_engine/obsidian_compressor"
CONFIG="$HOME/.hermes/cli-config.yaml"

echo "Installing Obsidian compression plugin..."

# Copy plugin
cp -r "$PLUGIN_SRC" "$PLUGIN_DST"
echo "  Plugin copied to $PLUGIN_DST"

# Patch cli-config.yaml — add context.engine block if not already present
if grep -q "engine: obsidian_compressor" "$CONFIG" 2>/dev/null; then
    echo "  cli-config.yaml already has obsidian_compressor — skipping."
else
    # Append the context engine block at the end of the file
    printf '\n# Context engine — saves compression summaries to Obsidian\ncontext:\n  engine: obsidian_compressor\n' >> "$CONFIG"
    echo "  cli-config.yaml updated."
fi

echo ""
echo "Done. Set your vault path if you haven't already:"
echo "  export OBSIDIAN_VAULT_PATH=\"/path/to/your/vault/Hermes Sessions\""
echo ""
echo "Then restart Hermes. Compression notes will appear in your vault automatically."
