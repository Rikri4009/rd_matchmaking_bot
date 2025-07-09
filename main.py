import discord
import json
import csv
import hashlib
import random
import os
import re
from threading import Thread, Lock
import time

users_rdsettings_mutex = Lock() #I hope this works???
current_games_mutex = Lock()

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f'{bot.user} is ready and online!')

def read_json(filename):
    with open(os.path.realpath(__file__) + '\\..\\' + filename, 'r') as in_file:
        return json.load(in_file)

def write_json(dict, filename):
    json_object = json.dumps(dict, indent=4)
    with open(os.path.realpath(__file__) + '\\..\\' + filename, 'w') as out_file:
        out_file.write(json_object)

@bot.command()
async def upload_rdsettings(
    ctx,
    settings_rdsave: discord.Option(discord.SlashCommandOptionType.attachment)
):
    users_rdsettings = read_json('users_rdsettings.json')

    file = await settings_rdsave.read()
    attached_rdsettings = json.loads((file.decode('utf-8-sig')).encode('utf-8'))

    user = str(ctx.user.id)
    users_rdsettings[user] = []

    # Extract hash of played levels
    for key, val in attached_rdsettings.items():
        if (key[0:12] == 'CustomLevel_') and (key[(len(key)-7):(len(key))] == '_normal') and (val != 'NotFinished'):
            users_rdsettings[user].append(key[12:(len(key)-7)])

    write_json(users_rdsettings, 'users_rdsettings.json')

    await ctx.respond(f'RDSettings updated!')

def create_user_id_list(players, caller_id):
    if players == None:
        players = '<@'+caller_id+'>'

    user_id_list = re.findall(r"\<\@(.*?)\>", players)
    return list(set(user_id_list)) #remove duplicates

def roll_random_level(ctx, peer_reviewed, played_before, difficulty, user_id_list):

    cafe_hashed = {}

    users_rdsettings = read_json('users_rdsettings.json')

    # iterate through cafe dataset
    with open(os.path.realpath(__file__) + '\\..\\cafe_query.csv', 'r', encoding='utf-8') as cafe_query:
        for line in csv.DictReader(cafe_query):
            level_prd = (line['approval'] == '10')
            level_nrd = (line['approval'] == '-1')

            level_pr_status = 'Peer Review in Progress'
            if level_prd:
                level_pr_status = 'Peer Reviewed'
            elif level_nrd:
                level_pr_status = 'Non-Refereed'

            # check if level matches pr option
            pr_check = (peer_reviewed == 'Any') or ((peer_reviewed == 'Yes') and level_prd) or ((peer_reviewed == 'No') and (level_nrd))

            level_diff = 'Easy'
            if line['difficulty'] == '1':
                level_diff = 'Medium'
            elif line['difficulty'] == '2':
                level_diff = 'Tough'
            elif line['difficulty'] == '3':
                level_diff = 'Very Tough'

            # does difficulty match
            diff_check = (difficulty == 'Any') or (difficulty == level_diff) or ((difficulty == 'Polarity') and ((level_diff == 'Easy') or (level_diff == 'Very Tough')))

            if pr_check and diff_check:
                authors_list = json.loads(line['authors'])
                authors = ', '.join(authors_list)

                artist = line['artist']
                song = line['song']

                hash = hashlib.md5((authors + artist + song).encode())
                hash_hex = hash.hexdigest()

                zip = line['url2']

                cafe_hashed[hash_hex] = {
                    'authors': authors,
                    'artist': artist,
                    'song': song,
                    'difficulty': level_diff,
                    'peer review status': level_pr_status,
                    'zip': zip}

    if played_before == 'No': #remove played levels
        for uid in user_id_list:
            if uid in users_rdsettings:
                for hash in users_rdsettings[uid]:
                    if hash in cafe_hashed:
                        del cafe_hashed[hash]

    elif played_before == 'Yes': #keep only played levels
        set_list = []

        # create list of users' played levels as sets
        for uid in user_id_list:
            if uid in users_rdsettings:
                set_list.append(set(users_rdsettings[uid]))

        # find levels everyone's played
        hashes_all_played = set.intersection(*set_list)

        new_cafe_hashed = {}

        # find matching levels on cafe
        for hash in hashes_all_played:
            if hash in cafe_hashed:
                new_cafe_hashed[hash] = cafe_hashed[hash]

        cafe_hashed = new_cafe_hashed

    return random.choice(list(cafe_hashed.values()))

