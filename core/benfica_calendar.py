"""Calendar API client for SL Benfica website.

Provides access to Benfica's official calendar API for match data.
Used as the primary source for match information with ESPN as fallback.
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Any

import pendulum
from bs4 import BeautifulSoup
from curl_cffi import requests

from config.constants import CALENDAR_API_URL, CALENDAR_URL, TIMEZONE
from core.retry import retry_on_failure

logger = logging.getLogger(__name__)

# Current Season - FALLBACK ONLY
# The actual season is extracted dynamically from the checked season checkbox
# on the calendar page. This is only used if extraction fails.
# Note: Update this annually if extraction fails
CURRENT_SEASON = "2025/26"

# Calendar API filter constants
# These values are used in the API request payload to filter calendar events

# Rank GUID - FALLBACK ONLY
# The actual rank ID is extracted dynamically from the checked radio button
# on the calendar page. This is only used if extraction fails.
RANK_ID = "16094ecf-9e78-4e3e-bcdf-28e4f765de9f"

# Tournament IDs - FALLBACK ONLY
# The actual tournament IDs are extracted dynamically from checked
# checkboxes on the calendar page. These are only used if extraction fails.
# Format: "dp:tournament:" for Benfica, "sr:tournament:" for SportRadar
TOURNAMENT_IDS = [
    "dp:tournament:50d243c9-fee7-4b34-bdcc-22bf446935eb",  # Eusébio Cup
    "sr:tournament:7",  # UEFA Champions League
    "sr:tournament:238",  # Liga Portugal (Primeira Liga)
    "sr:tournament:357",  # Mundial de Clubes FIFA
    "sr:tournament:345",  # Supertaça Cândido de Oliveira
    "sr:tournament:327",  # Taça da Liga
    "sr:tournament:336",  # Taça de Portugal
]


class Calendar:
    """Client for interacting with SL Benfica calendar API."""

    def __init__(self):
        """Initialize Calendar client and fetch verification token."""
        # Use curl_cffi with Chrome impersonation to bypass bot protection
        self.first_response = requests.get(
            CALENDAR_URL, impersonate="chrome", timeout=30
        )
        self.soup = BeautifulSoup(
            self.first_response.content, features="html.parser"
        )
        token_input = self.soup.find(
            name="input",
            attrs={"name": "__RequestVerificationToken", "type": "hidden"},
        )
        self.request_verification_token = token_input["value"]

        # Store cookies from first request for subsequent API calls
        # curl_cffi will automatically format these cookies for the request
        self.cookies = self.first_response.cookies
        logger.debug("Calendar client initialized")

    def _extract_current_season(self) -> str | None:
        """Extract current season from checked checkbox in calendar page.

        Returns:
            Current season string (e.g., "2025/26") or None if not found.
        """
        # Find the checked season checkbox
        season_checkbox = self.soup.find(
            "input", {"name": "season", "type": "checkbox", "checked": True}
        )
        if season_checkbox:
            season = season_checkbox.get("id")
            if season:
                logger.debug(f"Extracted current season from page: {season}")
                return season

        logger.warning("Failed to extract current season from page")
        return None

    def _extract_rank_id(self) -> str | None:
        """Extract rank ID from checked radio button in calendar page.

        Returns:
            Rank ID (UUID) of the selected team, or None if not found.
        """
        # Find all checked radio buttons
        checked_radios = self.soup.find_all(
            "input", {"type": "radio", "checked": True}
        )

        # Look for one with a team name (not just "radio")
        for radio in checked_radios:
            name_attr = radio.get("name")
            # Skip gender selector (name="radio")
            # Team rank has descriptive name like "Equipa Principal"
            if name_attr and name_attr != "radio":
                rank_id = radio.get("id")
                if rank_id:
                    logger.debug(
                        f"Extracted rank ID: {rank_id} (team: {name_attr})"
                    )
                    return rank_id

        logger.warning("Failed to extract rank ID from page")
        return None

    def _extract_tournament_ids(self) -> list[str]:
        """Extract tournament IDs from checked checkboxes in calendar page.

        Returns:
            List of tournament IDs that are checked by default on the page.
        """
        # Find all checked tournament checkboxes
        tournament_checkboxes = self.soup.find_all(
            "input",
            attrs={"name": "tournament", "type": "checkbox", "checked": True},
        )

        tournament_ids = []
        for checkbox in tournament_checkboxes:
            tid = checkbox.get("id")
            if tid:
                tournament_ids.append(tid)

        logger.debug(
            f"Extracted {len(tournament_ids)} tournament IDs from page"
        )
        return tournament_ids

    def _create_payload(self) -> dict[str, Any]:
        """Create API request payload.

        Extracts season, rank ID, and tournament IDs dynamically from
        calendar page. Falls back to constants if extraction fails.

        Returns:
            Dictionary with filters for calendar API.
        """
        modality = self.soup.find("div", attrs={"class": "modality"})["id"]

        # Try to extract current season from page, fallback to constant
        current_season = self._extract_current_season()
        if not current_season:
            logger.warning(
                "Failed to extract current season, using fallback constant"
            )
            current_season = CURRENT_SEASON

        # Try to extract rank ID from page, fallback to constant
        rank_id = self._extract_rank_id()
        if not rank_id:
            logger.warning(
                "Failed to extract rank ID, using fallback constant"
            )
            rank_id = RANK_ID

        # Try to extract tournament IDs from page, fallback to constants
        tournament_ids = self._extract_tournament_ids()
        if not tournament_ids:
            logger.warning(
                "Failed to extract tournament IDs, using fallback constants"
            )
            tournament_ids = TOURNAMENT_IDS

        payload = {
            "filters": {
                "Menu": "next",
                "Modality": f"{modality}",
                "IsMaleTeam": True,
                "Rank": rank_id,
                "Tournaments": tournament_ids,
                "Seasons": [current_season],
                "PageNumber": 0,
            }
        }
        return payload

    def _create_headers(self) -> dict[str, str]:
        """Create request headers for API call.

        Returns:
            Dictionary with HTTP headers.
        """
        # With curl_cffi impersonation, only need essential headers
        # The browser impersonation handles most headers automatically
        headers = {
            "Referer": "https://www.slbenfica.pt/pt-pt/futebol/calendario",
            "Content-Type": "application/json",
            "__RequestVerificationToken": self.request_verification_token,
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.slbenfica.pt",
        }
        return headers

    @retry_on_failure(
        max_attempts=3,
        delay=1.0,
        exceptions=(requests.RequestsError, TimeoutError),
    )
    def get_events(self) -> list[dict[str, Any]]:
        """Fetch calendar events from API.

        Returns:
            List of event dictionaries with match data.

        Raises:
            requests.HTTPError: If API request fails.
        """
        headers = self._create_headers()
        payload = self._create_payload()
        logger.debug("Fetching calendar events from API")

        # Use curl_cffi with Chrome impersonation and cookies
        response = requests.post(
            CALENDAR_API_URL,
            headers=headers,
            json=payload,
            cookies=self.cookies,
            impersonate="chrome",
            timeout=30,
            allow_redirects=True,
        )
        response.raise_for_status()
        logger.info(
            f"Calendar events fetched successfully. "
            f"Status: {response.status_code}, "
            f"Content-Length: {len(response.text)} bytes"
        )

        # Parse HTML response (API returns HTML fragments, not JSON)
        calendar_soup = BeautifulSoup(response.text, "html.parser")
        calendar_items = calendar_soup.find_all("div", class_="calendar-item")
        logger.info(f"Found {len(calendar_items)} calendar items in response")

        # Parse each calendar item into structured data
        events = []
        for item in calendar_items:
            event = self._parse_calendar_item(item)
            if event:
                events.append(event)

        return events

    def _parse_calendar_item(
        self, item: BeautifulSoup
    ) -> dict[str, Any] | None:
        """Parse a calendar item HTML element into structured data.

        Args:
            item: BeautifulSoup element representing a calendar item.

        Returns:
            Dictionary with match data or None if parsing fails.
        """
        try:
            # Extract from hidden calendar export divs
            title_div = item.find("div", class_="titleForCalendar")
            start_date_div = item.find("div", class_="startDateForCalendar")
            location_div = item.find("div", class_="locationForCalendar")

            if not title_div or not start_date_div:
                return None

            # Parse teams from title (format: "Team A vs Team B")
            title = title_div.text.strip()
            if " vs " in title:
                teams = title.split(" vs ")
                home_team = teams[0].strip()
                away_team = teams[1].strip()
                # Determine if Benfica is home or away
                # If Benfica appears in home_team, then Benfica is home
                is_home = "Benfica" in home_team
                # Adversary is whoever is NOT Benfica
                adversary = away_team if is_home else home_team
            else:
                adversary = title
                is_home = None

            # Parse datetime (format: "11/25/2025 5:45:00 PM")
            # The datetime from the website is already in Lisbon time
            datetime_str = start_date_div.text.strip()
            match_dt = datetime.strptime(datetime_str, "%m/%d/%Y %I:%M:%S %p")

            # Create timezone-aware datetime in Lisbon timezone
            match_dt_aware = pendulum.instance(match_dt, tz=TIMEZONE)

            # Competition
            comp_div = item.find("div", class_="calendar-competition")
            competition = comp_div.text.strip() if comp_div else "Unknown"

            # Location
            location = location_div.text.strip() if location_div else "Unknown"

            # TV Channel (from calendar-live-channels div)
            tv_channel = None
            tv_channels_div = item.find("div", class_="calendar-live-channels")
            if tv_channels_div:
                # Channel name is in a hidden <p> tag
                channel_p = tv_channels_div.find("p", attrs={"hidden": ""})
                if channel_p:
                    tv_channel = channel_p.text.strip()

            return {
                "MatchDate": match_dt_aware.to_iso8601_string(),
                "AdversaryName": adversary,
                "StadiumName": location,
                "TournamentName": competition,
                "IsHome": is_home if is_home is not None else True,
                "TvChannel": tv_channel,
            }

        except Exception as e:
            logger.warning(f"Failed to parse calendar item: {e}")
            return None


def _parse_match_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a match event from Benfica API into standardized format.

    Args:
        event: Event dictionary from Benfica API.

    Returns:
        Standardized match data dictionary or None if not a valid match.
    """
    try:
        # Extract match details
        match_date_str = event.get("MatchDate")
        adversary = event.get("AdversaryName", "Unknown")
        location = event.get("StadiumName", "Unknown")
        competition = event.get("TournamentName", "Unknown")
        is_home = event.get("IsHome", True)
        tv_channel = event.get("TvChannel")

        if not match_date_str:
            return None

        # Parse the date (format: "2024-11-24T20:15:00")
        match_dt = datetime.fromisoformat(
            match_date_str.replace("Z", "+00:00")
        )

        # Convert to Lisbon timezone
        match_dt_aware = pendulum.instance(match_dt).in_timezone(TIMEZONE)

        # Only return future matches
        now = pendulum.now(TIMEZONE)
        if match_dt_aware <= now:
            return None

        return {
            "date": match_dt_aware.format("DD-MM-YYYY"),
            "time": match_dt_aware.format("HH:mm"),
            "adversary": adversary,
            "location": location,
            "competition": competition,
            "home": "Casa" if is_home else "Fora",
            "tv_channel": tv_channel,
        }
    except Exception as e:
        logger.error(f"Error parsing match event: {e}")
        return None


