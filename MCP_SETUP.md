# Brightdata MCP Setup Guide

## Overview
This project uses Brightdata's Model Context Protocol (MCP) server for anti-bot web scraping bypass on Kompass and WLW.

## Components

### 1. MCP Server
- **Location:** Runs via `npx @brightdata/mcp`
- **Token:** `5f30e9a0-5119-4cc7-8c27-b638949d683f`
- **Groups Enabled:** `advanced_scraping` (includes batch scraping and extraction)
- **Startup:** `./start_brightdata_mcp.sh`

### 2. Python Integration
- **File:** `scripts/mcp_integration.py`
- **Purpose:** Provides BrightdataMCPServer class to communicate with MCP server
- **Tools Available:**
  - `scrape_as_markdown(url)` — Extract page content as markdown
  - `scrape_batch(urls)` — Batch scrape multiple URLs
  - `extract(url, schema)` — AI-assisted structured data extraction

### 3. Scrapers
- **Kompass Scraper:** Uses MCP to bypass CAPTCHA
- **WLW Scraper:** Uses MCP to bypass geo-blocks
- **Pipeline:** Deduplicates, validates, and normalizes results

## How It Works

### Setup Phase
1. Start MCP server: `./start_brightdata_mcp.sh`
2. Wait for zones to initialize (~5s)
3. Server listens on stdio for JSON-RPC requests

### Scraping Phase
1. Python scraper sends URL to MCP server
2. MCP server fetches via Brightdata's residential proxies (anti-bot bypass)
3. Returns HTML/markdown content
4. Python parser extracts company data
5. Pipeline deduplicates and validates

### Output
- `data/raw_companies.json` — Raw extracted data
- `data/enriched_companies.json` — Validated and normalized
- `data/final_leads.json` — Clean, deduplicated leads for outreach

## Usage

### Option 1: Run MCP Server Standalone
```bash
cd /home/molt/devspace/testhelp24-leads
./start_brightdata_mcp.sh  # Terminal 1

# In another terminal:
source venv/bin/activate
python3 scripts/scrapers.py  # Runs scraping pipeline
```

### Option 2: Run via Python Script
```bash
python3 scripts/mcp_integration.py
```

## Status
- ✅ MCP server installed globally (`npm install -g @brightdata/mcp`)
- ✅ Python client ready (`mcp_integration.py`)
- ✅ Startup script ready (`start_brightdata_mcp.sh`)
- ⏳ Pending: Full integration with scraping pipeline
- ⏳ Pending: Testing on live Kompass/WLW URLs

## Next Steps
1. Start MCP server
2. Test scraping on Berlin (Kompass + WLW)
3. Integrate into unified scraper
4. Scale to major German cities
5. Output clean lead list for partnership outreach