def get_level_chosen_message(level_chosen):
    return f"Your level: {level_chosen['artist']} - {level_chosen['song']} (by {level_chosen['authors']})\n\
Difficulty: {level_chosen['difficulty']}\n\
{level_chosen['peer review status']}\n\
{level_chosen['zip']}"

@bot.command()
async def roll_level(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Polarity'], default = 'Any', description = 'Default: Any'),
    players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
):
    level_chosen = roll_random_level(ctx, peer_reviewed, played_before, difficulty, create_user_id_list(players, str(ctx.user.id)))

    await ctx.respond(get_level_chosen_message(level_chosen))

lobby = bot.create_group('lobby', 'Lobby/matchmaking commands')

def get_lobby_open_message(lobby_name, host_id, player_id_dict):
    player_list = []
    for id in player_id_dict:
        player_list.append('<@' + id + '>')

    players = ', '.join(player_list)

    return '# Lobby: \"' + lobby_name + '\" is open!\n\
Do \"**/lobby join ' + lobby_name + '**\" to join. (The host should do this if they want to play!)\n\
Do \"**/lobby leave**\" to leave.\n\
The host can do \"**/lobby delete**\" to delete this lobby.\n\
The host can do \"**/lobby kick [player]**\" to kick a player.\n\
Once everyone has joined, the host should do \"**/lobby roll**\" to roll a level.\n\n\
**Host:** <@' + host_id + '>\n\
**Players:** ' + players

def get_lobby_rolling_message(player_id_dict, level_chosen):
    ready_list = ''

    for id in player_id_dict:
        ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    return f'Make sure you do \"**/lobby already_seen**\" if you recognize this level!\n\
Otherwise, do \"**/lobby ready**\" when you\'re at the button screen.\n\
Once everyone readies, the countdown will begin!\n\
The host can do \"**/lobby unroll**\" to trash this selection and allow more players to join the lobby.\n\n{ready_list}\n{get_level_chosen_message(level_chosen)}'

def get_lobby_playing_message(player_id_dict):
    submitted_list = ''

    for id in player_id_dict:
        submitted_list = submitted_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    return f'Make sure you do \"**/lobby already_seen**\" if you recognize this level!\n\
Otherwise, when you\'re done, do \"**/lobby submit_misses**\" to submit your miss count (and optionally add a comment).\n\
Once everyone submits, final results will be posted. (The host should kick AFK players.)\n\n{submitted_list}'

def get_lobby_message(status, lobby_name, host_id, player_id_dict, level_chosen):
    if status == 'Open':
        return get_lobby_open_message(lobby_name, host_id, player_id_dict)
    elif status == 'Rolling':
        return get_lobby_rolling_message(player_id_dict, level_chosen)
    elif status == 'Playing':
        print('todo')
    else:
        print('Huge Mistake')

