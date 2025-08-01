import json
import random
import hashlib

import rd_matchmaking_bot.utils.data as data

def roll_random_level(peer_reviewed, played_before, difficulty, user_id_list, users_rdsaves, tags, facets, require_gameplay):

    if difficulty == "Polarity":
        difficulty = random.choice(["Easy", "Easy", "Very Tough"])

    if tags == None:
        tags = []
    if facets == None:
        facets = {}

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

        # does level have all tags
        level_tags = json.loads(line['tags'])

        tags_check = True
        for tag in tags:
            if tag not in level_tags:
                tags_check = False

        # datasette facet check
        facets_check = True
        for facet in facets:
            if facet not in line:
                print("HUGE MISTAKE")
            elif str(facets[facet]) != str(line[facet]):
                facets_check = False

        # require_gameplay check
        has_gameplay_check = False
        if require_gameplay == False:
            has_gameplay_check = True # boolean zen blah blah shut up
        elif (str(line["has_classics"]) == "1") or (str(line["has_oneshots"]) == "1"):
            has_gameplay_check = True

        if pr_check and diff_check and facets_check and tags_check and has_gameplay_check:
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
                'image_url': image_url,
                'tags': level_tags
                }

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

        if len(set_list) == 0:
            return None

        # find levels everyone's played
        hashes_all_played = set.intersection(*set_list)

        new_cafe_hashed = {}

        # find matching levels on cafe
        for hash in hashes_all_played:
            if hash in cafe_hashed:
                new_cafe_hashed[hash] = cafe_hashed[hash]

        cafe_hashed = new_cafe_hashed

    print("Possible levels: " + str(len(cafe_hashed)))

    if len(cafe_hashed) == 0:
        return None

    chosen_level = random.choice(list(cafe_hashed.values()))
    chosen_level["possibilities"] = len(cafe_hashed)

    return chosen_level

def add_level_to_embed(level_embed, level_chosen):
    level_embed.add_field(name = 'Level', value = f"{level_chosen['artist']} - **{level_chosen['song']}**", inline = True)
    level_embed.add_field(name = 'Creator', value = level_chosen['authors'], inline = True)
    level_embed.add_field(name = 'Description', value = level_chosen['description'], inline = False)
    level_embed.add_field(name = 'Tags', value = ', '.join(level_chosen['tags']), inline = False)
    level_embed.add_field(name = 'Difficulty', value = level_chosen['difficulty'], inline = True)
    level_embed.add_field(name = 'PR Status', value = level_chosen['peer review status'], inline = True)
    level_embed.add_field(name = 'Download', value = f"[Link]({level_chosen['zip']})", inline = True)