import discord
import random
import math
import copy
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.misc as misc
import rd_matchmaking_bot.utils.relics as relics

async def newgame_button_pressed(self, button, interaction):
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


def get_certify_buttons(lobbycommands, lobby_name, runner_id):
    user_stats = lobbycommands.bot.users_stats[runner_id]
    max_available_certification = user_stats["highest_ascension_difficulty_beaten"] + 1

    class CertifyButtons(discord.ui.View):
        def __init__(self, lobbycommands, lobby_name, runner_id):
            super().__init__(timeout=2000)
            self.lobbycommands = lobbycommands
            self.lobby_name = lobby_name

            self.user_stats = self.lobbycommands.bot.users_stats[runner_id]

        async def update_certification(self, interaction, number):
            self.user_stats["current_ascension_difficulty"] = number
            await interaction.response.defer()
            await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
            self.lobbycommands.bot.save_data()

        @discord.ui.button(label="None", row=0, style=discord.ButtonStyle.secondary)
        async def c0_pressed(self, button, interaction):
            await self.update_certification(interaction, 0)

        @discord.ui.button(emoji=misc.get_number_emoji(1), row=0, style=discord.ButtonStyle.secondary)
        async def c1_pressed(self, button, interaction):
            await self.update_certification(interaction, 1)

        @discord.ui.button(emoji=misc.get_number_emoji(2), row=0, style=discord.ButtonStyle.secondary)
        async def c2_pressed(self, button, interaction):
            await self.update_certification(interaction, 2)

        @discord.ui.button(emoji=misc.get_number_emoji(3), row=0, style=discord.ButtonStyle.secondary)
        async def c3_pressed(self, button, interaction):
            await self.update_certification(interaction, 3)

        @discord.ui.button(emoji=misc.get_number_emoji(4), row=1, style=discord.ButtonStyle.secondary)
        async def c4_pressed(self, button, interaction):
            await self.update_certification(interaction, 4)

        @discord.ui.button(emoji=misc.get_number_emoji(5), row=1, style=discord.ButtonStyle.secondary)
        async def c5_pressed(self, button, interaction):
            await self.update_certification(interaction, 5)

        @discord.ui.button(emoji=misc.get_number_emoji(6), row=1, style=discord.ButtonStyle.secondary)
        async def c6_pressed(self, button, interaction):
            await self.update_certification(interaction, 6)

        @discord.ui.button(emoji=misc.get_number_emoji(7), row=1, style=discord.ButtonStyle.secondary)
        async def c7_pressed(self, button, interaction):
            await self.update_certification(interaction, 7)


    return CertifyButtons(lobbycommands, lobby_name, runner_id)


class SpecializeButtons(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__(timeout=2000)
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name

        self.user_stats = lobbycommands.bot.users_stats[runner_id]

    async def finish(self, interaction):
        self.lobbycommands.bot.save_data()
        await interaction.response.defer()
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)

    @discord.ui.button(label="Apples", style=discord.ButtonStyle.primary)
    async def apples_pressed(self, button, interaction):
        self.user_stats["specialization"] = "Apples"
        await self.finish(interaction)

    @discord.ui.button(label="Ivory Dice", style=discord.ButtonStyle.primary)
    async def dice_pressed(self, button, interaction):
        self.user_stats["specialization"] = "Ivory Dice"
        await self.finish(interaction)

    @discord.ui.button(label="Chronographs", style=discord.ButtonStyle.primary)
    async def chronographs_pressed(self, button, interaction):
        self.user_stats["specialization"] = "Chronographs"
        await self.finish(interaction)

    @discord.ui.button(label="Shields", style=discord.ButtonStyle.primary)
    async def shields_pressed(self, button, interaction):
        self.user_stats["specialization"] = "Shields"
        await self.finish(interaction)

    @discord.ui.button(label="None", style=discord.ButtonStyle.secondary)
    async def prev_pressed(self, button, interaction):
        self.user_stats["specialization"] = None
        await self.finish(interaction)


def get_ascension_buttons_welcome(lobbycommands, lobby_name, runner_id):
    user_stats = lobbycommands.bot.users_stats[runner_id]

    require_ticket = (user_stats["current_ascension_difficulty"] >= 1)
    show_certify = (user_stats["highest_set_beaten"] >= 5)
    show_specialize = (user_stats["current_ascension_difficulty"] >= 4)

    class AscensionButtonsWelcome(discord.ui.View):
        def __init__(self, lobbycommands, lobby_name, runner_id):
            super().__init__(timeout=20000)
            self.lobbycommands = lobbycommands
            self.lobby_name = lobby_name
            self.runner_id = runner_id

        @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
        async def continue_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            game_data = self.lobbycommands.bot.game_data
            if game_data["ascension"][self.runner_id]["status"] == "Not Started":
                await interaction.respond("You haven't started a run yet!", ephemeral=True)
                return

            self.stop()

            # note that the ascension data's status will never be rolling or playing, so no need to copy over level
            game_data["lobbies"][self.lobby_name]["status"] = game_data["ascension"][self.runner_id]["status"]

            await interaction.response.defer()
            await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)

        if require_ticket:
            @discord.ui.button(label="New Game", emoji="🎫", style=discord.ButtonStyle.danger)
            async def newgame_pressed(self, button, interaction):
                await newgame_button_pressed(self, button, interaction)
        else:
            @discord.ui.button(label="New Game", style=discord.ButtonStyle.danger)
            async def newgame_pressed(self, button, interaction):
                await newgame_button_pressed(self, button, interaction)


        if show_certify:
            @discord.ui.button(label="Certify", style=discord.ButtonStyle.secondary)
            async def certify_pressed(self, button, interaction):
                uid = str(interaction.user.id)
                if uid != self.runner_id:
                    await interaction.respond("Not your button!", ephemeral=True)
                    return

                current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
                lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)

                certify_embed = discord.Embed(colour = discord.Colour.light_grey(), title = "Certify?", description = f"Challenge yourself by attempting a certification!\nHigher certifications make runs **harder**, but yield **greater rewards**:\n- More bonus exp when completing cities\n- Leftover items on victory are converted to more essence\n- Random special reward on victory\n- Ascend...?\nThe journey to true rhythm mastery awaits you!")

                await interaction.response.defer()
                await lobby_curr_message.edit(embed=certify_embed, view=get_certify_buttons(self.lobbycommands, self.lobby_name, uid))
                return


        @discord.ui.button(label="Relics", style=discord.ButtonStyle.primary)
        async def relics_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
            lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)

            relics_embed = get_relics_embed(interaction, self.lobbycommands, self.runner_id)
            relics_view = get_ascension_buttons_relics(self.lobbycommands, self.lobby_name, self.runner_id)

            await interaction.response.defer()
            await lobby_curr_message.edit(embed=relics_embed, view=relics_view)
            return

        if show_specialize:
            @discord.ui.button(label="Specialize", style=discord.ButtonStyle.primary)
            async def specialize_pressed(self, button, interaction):
                uid = str(interaction.user.id)
                if uid != self.runner_id:
                    await interaction.respond("Not your button!", ephemeral=True)
                    return

                current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
                lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)

                specializations_embed = discord.Embed(colour = discord.Colour.purple(), title = "Specializations", description = f"Press a button to **specialize** in an item!\nYou are more likely to be offered the item you specialize in.\nAdditionally, you will begin runs with +1 of this item.\n__Specializations only work on Certification 4 or above.__")

                await interaction.response.defer()
                await lobby_curr_message.edit(embed=specializations_embed, view=SpecializeButtons(self.lobbycommands, self.lobby_name, self.runner_id))
                return

    return AscensionButtonsWelcome(lobbycommands, lobby_name, runner_id)


