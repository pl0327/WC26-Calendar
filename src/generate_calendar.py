#!/usr/bin/env python3
"""Generate World Cup 2026 calendar JSON database and ICS file from FIFA API."""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
FIFA_API = (
    "https://api.fifa.com/api/v3/calendar/matches"
    "?language=en&count=500&idSeason=285023"
)
SCORES_FIXTURES_URL = (
    "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures"
)
CALENDAR_TITLE = "World Cup 2026"
MATCH_DURATION = timedelta(hours=2)
UPDATE_DELAY = timedelta(hours=4)

STAGE_CATEGORY = {
    "First Stage": "GROUP",
    "Round of 32": "R32",
    "Round of 16": "R16",
    "Quarter-final": "QF",
    "Semi-final": "SF",
    "Play-off for third place": "3RD",
    "Final": "FINAL",
}

STAGE_DESCRIPTION = {
    "First Stage": "Group Stage",
    "Round of 32": "Round of 32",
    "Round of 16": "Round of 16",
    "Quarter-final": "Quarter-final",
    "Semi-final": "Semi-final",
    "Play-off for third place": "3rd Place Play-off",
    "Final": "Final",
}

CITY_TIMEZONE = {
    "Atlanta": "America/New_York",
    "Boston": "America/New_York",
    "Dallas": "America/Chicago",
    "Guadalajara": "America/Mexico_City",
    "Houston": "America/Chicago",
    "Kansas City": "America/Chicago",
    "Los Angeles": "America/Los_Angeles",
    "Mexico City": "America/Mexico_City",
    "Miami": "America/New_York",
    "Monterrey": "America/Monterrey",
    "New Jersey": "America/New_York",
    "Philadelphia": "America/New_York",
    "San Francisco Bay Area": "America/Los_Angeles",
    "Seattle": "America/Los_Angeles",
    "Toronto": "America/Toronto",
    "Vancouver": "America/Vancouver",
}

TRACKED_MATCH_FIELDS = ("home", "away", "summary", "description", "status")


def fetch_matches() -> list[dict]:
    with urllib.request.urlopen(FIFA_API) as response:
        payload = json.load(response)
    return sorted(payload["Results"], key=lambda match: match["MatchNumber"])


