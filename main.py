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

@bot.command(description="Upload your \"settings.rdsave\" file, located in the \"User\" directory of your RD installation")
async def upload_rdsettings(
    ctx,
    settings_rdsave: discord.Option(discord.SlashCommandOptionType.attachment)
):
    file = await settings_rdsave.read()
    attached_rdsettings = json.loads((file.decode('utf-8-sig')).encode('utf-8'))

    users_rdsettings = read_json('users_rdsettings.json')

    user = str(ctx.user.id)
    users_rdsettings[user] = []

    # Extract hash of played levels
    for key, val in attached_rdsettings.items():
        if (key[0:12] == 'CustomLevel_') and (key[(len(key)-7):(len(key))] == '_normal') and (val != 'NotFinished'):
            users_rdsettings[user].append(key[12:(len(key)-7)])

    write_json(users_rdsettings, 'users_rdsettings.json')

    await ctx.respond(f'RDSettings updated!', ephemeral=True)

def create_user_id_list(players, caller_id):
    if players == None:
        players = '<@'+caller_id+'>'

    user_id_list = re.findall(r"\<\@(.*?)\>", players)
    return list(set(user_id_list)) #remove duplicates

def roll_random_level_juxta(peer_reviewed, played_before, difficulty, user_id_list):
    juxta_tracker = read_json('juxta_tracker.json')
    juxta_tracker['current'] = juxta_tracker['current'] + 1
    write_json(juxta_tracker, 'juxta_tracker.json')
    juxta_tracker['current'] = juxta_tracker['current'] - 1
    the_list = [0] * 100

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

            level_diff = 'Easy'
            if line['difficulty'] == '1':
                level_diff = 'Medium'
            elif line['difficulty'] == '2':
                level_diff = 'Tough'
            elif line['difficulty'] == '3':
                level_diff = 'Very Tough'

            authors_list = json.loads(line['authors'])
            authors = ', '.join(authors_list)

            artist = line['artist']
            song = line['song']
            description = line['description']

            hash = hashlib.md5((authors + artist + song).encode())
            hash_hex = hash.hexdigest()

            zip = line['url2']

            image_url = line['image']

            if zip in juxta_tracker['list']:
                index = juxta_tracker['list'].index(zip)
                new_entry = {
                    'authors': authors,
                    'artist': artist,
                    'song': song,
                    'description': description,
                    'difficulty': level_diff,
                    'peer review status': level_pr_status,
                    'hash': hash_hex,
                    'zip': zip,
                    'image_url': image_url}
                the_list[index] = new_entry

                if zip == 'https://codex.rhythm.cafe/kiyubizu-PMtq8Xo2GwK.rdzip':
                    the_list[30] = new_entry
                    the_list[31] = new_entry

    print(len(juxta_tracker))
    return the_list[juxta_tracker['current']]

def roll_random_level(peer_reviewed, played_before, difficulty, user_id_list):

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
            diff_check = (difficulty == 'Any') or (difficulty == level_diff) or ((difficulty == 'Not Easy') and (level_diff != 'Easy')) or ((difficulty == 'Not Very Tough') and (level_diff != 'Very Tough')) or ((difficulty == 'Polarity') and ((level_diff == 'Easy') or (level_diff == 'Very Tough')))

            if pr_check and diff_check:
                authors_list = json.loads(line['authors'])
                authors = ', '.join(authors_list)

                artist = line['artist']
                song = line['song']
                description = line['description']

                hash = hashlib.md5((authors + artist + song).encode())
                hash_hex = hash.hexdigest()

                zip = line['url2']

                image_url = line['image']

                cafe_hashed[hash_hex] = {
                    'hash': hash_hex,
                    'authors': authors,
                    'artist': artist,
                    'song': song,
                    'description': description,
                    'difficulty': level_diff,
                    'peer review status': level_pr_status,
                    'zip': zip,
                    'image_url': image_url}

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

    print(len(cafe_hashed))
    return random.choice(list(cafe_hashed.values()))

def create_level_embed(level_embed, level_chosen):
    level_embed.add_field(name = 'Level', value = f"{level_chosen['artist']} - {level_chosen['song']}", inline = True)
    level_embed.add_field(name = 'Creator', value = level_chosen['authors'], inline = True)
    level_embed.add_field(name = 'Description', value = level_chosen['description'], inline = False)
    level_embed.add_field(name = 'Difficulty', value = level_chosen['difficulty'], inline = True)
    level_embed.add_field(name = 'PR Status', value = level_chosen['peer review status'], inline = True)
    level_embed.add_field(name = 'Download', value = f"[Link]({level_chosen['zip']})", inline = True)

@bot.command(description="(Use \"/lobby roll\" for lobbies!) Rolls a random level with specified settings")
async def out_of_lobby_roll(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Not Easy', 'Not Very Tough', 'Polarity'], default = 'Any', description = 'Default: Any'),
    players: discord.Option(discord.SlashCommandOptionType.string, required = False, description = 'List of @users. Default: Yourself')
):
    user = str(ctx.user.id)

    # if user doesn't have an rdsettings
    rdsettings = read_json('users_rdsettings.json')
    if user not in rdsettings:
        await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use **/upload_rdsettings** to do this.)', ephemeral=True)
        return

    level_chosen = roll_random_level(peer_reviewed, played_before, difficulty, create_user_id_list(players, user))

    level_embed = discord.Embed(colour = discord.Colour.green(), title = f"Here's your level:", image = level_chosen['image_url'])

    create_level_embed(level_embed, level_chosen)

    await ctx.respond(embed=level_embed)