def get_equipped_relics_text(ctx, lobbycommands, runner_id):
    relic_information = lobbycommands.bot.get_relic_information()
    runner_stats = lobbycommands.bot.users_stats[runner_id]
    runner_owned_relics = runner_stats["owned_relics"]
    runner_equipped_relics = runner_stats["equipped_relics"]

    runner_relic_slots = get_relic_slots(relic_information, runner_owned_relics)

    equipped_relics_text = "**Equipped Relics:** "

    for relic_slot in range(runner_relic_slots):
        if relic_slot < len(runner_equipped_relics):
            equipped_relics_text = equipped_relics_text + get_relic_text(ctx, relic_information, runner_equipped_relics[relic_slot])
        else:
            equipped_relics_text = equipped_relics_text + get_relic_text(ctx, relic_information, None)

        if relic_slot < runner_relic_slots - 1:
            equipped_relics_text = equipped_relics_text + ", "

    return equipped_relics_text


def get_relics_embed(ctx, lobbycommands, runner_id):
    relic_information = lobbycommands.bot.get_relic_information()
    runner_stats = lobbycommands.bot.users_stats[runner_id]
    runner_owned_relics = runner_stats["owned_relics"]
    runner_equipped_relics = runner_stats["equipped_relics"]

    runner_relic_slots = get_relic_slots(relic_information, runner_owned_relics)

    relics_text = "Relics are permanent items that give you special bonuses during runs. You can select your relic loadout here. (You can only equip 1 of each relic.)\n\n"
    relics_text = relics_text + "You can purchase a random relic if you have 40 💎.\n\n"

    equipped_relics_text = get_equipped_relics_text(ctx, lobbycommands, runner_id)

    relics_text = relics_text + equipped_relics_text

    if runner_relic_slots == 1:
        relics_text = relics_text + " (next relic slot at 7 total relics)"

    relics_text = relics_text + "\n\n**=-= Owned Relics =-=**\n"

    for relic_type in relic_information.keys():
        relic_type_text = ""

        for relic in relic_information[relic_type].keys():
            if (relic in runner_owned_relics) and (runner_owned_relics[relic] > 0):
                relic_type_text = relic_type_text + get_relic_text(ctx, relic_information, relic)

                if runner_owned_relics[relic] > 1:
                    relic_type_text = relic_type_text + " x" + str(runner_owned_relics[relic])

                relic_type_text = relic_type_text + "\n"

        if relic_type_text != "":
            relics_text = relics_text + f"- {relic_type}\n" + relic_type_text

    relics_embed = discord.Embed(colour = discord.Colour.yellow(), title = "Relics", description = f"{relics_text}\n(Not all Unique relics have been thoroughly tested. Let <@1207345676141465622> know if something breaks.)")
    relics_embed.set_footer(text="Hover over text for info!")
    return relics_embed


def get_relic_slots(relic_information, runner_owned_relics):
    user_relic_count = 0

    for relic_type in relic_information.keys():
        for relic in relic_information[relic_type].keys():
            if relic in runner_owned_relics:
                user_relic_count = user_relic_count + runner_owned_relics[relic]

    runner_relic_slots = 1
    if user_relic_count >= 7:
        runner_relic_slots = 2

    return runner_relic_slots


def get_relic_text(ctx, relic_information, relic):
    if relic == None:
        return "None"

    for relic_type in relic_information.keys():
        for relic_key in relic_information[relic_type].keys():
            if relic == relic_key:
                relic_dict = relic_information[relic_type][relic]
                return f"{relic_dict['emoji']} [{relic_dict['name']}]({ctx.channel.jump_url} \"{relic_dict['description']}\")"

    return "RELIC NOT FOUND"


