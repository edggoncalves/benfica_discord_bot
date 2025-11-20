import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from time import mktime

import pendulum
import requests
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

MATCH_DATA_FILE = Path(__file__).parent / "match_data.json"

PULHAS = "<:pulhas:867780231116095579>"
SLB = "<:slb:240116451782650914>"
ESPN_URL = "https://www.espn.com/soccer/team/fixtures/_/id/1929"

# Initialize user agent generator
ua = UserAgent()


def _get_headers() -> dict:
    """Generate realistic browser headers.

    Returns:
        Dictionary with User-Agent header.
    """
    return {"User-Agent": ua.random}
TZ = "Europe/Lisbon"
WEEKDAY = {
    1: "Segunda-feira",
    2: "Terça-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sábado",
    7: "Domingo",
}


def get_next_match() -> dict | None:
    """Scrape next match from ESPN using requests only (no Selenium).

    Returns:
        Dict with match data (date, adversary, location, competition)
        or None if no match found or error occurs.
    """
    try:
        logger.info(f"Fetching ESPN fixtures from {ESPN_URL}")
        response = requests.get(ESPN_URL, headers=_get_headers(), timeout=30)
        response.raise_for_status()
        logger.info(f"Page fetched successfully ({len(response.text)} bytes)")

        # Extract embedded JSON data from window['__espnfitt__']
        pattern = r"window\['__espnfitt__'\]\s*=\s*({.*?});"
        matches = re.findall(pattern, response.text, re.DOTALL)

        if not matches:
            logger.error("Could not find __espnfitt__ data in page")
            return None

        logger.info("Found __espnfitt__ data, parsing JSON...")
        data = json.loads(matches[0])

        # Navigate to fixtures
        fixtures = data.get("page", {}).get("content", {}).get("fixtures", {})
        events = fixtures.get("events", [])

        if not events:
            logger.error("No events found in fixtures data")
            return None

        logger.info(f"Found {len(events)} upcoming matches")

        # Get first event (they're sorted chronologically)
        event = events[0]

        # Extract match data
        date_str = event.get("date")
        if not date_str:
            logger.error("No date in first event")
            return None

        # Parse ISO 8601 date
        match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Get competition info
        competition = event.get("league", "Unknown Competition")

        # Get teams (directly from event.competitors)
        competitors = event.get("competitors", [])
        home_team = away_team = None
        for team in competitors:
            if team.get("isHome"):
                home_team = team.get("displayName")
            else:
                away_team = team.get("displayName")

        # Determine adversary and home/away status
        if home_team and "Benfica" in home_team:
            adversary = away_team or "Unknown"
            is_home = True
        else:
            adversary = home_team or "Unknown"
            is_home = False

        # Get venue
        venue = event.get("venue", {})
        location = venue.get("fullName", "Unknown Venue")

        match_data = {
            "date": match_date,
            "adversary": adversary,
            "location": location,
            "competition": competition,
            "is_home": is_home,
        }

        logger.info(
            f"Match data scraped: {adversary} on {match_date} at {location}"
        )
        return match_data

    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse ESPN data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting match data: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return None


def write_match_data(info: dict) -> None:
    """Write match information to JSON file.

    Args:
        info: Dictionary containing match data with date, adversary,
              location, and competition keys.
    """
    data = {
        "year": info["date"].year,
        "month": info["date"].month,
        "day": info["date"].day,
        "hour": info["date"].hour,
        "minute": info["date"].minute,
        "adversary": info["adversary"],
        "location": info["location"],
        "competition": info["competition"],
    }
    with open(MATCH_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Match data saved")


def read_match_data() -> dict:
    """Read match information from JSON file.

    Returns:
        Dictionary with match data.

    Raises:
        FileNotFoundError: If match data file doesn't exist.
    """
    if not MATCH_DATA_FILE.exists():
        raise FileNotFoundError(
            "Match data not found. Run !actualizar_data first."
        )
    with open(MATCH_DATA_FILE) as f:
        return json.load(f)


def update_match_date() -> bool:
    """Update match date by scraping website.

    Returns:
        True if update successful, False otherwise.
    """
    match_data = get_next_match()
    if match_data is None:
        logger.error("Failed to get match data")
        return False
    write_match_data(match_data)
    return True


def datetime_match_date() -> datetime:
    """Get next match date from saved data.

    Returns:
        Datetime object of next match.
    """
    match_info = read_match_data()
    match_date = datetime(
        int(match_info["year"]),
        int(match_info["month"]),
        int(match_info["day"]),
        int(match_info["hour"]),
        int(match_info["minute"]),
    )
    return match_date


def how_long_until() -> str:
    """Generate message showing time until next match.

    Returns:
        Formatted string with countdown to match.
    """
    match_data = read_match_data()

    # Create timezone-aware match datetime in Lisbon time
    match_dt_lisbon = pendulum.datetime(
        year=match_data["year"],
        month=match_data["month"],
        day=match_data["day"],
        hour=match_data["hour"],
        minute=match_data["minute"],
        tz=TZ,
    )

    # Get current time in Lisbon timezone
    now_lisbon = pendulum.now(TZ)

    # Calculate time difference
    time_to_match = match_dt_lisbon - now_lisbon

    # Extract days, hours, minutes, seconds from the duration
    total_seconds = int(time_to_match.total_seconds())
    days = total_seconds // 86400
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60

    # Check if match is actually today (same date)
    is_today = (
        now_lisbon.date() == match_dt_lisbon.date()
    )

    if is_today:
        sentence = (
            f"{PULHAS} É hoje! Já só falta(m) {hours} hora(s), "
            f"{minutes} minuto(s) e {seconds} segundo(s) para ver o "
            f"Glorioso de novo! {SLB}"
        )
    else:
        sentence = (
            f"{PULHAS} Falta(m) {days} dia(s), "
            f"{hours} hora(s), {minutes} minuto(s) e {seconds} "
            f"segundo(s) para ver o Glorioso de novo! {SLB}"
        )

    return sentence


def when_is_it() -> str:
    """Generate message showing when next match is scheduled.

    Returns:
        Formatted string with match date, time and details.
    """
    match_data = read_match_data()
    tz_diff = (pendulum.today(TZ) - pendulum.today()).total_hours()
    match_date = datetime_match_date() + timedelta(hours=int(tz_diff))
    h_m_timestamp = int(mktime(match_date.timetuple()))
    sentence = (
        f"{PULHAS} {WEEKDAY[match_date.isoweekday()]}, "
        f"dia {match_date.day} às <t:{h_m_timestamp}:t>, "
        f"{SLB} vs {match_data['adversary']}, "
        f"no {match_data['location']} "
        f"para o/a {match_data['competition']}"
    )
    return sentence


if __name__ == "__main__":
    # Test the ESPN scraper
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s - %(message)s"
    )
    success = update_match_date()
    print(f"\nResult: {'Success' if success else 'Failed'}")
    if success:
        with open(MATCH_DATA_FILE) as f:
            print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
