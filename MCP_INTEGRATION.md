# Brightdata MCP Integration Guide

## Overview
Brightdata's Model Context Protocol (MCP) server provides anti-bot bypass and web scraping capabilities. This document outlines how to integrate it with the Testhelp24 lead gen system.

## What We Have

### Brightdata Credentials
- **Token:** `5f30e9a0-5119-4cc7-8c27-b638949d683f`
- **Endpoint (Hosted):** `https://mcp.brightdata.com/mcp?token=YOUR_TOKEN`
- **Package (Local):** `@brightdata/mcp` (npm)
- **Available Groups:** advanced_scraping, browser, business, etc.

### Tools Available
- `scrape_as_markdown` — Extract page as clean markdown
- `scrape_batch` — Batch scrape multiple URLs
- `extract` — AI-assisted data extraction (in advanced_scraping group)
- `search_engine` — Web search with unblocking
- `scraping_browser_*` — Browser automation (requires Pro mode)

## Setup Options

### Option A: Run MCP Server Locally (Recommended)
Best for: Production use, full control, persistent connection

```bash
# Install package
npm install -g @brightdata/mcp

# Run with your token and desired groups
export API_TOKEN="5f30e9a0-5119-4cc7-8c27-b638949d683f"
export GROUPS="advanced_scraping"
export WEB_UNLOCKER_ZONE="testhelp24_unlocker"
export BROWSER_ZONE="testhelp24_browser"

npx @brightdata/mcp
```

Once running, the server listens on stdio and creates zones automatically.

### Option B: Use Hosted HTTP Endpoint
Best for: Quick testing, no setup

Requires proper HTTP/SSE implementation to call tools.

## Python Integration

### Minimal Working Example

```python
import subprocess
import json
from mcp.client import StdioMCPClient

# Start MCP server
process = subprocess.Popen(
    ["npx", "@brightdata/mcp"],
    env={
        "API_TOKEN": "5f30e9a0-5119-4cc7-8c27-b638949d683f",
        "GROUPS": "advanced_scraping"
    }
)

# Connect client
client = StdioMCPClient(process)

# Call tool
result = client.call_tool("scrape_as_markdown", {"url": "https://example.com"})
print(result)
```

## Implementation Path

1. **Phase 1:** Set up MCP server to run as background service
2. **Phase 2:** Create Python MCP client wrapper
3. **Phase 3:** Integrate into Kompass/WLW scrapers
4. **Phase 4:** Test on Berlin, scale to other cities

## Current Blockers

- Kompass: DataDome CAPTCHA protection
- WLW: Geo-blocking / 404 errors
- Brightdata MCP: Needs stdio communication, not simple HTTP

## Next Steps

1. Decide on setup approach (local vs hosted)
2. Install and test MCP server locally
3. Implement proper Python MCP client
4. Test scraping on single city
5. Integrate with data pipeline

## References
- Brightdata MCP GitHub: https://github.com/brightdata/brightdata-mcp
- Documentation: https://docs.brightdata.com/mcp
