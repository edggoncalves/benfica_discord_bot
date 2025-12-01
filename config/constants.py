"""Immutable constants for the Benfica Discord bot."""

# Legacy URLs (not currently used)
CALENDAR_URL = "https://www.slbenfica.pt/pt-pt/futebol/calendario"
CALENDAR_API_URL = (
    "https://www.slbenfica.pt/api/sitecore/Calendar/CalendarEvents"
)

# Timezone
TIMEZONE = "Europe/Lisbon"

# Newspaper names (for filename generation)
NEWSPAPER_NAMES = ["a_bola", "o_jogo", "record"]

# Discord custom emojis
PULHAS = "<:pulhas:867780231116095579>"
SLB = "<:slb:240116451782950914>"

# Weekday names in Portuguese
WEEKDAY = {
    1: "Segunda-feira",
    2: "Terça-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sábado",
    7: "Domingo",
}


# Error messages
ERROR_MATCH_DATA_NOT_FOUND = (
    "Dados do jogo não encontrados. Usa `/actualizar_data` primeiro."
)
ERROR_MATCH_DATA_UPDATE = "❌ Erro ao actualizar data do jogo."
ERROR_COVERS_FETCH = "❌ Erro ao obter capas dos jornais."
ERROR_COVERS_FILE_NOT_FOUND = "❌ Erro: Ficheiro de capas não encontrado."
ERROR_COVERS_FILE_READ = "❌ Erro ao ler o ficheiro de capas."
ERROR_COVERS_SEND = "❌ Erro ao enviar capas."
ERROR_MATCH_COUNTDOWN = "❌ Erro ao calcular tempo até ao jogo."
ERROR_MATCH_DATE = "❌ Erro ao obter data do jogo."
ERROR_TOTW_FETCH = "❌ Erro ao obter equipa da semana."
ERROR_EVENT_CREATE = "❌ Erro ao criar evento"
ERROR_GUILD_ONLY = "❌ Este comando só funciona em servidores."
ERROR_NO_UPCOMING_MATCH = (
    "❌ Não há jogos futuros disponíveis no calendário. "
    "Verifica mais tarde."
)

# Success messages
SUCCESS_MATCH_DATA_UPDATED = (
    "✅ Data do jogo actualizada. "
    "Testa com `/quando_joga` ou `/quanto_falta`"
)
SUCCESS_MATCH_DATA_REFRESHED = "🔄 A actualizar dados do calendário..."
SUCCESS_EVENT_CREATED = "✅ Evento criado com sucesso!"
SUCCESS_EVENT_DESCRIPTION = (
    "🏟️ **Local:** {location}\n"
    "🏆 **Competição:** {competition}\n\n"
    "Força Benfica! 🦅"
)

# Event messages
EVENT_ALREADY_EXISTS = (
    "❌ Já existe um evento com este nome!\n"
    "📅 {name}\n"
    "🕐 <t:{timestamp}:F>"
)
EVENT_CREATED = (
    "✅ Evento criado com sucesso!\n" "📅 {name}\n" "🕐 <t:{timestamp}:F>"
)
