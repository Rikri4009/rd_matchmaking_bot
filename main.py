import discord
import json
import csv
import hashlib
import random
import os
import re
from threading import Thread, Lock

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

@bot.command()
async def roll_level(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Polarity'], default = 'Any', description = 'Default: Any'),
    players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
):
    level_chosen = roll_random_level(ctx, peer_reviewed, played_before, difficulty, create_user_id_list(players, str(ctx.user.id)))

    await ctx.respond(f"Your level: {level_chosen['artist']} - {level_chosen['song']} (by {level_chosen['authors']})\n\
Difficulty: {level_chosen['difficulty']}\n\
{level_chosen['peer review status']}\n\
{level_chosen['zip']}")

lobby = bot.create_group('lobby', 'Lobby/matchmaking commands')

def get_lobby_creation_message(lobby_name, host_id, player_id_list):
    player_list = []
    for id in player_id_list:
        player_list.append('<@' + id + '>')

    players = ', '.join(player_list)

    return '**The lobby \"' + lobby_name + '\" has been created!**\n\
Do __\"/lobby join ' + lobby_name + '\"__ to join. (The host should do this if they want to play!)\n\
Do __\"/lobby leave\"__ to leave.\n\
The host can do __\"/lobby delete\"__ to delete this lobby.\n\
Once everyone has joined, the host should do __\"/lobby roll\"__ to roll a level.\n\n\
**Host:** <@' + host_id + '>\n\
**Players:** ' + players

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
    current_lobbies['lobbies'][name]['players'] = []

    message = await ctx.channel.send(get_lobby_creation_message(name, user, []))

    current_lobbies['lobbies'][name]['message_id'] = message.id

    print(current_lobbies)
    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def join(
    ctx,
    name: discord.Option(discord.SlashCommandOptionType.string, description = 'Name of lobby to join')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is playing in a lobby, or is hosting a lobby different to this one
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
        await ctx.respond(f'That lobby is already rolling for a level! (Consider asking the host to __/lobby unroll__ so that you can join.)')
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

    (current_lobbies['lobbies'][name]['players']).append(user)

    await ctx.respond(f'Joined \"{name}\".')

    if current_lobbies['lobbies'][name]['status'] == 'Open':
        lobby_creation_message = await ctx.fetch_message(current_lobbies['lobbies'][name]['message_id'])
        await lobby_creation_message.edit(get_lobby_creation_message(name, current_lobbies['lobbies'][name]['host'], current_lobbies['lobbies'][name]['players']))

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
    (current_lobbies['lobbies'][lobby_user_is_in]['players']).remove(user)

    del current_lobbies['users_playing'][user]

    await ctx.respond(f'Left \"{lobby_user_is_in}\".')

    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        lobby_creation_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
        await lobby_creation_message.edit(get_lobby_creation_message(lobby_user_is_in, current_lobbies['lobbies'][lobby_user_is_in]['host'], current_lobbies['lobbies'][lobby_user_is_in]['players']))

    write_json(current_lobbies, 'current_lobbies.json')

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
    (current_lobbies['lobbies'][lobby_user_is_hosting]['players']).remove(player_to_kick)

    del current_lobbies['users_playing'][player_to_kick]

    await ctx.respond(f'Kicked <@{player_to_kick}>.')

    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Open':
        lobby_creation_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])
        await lobby_creation_message.edit(get_lobby_creation_message(lobby_user_is_hosting, current_lobbies['lobbies'][lobby_user_is_hosting]['host'], current_lobbies['lobbies'][lobby_user_is_hosting]['players']))

    write_json(current_lobbies, 'current_lobbies.json')

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

    del current_lobbies['users_hosting'][user] #user is no longer hosting a lobby

    for player in current_lobbies['lobbies'][lobby_user_is_hosting]['players']:
        del current_lobbies['users_playing'][player] #players are no longer playing

    del current_lobbies['lobbies'][lobby_user_is_hosting]

    await ctx.respond(f'Deleted \"{lobby_user_is_hosting}\".')

    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command()
async def roll_level(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Polarity'], default = 'Any', description = 'Default: Any'),
    players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
):
    level_chosen = roll_random_level(ctx, peer_reviewed, played_before, difficulty, create_user_id_list(players, str(ctx.user.id)))

    await ctx.respond(f"Your level: {level_chosen['artist']} - {level_chosen['song']} (by {level_chosen['authors']})\n\
Difficulty: {level_chosen['difficulty']}\n\
{level_chosen['peer review status']}\n\
{level_chosen['zip']}")

with open('key.txt', 'r') as key_file:
    key = key_file.read().rstrip()

bot.run(key)