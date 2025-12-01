"""Match message formatters for Discord."""

import logging

import pendulum

from config.constants import PULHAS, SLB, TIMEZONE, WEEKDAY
from core.match.refresh import get_match_data_with_refresh
from core.match.repository import match_data_to_pendulum
from core.utils.date_parser import parse_dd_mm_yyyy_time

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


def format_upcoming_matches_message(matches: list[dict]) -> str:
    """Generate message showing multiple upcoming matches.

    Args:
        matches: List of match dictionaries from get_upcoming_matches().

    Returns:
        Formatted string with all upcoming matches.
    """
    if not matches:
        return "❌ Não há jogos futuros disponíveis no calendário."

    # Number emojis for list items (1-10)
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = ["📅 **Próximos Jogos do Benfica**\n"]

    for idx, match in enumerate(matches):
        # Parse match date and time to create pendulum datetime
        match_dt = parse_dd_mm_yyyy_time(match["date"], match["time"])

        # Use number emoji if available, otherwise use number
        if idx < len(number_emojis):
            number = number_emojis[idx]
        else:
            number = f"{idx + 1}."

        # Convert to Unix timestamp for Discord's dynamic date/time display
        timestamp = int(match_dt.timestamp())
        # Discord timestamp format 'F': "Tuesday, 20 April 2021 16:20"
        # Shows full date/time in user's locale
        lines.append(f"{number} **<t:{timestamp}:F>**")

        # Determine home/away with emoji
        # Note: home field is a string ("Casa" or "Fora"), not a boolean
        home_str = match.get("home", "Casa")
        is_home = home_str == "Casa"
        home_away_indicator = "🏠 Casa" if is_home else "✈️ Fora"

        # Format the match info
        if is_home:
            match_info = (
                f"   ⚽ {SLB} vs {match['adversary']} "
                f"{home_away_indicator}"
            )
        else:
            match_info = (
                f"   ⚽ {match['adversary']} vs {SLB} "
                f"{home_away_indicator}"
            )

        lines.append(match_info)
        lines.append(f"   🏟️ {match['location']}")
        lines.append(f"   🏆 {match['competition']}")

        # Add TV channel if available
        if match.get("tv_channel"):
            lines.append(f"   📺 {match['tv_channel']}")

        # Add blank line between matches (except after last one)
        if idx < len(matches) - 1:
            lines.append("")

    return "\n".join(lines)
