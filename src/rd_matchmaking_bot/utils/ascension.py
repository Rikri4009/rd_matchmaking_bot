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
            await interaction.respond("You haven't started climbing yet!", ephemeral=True)
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
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        if ascension_lobby["items"]["Apples"] < 1:
            await interaction.respond("You don't have any Pineapples! I mean Apples!")
            return

        if ascension_lobby["ascension_difficulty"] >= 1:
            ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

        ascension_lobby["items"]["Apples"] = ascension_lobby["items"]["Apples"] - 1
        ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + get_apple_heal_amount(ascension_lobby)
        #if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]: #clamp to max
        #    ascension_lobby["current_hp"] = ascension_lobby["max_hp"]
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

        if ascension_lobby["ascension_difficulty"] >= 1:
            ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

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

        if ascension_lobby["ascension_difficulty"] >= 1:
            ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - 2

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
        if ascension_lobby["ascension_difficulty"] >= 1: #lose 2hp for each shield used
            ascension_lobby["current_hp"] = ascension_lobby["current_hp"] - (2 * ascension_lobby["shields_used"])

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
    gained_exp = (3 + ascension_lobby["ascension_difficulty"]) * ascension_lobby["current_set"]
    player_stats["exp"] = player_stats["exp"] + gained_exp

    if ascension_lobby["s_ranked_so_far"]:
        player_stats["s_ranked_entire_set"] = player_stats["s_ranked_entire_set"] + 1

    # is the last level but not the last set:
    if ascension_lobby["current_set"] < 7:

        num_items_to_forage = ascension_lobby["extra"]

        if num_items_to_forage == 0: #offer item
            player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], ascension_lobby["current_set"])
            player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

            ascension_lobby["level_number"] = ascension_lobby["level_number"] + 1

            current_items_clone = copy.deepcopy(ascension_lobby["items"])

            for item in current_items_clone:
                current_items_clone[item] = current_items_clone[item] + 1

            # remove 2 "most likely" items
            del current_items_clone[weighted_choose_from_dict(current_items_clone)]
            del current_items_clone[weighted_choose_from_dict(current_items_clone)]

            item_choice = weighted_choose_from_dict(current_items_clone)
            ascension_lobby["chosen_item_1"] = item_choice
            del current_items_clone[item_choice]

            ascension_lobby["chosen_item_2"] = (list(current_items_clone.keys()))[0]

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

    await interaction.respond(f"YOU WIN! Congratulations!!!!! (technically this is still a beta test but it counts)\n\
You ended with {ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP.\n\n\
-# You can now do `/admin_command ascension {ascension_lobby['ascension_difficulty']+1}`...")
    ascension_lobby["status"] = "Not Started"
    auxiliary_lobby["status"] = "Not Started"
    self.bot.save_data()


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

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{name}\"", description = f"Runner: <@{runner_id}>\n\n\
    Welcome to Ascension!\n\
Your goal is to play levels to reach `   ` `     ` at the end of Set 7.\n\
You, the **runner**, start with ★ HP, and will lose 1 for each miss.\n\
Other players are **support**, and will earn SP for you through good performance.\n\
\nYour progress will save, even if you delete the lobby.\n\
Only when you reach 0 HP will you fall back to the beginning.")


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

    ascension_lobby["current_set"] = 1
    ascension_lobby["level_number"] = 0

    ascension_lobby["items"]["Apples"] = 0
    ascension_lobby["items"]["Ivory Dice"] = 1
    ascension_lobby["items"]["Chronographs"] = 0
    ascension_lobby["items"]["Shields"] = 0

    if ascension_difficulty >= 4:
        ascension_lobby["items"]["Ivory Dice"] = 2

    ascension_lobby["extra"] = 0

    self.bot.save_data()

    begin_set(self, runner_id, lobby_name)


