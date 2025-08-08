import discord
import random
import math
import rd_matchmaking_bot.utils.levels as levels

class AscensionButtonsWelcome(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        if game_data["ascension"][self.runner_id]["status"] == "Not Started":
            await interaction.respond("You haven't started climbing yet!", ephemeral=True)
            return

        # note that the ascension data's status will never be rolling or playing, so no need to copy over level
        game_data["lobbies"][self.lobby_name]["status"] = game_data["ascension"][self.runner_id]["status"]

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)

    @discord.ui.button(label="New Game", style=discord.ButtonStyle.danger)
    async def newgame_pressed(self, button, interaction):
        self.stop()

        begin(self.lobbycommands, interaction, self.runner_id, None, self.lobby_name)
        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)


class AscensionButtonsItem(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Apple", style=discord.ButtonStyle.secondary)
    async def apple_pressed(self, button, interaction):
        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Apples"] < 1:
            await interaction.respond("You don't have any Pineapples! I mean Apples!")
            return

        ascension_lobby["items"]["Apples"] = ascension_lobby["items"]["Apples"] - 1
        ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + 7
        if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]: #clamp to max
            ascension_lobby["current_hp"] = ascension_lobby["max_hp"]
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Apple eaten!")

    @discord.ui.button(label="Ivory Die", style=discord.ButtonStyle.secondary)
    async def die_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Ivory Dice"] < 1:
            await interaction.respond("You don't have any Ivory Dice!") #not ephemeral on purpose
            return

        ascension_lobby["items"]["Ivory Dice"] = ascension_lobby["items"]["Ivory Dice"] - 1
        ascension_lobby["die_used"] = True
        await interaction.channel.send("Ivory Die used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Chronograph", style=discord.ButtonStyle.secondary)
    async def chronograph_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Chronographs"] < 1:
            await interaction.respond("You don't have any Chronographs!")
            return

        ascension_lobby["items"]["Chronographs"] = ascension_lobby["items"]["Chronographs"] - 1
        ascension_lobby["chronograph_used"] = True #this gets checked in roll_level_from_settings, and is set off in finish_match
        await interaction.channel.send("Chronograph used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Shield", style=discord.ButtonStyle.secondary)
    async def shield_pressed(self, button, interaction):
        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Shields"] < 1:
            await interaction.respond("You don't have any Shields!")
            return

        ascension_lobby["items"]["Shields"] = ascension_lobby["items"]["Shields"] - 1
        ascension_lobby["shields_used"] = ascension_lobby["shields_used"] + 1
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Shield used!")

    @discord.ui.button(label="Use SP", style=discord.ButtonStyle.primary)
    async def sp_pressed(self, button, interaction):
        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["current_sp"] < 10:
            await interaction.respond("You don't have enough SP!")
            return

        ascension_lobby["sp_spent"] = ascension_lobby["sp_spent"] + max(10, ascension_lobby["current_sp"]/2)
        ascension_lobby["current_sp"] = ascension_lobby["current_sp"] - max(10, ascension_lobby["current_sp"]/2)
        ascension_lobby["sp_times_used"] = ascension_lobby["sp_times_used"] + 1
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond(f"{max(10, ascension_lobby['current_sp']/2)} SP used!")
        return

    @discord.ui.button(label="Proceed", style=discord.ButtonStyle.success)
    async def proceed_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        await proceed_helper(self, interaction)


