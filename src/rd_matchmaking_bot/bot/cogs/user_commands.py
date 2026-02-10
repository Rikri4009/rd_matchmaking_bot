import re
import datetime
import math
import json
import os
import discord
from discord import Attachment
from discord.ext import commands
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.ascension as ascension
import rd_matchmaking_bot.utils.misc as misc
import rd_matchmaking_bot.utils.data as data

class LeaderboardButtons(discord.ui.View):
    def __init__(self, bot: MatchmakingBot, uid, category, page):
        super().__init__(timeout=2000)
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


class UserCommands(commands.Cog):
    def __init__(self, bot: MatchmakingBot):
        self.bot = bot


    @discord.slash_command(description="Primer to the bot")
    async def about(self, ctx
    ):
        tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"\⭐ About This Bot \🎵", description = "Welcome to the __sync__hronized __ope__rations program!\n\
Treating patients from across the globe can require multiple interns working at once, which Syncope is designed to streamline.\n\n\
Be warned: You will only be assigned to **all-new treatments** (levels you've never played), so be prepared for anything!\n\n\
To begin a treatment session, do `/lobby create`!\nFor an overview of commands, do `/help`.\n\
Detailed documentation can be found [here](https://docs.google.com/document/d/1llry_KhVjVv7Lg47KqbDUV0BuKHE4mFSsobTcUiV0dI/edit?usp=sharing).\n\n\
-# Direct feedback/bug reports to <@1207345676141465622>.\n\
-# Character and artwork by <@201091631795929089>. Full credits are in the documentation.")

        await ctx.respond(embed=tooltipEmbed, ephemeral=True)


    @discord.slash_command(description="List of commands")
    async def help(self, ctx
    ):
        tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"Commands List",
