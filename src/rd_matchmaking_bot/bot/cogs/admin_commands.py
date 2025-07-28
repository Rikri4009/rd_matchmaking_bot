import discord
from discord.ext import commands
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.endless as endless

class AdminCommands(commands.Cog):
    def __init__(self, bot: MatchmakingBot):
        self.bot = bot
    
    @discord.slash_command(description="(ADVANCED) Run an admin command.")
    async def admin_command(self, ctx,
        command: discord.Option(discord.SlashCommandOptionType.string)
    ):
        uid = str(ctx.user.id)

        if (command == "endless begin") or (command == "e begin"):
            await endless.begin(self, ctx, uid)
            return
        
        if (command == "endless roll") or (command == "e roll"):
            await endless.roll(self, ctx, uid)
            return

        if (command == "endless already_seen") or (command == "e already_seen"):
            await endless.reroll(self, ctx, uid)
            return

        if (command == "endless recover") or (command == "e recover"):
            await endless.recover(self, ctx, uid)
            return
        
        if (command == "endless forage 1") or (command == "e forage 1"):
            await endless.roll_extra(self, ctx, uid, 1, "Medium")
            return

        if (command == "endless forage 2") or (command == "e forage 2"):
            await endless.roll_extra(self, ctx, uid, 2, "Tough")
            return

        args = command.split()

        if (len(args) == 3) and ((args[0] == "endless") or (args[0] == "e")) and (args[1] == "use"):
            await endless.use_item(self, ctx, uid, args[2])
            return

        if (len(args) == 3) and ((args[0] == "endless") or (args[0] == "e")) and (args[1] == "submit") and ((args[2]).isdigit()):
            await endless.submit_misses(self, ctx, uid, int(args[2]))
            return

        await ctx.respond(f"Invalid command!", ephemeral=True)
        return
    
def setup(bot: MatchmakingBot):
    cog = AdminCommands(bot)
    bot.add_cog(cog)