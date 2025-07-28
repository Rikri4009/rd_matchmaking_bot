import re
import random
import math
import json
import discord
from discord import Attachment
from discord.ext import commands
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.misc as misc

class UserCommands(commands.Cog):
    def __init__(self, bot: MatchmakingBot):
        self.bot = bot


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
            await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use **/upload_rdsettings** to do this.)', ephemeral=True)
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

        level_chosen = levels.roll_random_level(peer_reviewed, played_before, difficulty, players_id_list, self.bot.users_rdsaves, tags_array, None)

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
        unsorted_scores = {}

        if category == 'exp':
            category = ' ' + category
            for uid in self.bot.users_stats:
                if self.bot.users_stats[uid]['exp'] > 0: #remove people with 0 exp
                    unsorted_scores[uid] = self.bot.users_stats[uid]['exp']
        else:
            for uid in self.bot.users_stats:
                user_achievements = self.bot.get_user_achievements(ctx, uid)
                if user_achievements['total'] > 0:
                    unsorted_scores[uid] = user_achievements['total']

        users_places = misc.rank_players(unsorted_scores, True)

        leaderboard_message = ''

        for user in users_places:
            leaderboard_message = leaderboard_message + f"{users_places[user]['text']} ({unsorted_scores[user]}{category}): <@{user}>\n"

        leaderboard_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"{category} Leaderboard", description = leaderboard_message)
        await ctx.respond(embed=leaderboard_embed)


    @discord.slash_command(description="(ADVANCED) Run an admin command.")
    async def admin_command(self, ctx,
        command: discord.Option(discord.SlashCommandOptionType.string)
    ):
        uid = str(ctx.user.id)

        if (command == "endless begin") or (command == "e begin"):
            await self.endless_begin(ctx, uid)
            return
        
        if (command == "endless roll") or (command == "e roll"):
            await self.endless_roll(ctx, uid)
            return

        if (command == "endless already_seen") or (command == "e already_seen"):
            await self.endless_reroll(ctx, uid)
            return

        if (command == "endless recover") or (command == "e recover"):
            await self.endless_recover(ctx, uid)
            return
        
        if (command == "endless forage 1") or (command == "e forage 1"):
            await self.endless_roll_extra(ctx, uid, 1, "Medium")
            return

        if (command == "endless forage 2") or (command == "e forage 2"):
            await self.endless_roll_extra(ctx, uid, 2, "Tough")
            return

        args = command.split()

        if (len(args) == 3) and ((args[0] == "endless") or (args[0] == "e")) and (args[1] == "use"):
            await self.endless_use_item(ctx, uid, args[2])
            return

        if (len(args) == 3) and ((args[0] == "endless") or (args[0] == "e")) and (args[1] == "submit") and ((args[2]).isdigit()):
            await self.endless_submit_misses(ctx, uid, int(args[2]))
            return

        await ctx.respond(f"Invalid command!", ephemeral=True)
        return


    async def endless_begin(self, ctx, player_id):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby["status"] != "Not Started":
            await ctx.respond("You have already started climbing!", ephemeral=True)
            return

        achievement_count = (self.bot.get_user_achievements(ctx, player_id))["total"]
        endless_lobby["max_hp"] = achievement_count
        endless_lobby["current_hp"] = achievement_count
        endless_lobby["shields_used"] = 0
        endless_lobby["chronograph_used"] = False

        endless_lobby["current_set"] = 1
        endless_lobby["level_number"] = 0

        endless_lobby["items"]["Ivory Dice"] = 1
        endless_lobby["items"]["Apples"] = 0
        endless_lobby["items"]["Shields"] = 0
        endless_lobby["items"]["Chronographs"] = 0

        endless_lobby["extra"] = 0

        self.bot.save_data()

        await self.endless_begin_set(ctx, player_id)


    async def endless_begin_set(self, ctx, player_id):
        endless_lobby = self.bot.game_data["endless"][player_id]
        sets_config = self.bot.get_sets_config()
        set_number = str(endless_lobby['current_set'])

        set_difficulties = sets_config[set_number]['difficulties']

        endless_lobby['status'] = 'Started'

        endless_lobby["extra"] = 0

        set_theme = 'None'
        if len(sets_config[set_number]['theme']) != 0:
            set_theme = random.choice(sets_config[set_number]['theme'])
        endless_lobby['set_theme'] = set_theme

        set_modifier = 'None'
        if len(sets_config[set_number]['modifier']) != 0:
            set_modifier = random.choice(sets_config[set_number]['modifier'])
        endless_lobby['set_modifier'] = set_modifier

        endless_lobby['roll_tags'] = sets_config[set_theme]['tags'] + sets_config[set_modifier]['tags']
        endless_lobby['roll_facets'] = sets_config[set_theme]['facets'] | sets_config[set_modifier]['facets']

        if set_modifier != 'None':
            set_difficulties = sets_config[set_modifier]['diff_override']

        endless_lobby['set_difficulties'] = set_difficulties

        endless_lobby["chosen_item_1"] = None
        endless_lobby["chosen_item_2"] = None

        self.bot.save_data()

        await self.endless_show_status(ctx, player_id)


    async def endless_show_status(self, ctx, player_id):
        endless_lobby = self.bot.game_data["endless"][player_id]
        sets_config = self.bot.get_sets_config()
        set_number = endless_lobby['current_set']
        level_number = endless_lobby['level_number']

        theme_and_modifier_desc = ""

        set_theme = endless_lobby['set_theme']
        set_modifier = endless_lobby['set_modifier']

        if set_theme != "None":
            theme_and_modifier_desc = theme_and_modifier_desc + f"Set Theme: **{set_theme}**\n{sets_config[set_theme]['description']}\n\n"

        if set_modifier != "None":
            theme_and_modifier_desc = theme_and_modifier_desc + f"Set Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"

        set_difficulties_bold = (endless_lobby['set_difficulties']).copy()
        set_difficulties_bold[level_number] = "**" + set_difficulties_bold[level_number] + "**"
        set_difficulties_text = ' -> '.join(set_difficulties_bold)

        current_items = endless_lobby["items"]
        items_text = "*Your items (hover for info):*\n"

        if current_items["Ivory Dice"] > 0:
            items_text = items_text + f":game_die: [Ivory Dice]({ctx.channel.jump_url} \"After playing a level, INSTEAD OF submitting, use this item to reroll it\")"
            items_text = items_text + " x" + str(current_items["Ivory Dice"]) + "\n"
        if current_items["Apples"] > 0:
            items_text = items_text + f":apple: [Apples]({ctx.channel.jump_url} \"After playing a level, BEFORE submitting, use this item to recover 7 HP\")"
            items_text = items_text + " x" + str(current_items["Apples"]) + "\n"
        if current_items["Shields"] > 0:
            items_text = items_text + f":shield: [Shields]({ctx.channel.jump_url} \"After playing a level, BEFORE submitting, use this item to halve damage taken\")"
            items_text = items_text + " x" + str(current_items["Shields"]) + "\n"
        if current_items["Chronographs"] > 0:
            items_text = items_text + f":stopwatch: [Chronographs]({ctx.channel.jump_url} \"After playing a level, BEFORE submitting, use this item to REPLAY the level for a better score\")"
            items_text = items_text + " x" + str(current_items["Chronographs"]) + "\n"

        if items_text == "*Your items (hover for info):*\n":
            items_text = ""
        else:
            items_text = items_text + "\n"

        set_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Lobby: \"`   ` `     `\" | SET {set_number}", description = f"Player: <@{player_id}> ({endless_lobby['current_hp']}/{endless_lobby['max_hp']} HP)\n\n\
{items_text}Levels: {set_difficulties_text}\n\n{theme_and_modifier_desc}When you're ready, type \"**/admin_command endless roll**\".")
        await ctx.respond(embed = set_embed)


    async def endless_roll(self, ctx, player_id):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        set_number = endless_lobby['current_set']
        level_number = endless_lobby['level_number']

        if endless_lobby['status'] == 'Not Started':
            await ctx.respond("You have not yet started climbing!", ephemeral=True)
            return
        elif endless_lobby['status'] == 'Rolled':
            await ctx.respond("You have already rolled a level!", ephemeral=True)
            return
        elif endless_lobby['status'] == 'Choice':
            await ctx.respond("Choose an item stupid") #wanna see if anyone does this so not ephemeral
            return

        endless_lobby['status'] = 'Rolled'

        level_chosen = levels.roll_random_level("Yes", "No", endless_lobby['set_difficulties'][level_number], [player_id], self.bot.users_rdsaves, endless_lobby['roll_tags'], endless_lobby['roll_facets'])

        if level_chosen == None:
            await ctx.respond("HUGE MISTAKE ping me lol")
            return

        set_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Lobby: \"`   ` `     `\" | SET {set_number}", description = f"Player: <@{player_id}> ({endless_lobby['current_hp']}/{endless_lobby['max_hp']} HP)\n\n\
If you recognize this level, type \"**/admin_command endless already_seen**\".\n\
To use an item, type \"**/admin_command endless use [item name]**\".\n\
To submit your miss count, type \"**/admin_command endless submit [miss count]**\".", image = level_chosen['image_url'])
        levels.add_level_to_embed(set_embed, level_chosen)
        await ctx.respond(embed = set_embed)

        self.bot.save_data()


    async def endless_reroll(self, ctx, player_id):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby["status"] != "Rolled":
            await ctx.respond("A level has not been rolled!", ephemeral=True)
            return

        endless_lobby["status"] = "Started"

        await self.endless_roll(ctx, player_id)


    async def endless_use_item(self, ctx, player_id, item):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby['status'] != 'Rolled':
            await ctx.respond("Items should be used after a level is rolled and before submitting!", ephemeral=True)
            return

        item = item.lower()

        if (item == "ivory") or (item == "die") or (item == "dice"):
            if endless_lobby["items"]["Ivory Dice"] < 1:
                await ctx.respond("You don't have any Ivory Dice!") #not ephemeral on purpose
                return

            endless_lobby["items"]["Ivory Dice"] = endless_lobby["items"]["Ivory Dice"] - 1
            endless_lobby["chronograph_used"] = False #since chronographed level was rerolled
            await ctx.channel.send("Ivory Die used!")
            await self.endless_reroll(ctx, player_id)
            return

        if (item == "apples") or (item == "apple") or (item == "pineapples") or (item == "pineapple"):
            if endless_lobby["items"]["Apples"] < 1:
                await ctx.respond("You don't have any Pineapples! I mean Apples!")
                return

            endless_lobby["items"]["Apples"] = endless_lobby["items"]["Apples"] - 1
            endless_lobby["current_hp"] = endless_lobby["current_hp"] + 7
            if endless_lobby["current_hp"] > endless_lobby["max_hp"]: #clamp to max
                endless_lobby["current_hp"] = endless_lobby["max_hp"]
            await ctx.respond("Apple eaten!")
            return

        if (item == "shields") or (item == "shield"):
            if endless_lobby["items"]["Shields"] < 1:
                await ctx.respond("You don't have any Shields!")
                return

            endless_lobby["items"]["Shields"] = endless_lobby["items"]["Shields"] - 1
            endless_lobby["shields_used"] = endless_lobby["shields_used"] + 1
            await ctx.respond("Shield used!")
            return

        if (item == "chronographs") or (item == "chronograph"):
            if endless_lobby["items"]["Chronographs"] < 1:
                await ctx.respond("You don't have any Chronographs!")
                return

            endless_lobby["items"]["Chronographs"] = endless_lobby["items"]["Chronographs"] - 1
            endless_lobby["chronograph_used"] = True
            await ctx.respond("Chronograph used!")
            return

        await ctx.respond("That item doesn't exist!", ephemeral=True)
        return


    async def endless_submit_misses(self, ctx, player_id, miss_count):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby["status"] != "Rolled":
            await ctx.respond("A level has not been rolled!", ephemeral=True)
            return

        if endless_lobby["shields_used"]:
            endless_lobby["current_hp"] = endless_lobby["current_hp"] - (miss_count // (2 ** endless_lobby["shields_used"]))
            endless_lobby["shields_used"] = 0
        else:
            endless_lobby["current_hp"] = endless_lobby["current_hp"] - miss_count

        if endless_lobby["current_hp"] <= 0:
            await ctx.respond("You have died! Game over!")
            endless_lobby["status"] = "Not Started"
            self.bot.save_data()
            return

        player_stats = self.bot.users_stats[player_id]

        player_stats['exp'] = player_stats['exp'] + 5

        set_difficulty = endless_lobby["set_difficulties"][endless_lobby["level_number"]]
        if miss_count == 0:
            if endless_lobby["chronograph_used"] == False:
                if set_difficulty == 'Easy':
                    player_stats['easy_s_ranked'] = player_stats['easy_s_ranked'] + 1
                elif set_difficulty == 'Medium':
                    player_stats['medium_s_ranked'] = player_stats['medium_s_ranked'] + 1
                elif set_difficulty == 'Tough':
                    player_stats['tough_s_ranked'] = player_stats['tough_s_ranked'] + 1
                elif set_difficulty == 'Very Tough':
                    player_stats['vt_s_ranked'] = player_stats['vt_s_ranked'] + 1
                else:
                    print("HUGE ISSUE IN DIFF")

                if (set_difficulty == 'Tough') or (set_difficulty == 'Very Tough'):
                    if (endless_lobby["set_modifier"] == "Hard Difficulty Button") or (endless_lobby["set_modifier"] == "2-Player"): #todo
                        player_stats['tough_plus_s_ranked_modifier'] = player_stats['tough_plus_s_ranked_modifier'] + 1
            else: #chronograph used
                player_stats["s_ranked_with_chronograph"] = player_stats["s_ranked_with_chronograph"] + 1

        # not the last level: advance to next level in set
        if endless_lobby["level_number"] < len(endless_lobby["set_difficulties"]) - 1:
            endless_lobby["level_number"] = endless_lobby["level_number"] + 1
            endless_lobby["status"] = "Started"
            self.bot.save_data()
            await self.endless_show_status(ctx, player_id)
            return

        # is the last level but not the last set: offer item
        if endless_lobby["current_set"] < 5:
            player_stats = self.bot.users_stats[player_id]

            if endless_lobby["extra"] == 0:
                player_stats["exp"] = player_stats["exp"] + (10 * endless_lobby["current_set"])
                player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], endless_lobby["current_set"])
                player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

                endless_lobby["level_number"] = endless_lobby["level_number"] + 1
                item_list = ["Ivory Dice", "Apples", "Shields", "Chronographs"]
                endless_lobby["chosen_item_1"] = random.choice(item_list)
                item_list.remove(endless_lobby["chosen_item_1"])
                endless_lobby["chosen_item_2"] = random.choice(item_list)
                endless_lobby["status"] = "Choice"

                await ctx.respond(f"You have beaten this set and have {endless_lobby['current_hp']}/{endless_lobby['max_hp']} HP!\n\
You can choose to \"**/admin_command endless recover**\" 2/3rds of your missing HP now...\n\
Or, you can first play an extra Medium this set to also \"**/admin_command endless forage 1**\" __{endless_lobby['chosen_item_1']}__...\n\
Or, you can play an extra Tough to \"**/admin_command endless forage 2**\" __{endless_lobby['chosen_item_2']}__.")
                self.bot.save_data()
                return

            else:
                endless_lobby["status"] = "Choice"
                await self.endless_forage(ctx, player_id, endless_lobby["extra"])
                return

        # is the last set:
        player_stats = self.bot.users_stats[player_id]
        player_stats["exp"] = player_stats["exp"] + 70
        player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], endless_lobby["current_set"])
        player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

        await ctx.respond(f"Congratulations on beating the beta test!!! Sorry no cool rewards yet\n\
You ended with {endless_lobby['current_hp']}/{endless_lobby['max_hp']} HP btw")
        endless_lobby["status"] = "Not Started"
        self.bot.save_data()


    async def endless_roll_extra(self, ctx, player_id, number, difficulty):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby["status"] != "Choice":
            await ctx.respond("You haven't been offered a choice yet! Bozo") #ephemeral
            return

        (endless_lobby["set_difficulties"]).append(difficulty)
        endless_lobby["extra"] = number

        endless_lobby["status"] = "Started"

        await self.endless_roll(ctx, player_id)


    async def endless_recover(self, ctx, player_id):
        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            await ctx.respond("You need to join `   ` `     ` first!", ephemeral=True)
            return

        endless_lobby = endless_lobbies[player_id]

        if endless_lobby["status"] != "Choice":
            await ctx.respond("You haven't been offered a choice yet! Bozo") #ephemeral
            return

        # recover 2/3rds of missing hp
        endless_lobby["current_hp"] = math.ceil((2*endless_lobby["max_hp"] + endless_lobby["current_hp"]) / 3)

        # progress set
        endless_lobby["current_set"] = endless_lobby["current_set"] + 1
        endless_lobby["level_number"] = 0

        await self.endless_begin_set(ctx, player_id)


    async def endless_forage(self, ctx, player_id, number):
        endless_lobbies = self.bot.game_data["endless"]

        endless_lobby = endless_lobbies[player_id]

        # get the item
        chosen_item = endless_lobby["chosen_item_1"]
        if number == 2:
            chosen_item = endless_lobby["chosen_item_2"]
        endless_lobby["items"][chosen_item] = endless_lobby["items"][chosen_item] + number

        await self.endless_recover(ctx, player_id)


def setup(bot: MatchmakingBot):
    cog = UserCommands(bot)
    bot.add_cog(cog)