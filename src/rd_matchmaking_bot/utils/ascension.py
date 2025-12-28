import discord
import random
import math
import copy
import rd_matchmaking_bot.utils.levels as levels

class AscensionButtonsWelcome(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        if game_data["ascension"][self.runner_id]["status"] == "Not Started":
            await interaction.respond("You haven't started a run yet!", ephemeral=True)
            return

        # note that the ascension data's status will never be rolling or playing, so no need to copy over level
        game_data["lobbies"][self.lobby_name]["status"] = game_data["ascension"][self.runner_id]["status"]

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)

    @discord.ui.button(label="New Game", style=discord.ButtonStyle.danger)
    async def newgame_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        runner_stats = self.lobbycommands.bot.users_stats[uid]
        ascension_difficulty = runner_stats["current_ascension_difficulty"]
        runner_tickets = runner_stats["current_tickets"]

        if (ascension_difficulty >= 1) and (runner_tickets < 1):
            await interaction.respond("You don't have any tickets!", ephemeral=True)
            return

        self.stop()

        if ascension_difficulty >= 1:
            runner_stats["current_tickets"] = runner_stats["current_tickets"] - 1

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
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Apples"] < 1:
            await interaction.respond("You don't have any Pineapples! I mean Apples!")
            return

        #if ascension_lobby["ascension_difficulty"] >= 1:
        #    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

        ascension_lobby["items"]["Apples"] = ascension_lobby["items"]["Apples"] - 1
        ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + get_apple_heal_amount(ascension_lobby)
        #if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]: #clamp to max
        #    ascension_lobby["current_hp"] = ascension_lobby["max_hp"]

        if self.runner_id == "539019682968240128":
            ascension_lobby["current_hp"] = 0
            await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
            ascension_lobby["status"] = "Game Over"
            game_data["lobbies"][self.lobby_name]["status"] = "Game Over"
            await interaction.respond("Apple eaten!")
            await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction)
            return

        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Apple eaten!")

    @discord.ui.button(label="Ivory Die", style=discord.ButtonStyle.secondary)
    async def die_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Ivory Dice"] < 1:
            await interaction.respond("You don't have any Ivory Dice!") #not ephemeral on purpose
            return

        #if ascension_lobby["ascension_difficulty"] >= 1:
        #    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

        ascension_lobby["items"]["Ivory Dice"] = ascension_lobby["items"]["Ivory Dice"] - 1
        ascension_lobby["die_used"] = True
        await interaction.channel.send("Ivory Die used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Chronograph", style=discord.ButtonStyle.secondary)
    async def chronograph_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Chronographs"] < 1:
            await interaction.respond("You don't have any Chronographs!")
            return

        #if ascension_lobby["ascension_difficulty"] >= 1:
        #    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

        ascension_lobby["items"]["Chronographs"] = ascension_lobby["items"]["Chronographs"] - 1
        ascension_lobby["chronograph_used"] = True #this gets checked in roll_level_from_settings, and is set off in finish_match
        await interaction.channel.send("Chronograph used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Shield", style=discord.ButtonStyle.secondary)
    async def shield_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Shields"] < 1:
            await interaction.respond("You don't have any Shields!")
            return

        # don't take 2hp yet, only on shield activation

        ascension_lobby["items"]["Shields"] = ascension_lobby["items"]["Shields"] - 1
        ascension_lobby["shields_used"] = ascension_lobby["shields_used"] + 1
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Shield used!")

    @discord.ui.button(label="Use SP", style=discord.ButtonStyle.primary)
    async def sp_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["current_sp"] < 5:
            await interaction.respond("You don't have enough SP!")
            return

        await interaction.respond(f"{max(5, ascension_lobby['current_sp'] // 2)} SP used!")

        ascension_lobby["sp_spent"] = ascension_lobby["sp_spent"] + max(5, ascension_lobby["current_sp"] // 2)
        ascension_lobby["current_sp"] = ascension_lobby["current_sp"] - max(5, ascension_lobby["current_sp"] // 2)
        ascension_lobby["sp_times_used"] = ascension_lobby["sp_times_used"] + 1
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        return

    @discord.ui.button(label="Proceed", style=discord.ButtonStyle.success)
    async def proceed_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()
        await proceed_helper(self, interaction)


def is_last_set(ascension_lobby):
    if (ascension_lobby["ascension_difficulty"] == 0) and (ascension_lobby["current_set"] >= 5):
        return True
    elif (ascension_lobby["ascension_difficulty"] == 1) and (ascension_lobby["current_set"] >= 6):
        return True
    elif (ascension_lobby["ascension_difficulty"] == 2) and (ascension_lobby["current_set"] >= 7):
        return True
    elif ascension_lobby["current_set"] >= 7: #replace with 8
        return True
    else:
        return False


async def proceed_helper(self, interaction):
    game_data = self.lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][self.runner_id]

    lobby_name_user_is_hosting = self.lobbycommands.bot.lobby_name_user_is_hosting(self.runner_id)
    auxiliary_lobby = game_data["lobbies"][lobby_name_user_is_hosting]

    if ascension_lobby["die_used"] or ascension_lobby["chronograph_used"]: #if rerolling, refund used items, and take no damage
        ascension_lobby["items"]["Shields"] = ascension_lobby["items"]["Shields"] + ascension_lobby["shields_used"]
        ascension_lobby["current_sp"] = ascension_lobby["current_sp"] + ascension_lobby["sp_spent"]
        ascension_lobby["incoming_damage"] = 0
        ascension_lobby["level_number"] = ascension_lobby["level_number"] - 1
    else:
        ascension_lobby["incoming_damage"] = calculate_item_applied_incoming_damage(ascension_lobby) #apply items to incoming damage
        #if ascension_lobby["ascension_difficulty"] >= 1: #lose 2hp for each shield used
        #    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - (2 * ascension_lobby["shields_used"])

    ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - ascension_lobby["incoming_damage"]

    ascension_lobby["die_used"] = False
    ascension_lobby["shields_used"] = 0
    ascension_lobby["sp_spent"] = 0
    ascension_lobby["sp_times_used"] = 0

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
    gained_exp = 6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"]
    player_stats["exp"] = player_stats["exp"] + gained_exp

    if ascension_lobby["s_ranked_so_far"]:
        player_stats["s_ranked_entire_set"] = player_stats["s_ranked_entire_set"] + 1

    # is the last level but not the last set:
    if not is_last_set(ascension_lobby):

        num_items_to_forage = ascension_lobby["extra"]

        if num_items_to_forage == 0: #offer item
            player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], ascension_lobby["current_set"])
            player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

            ascension_lobby["level_number"] = ascension_lobby["level_number"] + 1

            current_items_clone = copy.deepcopy(ascension_lobby["items"])

            for item in current_items_clone:
                current_items_clone[item] = current_items_clone[item] + 1

            if ascension_lobby["ascension_difficulty"] >= 4:
                specialization = ascension_lobby["specialization"]
                if specialization != None:
                    current_items_clone[specialization] = current_items_clone[specialization]/2

            # remove 2 "most likely" items
            del current_items_clone[weighted_choose_from_dict(current_items_clone)]
            del current_items_clone[weighted_choose_from_dict(current_items_clone)]

            item_choice = weighted_choose_from_dict(current_items_clone)
            ascension_lobby["chosen_item_1"] = item_choice
            del current_items_clone[item_choice]

            ascension_lobby["chosen_item_2"] = (list(current_items_clone.keys()))[0]

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
    player_stats["highest_set_beaten"] = 7
    player_stats["highest_ascension_difficulty_beaten"] = max(player_stats["highest_ascension_difficulty_beaten"], ascension_lobby['ascension_difficulty'])
    player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

    # gain exp for a second time since it's doubled on victory
    gained_exp = 6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"]
    bonus_exp = 0
    for item in ascension_lobby["items"]:
        bonus_exp = bonus_exp + (3 + ascension_lobby["ascension_difficulty"]) * ascension_lobby["items"][item]
    player_stats["exp"] = player_stats["exp"] + gained_exp + bonus_exp

    ascension_lobby["status"] = "Victory"
    auxiliary_lobby["status"] = "Victory"

    await interaction.response.defer()
    await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
    self.lobbycommands.bot.save_data()
    return


