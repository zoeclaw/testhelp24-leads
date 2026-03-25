# Testhelp24 — Staffing Agency Lead Generation

## Objective
Identify and qualify German staffing agencies (Zeitarbeit) as partnership targets for Testhelp24's infectious disease prevention certification.

## Status
**POC Phase** — Single city, single source validation

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
Deduplicated, validated JSON leads ready for outreach.

## Progress
- [ ] Build data pipeline + deduplication
- [ ] Kompass scraper (POC: Berlin)
- [ ] WLW scraper (POC: Berlin)
- [ ] Google Maps enrichment
- [ ] Email extraction from websites
- [ ] Merge & validate
- [ ] Scale to remaining cities
