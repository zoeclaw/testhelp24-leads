"""
Inspect Kompass and WLW HTML structure to find correct selectors
"""
from playwright.sync_api import sync_playwright
import time

def inspect_kompass():
    print("\n" + "="*60)
    print("INSPECTING KOMPASS.DE")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://de.kompass.com/de/search?q=Zeitarbeit Berlin&page=1"
        print(f"Loading: {url}")
        
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # Save HTML for inspection
        html = page.content()
        with open("/tmp/kompass.html", "w") as f:
            f.write(html)
        
        # Try to find all divs/articles
        all_divs = page.query_selector_all("div")
        print(f"Total divs: {len(all_divs)}")
        
        # Look for specific patterns
        patterns = [
            ("div[class*='result']", "divs with 'result' in class"),
            ("div[class*='company']", "divs with 'company' in class"),
            ("article", "article tags"),
            ("a[href*='company']", "links with 'company' in href"),
            ("h2, h3, h4", "heading tags"),
        ]
        
        for selector, desc in patterns:
            elements = page.query_selector_all(selector)
            print(f"  {desc}: {len(elements)} found")
            if elements and len(elements) < 5:
                for i, el in enumerate(elements[:3]):
                    text = el.text_content()[:60] if el else ""
                    print(f"    [{i}] {text}")
        
        browser.close()
        print("\nHTML saved to /tmp/kompass.html for inspection")

def inspect_wlw():
    print("\n" + "="*60)
    print("INSPECTING WLW.DE")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://www.wlw.de/de/de/c/branche/50250200"
        print(f"Loading: {url}")
        
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # Save HTML
        html = page.content()
        with open("/tmp/wlw.html", "w") as f:
            f.write(html)
        
        # Look for patterns
        patterns = [
            ("div[class*='result']", "divs with 'result' in class"),
            ("div[class*='company']", "divs with 'company' in class"),
            ("a[href*='company']", "company links"),
            ("li", "list items"),
            ("article", "article tags"),
        ]
        
        for selector, desc in patterns:
            elements = page.query_selector_all(selector)
            print(f"  {desc}: {len(elements)} found")
            if elements and len(elements) < 5:
                for i, el in enumerate(elements[:3]):
                    text = el.text_content()[:60] if el else ""
                    print(f"    [{i}] {text}")
        
        browser.close()
        print("\nHTML saved to /tmp/wlw.html for inspection")

if __name__ == "__main__":
    inspect_kompass()
    inspect_wlw()
    print("\n✓ Inspection complete. Check /tmp/kompass.html and /tmp/wlw.html")