def begin_set(self, player_id, lobby_name):
    ascension_lobby = self.bot.game_data["ascension"][player_id]
    auxiliary_lobby = self.bot.game_data["lobbies"][lobby_name]
    sets_config = self.bot.get_sets_config()
    set_number = str(ascension_lobby['current_set'])

    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    set_difficulties = sets_config[set_number]['difficulties']

    # make the set harder if ascension difficulty says to
    if (ascension_difficulty < 7) and (((ascension_difficulty >= 3) and (set_number == 3)) or ((ascension_difficulty >= 5) and (set_number == 5))):
        for i in range(len(set_difficulties)):
            if set_difficulties[i] == "Easy":
                set_difficulties[i] = "Medium"
            if set_difficulties[i] == "Medium":
                set_difficulties[i] = "Tough"
            if set_difficulties[i] == "Tough":
                set_difficulties[i] = "Very Tough"

    ascension_lobby['status'] = 'Open'
    auxiliary_lobby['status'] = 'Open'

    ascension_lobby["extra"] = 0
    ascension_lobby["s_ranked_so_far"] = True

    set_theme = 'None'
    if len(sets_config[set_number]['theme']) != 0:
        set_theme = random.choice(sets_config[set_number]['theme'])
    ascension_lobby['set_theme'] = set_theme

    set_modifier = 'None'
    if len(sets_config[set_number]['modifier']) != 0:
        if (ascension_difficulty < 7) or (set_number % 2 == 0):
            set_modifier = random.choice(sets_config[set_number]['modifier'])
        else:
            set_modifier = random.choice(sets_config[set_number]['modifier_hard'])
    ascension_lobby['set_modifier'] = set_modifier

    ascension_lobby['roll_tags'] = sets_config[set_theme]['tags'] + sets_config[set_modifier]['tags']
    ascension_lobby['roll_facets'] = sets_config[set_theme]['facets'] | sets_config[set_modifier]['facets']

    if set_modifier != 'None':
        set_difficulties = sets_config[set_modifier]['diff_override']

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
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Theme: **{set_theme}**\n{sets_config[set_theme]['description']}\n\n"

    if set_modifier != "None":
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"

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

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
{ascension_difficulty_text}Levels: {set_difficulties_text}\n\n{theme_and_modifier_desc}{items_text}Do `/lobby roll` to proceed!\n\nSupport: {support}")


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

    level_image = None
    if level_chosen != None:
        level_image = level_chosen['image_url']

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
{modifier_text}Make sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, press \"**Ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}", image = level_image)
    levels.add_level_to_embed(level_embed, level_chosen)
    return level_embed


def get_ascension_item_embed(ctx, lobby_name, runner_id, ascension_lobby):
    items_text = get_current_items_text(ctx, ascension_lobby)

    sp_cost = max(5, ascension_lobby["current_sp"] // 2)

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
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

    gained_exp = (3 + ascension_difficulty) * ascension_lobby["current_set"]

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have beaten this set and have {ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP!\n\
You have also gained {gained_exp} additional exp.\n\n\
You will recover {recover_fraction} of your missing HP __at the start of the next set__.\n\n\
You can choose to **proceed** to the next set now...\n\
Or, you can first play an extra {forage_1_difficulty} this set to **forage 1** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_1'])}...\n\
Or, you can play an extra {forage_2_difficulty} to **forage 2** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_2'])}.")
    return level_embed


def get_ascension_gameover_embed(lobby_name, runner_id, ascension_lobby):
    set_number = str(ascension_lobby['current_set'])
    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Ascension Lobby: \"{lobby_name}\" | SET {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have run out of HP! GAME OVER!\n\n\
Press **New Game** to try again, or press **Delete** to delete this lobby.")
    return level_embed


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
        ascension_difficulty_text = ascension_difficulty_text + "\n<:bronze:1399860108665557043> Recovering only heals 1/2 of missing HP, and using an item costs 2 HP"
    if ascension_difficulty >= 2:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:silver:1399860110389542915> Easy levels deal x2 damage and medium levels deal x1.5, but apples heal 12 HP"
    if ascension_difficulty >= 3:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:gold:1399860113883402270> All easy/medium levels must be played either on hard or 2P, and Set 3 is harder"
    if ascension_difficulty >= 4:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:distinguished:1399860116119093529> Foraging is more difficult, but start with an extra Ivory Die"
    if ascension_difficulty >= 5:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:illustrious:1399860117700087888> All easy levels must be played either on chili speed or blindfolded, and Set 5 is harder"
    if ascension_difficulty >= 6:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:stellar:1399860119092854936> [Replaces <:silver:1399860110389542915>] Easy/medium levels deal x2 damage and tough/vt levels deal x1.5, but apples heal 15 HP"
    if ascension_difficulty >= 7:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:medical_grade:1399860122288783390> Odd-numbered sets have harder modifiers"

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