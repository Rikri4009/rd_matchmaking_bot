import discord
from discord.ext import commands
import time
import re
import math
import asyncio
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.misc as misc
import rd_matchmaking_bot.utils.ascension as ascension


class LobbyButtonsOpen(discord.ui.View):
    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def join_pressed(self, button, interaction):
        lobby_title = interaction.message.embeds[0].title
        lobby_name = re.findall('"([^"]*)"', lobby_title)[0]
        await LobbyCommands.join(interaction, lobby_name)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary)
    async def leave_pressed(self, button, interaction):
        await LobbyCommands.leave(interaction)

    @discord.ui.button(label="Roll Level", style=discord.ButtonStyle.primary)
    async def roll_pressed(self, button, interaction):
        await LobbyCommands.roll(interaction, "Yes", "No", "Any", "")


class LobbyButtonsRolling(discord.ui.View):
    @discord.ui.button(label="Ready", style=discord.ButtonStyle.success)
    async def ready_pressed(self, button, interaction):
        await LobbyCommands.ready(interaction)

    @discord.ui.button(label="Unready", style=discord.ButtonStyle.secondary)
    async def unready_pressed(self, button, interaction):
        await LobbyCommands.unready(interaction)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
    async def leave_pressed(self, button, interaction):
        await LobbyCommands.leave(interaction)