@lobby.command()
async def list_all(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    # if there are no lobbies
    if len(current_lobbies['lobbies']) == 0:
        await ctx.respond(f'There are currently no lobbies!')
        return

    lobby_list_message = ''
    for name in current_lobbies['lobbies']:
        lobby_list_message = lobby_list_message + f"{name}: {len(current_lobbies['lobbies'][name]['players'])} Players\n"

    await ctx.respond(lobby_list_message)

@lobby.command()
async def create(
    ctx,
    name: discord.Option(discord.SlashCommandOptionType.string, description = 'Lobby name')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is already in a lobby
    if (user in current_lobbies['users_playing']) or (user in current_lobbies['users_hosting']):
        lobby_user_is_in = (current_lobbies['users_playing'] | current_lobbies['users_hosting'])[user]
        await ctx.respond(f'You are already in the lobby \"{lobby_user_is_in}\"!')
        return

    # if a lobby with that name exists
    if name in current_lobbies['lobbies']:
        await ctx.respond(f'That lobby name is already in use!')
        return

    current_lobbies['users_hosting'][user] = name

    current_lobbies['lobbies'][name] = {}
    current_lobbies['lobbies'][name]['status'] = 'Open'
    current_lobbies['lobbies'][name]['host'] = user
    current_lobbies['lobbies'][name]['players'] = {}
    current_lobbies['lobbies'][name]['roll_settings'] = {}
    current_lobbies['lobbies'][name]['level'] = {}

    message = await ctx.channel.send(get_lobby_open_message(name, user, []))

    current_lobbies['lobbies'][name]['message_id'] = message.id

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def join(
    ctx,
    name: discord.Option(discord.SlashCommandOptionType.string, description = 'Name of lobby to join')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is playing in a lobby
    if user in current_lobbies['users_playing']:
        lobby_user_is_in = current_lobbies['users_playing'][user]
        await ctx.respond(f'You are already playing in the lobby \"{lobby_user_is_in}\"!')
        return

    # if user is hosting a lobby different to this one
    if (user in current_lobbies['users_hosting']) and (current_lobbies['users_hosting'][user] != name):
        lobby_user_is_in = current_lobbies['users_hosting'][user]
        await ctx.respond(f'You are already hosting the lobby \"{lobby_user_is_in}\"!')
        return

    # if lobby doesn't exist
    if name not in current_lobbies['lobbies']:
        await ctx.respond(f'That lobby doesn\'t exist!')
        return

    # if lobby is not open
    if current_lobbies['lobbies'][name]['status'] == 'Rolling':
        await ctx.respond(f'That lobby is already rolling for a level! (Consider asking the host to **/lobby unroll** so that you can join.)')
        return
    if current_lobbies['lobbies'][name]['status'] == 'Playing':
        await ctx.respond(f'That lobby is already playing!')
        return

    # if user doesn't have an rdsettings
    rdsettings = read_json('users_rdsettings.json')
    if user not in rdsettings:
        await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use **/upload_rdsettings** to do this.)')
        return

    current_lobbies['users_playing'][user] = name

    current_lobbies['lobbies'][name]['players'][user] = {}
    current_lobbies['lobbies'][name]['players'][user]['ready_status'] = 'Not Ready'
    current_lobbies['lobbies'][name]['players'][user]['miss_count'] = -2

    await ctx.respond(f'Joined \"{name}\".')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][name]['message_id'])
    lobby_status = current_lobbies['lobbies'][name]['status']
    lobby_host = current_lobbies['lobbies'][name]['host']
    lobby_players = current_lobbies['lobbies'][name]['players']
    level_chosen = current_lobbies['lobbies'][name]['level']

    await lobby_curr_message.edit(get_lobby_message(lobby_status, name, lobby_host, lobby_players, level_chosen))

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def leave(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!')
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # remove user from current lobby they're in
    del current_lobbies['lobbies'][lobby_user_is_in]['players'][user]

    del current_lobbies['users_playing'][user]

    await ctx.respond(f'Left \"{lobby_user_is_in}\".')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_status = current_lobbies['lobbies'][lobby_user_is_in]['status']
    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    lobby_players = current_lobbies['lobbies'][lobby_user_is_in]['players']
    level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    await lobby_curr_message.edit(get_lobby_message(lobby_status, lobby_user_is_in, lobby_host, lobby_players, level_chosen))

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await is_everyone_ready(ctx, current_lobbies, lobby_user_is_in, lobby_host)
    await has_everyone_submitted(ctx, current_lobbies, lobby_user_is_in, lobby_host)

@lobby.command()
async def kick(
    ctx,
    player: discord.Option(discord.SlashCommandOptionType.user)
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    player_to_kick = str(player.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!')
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if player is not in the lobby
    if player_to_kick not in current_lobbies['lobbies'][lobby_user_is_hosting]['players']:
        await ctx.respond(f'User not found in lobby!')
        return

    # kick player
    del current_lobbies['lobbies'][lobby_user_is_hosting]['players'][player_to_kick]

    del current_lobbies['users_playing'][player_to_kick]

    await ctx.respond(f'Kicked <@{player_to_kick}>.')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])
    lobby_status = current_lobbies['lobbies'][lobby_user_is_hosting]['status']
    lobby_players = (current_lobbies['lobbies'][lobby_user_is_hosting]['players']).keys()
    level_chosen = current_lobbies['lobbies'][lobby_user_is_hosting]['level']

    await lobby_curr_message.edit(get_lobby_message(lobby_status, lobby_user_is_hosting, user, lobby_players, level_chosen))

    write_json(current_lobbies, 'current_lobbies.json')

    await is_everyone_ready(ctx, current_lobbies, lobby_user_is_hosting, user)
    await has_everyone_submitted(ctx, current_lobbies, lobby_user_is_hosting, user)

@lobby.command()
async def delete(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!')
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])
    await lobby_curr_message.edit(f"This lobby \"{lobby_user_is_hosting}\" has been deleted!")

    del current_lobbies['users_hosting'][user] #user is no longer hosting a lobby

    for player in current_lobbies['lobbies'][lobby_user_is_hosting]['players']:
        del current_lobbies['users_playing'][player] #players are no longer playing

    del current_lobbies['lobbies'][lobby_user_is_hosting]

    await ctx.respond(f'Deleted \"{lobby_user_is_hosting}\".')

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def roll(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Polarity'], default = 'Any', description = 'Default: Any')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!')
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if lobby is not in open state
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Rolling':
        await ctx.respond(f'Your lobby has already rolled a level! Use **/lobby unroll** to re-open your lobby.')
        return
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing, or is waiting on people to submit their miss counts! Kick AFK players if you must.')
        return

    # if no one is playing
    if len(current_lobbies['lobbies'][lobby_user_is_hosting]['players']) == 0:
        await ctx.respond(f'No one is playing!')
        return

    current_lobbies['lobbies'][lobby_user_is_hosting]['status'] = 'Rolling'
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['peer_reviewed'] = peer_reviewed
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['played_before'] = played_before
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['difficulty'] = difficulty
    roll_player_id_list = (current_lobbies['lobbies'][lobby_user_is_hosting]['players']).keys()

    level_chosen = roll_random_level(ctx, peer_reviewed, played_before, difficulty, roll_player_id_list)

    current_lobbies['lobbies'][lobby_user_is_hosting]['level'] = level_chosen

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])

    await lobby_curr_message.edit(f'The lobby \"{lobby_user_is_hosting}\" has rolled a level!')

    lobby_new_message = await ctx.channel.send(get_lobby_rolling_message(current_lobbies['lobbies'][lobby_user_is_hosting]['players'], level_chosen))

    current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'] = lobby_new_message.id

    write_json(current_lobbies, 'current_lobbies.json')

