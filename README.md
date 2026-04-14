# Testhelp24 — Staffing Agency Lead Generation

## Objective
Identify and qualify German staffing agencies (Zeitarbeit) as partnership targets for Testhelp24's infectious disease prevention certification.

## Status
**POC Phase** — now tuned for a **volume-first** lead generation approach.

That means the pipeline prefers:
- broader coverage over perfect enrichment
- merged duplicate evidence over first-write-wins deduplication
- any contact path (email, phone, or website) as outreach-ready

## Target Data
- Company name
- Address / City
- Phone
- Email
- Website (if available)
- Company size (rough estimate)
- Decision-maker contact (owner/placement manager)

## Sources
1. Kompass (free directory)
2. WLW (free tier with filters)
3. Google Maps API (city-based queries)

## Output
Deduplicated, merged, volume-first JSON leads ready for outreach prioritization.

## Progress
- [x] Build base data pipeline + deduplication
- [x] Add volume-first validation and record merging
- [ ] Kompass scraper (POC: Berlin)
- [ ] WLW scraper (POC: Berlin)
- [ ] Google Maps enrichment
- [x] Email extraction from websites
- [x] Merge & validate
- [ ] Scale to remaining cities

## Current strategy: volume-first

Pipeline behavior now assumes that a lead is useful if we have:
- a company name, and
- either a locality signal (city/address) or a contact signal (phone/email/website)

Tiering is optimized for throughput:
- **Tier 1:** any contact channel exists now
- **Tier 2:** known company/locality, missing direct contact path
- **Tier 3:** weak records needing more discovery
