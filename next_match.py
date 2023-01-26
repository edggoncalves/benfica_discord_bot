from selenium.webdriver.common.by import By

from datetime import datetime, timedelta
import pendulum
import configuration
from gen_browser import gen_browser


URL = 'https://www.slbenfica.pt/pt-pt/futebol/calendario'
TZ = 'Europe/Lisbon'
WEEKDAY = {
    1: 'Segunda-feira',
    2: 'Terça-feira',
    3: 'Quarta-feira',
    4: 'Quinta-feira',
    5: 'Sexta-feira',
    6: 'Sábado',
    7: 'Domingo'
}


def get_next_match() -> datetime:
    browser = gen_browser()
    browser.get(URL)
    next_match = browser.find_element(By.CLASS_NAME, 'highlight-event-center')
    hour, minute = next_match.text.splitlines()[2].split('h')
    day, month = next_match.text.splitlines()[1].split('/')
    browser.quit()
    return datetime(datetime.now().year, int(month), int(day), int(hour), int(minute))


def write_conf(match_date: datetime):
    n = datetime.now()
    data = {
        'next_match': {
            'year': match_date.year,
            'month': match_date.month,
            'day': match_date.day,
            'hour': match_date.hour,
            'minute': match_date.minute,
        },
        'fetched': {
            'year': n.year,
            'month': n.month,
            'day': n.day,
            'hour': n.hour,
            'minute': n.minute,
        }
    }
    configuration.write(data)


def datetime_match_date():
    config = configuration.read()
    if config.has_section('next_match'):
        c = {s: dict(config.items(s)) for s in config.sections()}['fetched']
        fetched = datetime(
            int(c['year']),
            int(c['month']),
            int(c['day']),
            int(c['hour']),
            int(c['minute'])
        )

        if datetime.now() - fetched > timedelta(hours=2):
            match_date = get_next_match()
            write_conf(match_date)
        else:
            m = {s: dict(config.items(s)) for s in config.sections()}['next_match']
            match_date = datetime(
                int(m['year']),
                int(m['month']),
                int(m['day']),
                int(m['hour']),
                int(m['minute']),
            )
    else:
        match_date = get_next_match()
        write_conf(match_date)
    return match_date


def how_long_until() -> str:
    match_date = datetime_match_date()
    tz_diff = (pendulum.today() - pendulum.today(TZ)).total_hours()
    local_time = datetime.now() + timedelta(hours=int(tz_diff))
    time_to_match = match_date - local_time
    hours, minutes, seconds = str(timedelta(seconds=time_to_match.seconds)).split(':')

    if time_to_match.days != 0:
        sentence = f'<:slb:240116451782950914> Falta(m) {time_to_match.days} dia(s), {hours} hora(s), ' \
                   f'{minutes} minuto(s) e {seconds} segundo(s) para ver o Glorioso de novo! <:slb:240116451782950914>'
    else:
        sentence = f'<:slb:240116451782950914> É hoje! Já só falta(m) {hours} hora(s), {minutes} minuto(s) ' \
                   f'e {seconds} segundo(s) para ver o Glorioso de novo! <:slb:240116451782950914>'

    return sentence


def when_is_it() -> str:
    match_date = datetime_match_date()
    sentence = f'<:slb:240116451782950914> {WEEKDAY[match_date.isoweekday()]}, dia {match_date.day} ' \
               f'às {match_date.hour}h{match_date.minute} <:slb:240116451782950914>'
    return sentence