def _generate_discord_previews(match_data: dict[str, Any]) -> str:
    """Generate Discord message previews for match data.

    Args:
        match_data: Match data dictionary with date, time, adversary, etc.

    Returns:
        Formatted string with all Discord message previews.
    """
    # Parse date for Discord timestamp
    date_parts = match_data["date"].split("-")
    time_parts = match_data["time"].split(":")
    match_dt = pendulum.datetime(
        year=int(date_parts[2]),
        month=int(date_parts[1]),
        day=int(date_parts[0]),
        hour=int(time_parts[0]),
        minute=int(time_parts[1]),
        tz=TIMEZONE,
    )
    timestamp = int(match_dt.timestamp())

    # Import emojis and constants
    from config.constants import PULHAS, SLB, WEEKDAY

    lines = []
    lines.append("=" * 70)
    lines.append("DISCORD MESSAGE PREVIEWS")
    lines.append("=" * 70)

    # 1. /quando_joga message
    lines.append("")
    lines.append("1️⃣  /quando_joga command:")
    lines.append("-" * 70)
    quando_joga_msg = (
        f"{PULHAS} {WEEKDAY[match_dt.isoweekday()]}, "
        f"dia {match_dt.day} às <t:{timestamp}:t>, "
        f"{SLB} vs {match_data['adversary']}, "
        f"no {match_data['location']} "
        f"para o/a {match_data['competition']}"
    )
    # Add TV channel if available
    if match_data.get("tv_channel"):
        quando_joga_msg += f" 📺 {match_data['tv_channel']}"
    lines.append(quando_joga_msg)

    # 2. /quanto_falta message (sample)
    lines.append("")
    lines.append("2️⃣  /quanto_falta command (example output):")
    lines.append("-" * 70)
    now_lisbon = pendulum.now(TIMEZONE)
    time_to_match = match_dt - now_lisbon
    total_seconds = int(time_to_match.total_seconds())
    days = total_seconds // 86400
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    is_today = now_lisbon.date() == match_dt.date()
    if is_today:
        quanto_falta_msg = (
            f"{PULHAS} É hoje! Já só falta(m) {hours} hora(s), "
            f"{minutes} minuto(s) e {seconds} segundo(s) para ver o "
            f"Glorioso de novo! {SLB}"
        )
    else:
        quanto_falta_msg = (
            f"{PULHAS} Falta(m) {days} dia(s), "
            f"{hours} hora(s), {minutes} minuto(s) e {seconds} "
            f"segundo(s) para ver o Glorioso de novo! {SLB}"
        )
    lines.append(quanto_falta_msg)

    # 3. /criar_evento details
    lines.append("")
    lines.append("3️⃣  /criar_evento command:")
    lines.append("-" * 70)
    lines.append(f"Event Name: ⚽ Benfica vs {match_data['adversary']}")
    lines.append(f"Event Time: <t:{timestamp}:F>")
    lines.append(f"Location: {match_data['location']}")
    event_desc = (
        f"Benfica vs {match_data['adversary']} no "
        f"{match_data['location']} para o/a {match_data['competition']}"
    )
    if match_data.get("tv_channel"):
        event_desc += f"\n📺 {match_data['tv_channel']}"
    lines.append(f"Description: {event_desc}")
    end_time = match_dt.add(hours=2)
    lines.append(
        f"Duration: {match_dt.format('HH:mm')} - "
        f"{end_time.format('HH:mm')} (2 hours)"
    )

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def get_upcoming_matches(limit: int = 5) -> list[dict] | None:
    """Get multiple upcoming Benfica matches from calendar API.

    Args:
        limit: Maximum number of matches to return (default 5).

    Returns:
        List of match dictionaries sorted by date, or None if error.
        Each dict contains: date, time, adversary, location, competition,
        home (bool), tv_channel (optional).

    Raises:
        requests.RequestsError: If API request fails.
    """
    try:
        logger.info(
            f"Attempting to fetch {limit} upcoming matches from Benfica API"
        )
        calendar = Calendar()
        events = calendar.get_events()

        if not events:
            logger.warning("No events found in API response")
            return None

        matches = []
        for event in events:
            match = _parse_match_from_event(event)
            if match:  # Only future matches (past matches return None)
                matches.append(match)
                if len(matches) >= limit:
                    break

        logger.info(f"Successfully fetched {len(matches)} upcoming matches")
        return matches if matches else None
    except requests.RequestsError as e:
        logger.error(f"API error fetching upcoming matches: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Parse error fetching upcoming matches: {e}")
        return None


