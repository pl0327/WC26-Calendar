# World Cup 2026 Calendar

A calendar generator for FIFA World Cup 2026 matches. It fetches fixture data from the FIFA API, builds a JSON database, and publishes an ICS calendar file suitable for subscription.

Match data is sourced from [FIFA Matches](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures).

## Overview

Subscribe to get all **104 World Cup 2026 matches** in your calendar. Knockout-round opponents (e.g. `W74`, `W75`) update automatically after each match once results are confirmed.

**Subscription URL** (copy this):

```
https://cdn.jsdelivr.net/gh/pl0327/WC26-Calendar@master/world_cup_2026.ics
```

### How to subscribe

**Mac (Calendar app)**

1. Open **Calendar** → **File** → **New Calendar Subscription…**
2. Paste the URL above and click **Subscribe**
3. Choose a name (e.g. *World Cup 2026*), then **OK**

**iPhone / iPad**

1. Open **Settings** → **Calendar** → **Accounts** → **Add Account** → **Other**
2. Tap **Add Subscribed Calendar**
3. Paste the URL above and tap **Next**, then **Save**

**Other calendar apps**

Look for *Subscribe to calendar*, *From URL*, or *webcal* and paste the same URL. Use the `https://` link above — it works with Apple Calendar, Google Calendar, Outlook, and most other apps.

The calendar is read-only and refreshes periodically. During the tournament, match names and knockout opponents update on their own.

## Features

- **104 matches** across all stages: Group stage, Round of 32, Round of 16, Quarter-finals, Semi-finals, Third-place play-off, and Final
- **JSON database** (`data/matches.json`) with structured match metadata
- **ICS calendar** (`world_cup_2026.ics`) for calendar apps
- **Auto-updating knockout opponents** — after each match, downstream slots (e.g. `W74`, `W75`) are resolved to actual team names once FIFA publishes results
- **GitHub Actions** — hourly checks during the tournament, committing updates automatically
- **GitHub Pages** — hosts the ICS at a public URL for calendar subscription

## Repository layout

```
├── src/
│   └── generate_calendar.py   # Fetch FIFA data and generate outputs
├── data/
│   └── matches.json           # JSON match database
├── docs/
│   └── world_cup_2026.ics     # ICS copy for GitHub Pages
├── world_cup_2026.ics         # ICS calendar (repo root)
└── .github/workflows/
    └── update-calendar.yml    # Scheduled auto-update workflow
```

## Requirements

- Python 3.9+ (uses standard library only — no pip dependencies)

## Usage

### Generate or refresh the calendar

```bash
python src/generate_calendar.py --force
```

This fetches the latest data from FIFA and writes:

- `data/matches.json`
- `world_cup_2026.ics`
- `docs/world_cup_2026.ics`

### Smart update (used by GitHub Actions)

```bash
python src/generate_calendar.py --auto
```

`--auto` only fetches when:

1. At least one match is past kick-off **plus 4 hours** (time for results to be confirmed), and
2. FIFA data has actually changed (e.g. a knockout opponent updated from `W75` to a team name)

Before the tournament starts, `--auto` skips the FIFA fetch entirely.

## Event format

Each calendar event looks like:

```
SUMMARY: R32 - South Africa vs Canada (M73)
LOCATION: Los Angeles Stadium (Los Angeles)
```

Match categories: `GROUP`, `R32`, `R16`, `QF`, `SF`, `3RD`, `FINAL`.

For knockout rounds, opponents not yet decided are shown as placeholders (e.g. `W74`, `W75`). These are updated automatically once the feeding match result is available.

Each event includes links to the FIFA match page and the scores & fixtures page.

## GitHub setup

### 1. Enable GitHub Pages

GitHub Pages serves the ICS file from the `docs/` folder so it is available at a stable public URL.

1. Open the repo on GitHub → **Settings** → **Pages**
2. Under **Build and deployment** → **Source**, choose **Deploy from a branch**
3. Set **Branch** to `master` and **Folder** to `/docs`
4. Save

After the first deployment, the calendar is available at:

```
https://pl0327.github.io/WC26-Calendar/world_cup_2026.ics
```

Use the same URL with a `webcal://` prefix if your calendar app expects a subscription link.

### 2. Enable GitHub Actions

The auto-update workflow lives at `.github/workflows/update-calendar.yml`. GitHub Actions is enabled by default on most repos. To confirm:

1. Go to **Settings** → **Actions** → **General**
2. Allow actions to run (e.g. **Allow all actions and reusable workflows**)
3. Under **Workflow permissions**, choose **Read and write permissions** so the workflow can commit updated files

### 3. Initial calendar publish

Generate the calendar locally and push, or run the workflow once from GitHub:

```bash
python src/generate_calendar.py --force
git add data/matches.json world_cup_2026.ics docs/world_cup_2026.ics
git commit -m "Publish World Cup 2026 calendar"
git push
```

Alternatively: **Actions** → **Update World Cup Calendar** → **Run workflow** (requires `data/matches.json` to already exist in the repo for `--auto` to compare changes; use a local `--force` run for the first publish).

## Auto-update workflow

The [Update World Cup Calendar](.github/workflows/update-calendar.yml) workflow:

- Runs **every hour** on a cron schedule
- Can also be triggered manually via **Actions → Update World Cup Calendar → Run workflow**
- Runs `python src/generate_calendar.py --auto`
- Commits and pushes only when match data or the ICS file has changed

The 4-hour delay after kick-off gives FIFA time to publish final results before downstream knockout opponents are updated.

## Data source

Match data is fetched from:

```
https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=285023
```

Stable UIDs (`fifa-wc26-match-{N}@worldcup-calendar`) ensure that updated events merge correctly in subscribed calendars instead of creating duplicates.
