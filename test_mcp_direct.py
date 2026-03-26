#!/usr/bin/env python3
"""
Test direct MCP invocation via subprocess
"""
import subprocess
import json
import sys
import os

os.chdir("/home/molt/devspace/testhelp24-leads")

# Set environment
env = os.environ.copy()
env.update({
    "API_TOKEN": "5f30e9a0-5119-4cc7-8c27-b638949d683f",
    "GROUPS": "advanced_scraping",
})

# Try to invoke a single tool call via MCP
test_input = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "scrape_as_markdown",
    "params": {
        "url": "https://de.kompass.com/de/search?q=Zeitarbeit+Berlin&page=1"
    }
}

print(f"Test input: {json.dumps(test_input)}")
print("Sending to MCP server...")

try:
    # Start MCP server and pipe test input
    proc = subprocess.Popen(
        ["npx", "@brightdata/mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    
    # Send request
    stdout, stderr = proc.communicate(
        input=json.dumps(test_input) + "\n",
        timeout=30
    )
    
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    
    if stdout:
        try:
            response = json.loads(stdout)
            print(f"\nParsed response: {json.dumps(response, indent=2)}")
        except:
            pass

except subprocess.TimeoutExpired:
    proc.kill()
    print("Timeout waiting for MCP response")
except Exception as e:
    print(f"Error: {e}")
