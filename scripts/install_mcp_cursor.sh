#!/usr/bin/env bash

# install_mcp_cursor.sh
# Automatic installation script for OpenProject MCP for Cursor (macOS)
#
# Usage:
#   chmod +x scripts/install_mcp_cursor.sh
#   ./scripts/install_mcp_cursor.sh
#
# This script will:
#   - Ensure a Python virtual environment exists using uv (uv sync)
#   - Prompt for OpenProject URL and API key
#   - Configure ~/.cursor/mcp.json to register the MCP server

set -euo pipefail

echo ">>> Starting OpenProject MCP installation for Cursor..." 

# 1. Determine project root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
echo "📂 Project directory: ${PROJECT_ROOT}"

# 2. Check for uv and set up virtual environment
if ! command -v uv >/dev/null 2>&1; then
  cat <<EOF
❌ The 'uv' tool is not installed or not in your PATH.
   This script relies on uv to create and manage the virtual environment.

   To install uv on macOS (see https://docs.astral.sh/uv/getting-started/):

     curl -LsSf https://astral.sh/uv/install.sh | sh

   After installing, ensure 'uv' is available in your shell, then re-run:

     ${0}
EOF
  exit 1
fi

echo "✅ Found 'uv' – setting up virtual environment with 'uv sync'..."
(
  cd "${PROJECT_ROOT}"
  uv sync
)

VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "❌ Could not find Python executable at ${VENV_PYTHON} after 'uv sync'."
  echo "   Please verify your environment or run 'uv sync' manually, then retry."
  exit 1
fi

echo "✅ Virtual environment ready: ${VENV_PYTHON}"

# 3. Collect OpenProject configuration from user
echo
echo "🔐 Configure OpenProject connection"
read -r -p "Enter OpenProject URL (e.g., https://company.openproject.com): " OPENPROJECT_URL
if [[ -z "${OPENPROJECT_URL}" ]]; then
  echo "❌ URL cannot be empty."
  exit 1
fi

read -r -p "Enter your API Key (My account → Access tokens): " OPENPROJECT_API_KEY
if [[ -z "${OPENPROJECT_API_KEY}" ]]; then
  echo "❌ API Key cannot be empty."
  exit 1
fi

# 4. Prepare Cursor MCP config path
CURSOR_DIR="${HOME}/.cursor"
CONFIG_FILE="${CURSOR_DIR}/mcp.json"

mkdir -p "${CURSOR_DIR}"

# 5. Build/merge MCP configuration
SERVER_NAME="openproject-fastmcp"
SERVER_SCRIPT="${PROJECT_ROOT}/openproject-mcp-fastmcp.py"

if [[ ! -f "${SERVER_SCRIPT}" ]]; then
  echo "❌ Server entry point not found at ${SERVER_SCRIPT}."
  echo "   Make sure you're running this script from a valid OpenProject MCP checkout."
  exit 1
fi

echo
echo "📝 Updating Cursor MCP configuration at ${CONFIG_FILE}"

if command -v jq >/dev/null 2>&1; then
  # Use jq for safe JSON manipulation
  if [[ -f "${CONFIG_FILE}" && -s "${CONFIG_FILE}" ]]; then
    EXISTING_JSON="$(cat "${CONFIG_FILE}")"
  else
    EXISTING_JSON="{}"
  fi

  UPDATED_JSON="$(jq \
    --arg proj "${PROJECT_ROOT}" \
    --arg py "${VENV_PYTHON}" \
    --arg url "${OPENPROJECT_URL}" \
    --arg api_key "${OPENPROJECT_API_KEY}" \
    --arg server "${SERVER_NAME}" \
    '
    .mcpServers = (.mcpServers // {}) |
    .mcpServers[$server] = {
      command: $py,
      args: [$proj + "/openproject-mcp-fastmcp.py"],
      env: {
        PYTHONPATH: $proj,
        OPENPROJECT_URL: $url,
        OPENPROJECT_API_KEY: $api_key
      }
    }
    ' <<< "${EXISTING_JSON}")"

  echo "${UPDATED_JSON}" > "${CONFIG_FILE}"
else
  echo "⚠️ 'jq' is not installed; falling back to basic config handling."
  echo "   Existing MCP servers (if any) in ${CONFIG_FILE} will NOT be merged automatically."

  if [[ -f "${CONFIG_FILE}" && -s "${CONFIG_FILE}" ]]; then
    BACKUP_FILE="${CONFIG_FILE}.$(date +%Y%m%d%H%M%S).bak"
    cp "${CONFIG_FILE}" "${BACKUP_FILE}"
    echo "   Existing config was backed up to: ${BACKUP_FILE}"
  fi

  cat > "${CONFIG_FILE}" <<EOF
{
  "mcpServers": {
    "${SERVER_NAME}": {
      "command": "${VENV_PYTHON}",
      "args": ["${SERVER_SCRIPT}"],
      "env": {
        "PYTHONPATH": "${PROJECT_ROOT}",
        "OPENPROJECT_URL": "${OPENPROJECT_URL}",
        "OPENPROJECT_API_KEY": "${OPENPROJECT_API_KEY}"
      }
    }
  }
}
EOF
fi

echo
echo "✅ INSTALLATION SUCCESSFUL!"
echo "   Updated Cursor MCP config: ${CONFIG_FILE}"
echo
echo "👉 Next steps:"
echo "   - Restart Cursor if it is running."
echo "   - In Cursor settings, verify that the '${SERVER_NAME}' MCP server appears."
echo