async def proceed_helper(self, interaction):
    game_data = self.lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][self.runner_id]

    lobby_name_user_is_hosting = self.lobbycommands.bot.lobby_name_user_is_hosting(self.runner_id)
    auxiliary_lobby = game_data["lobbies"][lobby_name_user_is_hosting]

    if ascension_lobby["die_used"] or ascension_lobby["chronograph_used"]: #if rerolling, refund used items, and take no damage
        ascension_lobby["items"]["Shields"] = ascension_lobby["items"]["Shields"] + ascension_lobby["shields_used"]
        ascension_lobby["current_sp"] = ascension_lobby["current_sp"] + ascension_lobby["sp_spent"]
        ascension_lobby["incoming_damage"] = 0
    else:
        ascension_lobby["incoming_damage"] = calculate_item_applied_incoming_damage(ascension_lobby) #apply items to incoming damage

    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - ascension_lobby["incoming_damage"]

    ascension_lobby["die_used"] = False
    ascension_lobby["shields_used"] = 0
    ascension_lobby["sp_spent"] = 0

    # died: game over
    if ascension_lobby["current_hp"] <= 0:
        ascension_lobby["status"] = "Game Over"
        auxiliary_lobby["status"] = "Game Over"
        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
        self.lobbycommands.bot.save_data()
        return

    # not the last level: advance to next level in set
    if ascension_lobby["level_number"] < len(ascension_lobby["set_difficulties"]) - 1:
        ascension_lobby["level_number"] = ascension_lobby["level_number"] + 1
        ascension_lobby["status"] = "Open"
        auxiliary_lobby["status"] = "Open"
        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
        self.lobbycommands.bot.save_data()
        return

    # if last level

    player_stats = self.lobbycommands.bot.users_stats[self.runner_id]
    gained_exp = 5 * ascension_lobby["current_set"]
    player_stats["exp"] = player_stats["exp"] + gained_exp

    if ascension_lobby["s_ranked_so_far"]:
        player_stats["s_ranked_entire_set"] = player_stats["s_ranked_entire_set"] + 1

    # is the last level but not the last set:
    if ascension_lobby["current_set"] < 6:

        num_items_to_forage = ascension_lobby["extra"]

        if num_items_to_forage == 0: #offer item
            player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], ascension_lobby["current_set"])
            player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

            ascension_lobby["level_number"] = ascension_lobby["level_number"] + 1
            item_list = ["Ivory Dice", "Apples", "Shields", "Chronographs"]
            ascension_lobby["chosen_item_1"] = random.choice(item_list)
            item_list.remove(ascension_lobby["chosen_item_1"])
            ascension_lobby["chosen_item_2"] = random.choice(item_list)
            ascension_lobby["status"] = "Choice"
            auxiliary_lobby["status"] = "Choice"

            await interaction.response.defer()
            await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
            self.lobbycommands.bot.save_data()
            return

        else: #don't offer
            ascension_lobby["status"] = "Open"
            auxiliary_lobby["status"] = "Open"
            chosen_item = ascension_lobby["chosen_item_1"]
            if num_items_to_forage == 2:
                chosen_item = ascension_lobby["chosen_item_2"]
            ascension_lobby["items"][chosen_item] = ascension_lobby["items"][chosen_item] + num_items_to_forage
            await recover_helper(self, interaction)
            return

    # is the last set:
    player_stats = self.bot.users_stats[self.runner_id]
    player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], ascension_lobby["current_set"])
    player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

    #await ctx.respond(f"Congratulations on beating the beta test!!! Sorry no cool rewards yet\n\
    #You ended with {endless_lobby['current_hp']}/{endless_lobby['max_hp']} HP btw")
    ascension_lobby["status"] = "Not Started"
    auxiliary_lobby["status"] = "Not Started"
    self.bot.save_data()


class AscensionButtonsChoice(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Recover", style=discord.ButtonStyle.success)
    async def recover_pressed(self, button, interaction):
        self.stop()

        await recover_helper(self, interaction)
        self.lobbycommands.bot.save_data()

    @discord.ui.button(label="Forage 1", style=discord.ButtonStyle.primary)
    async def forage1_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]
        auxiliary_lobby = game_data["lobbies"][self.lobby_name]

        (ascension_lobby["set_difficulties"]).append("Medium")
        ascension_lobby["extra"] = 1

        ascension_lobby["status"] = "Open"
        auxiliary_lobby["status"] = "Open"

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
        self.lobbycommands.bot.save_data()

    @discord.ui.button(label="Forage 2", style=discord.ButtonStyle.danger)
    async def forage2_pressed(self, button, interaction):
        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]
        auxiliary_lobby = game_data["lobbies"][self.lobby_name]

        (ascension_lobby["set_difficulties"]).append("Tough")
        ascension_lobby["extra"] = 2

        ascension_lobby["status"] = "Open"
        auxiliary_lobby["status"] = "Open"

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
        self.lobbycommands.bot.save_data()


async def recover_helper(self, interaction):
    game_data = self.lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][self.runner_id]

    # recover 2/3rds of missing hp
    ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((2*ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 3))

    # progress set
    ascension_lobby["current_set"] = ascension_lobby["current_set"] + 1
    ascension_lobby["level_number"] = 0

    begin_set(self.lobbycommands, self.runner_id, self.lobby_name)
    await interaction.response.defer()
    await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
    self.lobbycommands.bot.save_data()


