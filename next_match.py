from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException


from datetime import datetime, timedelta
import pendulum
import configuration
from gen_browser import gen_browser


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
    browser = gen_browser()
    browser.get(URL)
    try:
        calendar_obj = WebDriverWait(browser, 3).until(
            ec.presence_of_element_located((By.CLASS_NAME, "calendar-match-info"))
        )
        next_match_date = calendar_obj.find_element(
            By.CLASS_NAME, "startDateForCalendar"
        ).get_attribute("textContent")
        match_date = datetime.strptime(next_match_date, r"%m/%d/%Y %I:%M:%S %p")

        teams = [
            i.strip() for i in
            calendar_obj.find_element(
                By.CLASS_NAME, "titleForCalendar").get_attribute("textContent").split("vs")
        ]
        teams.pop(teams.index("SL Benfica"))
        adversary = teams[0]

        location = calendar_obj.find_element(
                By.CLASS_NAME, "locationForCalendar").get_attribute("textContent")

        competition = browser.find_element(By.CLASS_NAME, "calendar-competition").text

        match_data = {
            "date": match_date,
            "adversary": adversary,
            "location": location,
            "competition": competition,
        }

    except TimeoutException:
        match_data = None

    browser.quit()
    return match_data


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
#

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
    match_date = datetime_match_date()
    hour, minutes = match_date.time().isoformat().split(":")[:-1]
    sentence = (
        f"{PULHAS} {WEEKDAY[match_date.isoweekday()]}, dia {match_date.day} às {hour}h{minutes}, {SLB} vs "
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