def weighted_choose_from_dict(item_dict):
    item_list = list(item_dict.keys())
    item_weights = list(item_dict.values())
    return random.choices(item_list, weights = item_weights)[0]


class AscensionButtonsChoice(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__()
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Proceed", style=discord.ButtonStyle.success)
    async def proceed_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        await recover_helper(self, interaction)
        self.lobbycommands.bot.save_data()

    @discord.ui.button(label="Forage 1", style=discord.ButtonStyle.primary)
    async def forage1_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]
        auxiliary_lobby = game_data["lobbies"][self.lobby_name]

        ascension_difficulty = ascension_lobby["ascension_difficulty"]

        if ascension_difficulty < 4:
            (ascension_lobby["set_difficulties"]).append("Medium")
        else:
            (ascension_lobby["set_difficulties"]).append("Tough")

        ascension_lobby["extra"] = 1

        ascension_lobby["status"] = "Open"
        auxiliary_lobby["status"] = "Open"

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
        self.lobbycommands.bot.save_data()

    @discord.ui.button(label="Forage 2", style=discord.ButtonStyle.danger)
    async def forage2_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]
        auxiliary_lobby = game_data["lobbies"][self.lobby_name]

        ascension_difficulty = ascension_lobby["ascension_difficulty"]

        if ascension_difficulty < 4:
            (ascension_lobby["set_difficulties"]).append("Tough")
        else:
            (ascension_lobby["set_difficulties"]).append("Very Tough")

        ascension_lobby["extra"] = 2

        ascension_lobby["status"] = "Open"
        auxiliary_lobby["status"] = "Open"

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
        self.lobbycommands.bot.save_data()


