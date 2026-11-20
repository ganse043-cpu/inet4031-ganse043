# Week 11 Data Quality Report

Author and tester: Otto Ganser

| Test | Result |
|---|---|
| Row count | Pass — 12,000 tickets, exceeding the 10,000 minimum |
| Date coverage | Pass — 111.984 days, exceeding the 90-day minimum |
| Categories | Pass — 0 invalid or missing categories |
| Closed tickets | Pass — all 11,982 closed tickets had resolution timestamps |
| Resolution timestamps | Pass — 0 violations |
| Repeatability | Pass — both PostgreSQL exports had identical SHA-256 hashes and 0 duplicate ticket IDs |