async def unroll_level(ctx, current_lobbies, lobby_name, host):
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_name]['message_id'])
    unrolled_artist = current_lobbies['lobbies'][lobby_name]['level']['artist']
    unrolled_song = current_lobbies['lobbies'][lobby_name]['level']['song']
    unrolled_authors = current_lobbies['lobbies'][lobby_name]['level']['authors']

    await lobby_curr_message.edit(f"The level \"{unrolled_artist} - {unrolled_song}\" (by {unrolled_authors}) was unrolled!")

    current_lobbies['lobbies'][lobby_name]['status'] = 'Open'

    current_lobbies['lobbies'][lobby_name]['roll_settings'] = {}
    current_lobbies['lobbies'][lobby_name]['level'] = {}

    lobby_new_message = await ctx.channel.send(get_lobby_open_message(lobby_name, host, current_lobbies['lobbies'][lobby_name]['players']))

    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def unroll(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!')
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if lobby is not in rolling state
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!')
        return
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing! Wait for everyone to finish.')
        return

    await unroll_level(ctx, current_lobbies, lobby_user_is_hosting, user)

@lobby.command()
async def already_seen(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!')
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!')
        return

    # if rolling
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Rolling':
        lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
        rerolled_artist = current_lobbies['lobbies'][lobby_user_is_in]['level']['artist']
        rerolled_song = current_lobbies['lobbies'][lobby_user_is_in]['level']['song']
        rerolled_authors = current_lobbies['lobbies'][lobby_user_is_in]['level']['authors']

        await lobby_curr_message.edit(f"The level \"{rerolled_artist} - {rerolled_song}\" (by {rerolled_authors}) was rerolled!")

        # unready everyone
        for player in current_lobbies['lobbies'][lobby_user_is_in]['players']:
            current_lobbies['lobbies'][lobby_user_is_in]['players'][player]['ready_status'] = 'Not Ready'

        # choose a new level
        new_peer_reviewed = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['peer_reviewed']
        new_played_before = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['played_before']
        new_difficulty = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['difficulty']
        roll_player_id_list = (current_lobbies['lobbies'][lobby_user_is_in]['players']).keys()

        new_level_chosen = roll_random_level(ctx, new_peer_reviewed, new_played_before, new_difficulty, roll_player_id_list)

        current_lobbies['lobbies'][lobby_user_is_in]['level'] = new_level_chosen

        lobby_new_message = await ctx.channel.send(get_lobby_rolling_message(current_lobbies['lobbies'][lobby_user_is_in]['players'], new_level_chosen))

        current_lobbies['lobbies'][lobby_user_is_in]['message_id'] = lobby_new_message.id

        await ctx.respond(f'Rerolled!')

    elif current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing': #if playing
        # if user has already submitted
        if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Submitted':
            await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)')
            return

        current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Submitted'
        current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['miss_count'] = -1

        lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])

        await lobby_curr_message.edit(get_lobby_playing_message(current_lobbies['lobbies'][lobby_user_is_in]['players']))

        await ctx.respond(f'Submitted! Just wait for everyone else to submit...')

    write_json(current_lobbies, 'current_lobbies.json')