async def recover_helper(self, interaction):
    game_data = self.lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][self.runner_id]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    if ascension_difficulty < 1: # recover 2/3rds of missing hp
        ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((2*ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 3))
    else: #recover 1/2
        ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 2))

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
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()
        await AscensionButtonsWelcome.newgame_pressed(self, button, interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()
        await self.lobbycommands.delete(interaction)


def get_ascension_welcome_embed(self, name, runner_id):
    ascension_lobbies = self.bot.game_data["ascension"]

    if runner_id not in ascension_lobbies:
        ascension_lobbies[runner_id] = {}
        ascension_lobbies[runner_id]["status"] = "Not Started"
        self.bot.validate_game_data()
        self.bot.save_data()

    runner_stats = self.bot.users_stats[runner_id]
    ascension_difficulty = runner_stats["current_ascension_difficulty"]
    runner_tickets = runner_stats["current_tickets"]

    ticket_cost_text = ""
    if ascension_difficulty >= 1:
        ticket_cost_text = f"\n\n**Starting a new game costs 1 🎫!** (You currently have {runner_tickets} 🎫)"

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{name}\"", description = f"Runner: <@{runner_id}>\n\n\
    Welcome to World Tour!\n\
Your goal is to treat patients across 5 cities spanning the globe.\n\
You, the **runner**, start with \⭐ HP, and will lose 1 for each miss.\n\
Other players are **support**, and will earn SP for you through good performance.\n\
\nYour progress will save, even if you delete the lobby.\n\
If you reach 0 HP, your tour will be cut short!{ticket_cost_text}")


def begin(self, ctx, runner_id, max_hp, lobby_name):
    ascension_lobby = self.bot.game_data["ascension"][runner_id]
    runner_stats = self.bot.users_stats[runner_id]

    ascension_difficulty = 0
    if "current_ascension_difficulty" in runner_stats:
        ascension_difficulty = runner_stats["current_ascension_difficulty"]
    ascension_lobby["ascension_difficulty"] = ascension_difficulty

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

    ascension_lobby["current_set"] = 3

    if (ascension_difficulty == 1) or (ascension_difficulty == 6):
        ascension_lobby["current_set"] = 2
    elif (ascension_difficulty == 0) or (ascension_difficulty == 7):
        ascension_lobby["current_set"] = 1

    ascension_lobby["level_number"] = 0

    ascension_lobby["items"]["Apples"] = 0
    ascension_lobby["items"]["Ivory Dice"] = 1
    ascension_lobby["items"]["Chronographs"] = 0
    ascension_lobby["items"]["Shields"] = 0

    specialization = runner_stats["specialization"]
    ascension_lobby["specialization"] = specialization

    if (ascension_difficulty >= 4) and (specialization != None):
        ascension_lobby["items"][specialization] = ascension_lobby["items"][specialization] + 1

    ascension_lobby["extra"] = 0

    ascension_lobby["no_levels_found_damage_multiplier"] = 1

    self.bot.save_data()

    begin_set(self, runner_id, lobby_name)


