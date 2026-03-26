"""
Proper MCP Protocol Client
Implements full initialization handshake + tool discovery
"""
import subprocess
import json
import sys
import os
import time
from typing import Optional, List, Dict
from utils import log_progress, log_error

BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"


class MCPProtocolClient:
    """
    Full MCP protocol implementation with handshake
    Follows Model Context Protocol spec v1.0
    """
    
    def __init__(self, command: str, env: dict = None):
        self.command = command
        self.env = env or {}
        self.process = None
        self.started = False
        self.message_id = 0
        self.tools = {}
    
    def start(self) -> bool:
        """Start MCP server and perform initialization handshake"""
        try:
            log_progress("Starting MCP server...")
            
            # Prepare environment
            full_env = os.environ.copy()
            full_env.update(self.env)
            
            # Spawn process
            self.process = subprocess.Popen(
                self.command if isinstance(self.command, list) else [self.command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=full_env,
                bufsize=1,
            )
            
            log_progress(f"✓ MCP server started (PID: {self.process.pid})")
            
            # Perform MCP initialization handshake
            if not self._initialize():
                return False
            
            self.started = True
            return True
        
        except Exception as e:
            log_error(f"Failed to start MCP server", source="mcp_client", exception=e)
            return False
    
    def _send_request(self, method: str, params: dict = None) -> Optional[dict]:
        """Send JSON-RPC request to MCP server"""
        try:
            self.message_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": method,
            }
            if params:
                request["params"] = params
            
            json_str = json.dumps(request) + "\n"
            self.process.stdin.write(json_str)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                return response
            
            return None
        
        except Exception as e:
            log_error(f"Failed to send request {method}", source="mcp_client", exception=e)
            return None
    
    def _send_notification(self, method: str, params: dict = None):
        """Send JSON-RPC notification (no response expected)"""
        try:
            notification = {
                "jsonrpc": "2.0",
                "method": method,
            }
            if params:
                notification["params"] = params
            
            json_str = json.dumps(notification) + "\n"
            self.process.stdin.write(json_str)
            self.process.stdin.flush()
        
        except Exception as e:
            log_error(f"Failed to send notification {method}", source="mcp_client", exception=e)
    
    def _initialize(self) -> bool:
        """Perform MCP initialize handshake"""
        log_progress("Initializing MCP connection...")
        
        # Step 1: Send initialize request
        init_request = {
            "clientInfo": {
                "name": "testhelp24-scraper",
                "version": "1.0.0",
            },
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "sampling": {},
                "roots": {
                    "listChanged": False,
                }
            }
        }
        
        response = self._send_request("initialize", init_request)
        
        if not response:
            log_error("No response to initialize", source="mcp_client")
            return False
        
        if "error" in response:
            log_error(f"Initialize error: {response['error']}", source="mcp_client")
            return False
        
        if "result" not in response:
            log_error(f"Invalid initialize response: {response}", source="mcp_client")
            return False
        
        result = response["result"]
        log_progress(f"✓ Server initialized: {result.get('serverInfo', {}).get('name', 'Unknown')}")
        
        # Store server info
        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})
        
        # Step 2: Send initialized notification
        log_progress("Sending initialized notification...")
        self._send_notification("initialized", {})
        
        # Step 3: List available tools
        log_progress("Discovering available tools...")
        if not self._list_tools():
            log_progress("⚠ Tool discovery failed, continuing anyway")
        
        return True
    
    def _list_tools(self) -> bool:
        """Get list of available tools from server"""
        try:
            response = self._send_request("tools/list", {})
            
            if not response or "result" not in response:
                return False
            
            tools = response["result"].get("tools", [])
            log_progress(f"Found {len(tools)} tools")
            
            for tool in tools[:5]:  # Show first 5
                log_progress(f"  - {tool.get('name')}")
                self.tools[tool.get('name')] = tool
            
            if len(tools) > 5:
                log_progress(f"  ... and {len(tools) - 5} more")
            
            return True
        
        except Exception as e:
            log_error(f"Tool discovery failed", source="mcp_client", exception=e)
            return False
    
    def call_tool(self, tool_name: str, **kwargs) -> Optional[dict]:
        """Call a tool via MCP"""
        if not self.started:
            log_error("MCP client not initialized", source="mcp_client")
            return None
        
        try:
            log_progress(f"Calling tool: {tool_name}")
            
            response = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": kwargs,
            })
            
            if not response:
                log_error(f"No response from tool call", source="mcp_client")
                return None
            
            if "error" in response:
                log_error(f"Tool error: {response['error']}", source="mcp_client")
                return None
            
            if "result" not in response:
                log_error(f"Invalid tool response: {response}", source="mcp_client")
                return None
            
            result = response["result"]
            log_progress(f"✓ Tool returned result (type: {type(result).__name__})")
            return result
        
        except Exception as e:
            log_error(f"Failed to call tool {tool_name}", source="mcp_client", exception=e)
            return None
    
    def stop(self):
        """Stop MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                log_progress("✓ MCP server stopped")
            except:
                self.process.kill()
                log_progress("✓ MCP server killed")
            self.started = False


def test_mcp_protocol():
    """Test MCP protocol with Brightdata"""
    
    client = MCPProtocolClient(
        ["npx", "@brightdata/mcp"],
        env={
            "API_TOKEN": BRIGHTDATA_TOKEN,
            "GROUPS": "advanced_scraping",
        }
    )
    
    if not client.start():
        log_progress("✗ Failed to initialize MCP")
        return
    
    try:
        # Test scraping
        log_progress("\n" + "="*60)
        log_progress("Testing scrape_as_markdown tool")
        log_progress("="*60)
        
        result = client.call_tool(
            "scrape_as_markdown",
            url="https://de.kompass.com/de/search?q=Zeitarbeit+Berlin&page=1"
        )
        
        if result:
            if isinstance(result, list):
                # Could be array of results
                log_progress(f"✓ Got {len(result)} results")
                if result and isinstance(result[0], dict):
                    first = result[0]
                    log_progress(f"  First result keys: {list(first.keys())}")
            elif isinstance(result, dict):
                log_progress(f"✓ Got dict with keys: {list(result.keys())}")
                # Show content sample
                for key in ["markdown", "content", "html"]:
                    if key in result:
                        content = result[key]
                        log_progress(f"  {key}: {len(str(content))} chars")
                        break
            else:
                log_progress(f"✓ Got result: {str(result)[:200]}")
        else:
            log_progress("✗ Tool call failed")
    
    finally:
        client.stop()


if __name__ == "__main__":
    test_mcp_protocol()