async def begin_match(ctx, current_lobbies, lobby_name):
    current_lobbies['lobbies'][lobby_name]['status'] = 'Playing'

    message = ''

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        message = message + f"<@{player}> "
        current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] = 'Not Yet Submitted'

    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.channel.send(message + '\n**Beginning match in 10 seconds!**')
    time.sleep(7)

    await ctx.channel.send('**3**')
    time.sleep(1)
    await ctx.channel.send('**2**')
    time.sleep(1)
    await ctx.channel.send('**1**')
    time.sleep(1)
    await ctx.channel.send('**GO!**')
    time.sleep(10)

    lobby_new_message = await ctx.channel.send(get_lobby_playing_message(current_lobbies['lobbies'][lobby_name]['players']))

    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id

    write_json(current_lobbies, 'current_lobbies.json')

async def is_everyone_ready(ctx, current_lobbies, lobby_name, host):
    if current_lobbies['lobbies'][lobby_name]['status'] != 'Rolling':
        return

    if len(current_lobbies['lobbies'][lobby_name]['players']) == 0: #no players in lobby
        current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
        await unroll_level(ctx, current_lobbies, lobby_name, host)
        return

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        if current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] == 'Not Ready':
            return

    await begin_match(ctx, current_lobbies, lobby_name)

async def finish_match(ctx, current_lobbies, lobby_name, host):
    unsorted_misses = {}

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        unsorted_misses[player] = current_lobbies['lobbies'][lobby_name]['players'][player]['miss_count']

    sorted_misses = {}
    for player in sorted(unsorted_misses, key=unsorted_misses.get):
        sorted_misses[player] = unsorted_misses[player]

    players_already_seen = []
    players_places = {}

    current_place = 1
    prev_player_place = 1
    prev_misses = -100

    for player in sorted_misses:
        if sorted_misses[player] == -1: #they already played
            players_already_seen.append(player)
        else:
            if sorted_misses[player] == prev_misses: #a tie
                players_places[player] = prev_player_place #give the same place as prev player
            else: #not a tie
                players_places[player] = current_place
                prev_player_place = current_place
            
            current_place = current_place + 1

    for player in players_already_seen: #already played players
        players_places[player] = current_place #joint last place

    level_artist = current_lobbies['lobbies'][lobby_name]['level']['artist']
    level_song = current_lobbies['lobbies'][lobby_name]['level']['song']
    level_authors = current_lobbies['lobbies'][lobby_name]['level']['authors']
    placement_message = f"# Results for {level_artist} - {level_song} (by {level_authors}):\n"

    num_players = len(players_places) #for exp calculation

    users_stats = read_json('users_stats.json')

    players_higher_places = [] #to calculate opponents_beaten_list for each player

    for player in players_places:
        placement_message = placement_message + f"Place {players_places[player]}: <@{player}> (+{num_players*2 - players_places[player]} exp)\n" #(2*players - place) exp gained

        if player not in users_stats:
            users_stats[player] = {}
            users_stats[player]['exp'] = 0
            users_stats[player]['matches_played'] = 0
            users_stats[player]['opponents_beaten'] = 0
            users_stats[player]['opponents_beaten_list'] = []
            users_stats[player]['easy_s_ranked'] = 0
            users_stats[player]['medium_s_ranked'] = 0
            users_stats[player]['tough_s_ranked'] = 0
            users_stats[player]['vt_s_ranked'] = 0
            users_stats[player]['largest_match_played'] = 0
            users_stats[player]['largest_match_won'] = 0
            users_stats[player]['nr_played'] = 0
            users_stats[player]['polarity_played'] = 0

        users_stats[player]['exp'] = users_stats[player]['exp'] + num_players*2 - players_places[player]
        users_stats[player]['matches_played'] = users_stats[player]['matches_played'] + 1
        users_stats[player]['opponents_beaten'] = users_stats[player]['opponents_beaten'] + num_players - players_places[player]
        for better_player in players_higher_places:
            users_stats[better_player]['opponents_beaten_list'].append(player)
            users_stats[better_player]['opponents_beaten_list'] = list(set(users_stats[better_player]['opponents_beaten_list'])) #remove duplicates
        if sorted_misses[player] == 0:
            if current_lobbies['lobbies'][lobby_name]['level']['difficulty'] == 'Easy':
                users_stats[player]['easy_s_ranked'] = users_stats[player]['easy_s_ranked'] + 1
            elif current_lobbies['lobbies'][lobby_name]['level']['difficulty'] == 'Medium':
                users_stats[player]['medium_s_ranked'] = users_stats[player]['medium_s_ranked'] + 1
            elif current_lobbies['lobbies'][lobby_name]['level']['difficulty'] == 'Tough':
                users_stats[player]['tough_s_ranked'] = users_stats[player]['tough_s_ranked'] + 1
            else:
                users_stats[player]['vt_s_ranked'] = users_stats[player]['vt_s_ranked'] + 1
        if len(sorted_misses) > users_stats[player]['largest_match_played']:
            users_stats[player]['largest_match_played'] = len(sorted_misses)
        if (players_places[player] == 1) and (len(sorted_misses) > users_stats[player]['largest_match_won']):
            users_stats[player]['largest_match_won'] = len(sorted_misses)
        if current_lobbies['lobbies'][lobby_name]['level']['peer review status'] == 'Non-Refereed':
            users_stats[player]['nr_played'] = users_stats[player]['nr_played'] + 1
        if current_lobbies['lobbies'][lobby_name]['roll_settings']['difficulty'] == 'Polarity':
            users_stats[player]['polarity_played'] = users_stats[player]['polarity_played'] + 1

    write_json(users_stats, 'users_stats.json')

    await ctx.channel.send(placement_message)

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] = 'Not Ready'
        current_lobbies['lobbies'][lobby_name]['players'][player]['miss_count'] = -2
        #todo: clear comment

    current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
    current_lobbies['lobbies'][lobby_name]['roll_settings'] = {}
    current_lobbies['lobbies'][lobby_name]['level'] = {}

    player_list = current_lobbies['lobbies'][lobby_name]['players']

    lobby_new_message = await ctx.channel.send(get_lobby_open_message(lobby_name, host, player_list))

    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id

    write_json(current_lobbies, 'current_lobbies.json')

