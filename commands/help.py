"""Help command implementation."""

import discord


async def help_command(interaction: discord.Interaction) -> None:
    """Show all available bot commands.

    Args:
        interaction: Discord interaction object.
    """
    help_msg = (
        "📋 **Comandos Disponíveis**\n\n"
        "**Capas de Jornais:**\n"
        "`/capas` - Mostrar capas dos jornais desportivos\n\n"
        "**Informação de Jogos:**\n"
        "`/quando_joga` - Ver quando joga o Benfica\n"
        "`/quanto_falta` - Tempo até ao próximo jogo\n"
        "`/actualizar_data` - Atualizar dados do próximo jogo\n"
        "`/calendario [quantidade]` - Próximos jogos (padrão: 5, máx: 10)\n"
        "`/criar_evento` - Criar evento no Discord para o próximo jogo\n\n"
        "**Estatísticas:**\n"
        "`/equipa_semana` - Equipa da semana da Liga Portugal\n\n"
        "**Outros:**\n"
        "`/help` - Mostrar esta mensagem de ajuda"
    )

    await interaction.followup.send(help_msg, ephemeral=True)
