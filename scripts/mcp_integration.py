"""
Brightdata MCP Integration
Spawns local MCP server and provides tool access to scrapers
"""
import subprocess
import json
import sys
import time
from typing import Optional, List, Dict
from utils import log_progress, log_error

BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"


class BrightdataMCPServer:
    """
    Manages the Brightdata MCP server process
    """
    
    def __init__(self, token: str):
        self.token = token
        self.process = None
        self.started = False
    
    def start(self) -> bool:
        """
        Start the MCP server
        """
        try:
            log_progress("Starting Brightdata MCP server...")
            
            # Prepare environment
            env = {
                "API_TOKEN": self.token,
                "GROUPS": "advanced_scraping",
                "PRO_MODE": "false",
            }
            
            # Spawn MCP server
            # The server runs as a subprocess and communicates via stdio
            self.process = subprocess.Popen(
                ["npx", "@brightdata/mcp"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, **env},
                bufsize=1,
            )
            
            # Give it time to start
            time.sleep(5)
            
            if self.process.poll() is None:
                log_progress("✓ MCP server started (PID: {})".format(self.process.pid))
                self.started = True
                return True
            else:
                stderr = self.process.stderr.read()
                log_error(f"MCP server failed to start: {stderr}", source="mcp_server")
                return False
        
        except Exception as e:
            log_error(f"Failed to start MCP server", source="mcp_server", exception=e)
            return False
    
    def stop(self):
        """
        Stop the MCP server
        """
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                log_progress("✓ MCP server stopped")
            except:
                self.process.kill()
                log_progress("✓ MCP server killed")
            self.started = False
    
    def call_tool(self, tool_name: str, **kwargs) -> Optional[dict]:
        """
        Call an MCP tool via JSON-RPC
        
        Actual Brightdata MCP tools:
        - scrape_as_markdown(url) -> {"markdown": "..."}
        - scrape_as_html(url) -> {"html": "..."}
        - scrape_batch(urls) -> [{"url": "...", "markdown": "..."}]
        - extract(url, extraction_schema, custom_extraction_prompt) -> {"json": {...}}
        - search_engine(query, ...) -> results
        """
        if not self.started:
            log_error("MCP server not started", source="mcp_server")
            return None
        
        try:
            # Prepare JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "method": tool_name,
                "params": kwargs,
                "id": 1,
            }
            
            # Send to MCP server stdin
            json_str = json.dumps(request) + "\n"
            self.process.stdin.write(json_str)
            self.process.stdin.flush()
            
            # Read response from stdout
            response_line = self.process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    log_error(f"MCP error: {response['error']}", source="mcp_server")
                    return None
            
            return None
        
        except Exception as e:
            log_error(f"Failed to call MCP tool {tool_name}", source="mcp_server", exception=e)
            return None


def scrape_with_mcp(url: str, server: BrightdataMCPServer) -> Optional[str]:
    """
    Scrape a URL using Brightdata MCP scrape_as_markdown tool
    Returns markdown content
    """
    log_progress(f"Scraping (MCP): {url}")
    
    result = server.call_tool("scrape_as_markdown", url=url)
    
    if result:
        # Result structure: {"markdown": "..."}
        return result.get("markdown") or result.get("content") or str(result)
    
    return None


def extract_with_mcp(url: str, extraction_schema: str, server: BrightdataMCPServer) -> Optional[dict]:
    """
    Extract structured data from URL using Brightdata MCP extract tool
    Returns JSON-structured data based on extraction schema
    """
    log_progress(f"Extracting (MCP): {url}")
    
    result = server.call_tool("extract", url=url, extraction_schema=extraction_schema)
    
    if result:
        # Result structure: {"json": {...}} or raw dict
        return result.get("json") or result
    
    return None


if __name__ == "__main__":
    import os
    
    # Test the MCP integration
    server = BrightdataMCPServer(BRIGHTDATA_TOKEN)
    
    if server.start():
        log_progress("Server ready")
        
        # Test scrape
        url = "https://de.kompass.com/de/search?q=Zeitarbeit+Berlin&page=1"
        content = scrape_with_mcp(url, server)
        
        if content:
            log_progress(f"✓ Scraped {len(content)} characters")
        else:
            log_progress("✗ Scrape failed")
        
        server.stop()
    else:
        log_progress("✗ Failed to start MCP server")
