#!/usr/bin/env python3
"""
Simple POC test: Create mock data and run pipeline
This validates the infrastructure without hitting Kompass yet
"""
import sys
from pathlib import Path
from utils import log_progress, save_json, RAW_COMPANIES_FILE
from pipeline import run_pipeline

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))


def create_mock_data():
    """Create mock Berlin staffing agencies for POC testing"""
    mock_companies = [
        {
            "company_name": "StaffSolutions Berlin GmbH",
            "address": "Hauptstr. 42",
            "city": "Berlin",
            "phone": "+49 30 123456",
            "email": "",
            "website": "https://staffsolutions-berlin.de",
            "company_size": "50-100",
            "contact_person": "",
            "source": "Mock",
        },
        {
            "company_name": "Berliner Zeitarbeit AG",
            "address": "Kurfürstendamm 100",
            "city": "Berlin",
            "phone": "+49 30 234567",
            "email": "",
            "website": "https://berliner-zeitarbeit.de",
            "company_size": "100-250",
            "contact_person": "",
            "source": "Mock",
        },
        {
            "company_name": "Personal-Service Mitte",
            "address": "Alexanderplatz 1",
            "city": "Berlin",
            "phone": "+49 30 345678",
            "email": "",
            "website": "",
            "company_size": "20-50",
            "contact_person": "",
            "source": "Mock",
        },
        {
            "company_name": "Staff Plus Recruitment",
            "address": "Potsdamer Str. 50",
            "city": "Berlin",
            "phone": "+49 30 456789",
            "email": "",
            "website": "https://staffplus-recruitment.de",
            "company_size": "10-20",
            "contact_person": "",
            "source": "Mock",
        },
        # Duplicate test
        {
            "company_name": "StaffSolutions Berlin GmbH",
            "address": "Hauptstr. 42",
            "city": "Berlin",
            "phone": "+49 30 123456",
            "email": "",
            "website": "https://staffsolutions-berlin.de",
            "company_size": "50-100",
            "contact_person": "",
            "source": "Mock",
        },
    ]
    
    log_progress(f"Creating mock data: {len(mock_companies)} companies (with 1 duplicate)")
    save_json(RAW_COMPANIES_FILE, mock_companies, append=False)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTHELP24 LEAD GEN — POC TEST")
    print("="*60 + "\n")
    
    # Create mock data
    create_mock_data()
    
    # Run pipeline
    print()
    run_pipeline()