def _run_dry_run() -> None:
    """Execute dry-run mode showing API extraction and Discord previews."""
    print("\n" + "=" * 70)
    print("🔍 DRY RUN MODE - Calendar API Data Extraction")
    print("=" * 70 + "\n")

    try:
        # Initialize calendar and fetch raw events
        print("📡 Initializing Calendar API client...")
        calendar = Calendar()
        print("✓ Token extracted successfully\n")

        # Show the payload that will be sent
        payload = calendar._create_payload()
        print("-" * 70)
        print("REQUEST PAYLOAD (Filters):")
        print("-" * 70)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()

        print("📡 Fetching events from API...")
        print(f"URL: {CALENDAR_API_URL}")
        print("Method: POST")
        print()

        # Make the request and capture response before parsing JSON
        headers = calendar._create_headers()
        payload = calendar._create_payload()
        response = requests.post(
            CALENDAR_API_URL,
            headers=headers,
            json=payload,
            cookies=calendar.cookies,
            impersonate="chrome",
            timeout=30,
            allow_redirects=True,
        )
        print(f"✓ Response received: Status {response.status_code}\n")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Response length: {len(response.text)} bytes\n")
        print("-" * 70)
        print("RAW RESPONSE BODY (first 500 chars):")
        print("-" * 70)
        print(response.text[:500])
        print("\n")

        # Parse HTML response
        print("✓ Parsing HTML response\n")
        calendar_soup = BeautifulSoup(response.text, "html.parser")
        calendar_items = calendar_soup.find_all("div", class_="calendar-item")

        print("-" * 70)
        print(f"TOTAL CALENDAR ITEMS FOUND: {len(calendar_items)}")
        print("-" * 70)
        print()

        # Parse each calendar item
        events = []
        for item in calendar_items:
            event = calendar._parse_calendar_item(item)
            if event:
                events.append(event)

        print(f"✓ Successfully parsed {len(events)} events\n")

        # Show all parsed events
        if events:
            print("-" * 70)
            print("ALL PARSED EVENTS:")
            print("-" * 70)
            for i, event in enumerate(events, 1):
                print(
                    f"\n{i}. {event['AdversaryName']} - {event['MatchDate']}"
                )
                print(f"   Competition: {event['TournamentName']}")
                print(f"   Location: {event['StadiumName']}")
                print(f"   Home/Away: {'Casa' if event['IsHome'] else 'Fora'}")
            print()

            # Find first future match using _parse_match_from_event
            print("-" * 70)
            print("SEARCHING FOR NEXT UPCOMING MATCH:")
            print("-" * 70)
            future_match_found = False
            for i, event in enumerate(events, 1):
                match_data = _parse_match_from_event(event)
                if match_data:
                    print(f"\n✓ Next match found (Event #{i}):\n")
                    print("-" * 70)
                    print("PARSED MATCH DATA:")
                    print("-" * 70)
                    print(json.dumps(match_data, indent=2, ensure_ascii=False))
                    print()
                    print("FORMATTED OUTPUT:")
                    print(f"  Adversário: {match_data['adversary']}")
                    print(f"  Data: {match_data['date']}")
                    print(f"  Hora: {match_data['time']}")
                    print(f"  Local: {match_data['location']}")
                    print(f"  Competição: {match_data['competition']}")
                    print(f"  Casa/Fora: {match_data['home']}")
                    if match_data.get("tv_channel"):
                        print(f"  📺 Canal TV: {match_data['tv_channel']}")

                    # Show Discord message previews
                    print()
                    print(_generate_discord_previews(match_data))

                    future_match_found = True
                    break

            if not future_match_found:
                print("\n⚠️  No future matches found")
                print("All events are past matches\n")
        else:
            print("⚠️  No events could be parsed from the response\n")

    except Exception as e:
        print(f"\n❌ Error during dry-run: {e}")
        logger.error(f"Dry-run error: {e}", exc_info=True)

    print("\n" + "=" * 70)
    print("ℹ️  Dry-run complete - no files were modified")
    print("=" * 70 + "\n")