def get_ascension_buttons_relics(lobbycommands, lobby_name, runner_id):
    relic_information = lobbycommands.bot.get_relic_information()
    runner_stats = lobbycommands.bot.users_stats[runner_id]
    runner_owned_relics = runner_stats["owned_relics"]

    runner_owned_relics_options = []

    for relic_type in relic_information.keys():
        for relic in relic_information[relic_type].keys():
            if (relic in runner_owned_relics) and (runner_owned_relics[relic] > 0):
                relic_option = discord.SelectOption(label = relic_information[relic_type][relic]["name"], description = relic_information[relic_type][relic]["description"])
                runner_owned_relics_options.append(relic_option)

    relic_slots = get_relic_slots(relic_information, runner_owned_relics)

    class AscensionButtonsRelics(discord.ui.View):
        def __init__(self, lobbycommands, lobby_name, runner_id):
            super().__init__(timeout=20000)
            self.lobbycommands = lobbycommands
            self.lobby_name = lobby_name
            self.runner_id = runner_id

        @discord.ui.select(
                placeholder = "Choose Relics",
                min_values = 0,
                max_values = relic_slots,
                options = runner_owned_relics_options
        )
        async def relics_selected(self, select, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your selection!", ephemeral=True)
                return

            runner_stats = self.lobbycommands.bot.users_stats[runner_id]

            runner_stats["equipped_relics"] = []

            for relic_name in select.values:
                runner_stats["equipped_relics"].append(relic_name_to_key(relic_information, relic_name))

            if ("short_levels" in runner_stats["equipped_relics"]) and ("long_levels" in runner_stats["equipped_relics"]):
                runner_stats["equipped_relics"] = []
                await interaction.respond("ERROR: PARADOX DETECTED -- PARADOX RESOLUTION PROTOCOL NOT IMPLEMENTED!")
            else:
                await interaction.response.defer()

            current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
            lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)

            relics_embed = get_relics_embed(interaction, self.lobbycommands, self.runner_id)
            relics_view = get_ascension_buttons_relics(self.lobbycommands, self.lobby_name, self.runner_id)

            await lobby_curr_message.edit(embed=relics_embed, view=relics_view)
            return

        @discord.ui.button(label="Back", style=discord.ButtonStyle.primary)
        async def back_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            self.lobbycommands.bot.save_data()
            await interaction.response.defer()
            await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
            return

        @discord.ui.button(label="Unequip All", style=discord.ButtonStyle.secondary)
        async def unequip_all_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            runner_stats = self.lobbycommands.bot.users_stats[runner_id]

            runner_stats["equipped_relics"] = []

            current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
            lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)

            relics_embed = get_relics_embed(interaction, self.lobbycommands, self.runner_id)
            relics_view = get_ascension_buttons_relics(self.lobbycommands, self.lobby_name, self.runner_id)

            await interaction.response.defer()
            await lobby_curr_message.edit(embed=relics_embed, view=relics_view)
            return

        @discord.ui.button(label="Purchase Relic", emoji="💎", style=discord.ButtonStyle.success)
        async def purchase_relic_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            await interaction.respond("You don't have enough 💎!", ephemeral=True)
            return

    return AscensionButtonsRelics(lobbycommands, lobby_name, runner_id)


def relic_name_to_key(relic_information, relic_name):
    for relic_type in relic_information.keys():
        for relic_key in relic_information[relic_type].keys():
            if relic_information[relic_type][relic_key]["name"] == relic_name:
                return relic_key

    return "RELIC NOT FOUND!"


def get_ascension_buttons_item(lobbycommands, lobby_name, runner_id):
    user_stats = lobbycommands.bot.users_stats[runner_id]

    show_essences = False
    for item in user_stats["essences"]:
        if user_stats["essences"][item] > 0:
            show_essences = True

    proceed_color = discord.ButtonStyle.success
    proceed_emoji = None

    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    if calculate_item_applied_incoming_damage(ascension_lobby) >= ascension_lobby["current_hp"]:
        proceed_color = discord.ButtonStyle.danger
        proceed_emoji = "☠️"

    has_use_winner_usage = relics.use_winner_has_usage(ascension_lobby)

    class AscensionButtonsItem(discord.ui.View):
        def __init__(self, lobbycommands, lobby_name, runner_id):
            super().__init__(timeout=20000)
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

            ascension_lobby["items"]["Apples"] = ascension_lobby["items"]["Apples"] - 1
            ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + get_apple_heal_amount(ascension_lobby)
            #if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]: #clamp to max
            #    ascension_lobby["current_hp"] = ascension_lobby["max_hp"]

            relics.apples_powerup(ascension_lobby)

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

            game_data = self.lobbycommands.bot.game_data
            ascension_lobby = game_data["ascension"][self.runner_id]

            if ascension_lobby["items"]["Ivory Dice"] < 1:
                await interaction.respond("You don't have any Ivory Dice!") #not ephemeral on purpose
                return

            self.stop()

            ascension_lobby["items"]["Ivory Dice"] = ascension_lobby["items"]["Ivory Dice"] - 1
            ascension_lobby["die_used"] = True

            relics.ivory_dice_powerup(ascension_lobby, ascension_lobby["current_hp"], calculate_item_applied_incoming_damage(ascension_lobby))

            await interaction.channel.send("Ivory Die used!")

            await proceed_helper(self, interaction)

        @discord.ui.button(label="Chronograph", style=discord.ButtonStyle.secondary)
        async def chronograph_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            game_data = self.lobbycommands.bot.game_data
            ascension_lobby = game_data["ascension"][self.runner_id]

            if ascension_lobby["items"]["Chronographs"] < 1:
                await interaction.respond("You don't have any Chronographs!")
                return

            self.stop()

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

            sp_cost = get_sp_cost(ascension_lobby)

            await interaction.respond(f"{sp_cost} SP used!")

            ascension_lobby["sp_spent"] = ascension_lobby["sp_spent"] + sp_cost
            ascension_lobby["current_sp"] = ascension_lobby["current_sp"] - sp_cost
            ascension_lobby["sp_times_used"] = ascension_lobby["sp_times_used"] + 1
            await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
            return

        if show_essences:
            @discord.ui.button(label="View Essences", style=discord.ButtonStyle.primary)
            async def view_essences_pressed(self, button, interaction):
                uid = str(interaction.user.id)
                if uid != self.runner_id:
                    await interaction.respond("Not your button!", ephemeral=True)
                    return

                current_lobby = self.lobbycommands.bot.game_data["lobbies"][self.lobby_name]
                lobby_curr_message = await self.lobbycommands.get_lobby_curr_message(current_lobby)
                runner_essences = self.lobbycommands.bot.users_stats[self.runner_id]["essences"]

                game_data = self.lobbycommands.bot.game_data
                ascension_lobby = game_data["ascension"][self.runner_id]

                await interaction.response.defer()
                await lobby_curr_message.edit(embed=get_ascension_essences_embed(interaction, self.lobby_name, self.runner_id, ascension_lobby, runner_essences), view=AscensionButtonsEssences(self.lobbycommands, self.lobby_name, self.runner_id))
                return

        @discord.ui.button(label="Proceed", emoji=proceed_emoji, style=proceed_color)
        async def proceed_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            self.stop()
            await proceed_helper(self, interaction)

        if has_use_winner_usage:
            @discord.ui.button(label="Use Winner's Score", emoji='💾', style=discord.ButtonStyle.primary)
            async def view_essences_pressed(self, button, interaction):
                uid = str(interaction.user.id)
                if uid != self.runner_id:
                    await interaction.respond("Not your button!", ephemeral=True)
                    return

                game_data = self.lobbycommands.bot.game_data
                ascension_lobby = game_data["ascension"][self.runner_id]

                ascension_lobby["incoming_damage"] = ascension_lobby["relic_data"]["use_winner_miss_count"]
                ascension_lobby["relic_data"]["use_winner_uses"] = ascension_lobby["relic_data"]["use_winner_uses"] + 1

                await interaction.response.defer()
                await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
                return

    return AscensionButtonsItem(lobbycommands, lobby_name, runner_id)


