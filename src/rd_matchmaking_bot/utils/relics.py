import discord
import rd_matchmaking_bot.utils.ascension as ascension

def easy_button_damage(ascension_lobby):
    if "easy_button" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_damage_multipliers"].append(1.1)
    return


def choose_modifiers(ascension_lobby, lobbycommands):
    if "choose_modifiers" not in ascension_lobby["lobby_relics"]:
        return []

    sets_config = lobbycommands.bot.get_sets_config()

    next_city_modifiers = ascension.get_set_modifier_options(ascension_lobby, ascension_lobby['current_set']+1, lobbycommands)
    next_city_modifier_choices = []

    for modifier in next_city_modifiers:
        next_city_modifier_choices.append(discord.SelectOption(label = modifier, description = sets_config[modifier]["description"]))

    return next_city_modifier_choices

def apples_powerup(ascension_lobby):
    if "apples_powerup" not in ascension_lobby["lobby_relics"]:
        return
    return


def ivory_dice_powerup(ascension_lobby):
    if "ivory_dice_powerup" not in ascension_lobby["lobby_relics"]:
        return
    return


def chronographs_powerup(ascension_lobby):
    if "chronographs_powerup" not in ascension_lobby["lobby_relics"]:
        return
    return


def shields_powerup(ascension_lobby, shield_block_factor):
    if "shields_powerup" not in ascension_lobby["lobby_relics"]:
        return shield_block_factor

    level_difficulty = ascension_lobby["set_difficulties"][ascension_lobby["level_number"]]

    if (level_difficulty == "Easy") or (level_difficulty == "Medium"):
        shield_block_factor = 4

    return shield_block_factor


def max_hp(ascension_lobby):
    if "max_hp" not in ascension_lobby["lobby_relics"]:
        return
    return


def skip_levels(ascension_lobby):
    if "skip_levels" not in ascension_lobby["lobby_relics"]:
        return
    return


def s_rank_bonus(ascension_lobby):
    if "s_rank_bonus" not in ascension_lobby["lobby_relics"]:
        return
    return


def use_winner(ascension_lobby):
    if "use_winner" not in ascension_lobby["lobby_relics"]:
        return
    return


def immediate_foraging(ascension_lobby):
    if "immediate_foraging" not in ascension_lobby["lobby_relics"]:
        return False
    return True


def cheaper_essence(ascension_lobby, base_cost):
    if "cheaper_essence" not in ascension_lobby["lobby_relics"]:
        return base_cost

    return 3


def double_foraging_damage(ascension_lobby):
    if "double_foraging" not in ascension_lobby["lobby_relics"]:
        return

    if ascension_lobby["extra"] > 0:
        ascension_lobby["relic_damage_multipliers"].append(2)

def double_foraging_item_count(ascension_lobby, item_count):
    if "double_foraging" not in ascension_lobby["lobby_relics"]:
        return item_count

    # as per double foraging's wording, *levels* played when foraging yield double rewards, meaning old foraging is unaffected
    if old_foraging_skip_level(ascension_lobby) and (item_count == 2):
        return 2

    return 2 * item_count


def old_foraging_emoji(ascension_lobby, emoji):
    if "old_foraging" not in ascension_lobby["lobby_relics"]:
        return emoji

    emoji = "☕"

    return emoji

def old_foraging_skip_level(ascension_lobby):
    if "old_foraging" not in ascension_lobby["lobby_relics"]:
        return False

    if ascension_lobby["extra"] != 2:
        return False

    return True


def cheaper_sp(ascension_lobby, sp_cost):
    if "cheaper_sp" not in ascension_lobby["lobby_relics"]:
        return sp_cost

    sp_cost = max(5, ascension_lobby['current_sp'] // 4)

    return sp_cost


def short_levels_damage(ascension_lobby):
    if "short_levels" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_damage_multipliers"].append(1.2)

def short_levels_roll_settings(ascension_lobby, roll_settings):
    if "short_levels" not in ascension_lobby["lobby_relics"]:
        return

    roll_settings["special"].append("short")


def long_levels_damage(ascension_lobby):
    if "long_levels" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_damage_multipliers"].append(0.75)

def long_levels_roll_settings(ascension_lobby, roll_settings):
    if "long_levels" not in ascension_lobby["lobby_relics"]:
        return

    roll_settings["special"].append("long")