async def has_everyone_submitted(ctx, current_lobbies, lobby_name, host):
    if current_lobbies['lobbies'][lobby_name]['status'] != 'Playing':
        return

    if len(current_lobbies['lobbies'][lobby_name]['players']) == 0: #no players in lobby
        current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
        await unroll_level(ctx, current_lobbies, lobby_name, host)
        return

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        if current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] == 'Not Yet Submitted':
            return

    await finish_match(ctx, current_lobbies, lobby_name, host)

@lobby.command()
async def ready(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!')
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!')
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing!')
        return

    # if user is already ready
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Ready':
        await ctx.respond(f'You are already ready!')
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Ready'

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    await lobby_curr_message.edit(get_lobby_rolling_message(current_lobbies['lobbies'][lobby_user_is_in]['players'], lobby_level_chosen))

    await ctx.respond(f'Readied!')

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await is_everyone_ready(ctx, current_lobbies, lobby_user_is_in, lobby_host)

@lobby.command()
async def unready(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!')
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!')
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing!')
        return

    # if user is already not ready
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Not Ready':
        await ctx.respond(f'You are already not ready!')
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Not Ready'

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    await lobby_curr_message.edit(get_lobby_rolling_message(current_lobbies['lobbies'][lobby_user_is_in]['players'], lobby_level_chosen))

    await ctx.respond(f'Unreadied!')

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def submit_misses(
    ctx,
    miss_count: discord.Option(discord.SlashCommandOptionType.integer, description = 'How many misses you got'),
    comment: discord.Option(discord.SlashCommandOptionType.string, description = 'DOESNT CURRENTLY DO ANYTHING DONT USE (Optional) a short comment about the level')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!')
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if lobby isn't playing
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level! (Contact <@1207345676141465622> if you made a mistake.)')
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Rolling':
        await ctx.respond(f'Your lobby has not yet started playing! (Contact <@1207345676141465622> if you made a mistake.)')
        return

    # if user has already submitted
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Submitted':
        await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)')
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Submitted'
    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['miss_count'] = miss_count

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])

    await lobby_curr_message.edit(get_lobby_playing_message(current_lobbies['lobbies'][lobby_user_is_in]['players']))

    await ctx.respond(f'Submitted! Just wait for everyone else to submit...')

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await has_everyone_submitted(ctx, current_lobbies, lobby_user_is_in, lobby_host)

with open('key.txt', 'r') as key_file:
    bot_api_key = key_file.read().rstrip()

bot.run(bot_api_key)