class AscensionButtonsEssences(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__(timeout=20000)
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

        self.runner_essences = lobbycommands.bot.users_stats[runner_id]["essences"]

    @discord.ui.button(label="Apple", style=discord.ButtonStyle.secondary)
    async def apple_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        essence_cost = get_essence_cost(ascension_lobby)

        if self.runner_essences["Apples"] < essence_cost:
            await interaction.respond("You don't have enough Apples' Essence!")
            return

        self.runner_essences["Apples"] = self.runner_essences["Apples"] - essence_cost
        ascension_lobby["essence_uses"] = ascension_lobby["essence_uses"] + 1
        ascension_lobby["current_hp"] = ascension_lobby["current_hp"] + get_apple_heal_amount(ascension_lobby)
        #if ascension_lobby["current_hp"] > ascension_lobby["max_hp"]: #clamp to max
        #    ascension_lobby["current_hp"] = ascension_lobby["max_hp"]

        relics.apples_powerup(ascension_lobby)

        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Apples' Essence used!")

    @discord.ui.button(label="Ivory Die", style=discord.ButtonStyle.secondary)
    async def die_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        essence_cost = get_essence_cost(ascension_lobby)

        if self.runner_essences["Ivory Dice"] < essence_cost:
            await interaction.respond("You don't have enough Ivory Dice's Essence!")
            return

        self.stop()

        self.runner_essences["Ivory Dice"] = self.runner_essences["Ivory Dice"] - essence_cost
        ascension_lobby["essence_uses"] = ascension_lobby["essence_uses"] + 1
        ascension_lobby["die_used"] = True

        relics.ivory_dice_powerup(ascension_lobby, ascension_lobby["current_hp"], calculate_item_applied_incoming_damage(ascension_lobby))

        await interaction.channel.send("Ivory Die's Essence used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Chronograph", style=discord.ButtonStyle.secondary)
    async def chronograph_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        essence_cost = get_essence_cost(ascension_lobby)

        if self.runner_essences["Chronographs"] < essence_cost:
            await interaction.respond("You don't have enough Chronographs' Essence!")
            return

        self.stop()

        self.runner_essences["Chronographs"] = self.runner_essences["Chronographs"] - essence_cost
        ascension_lobby["essence_uses"] = ascension_lobby["essence_uses"] + 1
        ascension_lobby["chronograph_used"] = True #this gets checked in roll_level_from_settings, and is set off in finish_match
        await interaction.channel.send("Chronographs' Essence used!")

        await proceed_helper(self, interaction)

    @discord.ui.button(label="Shield", style=discord.ButtonStyle.secondary)
    async def shield_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]

        essence_cost = get_essence_cost(ascension_lobby)

        if self.runner_essences["Shields"] < essence_cost:
            await interaction.respond("You don't have enough Shields' Essence!")
            return

        self.runner_essences["Shields"] = self.runner_essences["Shields"] - essence_cost
        ascension_lobby["essence_uses"] = ascension_lobby["essence_uses"] + 1
        ascension_lobby["shields_used"] = ascension_lobby["shields_used"] + 1
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        await interaction.respond("Shields' Essence used!")

    @discord.ui.button(label="Back", row=1, style=discord.ButtonStyle.primary)
    async def back_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        await interaction.response.defer()
        await self.lobbycommands.edit_current_lobby_message(self.lobby_name, interaction)
        return


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

        # this upcoming level is the final boss
        if ascension_lobby["set_difficulties"][ascension_lobby["level_number"]] == "???":

            if ascension_lobby["ascension_difficulty"] < 4: #no recovering after city 7 at certificate 4
                ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 2))

                await interaction.channel.send("You've made it to the end of City 7!\nThankfully, you're given a bit of reprieve, and heal 1/2 of your remaining HP.")
            
            final_boss_level = {}
            final_boss_level["hash"] = "temp"
            final_boss_level["authors"] = "temp"
            final_boss_level["artist"] = "temp"
            final_boss_level["song"] = "rrr5 lmao"
            final_boss_level["description"] = "temp"
            final_boss_level["difficulty"] = "???"
            final_boss_level["peer review status"] = "Peer Reviewed"
            final_boss_level["total_hits_approx"] = 300
            final_boss_level["zip"] = "https://codex.rhythm.cafe/rodney-s-HGfkpCv3PS3.rdzip"
            final_boss_level["image_url"] = "https://cdn.discordapp.com/emojis/1393723419031244832.webp?size=128"
            final_boss_level["tags"] = []
            final_boss_level["possibilities"] = 1

            auxiliary_lobby["roll_settings"]["level_override"] = final_boss_level

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
        self.lobbycommands.bot.save_data()
        return

    # if last level

    player_stats = self.lobbycommands.bot.users_stats[self.runner_id]

    num_items_to_forage = ascension_lobby["extra"]

    if num_items_to_forage == 0: #the level just played was not a forage level
        gained_exp = 6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"]
        self.lobbycommands.bot.increment_user_stat(self.runner_id, "exp", gained_exp, True)

        if ascension_lobby["s_ranked_so_far"]:
            player_stats["s_ranked_entire_set"] = player_stats["s_ranked_entire_set"] + 1

    # is the last level but not the last set:
    if not is_last_set(ascension_lobby):
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

            if not relics.immediate_foraging(ascension_lobby):
                gain_foraging_items(ascension_lobby, num_items_to_forage)

            await recover_helper(self, interaction)
            return

    # is the last set:
    player_stats["highest_set_beaten"] = max(player_stats["highest_set_beaten"], ascension_lobby["current_set"])
    player_stats["highest_ascension_difficulty_beaten"] = max(player_stats["highest_ascension_difficulty_beaten"], ascension_lobby['ascension_difficulty'])
    player_stats["total_sets_beaten"] = player_stats["total_sets_beaten"] + 1

    if "choose_modifiers" not in player_stats["owned_relics"]:
        player_stats["owned_relics"]["choose_modifiers"] = 1

    # gain exp for a second time since it's doubled on victory
    self.lobbycommands.bot.increment_user_stat(self.runner_id, "exp", gained_exp, True)

    for item in ascension_lobby["items"]:
        player_stats["essences"][item] = player_stats["essences"][item] + (1 + ascension_lobby["ascension_difficulty"]) * ascension_lobby["items"][item]

    victory_random_reward = get_victory_random_reward(interaction, ascension_lobby, ascension_lobby["ascension_difficulty"])
    ascension_lobby["victory_random_reward"] = victory_random_reward

    if victory_random_reward["item"] == "essences":
        player_stats["essences"][victory_random_reward["type"]] = player_stats["essences"][victory_random_reward["type"]] + victory_random_reward["count"]
    else:
        player_stats[victory_random_reward["item"]] = player_stats[victory_random_reward["item"]] + victory_random_reward["count"]

    ascension_lobby["status"] = "Victory"
    auxiliary_lobby["status"] = "Victory"

    await interaction.response.defer()
    await self.lobbycommands.send_current_lobby_message(lobby_name_user_is_hosting, interaction, False)
    self.lobbycommands.bot.save_data()
    return