def begin_set(self, player_id, lobby_name):
    ascension_lobby = self.bot.game_data["ascension"][player_id]
    auxiliary_lobby = self.bot.game_data["lobbies"][lobby_name]
    sets_config = self.bot.get_sets_config()
    set_number = ascension_lobby['current_set']
    set_number_str = str(set_number)

    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    ascension_lobby['status'] = 'Open'
    auxiliary_lobby['status'] = 'Open'

    ascension_lobby["extra"] = 0
    ascension_lobby["s_ranked_so_far"] = True

    set_theme = 'None'
    if len(sets_config[set_number_str]['theme']) != 0:
        set_theme = random.choice(sets_config[set_number_str]['theme'])
    ascension_lobby['set_theme'] = set_theme

    set_modifier = 'None'
    if (ascension_difficulty < 7) or (set_number % 2 == 0):
        if len(sets_config[set_number_str]['modifier']) != 0:
            set_modifier = random.choice(sets_config[set_number_str]['modifier'])
    else:
        if len(sets_config[set_number_str]['modifier_hard']) != 0:
            set_modifier = random.choice(sets_config[set_number_str]['modifier_hard'])

    ascension_lobby['set_modifier'] = set_modifier

    ascension_lobby['roll_tags'] = sets_config[set_theme]['tags'] + sets_config[set_modifier]['tags']
    ascension_lobby['roll_facets'] = sets_config[set_theme]['facets'] | sets_config[set_modifier]['facets']

    ascension_lobby['roll_special'] = []
    if "special" in sets_config[set_theme]:
        ascension_lobby['roll_special'] = ascension_lobby['roll_special'] + sets_config[set_theme]['special']
    if "special" in sets_config[set_modifier]:
        ascension_lobby['roll_special'] = ascension_lobby['roll_special'] + sets_config[set_modifier]['special']

    set_difficulties = sets_config[set_number_str]['difficulties']

    if set_modifier != 'None':
        set_difficulties = sets_config[set_modifier]['diff_override']

    # make the set harder if ascension difficulty says to
    if ((ascension_difficulty >= 3) and (set_number == 3)) or ((ascension_difficulty >= 5) and (set_number == 5)):
        for i in range(len(set_difficulties)):
            if set_difficulties[i] == "Easy":
                set_difficulties[i] = "Medium"
            elif set_difficulties[i] == "Medium":
                set_difficulties[i] = "Tough"
            elif set_difficulties[i] == "Tough":
                set_difficulties[i] = "Very Tough"

    ascension_lobby['certificate_3_modifiers'] = []
    for i in range(len(set_difficulties)+1):
        if ("Button" in set_modifier) and ("Player" not in set_modifier):
            ascension_lobby['certificate_3_modifiers'].append("2-Player")
        elif ("Button" not in set_modifier) and ("Player" in set_modifier):
            ascension_lobby['certificate_3_modifiers'].append("Hard Difficulty Button")
        elif ("Button" not in set_modifier) and ("Player" not in set_modifier):
            ascension_lobby['certificate_3_modifiers'].append(random.choice(["Hard Difficulty Button", "2-Player"]))
        else:
            ascension_lobby['certificate_3_modifiers'].append("None")

    ascension_lobby['certificate_5_modifiers'] = []
    for i in range(len(set_difficulties)+1):
        if ("Blindfolded" in set_modifier) and ("Nightcore" not in set_modifier):
            ascension_lobby['certificate_5_modifiers'].append("Nightcore")
        elif ("Blindfolded" not in set_modifier) and ("Nightcore" in set_modifier):
            ascension_lobby['certificate_5_modifiers'].append("Blindfolded")
        elif ("Blindfolded" not in set_modifier) and ("Nightcore" not in set_modifier):
            ascension_lobby['certificate_5_modifiers'].append(random.choice(["Blindfolded", "Nightcore"]))
        else:
            ascension_lobby['certificate_3_modifiers'].append("None")

    ascension_lobby['set_difficulties'] = set_difficulties

    ascension_lobby["chosen_item_1"] = None
    ascension_lobby["chosen_item_2"] = None

    self.bot.save_data()


