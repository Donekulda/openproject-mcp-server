#!/usr/bin/env python3
"""
OpenProject MCP Server - Stdio Transport Entry Point

This is the entry point for stdio transport (Claude Code desktop).
FastMCP-based implementation with automatic tool registration.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""

from src.server import mcp

if __name__ == "__main__":
    # Run with stdio transport (default for Claude Code and Cursor)
    mcp.run(transport="stdio")