def get_victory_random_reward(ctx, ascension_lobby, certificate):
    if certificate == 0:
        return {}

    box_dict = {}
    box_dict["item"] = "relic_box"
    box_dict["name"] = "📦 Relic Box"
    box_dict["count"] = 1

    diamonds_dict = {}
    diamonds_dict["item"] = "diamonds"
    diamonds_dict["name"] = "💎"
    diamonds_dict["count"] = certificate

    exp_boosters_dict = {}
    exp_boosters_dict["item"] = "exp_boosters"
    exp_boosters_dict["name"] = "🧪 exp boosters"
    exp_boosters_dict["count"] = (certificate + 1) // 2

    essence_type = random.choice(["Apples", "Ivory Dice", "Chronographs", "Shields"])

    essence_dict = {}
    essence_dict["item"] = "essences"
    essence_dict["type"] = essence_type
    essence_dict["name"] = get_essence_text(ctx, ascension_lobby, essence_type)
    essence_dict["count"] = 5 * certificate

    if 100*random.random() < certificate:
        return box_dict

    return random.choice([diamonds_dict, exp_boosters_dict, essence_dict])


def weighted_choose_from_dict(item_dict):
    item_list = list(item_dict.keys())
    item_weights = list(item_dict.values())
    return random.choices(item_list, weights = item_weights)[0]


def get_ascension_buttons_choice(lobbycommands, lobby_name, runner_id):
    game_data = lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][runner_id]

    forage2_emoji = None
    forage2_emoji = relics.old_foraging_emoji(ascension_lobby, forage2_emoji)

    next_city_modifier_choices = relics.choose_modifiers(ascension_lobby, lobbycommands)

    class AscensionButtonsChoice(discord.ui.View):
        def __init__(self, lobbycommands, lobby_name, runner_id):
            super().__init__(timeout=20000)
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

            if relics.immediate_foraging(ascension_lobby):
                gain_foraging_items(ascension_lobby, 1)

            ascension_lobby["status"] = "Open"
            auxiliary_lobby["status"] = "Open"

            await interaction.response.defer()
            await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
            self.lobbycommands.bot.save_data()

        @discord.ui.button(label="Forage 2", emoji=forage2_emoji, style=discord.ButtonStyle.danger)
        async def forage2_pressed(self, button, interaction):
            uid = str(interaction.user.id)
            if uid != self.runner_id:
                await interaction.respond("Not your button!", ephemeral=True)
                return

            self.stop()

            game_data = self.lobbycommands.bot.game_data
            ascension_lobby = game_data["ascension"][self.runner_id]
            auxiliary_lobby = game_data["lobbies"][self.lobby_name]

            ascension_lobby["extra"] = 2

            if relics.old_foraging_skip_level(ascension_lobby):
                gain_foraging_items(ascension_lobby, 2)
                await recover_helper(self, interaction)
                return

            if relics.immediate_foraging(ascension_lobby):
                gain_foraging_items(ascension_lobby, 2)

            ascension_difficulty = ascension_lobby["ascension_difficulty"]

            if ascension_difficulty < 4:
                (ascension_lobby["set_difficulties"]).append("Tough")
            else:
                (ascension_lobby["set_difficulties"]).append("Very Tough")

            ascension_lobby["status"] = "Open"
            auxiliary_lobby["status"] = "Open"

            await interaction.response.defer()
            await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
            self.lobbycommands.bot.save_data()

        if len(next_city_modifier_choices) > 1:
            @discord.ui.select(
                placeholder = "🧭 Choose next city modifier",
                min_values = 1,
                max_values = 1,
                options = next_city_modifier_choices
            )
            async def relics_selected(self, select, interaction):
                uid = str(interaction.user.id)
                if uid != self.runner_id:
                    await interaction.respond("Not your selection!", ephemeral=True)
                    return

                ascension_lobby["set_modifiers_override"] = [select.values[0]]

                await interaction.response.defer()
                await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
                return

    return AscensionButtonsChoice(lobbycommands, lobby_name, runner_id)

def gain_foraging_items(ascension_lobby, item_count):
    chosen_item = ascension_lobby["chosen_item_1"]
    if item_count > 1:
        chosen_item = ascension_lobby["chosen_item_2"]
    ascension_lobby["items"][chosen_item] = ascension_lobby["items"][chosen_item] + relics.double_foraging_item_count(ascension_lobby, item_count)


async def recover_helper(self, interaction):
    game_data = self.lobbycommands.bot.game_data
    ascension_lobby = game_data["ascension"][self.runner_id]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    if (not relics.old_foraging_skip_level(ascension_lobby)) and (not ((ascension_difficulty >= 6) and (ascension_lobby["current_set"] == 2))):
        if ascension_difficulty < 1: # recover 2/3rds of missing hp
            ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((2*ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 3))
        else: #recover 1/2
            ascension_lobby["current_hp"] = max(ascension_lobby["current_hp"], math.ceil((ascension_lobby["max_hp"] + ascension_lobby["current_hp"]) / 2))

    # progress set
    ascension_lobby["current_set"] = ascension_lobby["current_set"] + 1
    ascension_lobby["level_number"] = 0

    relics.skip_levels_use(ascension_lobby)

    begin_set(self.lobbycommands, self.runner_id, self.lobby_name)
    await interaction.response.defer()
    await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)
    self.lobbycommands.bot.save_data()


