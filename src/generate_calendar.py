#!/usr/bin/env python3
"""Generate World Cup 2026 calendar JSON database and ICS file from FIFA API."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIFA_API = (
    "https://api.fifa.com/api/v3/calendar/matches"
    "?language=en&count=500&idSeason=285023"
)
SCORES_FIXTURES_URL = (
    "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures"
)
CALENDAR_TITLE = "World Cup 2026"
MATCH_DURATION = timedelta(hours=2)

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
        "matchCount": len(matches),
        "matches": matches,
    }


def build_ics(matches: list[dict], generated_at: datetime) -> str:
    dtstamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//World Cup Calendar//FIFA WC 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{CALENDAR_TITLE}",
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


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc)

    raw_matches = fetch_matches()
    matches = [transform_match(raw) for raw in raw_matches]
    database = build_database(matches)

    json_path = DATA_DIR / "matches.json"
    ics_path = ROOT / "world_cup_2026.ics"

    json_path.write_text(json.dumps(database, indent=2, ensure_ascii=False) + "\n")
    ics_path.write_text(build_ics(matches, generated_at))

    print(f"Wrote {len(matches)} matches to {json_path}")
    print(f"Wrote calendar to {ics_path}")


if __name__ == "__main__":
    main()
