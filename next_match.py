import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from time import mktime

import pendulum
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from gen_browser import gen_browser

logger = logging.getLogger(__name__)

MATCH_DATA_FILE = Path(__file__).parent / "match_data.json"

PULHAS = "<:pulhas:867780231116095579>"
SLB = "<:slb:240116451782950914>"
URL = "https://www.slbenfica.pt/pt-pt/futebol/calendario"
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
    """Scrape next match information from SL Benfica website.

    Returns:
        Dict with match data (date, adversary, location, competition)
        or None if no match found or error occurs.
    """
    browser = gen_browser()
    try:
        browser.get(URL)
        calendar_obj = WebDriverWait(browser, 3).until(
            ec.presence_of_element_located(
                (By.CLASS_NAME, "calendar-match-info")
            )
        )
        next_match_date = calendar_obj.find_element(
            By.CLASS_NAME, "startDateForCalendar"
        ).get_attribute("textContent")
        match_date = datetime.strptime(
            next_match_date, r"%m/%d/%Y %I:%M:%S %p"
        )

        title_element = calendar_obj.find_element(
            By.CLASS_NAME, "titleForCalendar"
        )
        teams = [
            i.strip()
            for i in title_element.get_attribute("textContent").split("vs")
        ]
        teams.pop(teams.index("SL Benfica"))
        adversary = teams[0]

        location = calendar_obj.find_element(
            By.CLASS_NAME, "locationForCalendar"
        ).get_attribute("textContent")

        competition = browser.find_element(
            By.CLASS_NAME, "calendar-competition"
        ).text

        match_data = {
            "date": match_date,
            "adversary": adversary,
            "location": location,
            "competition": competition,
        }
        return match_data

    except TimeoutException:
        logger.warning("Timeout waiting for calendar element")
        return None
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting match data: {e}")
        return None
    finally:
        browser.quit()


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

    if days != 0:
        sentence = (
            f"{PULHAS} Falta(m) {days} dia(s), "
            f"{hours} hora(s), {minutes} minuto(s) e {seconds} "
            f"segundo(s) para ver o Glorioso de novo! {SLB}"
        )
    else:
        sentence = (
            f"{PULHAS} É hoje! Já só falta(m) {hours} hora(s), "
            f"{minutes} minuto(s) e {seconds} segundo(s) para ver o "
            f"Glorioso de novo! {SLB}"
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


def generate_event() -> str:
    """Generate formatted event text for Discord.

    Returns:
        Multi-line string with match event details.
    """
    match_data = read_match_data()
    match_date = datetime_match_date()
    hour, minutes = match_date.time().isoformat().split(":")[:-1]

    event_text = (
        "```",
        f":trophy: {match_data['competition']}",
        f":stadium: {match_data['location']}",
        f":alarm_clock: {hour}:{minutes}",
        ":tv:",
        "```",
    )
    return "\n".join(event_text)