class AscensionButtonsGameOver(discord.ui.View):
    def __init__(self, lobbycommands, lobby_name, runner_id):
        super().__init__(timeout=20000)
        self.lobbycommands = lobbycommands
        self.lobby_name = lobby_name
        self.runner_id = runner_id

    @discord.ui.button(label="Main Menu", style=discord.ButtonStyle.primary)
    async def main_menu_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()

        game_data = self.lobbycommands.bot.game_data
        ascension_lobby = game_data["ascension"][self.runner_id]
        auxiliary_lobby = game_data["lobbies"][self.lobby_name]

        ascension_lobby["status"] = "Not Started"
        auxiliary_lobby["status"] = "Not Started"

        await interaction.response.defer()
        await self.lobbycommands.send_current_lobby_message(self.lobby_name, interaction, False)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_pressed(self, button, interaction):
        uid = str(interaction.user.id)
        if uid != self.runner_id:
            await interaction.respond("Not your button!", ephemeral=True)
            return

        self.stop()
        await self.lobbycommands.delete(interaction)


def get_ascension_welcome_embed(self, ctx, name, runner_id):
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
        ticket_cost_text = f"**Starting a new game costs 1 🎫!** (You currently have {runner_tickets} 🎫)"

    ascension_difficulty_text = get_ascension_difficulty_text(ascension_difficulty)

    equipped_relics_text = get_equipped_relics_text(ctx, self, runner_id) + "\n"

    specialization_text = ""
    if ascension_difficulty >= 4:
        if runner_stats['specialization'] == None:
            specialization_text = "You are not specializing in anything.\n\n"
        else:
            specialization_text = f"You are specializing in {runner_stats['specialization']}.\n\n"

    return discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{name}\"", description = f"Runner: <@{runner_id}>\n\n\
    Welcome to World Tour!\n\
Your goal is to treat patients across 5 cities spanning the globe.\n\
You, the **runner**, start with \⭐ HP, and will lose 1 for each miss.\n\
Other players are **support**, and will earn SP for you through good performance.\n\
\nYour progress will save, even if you delete the lobby.\n\
If you reach 0 HP, your tour will be cut short!\n\n{ascension_difficulty_text}{equipped_relics_text}{specialization_text}{ticket_cost_text}")


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

    relics.max_hp(ascension_lobby)

    ascension_lobby["current_sp"] = 0
    ascension_lobby["sp_times_used"] = 0
    ascension_lobby["sp_spent"] = 0

    ascension_lobby["incoming_damage"] = 0
    ascension_lobby["shields_used"] = 0
    ascension_lobby["die_used"] = False
    ascension_lobby["chronograph_used"] = False

    ascension_lobby["current_set"] = 2

    if (ascension_difficulty == 0) or (ascension_difficulty == 7):
        ascension_lobby["current_set"] = 1

    ascension_lobby["level_number"] = 0

    relics.skip_levels_use(ascension_lobby)

    ascension_lobby["items"]["Apples"] = 0
    ascension_lobby["items"]["Ivory Dice"] = 1
    ascension_lobby["items"]["Chronographs"] = 0
    ascension_lobby["items"]["Shields"] = 0

    ascension_lobby["essence_uses"] = 0

    ascension_lobby["lobby_relics"] = runner_stats["equipped_relics"]

    specialization = runner_stats["specialization"]
    ascension_lobby["specialization"] = specialization

    if (ascension_difficulty >= 4) and (specialization != None):
        ascension_lobby["items"][specialization] = ascension_lobby["items"][specialization] + 1

    ascension_lobby["extra"] = 0

    ascension_lobby["no_levels_found_damage_multiplier"] = 1

    ascension_lobby["set_modifiers_override"] = []

    ascension_lobby["relic_data"] = {}
    relics.skip_levels_initialize_data(ascension_lobby)
    relics.use_winner_initialize_data(ascension_lobby)

    self.bot.save_data()

    begin_set(self, runner_id, lobby_name)


def get_set_modifier_options(ascension_lobby, set_number, lobbycommands):
    sets_config = lobbycommands.bot.get_sets_config()
    set_number_str = str(set_number)
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    if len(ascension_lobby["set_modifiers_override"]) > 0:
        return ascension_lobby["set_modifiers_override"]

    if (ascension_difficulty < 7) or (set_number % 2 == 0):
        return sets_config[set_number_str]['modifier']

    return sets_config[set_number_str]['modifier_hard']


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

    set_modifier_options = get_set_modifier_options(ascension_lobby, ascension_lobby['current_set'], self)
    ascension_lobby["set_modifiers_override"] = []

    if len(set_modifier_options) != 0:
        set_modifier = random.choice(set_modifier_options)

    ascension_lobby['set_modifier'] = set_modifier

    ascension_lobby['roll_theme_tags'] = sets_config[set_theme]['tags']
    ascension_lobby['roll_theme_facets'] = sets_config[set_theme]['facets']
    ascension_lobby['roll_modifier_tags'] = sets_config[set_modifier]['tags']
    ascension_lobby['roll_modifier_facets'] = sets_config[set_modifier]['facets']

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

    if (ascension_difficulty >= 3) and (set_number == 7):
        ascension_lobby['set_difficulties'].append("???")

    ascension_lobby["chosen_item_1"] = None
    ascension_lobby["chosen_item_2"] = None

    self.bot.save_data()