class LobbyCommands(commands.Cog):
    lobby = discord.SlashCommandGroup("lobby", "Lobby commands")


    def __init__(self, bot: MatchmakingBot):
        self.bot = bot


    def get_lobby_open_embed(self, lobby_name, host_id, player_id_dict):
        player_list = []
        for id in player_id_dict:
            player_list.append('<@' + id + '>')

        players = ', '.join(player_list)

        return discord.Embed(colour = discord.Colour.blue(), title = f"Free Play Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n# This lobby is open!\nPress \"**Join**\" to join.\n\n**Players:** {players}")


    def get_lobby_rolling_embed(self, lobby_name, host_id, player_id_dict, level_chosen):
        ready_list = ''

        for id in player_id_dict:
            ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

        level_embed = discord.Embed(colour = discord.Colour.green(), title = f"Free Play Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n\nMake sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, press \"**Ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}\n", image = level_chosen['image_url'])
        levels.add_level_to_embed(level_embed, level_chosen)
        return level_embed


    def get_lobby_playing_embed(self, mode, lobby_name, host_id, player_id_dict):
        submitted_list = ''

        for id in player_id_dict:
            submitted_list = submitted_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

        host_title = "Host"
        if mode == "Ascension":
            host_title = "Runner"

        return discord.Embed(colour = discord.Colour.red(), title = f"{mode} Lobby: \"{lobby_name}\"", description = f"{host_title}: <@{host_id}>\n\nMake sure you do `/lobby already_seen` if you recognize this level!\nOtherwise, when you\'re done, do `/lobby submit_misses` to submit your miss count.\nOnce everyone submits, final results will be posted. (The host should kick AFK players.)\n\n{submitted_list}")


    # pseudo-state machine my beloved
    def get_current_lobby_embed(self, ctx, lobby_name):
        current_lobby = self.bot.game_data["lobbies"][lobby_name]
        mode = current_lobby["mode"]
        status = current_lobby["status"]
        host_id = current_lobby["host"]
        player_id_dict = current_lobby["players"]
        level_chosen = current_lobby["level"]

        if mode == 'Free Play':
            if status == 'Open':
                return self.get_lobby_open_embed(lobby_name, host_id, player_id_dict)
            elif status == 'Rolling':
                return self.get_lobby_rolling_embed(lobby_name, host_id, player_id_dict, level_chosen)
            elif status == 'Playing':
                return self.get_lobby_playing_embed(mode, lobby_name, host_id, player_id_dict)
        elif mode == 'Ascension':
            if host_id not in self.bot.game_data["ascension"]:
                self.bot.game_data["ascension"][host_id] = {}
                self.bot.validate_game_data()
                self.bot.save_data()
            
            ascension_lobby = self.bot.game_data["ascension"][host_id]

            if status == 'Not Started':
                return ascension.get_ascension_welcome_embed(self, lobby_name, host_id)
            elif status == 'Open':
                return ascension.get_ascension_open_embed(self, ctx, lobby_name, host_id, player_id_dict)
            elif status == 'Rolling':
                return ascension.get_ascension_rolling_embed(self, lobby_name, host_id, player_id_dict, level_chosen, ascension_lobby)
            elif status == 'Playing':
                return self.get_lobby_playing_embed(mode, lobby_name, host_id, player_id_dict)
            elif status == 'Item':
                return ascension.get_ascension_item_embed(ctx, lobby_name, host_id, ascension_lobby)
            elif status == 'Choice':
                return ascension.get_ascension_choice_embed(ctx, lobby_name, host_id, ascension_lobby)
            elif status == 'Game Over':
                return ascension.get_ascension_gameover_embed(self, lobby_name, host_id, ascension_lobby)
            elif status == 'Victory':
                return ascension.get_ascension_victory_embed(lobby_name, host_id, ascension_lobby)
        print('Huge Mistake')


    def get_current_lobby_view(self, lobby_name):
        current_lobby = self.bot.game_data["lobbies"][lobby_name]
        mode = current_lobby["mode"]
        status = current_lobby["status"]
        host_id = current_lobby["host"]
        player_id_dict = current_lobby["players"]
        level_chosen = current_lobby["level"]
        if status == 'Not Started':
            return ascension.AscensionButtonsWelcome(self, lobby_name, host_id)
        elif status == 'Open':
            return LobbyButtonsOpen()
        elif status == 'Rolling':
            return LobbyButtonsRolling()
        elif status == 'Playing':
            return None
        elif status == 'Item':
            return ascension.AscensionButtonsItem(self, lobby_name, host_id)
        elif status == 'Choice':
            return ascension.AscensionButtonsChoice(self, lobby_name, host_id)
        elif status == 'Game Over':
            return ascension.AscensionButtonsGameOver(self, lobby_name, host_id)
        elif status == 'Victory':
            return ascension.AscensionButtonsGameOver(self, lobby_name, host_id)
        print('Huge Mistake')


    async def send_current_lobby_message(self, lobby_name, ctx, is_response): #is_response currently unused
        if lobby_name not in self.bot.game_data["lobbies"]:
            return

        current_lobby = self.bot.game_data["lobbies"][lobby_name]
        lobby_embed = self.get_current_lobby_embed(ctx, lobby_name)
        lobby_view = self.get_current_lobby_view(lobby_name)

        #await self.disable_current_message_view(current_lobby)

        message = None
        if is_response:
            message = await ctx.respond(embed=lobby_embed, view=lobby_view)
        else:
            message = await ctx.channel.send(embed=lobby_embed, view=lobby_view)

        current_lobby["channel_id"] = message.channel.id
        current_lobby["message_id"] = message.id

        for player_id in current_lobby["players"]:
            dm_message = ""

            new_achievements_message = self.bot.pop_user_achievement_changes(ctx, player_id)
            if new_achievements_message != None:
                dm_message = dm_message + new_achievements_message

            completed_quests_message = self.bot.pop_user_completed_quests(player_id)
            if completed_quests_message != None:
                dm_message = dm_message + completed_quests_message

            if dm_message != "":
                player_user = await self.bot.fetch_user(player_id)
                player_dm_channel = player_user.dm_channel

                if player_dm_channel == None:
                    player_dm_channel = await player_user.create_dm()

                await player_dm_channel.send(dm_message)


    async def disable_current_message_view(self, current_lobby): #doesnt work???
        if "message_id" in current_lobby:
            lobby_curr_message = await (await self.bot.fetch_channel(current_lobby["channel_id"])).fetch_message(current_lobby["message_id"])
            for component in lobby_curr_message.components:
                if isinstance(component, discord.ActionRow):
                    for child in component.children:
                        child.disabled = True


    async def edit_current_lobby_message(self, lobby_name, ctx):
        current_lobby = self.bot.game_data["lobbies"][lobby_name]

        lobby_channel_id = current_lobby["channel_id"]

        lobby_embed = self.get_current_lobby_embed(ctx, lobby_name)
        lobby_view = self.get_current_lobby_view(lobby_name)

        lobby_curr_message = await (await self.bot.fetch_channel(lobby_channel_id)).fetch_message(current_lobby["message_id"])

        await lobby_curr_message.edit(embed=lobby_embed, view=lobby_view)

    
    @lobby.command(description="List all existing lobbies")
    async def list_all(self, ctx
    ):
        current_lobbies = self.bot.game_data['lobbies']

        # if there are no lobbies
        if len(current_lobbies) == 0:
            await ctx.respond(f'There are currently no lobbies!', ephemeral=True)
            return

        lobby_list_message = ''
        for name in current_lobbies:
            lobby_list_message = lobby_list_message + f"{name}: {len(current_lobbies[name]['players'])} Players (<#{current_lobbies[name]['channel_id']}>)\n"

        await ctx.respond(lobby_list_message, ephemeral=True)


    @lobby.command(description="Create a lobby")
    async def create(self, ctx,
        name: discord.Option(discord.SlashCommandOptionType.string, description = 'Lobby name'),
        mode: discord.Option(choices = ['Free Play', 'World Tour', 'Archipelago'], description = 'Free Play is the standard lobby mode, World Tour is the roguelike')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        if name.startswith('the light'): #secret
            await ctx.respond(f'That lobby name is already in use...!?', ephemeral=True)
            return

        # if user is already in a lobby
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting != None:
            await ctx.respond(f'You are already hosting the lobby \"{lobby_name_user_is_hosting}\"!', ephemeral=True)
            return

        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in != None:
            await ctx.respond(f'You are already in the lobby \"{lobby_name_user_is_playing_in}\"!', ephemeral=True)
            return

        # if a lobby with that name exists
        if name in current_lobbies:
            await ctx.respond(f'That lobby name is already in use!', ephemeral=True)
            return

        if mode == "Archipelago":
            await ctx.respond("That mode is currently being implemented!", ephemeral=True)
            return

        if mode == "World Tour":
            user_achievements = self.bot.get_user_achievements(ctx, uid)
            if user_achievements['total'] < 10:
                await ctx.respond("You need at least 10★ in order to be the runner!", ephemeral=True)
                return
            mode = "Ascension"

        current_lobbies[name] = {}
        current_lobby = current_lobbies[name]

        current_lobby['mode'] = mode
        current_lobby['host'] = uid
        current_lobby['players'] = {}
        current_lobby['players'][uid] = {}
        current_lobby['players'][uid]['ready_status'] = 'Not Ready'
        current_lobby['players'][uid]['miss_count'] = None
        current_lobby['roll_settings'] = {}
        current_lobby['level'] = {}

        if mode == "Free Play":
            current_lobby['status'] = 'Open'
        elif mode == "Ascension":
            current_lobby['status'] = 'Not Started'

        if mode == "Free Play":
            await ctx.respond(f"<@{uid}> You have started hosting the lobby \"{name}\"!\n\
Make sure to press \"**Leave**\" if you don't want to play.\n\
Do `/lobby kick [player]` to kick an AFK player.\n\
Do `/lobby transfer_host [player]` to transfer host status to another player.\n\
Do `/lobby delete` to delete this lobby. (Don't do this until after level results are sent, it's rude!)\n\n\
Once everyone has joined, do `/lobby roll` to roll a level.", ephemeral=True)
        elif mode == "Ascension":
            await ctx.respond(f"<@{uid}> You have started hosting the lobby \"{name}\"!\n\
Do `/lobby kick [player]` to kick an AFK player.\n\
Do `/lobby delete` to delete this lobby. (Your current run will be saved.)\n\n\
Once everyone has joined, do `/lobby roll` to roll a level.", ephemeral=True)

        await self.send_current_lobby_message(name, ctx, False)

        self.bot.save_data()


    @lobby.command(description="Join a specified lobby")
    async def join(self, ctx,
        name: discord.Option(discord.SlashCommandOptionType.string, description = 'Name of lobby to join')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        if name == 'the light': #secret
            await ctx.respond(f'\"Whoa whoa hang on, you think I\'m gonna just let you do THAT?\"\n\
\"If you really want to prove your worth, make a World Tour lobby!\"\n\
\"...What, you want an achievement? Just for finding this place? But that one\'s MINE! And you barely did any work!\"\n\
\"Fine, I\'ll give you something... if you can survive my level! Given its... PR status, this should be fun to watch...\"', ephemeral=True)

        # if user is playing in a lobby
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in != None:
            await ctx.respond(f'You are already playing in the lobby \"{lobby_name_user_is_playing_in}\"!', ephemeral=True)
            return

        # if user is hosting a lobby different to this one
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if (lobby_name_user_is_hosting != None) and (lobby_name_user_is_hosting != name):
            await ctx.respond(f'You are already hosting the lobby \"{lobby_name_user_is_hosting}\"!', ephemeral=True)
            return

        # if lobby doesn't exist
        if name not in current_lobbies:
            await ctx.respond(f'That lobby doesn\'t exist!', ephemeral=True)
            return

        user_channel_id = ctx.channel.id

        current_lobby = current_lobbies[name]

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        # if user isn't in lobby's channel
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if lobby is not open
        if current_lobby['status'] == 'Rolling':
            await ctx.respond(f'That lobby is already rolling for a level! (Consider asking the host to `/lobby unroll` so that you can join.)', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'That lobby is already playing!', ephemeral=True)
            return
        elif current_lobby['status'] != 'Open':
            await ctx.respond(f'That lobby is not open!', ephemeral=True)
            return

        # if user doesn't have an rdsettings
        if uid not in self.bot.users_rdsaves:
            await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use `/upload_rdsave` to do this.)', ephemeral=True)
            return

        current_lobby['players'][uid] = {}
        current_lobby['players'][uid]['ready_status'] = 'Not Ready'
        current_lobby['players'][uid]['miss_count'] = None

        await ctx.respond(f'Joined \"{name}\".\nWait for the host to roll a level...', ephemeral=True)
        await lobby_channel.send(f'<@{uid}> Joined \"{name}\"!')

        await self.edit_current_lobby_message(name, ctx)


    @lobby.command(description="Leave the lobby you're in")
    async def leave(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not playing
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in == None:
            await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_playing_in]

        # if host tries to leave ascension lobby
        if (current_lobby["mode"] != "Free Play") and (uid == current_lobby["host"]):
            await ctx.respond(f"You can't do that in this mode!", ephemeral=True)
            return

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        # remove user from current lobby they're in
        del current_lobby['players'][uid]

        await ctx.respond(f'Left \"{lobby_name_user_is_playing_in}\".', ephemeral=True)
        await lobby_channel.send(f'<@{uid}> left \"{lobby_name_user_is_playing_in}\".')

        # edit lobby message
        await self.edit_current_lobby_message(lobby_name_user_is_playing_in, ctx)

        lobby_host = current_lobbies[lobby_name_user_is_playing_in]['host']
        await self.is_everyone_ready(ctx, lobby_name_user_is_playing_in, lobby_host)
        await self.has_everyone_submitted(ctx, lobby_name_user_is_playing_in, lobby_host)


    @lobby.command(description="Kick a player from your lobby")
    async def kick(self, ctx,
        player: discord.Option(discord.SlashCommandOptionType.user)
    ):
        current_lobbies = self.bot.game_data["lobbies"]
        current_lobby = current_lobbies[lobby_name_user_is_hosting]

        uid = str(ctx.user.id)
        player_to_kick = str(player.id)

        # if not free play and host tries to kick themselves
        if (current_lobby["mode"] != "Free Play") and (uid == player_to_kick):
            await ctx.respond(f"You can't leave in this mode!", ephemeral=True)
            return

        # if user is not hosting
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting == None:
            await ctx.respond(f'You are not hosting!', ephemeral=True)
            return

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if player is not in the lobby
        if player_to_kick not in current_lobby['players']:
            await ctx.respond(f'User not found in lobby!', ephemeral=True)
            return

        # kick player
        del current_lobby['players'][player_to_kick]

        await ctx.respond(f'Kicked <@{player_to_kick}>.')

        # edit lobby message
        await self.edit_current_lobby_message(lobby_name_user_is_hosting, ctx)

        await self.is_everyone_ready(ctx, lobby_name_user_is_hosting, uid)
        await self.has_everyone_submitted(ctx, lobby_name_user_is_hosting, uid)


    @lobby.command(description="Transfer a lobby you're hosting to a player in the lobby")
    async def transfer_host(self, ctx,
        player: discord.Option(discord.SlashCommandOptionType.user)
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not hosting
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting == None:
            await ctx.respond(f"You are not hosting!", ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_hosting]

        # if not free play
        if current_lobby["mode"] != "Free Play":
            await ctx.respond(f"You can't do that in this mode!", ephemeral=True)
            return

        lobby_channel_id = current_lobby["channel_id"]

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if player is not in the lobby
        player_to_transfer_to = str(player.id)
        if player_to_transfer_to not in current_lobby['players']:
            await ctx.respond(f'User not found in lobby!', ephemeral=True)
            return

        # transfer ownership
        current_lobby['host'] = player_to_transfer_to

        await ctx.respond(f'Transferred host to <@{player_to_transfer_to}>.')

        # edit lobby message
        await self.edit_current_lobby_message(lobby_name_user_is_hosting, ctx)


    @lobby.command(description="Delete your lobby")
    async def delete(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not hosting
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting == None:
            await ctx.respond(f'You are not hosting!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_hosting]

        # edit lobby message
        lobby_channel_id = current_lobby['channel_id']
        try:
            lobby_curr_message = await (await self.bot.fetch_channel(lobby_channel_id)).fetch_message(current_lobby['message_id'])
            if lobby_curr_message != None:
                if (current_lobby["status"] != "Game Over") and (current_lobby["status"] != "Victory"):
                    await lobby_curr_message.edit(f"This lobby \"{lobby_name_user_is_hosting}\" has been deleted!", embed=None, view=None)
                else:
                    await lobby_curr_message.edit(lobby_curr_message.content, embed=None, view=None)
        except:
            #print(current_lobbies[lobby_name_user_is_hosting])
            print("Lobby message edit failed in delete")

        del current_lobbies[lobby_name_user_is_hosting]

        await ctx.respond(f'Deleted \"{lobby_name_user_is_hosting}\".')

        self.bot.save_data()


    def roll_level_from_settings(self, lobby_name):
        current_lobby = self.bot.game_data["lobbies"][lobby_name]

        roll_settings = current_lobby["roll_settings"]

        # chronograph used: same level, played before
        if current_lobby["mode"] == "Ascension":
            runner_id = current_lobby["host"]
            ascension_lobby = self.bot.game_data["ascension"][runner_id]
            if ascension_lobby["chronograph_used"]:
                roll_settings["played_before"] = "Yes"
                return
            else:
                roll_settings["played_before"] = "No"

        peer_reviewed = roll_settings["peer_reviewed"]
        played_before = roll_settings["played_before"]
        difficulty = roll_settings["difficulty"]
        tags = roll_settings["tags"]
        facets = roll_settings["facets"]
        require_gameplay = roll_settings["require_gameplay"]

        roll_player_id_list = (current_lobby["players"]).keys()
        users_rdsaves = self.bot.users_rdsaves

        current_lobby["level"] = levels.roll_random_level(peer_reviewed, played_before, difficulty, roll_player_id_list, users_rdsaves, tags, facets, require_gameplay)


    @lobby.command(description="Roll a random level for your lobby with specified settings")
    async def roll(self, ctx,
        peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
        played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
        difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Not Easy', 'Not Very Tough', 'Polarity'], default = 'Any', description = 'Default: Any'),
        tags: discord.Option(discord.SlashCommandOptionType.string, default = '', description = 'List of tags the level must have. Default: None')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not hosting
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting == None:
            await ctx.respond(f'You are not hosting!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_hosting]

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        if ctx.channel.id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if lobby is not in open state
        if current_lobby['status'] == 'Rolling':
            await ctx.respond(f'Your lobby has already rolled a level! Use `/lobby unroll` to re-open your lobby.', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing, or is waiting on people to submit their miss counts! Kick AFK players if you must.', ephemeral=True)
            return
        elif current_lobby['status'] != 'Open':
            await ctx.respond(f'Your lobby is not open!', ephemeral=True)
            return

        # if no one is playing
        if len(current_lobby['players']) == 0:
            await ctx.respond(f'No one is playing!', ephemeral=True)
            return

        current_lobby["status"] = "Rolling"

        if current_lobby["mode"] == "Free Play":
            tags_array = tags.split(',')
            if tags == '':
                tags_array = []

            for i, tag in enumerate(tags_array):
                tags_array[i] = tag.lstrip()

            current_lobby['roll_settings']['peer_reviewed'] = peer_reviewed
            current_lobby['roll_settings']['played_before'] = played_before
            current_lobby['roll_settings']['difficulty'] = difficulty
            current_lobby['roll_settings']['tags'] = tags_array
            current_lobby['roll_settings']['facets'] = {}
            current_lobby['roll_settings']['require_gameplay'] = True

        elif current_lobby["mode"] == "Ascension":
            ascension.set_roll_settings(self, lobby_name_user_is_hosting, uid)

        else:
            await ctx.respond("<@1207345676141465622> What")
            print("todo")

        self.roll_level_from_settings(lobby_name_user_is_hosting)

        level_chosen = current_lobby["level"]

        if level_chosen == None:
            if current_lobby["mode"] == "Free Play":
                await ctx.respond("No levels found with those arguments!") #deliberately not ephemeral
                return

            elif current_lobby["mode"] == "Ascension":
                await ascension.no_levels_found(self, ctx, self.bot.game_data["ascension"][uid], current_lobby, lobby_name_user_is_hosting)
                if level_chosen == None:
                    self.bot.save_data()
                    await ctx.respond("<@1207345676141465622> HELP HELP HELP HELP HELP HELP HELP HELP HELP")
                    return

            else:
                await ctx.respond("<@1207345676141465622> What")
                print("todo")

        if current_lobby["mode"] == "Free Play":
            lobby_curr_message = await (await self.bot.fetch_channel(lobby_channel_id)).fetch_message(current_lobby['message_id'])
            await lobby_curr_message.edit(f'The lobby \"{lobby_name_user_is_hosting}\" has rolled a level!', embed=None, view=None)

        await self.send_current_lobby_message(lobby_name_user_is_hosting, ctx, False)

        await ctx.respond(f'<@{uid}> You have rolled a level! No more players may join this lobby.\nYou can do `/lobby unroll` to trash this selection and allow more players to join.', ephemeral=True)

        self.bot.save_data()


    async def unroll_level(self, ctx, lobby_name, host_id):
        current_lobby = self.bot.game_data['lobbies'][lobby_name]

        lobby_channel_id = current_lobby['channel_id']
        lobby_curr_message = await (await self.bot.fetch_channel(lobby_channel_id)).fetch_message(current_lobby['message_id'])
        unrolled_artist = ""
        unrolled_song = ""
        unrolled_authors = ""
        if current_lobby['level'] != None:
            unrolled_artist = current_lobby['level']['artist']
            unrolled_song = current_lobby['level']['song']
            unrolled_authors = current_lobby['level']['authors']

        current_lobby['status'] = 'Open'
        current_lobby['roll_settings'] = {}
        current_lobby['level'] = {}

        await lobby_curr_message.edit(f"The level \"{unrolled_artist} - {unrolled_song}\" (by {unrolled_authors}) was unrolled!", embed=None, view=None)

        await self.send_current_lobby_message(lobby_name, ctx, False)

        self.bot.save_data()


    @lobby.command(description="Trash your lobby's level selection and re-open it")
    async def unroll(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not hosting
        lobby_name_user_is_hosting = self.bot.lobby_name_user_is_hosting(uid)
        if lobby_name_user_is_hosting == None:
            await ctx.respond(f'You are not hosting!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_hosting]

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if lobby is not in rolling state
        if current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing! Wait for everyone to finish.', ephemeral=True)
            return
        elif current_lobby['status'] != 'Rolling':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return

        await self.unroll_level(ctx, lobby_name_user_is_hosting, uid)

        await ctx.respond("Unrolled.", ephemeral=True)


    @lobby.command(description="Use this command if you've seen the rolled level before")
    async def already_seen(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not playing
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in == None:
            await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_playing_in]

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if level isn't rolled yet
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return
        elif (current_lobby['status'] != 'Rolling') and (current_lobby['status'] != 'Playing'):
            await ctx.respond(f'That command is not valid in this state!', ephemeral=True)
            return

        # if rolling
        if current_lobby['status'] == 'Rolling':
            rerolled_artist = ""
            rerolled_song = ""
            rerolled_authors = ""
            if current_lobby['level'] != None:
                rerolled_artist = current_lobby['level']['artist']
                rerolled_song = current_lobby['level']['song']
                rerolled_authors = current_lobby['level']['authors']

            # unready everyone
            for player in current_lobby['players']:
                current_lobby['players'][player]['ready_status'] = 'Not Ready'

            # chronograph used: sorry
            if current_lobby["mode"] == "Ascension":
                runner_id = current_lobby["host"]
                ascension_lobby = self.bot.game_data["ascension"][runner_id]
                if ascension_lobby["chronograph_used"]:
                    await ctx.respond(f"Chronograph used, sorry! Wait until after everyone readies to do this command, or leave.", ephemeral=True)
                    return

            # choose a new level, SHOULD be impossible for this to return None
            self.roll_level_from_settings(lobby_name_user_is_playing_in)

            lobby_curr_message = await (await self.bot.fetch_channel(lobby_channel_id)).fetch_message(current_lobby['message_id'])
            await lobby_curr_message.edit(f"The level \"{rerolled_artist} - {rerolled_song}\" (by {rerolled_authors}) was rerolled!", embed=None, view=None)

            await self.send_current_lobby_message(lobby_name_user_is_playing_in, ctx, False)

            await ctx.respond(f'Rerolled!', ephemeral=True)

            self.bot.save_data()

        elif current_lobby['status'] == 'Playing': #if playing
            # if user has already submitted
            if current_lobby['players'][uid]['ready_status'] == 'Submitted':
                await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
                return

            current_lobby['players'][uid]['ready_status'] = 'Submitted'
            current_lobby['players'][uid]['miss_count'] = -1

            lobby_host = current_lobby['host']
            await self.edit_current_lobby_message(lobby_name_user_is_playing_in, ctx)

            await ctx.respond(f'Submitted! Just wait for everyone else to submit...', ephemeral=True)

            await self.has_everyone_submitted(ctx, lobby_name_user_is_playing_in, lobby_host)


    async def begin_match(self, ctx, lobby_name):
        current_lobbies = self.bot.game_data["lobbies"]
        current_lobby = current_lobbies[lobby_name]

        current_lobby['status'] = 'Playing'

        message = ''

        for player_id in current_lobby['players']:
            message = message + f"<@{player_id}> "
            current_lobby['players'][player_id]['ready_status'] = 'Not Yet Submitted'

        #await self.disable_current_message_view(current_lobby)

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        if len(current_lobby['players']) > 1:
            await lobby_channel.send(message + '\n**Beginning match in 10 seconds!**')
            await asyncio.sleep(7)

            await lobby_channel.send('**3**')
            await asyncio.sleep(1)
            await lobby_channel.send('**2**')
            await asyncio.sleep(1)
            await lobby_channel.send('**1**')
            await asyncio.sleep(1)
            await lobby_channel.send('**GO!**')
            await asyncio.sleep(10)

        await self.send_current_lobby_message(lobby_name, ctx, False)

        self.bot.save_data()


    async def is_everyone_ready(self, ctx, lobby_name, host):
        current_lobbies = self.bot.game_data["lobbies"]
        current_lobby = current_lobbies[lobby_name]

        if current_lobby['status'] != 'Rolling':
            return

        if len(current_lobby['players']) == 0: #no players in lobby
            current_lobby['status'] = 'Open'
            await self.unroll_level(ctx, lobby_name, host)
            return

        for player in current_lobby['players']:
            if current_lobby['players'][player]['ready_status'] == 'Not Ready':
                return

        await self.begin_match(ctx, lobby_name)


    async def finish_match(self, ctx, lobby_name, host):
        current_lobby = self.bot.game_data["lobbies"][lobby_name]

        unsorted_misses = {}

        for player in current_lobby['players']:
            unsorted_misses[player] = current_lobby['players'][player]['miss_count']

        players_places = misc.rank_players(unsorted_misses, False)

        level_artist = current_lobby['level']['artist']
        level_song = current_lobby['level']['song']
        level_authors = current_lobby['level']['authors']
        placement_message = ''

        num_players = len(players_places) #for exp calculation

        users_stats = self.bot.users_stats #for convenience lol

        total_sp_earned = 0

        for player in players_places:
            player_rank = players_places[player]['rank']

            sp_earned = 0
            if current_lobby['mode'] == 'Ascension':
                runner_misses = current_lobby["players"][host]["miss_count"]
                support_misses = current_lobby["players"][player]["miss_count"]
                if (runner_misses != -1) and (support_misses != -1) and (host != player):
                    sp_earned = ascension.calculate_sp(runner_misses, support_misses)

            total_sp_earned = total_sp_earned + sp_earned

            placement_message_line = f"{players_places[player]['text']}: <@{player}> with {unsorted_misses[player]} misses (+{num_players*2 - player_rank + 4} exp)\n"
            if sp_earned > 0:
                placement_message_line = f"{players_places[player]['text']}: <@{player}> with {unsorted_misses[player]} misses (+{num_players*2 - player_rank + 4} exp) [+{ascension.calculate_sp(runner_misses, support_misses)} SP]\n"

            placement_message = placement_message + placement_message_line

            if player not in users_stats:
                users_stats[player] = {}
                self.bot.validate_users_stats()

            player_stats = users_stats[player]

            level_is_tough_plus = (current_lobby['level']['difficulty'] == 'Tough') or (current_lobby['level']['difficulty'] == 'Very Tough')

            self.bot.increment_user_stat(player, "exp", num_players*2 - player_rank + 4, True)
            self.bot.increment_user_stat(player, "total_sp_earned", sp_earned, True)

            player_stats['matches_played'] = player_stats['matches_played'] + 1
            player_stats['opponents_beaten'] = player_stats['opponents_beaten'] + num_players - player_rank
            if (current_lobby['roll_settings']['played_before'] == 'No'):
                for player_beaten in players_places:
                    if (player_rank <= players_places[player_beaten]['rank']) and (player_beaten != player): #if player did better than player_beaten
                        player_stats['opponents_beaten_list'].append(player_beaten)
                        player_stats['opponents_beaten_list'] = list(set(player_stats['opponents_beaten_list'])) #remove duplicates
                        player_stats['unique_opponents_beaten'] = len(player_stats['opponents_beaten_list'])

                        if level_is_tough_plus:
                            player_stats['tough_plus_opponents_beaten_list'].append(player_beaten)
                            player_stats['tough_plus_opponents_beaten_list'] = list(set(player_stats['tough_plus_opponents_beaten_list'])) #remove duplicates
            if unsorted_misses[player] == 0:
                if current_lobby['roll_settings']['played_before'] == 'No':
                    if current_lobby['level']['difficulty'] == 'Easy':
                        player_stats['easy_s_ranked'] = player_stats['easy_s_ranked'] + 1
                    elif current_lobby['level']['difficulty'] == 'Medium':
                        player_stats['medium_s_ranked'] = player_stats['medium_s_ranked'] + 1
                    elif current_lobby['level']['difficulty'] == 'Tough':
                        player_stats['tough_s_ranked'] = player_stats['tough_s_ranked'] + 1
                    elif current_lobby['level']['difficulty'] == 'Very Tough':
                        player_stats['vt_s_ranked'] = player_stats['vt_s_ranked'] + 1
                if current_lobby['mode'] == 'Ascension':
                    if current_lobby['roll_settings']['played_before'] == 'Yes': #means chronograph was used
                        player_stats["s_ranked_with_chronograph"] = player_stats["s_ranked_with_chronograph"] + 1
                    if (current_lobby['level']['difficulty'] == 'Tough') or (current_lobby['level']['difficulty'] == 'Very Tough'):
                        ascension_lobby = self.bot.game_data["ascension"][host]
                        if (ascension_lobby["set_modifier"] == "Hard Difficulty Button") or (ascension_lobby["set_modifier"] == "2-Player") or (ascension_lobby["set_modifier"] == "Blindfolded") or (ascension_lobby["set_modifier"] == "Nightcore"): #todo
                            player_stats['tough_plus_s_ranked_modifier'] = player_stats['tough_plus_s_ranked_modifier'] + 1
            if len(unsorted_misses) > player_stats['largest_match_played']:
                player_stats['largest_match_played'] = len(unsorted_misses)
            if (player_rank == 1) and (len(unsorted_misses) > player_stats['largest_match_won']):
                player_stats['largest_match_won'] = len(unsorted_misses)
            if (player_rank == 1) and (len(unsorted_misses) > player_stats['tough_plus_largest_match_won']) and level_is_tough_plus:
                player_stats['tough_plus_largest_match_won'] = len(unsorted_misses)
            if current_lobby['level']['peer review status'] == 'Non-Refereed':
                player_stats['nr_played'] = player_stats['nr_played'] + 1
            if current_lobby['roll_settings']['difficulty'] == 'Polarity':
                player_stats['polarity_played'] = player_stats['polarity_played'] + 1

            # beat srt3 players
            srt3_semifinalists = ['298722923626364928', '1207345676141465622', '943278556543352873', '224514766486372352']
            no_srt3_semifinalists_beaten = 0
            tough_plus_no_srt3_semifinalists_beaten = 0
            for semifinalist in srt3_semifinalists:
                if semifinalist in player_stats['opponents_beaten_list']:
                    no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
                if semifinalist in player_stats['tough_plus_opponents_beaten_list']:
                    tough_plus_no_srt3_semifinalists_beaten = tough_plus_no_srt3_semifinalists_beaten + 1

            player_stats['srt3_semifinalists_beaten'] = no_srt3_semifinalists_beaten
            player_stats['tough_plus_srt3_semifinalists_beaten'] = tough_plus_no_srt3_semifinalists_beaten

            # divine intervention secret
            if current_lobby['level']['hash'] == 'c0d7a6c64264d812e06707159c297eb2':
                if current_lobby['players'][player]['miss_count'] <= 75:
                    player_stats['divine_intervention'] = 1

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        placement_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"Results for {level_artist} - {level_song} (by {level_authors}):", description = placement_message)
        await lobby_channel.send(embed=placement_embed)

        if current_lobby['mode'] == 'Free Play':
            current_lobby['status'] = 'Open'
            current_lobby['roll_settings'] = {}
            current_lobby['level'] = {}

        elif current_lobby['mode'] == 'Ascension':
            ascension_lobby = self.bot.game_data["ascension"][host]
            ascension_difficulty = ascension_lobby["ascension_difficulty"]
            level_difficulty = current_lobby['level']['difficulty']

            runner_misses = current_lobby["players"][host]["miss_count"]

            ascension_lobby['current_sp'] = ascension_lobby['current_sp'] + total_sp_earned

            damage_factor = 1
            if ascension_lobby["set_modifier"] == "Double Damage":
                damage_factor = damage_factor * 2

            damage_factor = damage_factor * ascension_lobby["no_levels_found_damage_multiplier"]
            ascension_lobby["no_levels_found_damage_multiplier"] = 1

            if ascension_difficulty >= 6:
                if (level_difficulty == "Easy") or (level_difficulty == "Medium"):
                    damage_factor = damage_factor * 2
                elif (level_difficulty == "Tough") or (level_difficulty == "Very Tough"): #unnecessary check idc
                    damage_factor = damage_factor * 1.5
            elif ascension_difficulty >= 2:
                if level_difficulty == "Easy":
                    damage_factor = damage_factor * 2
                elif level_difficulty == "Medium":
                    damage_factor = damage_factor * 1.5

            ascension_lobby["incoming_damage"] = math.floor(runner_misses * damage_factor)

            if runner_misses == -1:
                current_lobby['status'] = 'Open'
                ascension_lobby['status'] = 'Open'
            else:
                if runner_misses > 0:
                    ascension_lobby["s_ranked_so_far"] = False
                current_lobby['status'] = 'Item'
                ascension_lobby['status'] = 'Item'

            ascension_lobby["chronograph_used"] = False #no ones gonna chronograph an already seen level

        for player in current_lobby['players']:
            current_lobby['players'][player]['ready_status'] = 'Not Ready'
            current_lobby['players'][player]['miss_count'] = None

        await self.send_current_lobby_message(lobby_name, ctx, False)

        self.bot.save_data()


    async def has_everyone_submitted(self, ctx, lobby_name, host_id):
        current_lobbies = self.bot.game_data["lobbies"]
        current_lobby = current_lobbies[lobby_name]

        if current_lobby['status'] != 'Playing':
            return

        if len(current_lobby['players']) == 0: #no players in lobby
            current_lobby['status'] = 'Open'
            await self.unroll_level(ctx, lobby_name, host_id)
            return

        for player in current_lobby['players']:
            if current_lobby['players'][player]['ready_status'] == 'Not Yet Submitted':
                return

        await self.finish_match(ctx, lobby_name, host_id)


    @lobby.command(description="MAKE SURE YOU\'RE AT THE BUTTON SCREEN!")
    async def ready(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not playing
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in == None:
            await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_playing_in]

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if level isn't rolled yet
        if current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
            return
        elif current_lobby['status'] != 'Rolling':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return

        # if user is already ready
        if current_lobby['players'][uid]['ready_status'] == 'Ready':
            await ctx.respond(f'You are already ready!', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Ready'

        await self.edit_current_lobby_message(lobby_name_user_is_playing_in, ctx)

        await ctx.respond(f'Readied!', ephemeral=True)

        lobby_host = current_lobby['host']
        await self.is_everyone_ready(ctx, lobby_name_user_is_playing_in, lobby_host)


    @lobby.command(description="Use this command if you\'re no longer ready")
    async def unready(self, ctx
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not playing
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in == None:
            await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_playing_in]

        # deliberately do not have to be in the correct channel

        # if level isn't rolled yet
        if current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
            return
        elif current_lobby['status'] != 'Rolling':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return

        # if user is already not ready
        if current_lobby['players'][uid]['ready_status'] == 'Not Ready':
            await ctx.respond(f'You are already not ready!', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Not Ready'

        await self.edit_current_lobby_message(lobby_name_user_is_playing_in, ctx)

        await ctx.respond(f'Unreadied.', ephemeral=True)


    @lobby.command(description="Submit your miss count")
    async def submit_misses(self, ctx,
        miss_count: discord.Option(discord.SlashCommandOptionType.integer, description = 'How many misses you got')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        # if user is not playing
        lobby_name_user_is_playing_in = self.bot.lobby_name_user_is_playing_in(uid)
        if lobby_name_user_is_playing_in == None:
            await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
            return

        current_lobby = current_lobbies[lobby_name_user_is_playing_in]

        lobby_channel_id = current_lobby['channel_id']

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if lobby isn't playing
        if current_lobby['status'] == 'Rolling':
            await ctx.respond(f'Your lobby has not yet started playing! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return
        elif current_lobby['status'] != 'Playing':
            await ctx.respond(f'Your lobby has not yet rolled a level! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return

        # if user has already submitted
        if current_lobby['players'][uid]['ready_status'] == 'Submitted':
            await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Submitted'
        current_lobby['players'][uid]['miss_count'] = miss_count

        await self.edit_current_lobby_message(lobby_name_user_is_playing_in, ctx)

        await ctx.respond(f'Submitted! Just wait for everyone else to submit...', ephemeral=True)

        lobby_host = current_lobby['host']
        await self.has_everyone_submitted(ctx, lobby_name_user_is_playing_in, lobby_host)


    @lobby.command(description="Resend a lobby's status (try this command if buttons break)")
    async def resend(self, ctx,
        name: discord.Option(discord.SlashCommandOptionType.string, description = 'The lobby\'s name')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        if name not in current_lobbies:
            await ctx.respond(f'That lobby doesn\'t exist!', ephemeral=True)
            return

        await ctx.respond(f'Resent in the lobby\'s channel!', ephemeral=True)

        await self.send_current_lobby_message(name, ctx, False)


def setup(bot: MatchmakingBot):
    cog = LobbyCommands(bot)
    bot.add_cog(cog)