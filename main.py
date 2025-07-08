import discord
import json
import csv
import hashlib
import random
import os
import re

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.command()
async def upload_rdsettings(
    ctx,
    settings_rdsave: discord.Option(discord.SlashCommandOptionType.attachment)
):
    with open(os.path.realpath(__file__) + '\\..\\users_dict.json', 'r') as in_file:
        users_dict = json.load(in_file)

    file = await settings_rdsave.read()
    user_rdsettings = json.loads((file.decode('utf-8-sig')).encode("utf-8"))

    user = str(ctx.user.id)
    users_dict[user] = []

    # Extract hash of played levels
    for key, val in user_rdsettings.items():
        if (key[0:12] == 'CustomLevel_') and (key[(len(key)-7):(len(key))] == '_normal') and (val != 'NotFinished'):
            users_dict[user].append(key[12:(len(key)-7)])

    json_object = json.dumps(users_dict, indent=4)
    with open(os.path.realpath(__file__) + "\\..\\users_dict.json", "w") as out_file:
        out_file.write(json_object)

    await ctx.respond(f"RDSettings updated!")

@bot.command()
async def roll_level(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played_before: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    difficulty: discord.Option(choices = ['Easy', 'Medium', 'Tough', 'Very Tough', 'Any', 'Polarity'], default = 'Any', description = 'Default: Any'),
    players: discord.Option(discord.SlashCommandOptionType.string, default = "", description = 'List of @users; no need to include yourself'),
):
    id_list = re.findall(r"\<\@(.*?)\>", players)

    id_list.append(str(ctx.user.id)) #add the user invoking the command

    id_list = list(set(id_list)) #remove duplicates

    cafe_hashed = {}

    with open(os.path.realpath(__file__) + '\\..\\users_dict.json', 'r') as in_file:
        users_dict = json.load(in_file)

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
        for id in id_list:
            if id in users_dict:
                for hash in users_dict[id]:
                    if hash in cafe_hashed:
                        del cafe_hashed[hash]

    elif played_before == 'Yes': #keep only played levels
        set_list = []

        # create list of users' played levels as sets
        for id in id_list:
            if id in users_dict:
                set_list.append(set(users_dict[id]))

        # find levels everyone's played
        hashes_all_played = set.intersection(*set_list)

        new_cafe_hashed = {}

        # find matching levels on cafe
        for hash in hashes_all_played:
            if hash in cafe_hashed:
                new_cafe_hashed[hash] = cafe_hashed[hash]

        cafe_hashed = new_cafe_hashed

    level_chosen = random.choice(list(cafe_hashed.values()))

    await ctx.respond(f"Your level: {level_chosen['artist']} - {level_chosen['song']} (by {level_chosen['authors']})\nDifficulty: {level_chosen['difficulty']} // {level_chosen['peer review status']}\n{level_chosen['zip']}")

with open('key.txt', 'r') as key_file:
    key = key_file.read().rstrip()

bot.run(key)