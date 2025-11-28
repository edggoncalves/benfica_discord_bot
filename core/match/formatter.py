"""Match message formatters for Discord."""

import logging

import pendulum

from config.constants import PULHAS, SLB, TIMEZONE, WEEKDAY
from core.match.refresh import get_match_data_with_refresh
from core.match.repository import match_data_to_pendulum

logger = logging.getLogger(__name__)


def format_countdown_message() -> str:
    """Generate message showing time until next match.

    Automatically refreshes match data if stored match is in the past.

    Returns:
        Formatted string with countdown to match.
    """
    # Use auto-refresh to ensure we have upcoming match
    match_data, was_refreshed = get_match_data_with_refresh()

    if match_data is None:
        return (
            f"{PULHAS} Não há jogos agendados no momento. "
            f"Usa /actualizar_data para tentar obter novos dados."
        )

    match_dt_lisbon = match_data_to_pendulum(match_data)
    now_lisbon = pendulum.now(TIMEZONE)

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
    is_today = now_lisbon.date() == match_dt_lisbon.date()

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


def format_match_schedule_message() -> str:
    """Generate message showing when next match is scheduled.

    Automatically refreshes match data if stored match is in the past.

    Returns:
        Formatted string with match date, time and details.
    """
    # Use auto-refresh to ensure we have upcoming match
    match_data, was_refreshed = get_match_data_with_refresh()

    if match_data is None:
        return (
            f"{PULHAS} Não há jogos agendados no momento. "
            f"Usa /actualizar_data para tentar obter novos dados."
        )

    match_dt = match_data_to_pendulum(match_data)

    # Convert to Unix timestamp for Discord's <t:timestamp:t> formatting
    h_m_timestamp = int(match_dt.timestamp())

    sentence = (
        f"{PULHAS} {WEEKDAY[match_dt.isoweekday()]}, "
        f"dia {match_dt.day} às <t:{h_m_timestamp}:t>, "
        f"{SLB} vs {match_data['adversary']}, "
        f"no {match_data['location']} "
        f"para o/a {match_data['competition']}"
    )

    # Add TV channel if available
    if "tv_channel" in match_data and match_data["tv_channel"]:
        sentence += f" 📺 {match_data['tv_channel']}"

    return sentence