def get_ascension_open_embed(lobbycommands, ctx, lobby_name, runner_id, players_id_dict):
    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    sets_config = lobbycommands.bot.get_sets_config()
    ascension_difficulty = ascension_lobby["ascension_difficulty"]
    set_number = ascension_lobby["current_set"]
    level_number = ascension_lobby["level_number"]

    theme_and_modifier_desc = ""

    set_theme = ascension_lobby["set_theme"]
    set_modifier = ascension_lobby["set_modifier"]

    if set_theme != "None":
        theme_and_modifier_desc = theme_and_modifier_desc + f"City Theme: **{set_theme}**\n{sets_config[set_theme]['description']}\n\n"

    if set_modifier != "None":
        theme_and_modifier_desc = theme_and_modifier_desc + f"City Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"

    set_difficulties_bold = (ascension_lobby["set_difficulties"]).copy()
    set_difficulties_bold[level_number] = "**" + set_difficulties_bold[level_number] + "**"
    set_difficulties_text = ' -> '.join(set_difficulties_bold)

    items_text = get_current_items_text(ctx, ascension_lobby)

    ascension_difficulty_text = get_ascension_difficulty_text(ascension_difficulty)

    support_list = []
    for id in players_id_dict:
        support_list.append('<@' + id + '>')

    support_list.remove(f"<@{runner_id}>") #will always be included bc ascension

    support = ', '.join(support_list)

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
{ascension_difficulty_text}Levels: {set_difficulties_text}\n\n{theme_and_modifier_desc}{items_text}Support: {support}")


def set_roll_settings(lobbycommands, lobby_name, runner_id):
    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    auxiliary_lobby = lobbycommands.bot.game_data["lobbies"][lobby_name]

    level_number = ascension_lobby["level_number"]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    roll_settings = auxiliary_lobby["roll_settings"]

    roll_settings["peer_reviewed"] = "Yes"
    roll_settings["played_before"] = "No"
    roll_settings["difficulty"] = ascension_lobby["set_difficulties"][level_number]
    roll_settings["tags"] = (ascension_lobby["roll_tags"]).copy()
    roll_settings["facets"] = (ascension_lobby["roll_facets"]).copy()
    roll_settings["require_gameplay"] = True
    roll_settings["special"] = (ascension_lobby["roll_special"]).copy()
    roll_settings["difficulty_modifiers"] = []

    sets_config = lobbycommands.bot.get_sets_config()
    set_modifier = ascension_lobby["set_modifier"]

    if (set_modifier != "None") and ("difficulty_modifiers" in sets_config[set_modifier]):
        roll_settings["difficulty_modifiers"] = sets_config[set_modifier]["difficulty_modifiers"]

    set_number = ascension_lobby["current_set"]

    if (ascension_difficulty >= 3) and (set_number != 3) and ((roll_settings["difficulty"] == "Easy") or (roll_settings["difficulty"] == "Medium")):
        roll_settings["difficulty_modifiers"].append(ascension_lobby['certificate_3_modifiers'][level_number])
        if ascension_lobby['certificate_3_modifiers'][level_number] == "2-Player":
            roll_settings["facets"]["two_player"] = 1

    if (ascension_difficulty >= 5) and (set_number != 5) and (roll_settings["difficulty"] == "Easy"):
        roll_settings["difficulty_modifiers"].append(ascension_lobby['certificate_5_modifiers'][level_number])
    
    roll_settings["difficulty_modifiers"] = list(set(roll_settings["difficulty_modifiers"]))


def get_ascension_rolling_embed(lobbycommands, lobby_name, runner_id, player_id_dict, level_chosen, ascension_lobby):
    ready_list = ''

    for id in player_id_dict:
        ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    sets_config = lobbycommands.bot.get_sets_config()
    set_modifier = ascension_lobby["set_modifier"]

    set_number = ascension_lobby["current_set"]

    level_image = None
    if level_chosen != None:
        level_image = level_chosen['image_url']

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
Make sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, press \"**Ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}", image = level_image)
    levels.add_level_to_embed(level_embed, level_chosen)

    if set_modifier != "None":
        level_embed.add_field(name = f"Modifier: **{set_modifier}**", value = sets_config[set_modifier]['description'], inline = False)

    level_number = ascension_lobby["level_number"]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    if (ascension_difficulty >= 3) and (set_number != 3) and ((level_chosen['difficulty'] == "Easy") or (level_chosen['difficulty'] == "Medium")):
        c3_modifier = ascension_lobby['certificate_3_modifiers'][level_number]
        level_embed.add_field(name = f"<:gold:1399860113883402270> Extra Modifier: **{c3_modifier}**", value = sets_config[c3_modifier]['description'], inline = False)

    if (ascension_difficulty >= 5) and (set_number != 5) and (level_chosen['difficulty'] == "Easy"):
        c5_modifier = ascension_lobby['certificate_5_modifiers'][level_number]
        level_embed.add_field(name = f"<:illustrious:1399860117700087888> Extra Modifier: **{c5_modifier}**", value = sets_config[c5_modifier]['description'], inline = False)

    return level_embed