def normalize_placeholder(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("RU"):
        return f"L{value[2:]}"
    return value


def opponent_name(team: dict | None, placeholder: str | None) -> str:
    if team and team.get("TeamName"):
        return team["TeamName"][0]["Description"]
    normalized = normalize_placeholder(placeholder)
    return normalized or "TBD"


def parse_local_datetime(local_date: str) -> datetime:
    # FIFA LocalDate is local wall time with a trailing Z suffix.
    return datetime.fromisoformat(local_date.replace("Z", ""))


def match_kickoff_utc(match: dict) -> datetime:
    tz = ZoneInfo(match["timezone"])
    start = parse_local_datetime(match["startLocal"]).replace(tzinfo=tz)
    return start.astimezone(timezone.utc)


def any_match_due_for_update(matches: list[dict], now: datetime) -> bool:
    """True when at least one match is past kick-off plus the update delay."""
    for match in matches:
        if now >= match_kickoff_utc(match) + UPDATE_DELAY:
            return True
    return False


def matches_changed(old_matches: list[dict], new_matches: list[dict]) -> bool:
    old_by_number = {match["matchNumber"]: match for match in old_matches}
    for match in new_matches:
        previous = old_by_number.get(match["matchNumber"])
        if previous is None:
            return True
        for field in TRACKED_MATCH_FIELDS:
            if previous.get(field) != match.get(field):
                return True
    return False


def changed_match_numbers(old_matches: list[dict], new_matches: list[dict]) -> list[int]:
    old_by_number = {match["matchNumber"]: match for match in old_matches}
    changed: list[int] = []
    for match in new_matches:
        previous = old_by_number.get(match["matchNumber"])
        if previous is None:
            changed.append(match["matchNumber"])
            continue
        for field in TRACKED_MATCH_FIELDS:
            if previous.get(field) != match.get(field):
                changed.append(match["matchNumber"])
                break
    return changed


def load_existing_matches(json_path: Path) -> list[dict] | None:
    if not json_path.exists():
        return None
    database = json.loads(json_path.read_text())
    return database.get("matches")


def format_ics_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_match_url(stage_id: str, match_id: str) -> str:
    return (
        "https://www.fifa.com/en/match-centre/match/17/285023/"
        f"{stage_id}/{match_id}"
    )


def transform_match(raw: dict) -> dict:
    stage = raw["StageName"][0]["Description"]
    category = STAGE_CATEGORY[stage]
    stage_label = STAGE_DESCRIPTION[stage]
    match_number = raw["MatchNumber"]

    stadium = raw["Stadium"]
    stadium_name = stadium["Name"][0]["Description"]
    city = stadium["CityName"][0]["Description"]
    timezone_id = CITY_TIMEZONE[city]

    home = opponent_name(raw.get("Home"), raw.get("PlaceHolderA"))
    away = opponent_name(raw.get("Away"), raw.get("PlaceHolderB"))

    start_local = parse_local_datetime(raw["LocalDate"])
    end_local = start_local + MATCH_DURATION

    group = None
    if raw.get("GroupName"):
        group = raw["GroupName"][0]["Description"]

    match_url = build_match_url(raw["IdStage"], raw["IdMatch"])
    location = f"{stadium_name} ({city})"
    summary = f"{category} - {home} vs {away} (M{match_number})"
    description = (
        f"FIFA World Cup 2026 Match {match_number}\\n"
        f"{stage_label} - {home} vs {away}\\n\\n"
        f"Scores and fixtures: {SCORES_FIXTURES_URL} \\n\\n"
        f" Match page: {match_url}"
    )

    return {
        "matchNumber": match_number,
        "uid": f"fifa-wc26-match-{match_number}@worldcup-calendar",
        "category": category,
        "stage": stage,
        "stageLabel": stage_label,
        "group": group,
        "home": home,
        "away": away,
        "homePlaceholder": normalize_placeholder(raw.get("PlaceHolderA")),
        "awayPlaceholder": normalize_placeholder(raw.get("PlaceHolderB")),
        "startLocal": start_local.isoformat(),
        "endLocal": end_local.isoformat(),
        "timezone": timezone_id,
        "stadium": stadium_name,
        "city": city,
        "location": location,
        "matchUrl": match_url,
        "fifaMatchId": raw["IdMatch"],
        "fifaStageId": raw["IdStage"],
        "status": "CONFIRMED",
        "summary": summary,
        "description": description.replace("\\n", "\n"),
    }


def build_database(matches: list[dict]) -> dict:
    return {
        "calendarTitle": CALENDAR_TITLE,
        "lastUpdated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": FIFA_API,
        "scoresFixturesUrl": SCORES_FIXTURES_URL,
        "updateDelayHours": int(UPDATE_DELAY.total_seconds() // 3600),
        "matchCount": len(matches),
        "matches": matches,
    }


def build_ics(matches: list[dict], generated_at: datetime) -> str:
    dtstamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    refresh_hours = int(UPDATE_DELAY.total_seconds() // 3600)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//World Cup Calendar//FIFA WC 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CALENDAR_TITLE}",
        f"REFRESH-INTERVAL;VALUE=DURATION:PT{refresh_hours}H",
        f"X-PUBLISHED-TTL:PT{refresh_hours}H",
    ]

    for match in matches:
        start = parse_local_datetime(match["startLocal"])
        end = parse_local_datetime(match["endLocal"])
        description = (
            f"FIFA World Cup 2026 Match {match['matchNumber']}\\n"
            f"{match['stageLabel']} - {match['home']} vs {match['away']}\\n\\n"
            f"Scores and fixtures: {SCORES_FIXTURES_URL} \\n\\n"
            f" Match page: {match['matchUrl']}"
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{match['uid']}",
                f"DTSTAMP:{dtstamp}",
                (
                    f"DTSTART;TZID={match['timezone']}:"
                    f"{format_ics_datetime(start)}"
                ),
                f"DTEND;TZID={match['timezone']}:{format_ics_datetime(end)}",
                f"SUMMARY:{escape_ics_text(match['summary'])}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{escape_ics_text(match['location'])}",
                f"URL:{match['matchUrl']}",
                f"STATUS:{match['status']}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def write_outputs(matches: list[dict], generated_at: datetime) -> tuple[Path, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    database = build_database(matches)
    json_path = DATA_DIR / "matches.json"
    ics_path = ROOT / "world_cup_2026.ics"
    docs_ics_path = DOCS_DIR / "world_cup_2026.ics"

    ics_content = build_ics(matches, generated_at)
    json_path.write_text(json.dumps(database, indent=2, ensure_ascii=False) + "\n")
    ics_path.write_text(ics_content)
    docs_ics_path.write_text(ics_content)
    (DOCS_DIR / ".nojekyll").touch()

    return json_path, ics_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Only fetch and write when a match is past kick-off plus the "
            "update delay, and FIFA data has changed."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Always fetch from FIFA and rewrite outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generated_at = datetime.now(timezone.utc)
    json_path = DATA_DIR / "matches.json"
    existing_matches = load_existing_matches(json_path)

    if args.auto and not args.force:
        if existing_matches is None:
            print("No existing database found; performing initial fetch.")
        elif not any_match_due_for_update(existing_matches, generated_at):
            print(
                "No matches are past kick-off plus "
                f"{int(UPDATE_DELAY.total_seconds() // 3600)} hours yet; skipping update."
            )
            return

    raw_matches = fetch_matches()
    matches = [transform_match(raw) for raw in raw_matches]

    if args.auto and not args.force and existing_matches is not None:
        if not matches_changed(existing_matches, matches):
            print("FIFA data unchanged; no calendar update needed.")
            return
        changed = changed_match_numbers(existing_matches, matches)
        print(f"Updating calendar for changed matches: {changed}")

    write_outputs(matches, generated_at)
    print(f"Wrote {len(matches)} matches to {json_path}")
    print(f"Wrote calendar to {ROOT / 'world_cup_2026.ics'}")
    print(f"Wrote calendar to {DOCS_DIR / 'world_cup_2026.ics'}")


if __name__ == "__main__":
    main()
