import discord
from discord.ext import commands
import time
from rd_matchmaking_bot.bot.matchmaking_bot import MatchmakingBot
import rd_matchmaking_bot.utils.levels as levels
import rd_matchmaking_bot.utils.misc as misc


class LobbyCommands(commands.Cog):
    lobby = discord.SlashCommandGroup("lobby", "Lobby commands")


    def __init__(self, bot: MatchmakingBot):
        self.bot = bot


    def get_lobby_open_embed(self, lobby_name, host_id, player_id_dict):
        player_list = []
        for id in player_id_dict:
            player_list.append('<@' + id + '>')

        players = ', '.join(player_list)

        return discord.Embed(colour = discord.Colour.blue(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n# This lobby is open!\nDo \"**/lobby join {lobby_name}**\" to join.\n\n**Players:** {players}")


    def get_lobby_rolling_embed(self, lobby_name, host_id, player_id_dict, level_chosen):
        ready_list = ''

        for id in player_id_dict:
            ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

        level_embed = discord.Embed(colour = discord.Colour.green(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n\nMake sure you do \"**/lobby already_seen**\" if you recognize this level!\nOtherwise, do \"**/lobby ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}\n", image = level_chosen['image_url'])
        levels.add_level_to_embed(level_embed, level_chosen)
        return level_embed


    def get_lobby_playing_embed(self, lobby_name, host_id, player_id_dict):
        submitted_list = ''

        for id in player_id_dict:
            submitted_list = submitted_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

        return discord.Embed(colour = discord.Colour.red(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n\nMake sure you do \"**/lobby already_seen**\" if you recognize this level!\nOtherwise, when you\'re done, do \"**/lobby submit_misses**\" to submit your miss count.\nOnce everyone submits, final results will be posted. (The host should kick AFK players.)\n\n{submitted_list}")


    def get_lobby_embed(self, status, lobby_name, host_id, player_id_dict, level_chosen):
        if status == 'Open':
            return self.get_lobby_open_embed(lobby_name, host_id, player_id_dict)
        elif status == 'Rolling':
            return self.get_lobby_rolling_embed(lobby_name, host_id, player_id_dict, level_chosen)
        elif status == 'Playing':
            return self.get_lobby_playing_embed(lobby_name, host_id, player_id_dict)
        else:
            print('Huge Mistake')

    
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
        name: discord.Option(discord.SlashCommandOptionType.string, description = 'Lobby name')
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

        current_lobbies[name] = {}
        current_lobby = current_lobbies[name]

        current_lobby['status'] = 'Open'
        current_lobby['host'] = uid
        current_lobby['players'] = {}
        current_lobby['roll_settings'] = {}
        current_lobby['level'] = {}

        message = await ctx.channel.send(embed=self.get_lobby_open_embed(name, uid, []))

        current_lobby['channel_id'] = message.channel.id
        current_lobby['message_id'] = message.id

        await ctx.respond(f"<@{uid}> You have started hosting the lobby \"{name}\"!\n\
    Make sure to do \"**/lobby join {name}**\" if you want to play.\n\
    You can do \"**/lobby kick [player]**\" to kick an AFK player.\n\
    You can do \"**/lobby delete**\" to delete this lobby. (Don't do this until after level results are sent, it's rude!)\n\n\
    Once everyone has joined, do \"**/lobby roll**\" to roll a level.", ephemeral=True)

        self.bot.save_data()


    @lobby.command(description="Join a specified lobby")
    async def join(self, ctx,
        name: discord.Option(discord.SlashCommandOptionType.string, description = 'Name of lobby to join')
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        if name == 'the light': #secret
            await ctx.respond(f'\"Whoa whoa hang on, you think I\'m gonna just let you do THAT?\"\n\
\"...okay, fine, I\'m supposed to let those with 15★ or more in. Don\'t think your attempt will be easy, though!\"\n\
\"...What, you want an achievement? Just for finding this place? But that one\'s MINE! And you barely did any work!\"\n\
\"Fine, I\'ll give you something... if you can survive my level! Given its... PR status, this should be fun to watch...\"', ephemeral=True)
            user_achievements = self.bot.get_user_achievements(ctx, uid)
            if user_achievements['total'] >= 15:
                await self.endless_welcome(ctx, uid)
            return

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
            await ctx.respond(f'That lobby is already rolling for a level! (Consider asking the host to **/lobby unroll** so that you can join.)', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'That lobby is already playing!', ephemeral=True)
            return

        # if user doesn't have an rdsettings
        if uid not in self.bot.users_rdsaves:
            await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use **/upload_rdsave** to do this.)', ephemeral=True)
            return

        current_lobby['players'][uid] = {}
        current_lobby['players'][uid]['ready_status'] = 'Not Ready'
        current_lobby['players'][uid]['miss_count'] = None

        await ctx.respond(f'Joined \"{name}\".\nDo \"**/lobby leave**\" to leave.\nWait for the host to roll a level...', ephemeral=True)
        await lobby_channel.send(f'<@{uid}> Joined \"{name}\"!')

        # edit lobby message
        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_status = current_lobby['status']
        lobby_host = current_lobby['host']
        lobby_players = current_lobby['players']
        level_chosen = current_lobby['level']

        await lobby_curr_message.edit(embed=self.get_lobby_embed(lobby_status, name, lobby_host, lobby_players, level_chosen))


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

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        # remove user from current lobby they're in
        del current_lobby['players'][uid]

        await ctx.respond(f'Left \"{lobby_name_user_is_playing_in}\".', ephemeral=True)
        await lobby_channel.send(f'<@{uid}> left \"{lobby_name_user_is_playing_in}\".')

        # edit lobby message
        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_status = current_lobby['status']
        lobby_host = current_lobby['host']
        lobby_players = current_lobby['players']
        level_chosen = current_lobby['level']

        await lobby_curr_message.edit(embed=self.get_lobby_embed(lobby_status, lobby_name_user_is_playing_in, lobby_host, lobby_players, level_chosen))

        lobby_host = current_lobbies[lobby_name_user_is_playing_in]['host']
        await self.is_everyone_ready(ctx, lobby_name_user_is_playing_in, lobby_host)
        await self.has_everyone_submitted(ctx, lobby_name_user_is_playing_in, lobby_host)


    @lobby.command(description="Kick a player from your lobby")
    async def kick(self, ctx,
        player: discord.Option(discord.SlashCommandOptionType.user)
    ):
        current_lobbies = self.bot.game_data["lobbies"]

        uid = str(ctx.user.id)

        player_to_kick = str(player.id)

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

        # if player is not in the lobby
        if player_to_kick not in current_lobby['players']:
            await ctx.respond(f'User not found in lobby!', ephemeral=True)
            return

        # kick player
        del current_lobby['players'][player_to_kick]

        await ctx.respond(f'Kicked <@{player_to_kick}>.')

        # edit lobby message
        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_status = current_lobby['status']
        lobby_players = current_lobby['players']
        level_chosen = current_lobby['level']

        await lobby_curr_message.edit(embed=self.get_lobby_embed(lobby_status, lobby_name_user_is_hosting, uid, lobby_players, level_chosen))

        await self.is_everyone_ready(ctx, lobby_name_user_is_hosting, uid)
        await self.has_everyone_submitted(ctx, lobby_name_user_is_hosting, uid)


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

        # edit lobby message; possible await race condition here but very unlikely? also not a big deal lol
        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        if lobby_curr_message != None:
            await lobby_curr_message.edit(f"This lobby \"{lobby_name_user_is_hosting}\" has been deleted!", embed=None)

        del current_lobbies[lobby_name_user_is_hosting]

        await ctx.respond(f'Deleted \"{lobby_name_user_is_hosting}\".')

        self.bot.save_data()


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
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if lobby is not in open state
        if current_lobby['status'] == 'Rolling':
            await ctx.respond(f'Your lobby has already rolled a level! Use **/lobby unroll** to re-open your lobby.', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing, or is waiting on people to submit their miss counts! Kick AFK players if you must.', ephemeral=True)
            return

        # if no one is playing
        if len(current_lobby['players']) == 0:
            await ctx.respond(f'No one is playing!', ephemeral=True)
            return

        tags_array = tags.split(',')
        if tags == '':
            tags_array = []

        for i, tag in enumerate(tags_array):
            tags_array[i] = tag.lstrip()

        roll_player_id_list = (current_lobby['players']).keys()

        level_chosen = levels.roll_random_level(peer_reviewed, played_before, difficulty, roll_player_id_list, self.bot.users_rdsaves, tags_array, None)

        if level_chosen == None:
            await ctx.respond("No levels found with those arguments!", ephemeral=True)
            return

        current_lobby['status'] = 'Rolling'
        current_lobby['roll_settings']['peer_reviewed'] = peer_reviewed
        current_lobby['roll_settings']['played_before'] = played_before
        current_lobby['roll_settings']['difficulty'] = difficulty
        current_lobby['roll_settings']['tags'] = tags_array

        current_lobby['level'] = level_chosen

        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])

        await lobby_curr_message.edit(f'The lobby \"{lobby_name_user_is_hosting}\" has rolled a level!', embed=None)

        lobby_new_message = await lobby_channel.send(embed=self.get_lobby_rolling_embed(lobby_name_user_is_hosting, uid, current_lobby['players'], level_chosen))

        await ctx.respond(f'<@{uid}> You have rolled a level! No more players may join this lobby.\nYou can do \"**/lobby unroll**\" to trash this selection and allow more players to join.', ephemeral=True)
        current_lobby['message_id'] = lobby_new_message.id

        self.bot.save_data()


    async def unroll_level(self, ctx, lobby_name, host_id):
        current_lobby = self.bot.game_data['lobbies'][lobby_name]

        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        unrolled_artist = current_lobby['level']['artist']
        unrolled_song = current_lobby['level']['song']
        unrolled_authors = current_lobby['level']['authors']

        current_lobby['status'] = 'Open'
        current_lobby['roll_settings'] = {}
        current_lobby['level'] = {}

        await lobby_curr_message.edit(f"The level \"{unrolled_artist} - {unrolled_song}\" (by {unrolled_authors}) was unrolled!", embed=None)

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        lobby_new_message = await lobby_channel.send(embed=self.get_lobby_open_embed(lobby_name, host_id, current_lobby['players']))

        current_lobby['message_id'] = lobby_new_message.id

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
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing! Wait for everyone to finish.', ephemeral=True)
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
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        # if user isn't in lobby's channel
        user_channel_id = ctx.channel.id
        if user_channel_id != lobby_channel_id:
            await ctx.respond(f'You are not in the lobby\'s channel!', ephemeral=True)
            return

        # if level isn't rolled yet
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return

        # if rolling
        if current_lobby['status'] == 'Rolling':
            rerolled_artist = current_lobby['level']['artist']
            rerolled_song = current_lobby['level']['song']
            rerolled_authors = current_lobby['level']['authors']

            # unready everyone
            for player in current_lobby['players']:
                current_lobby['players'][player]['ready_status'] = 'Not Ready'

            # choose a new level
            new_peer_reviewed = current_lobby['roll_settings']['peer_reviewed']
            new_played_before = current_lobby['roll_settings']['played_before']
            new_difficulty = current_lobby['roll_settings']['difficulty']
            new_level_tags = current_lobby['roll_settings']['tags']
            roll_player_id_list = (current_lobby['players']).keys()

            # SHOULD be impossible for this to return None
            new_level_chosen = levels.roll_random_level(new_peer_reviewed, new_played_before, new_difficulty, roll_player_id_list, self.bot.users_rdsaves, new_level_tags, None)

            current_lobby['level'] = new_level_chosen

            lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
            await lobby_curr_message.edit(f"The level \"{rerolled_artist} - {rerolled_song}\" (by {rerolled_authors}) was rerolled!", embed=None)

            lobby_host = current_lobby['host']
            lobby_new_message = await lobby_channel.send(embed=self.get_lobby_rolling_embed(lobby_name_user_is_playing_in, lobby_host, current_lobby['players'], new_level_chosen))

            await ctx.respond(f'Rerolled!', ephemeral=True)

            current_lobby['message_id'] = lobby_new_message.id

            self.bot.save_data()

        elif current_lobby['status'] == 'Playing': #if playing
            # if user has already submitted
            if current_lobby['players'][uid]['ready_status'] == 'Submitted':
                await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
                return

            current_lobby['players'][uid]['ready_status'] = 'Submitted'
            current_lobby['players'][uid]['miss_count'] = -1

            lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
            lobby_host = current_lobby['host']
            await lobby_curr_message.edit(embed=self.get_lobby_playing_embed(lobby_name_user_is_playing_in, lobby_host, current_lobby['players']))

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

        lobby_channel_id = current_lobby['channel_id']
        lobby_channel = await self.bot.fetch_channel(lobby_channel_id)

        await lobby_channel.send(message + '\n**Beginning match in 10 seconds!**')
        time.sleep(7)

        await lobby_channel.send('**3**')
        time.sleep(1)
        await lobby_channel.send('**2**')
        time.sleep(1)
        await lobby_channel.send('**1**')
        time.sleep(1)
        await lobby_channel.send('**GO!**')
        time.sleep(10)

        lobby_host = current_lobby['host']
        lobby_new_message = await lobby_channel.send(embed=self.get_lobby_playing_embed(lobby_name, lobby_host, current_lobby['players']))

        current_lobby['message_id'] = lobby_new_message.id

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
        current_lobbies = self.bot.game_data["lobbies"]
        current_lobby = current_lobbies[lobby_name]

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

        for player in players_places:
            player_rank = players_places[player]['rank']

            placement_message = placement_message + f"{players_places[player]['text']}: <@{player}> with {unsorted_misses[player]} misses (+{num_players*2 - player_rank + 4} exp)\n" #(2*players - place) exp gained

            if player not in users_stats:
                users_stats[player] = {}
                self.bot.validate_users_stats()

            player_stats = users_stats[player]

            level_is_tough_plus = (current_lobby['level']['difficulty'] == 'Tough') or (current_lobby['level']['difficulty'] == 'Very Tough')

            player_stats['exp'] = player_stats['exp'] + num_players*2 - player_rank + 4
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
            if (unsorted_misses[player] == 0) and (current_lobby['roll_settings']['played_before'] == 'No'):
                if current_lobby['level']['difficulty'] == 'Easy':
                    player_stats['easy_s_ranked'] = player_stats['easy_s_ranked'] + 1
                elif current_lobby['level']['difficulty'] == 'Medium':
                    player_stats['medium_s_ranked'] = player_stats['medium_s_ranked'] + 1
                elif current_lobby['level']['difficulty'] == 'Tough':
                    player_stats['tough_s_ranked'] = player_stats['tough_s_ranked'] + 1
                else:
                    player_stats['vt_s_ranked'] = player_stats['vt_s_ranked'] + 1
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

        for player in current_lobby['players']:
            current_lobby['players'][player]['ready_status'] = 'Not Ready'
            current_lobby['players'][player]['miss_count'] = None

        current_lobby['status'] = 'Open'
        current_lobby['roll_settings'] = {}
        current_lobby['level'] = {}

        player_list = current_lobby['players']
        lobby_new_message = await lobby_channel.send(embed=self.get_lobby_open_embed(lobby_name, host, player_list))

        current_lobby['message_id'] = lobby_new_message.id

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
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return
        elif current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
            return

        # if user is already ready
        if current_lobby['players'][uid]['ready_status'] == 'Ready':
            await ctx.respond(f'You are already ready!', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Ready'

        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_level_chosen = current_lobby['level']

        lobby_host = current_lobby['host']
        await lobby_curr_message.edit(embed=self.get_lobby_rolling_embed(lobby_name_user_is_playing_in, lobby_host, current_lobby['players'], lobby_level_chosen))

        await ctx.respond(f'Readied!', ephemeral=True)

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
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
            return
        if current_lobby['status'] == 'Playing':
            await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
            return

        # if user is already not ready
        if current_lobby['players'][uid]['ready_status'] == 'Not Ready':
            await ctx.respond(f'You are already not ready!', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Not Ready'

        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_level_chosen = current_lobby['level']

        lobby_host = current_lobby['host']
        await lobby_curr_message.edit(embed=self.get_lobby_rolling_embed(lobby_name_user_is_playing_in, lobby_host, current_lobby['players'], lobby_level_chosen))

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
        if current_lobby['status'] == 'Open':
            await ctx.respond(f'Your lobby has not yet rolled a level! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return
        elif current_lobby['status'] == 'Rolling':
            await ctx.respond(f'Your lobby has not yet started playing! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return

        # if user has already submitted
        if current_lobby['players'][uid]['ready_status'] == 'Submitted':
            await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return

        current_lobby['players'][uid]['ready_status'] = 'Submitted'
        current_lobby['players'][uid]['miss_count'] = miss_count

        lobby_curr_message = await ctx.fetch_message(current_lobby['message_id'])
        lobby_host = current_lobby['host']
        await lobby_curr_message.edit(embed=self.get_lobby_playing_embed(lobby_name_user_is_playing_in, lobby_host, current_lobby['players']))

        await ctx.respond(f'Submitted! Just wait for everyone else to submit...', ephemeral=True)

        await self.has_everyone_submitted(ctx, lobby_name_user_is_playing_in, lobby_host)


    async def endless_welcome(self, ctx, player_id):
        welcome_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Lobby: \"`   ` `     `\"", description = f"Player: <@{player_id}>\n\n\
    Welcome to Endless Setlists!\n\
Here, your goal is to play levels to reach `   ` `     ` at the end of Set 7.\n\
(Note: As this is a beta test, runs currently end when completing Set 5.)\n\
Each set will consist of 4 levels. You start with ★HP, and will lose 1 for each miss.\n\
\nYou can join other lobbies during your attempt.\n\
(Starting runs will cost a currency once testing is complete, but is currently free.)\n\n\
To begin an attempt, type \"**/admin_command endless begin**\".\n\
(Tip: \"endless\" can be shortened to \"e\" in commands.)")
        await ctx.channel.send(embed = welcome_embed)

        endless_lobbies = self.bot.game_data["endless"]

        if player_id not in endless_lobbies:
            endless_lobbies[player_id] = {}
            self.bot.validate_game_data()
            self.bot.save_data()


def setup(bot: MatchmakingBot):
    cog = LobbyCommands(bot)
    bot.add_cog(cog)