# Just Stream It

Analytics site for the "Just Stream It" ESPN fantasy football league (a keeper
league, first season 2025).

## How it works

- `scripts/generate_data.py` pulls league data from ESPN's undocumented
  Fantasy Football API and bakes it into `docs/data/` as static JSON.
- `docs/index.html` is a static site that reads that JSON. No build step.
- A GitHub Actions cron (`.github/workflows/update-data.yml`) runs the pull
  daily and commits any changes, then GitHub Pages serves `docs/`.

## Local setup

The league is private, so ESPN requires the `espn_s2` and `SWID` cookies from
a logged-in browser session. Locally, put them in a gitignored
`secrets.json` at the repo root:

```json
{
  "espn_s2": "...",
  "swid": "{...}"
}
```

(In GitHub Actions these come from the `ESPN_S2` / `ESPN_SWID` repo secrets
instead.)

Then:

```bash
pip install -r requirements.txt
python scripts/generate_data.py
```

This writes `docs/data/meta.json` and, per season, `teams.json`,
`matchups.json`, `rosters.json`, and `draft.json`.

## Adding seasons

Add the year to `SEASONS` in `scripts/config.py`. Bump `CURRENT_SEASON` each
year once the new season opens (this determines which ESPN endpoint shape to
use - current vs. historical).
