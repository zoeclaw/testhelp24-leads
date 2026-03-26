"""
Live MCP-based scraper for Kompass and WLW
Now that protocol works, integrate with data pipeline
"""
import json
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from mcp_protocol_client import MCPProtocolClient
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"


def scrape_kompass_via_mcp(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Scrape Kompass using MCP protocol
    """
    companies = []
    
    client = MCPProtocolClient(
        ["npx", "@brightdata/mcp"],
        env={
            "API_TOKEN": BRIGHTDATA_TOKEN,
            "GROUPS": "advanced_scraping",
        }
    )
    
    if not client.start():
        log_error("Failed to start MCP client", source="kompass_mcp")
        return companies
    
    try:
        log_progress(f"Scraping Kompass: {city}")
        
        for page_num in range(1, max_pages + 1):
            try:
                url = f"https://de.kompass.com/de/search?q=Zeitarbeit {city}&page={page_num}"
                
                log_progress(f"  Page {page_num}: {url}")
                
                # Call MCP tool
                result = client.call_tool("scrape_as_markdown", url=url)
                
                if not result:
                    log_progress(f"    Failed to fetch page")
                    break
                
                content = result.get("content") or result.get("markdown") or ""
                
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                else:
                    content = str(content)
                
                if not content or content.strip() == "":
                    log_progress(f"    Empty content")
                    break
                
                # Parse content
                soup = BeautifulSoup(content, "html.parser")
                
                # Look for company listings
                listings = soup.select("div[class*='result'], article, li")
                
                if not listings:
                    log_progress(f"    No listings found")
                    break
                
                log_progress(f"    Found {len(listings)} listing elements")
                
                # Extract company data
                for listing in listings:
                    try:
                        # Get text content
                        text = listing.get_text(strip=True)
                        
                        if not text or len(text) < 10:
                            continue
                        
                        # Look for patterns: company name, phone, address
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        if not lines:
                            continue
                        
                        # First line is usually company name
                        name = lines[0]
                        
                        # Look for phone in text
                        phone = ""
                        phone_match = re.search(r'(\+49|0)[0-9\s\-()]{8,}', text)
                        if phone_match:
                            phone = phone_match.group(0)
                        
                        # Try to extract address
                        address = " ".join(lines[1:3]) if len(lines) > 1 else ""
                        
                        if name and len(name) > 3:
                            company_data = {
                                "company_name": name,
                                "address": address[:100],
                                "city": city,
                                "phone": phone,
                                "email": "",
                                "website": "",
                                "company_size": "",
                                "contact_person": "",
                                "source": "Kompass-MCP",
                            }
                            companies.append(company_data)
                            log_progress(f"    → {name[:60]}")
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                log_error(f"Error on page {page_num}", source="kompass_mcp", exception=e)
                break
    
    finally:
        client.stop()
    
    return companies


def scrape_wlw_via_mcp(city: str) -> List[Dict]:
    """
    Scrape WLW using MCP protocol
    """
    companies = []
    
    client = MCPProtocolClient(
        ["npx", "@brightdata/mcp"],
        env={
            "API_TOKEN": BRIGHTDATA_TOKEN,
            "GROUPS": "advanced_scraping",
        }
    )
    
    if not client.start():
        log_error("Failed to start MCP client", source="wlw_mcp")
        return companies
    
    try:
        log_progress(f"Scraping WLW: {city}")
        
        url = "https://www.wlw.de/de/de/c/branche/50250200"
        
        log_progress(f"  {url}")
        
        result = client.call_tool("scrape_as_markdown", url=url)
        
        if not result:
            log_progress(f"    Failed to fetch")
            return companies
        
        content = result.get("content") or result.get("markdown") or ""
        
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        else:
            content = str(content)
        
        if not content or content.strip() == "":
            log_progress(f"    Empty content")
            return companies
        
        soup = BeautifulSoup(content, "html.parser")
        
        listings = soup.select("div, article, li")
        
        log_progress(f"    Found {len(listings)} elements, extracting...")
        
        for listing in listings:
            try:
                text = listing.get_text(strip=True)
                
                if not text or len(text) < 5 or len(text) > 500:
                    continue
                
                # Filter for company-like entries
                if any(skip in text.lower() for skip in ["javascript", "cookies", "accept", "data"]):
                    continue
                
                # Check if looks like a company name
                lines = text.split('\n')
                name = lines[0].strip() if lines else text[:60]
                
                if name and len(name) > 3 and not name.isupper():
                    company_data = {
                        "company_name": name,
                        "address": "",
                        "city": city,
                        "phone": "",
                        "email": "",
                        "website": "",
                        "company_size": "",
                        "contact_person": "",
                        "source": "WLW-MCP",
                    }
                    companies.append(company_data)
                    log_progress(f"    → {name[:60]}")
            
            except Exception as e:
                continue
    
    finally:
        client.stop()
    
    return companies


def scrape_city(city: str):
    """
    Scrape city via MCP
    """
    log_progress(f"\n{'='*60}")
    log_progress(f"MCP LIVE SCRAPING: {city}")
    log_progress(f"{'='*60}")
    
    kompass_companies = scrape_kompass_via_mcp(city, max_pages=2)
    wlw_companies = scrape_wlw_via_mcp(city)
    
    all_companies = kompass_companies + wlw_companies
    
    if all_companies:
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + all_companies
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        
        log_progress(f"\n✓ Scraping complete:")
        log_progress(f"  Kompass: {len(kompass_companies)} companies")
        log_progress(f"  WLW: {len(wlw_companies)} companies")
        log_progress(f"  Total new: {len(all_companies)}")
        log_progress(f"  Saved to: {RAW_COMPANIES_FILE}")
    else:
        log_progress(f"\n✗ No companies found")


if __name__ == "__main__":
    scrape_city("Berlin")
