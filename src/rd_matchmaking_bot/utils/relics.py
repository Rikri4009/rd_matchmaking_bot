import discord
import math
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

    if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]:
        ascension_lobby["max_hp"] = ascension_lobby["max_hp"] + 10


def ivory_dice_powerup(ascension_lobby, current_hp, incoming_damage):
    if "ivory_dice_powerup" not in ascension_lobby["lobby_relics"]:
        return

    if current_hp > incoming_damage:
        ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], ascension_lobby["max_hp"])


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

    ascension_lobby["max_hp"] = ascension_lobby["max_hp"] + 7


def skip_levels_initialize_data(ascension_lobby):
    if "skip_levels" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_data"]["skip_levels"] = 0


def skip_levels_use(ascension_lobby):
    if "skip_levels" not in ascension_lobby["lobby_relics"]:
        return

    if ascension_lobby["relic_data"]["skip_levels"] >= 3:
        return

    ascension_lobby["level_number"] = 1
    ascension_lobby["relic_data"]["skip_levels"] = ascension_lobby["relic_data"]["skip_levels"] + 1


def s_rank_bonus(ascension_lobby, miss_count):
    if "s_rank_bonus" not in ascension_lobby["lobby_relics"]:
        return

    if miss_count == 0:
        ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + 30

    return


def use_winner_initialize_data(ascension_lobby):
    if "use_winner" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_data"]["use_winner_uses"] = 0
    ascension_lobby["relic_data"]["use_winner_miss_count"] = -1


def use_winner_save_miss_count(ascension_lobby, miss_count):
    if "use_winner" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_data"]["use_winner_miss_count"] = miss_count


def use_winner_add_damage_factor(ascension_lobby, damage_factor):
    if "use_winner" not in ascension_lobby["lobby_relics"]:
        return

    ascension_lobby["relic_data"]["use_winner_miss_count"] = math.floor(ascension_lobby["relic_data"]["use_winner_miss_count"] * damage_factor)


def use_winner_has_usage(ascension_lobby):
    if "use_winner" not in ascension_lobby["lobby_relics"]:
        return False

    return (ascension_lobby["relic_data"]["use_winner_uses"] < 2)


def immediate_foraging(ascension_lobby):
    if "immediate_foraging" not in ascension_lobby["lobby_relics"]:
        return False
    return True


def cheaper_essence(ascension_lobby, base_cost, base_base):
    if "cheaper_essence" not in ascension_lobby["lobby_relics"]:
        return [base_cost, base_base]

    return [3, 1.5]


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

def old_foraging_forage2_text(ascension_lobby, forage2_text):
    if "old_foraging" not in ascension_lobby["lobby_relics"]:
        return forage2_text

    return "☕ skip recovering altogether"


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