class AscensionButtonsGameOver(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="New Game", style=discord.ButtonStyle.success)
    async def newgame_pressed(self, button, interaction):
        self.stop()
        await AscensionButtonsWelcome.newgame_pressed(self, button, interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def newgame_pressed(self, button, interaction):
        self.stop()
        await self.lobbycommands.delete(self.lobbycommands, interaction)


def get_ascension_welcome_embed(self, name, runner_id):
    ascension_lobbies = self.bot.game_data["ascension"]

    if runner_id not in ascension_lobbies:
        ascension_lobbies[runner_id] = {}
        ascension_lobbies[runner_id]["status"] = "Not Started"
        self.bot.validate_game_data()
        self.bot.save_data()

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{name}\"", description = f"Runner: <@{runner_id}>\n\n\
    Welcome to Ascension!\n\
Your goal is to play levels to reach `   ` `     ` at the end of Set 7.\n\
You, the **runner**, start with ★ HP, and will lose 1 for each miss.\n\
Other players are **support**, and will earn SP for you through good performance.\n\
\nYour progress will save, even if you delete the lobby.\n\
Only when you reach 0 HP will you fall back to the beginning.")


def begin(self, ctx, runner_id, max_hp, lobby_name):
    ascension_lobby = self.bot.game_data["ascension"][runner_id]

    ascension_lobby["ascension"] = 0

    achievement_count = (self.bot.get_user_achievements(ctx, runner_id))["total"]

    ascension_lobby["max_hp"] = achievement_count
    ascension_lobby["current_hp"] = achievement_count

    if max_hp != None:
        ascension_lobby["max_hp"] = max_hp
        ascension_lobby["current_hp"] = max_hp

    ascension_lobby["current_sp"] = 0
    ascension_lobby["sp_times_used"] = 0
    ascension_lobby["sp_spent"] = 0

    ascension_lobby["incoming_damage"] = 0
    ascension_lobby["shields_used"] = 0
    ascension_lobby["die_used"] = False
    ascension_lobby["chronograph_used"] = False

    ascension_lobby["current_set"] = 1
    ascension_lobby["level_number"] = 0

    ascension_lobby["items"]["Apples"] = 0
    ascension_lobby["items"]["Ivory Dice"] = 1
    ascension_lobby["items"]["Chronographs"] = 0
    ascension_lobby["items"]["Shields"] = 0

    ascension_lobby["extra"] = 0

    self.bot.save_data()

    begin_set(self, runner_id, lobby_name)


def begin_set(self, player_id, lobby_name):
    endless_lobby = self.bot.game_data["ascension"][player_id]
    auxiliary_lobby = self.bot.game_data["lobbies"][lobby_name]
    sets_config = self.bot.get_sets_config()
    set_number = str(endless_lobby['current_set'])

    set_difficulties = sets_config[set_number]['difficulties']

    endless_lobby['status'] = 'Open'
    auxiliary_lobby['status'] = 'Open'

    endless_lobby["extra"] = 0
    endless_lobby["s_ranked_so_far"] = True

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


def get_ascension_open_embed(lobbycommands, ctx, lobby_name, runner_id, players_id_dict):
    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    sets_config = lobbycommands.bot.get_sets_config()
    set_number = ascension_lobby['current_set']
    level_number = ascension_lobby['level_number']

    theme_and_modifier_desc = ""

    set_theme = ascension_lobby['set_theme']
    set_modifier = ascension_lobby['set_modifier']

    if set_theme != "None":
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Theme: **{set_theme}**\n{sets_config[set_theme]['description']}\n\n"

    if set_modifier != "None":
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"

    set_difficulties_bold = (ascension_lobby['set_difficulties']).copy()
    set_difficulties_bold[level_number] = "**" + set_difficulties_bold[level_number] + "**"
    set_difficulties_text = ' -> '.join(set_difficulties_bold)

    items_text = get_current_items_text(ctx, ascension_lobby)

    support_list = []
    for id in players_id_dict:
        support_list.append('<@' + id + '>')

    support_list.remove(f"<@{runner_id}>") #will always be included bc ascension

    support = ', '.join(support_list)

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
{items_text}Levels: {set_difficulties_text}\n\n{theme_and_modifier_desc}Do `/lobby roll` to proceed!\n\nSupport: {support}")