description = "`/about`: Get an overview of the bot.\n\n\
`/lobby create`: Create a new lobby to start playing levels!\n\
`/lobby resend`: If the bot's buttons stop working, use this command.\n\
`/lobby list_all`: View all current lobbies, and the channels they're located in.\n\
Other lobby commands are explained after you create a lobby.\n\n\
`/quests`: View your daily quests.\n\
`/achievements`: View your overall statistics.\n\
`/player_rating`: Get an estimate of your overall performance.\n\
`/leaderboard`: View the exp or \⭐ leaderboards.\n\n\
`/out_of_lobby_roll`: Find a level for a set of players outside of a lobby.\n\
`/upload_rdsave`: Upload your save data. (See [here](https://docs.google.com/document/d/1llry_KhVjVv7Lg47KqbDUV0BuKHE4mFSsobTcUiV0dI/edit?usp=sharing) for details.)")

        await ctx.respond(embed=tooltipEmbed, ephemeral=True)


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
        tags: discord.Option(discord.SlashCommandOptionType.string, default = '', description = 'List of tags the level must have, comma-separated. Default: None'),
        players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
    ):
        uid = str(ctx.user.id)

        # if user doesn't have an rdsettings
        if uid not in self.bot.users_rdsaves:
            await ctx.respond(misc.get_upload_rdsave_message(), ephemeral=True)
            return

        if players == None:
            players = '<@'+uid+'>'

        players_id_list = re.findall(r"\<\@(.*?)\>", players) #extract user ids
        players_id_list = list(set(players_id_list)) #remove duplicates

        tags_list = tags.split(',')
        if tags == '':
            tags_list = []

        for i, tag in enumerate(tags_list):
            tags_list[i] = tag.lstrip()

        tag_facet_array = []

        for tag in tags_list:
            new_sub_list = {}
            new_sub_list["tags"] = []
            new_sub_list["tags"].append(tag)

            tag_facet_array.append(new_sub_list)

        level_chosen = levels.roll_random_level(peer_reviewed, played_before, difficulty, players_id_list, self.bot.users_rdsaves, tag_facet_array, False, [])

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

        user_stats = self.bot.users_stats[ach_uid]
        achievements_list = self.bot.get_user_achievements(ctx, ach_uid)

        if achievements_list == None:
            if ach_uid == str(ctx.user.id):
                await ctx.respond('You have not played any matches!', ephemeral = True)
            else:
                await ctx.respond('This user has not played any matches!', ephemeral = True)
            return

        total_player_rating = '{:.2f}'.format(self.bot.get_user_ratings(ach_uid)["Total"])

        tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"{ach_user.display_name}\'s Achievements ({achievements_list['total']}\⭐| {user_stats['exp']}\🎵 | {total_player_rating}\🩺)", description = achievements_list['message'])
        tooltipEmbed.set_footer(text="Hover over text for info!")

        await ctx.respond(embed=tooltipEmbed)


    @discord.slash_command(description="See the rankings")
    async def leaderboard(self, ctx,
        category: discord.Option(choices = ['exp', '⭐'], default = 'exp', description = 'Default: exp')
    ):
        uid = str(ctx.user.id)

        leaderboard_embed = misc.get_leaderboard_embed(ctx, self.bot, category, 1)

        await ctx.respond(embed=leaderboard_embed, view=LeaderboardButtons(self.bot, uid, category, 1))


    @discord.slash_command(description="See your Player Rating")
    async def player_rating(self, ctx,
        user: discord.Option(discord.SlashCommandOptionType.user, required = False, description = '@user to view the Player Rating of. Default: Yourself')
    ):
        if user == None:
            rating_user = ctx.user
        else:
            rating_user = user

        rating_uid = str(rating_user.id)

        player_ratings = self.bot.get_user_ratings(rating_uid)
        player_ratings_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"{rating_user.display_name}\'s Player Ratings", description = f"# `Total: {'{:.2f}'.format(player_ratings['Total'])}🩺`\n\n`      Easy: {'{:.2f}'.format(player_ratings['Easy'])}💚`\n`    Medium: {'{:.2f}'.format(player_ratings['Medium'])}💛`\n`     Tough: {'{:.2f}'.format(player_ratings['Tough'])}❤️`\n`Very Tough: {'{:.2f}'.format(player_ratings['Very Tough'])}💜`")
        player_ratings_embed.set_footer(text="Your Player Rating is based on the last 16 levels of each difficulty you\'ve played.\nLevels played with difficulty modifiers (e.g. hard button) don't count.")

        await ctx.respond(embed=player_ratings_embed)


    @discord.slash_command(description="View your quests")
    async def quests(self, ctx
    ):
        uid = str(ctx.user.id)

        self.bot.refresh_eligible_quests(uid)

        est_time = datetime.timezone(-datetime.timedelta(hours=5))
        now = datetime.datetime.now(est_time)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = midnight + datetime.timedelta(days=1)

        quests_text = f"Completed quests will refresh <t:{math.floor(tomorrow.timestamp())}:R>!\n\n"

        user_quests = self.bot.get_user_stat(uid, "quests")

        for i in range(len(user_quests)):
            if user_quests[i]["completion_time"] == None:
                quests_text = quests_text + f"- **Quest {str(i+1)}**: {user_quests[i]['description']} ({user_quests[i]['completion']}/{user_quests[i]['requirement']})\n  - Reward: {user_quests[i]['reward_amount']} {user_quests[i]['reward_description']}"
            else:
                quests_text = quests_text + f"- ~~**Quest {str(i+1)}**: {user_quests[i]['description']} (Completed!)\n  - Reward: {user_quests[i]['reward_amount']} {user_quests[i]['reward_description']}~~"
            
            quests_text = quests_text + "\n"

        quests_embed = discord.Embed(colour = discord.Colour.green(), title = "Daily Quests", description = quests_text)

        await ctx.respond(embed=quests_embed)


    @discord.slash_command(description="(ADVANCED) Run an admin command.")
    async def admin_command(self, ctx,
        command: discord.Option(discord.SlashCommandOptionType.string)
    ):
        uid = str(ctx.user.id)

        args = command.split()

        #if (len(args) == 2) and ((args[0] == "certify") or (args[0] == "a")) and ((args[1]).isdigit()):
        #    await self.change_ascension_difficulty(ctx, uid, int(args[1]))
        #    return

        #if (len(args) == 1) and (args[0] == "specialize"):
        #    await self.specializations(ctx, uid)
        #    return

        if uid == "1207345676141465622":
            if (len(args) == 1) and (args[0] == "get_backups"):
                await self.get_backups(ctx)
                return

            if (len(args) == 1) and (args[0] == "clear_backups"):
                await self.clear_backups(ctx)
                return

            if (len(args) == 2) and (args[0] == "clear_rdsave"):
                await self.clear_rdsave(ctx, args[1])
                return

            if (len(args) == 2) and (args[0] == "clear_stat_from_all_users"):
                await self.clear_stat_from_all_users(ctx, args[1])
                return

            if (len(args) == 4) and (args[0] == "edit_world_tour_run"):
                await self.edit_world_tour_run(ctx, args[1], args[2], args[3])
                return

        await ctx.respond(f"Invalid command!", ephemeral=True)
        return


    async def get_backups(self, ctx):
        path = data.get_path("resources/data")

        await ctx.respond("Backups:", file = discord.File(fp = (path + os.sep + "users_stats_backups.json")))

    async def clear_backups(self, ctx):
        path = data.get_path("resources/data")
        users_stats_backups = data.read_file(path, "users_stats_backups.json")

        users_stats_backups = []

        data.write_json(users_stats_backups, path, "users_stats_backups.json")

        await ctx.respond("Backups cleared.")

    async def clear_rdsave(self, ctx, uid):
        self.bot.users_rdsaves[uid] = []
        self.bot.save_data()

        await ctx.respond("Done!")

    async def clear_stat_from_all_users(self, ctx, stat):
        users_stats = self.bot.users_stats

        for user in users_stats:
            if stat in users_stats[user]:
                del users_stats[user][stat]

        self.bot.validate_users_stats()
        self.bot.save_data()

        await ctx.respond("Done!")

    async def edit_world_tour_run(self, ctx, key, value_type, value):
        uid = str(ctx.user.id)
        game_data = self.bot.game_data
        ascension_lobby = game_data["ascension"][uid]

        if key not in ascension_lobby:
            await ctx.respond("Key not found!")
            return

        if value_type == "int":
            value = int(value)

        ascension_lobby[key] = value
        await ctx.respond("Done!")


def setup(bot: MatchmakingBot):
    cog = UserCommands(bot)
    bot.add_cog(cog)