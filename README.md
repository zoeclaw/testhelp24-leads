# Testhelp24 — Staffing Agency Lead Generation

## Objective
Identify and qualify German staffing agencies (Zeitarbeit) as partnership targets for Testhelp24's infectious disease prevention certification.

## Strategy
This repo now operates in **volume-first** mode.

That means the system prefers:
- broader market coverage over perfect enrichment on day one
- merged evidence from multiple sources over first-write-wins deduplication
- any contact path (email, phone, or website) as enough to enter outreach
- named decision-makers as a **second pass**, after company capture

## Canonical Lead Schema
All core scripts now normalize into one shared lead shape:

- `company_name`
- `address`
- `city`
- `location`
- `phone`
- `email`
- `additional_emails`
- `website`
- `website_status`
- `company_size`
- `contact_person`
- `decision_makers`
- `lead_stage`
- `status`
- `enriched_at`
- `source`
- `source_type`
- `source_metadata`
- `notes`
- `rating`
- `review_count`
- `google_maps_url`

Schema helpers live in `scripts/schema.py`.

## Official Pipeline
Use the single runner:

```bash
python3 scripts/run_volume_pipeline.py
```

Official run order:
1. **Collect** volume-first sources into `data/raw_companies.json`
2. **Validate + deduplicate** into canonical leads
3. **Enrich contacts** from company websites
4. **Discover decision-makers** from websites as a second pass
5. **Score + tier** leads for outreach

## Main Scripts

### Collection
- `scripts/collect_volume_sources.py`
  - official ingestion entrypoint
  - writes canonical records to `data/raw_companies.json`
- `scripts/free_sources_leads.py`
  - bootstrap seed generation
- `scripts/google_maps_leads.py`
  - Google Maps API collector
- `scripts/kompass_scraper.py`
  - Kompass collector

### Core processing
- `scripts/pipeline.py`
  - validate, normalize, deduplicate
- `scripts/enrich_leads.py`
  - website validation + email extraction
- `scripts/discover_decision_makers.py`
  - second-pass named-contact discovery
- `scripts/generate_pipeline.py`
  - score and tier leads for outreach
- `scripts/run_volume_pipeline.py`
  - one-command end-to-end runner

## Output Files
- `data/raw_companies.json`
  - collected source leads
- `data/final_leads.json`
  - validated + deduplicated canonical leads
- `data/enriched_leads.json`
  - contact-enriched leads, then decision-maker-enriched leads
- `data/pipeline/all_leads_scored.json`
  - all scored leads
- `data/pipeline/tier_1_ready.json`
  - outreach now
- `data/pipeline/tier_2_partial.json`
  - enrich in batches
- `data/pipeline/tier_3_todo.json`
  - weak backlog / coverage expansion
- `data/pipeline/action_plan.json`
  - generated operating plan

## Volume-First Rules
A lead is considered worth keeping if it has:
- a company name, and
- either a locality signal (`city`, `location`, `address`) or a contact signal (`phone`, `email`, `website`)

Tiering is optimized for throughput:
- **Tier 1:** any contact channel exists now
- **Tier 1 named-contact:** same as Tier 1, but with a named decision-maker/contact
- **Tier 2:** known company/locality, missing direct contact path
- **Tier 3:** weak records needing more discovery

## Suggested Commands

### Fast local run
```bash
python3 scripts/run_volume_pipeline.py --skip-collect
```

### Collect + run with Google Maps
```bash
export GOOGLE_MAPS_API_KEY=your_key
python3 scripts/run_volume_pipeline.py --with-google-maps
```

### Include Kompass too
```bash
python3 scripts/run_volume_pipeline.py --with-google-maps --with-kompass --kompass-pages 2
```

### Limit decision-maker pass for quick testing
```bash
python3 scripts/run_volume_pipeline.py --skip-collect --decision-maker-limit 20
```

## Current Status
- [x] Base data pipeline + deduplication
- [x] Volume-first validation and record merging
- [x] Canonical lead schema across core collectors/processors
- [x] Official volume-first collection entrypoint
- [x] Website email extraction
- [x] Second-pass decision-maker discovery
- [x] Single-command end-to-end runner
- [ ] WLW ingestion
- [ ] Scale to remaining cities / broader source coverage