def get_ascension_open_embed(lobbycommands, ctx, lobby_name, runner_id, players_id_dict, is_open):
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

    equipped_relics_text = get_equipped_relics_text(ctx, lobbycommands, runner_id) + "\n\n"

    items_text = get_current_items_text(ctx, ascension_lobby)

    ascension_difficulty_text = get_ascension_difficulty_text(ascension_difficulty)

    support_list = []
    for id in players_id_dict:
        support_list.append('<@' + id + '>')

    support_list.remove(f"<@{runner_id}>") #will always be included bc ascension

    support = ', '.join(support_list)

    is_open_text = "\n"
    if is_open:
        is_open_text = "# This lobby is open!\nPress \"**Join**\" to join.\n\n"

    embed = discord.Embed(colour = discord.Colour.blue(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\
{is_open_text}{ascension_difficulty_text}Levels: {set_difficulties_text}\n\n{theme_and_modifier_desc}{equipped_relics_text}{items_text}**Support:** {support}")
    embed.set_footer(text="Buttons broke? Use /lobby resend")
    return embed


def set_roll_settings(lobbycommands, lobby_name, runner_id, use_theme):
    ascension_lobby = lobbycommands.bot.game_data["ascension"][runner_id]
    auxiliary_lobby = lobbycommands.bot.game_data["lobbies"][lobby_name]

    level_number = ascension_lobby["level_number"]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    roll_settings = auxiliary_lobby["roll_settings"]

    roll_settings["peer_reviewed"] = "Yes"
    roll_settings["played_before"] = "No"
    roll_settings["difficulty"] = ascension_lobby["set_difficulties"][level_number]
    roll_settings["special"] = []

    tag_facet_array = []

    def append_tag_facet_options_to_array(tags, facets):
        if (tags != []) or (facets != {}):
            tag_facet_options = {}
            tag_facet_options["tags"] = tags.copy()
            tag_facet_options["facets"] = facets.copy()
            tag_facet_array.append(tag_facet_options)

    if use_theme:
        append_tag_facet_options_to_array(ascension_lobby["roll_theme_tags"], ascension_lobby["roll_theme_facets"])
        roll_settings["special"] = (ascension_lobby["roll_special"]).copy()

    append_tag_facet_options_to_array(ascension_lobby["roll_modifier_tags"], ascension_lobby["roll_modifier_facets"])

    roll_settings["tag_facet_array"] = tag_facet_array

    roll_settings["require_gameplay"] = True
    roll_settings["difficulty_modifiers"] = []

    sets_config = lobbycommands.bot.get_sets_config()
    set_modifier = ascension_lobby["set_modifier"]

    if (set_modifier != "None") and ("difficulty_modifiers" in sets_config[set_modifier]):
        roll_settings["difficulty_modifiers"] = sets_config[set_modifier]["difficulty_modifiers"]

    set_number = ascension_lobby["current_set"]

    if (ascension_difficulty >= 3) and (set_number != 3) and ((roll_settings["difficulty"] == "Easy") or (roll_settings["difficulty"] == "Medium")):
        c3_modifier_name = ascension_lobby["certificate_3_modifiers"][level_number]

        roll_settings["difficulty_modifiers"].append(c3_modifier_name)

        append_tag_facet_options_to_array(sets_config[c3_modifier_name]["tags"], sets_config[c3_modifier_name]["facets"])

    if (ascension_difficulty >= 5) and (set_number != 5) and (roll_settings["difficulty"] == "Easy"):
        c5_modifier_name = ascension_lobby["certificate_5_modifiers"][level_number]

        roll_settings["difficulty_modifiers"].append(c5_modifier_name)

        append_tag_facet_options_to_array(sets_config[c5_modifier_name]["tags"], sets_config[c5_modifier_name]["facets"])
    
    roll_settings["difficulty_modifiers"] = list(set(roll_settings["difficulty_modifiers"]))

    # unless 2-player modifier is active, make sure the level has a 1p
    if "2-Player" not in roll_settings["difficulty_modifiers"]:
        single_player_facet = {}
        single_player_facet["single_player"] = 1
        append_tag_facet_options_to_array([], single_player_facet)

    relics.short_levels_roll_settings(ascension_lobby, roll_settings)
    relics.long_levels_roll_settings(ascension_lobby, roll_settings)

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

    level_embed = discord.Embed(colour = discord.Colour.green(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
Make sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, press \"**Ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}", image = level_image)
    levels.add_level_to_embed(level_embed, level_chosen)

    if level_chosen['difficulty'] == "???":
        level_embed.add_field(name = f"‼️ Modifier: None!", value = "City 7's usual modifier does **NOT** apply to this level!", inline = False)
    elif (set_modifier != "None"):
        level_embed.add_field(name = f"‼️ Modifier: **{set_modifier}**", value = sets_config[set_modifier]['description'], inline = False)

    level_number = ascension_lobby["level_number"]
    ascension_difficulty = ascension_lobby["ascension_difficulty"]

    if (ascension_difficulty >= 3) and (set_number != 3) and ((level_chosen['difficulty'] == "Easy") or (level_chosen['difficulty'] == "Medium")):
        c3_modifier = ascension_lobby['certificate_3_modifiers'][level_number]
        level_embed.add_field(name = f"<:gold:1399860113883402270> Extra Modifier: **{c3_modifier}**", value = sets_config[c3_modifier]['description'], inline = False)

    if (ascension_difficulty >= 5) and (set_number != 5) and (level_chosen['difficulty'] == "Easy"):
        c5_modifier = ascension_lobby['certificate_5_modifiers'][level_number]
        level_embed.add_field(name = f"<:illustrious:1399860117700087888> Extra Modifier: **{c5_modifier}**", value = sets_config[c5_modifier]['description'], inline = False)

    if (ascension_difficulty >= 5) and (level_chosen['difficulty'] == "???"):
        level_embed.add_field(name = f"<:illustrious:1399860117700087888> Extra Modifier: **Hard Difficulty Button**", value = "You must use the hard difficulty button!", inline = False)

    return level_embed


def get_ascension_item_embed(ctx, lobby_name, runner_id, ascension_lobby):
    items_text = get_current_items_text(ctx, ascension_lobby)

    sp_cost = get_sp_cost(ascension_lobby)

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
You are about to take {calculate_item_applied_incoming_damage(ascension_lobby)} damage!\n\
Press the corresponding button below to use an item.\n\n\
{items_text}Press \"**Use SP**\" to spend {sp_cost} SP to reduce incoming damage by 3. (This is more expensive if you have a lot of SP!)")
    return level_embed


def get_sp_cost(ascension_lobby):
    sp_cost = max(5, ascension_lobby['current_sp'] // 2)
    sp_cost = relics.cheaper_sp(ascension_lobby, sp_cost)
    return sp_cost


def get_ascension_essences_embed(ctx, lobby_name, runner_id, ascension_lobby, runner_essences):
    essences_text = get_essences_text(ctx, ascension_lobby, runner_essences)

    set_number = ascension_lobby["current_set"]

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
You are about to take {calculate_item_applied_incoming_damage(ascension_lobby)} damage!\n\
Press the corresponding button below to activate an essence.\n\n\
{essences_text}")
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

    recover_text = f"You will recover {recover_fraction} of your missing HP __at the start of the next set__.\n\n"
    if (ascension_difficulty >= 6) and (ascension_lobby["current_set"] == 2):
        recover_text = ""

    forage2_text = f"play an extra {forage_2_difficulty}"
    forage2_text = relics.old_foraging_forage2_text(ascension_lobby, forage2_text)

    level_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have beaten this set and have {ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP!\n\
You have also gained {gained_exp} additional \🎵.\n\n\
{recover_text}\
You can choose to **proceed** to the next set now...\n\
Or, you can first play an extra {forage_1_difficulty} this set to **forage 1** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_1'])}...\n\
Or, you can {forage2_text} to **forage 2** {get_item_text(ctx, ascension_lobby, ascension_lobby['chosen_item_2'])}.")
    return level_embed


def get_ascension_gameover_embed(lobbycommands, lobby_name, runner_id, ascension_lobby):
    set_number = str(ascension_lobby['current_set'])

    gameover_embed = discord.Embed(colour = discord.Colour.red(), title = f"World Tour Lobby: \"{lobby_name}\" | CITY {set_number}", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP)\n\n\
You have run out of HP! GAME OVER!\n\n\
Press **Main Menu** to try again, or press **Delete** to delete this lobby.")
    return gameover_embed


def get_ascension_victory_embed(lobby_name, runner_id, ascension_lobby):
    gained_exp = 2 * (6 + ascension_lobby["ascension_difficulty"] + ascension_lobby["current_set"])

    total_essence = 0
    for item in ascension_lobby["items"]:
        total_essence = total_essence + (1 + ascension_lobby["ascension_difficulty"]) * ascension_lobby["items"][item]

    compass_text = ""
    certification_text = ""
    if ascension_lobby["ascension_difficulty"] == 0:
        compass_text = "You have been issued your Heart's Compass! Equip it through Relics.\n\n"
    else:
        certification_text = "**{ CERTIFICATE " + str(ascension_lobby["ascension_difficulty"]) + " OBTAINED }**\n\n"

    spec_unlocked_text = ""
    if ascension_lobby["ascension_difficulty"] == 3:
        spec_unlocked_text = "**You can now specialize!**\n\n"

    victory_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"World Tour Lobby: \"{lobby_name}\" | **VICTORY!**", description = f"Runner: <@{runner_id}> ({ascension_lobby['current_hp']}/{ascension_lobby['max_hp']} HP) [{ascension_lobby['current_sp']} SP]\n\n\
{certification_text}YOU WIN! Congratulations!!!!!\n\
You have gained {gained_exp} additional \🎵.\n\
Your remaining items have been converted to {total_essence} total essence.\n\
You have earned a random special reward: {ascension_lobby['victory_random_reward']['count']} {ascension_lobby['victory_random_reward']['name']}!\n\n{spec_unlocked_text}{compass_text}\
-# You can now attempt Certification {ascension_lobby['ascension_difficulty']+1}...")
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


def get_essences_text(ctx, ascension_lobby, runner_essences):
    essence_cost = get_essence_cost(ascension_lobby)

    items_text = "*Your essences (hover for info):*\n"
    for item in runner_essences.keys():
        items_text = items_text + get_essence_text(ctx, ascension_lobby, item)
        items_text = items_text + " x" + str(runner_essences[item]) + "\n"

    items_text = items_text + f"\nYou can spend **{str(essence_cost)}** of an essence in order to activate its respective item effect. (This cost doubles per essence usage this run.)"

    return items_text


def get_essence_cost(ascension_lobby):
    base_cost = 5
    base_cost = relics.cheaper_essence(ascension_lobby, base_cost)
    return base_cost * (2 ** ascension_lobby["essence_uses"])


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


def get_essence_text(ctx, ascension_lobby, item):
    if item == "Apples":
        return f"🌿 [Apples]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to recover {get_apple_heal_amount(ascension_lobby)} HP\")' Essence"
    elif item == "Ivory Dice":
        return f"🪸 [Ivory Dice]({ctx.channel.jump_url} \"After playing a level, INSTEAD OF taking damage, use this item to reroll it\")'s Essence"
    elif item == "Chronographs":
        return f"🍄 [Chronographs]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to REPLAY the level for a better score\")' Essence"
    elif item == "Shields":
        return f"🪻 [Shields]({ctx.channel.jump_url} \"After playing a level, BEFORE taking damage, use this item to halve incoming damage\")' Essence"
    else:
        return "HUGE MISTAKE"


def get_apple_heal_amount(ascension_lobby):
    if ascension_lobby["ascension_difficulty"] < 2:
        return 10
    elif ascension_lobby["ascension_difficulty"] < 6:
        return 15
    else:
        return 25


def get_ascension_difficulty_text(ascension_difficulty):
    if ascension_difficulty < 1:
        return ""

    ascension_difficulty_text = "**Certifications:**"

    if ascension_difficulty >= 1:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:bronze:1399860108665557043> Starting runs costs 1 🎫 **/** Recovering heals less HP **/** Clear cities 2-6"
    if ascension_difficulty >= 2:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:silver:1399860110389542915> Easier levels deal more damage **/** Clear cities 2-7 **/** Apples heal more"
    if ascension_difficulty >= 3:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:gold:1399860113883402270> City 3 invades easier levels **/** City 3 is harder **/** The final boss appears"
    if ascension_difficulty >= 4:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:distinguished:1399860116119093529> More difficult foraging **/** No recovery in City 7 **/** Unlock specialization" # hard button
    if ascension_difficulty >= 5:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:illustrious:1399860117700087888> City 5 invades easy levels **/** City 5 is harder **/** Hard button final boss"
    if ascension_difficulty >= 6:
        ascension_difficulty_text = ascension_difficulty_text + "\n<:stellar:1399860119092854936> All levels deal more damage **/** No City 2 recovery **/** Apples heal more"
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

    shield_block_factor = 2
    shield_block_factor = relics.shields_powerup(ascension_lobby, shield_block_factor)

    # use shields
    applied_incoming_damage = applied_incoming_damage // (shield_block_factor ** ascension_lobby["shields_used"])
    # use sp
    applied_incoming_damage = applied_incoming_damage - (3 * ascension_lobby["sp_times_used"])

    applied_incoming_damage = max(0, applied_incoming_damage)

    return applied_incoming_damage


async def no_levels_found(lobby_commands, ctx, runner_id, ascension_lobby, auxiliary_lobby, lobby_name):
    await ctx.channel.send("No levels found! Rerolling without theme...")

    set_roll_settings(lobby_commands, lobby_name, runner_id, False)

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