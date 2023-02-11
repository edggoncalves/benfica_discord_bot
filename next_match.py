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


def get_next_match() -> datetime | None:
    browser = gen_browser()
    browser.get(URL)
    try:
        calendar_obj = WebDriverWait(browser, 3).until(
            ec.presence_of_element_located((By.CLASS_NAME, "calendar-match-info"))
        )
        # calendar_obj = browser.find_element(By.CLASS_NAME, "calendar-match-info")
        next_match_date = calendar_obj.find_element(
            By.CLASS_NAME, "startDateForCalendar"
        ).get_attribute("textContent")
        match_date = datetime.strptime(next_match_date, r"%m/%d/%Y %I:%M:%S %p")
    except TimeoutException:
        match_date = None

    browser.quit()
    return match_date


def write_conf(match_date: datetime):
    n = datetime.now()
    data = {
        "next_match": {
            "year": match_date.year,
            "month": match_date.month,
            "day": match_date.day,
            "hour": match_date.hour,
            "minute": match_date.minute,
        },
        "fetched": {
            "year": n.year,
            "month": n.month,
            "day": n.day,
            "hour": n.hour,
            "minute": n.minute,
        },
    }
    configuration.write(data)


def update_match_date():
    match_date = get_next_match()
    write_conf(match_date)


def datetime_match_date():
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
    match_date = datetime_match_date()
    hour, minutes = match_date.time().isoformat().split(":")[:-1]
    sentence = f"{PULHAS} {WEEKDAY[match_date.isoweekday()]}, dia {match_date.day} às {hour}h{minutes} {SLB}"

    return sentence
