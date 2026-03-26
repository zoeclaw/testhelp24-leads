"""
Kompass.de scraper using Playwright (browser-based)
Handles JavaScript rendering and dynamic content
"""
import asyncio
import json
from typing import List, Dict
from playwright.async_api import async_playwright
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


async def scrape_kompass_city(city: str, max_pages: int = 3) -> List[Dict]:
    """Scrape Kompass for staffing agencies using Playwright"""
    companies = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(extra_http_headers=HEADERS)
        page = await context.new_page()
        
        log_progress(f"Starting Playwright scrape for {city}")
        
        try:
            # Try multiple URL formats
            urls_to_try = [
                f"https://www.kompass.de/de/search?q=Zeitarbeit+{city}",
                f"https://de.kompass.com/search?q=Zeitarbeit+{city}",
                f"https://www.kompass.de/search/staffing-agencies/{city}",
            ]
            
            page_content = None
            successful_url = None
            
            for url in urls_to_try:
                try:
                    log_progress(f"Trying: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_load_state("domcontentloaded")
                    
                    page_content = await page.content()
                    successful_url = url
                    log_progress(f"✓ Loaded: {successful_url}")
                    break
                except Exception as e:
                    log_progress(f"  Failed: {str(e)[:100]}")
                    continue
            
            if not page_content:
                log_error(f"Could not load any Kompass URL for {city}", source="kompass_playwright")
                await browser.close()
                return []
            
            # Parse all visible text to find company listings
            # Try to find company name patterns and contact info
            
            # Look for common company listing patterns
            try:
                # Method 1: Find all links that look like company names
                company_links = await page.query_selector_all("a[href*='/de/firma/'], a[href*='/company/']")
                log_progress(f"Found {len(company_links)} potential company links")
                
                for link in company_links[:10]:  # Limit to first 10 for POC
                    try:
                        name = await link.inner_text()
                        href = await link.get_attribute("href")
                        
                        if name and len(name) > 2:
                            # Try to get more info from the listing
                            parent = await link.evaluate("el => el.closest('.company-result, .listing, [data-company])")
                            
                            phone = ""
                            email = ""
                            address = ""
                            
                            if parent:
                                phone_elem = await parent.query_selector("span:has-text('+'), [data-phone]")
                                if phone_elem:
                                    phone = await phone_elem.inner_text()
                            
                            company_data = {
                                "company_name": name.strip(),
                                "address": address,
                                "city": city,
                                "phone": phone,
                                "email": email,
                                "website": href or "",
                                "company_size": "",
                                "contact_person": "",
                                "source": "Kompass-Playwright",
                            }
                            
                            if company_data["company_name"]:
                                companies.append(company_data)
                                log_progress(f"  → {name.strip()}")
                    
                    except Exception as e:
                        log_error(f"Failed to parse company link", source="kompass_playwright", exception=e)
                        continue
                
            except Exception as e:
                log_error(f"Error extracting companies from page", source="kompass_playwright", exception=e)
            
            # Method 2: Extract text content and look for patterns
            if not companies:
                log_progress("Fallback: Extracting text patterns...")
                
                # Get all visible text
                text_content = await page.locator("body").inner_text()
                
                # Look for phone/email patterns (simple extraction)
                import re
                
                phone_pattern = r'\+49\s*\d[\d\s]{9,}'
                email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                
                phones = re.findall(phone_pattern, text_content)
                emails = re.findall(email_pattern, text_content)
                
                log_progress(f"Found {len(phones)} phone numbers, {len(emails)} email addresses")
        
        except Exception as e:
            log_error(f"Fatal error in Playwright scrape", source="kompass_playwright", exception=e)
        
        finally:
            await browser.close()
    
    return companies


async def main():
    """Run scraper for multiple cities"""
    cities = ["Berlin"]  # POC: start with Berlin
    
    all_companies = []
    
    for city in cities:
        companies = await scrape_kompass_city(city, max_pages=2)
        all_companies.extend(companies)
        log_progress(f"✓ Scraped {city}: {len(companies)} companies")
    
    # Save results
    if all_companies:
        save_json(RAW_COMPANIES_FILE, all_companies, append=False)
        log_progress(f"✓ Saved {len(all_companies)} companies to {RAW_COMPANIES_FILE}")
    else:
        log_progress("⚠ No companies found")


if __name__ == "__main__":
    asyncio.run(main())
