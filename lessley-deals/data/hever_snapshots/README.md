# Hever local snapshots

Two Hever sources read from local files here instead of fetching `hvr.co.il`
live — the site requires a logged-in session the scraper doesn't automate,
and both pages already contain everything needed once saved. Nothing in this
directory is committed (see `.gitignore`) since a real export contains the
logged-in member's own name/session data.

Drop these two files here, refreshed periodically by hand:

- **`giftcard.json`** — the raw JSON response from
  `https://www.hvr.co.il/bs2/datasets/giftcard.json` while logged in. Easiest
  way: log into hvr.co.il, open browser devtools → Network tab, visit
  `site/pg/gift_card_company`, find the `giftcard.json` request, and save its
  response body. (Navigating to the URL directly in a logged-in tab and using
  "Save As" also works.) Consumed by `hever_gift_card_company`
  (`scraping/sources/hever.py`) — a plain deterministic adapter, no LLM: every
  field (`company`, `limitations`, etc.) is mapped directly, same as `hot.py`'s
  API adapter.
- **`teamim_card_store.html`** — the full page source of
  `https://www.hvr.co.il/site/pg/teamim_card_store` while logged in
  ("Save Page As → Webpage, HTML only", or view-source and save). Unlike the
  gift-card page, this one is fully server-rendered with every restaurant
  already inline — no separate JSON endpoint exists for it, so it's still
  parsed via the LLM route (`llm:hever-teamim` in `data/seed/llm_sources.json`).

Run `python -m deals scrape --source hever_gift_card_company` /
`--source llm:hever-teamim` (or `--all`) to parse whatever's currently in
this folder.