def set_roll_settings(lobbycommands, lobby_name, runner_id):
    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    auxiliary_lobby = lobbycommands.bot.game_data["lobbies"][lobby_name]

    level_number = ascension_lobby["level_number"]

    roll_settings = auxiliary_lobby["roll_settings"]

    roll_settings["peer_reviewed"] = "Yes"
    roll_settings["played_before"] = "No"
    roll_settings["difficulty"] = ascension_lobby["set_difficulties"][level_number]
    roll_settings["tags"] = ascension_lobby["roll_tags"]
    roll_settings["facets"] = ascension_lobby["roll_facets"]
    roll_settings["require_gameplay"] = True


def get_ascension_rolling_embed(lobbycommands, lobby_name, runner_id, player_id_dict, level_chosen, ascension_lobby):
    ready_list = ''

    for id in player_id_dict:
        ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    sets_config = lobbycommands.bot.get_sets_config()
    set_modifier = ascension_lobby["set_modifier"]

    modifier_text = ''
    if set_modifier != "None":
        modifier_text = f"Set Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
{modifier_text}Make sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, press \"**Ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}", image = level_chosen['image_url'])
    levels.add_level_to_embed(level_embed, level_chosen)
    return level_embed


def get_ascension_item_embed(ctx, lobby_name, runner_id, ascension_lobby):
    items_text = get_current_items_text(ctx, ascension_lobby)

    sp_cost = max(10, ascension_lobby["current_sp"]/2)

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
You are about to take {calculate_item_applied_incoming_damage(ascension_lobby)} damage!\n\
Press the corresponding button below to use an item.\n\n\
{items_text}Press \"**Use SP**\" to spend {sp_cost} SP to reduce incoming damage by 5. (This is more expensive if you have a lot of SP!)")
    return level_embed


def get_ascension_choice_embed(lobby_name, runner_id, ascension_lobby):
    forage_1_difficulty = "Medium"
    forage_2_difficulty = "Tough"

    gained_exp = 5 * ascension_lobby["current_set"]

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have beaten this set and have {ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP!\n\
You have also gained {gained_exp} additional exp.\n\n\
You can choose to **recover** 2/3rds of your missing HP now...\n\
Or, you can first play an extra {forage_1_difficulty} this set to also **forage 1** __{ascension_lobby['chosen_item_1']}__ then recover...\n\
Or, you can play an extra {forage_2_difficulty} to **forage 2** __{ascension_lobby['chosen_item_2']}__ then recover.")
    return level_embed


def get_ascension_gameover_embed(lobby_name, runner_id, ascension_lobby):
    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have run out of HP! GAME OVER!\n\n\
Press **New Game** to try again, or press **Delete** to delete this lobby.")
    return level_embed


def get_current_items_text(ctx, ascension_lobby):
    current_items = ascension_lobby["items"]
    items_text = "*Your items (hover for info):*\n"

    if current_items["Apples"] > 0:
        items_text = items_text + f":apple: [Apples]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to recover 7 HP\")"
        items_text = items_text + " x" + str(current_items["Apples"]) + "\n"
    if current_items["Ivory Dice"] > 0:
        items_text = items_text + f":game_die: [Ivory Dice]({ctx.channel.jump_url} \"After playing a level, INSTEAD OF taking damage, use this item to reroll it\")"
        items_text = items_text + " x" + str(current_items["Ivory Dice"]) + "\n"
    if current_items["Chronographs"] > 0:
        items_text = items_text + f":stopwatch: [Chronographs]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to REPLAY the level for a better score\")"
        items_text = items_text + " x" + str(current_items["Chronographs"]) + "\n"
    if current_items["Shields"] > 0:
        items_text = items_text + f":shield: [Shields]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to halve incoming damage\")"
        items_text = items_text + " x" + str(current_items["Shields"]) + "\n"

    if items_text == "*Your items (hover for info):*\n":
        items_text = ""
    else:
        items_text = items_text + "\n"

    return items_text


def calculate_sp(runner_misses, support_misses):
    if support_misses * 2 <= runner_misses+1:
        return 5
    elif support_misses * 1.5 <= runner_misses+1:
        return 4
    elif support_misses <= runner_misses+1:
        return 3
    elif support_misses * 0.5 <= runner_misses+1:
        return 2
    else:
        return 1


def calculate_item_applied_incoming_damage(ascension_lobby):
    applied_incoming_damage = ascension_lobby["incoming_damage"]

    # use shields
    applied_incoming_damage = applied_incoming_damage // (2 ** ascension_lobby["shields_used"])
    # use sp
    applied_incoming_damage = applied_incoming_damage - (5 * ascension_lobby["sp_times_used"])

    applied_incoming_damage = max(0, applied_incoming_damage)

    return applied_incoming_damage