import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

from datetime import datetime, timedelta
from time import mktime
import pendulum

import configuration


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
    """
    Write a function that returns the next match date, adversary, location and competition
    :return: dict
    """
    response = _request_with_retry(URL)
    response.raise_for_status()  # Check for errors

    soup = BeautifulSoup(response.content, features="html.parser")

    match_info = soup.find(name="div", class_="calendar-match-info")
    # browser = gen_browser()
    # browser.get(URL)
    # try:
    #     calendar_obj = WebDriverWait(browser, 3).until(
    #         ec.presence_of_element_located((By.CLASS_NAME, "calendar-match-info"))
    #     )
    #     next_match_date = calendar_obj.find_element(
    #         By.CLASS_NAME, "startDateForCalendar"
    #     ).get_attribute("textContent")
    #     match_date = datetime.strptime(next_match_date, r"%m/%d/%Y %I:%M:%S %p")
    #
    #     teams = [
    #         i.strip() for i in
    #         calendar_obj.find_element(
    #             By.CLASS_NAME, "titleForCalendar").get_attribute("textContent").split("vs")
    #     ]
    #     teams.pop(teams.index("SL Benfica"))
    #     adversary = teams[0]
    #
    #     location = calendar_obj.find_element(
    #             By.CLASS_NAME, "locationForCalendar").get_attribute("textContent")
    #
    #     competition = browser.find_element(By.CLASS_NAME, "calendar-competition").text
    #
    #     match_data = {
    #         "date": match_date,
    #         "adversary": adversary,
    #         "location": location,
    #         "competition": competition,
    #     }
    #
    # except TimeoutException:
    #     match_data = None
    #
    # browser.quit()
    return match_data


def _request_with_retry(url: str, max_retries: int = 3, timeout: float = 5.0) -> requests.Response | None:
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            return response
        except RequestException as e:
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print(f"Max retries exceeded. Giving up.\n\n{e}")
                return None


def write_conf(info: dict):
    data = {
        "next_match": {
            "year": info["date"].year,
            "month": info["date"].month,
            "day": info["date"].day,
            "hour": info["date"].hour,
            "minute": info["date"].minute,
            "adversary": info["adversary"],
            "location": info["location"],
            "competition": info["competition"],
        }
    }
    configuration.write(data)


def update_match_date():
    match_data = get_next_match()
    write_conf(match_data)


def datetime_match_date() -> datetime:
    config = configuration.read()
    m = {s: dict(config.items(s)) for s in config.sections()}["next_match"]
    match_date = datetime(
        int(m["year"]),
        int(m["month"]),
        int(m["day"]),
        int(m["hour"]),
        int(m["minute"]),
    )

    return match_date


def how_long_until() -> str:
    match_date = datetime_match_date()
    tz_diff = (pendulum.today() - pendulum.today(TZ)).total_hours()
    local_time = datetime.now() + timedelta(hours=int(tz_diff))
    time_to_match = match_date - local_time
    hours, minutes, seconds = str(timedelta(seconds=time_to_match.seconds)).split(":")

    if time_to_match.days != 0:
        sentence = (
            f"{PULHAS} Falta(m) {time_to_match.days} dia(s), {hours} hora(s), {minutes} minuto(s) e {seconds} "
            f"segundo(s) para ver o Glorioso de novo! {SLB}"
        )
    else:
        sentence = (
            f"{PULHAS} É hoje! Já só falta(m) {hours} hora(s), {minutes} minuto(s) e {seconds} segundo(s) para ver o "
            f"Glorioso de novo! {SLB}"
        )

    return sentence


def when_is_it() -> str:
    config = configuration.read()
    match_data = {s: dict(config.items(s)) for s in config.sections()}["next_match"]
    tz_diff = (pendulum.today(TZ) - pendulum.today()).total_hours()
    match_date = datetime_match_date() + timedelta(hours=int(tz_diff))
    h_m_timestamp = int(mktime(match_date.timetuple()))
    sentence = (
        f"{PULHAS} {WEEKDAY[match_date.isoweekday()]}, dia {match_date.day} às <t:{h_m_timestamp}:t>, {SLB} vs "
        f"{match_data['adversary']}, no {match_data['location']} para o/a {match_data['competition']}"
    )

    return sentence


def generate_event() -> str:
    config = configuration.read()
    match_data = {s: dict(config.items(s)) for s in config.sections()}["next_match"]
    match_date = datetime_match_date()
    hour, minutes = match_date.time().isoformat().split(":")[:-1]

    event_text = (
        f"```",
        f":trophy: {match_data['competition']}",
        f":stadium: {match_data['location']}",
        f":alarm_clock: {hour}:{minutes}",
        f":tv:",
        f"```",
    )
    return "\n".join(event_text)
