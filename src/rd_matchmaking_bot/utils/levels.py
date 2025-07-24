import json
import random
import hashlib

import rd_matchmaking_bot.utils.data as data

def roll_random_level(peer_reviewed, played_before, difficulty, user_id_list, users_rdsaves):

    cafe_hashed = {}

    # iterate through cafe dataset
    path = data.get_path("resources/data")

    cafe_levels = data.read_file(path, "cafe_query.csv")

    for line in cafe_levels:
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
            if uid in users_rdsaves:
                for hash in users_rdsaves[uid]:
                    if hash in cafe_hashed:
                        del cafe_hashed[hash]

    elif played_before == 'Yes': #keep only played levels
        set_list = []

        # create list of users' played levels as sets
        for uid in user_id_list:
            if uid in users_rdsaves:
                set_list.append(set(users_rdsaves[uid]))

        # find levels everyone's played
        hashes_all_played = set.intersection(*set_list)

        new_cafe_hashed = {}

        # find matching levels on cafe
        for hash in hashes_all_played:
            if hash in cafe_hashed:
                new_cafe_hashed[hash] = cafe_hashed[hash]

        cafe_hashed = new_cafe_hashed

    print("Possible levels: " + str(len(cafe_hashed)))
    return random.choice(list(cafe_hashed.values()))

def add_level_to_embed(level_embed, level_chosen):
    level_embed.add_field(name = 'Level', value = f"{level_chosen['artist']} - {level_chosen['song']}", inline = True)
    level_embed.add_field(name = 'Creator', value = level_chosen['authors'], inline = True)
    level_embed.add_field(name = 'Description', value = level_chosen['description'], inline = False)
    level_embed.add_field(name = 'Difficulty', value = level_chosen['difficulty'], inline = True)
    level_embed.add_field(name = 'PR Status', value = level_chosen['peer review status'], inline = True)
    level_embed.add_field(name = 'Download', value = f"[Link]({level_chosen['zip']})", inline = True)