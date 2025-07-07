import discord
import json
import csv
import hashlib
import random

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.command()
async def upload_rdsettings(
    ctx,
    settings_rdsave: discord.Option(discord.SlashCommandOptionType.attachment)
):
    with open('users_dict.json', 'r') as in_file:
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
    with open("users_dict.json", "w") as out_file:
        out_file.write(json_object)

    await ctx.respond(f"RDSettings updated!")

@bot.command()
async def roll_level(
    ctx,
    peer_reviewed: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'Yes', description = 'Default: Yes'),
    played: discord.Option(choices = ['Yes', 'No', 'Any'], default = 'No', description = 'Default: No'),
    player_2: discord.Option(discord.SlashCommandOptionType.user, required = False),
    player_3: discord.Option(discord.SlashCommandOptionType.user, required = False),
    player_4: discord.Option(discord.SlashCommandOptionType.user, required = False)
):
    
    id_list = []

    id_list.append(str(ctx.user.id))
    if player_2 != None:
        id_list.append(str(player_2.id))
    if player_3 != None:
        id_list.append(str(player_3.id))
    if player_4 != None:
        id_list.append(str(player_4.id))

    cafe_hashed = {}

    with open('users_dict.json', 'r') as in_file:
        users_dict = json.load(in_file)

    # iterate through cafe dataset
    with open('cafe_query.csv', 'r', encoding='utf-8') as cafe_query:
        for line in csv.DictReader(cafe_query):

            # check if level matches pr option
            pr_check = (peer_reviewed == 'Any') or ((peer_reviewed == 'Yes') and (line['approval'] == '10')) or ((peer_reviewed == 'No') and (line['approval'] == '-1'))

            if pr_check:
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
                    'zip': zip}

    if played == 'No': #remove played levels
        for id in id_list:
            for hash in users_dict[id]:
                if hash in cafe_hashed:
                    del cafe_hashed[hash]

    elif played == 'Yes': #keep only played levels
        hashes_all_played = set()

        # create list with only first user's played levels
        for id in id_list:
            hashes_all_played = hashes_all_played.union(users_dict[id])

        new_cafe_hashed = {}

        # find matching levels on cafe
        for hash in hashes_all_played:
            if hash in cafe_hashed:
                new_cafe_hashed[hash] = cafe_hashed[hash]

        cafe_hashed = new_cafe_hashed

    level_chosen = random.choice(list(cafe_hashed.values()))

    await ctx.respond(f"Your level: " + level_chosen['artist'] + " - " + level_chosen['song'] + " (by " + level_chosen['authors'] + ")\n" + level_chosen['zip'])

with open('key.txt', 'r') as key_file:
    key = key_file.read().rstrip()

bot.run(key)