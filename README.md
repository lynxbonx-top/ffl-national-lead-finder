# FFL National Lead Finder

Streamlit research dashboard for publicly listed Family First Life agency owners, brokers, and agents in all 50 states.

## Features
- Search-engine candidate discovery by state and role (via optional DDGS public search, which can be blocked/rate limited)
- Inspect manually supplied agency/profile URLs and a few same-site about/team/contact pages
- Extract publicly displayed business emails, phone numbers, and explicitly labeled name/role pairs
- Require page evidence of `Family First Life` / `Family 1st Life`, or classify URL-only matches as possible
- CSV import, deduplication, filters, export

## Deploy
1. Create a GitHub repository, and upload the **contents** of this directory to its root.
2. Visit https://share.streamlit.io and select **Create app**.
3. Select repository and branch `main`; entrypoint `app.py`; deploy.
4. Open the deployed URL. Select `All states` or a state and target role, then **Discover public pages**. Inspect candidates; alternatively paste public agency URLs.
5. Download CSV before the session ends. No database is attached.

## Local run
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Limitations
This is not a proprietary contact database, and does not automatically enumerate every FFL agent. Search-engine access may fail or throttle; importing CSVs and URLs works without search. Name/role extraction is conservative; email/phone are **page-level**, not guaranteed to belong to the named individual. State filters apply to data with known state values; automatically scraped pages usually do not reliably identify a state. Human review is necessary. Public website robots.txt restrictions are respected; redirects are not followed. Do not use collected data as evidence of consent to marketing messages.

Sources: https://familyfirstlife.com/agents/ and https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