def get_next_match_from_api() -> dict[str, Any] | None:
    """Get next match data from Benfica official API.

    Returns:
        Match data dictionary or None if API fails or no upcoming matches.
    """
    try:
        logger.info("Attempting to fetch match data from Benfica API")
        calendar = Calendar()
        events = calendar.get_events()

        # get_events() now returns a list of event dictionaries
        if not events:
            logger.warning("No events found in API response")
            return None

        # Find the first upcoming match
        for event in events:
            match_data = _parse_match_from_event(event)
            if match_data:
                logger.info(
                    f"Found next match from API: {match_data['adversary']} "
                    f"on {match_data['date']}"
                )
                return match_data

        logger.warning("No upcoming matches found in API response")
        return None

    except Exception as e:
        logger.error(f"Error fetching match data from Benfica API: {e}")
        return None


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Fetch Benfica match data from official calendar API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show detailed extraction info with Discord message previews",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.dry_run:
        _run_dry_run()
    else:
        # Normal mode - just get next match
        print("\n📅 Fetching next match from Benfica Calendar API...\n")
        match_data = get_next_match_from_api()
        if match_data:
            print("✓ Next match found:")
            print(json.dumps(match_data, indent=2, ensure_ascii=False))
        else:
            print("⚠️  No upcoming matches found")
