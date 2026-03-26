#!/bin/bash
# Start Brightdata MCP server
# Run with: ./start_brightdata_mcp.sh

export API_TOKEN="5f30e9a0-5119-4cc7-8c27-b638949d683f"
export GROUPS="advanced_scraping"
export PRO_MODE="false"

echo "Starting Brightdata MCP server..."
echo "Token: $API_TOKEN"
echo "Groups: $GROUPS"

npx @brightdata/mcp