def get_ascension_item_embed(ctx, lobby_name, runner_id, ascension_lobby):
    items_text = get_current_items_text(ctx, ascension_lobby)

    sp_cost = max(5, ascension_lobby["current_sp"] // 2)

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
You are about to take {calculate_item_applied_incoming_damage(ascension_lobby)} damage!\n\
Press the corresponding button below to use an item.\n\n\
{items_text}Press \"**Use SP**\" to spend {sp_cost} SP to reduce incoming damage by 3. (This is more expensive if you have a lot of SP!)")
    return level_embed


def get_ascension_choice_embed(ctx, lobby_name, runner_id, ascension_lobby):
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    recover_fraction = "2/3"
    forage_1_difficulty = "Medium"
    forage_2_difficulty = "Tough"

    if ascension_difficulty >= 1:
        recover_fraction = "1/2"
    if ascension_difficulty >= 4:
        forage_1_difficulty = "Tough"
        forage_2_difficulty = "Very Tough"

    gained_exp = 6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"]

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have beaten this set and have {ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP!\n\
You have also gained {gained_exp} additional \🎵.\n\n\
You will recover {recover_fraction} of your missing HP __at the start of the next set__.\n\n\
You can choose to **proceed** to the next set now...\n\
Or, you can first play an extra {forage_1_difficulty} this set to **forage 1** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_1'])}...\n\
Or, you can play an extra {forage_2_difficulty} to **forage 2** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_2'])}.")
    return level_embed


def get_ascension_gameover_embed(lobbycommands, lobby_name, runner_id, ascension_lobby):
    set_number = str(ascension_lobby['current_set'])

    runner_stats = lobbycommands.bot.users_stats[runner_id]
    ascension_difficulty = runner_stats["current_ascension_difficulty"]
    runner_tickets = runner_stats["current_tickets"]

    ticket_cost_text = ""
    if ascension_difficulty >= 1:
        ticket_cost_text = f"\n\n**Starting a new game costs 1 🎫!** (You currently have {runner_tickets} 🎫)"

    gameover_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have run out of HP! GAME OVER!\n\n\
Press **New Game** to try again, or press **Delete** to delete this lobby.{ticket_cost_text}")
    return gameover_embed