def get_user_achievements(ctx, user):
    users_stats = read_json('users_stats.json')

    if user not in users_stats:
        return None

    this_user_stats = users_stats[user]

    achievement_list = {}
    achievement_list['Tiered'] = {}
    achievement_list['Secret'] = {}
    achievement_list['message'] = '**Tiered Achievements:**\n'
    achievement_list['total'] = 0

    achievement_list['Tiered']['Doctor in Training'] = {}
    achievement_list['Tiered']['Doctor in Training']['Description'] = 'Earned exp'
    achievement_list['Tiered']['Doctor in Training']['Assoc_Stat'] = 'exp'
    achievement_list['Tiered']['Doctor in Training']['Requirements'] = [100, 250, 500, 800, 1300, 2000, 3000]

    achievement_list['Tiered']['Place Your Bets'] = {}
    achievement_list['Tiered']['Place Your Bets']['Description'] = 'Matches played'
    achievement_list['Tiered']['Place Your Bets']['Assoc_Stat'] = 'matches_played'
    achievement_list['Tiered']['Place Your Bets']['Requirements'] = [10, 25, 50, 80, 130, 200, 300]
 
    achievement_list['Tiered']['A Cut Above'] = {}
    achievement_list['Tiered']['A Cut Above']['Description'] = 'Opponents beaten'
    achievement_list['Tiered']['A Cut Above']['Assoc_Stat'] = 'opponents_beaten'
    achievement_list['Tiered']['A Cut Above']['Requirements'] = [30, 80, 160, 300, 450, 700, 1000]

    achievement_list['Tiered']['Well Acquainted'] = {}
    achievement_list['Tiered']['Well Acquainted']['Description'] = 'Unique opponents beaten'
    achievement_list['Tiered']['Well Acquainted']['Assoc_Stat'] = 'unique_opponents_beaten'
    achievement_list['Tiered']['Well Acquainted']['Requirements'] = [3, 7, 12, 18, 25, 32, 40]

    achievement_list['Tiered']['Baking Cake Isn\'t Easy'] = {}
    achievement_list['Tiered']['Baking Cake Isn\'t Easy']['Description'] = 'Easy levels S-ranked on sightread'
    achievement_list['Tiered']['Baking Cake Isn\'t Easy']['Assoc_Stat'] = 'easy_s_ranked'
    achievement_list['Tiered']['Baking Cake Isn\'t Easy']['Requirements'] = [2, 4, 8, 13, 20, 30, 50]

    achievement_list['Tiered']['Middle Difficult'] = {}
    achievement_list['Tiered']['Middle Difficult']['Description'] = 'Medium levels S-ranked on sightread'
    achievement_list['Tiered']['Middle Difficult']['Assoc_Stat'] = 'medium_s_ranked'
    achievement_list['Tiered']['Middle Difficult']['Requirements'] = [2, 4, 8, 13, 20, 30, 50]

    achievement_list['Tiered']['Flawless Performance'] = {}
    achievement_list['Tiered']['Flawless Performance']['Description'] = 'Tough levels S-ranked on sightread'
    achievement_list['Tiered']['Flawless Performance']['Assoc_Stat'] = 'tough_s_ranked'
    achievement_list['Tiered']['Flawless Performance']['Requirements'] = [1, 3, 5, 8, 13, 20, 30]

    achievement_list['Tiered']['Winner Takes All'] = {}
    achievement_list['Tiered']['Winner Takes All']['Description'] = 'Largest match won'
    achievement_list['Tiered']['Winner Takes All']['Assoc_Stat'] = 'largest_match_won'
    achievement_list['Tiered']['Winner Takes All']['Requirements'] = [2, 5, 8, 11, 14, 17, 20]

    achievement_list['Secret']['Mega Lobby'] = {}
    achievement_list['Secret']['Mega Lobby']['Description'] = '20-player match played'
    achievement_list['Secret']['Mega Lobby']['Assoc_Stat'] = 'largest_match_played'
    achievement_list['Secret']['Mega Lobby']['Requirement'] = 20

    achievement_list['Secret']['Godlike'] = {}
    achievement_list['Secret']['Godlike']['Description'] = 'S-rank a Very Tough level on sightread'
    achievement_list['Secret']['Godlike']['Assoc_Stat'] = 'vt_s_ranked'
    achievement_list['Secret']['Godlike']['Requirement'] = 1

    achievement_list['Secret']['Workshop Hell'] = {}
    achievement_list['Secret']['Workshop Hell']['Description'] = 'Play 5 non-refereed levels'
    achievement_list['Secret']['Workshop Hell']['Assoc_Stat'] = 'nr_played'
    achievement_list['Secret']['Workshop Hell']['Requirement'] = 5

    achievement_list['Secret']['So Juxta'] = {}
    achievement_list['Secret']['So Juxta']['Description'] = 'Play 5 levels with the polarity difficulty setting'
    achievement_list['Secret']['So Juxta']['Assoc_Stat'] = 'polarity_played'
    achievement_list['Secret']['So Juxta']['Requirement'] = 5

    achievement_list['Secret']['Hard-Fought Victory'] = {}
    achievement_list['Secret']['Hard-Fought Victory']['Description'] = 'Win a 20-player match... on a Tough level or harder'
    achievement_list['Secret']['Hard-Fought Victory']['Assoc_Stat'] = 'tough_plus_largest_match_won'
    achievement_list['Secret']['Hard-Fought Victory']['Requirement'] = 20

    achievement_list['Secret']['Ruler of the Cosmos'] = {}
    achievement_list['Secret']['Ruler of the Cosmos']['Description'] = 'Want to know what levels I\'ve played? Tough luck, they\'re all NR\'d!'
    achievement_list['Secret']['Ruler of the Cosmos']['Assoc_Stat'] = 'secret_bot'
    achievement_list['Secret']['Ruler of the Cosmos']['Requirement'] = 1

    achievement_list['Secret']['Bearer of the Cosmos'] = {}
    achievement_list['Secret']['Bearer of the Cosmos']['Description'] = 'Survive Quaver\'s challenge'
    achievement_list['Secret']['Bearer of the Cosmos']['Assoc_Stat'] = 'divine_intervention'
    achievement_list['Secret']['Bearer of the Cosmos']['Requirement'] = 1

    for achievement in achievement_list['Tiered']:
        ach_description = achievement_list['Tiered'][achievement]['Description']
        ach_assoc_stat = achievement_list['Tiered'][achievement]['Assoc_Stat']
        ach_requirements = achievement_list['Tiered'][achievement]['Requirements']
        ach_tier = -1

        ach_user_current_stat = this_user_stats[ach_assoc_stat]
        for tier_requirement in ach_requirements:
            if ach_user_current_stat >= tier_requirement:
                ach_tier = ach_tier + 1

        ach_level_desc = 'Unobtained'
        ach_emoji = ''

        ach_value = 0

        match ach_tier:
            case 0:
                ach_level_desc = 'Bronze'
                ach_emoji = ':third_place:'
                ach_value = 1
            case 1:
                ach_level_desc = 'Silver'
                ach_emoji = ':second_place:'
                ach_value = 2
            case 2:
                ach_level_desc = 'Gold'
                ach_emoji = ':first_place:'
                ach_value = 3
            case 3:
                ach_level_desc = 'Distinguished'
                ach_emoji = ':trophy:'
                ach_value = 4
            case 4:
                ach_level_desc = 'Illustrious'
                ach_emoji = ':gem:'
                ach_value = 5
            case 5:
                ach_level_desc = 'Otherworldly'
                ach_emoji = ':comet:'
                ach_value = 6
            case 6:
                ach_level_desc = 'Medical-Grade'
                ach_emoji = ':syringe:'
                ach_value = 7

        ach_next_tier = ach_tier+1
        if ach_tier == 6:
            ach_next_tier = ach_tier #no next tier to speak of

        achievement_list['message'] = achievement_list['message'] + f'{ach_emoji} [{achievement}]({ctx.channel.jump_url} "{ach_description}") ({ach_level_desc}): ({ach_user_current_stat}/{ach_requirements[ach_next_tier]})\n'

        achievement_list['total'] = achievement_list['total'] + ach_value

    achievement_list['message'] = achievement_list['message'] + '\n**Secret Achievements:**\n'
    for achievement in achievement_list['Secret']:
        ach_description = achievement_list['Secret'][achievement]['Description']
        ach_assoc_stat = achievement_list['Secret'][achievement]['Assoc_Stat']
        ach_requirement = achievement_list['Secret'][achievement]['Requirement']

        if ach_assoc_stat in this_user_stats:
            ach_user_current_stat = this_user_stats[ach_assoc_stat]

            if ach_user_current_stat >= ach_requirement:
                achievement_list['message'] = achievement_list['message'] + f':medal: [{achievement}]({ctx.channel.jump_url} "{ach_description}"): ({ach_user_current_stat}/{ach_requirement})\n'

                achievement_list['total'] = achievement_list['total'] + 1

    no_srt3_semifinalists_beaten = 0
    if '298722923626364928' in this_user_stats['opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '1207345676141465622' in this_user_stats['opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '943278556543352873' in this_user_stats['opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '224514766486372352' in this_user_stats['opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    
    if no_srt3_semifinalists_beaten >= 3:
        achievement_list['message'] = achievement_list['message'] + f':medal: [Finalist]({ctx.channel.jump_url} "Beat 3 of 4 RDSRT3 semifinalists"): ({no_srt3_semifinalists_beaten}/3)\n'
        achievement_list['total'] = achievement_list['total'] + 1

    no_srt3_semifinalists_beaten = 0
    if '298722923626364928' in this_user_stats['tough_plus_opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '1207345676141465622' in this_user_stats['tough_plus_opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '943278556543352873' in this_user_stats['tough_plus_opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    if '224514766486372352' in this_user_stats['tough_plus_opponents_beaten_list']:
        no_srt3_semifinalists_beaten = no_srt3_semifinalists_beaten + 1
    
    if no_srt3_semifinalists_beaten >= 3:
        achievement_list['message'] = achievement_list['message'] + f':medal: [Grand Finalist]({ctx.channel.jump_url} "Beat 3 of 4 RDSRT3 semifinalists... on Tough levels or harder"): ({no_srt3_semifinalists_beaten}/3)\n'
        achievement_list['total'] = achievement_list['total'] + 1

    return achievement_list

@bot.command(description="View your milestones")
async def achievements(
    ctx,
    user: discord.Option(discord.SlashCommandOptionType.user, required = False, description = '@user to view achievements of. Default: Yourself')
):
    if user == None:
        ach_user = ctx.user
    else:
        ach_user = user

    ach_user_id = str(ach_user.id)

    achievements_list = get_user_achievements(ctx, ach_user_id)

    if achievements_list == None:
        if ach_user_id == str(ctx.user.id):
            await ctx.respond('You have not played any matches!', ephemeral = True)
        else:
            await ctx.respond('This user has not played any matches!', ephemeral = True)
        return

    tooltipEmbed = discord.Embed(colour = discord.Colour.yellow(), title = f"{ach_user.global_name}\'s Achievements ({achievements_list['total']}★)", description = achievements_list['message'])
    tooltipEmbed.set_footer(text="Hover over text for info!")

    await ctx.respond(embed=tooltipEmbed)

@bot.command(description="See the rankings")
async def leaderboard(
    ctx,
    category: discord.Option(choices = ['exp', '★'], default = 'exp', description = 'Default: exp'),
):
    users_stats = read_json('users_stats.json')

    unsorted_score = {}

    if category == 'exp':
        category = ' ' + category
        for user in users_stats:
            if users_stats[user]['exp'] > 0: #remove people with 0 exp
                unsorted_score[user] = users_stats[user]['exp']
    else:
        for user in users_stats:
            user_achievements = get_user_achievements(ctx, user)
            if user_achievements['total'] > 0:
                unsorted_score[user] = user_achievements['total']

    sorted_score = {}
    for user in sorted(unsorted_score, key=unsorted_score.get, reverse=True):
        sorted_score[user] = unsorted_score[user]

    users_places = {}
    current_place = 1
    prev_user_place = 1
    prev_score = -100

    for user in sorted_score:
        if sorted_score[user] == prev_score: #a tie
            users_places[user] = prev_user_place #give the same place as prev player
        else: #not a tie
            users_places[user] = current_place
            prev_user_place = current_place

        prev_score = sorted_score[user]
        current_place = current_place + 1

    leaderboard_message = ''

    for user in users_places:
        leaderboard_message = leaderboard_message + f"Place {users_places[user]} ({sorted_score[user]}{category}): <@{user}>\n" #(2*players - place) exp gained

    leaderboard_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"{category} Leaderboard", description = leaderboard_message)
    await ctx.respond(embed=leaderboard_embed)

lobby = bot.create_group('lobby', 'Lobby/matchmaking commands')

def get_lobby_open_embed(lobby_name, host_id, player_id_dict):
    player_list = []
    for id in player_id_dict:
        player_list.append('<@' + id + '>')

    players = ', '.join(player_list)

    return discord.Embed(colour = discord.Colour.blue(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n# This lobby is open!\nDo \"**/lobby join {lobby_name}**\" to join.\n\n**Players:** {players}")

def get_lobby_rolling_embed(lobby_name, host_id, player_id_dict, level_chosen):
    ready_list = ''

    for id in player_id_dict:
        ready_list = ready_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    level_embed = discord.Embed(colour = discord.Colour.green(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n\nMake sure you do \"**/lobby already_seen**\" if you recognize this level!\nOtherwise, do \"**/lobby ready**\" when you\'re at the button screen.\nOnce everyone readies, the countdown will begin!\n\n{ready_list}\n", image = level_chosen['image_url'])
    create_level_embed(level_embed, level_chosen)
    return level_embed

def get_lobby_playing_embed(lobby_name, host_id, player_id_dict):
    submitted_list = ''

    for id in player_id_dict:
        submitted_list = submitted_list + '<@' + id + '>: ' + player_id_dict[id]['ready_status'] + '\n'

    return discord.Embed(colour = discord.Colour.red(), title = f"Lobby: \"{lobby_name}\"", description = f"Host: <@{host_id}>\n\nMake sure you do \"**/lobby already_seen**\" if you recognize this level!\nOtherwise, when you\'re done, do \"**/lobby submit_misses**\" to submit your miss count.\nOnce everyone submits, final results will be posted. (The host should kick AFK players.)\n\n{submitted_list}")

def get_lobby_embed(status, lobby_name, host_id, player_id_dict, level_chosen):
    if status == 'Open':
        return get_lobby_open_embed(lobby_name, host_id, player_id_dict)
    elif status == 'Rolling':
        return get_lobby_rolling_embed(lobby_name, host_id, player_id_dict, level_chosen)
    elif status == 'Playing':
        return get_lobby_playing_embed(lobby_name, host_id, player_id_dict)
    else:
        print('Huge Mistake')

@lobby.command(description="List all existing lobbies")
async def list_all(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    # if there are no lobbies
    if len(current_lobbies['lobbies']) == 0:
        await ctx.respond(f'There are currently no lobbies!', ephemeral=True)
        return

    lobby_list_message = ''
    for name in current_lobbies['lobbies']:
        lobby_list_message = lobby_list_message + f"{name}: {len(current_lobbies['lobbies'][name]['players'])} Players\n"

    await ctx.respond(lobby_list_message, ephemeral=True)

@lobby.command(description="Create a lobby")
async def create(
    ctx,
    name: discord.Option(discord.SlashCommandOptionType.string, description = 'Lobby name')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    if name.startswith('the light'): #secret
        await ctx.respond(f'That lobby name is already in use...!?', ephemeral=True)
        return

    # if user is already in a lobby
    if (user in current_lobbies['users_playing']) or (user in current_lobbies['users_hosting']):
        lobby_user_is_in = (current_lobbies['users_playing'] | current_lobbies['users_hosting'])[user]
        await ctx.respond(f'You are already in the lobby \"{lobby_user_is_in}\"!', ephemeral=True)
        return

    # if a lobby with that name exists
    if name in current_lobbies['lobbies']:
        await ctx.respond(f'That lobby name is already in use!', ephemeral=True)
        return

    current_lobbies['users_hosting'][user] = name

    current_lobbies['lobbies'][name] = {}
    current_lobbies['lobbies'][name]['status'] = 'Open'
    current_lobbies['lobbies'][name]['host'] = user
    current_lobbies['lobbies'][name]['players'] = {}
    current_lobbies['lobbies'][name]['roll_settings'] = {}
    current_lobbies['lobbies'][name]['level'] = {}

    write_json(current_lobbies, 'current_lobbies.json')

    message = await ctx.channel.send(embed=get_lobby_open_embed(name, user, []))

    current_lobbies = read_json('current_lobbies.json')
    current_lobbies['lobbies'][name]['message_id'] = message.id
    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.respond(f"<@{user}> You have started hosting the lobby \"{name}\"!\n\
Make sure to do \"**/lobby join {name}**\" if you want to play.\n\
You can do \"**/lobby kick [player]**\" to kick an AFK player.\n\
You can do \"**/lobby delete**\" to delete this lobby. (Don't do this until after level results are sent, it's rude!)\n\n\
Once everyone has joined, do \"**/lobby roll**\" to roll a level.", ephemeral=True)

async def the_light_welcome(ctx, player_id):
    welcome_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Lobby: \"`   ` `     `\"", description = f"`      `: <@{player_id}>\n\n\
Welcome!\nHere, your goal is to `           ` to reach `   ` `     ` at the end of `   ` 7.\n\
Each `   ` consists of 4 `      `.\nYou start with ★ `  `, and will lose 1 for `         `.\n\
**Starting an `       ` costs 5`     `!**\nYou can join `             ` during your `       `.\n\n\
To begin an `       `, type \"**/`                          `**\".")
    await ctx.channel.send(embed = welcome_embed)

    lobbies = read_json('current_lobbies.json')
    if 'the light' not in lobbies:
        lobbies['the light'] = {}
    if player_id not in lobbies['the light']:
        lobbies['the light'][player_id] = {}
        lobbies['the light'][player_id]['status'] = 'Not Started'
        lobbies['the light'][player_id]['set_theme'] = ''
        lobbies['the light'][player_id]['set_modifier'] = ''
        lobbies['the light'][player_id]['set_difficulties'] = []
    write_json(lobbies, 'current_lobbies.json')

async def the_light_begin(ctx, player_id):
    lobbies = read_json('current_lobbies.json')

    if lobbies['the light'][player_id]['status'] != 'Not Started':
        await ctx.respond('You have already started climbing!')
        return

    lobbies['the light'][player_id]['status'] = 'Started'
    write_json(lobbies, 'current_lobbies.json')

    await begin_set(ctx, player_id, 1)

async def begin_set(ctx, player_id, set_number):
    sets_config = {}

    sets_config[1] = {}
    sets_config[1]['difficulties'] = ['Easy', 'Medium', 'Easy', 'Tough']
    sets_config[1]['theme'] = []
    sets_config[1]['modifier'] = []

    sets_config[2] = {}
    sets_config[2]['difficulties'] = ['Easy', 'Medium', 'Medium', 'Tough']
    sets_config[2]['theme'] = ['Holds', 'Skipshots']
    sets_config[2]['modifier'] = []

    sets_config[3] = {}
    sets_config[3]['difficulties'] = ['Easy', 'Medium', 'Medium', 'Tough']
    sets_config[3]['theme'] = []
    sets_config[3]['modifier'] = ['Hard Difficulty Button', '2-Player']

    sets_config[4] = {}
    sets_config[4]['difficulties'] = ['Easy', 'Medium', 'Medium', 'Tough']
    sets_config[4]['theme'] = ['No Classics', 'Syncopation']
    sets_config[4]['modifier'] = []

    sets_config[5] = {}
    sets_config[5]['difficulties'] = []
    sets_config[5]['theme'] = []
    sets_config[5]['modifier'] = ['Blindfolded', 'Chili Speed']

    sets_config[6] = {}
    sets_config[6]['difficulties'] = []
    sets_config[6]['theme'] = ['No Oneshots', 'Freezeshots']
    sets_config[6]['modifier'] = ['Double Damage', 'Endurance']

    sets_config[7] = {}
    sets_config[7]['difficulties'] = []
    sets_config[7]['theme'] = ['None', 'Holds', 'Skipshots', 'No Classics', 'Syncopation', 'No Oneshots', 'Freezeshots', '8-Beat', 'Window Dance']
    sets_config[7]['modifier'] = ['Extreme']

    sets_config['None'] = {}
    sets_config['None']['description'] = 'Anything is possible!'
    sets_config['None']['tags'] = []
    sets_config['None']['facets'] = {}

    sets_config['Holds'] = {}
    sets_config['Holds']['description'] = 'This set\'s levels contain holds.'
    sets_config['Holds']['tags'] = []
    sets_config['Holds']['facets'] = {'has_holds': 1}

    sets_config['Skipshots'] = {}
    sets_config['Skipshots']['description'] = 'This set\'s levels contain skipshots.'
    sets_config['Skipshots']['tags'] = []
    sets_config['Skipshots']['facets'] = {'has_skipshots': 1}

    sets_config['No Classics'] = {}
    sets_config['No Classics']['description'] = 'This set\'s levels don\'t contain classic rows.'
    sets_config['No Classics']['tags'] = []
    sets_config['No Classics']['facets'] = {'has_classics': 0}

    sets_config['Syncopation'] = {}
    sets_config['Syncopation']['description'] = 'This set\'s levels contain syncopation.'
    sets_config['Syncopation']['tags'] = ['syncopation']
    sets_config['Syncopation']['facets'] = {}

    sets_config['8-Beat'] = {}
    sets_config['8-Beat']['description'] = 'This set\'s levels contain 8-beat.'
    sets_config['8-Beat']['tags'] = ['8beat']
    sets_config['8-Beat']['facets'] = {}

    sets_config['No Oneshots'] = {}
    sets_config['No Oneshots']['description'] = 'This set\'s levels don\'t contain oneshot rows.'
    sets_config['No Oneshots']['tags'] = []
    sets_config['No Oneshots']['facets'] = {'has_oneshots': 0}

    sets_config['Freezeshots'] = {}
    sets_config['Freezeshots']['description'] = 'This set\'s levels contain freezeshots.'
    sets_config['Freezeshots']['tags'] = []
    sets_config['Freezeshots']['facets'] = {'has_freezeshots': 1}

    sets_config['Window Dance'] = {}
    sets_config['Window Dance']['description'] = 'This set\'s levels contain window dance.'
    sets_config['Window Dance']['tags'] = []
    sets_config['Window Dance']['facets'] = {'has_window_dance': 1}

    sets_config['Hard Difficulty Button'] = {}
    sets_config['Hard Difficulty Button']['diff_override'] = ['Easy', 'Medium', 'Medium', 'Tough']
    sets_config['Hard Difficulty Button']['description'] = 'You must use the hard difficulty button!'
    sets_config['Hard Difficulty Button']['tags'] = []
    sets_config['Hard Difficulty Button']['facets'] = {}

    sets_config['2-Player'] = {}
    sets_config['2-Player']['diff_override'] = ['Easy', 'Medium', 'Medium', 'Tough']
    sets_config['2-Player']['description'] = 'You must play on 2-player mode!'
    sets_config['2-Player']['tags'] = []
    sets_config['2-Player']['facets'] = {'two_player': 1}

    sets_config['Blindfolded'] = {}
    sets_config['Blindfolded']['diff_override'] = ['Easy', 'Medium', 'Easy', 'Medium']
    sets_config['Blindfolded']['description'] = 'You must play with your eyes fully closed!'
    sets_config['Blindfolded']['tags'] = []
    sets_config['Blindfolded']['facets'] = {}

    sets_config['Chili Speed'] = {}
    sets_config['Chili Speed']['diff_override'] = ['Easy', 'Medium', 'Easy', 'Medium']
    sets_config['Chili Speed']['description'] = 'You must play on :hot_pepper: chili speed!'

    sets_config['Blindfolded']['tags'] = []
    sets_config['Blindfolded']['facets'] = {}

    sets_config['Double Damage'] = {}
    sets_config['Double Damage']['diff_override'] = ['Easy', 'Easy', 'Medium', 'Tough']
    sets_config['Double Damage']['description'] = 'Damage taken is doubled!'
    sets_config['Double Damage']['tags'] = []
    sets_config['Double Damage']['facets'] = {}

    sets_config['Endurance'] = {}
    sets_config['Endurance']['diff_override'] = ['Easy', 'Medium', 'Medium', 'Easy', 'Medium', 'Medium', 'Tough']
    sets_config['Endurance']['description'] = 'This set is extra long!'
    sets_config['Endurance']['tags'] = []
    sets_config['Endurance']['facets'] = {}

    sets_config['Extreme'] = {}
    sets_config['Extreme']['diff_override'] = ['Tough', 'Medium', 'Tough', 'Very Tough']
    sets_config['Extreme']['description'] = 'This set is impossible.'
    sets_config['Extreme']['tags'] = []
    sets_config['Extreme']['facets'] = {}

    lobbies = read_json('current_lobbies.json')

    lobbies['the light'][player_id]['set_number'] = set_number

    theme_and_modifier_desc = ''
    set_difficulties = sets_config[set_number]['difficulties']

    set_theme = 'None'
    if len(sets_config[set_number]['theme']) != 0:
        set_theme = random.choice(sets_config[set_number]['theme'])
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Theme: **{set_theme}**\n{sets_config[set_theme]['description']}\n\n"
    lobbies['the light'][player_id]['set_theme'] = set_theme

    set_modifier = 'None'
    if len(sets_config[set_number]['modifier']) != 0:
        set_modifier = random.choice(sets_config[set_number]['modifier'])
        theme_and_modifier_desc = theme_and_modifier_desc + f"Set Modifier: **{set_modifier}**\n{sets_config[set_modifier]['description']}\n\n"
    lobbies['the light'][player_id]['set_modifier'] = set_modifier

    lobbies['the light'][player_id]['roll_tags'] = sets_config[set_theme]['tags'] + sets_config[set_modifier]['tags']
    lobbies['the light'][player_id]['roll_facets'] = sets_config[set_theme]['facets'] | sets_config[set_modifier]['facets']

    if set_modifier != 'None':
        set_difficulties = sets_config[set_modifier]['diff_override']

    lobbies['the light'][player_id]['set_difficulties'] = set_difficulties

    write_json(lobbies, 'current_lobbies.json')

    set_embed = discord.Embed(colour = discord.Colour.light_grey(), title = f"Lobby: \"`   ` `     `\" | SET {set_number}", description = f"Player: <@{player_id}>\n\n\
{' -> '.join(set_difficulties)}\n\n{theme_and_modifier_desc}When you're ready, abc")
    await ctx.respond(embed = set_embed)

@lobby.command(description="Join a specified lobby")
async def join(
    ctx,
    name: discord.Option(discord.SlashCommandOptionType.string, description = 'Name of lobby to join')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    if name == 'the light': #secret
        await ctx.respond(f'\"Whoa whoa hang on, you think I\'m gonna just let you do THAT?\"\n\
\"...okay, fine, I\'m supposed to let those with 15★ or more in. Don\'t think your attempt will be easy, though!\"\n\
\"...What, you want an achievement? Just for finding this place? But that one\'s MINE! And you barely did any work!\"\n\
\"Fine, I\'ll give you something... if you can survive my level! Given its... PR status, this should be fun to watch...\"', ephemeral=True)
        user_achievements = get_user_achievements(ctx, user)
        if user_achievements['total'] >= 15:
            await the_light_welcome(ctx, user)
        return

    if user in current_lobbies['the light']:
        if name == 'the light begin':
            await the_light_begin(ctx, user)
            return

    # if user is playing in a lobby
    if user in current_lobbies['users_playing']:
        lobby_user_is_in = current_lobbies['users_playing'][user]
        await ctx.respond(f'You are already playing in the lobby \"{lobby_user_is_in}\"!', ephemeral=True)
        return

    # if user is hosting a lobby different to this one
    if (user in current_lobbies['users_hosting']) and (current_lobbies['users_hosting'][user] != name):
        lobby_user_is_in = current_lobbies['users_hosting'][user]
        await ctx.respond(f'You are already hosting the lobby \"{lobby_user_is_in}\"!', ephemeral=True)
        return

    # if lobby doesn't exist
    if name not in current_lobbies['lobbies']:
        await ctx.respond(f'That lobby doesn\'t exist!', ephemeral=True)
        return

    # if lobby is not open
    if current_lobbies['lobbies'][name]['status'] == 'Rolling':
        await ctx.respond(f'That lobby is already rolling for a level! (Consider asking the host to **/lobby unroll** so that you can join.)', ephemeral=True)
        return
    if current_lobbies['lobbies'][name]['status'] == 'Playing':
        await ctx.respond(f'That lobby is already playing!', ephemeral=True)
        return

    # if user doesn't have an rdsettings
    rdsettings = read_json('users_rdsettings.json')
    if user not in rdsettings:
        await ctx.respond(f'You haven\'t uploaded your \"settings.rdsave\" file! (Use **/upload_rdsettings** to do this.)', ephemeral=True)
        return

    current_lobbies['users_playing'][user] = name

    current_lobbies['lobbies'][name]['players'][user] = {}
    current_lobbies['lobbies'][name]['players'][user]['ready_status'] = 'Not Ready'
    current_lobbies['lobbies'][name]['players'][user]['miss_count'] = -2

    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.respond(f'Joined \"{name}\".\nDo \"**/lobby leave**\" to leave.\nWait for the host to roll a level...', ephemeral=True)
    await ctx.channel.send(f'<@{user}> Joined \"{name}\"!')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][name]['message_id'])
    lobby_status = current_lobbies['lobbies'][name]['status']
    lobby_host = current_lobbies['lobbies'][name]['host']
    lobby_players = current_lobbies['lobbies'][name]['players']
    level_chosen = current_lobbies['lobbies'][name]['level']

    await lobby_curr_message.edit(embed=get_lobby_embed(lobby_status, name, lobby_host, lobby_players, level_chosen))

@lobby.command(description="Leave the lobby you're in")
async def leave(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # remove user from current lobby they're in
    del current_lobbies['lobbies'][lobby_user_is_in]['players'][user]

    del current_lobbies['users_playing'][user]

    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.respond(f'Left \"{lobby_user_is_in}\".', ephemeral=True)
    await ctx.channel.send(f'<@{user}> left \"{lobby_user_is_in}\".')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_status = current_lobbies['lobbies'][lobby_user_is_in]['status']
    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    lobby_players = current_lobbies['lobbies'][lobby_user_is_in]['players']
    level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    await lobby_curr_message.edit(embed=get_lobby_embed(lobby_status, lobby_user_is_in, lobby_host, lobby_players, level_chosen))

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await is_everyone_ready(ctx, lobby_user_is_in, lobby_host)
    await has_everyone_submitted(ctx, lobby_user_is_in, lobby_host)

@lobby.command(description="Kick a player from your lobby")
async def kick(
    ctx,
    player: discord.Option(discord.SlashCommandOptionType.user)
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    player_to_kick = str(player.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!', ephemeral=True)
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if player is not in the lobby
    if player_to_kick not in current_lobbies['lobbies'][lobby_user_is_hosting]['players']:
        await ctx.respond(f'User not found in lobby!', ephemeral=True)
        return

    # kick player
    del current_lobbies['lobbies'][lobby_user_is_hosting]['players'][player_to_kick]

    del current_lobbies['users_playing'][player_to_kick]

    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.respond(f'Kicked <@{player_to_kick}>.')

    # edit lobby message
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])
    lobby_status = current_lobbies['lobbies'][lobby_user_is_hosting]['status']
    lobby_players = current_lobbies['lobbies'][lobby_user_is_hosting]['players']
    level_chosen = current_lobbies['lobbies'][lobby_user_is_hosting]['level']

    await lobby_curr_message.edit(embed=get_lobby_embed(lobby_status, lobby_user_is_hosting, user, lobby_players, level_chosen))

    await is_everyone_ready(ctx, lobby_user_is_hosting, user)
    await has_everyone_submitted(ctx, lobby_user_is_hosting, user)

@lobby.command(description="Delete your lobby")
async def delete(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!', ephemeral=True)
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # edit lobby message; possible await race condition here but very unlikely? also not a big deal lol
    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])
    if lobby_curr_message != None:
        await lobby_curr_message.edit(f"This lobby \"{lobby_user_is_hosting}\" has been deleted!", embed=None)

    del current_lobbies['users_hosting'][user] #user is no longer hosting a lobby

    for player in current_lobbies['lobbies'][lobby_user_is_hosting]['players']:
        del current_lobbies['users_playing'][player] #players are no longer playing

    del current_lobbies['lobbies'][lobby_user_is_hosting]

    write_json(current_lobbies, 'current_lobbies.json')

    await ctx.respond(f'Deleted \"{lobby_user_is_hosting}\".')

@lobby.command(description="Roll a random level for your lobby with specified settings")
async def roll(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Not Easy', 'Not Very Tough', 'Polarity'], default = 'Any', description = 'Default: Any')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!', ephemeral=True)
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if lobby is not in open state
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Rolling':
        await ctx.respond(f'Your lobby has already rolled a level! Use **/lobby unroll** to re-open your lobby.', ephemeral=True)
        return
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing, or is waiting on people to submit their miss counts! Kick AFK players if you must.', ephemeral=True)
        return

    # if no one is playing
    if len(current_lobbies['lobbies'][lobby_user_is_hosting]['players']) == 0:
        await ctx.respond(f'No one is playing!', ephemeral=True)
        return

    current_lobbies['lobbies'][lobby_user_is_hosting]['status'] = 'Rolling'
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['peer_reviewed'] = peer_reviewed
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['played_before'] = played_before
    current_lobbies['lobbies'][lobby_user_is_hosting]['roll_settings']['difficulty'] = difficulty
    roll_player_id_list = (current_lobbies['lobbies'][lobby_user_is_hosting]['players']).keys()

    level_chosen = roll_random_level(peer_reviewed, played_before, difficulty, roll_player_id_list)

    current_lobbies['lobbies'][lobby_user_is_hosting]['level'] = level_chosen
    write_json(current_lobbies, 'current_lobbies.json')

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'])

    await lobby_curr_message.edit(f'The lobby \"{lobby_user_is_hosting}\" has rolled a level!', embed=None)

    lobby_new_message = await ctx.channel.send(embed=get_lobby_rolling_embed(lobby_user_is_hosting, user, current_lobbies['lobbies'][lobby_user_is_hosting]['players'], level_chosen))

    await ctx.respond(f'<@{user}> You have rolled a level! No more players may join this lobby.\nYou can do \"**/lobby unroll**\" to trash this selection and allow more players to join.', ephemeral=True)

    current_lobbies = read_json('current_lobbies.json')
    current_lobbies['lobbies'][lobby_user_is_hosting]['message_id'] = lobby_new_message.id
    write_json(current_lobbies, 'current_lobbies.json')

async def unroll_level(ctx, lobby_name, host):
    current_lobbies = read_json('current_lobbies.json')

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_name]['message_id'])
    unrolled_artist = current_lobbies['lobbies'][lobby_name]['level']['artist']
    unrolled_song = current_lobbies['lobbies'][lobby_name]['level']['song']
    unrolled_authors = current_lobbies['lobbies'][lobby_name]['level']['authors']

    current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
    current_lobbies['lobbies'][lobby_name]['roll_settings'] = {}
    current_lobbies['lobbies'][lobby_name]['level'] = {}

    write_json(current_lobbies, 'current_lobbies.json')

    await lobby_curr_message.edit(f"The level \"{unrolled_artist} - {unrolled_song}\" (by {unrolled_authors}) was unrolled!", embed=None)

    lobby_new_message = await ctx.channel.send(embed=get_lobby_open_embed(lobby_name, host, current_lobbies['lobbies'][lobby_name]['players']))

    current_lobbies = read_json('current_lobbies.json')
    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id
    write_json(current_lobbies, 'current_lobbies.json')

@lobby.command(description="Trash your lobby's level selection and re-open it")
async def unroll(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not hosting
    if user not in current_lobbies['users_hosting']:
        await ctx.respond(f'You are not hosting!', ephemeral=True)
        return

    lobby_user_is_hosting = current_lobbies['users_hosting'][user]

    # if lobby is not in rolling state
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
        return
    if current_lobbies['lobbies'][lobby_user_is_hosting]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing! Wait for everyone to finish.', ephemeral=True)
        return

    await unroll_level(ctx, lobby_user_is_hosting, user)

    await ctx.respond("Unrolled.", ephemeral=True)

@lobby.command(description="Use this command if you've seen the rolled level before")
async def already_seen(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
        return

    # if rolling
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Rolling':
        rerolled_artist = current_lobbies['lobbies'][lobby_user_is_in]['level']['artist']
        rerolled_song = current_lobbies['lobbies'][lobby_user_is_in]['level']['song']
        rerolled_authors = current_lobbies['lobbies'][lobby_user_is_in]['level']['authors']

        # unready everyone
        for player in current_lobbies['lobbies'][lobby_user_is_in]['players']:
            current_lobbies['lobbies'][lobby_user_is_in]['players'][player]['ready_status'] = 'Not Ready'

        # choose a new level
        new_peer_reviewed = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['peer_reviewed']
        new_played_before = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['played_before']
        new_difficulty = current_lobbies['lobbies'][lobby_user_is_in]['roll_settings']['difficulty']
        roll_player_id_list = (current_lobbies['lobbies'][lobby_user_is_in]['players']).keys()

        new_level_chosen = roll_random_level(new_peer_reviewed, new_played_before, new_difficulty, roll_player_id_list)

        current_lobbies['lobbies'][lobby_user_is_in]['level'] = new_level_chosen

        write_json(current_lobbies, 'current_lobbies.json')

        lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
        await lobby_curr_message.edit(f"The level \"{rerolled_artist} - {rerolled_song}\" (by {rerolled_authors}) was rerolled!", embed=None)

        lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
        lobby_new_message = await ctx.channel.send(embed=get_lobby_rolling_embed(lobby_user_is_in, lobby_host, current_lobbies['lobbies'][lobby_user_is_in]['players'], new_level_chosen))

        await ctx.respond(f'Rerolled!', ephemeral=True)

        current_lobbies = read_json('current_lobbies.json')
        current_lobbies['lobbies'][lobby_user_is_in]['message_id'] = lobby_new_message.id
        write_json(current_lobbies, 'current_lobbies.json')

    elif current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing': #if playing
        # if user has already submitted
        if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Submitted':
            await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
            return

        current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Submitted'
        current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['miss_count'] = -1

        write_json(current_lobbies, 'current_lobbies.json')

        lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
        lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
        await lobby_curr_message.edit(embed=get_lobby_playing_embed(lobby_user_is_in, lobby_host, current_lobbies['lobbies'][lobby_user_is_in]['players']))

        await ctx.respond(f'Submitted! Just wait for everyone else to submit...', ephemeral=True)

async def begin_match(ctx, lobby_name):
    current_lobbies = read_json('current_lobbies.json')

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

    current_lobbies = read_json('current_lobbies.json')
    lobby_host = current_lobbies['lobbies'][lobby_name]['host']
    lobby_new_message = await ctx.channel.send(embed=get_lobby_playing_embed(lobby_name, lobby_host, current_lobbies['lobbies'][lobby_name]['players']))

    current_lobbies = read_json('current_lobbies.json')
    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id
    write_json(current_lobbies, 'current_lobbies.json')

async def is_everyone_ready(ctx, lobby_name, host):
    current_lobbies = read_json('current_lobbies.json')

    if current_lobbies['lobbies'][lobby_name]['status'] != 'Rolling':
        return

    if len(current_lobbies['lobbies'][lobby_name]['players']) == 0: #no players in lobby
        current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
        await unroll_level(ctx, lobby_name, host)
        return

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        if current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] == 'Not Ready':
            return

    await begin_match(ctx, lobby_name)

async def finish_match(ctx, lobby_name, host):
    current_lobbies = read_json('current_lobbies.json')

    unsorted_misses = {}

    #users_rdsettings = read_json('users_rdsettings.json')
    for player in current_lobbies['lobbies'][lobby_name]['players']:
        unsorted_misses[player] = current_lobbies['lobbies'][lobby_name]['players'][player]['miss_count']

        # add level to player's rdsettings
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

            prev_misses = sorted_misses[player]
            current_place = current_place + 1

    for player in players_already_seen: #already played players
        players_places[player] = current_place #joint last place

    level_artist = current_lobbies['lobbies'][lobby_name]['level']['artist']
    level_song = current_lobbies['lobbies'][lobby_name]['level']['song']
    level_authors = current_lobbies['lobbies'][lobby_name]['level']['authors']
    placement_message = ''

    num_players = len(players_places) #for exp calculation

    users_stats = read_json('users_stats.json')

    for player in players_places:
        placement_message = placement_message + f"Place {players_places[player]}: <@{player}> with {sorted_misses[player]} misses (+{num_players*2 - players_places[player] + 4} exp)\n" #(2*players - place) exp gained

        if player not in users_stats:
            users_stats[player] = {}
            users_stats[player]['exp'] = 0
            users_stats[player]['matches_played'] = 0
            users_stats[player]['opponents_beaten'] = 0
            users_stats[player]['opponents_beaten_list'] = []
            users_stats[player]['tough_plus_opponents_beaten_list'] = []
            users_stats[player]['unique_opponents_beaten'] = 0
            users_stats[player]['easy_s_ranked'] = 0
            users_stats[player]['medium_s_ranked'] = 0
            users_stats[player]['tough_s_ranked'] = 0
            users_stats[player]['vt_s_ranked'] = 0
            users_stats[player]['largest_match_played'] = 0
            users_stats[player]['largest_match_won'] = 0
            users_stats[player]['tough_plus_largest_match_won'] = 0
            users_stats[player]['nr_played'] = 0
            users_stats[player]['polarity_played'] = 0
            users_stats[player]['secret'] = 0

        level_is_tough_plus = (current_lobbies['lobbies'][lobby_name]['level']['difficulty'] == 'Tough') or (current_lobbies['lobbies'][lobby_name]['level']['difficulty'] == 'Very Tough')

        users_stats[player]['exp'] = users_stats[player]['exp'] + num_players*2 - players_places[player] + 4
        users_stats[player]['matches_played'] = users_stats[player]['matches_played'] + 1
        users_stats[player]['opponents_beaten'] = users_stats[player]['opponents_beaten'] + num_players - players_places[player]
        if (current_lobbies['lobbies'][lobby_name]['roll_settings']['played_before'] == 'No'):
            for player_beaten in players_places:
                if (players_places[player] <= players_places[player_beaten]) and (player_beaten != player): #if player did better than player_beaten
                    users_stats[player]['opponents_beaten_list'].append(player_beaten)
                    users_stats[player]['opponents_beaten_list'] = list(set(users_stats[player]['opponents_beaten_list'])) #remove duplicates
                    users_stats[player]['unique_opponents_beaten'] = len(users_stats[player]['opponents_beaten_list'])

                    if level_is_tough_plus:
                        users_stats[player]['tough_plus_opponents_beaten_list'].append(player_beaten)
                        users_stats[player]['tough_plus_opponents_beaten_list'] = list(set(users_stats[player]['tough_plus_opponents_beaten_list'])) #remove duplicates
        if (sorted_misses[player] == 0) and (current_lobbies['lobbies'][lobby_name]['roll_settings']['played_before'] == 'No'):
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
        if (players_places[player] == 1) and (len(sorted_misses) > users_stats[player]['tough_plus_largest_match_won']) and level_is_tough_plus:
            users_stats[player]['tough_plus_largest_match_won'] = len(sorted_misses)
        if current_lobbies['lobbies'][lobby_name]['level']['peer review status'] == 'Non-Refereed':
            users_stats[player]['nr_played'] = users_stats[player]['nr_played'] + 1
        if current_lobbies['lobbies'][lobby_name]['roll_settings']['difficulty'] == 'Polarity':
            users_stats[player]['polarity_played'] = users_stats[player]['polarity_played'] + 1

        # divine intervention secret
        if current_lobbies['lobbies'][lobby_name]['level']['hash'] == 'c0d7a6c64264d812e06707159c297eb2':
            if current_lobbies['lobbies'][lobby_name]['players'][player]['miss_count'] <= 75:
                users_stats[player]['divine_intervention'] = 1

    write_json(users_stats, 'users_stats.json')

    placement_embed = discord.Embed(colour = discord.Colour.yellow(), title = f"Results for {level_artist} - {level_song} (by {level_authors}):", description = placement_message)
    await ctx.channel.send(embed=placement_embed)

    current_lobbies = read_json('current_lobbies.json')

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] = 'Not Ready'
        current_lobbies['lobbies'][lobby_name]['players'][player]['miss_count'] = -2
        #todo: clear comment

    current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
    current_lobbies['lobbies'][lobby_name]['roll_settings'] = {}
    current_lobbies['lobbies'][lobby_name]['level'] = {}

    write_json(current_lobbies, 'current_lobbies.json')

    player_list = current_lobbies['lobbies'][lobby_name]['players']
    lobby_new_message = await ctx.channel.send(embed=get_lobby_open_embed(lobby_name, host, player_list))

    current_lobbies = read_json('current_lobbies.json')
    current_lobbies['lobbies'][lobby_name]['message_id'] = lobby_new_message.id
    write_json(current_lobbies, 'current_lobbies.json')

async def has_everyone_submitted(ctx, lobby_name, host):
    current_lobbies = read_json('current_lobbies.json')

    if current_lobbies['lobbies'][lobby_name]['status'] != 'Playing':
        return

    if len(current_lobbies['lobbies'][lobby_name]['players']) == 0: #no players in lobby
        current_lobbies['lobbies'][lobby_name]['status'] = 'Open'
        await unroll_level(ctx, lobby_name, host)
        return

    for player in current_lobbies['lobbies'][lobby_name]['players']:
        if current_lobbies['lobbies'][lobby_name]['players'][player]['ready_status'] == 'Not Yet Submitted':
            return

    await finish_match(ctx, lobby_name, host)

@lobby.command(description="MAKE SURE YOU\'RE AT THE BUTTON SCREEN!")
async def ready(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
        return

    # if user is already ready
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Ready':
        await ctx.respond(f'You are already ready!', ephemeral=True)
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Ready'

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await lobby_curr_message.edit(embed=get_lobby_rolling_embed(lobby_user_is_in, lobby_host, current_lobbies['lobbies'][lobby_user_is_in]['players'], lobby_level_chosen))

    await ctx.respond(f'Readied!', ephemeral=True)

    await is_everyone_ready(ctx, lobby_user_is_in, lobby_host)

@lobby.command(description="Use this command if you\'re no longer ready")
async def unready(
    ctx
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if level isn't rolled yet
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level!', ephemeral=True)
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Playing':
        await ctx.respond(f'Your lobby is already playing!', ephemeral=True)
        return

    # if user is already not ready
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Not Ready':
        await ctx.respond(f'You are already not ready!', ephemeral=True)
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Not Ready'

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_level_chosen = current_lobbies['lobbies'][lobby_user_is_in]['level']

    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await lobby_curr_message.edit(embed=get_lobby_rolling_embed(lobby_user_is_in, lobby_host, current_lobbies['lobbies'][lobby_user_is_in]['players'], lobby_level_chosen))

    await ctx.respond(f'Unreadied.', ephemeral=True)

@lobby.command(description="Submit your miss count")
async def submit_misses(
    ctx,
    miss_count: discord.Option(discord.SlashCommandOptionType.integer, description = 'How many misses you got')
):
    current_lobbies = read_json('current_lobbies.json')

    user = str(ctx.user.id)

    # if user is not playing
    if user not in current_lobbies['users_playing']:
        await ctx.respond(f'You are not playing in any lobbies!', ephemeral=True)
        return

    lobby_user_is_in = current_lobbies['users_playing'][user]

    # if lobby isn't playing
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Open':
        await ctx.respond(f'Your lobby has not yet rolled a level! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
        return
    if current_lobbies['lobbies'][lobby_user_is_in]['status'] == 'Rolling':
        await ctx.respond(f'Your lobby has not yet started playing! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
        return

    # if user has already submitted
    if current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] == 'Submitted':
        await ctx.respond(f'You already submitted! (Contact <@1207345676141465622> if you made a mistake.)', ephemeral=True)
        return

    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['ready_status'] = 'Submitted'
    current_lobbies['lobbies'][lobby_user_is_in]['players'][user]['miss_count'] = miss_count

    write_json(current_lobbies, 'current_lobbies.json')

    lobby_curr_message = await ctx.fetch_message(current_lobbies['lobbies'][lobby_user_is_in]['message_id'])
    lobby_host = current_lobbies['lobbies'][lobby_user_is_in]['host']
    await lobby_curr_message.edit(embed=get_lobby_playing_embed(lobby_user_is_in, lobby_host, current_lobbies['lobbies'][lobby_user_is_in]['players']))

    await ctx.respond(f'Submitted! Just wait for everyone else to submit...', ephemeral=True)

    await has_everyone_submitted(ctx, lobby_user_is_in, lobby_host)

with open('key.txt', 'r') as key_file:
    bot_api_key = key_file.read().rstrip()

bot.run(bot_api_key)