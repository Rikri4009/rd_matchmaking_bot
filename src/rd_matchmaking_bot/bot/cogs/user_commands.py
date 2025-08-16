import re
import random
import math
import json
import discord
from discord import Attachment
from discord.ext import commands
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.ascension as ascension
import rd_matchmaking_bot.utils.misc as misc

class LeaderboardButtons(discord.ui.View):
    def __init__(self, bot: MatchmakingBot, uid, category, page):
        super().__init__()
        self.bot = bot
        self.uid = uid
        self.category = category
        self.page = page

    @discord.ui.button(label="<-", style=discord.ButtonStyle.secondary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        if self.page < 2:
            await interaction.respond("Already on first page!", ephemeral=True)
            return

        new_page = self.page - 1
        leaderboard_embed = misc.get_leaderboard_embed(interaction, self.bot, self.category, new_page)
        await interaction.response.edit_message(embed=leaderboard_embed, view=LeaderboardButtons(self.bot, self.uid, self.category, new_page))

    @discord.ui.button(label="->", style=discord.ButtonStyle.secondary)
    async def next_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        new_page = self.page + 1
        leaderboard_embed = misc.get_leaderboard_embed(interaction, self.bot, self.category, new_page)
        await interaction.response.edit_message(embed=leaderboard_embed, view=LeaderboardButtons(self.bot, self.uid, self.category, new_page))


class SpecializeButtons(discord.ui.View):
    def __init__(self, bot: MatchmakingBot, uid):
        super().__init__()
        self.bot = bot
        self.uid = uid

    @discord.ui.button(label="Apples", style=discord.ButtonStyle.primary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        user_stats = self.bot.users_stats[self.uid]
        user_stats["specialization"] = "Apples"

        await interaction.responsd("You now specialize in Apples!")

    @discord.ui.button(label="Ivory Dice", style=discord.ButtonStyle.primary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        user_stats = self.bot.users_stats[self.uid]
        user_stats["specialization"] = "Ivory Dice"

        await interaction.responsd("You now specialize in Ivory Dice!")

    @discord.ui.button(label="Chronographs", style=discord.ButtonStyle.primary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        user_stats = self.bot.users_stats[self.uid]
        user_stats["specialization"] = "Chronographs"

        await interaction.responsd("You now specialize in Chronographs!")

    @discord.ui.button(label="Shields", style=discord.ButtonStyle.primary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        user_stats = self.bot.users_stats[self.uid]
        user_stats["specialization"] = "Shields"

        await interaction.responsd("You now specialize in Shields!")

    @discord.ui.button(label="None", style=discord.ButtonStyle.secondary)
    async def prev_pressed(self, button, interaction):
        if self.uid != str(interaction.user.id):
            await interaction.respond("This isn't your button!", ephemeral=True)
            return

        user_stats = self.bot.users_stats[self.uid]
        user_stats["specialization"] = None

        await interaction.responsd("You are no longer specializing!")


class UserCommands(commands.Cog):
    def __init__(self, bot: MatchmakingBot):
        self.bot = bot


    @discord.slash_command(description="Primer to the bot")
    async def about(self, ctx
    ):
        tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"About This Bot", description = "Welcome to the Rhythm Doctor Program for International Treatments (RD PITS)!\n\
Treating patients from across the globe can require multiple interns at once.\n\
To facilitate this, **Synchronized Operations** (Syncope), designed to synchronize interns with their patients, was created.\n\n\
To begin a treatment session, do `/lobby create`!\n\n\
-# This bot is developed by <@1207345676141465622>, with support from <@758112945636376677> and <@340013796976492552>.\n\
-# Character and artwork by <@201091631795929089>.")

        await ctx.respond(embed=tooltipEmbed)


    @discord.slash_command(description="Upload your \"settings.rdsave\" file, located in the \"User\" directory of your RD installation")
    async def upload_rdsave(self, ctx,
        attachment: discord.Option(Attachment, description="settings.rdsave file")
    ):
        if attachment.filename != "settings.rdsave":
            await ctx.respond(f"`{attachment.filename}` is an invalid file. Make sure it's an `settings.rdsave`!", ephemeral=True)
            return

        uid = str(ctx.user.id)

        file = await attachment.read()
        rdsave = json.loads((file.decode('utf-8-sig')).encode('utf-8'))

        played_levels = []
        for level, rank in rdsave.items():
            is_custom = level.startswith("CustomLevel_") and level.endswith("_normal")
            was_played = rank != "NotFinished"

            if is_custom and was_played:
                level_hash = level[12:-7]
                played_levels.append(level_hash)

        self.bot.users_rdsaves[uid] = played_levels
        self.bot.save_data()

        await ctx.respond("Your save file was updated!", ephemeral=True)


    @discord.slash_command(description="(Use \"/lobby roll\" for lobbies!) Rolls a random level with specified settings")
    async def out_of_lobby_roll(self, ctx,
        peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
        played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
        difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Not Easy', 'Not Very Tough', 'Polarity'], default = 'Any', description = 'Default: Any'),
        tags: discord.Option(discord.SlashCommandOptionType.string, default = '', description = 'List of tags the level must have. Default: None'),
        players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
    ):
        uid = str(ctx.user.id)

        # if user doesn't have an rdsettings
        if uid not in self.bot.users_rdsaves:
            await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use `/upload_rdsave` to do this.)', ephemeral=True)
            return

        if players == None:
            players = '<@'+uid+'>'

        players_id_list = re.findall(r"\<\@(.*?)\>", players) #extract user ids
        players_id_list = list(set(players_id_list)) #remove duplicates

        tags_array = tags.split(',')
        if tags == '':
            tags_array = []

        for i, tag in enumerate(tags_array):
            tags_array[i] = tag.lstrip()

        level_chosen = levels.roll_random_level(peer_reviewed, played_before, difficulty, players_id_list, self.bot.users_rdsaves, tags_array, None, False)

        if level_chosen == None:
            await ctx.respond("No levels found with those arguments!") #intentionally not ephemeral
            return

        level_embed = discord.Embed(colour = discord.Colour.green(), title = f"Here's your level (chosen from {level_chosen['possibilities']} levels):", image = level_chosen['image_url'])

        levels.add_level_to_embed(level_embed, level_chosen)

        await ctx.respond(embed=level_embed)


    @discord.slash_command(description="View your milestones")
    async def achievements(self, ctx,
        user: discord.Option(discord.SlashCommandOptionType.user, required = False, description = '@user to view achievements of. Default: Yourself')
    ):
        if user == None:
            ach_user = ctx.user
        else:
            ach_user = user

        ach_uid = str(ach_user.id)

        achievements_list = self.bot.get_user_achievements(ctx, ach_uid)

        if achievements_list == None:
            if ach_uid == str(ctx.user.id):
                await ctx.respond('You have not played any matches!', ephemeral = True)
            else:
                await ctx.respond('This user has not played any matches!', ephemeral = True)
            return

        tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"{ach_user.global_name}\'s Achievements ({achievements_list['total']}★)", description = achievements_list['message'])
        tooltipEmbed.set_footer(text="Hover over text for info!")

        await ctx.respond(embed=tooltipEmbed)


    @discord.slash_command(description="See the rankings")
    async def leaderboard(self, ctx,
        category: discord.Option(choices = ['exp', '★'], default = 'exp', description = 'Default: exp')
    ):
        uid = str(ctx.user.id)

        leaderboard_embed = misc.get_leaderboard_embed(ctx, self.bot, category, 1)

        await ctx.respond(embed=leaderboard_embed, view=LeaderboardButtons(self.bot, uid, category, 1))


    @discord.slash_command(description="(ADVANCED) Run an admin command.")
    async def admin_command(self, ctx,
        command: discord.Option(discord.SlashCommandOptionType.string)
    ):
        uid = str(ctx.user.id)

        args = command.split()

        if (len(args) == 2) and ((args[0] == "ascension") or (args[0] == "a")) and ((args[1]).isdigit()):
            await self.change_ascension_difficulty(ctx, uid, int(args[1]))
            return

        if (len(args) == 1) and (args[0] == "specialize"):
            await self.specializations(ctx, uid)
            return

        await ctx.respond(f"Invalid command!", ephemeral=True)
        return


    async def change_ascension_difficulty(self, ctx, uid, difficulty):
        if (difficulty < 0) or (difficulty > 6):
            await ctx.respond(f"Invalid certificate!", ephemeral=True)

        user_stats = self.bot.users_stats[uid]

        if user_stats["highest_set_beaten"] < 7:
            await ctx.respond(f"You need to beat Ascension mode as the runner first!", ephemeral=True)

        if user_stats["highest_ascension_difficulty_beaten"]+1 < difficulty:
            await ctx.respond(f"You haven't unlocked that yet!", ephemeral=True)

        user_stats["current_ascension_difficulty"] = difficulty
        await ctx.respond(f"Certificate updated!", ephemeral=True)


    async def specializations(self, ctx, uid):
        user_stats = self.bot.users_stats[uid]

        if user_stats["specialization"] != None:
            ctx.channel.send(user_stats["specialization"])

        #if user_stats["highest_ascension_difficulty_beaten"] < 3:
        #    await ctx.respond(f"You haven't unlocked that yet!", ephemeral=True)

        specializations_embed = discord.Embed(colour = discord.Colour.purple(), title = "Specializations", description = f"Press a button to **specialize** in an item!\nYou are more likely to be offered the item you specialize in.\nAdditionally, you will begin runs with +1 of this item.\n__Specializations only work on Certification 4 or above.__")

        await ctx.respond(embed=specializations_embed, view=SpecializeButtons(self.bot, uid))


def setup(bot: MatchmakingBot):
    cog = UserCommands(bot)
    bot.add_cog(cog)