def get_ascension_victory_embed(lobby_name, runner_id, ascension_lobby):
    gained_exp = 2 * (6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"])
    bonus_exp = 0
    for item in ascension_lobby["items"]:
        bonus_exp = bonus_exp + (3 + ascension_lobby["ascension_difficulty"]) * ascension_lobby["items"][item]

    certification_text = ""
    if ascension_lobby["ascension_difficulty"] > 0:
        certification_text = "**{ CERTIFICATE " + str(ascension_lobby["ascension_difficulty"]) + " OBTAINED }**\n\n"

    spec_unlocked_text = ""
    if ascension_lobby["ascension_difficulty"] == 3:
        spec_unlocked_text = "**You can now do `/admin_command specialize`!**\n\n"

    victory_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | **VICTORY!**", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
{certification_text}YOU WIN! Congratulations!!!!!\n\
You have gained {gained_exp} additional \🎵.\n\
Your remaining items have been converted to {bonus_exp} total \🎵.\n\n{spec_unlocked_text}\
-# You can now do `/admin_command certify {ascension_lobby['ascension_difficulty']+1}`...")
    return victory_embed


def get_current_items_text(ctx, ascension_lobby):
    current_items = ascension_lobby["items"]
    items_text = "*Your items (hover for info):*\n"

    for item in current_items.keys():
        if current_items[item] > 0:
            items_text = items_text + get_item_text(ctx, ascension_lobby, item)
            items_text = items_text + " x" + str(current_items[item]) + "\n"

    if items_text == "*Your items (hover for info):*\n":
        items_text = ""
    else:
        items_text = items_text + "\n"

    return items_text


def get_item_text(ctx, ascension_lobby, item):
    if item == "Apples":
        return f"<:Apple:1405858469726257153> [Apples]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to recover {get_apple_heal_amount(ascension_lobby)} HP\")"
    elif item == "Ivory Dice":
        return f"<:IvoryDie:1405867029570916374> [Ivory Dice]({ctx.channel.jump_url} \"After playing a level, INSTEAD OF taking damage, use this item to reroll it\")"
    elif item == "Chronographs":
        return f"<:Chronograph:1405867070888873994> [Chronographs]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to REPLAY the level for a better score\")"
    elif item == "Shields":
        return f"<:Shield:1405867148856791080> [Shields]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to halve incoming damage\")"
    else:
        return "HUGE MISTAKE"


def get_apple_heal_amount(ascension_lobby):
    if ascension_lobby["ascension_difficulty"] < 2:
        return 10
    elif ascension_lobby["ascension_difficulty"] < 6:
        return 12
    else:
        return 15


def get_ascension_difficulty_text(ascension_difficulty):
    if ascension_difficulty < 1:
        return ""

    ascension_difficulty_text = "**Certifications:**"

    if ascension_difficulty >= 1:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:bronze:1399860108665557043> Starting runs costs 1 🎫 **/** Recovering heals less HP **/** Clear cities 2-6"
    if ascension_difficulty >= 2:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:silver:1399860110389542915> Easier levels deal more damage **/** Clear cities 3-7 **/** Apples heal more"
    if ascension_difficulty >= 3:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:gold:1399860113883402270> City 3 invades easier levels **/** City 3 is harder **/** The final boss appears"
    if ascension_difficulty >= 4:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:distinguished:1399860116119093529> More difficult foraging **/** Hard button final boss **/** You may `specialize`" # hard button
    if ascension_difficulty >= 5:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:illustrious:1399860117700087888> City 5 invades easy levels **/** City 5 is harder **/** No recovering after city 7"
    if ascension_difficulty >= 6:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:stellar:1399860119092854936> All levels deal more damage **/** Clear cities 2-7 **/** Apples heal even more"
    if ascension_difficulty >= 7:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:medical_grade:1399860122288783390> Odd cities are corrupted **/** Clear cities 1-7 **/** Double damage final boss" # double damage

    ascension_difficulty_text = ascension_difficulty_text + "\n\n"

    return ascension_difficulty_text


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
    applied_incoming_damage = applied_incoming_damage - (3 * ascension_lobby["sp_times_used"])

    applied_incoming_damage = max(0, applied_incoming_damage)

    return applied_incoming_damage


async def no_levels_found(lobby_commands, ctx, ascension_lobby, auxiliary_lobby, lobby_name):
    new_facets = {}
    if ("two_player" in auxiliary_lobby["roll_settings"]["facets"]) and (auxiliary_lobby["roll_settings"]["facets"]["two_player"] == 1):
        new_facets = {"two_player": 1}

    await ctx.channel.send("No levels found! Rerolling without theme...")

    auxiliary_lobby["roll_settings"]["tags"] = []
    auxiliary_lobby["roll_settings"]["facets"] = new_facets

    lobby_commands.roll_level_from_settings(lobby_name)
    level_chosen = auxiliary_lobby["level"]

    if level_chosen != None:
        return

    await ctx.channel.send("No levels found! Rerolling with lower difficulty (**2.5x damage multiplier**)...")

    ascension_lobby["no_levels_found_damage_multiplier"] = 2.5

    level_difficulty = auxiliary_lobby["roll_settings"]["difficulty"]

    lower_level_difficulty = "Easy"
    if level_difficulty == "Very Tough":
        lower_level_difficulty = "Tough"
    elif level_difficulty == "Tough":
        lower_level_difficulty = "Medium"

    auxiliary_lobby["roll_settings"]["difficulty"] = lower_level_difficulty

    lobby_commands.roll_level_from_settings(lobby_name)
    level_chosen = auxiliary_lobby["level"]

    if level_chosen != None:
        return

    await ctx.channel.send("No levels found! Rerolling for Non-Refereed levels...")

    ascension_lobby["no_levels_found_damage_multiplier"] = 1

    auxiliary_lobby["roll_settings"]["difficulty"] = level_difficulty
    auxiliary_lobby['roll_settings']['peer_reviewed'] = "Any"

    lobby_commands.roll_level_from_settings(lobby_name)
    return