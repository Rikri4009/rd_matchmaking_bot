import discord
from itertools import islice

def rank_players(unsorted_scores, reverse):
    sorted_scores = {}
    for uid in sorted(unsorted_scores, key=unsorted_scores.get, reverse=reverse):
        sorted_scores[uid] = unsorted_scores[uid]

    users_disqualified = []
    users_places = {}
    current_place = 1
    prev_user_place = 1
    prev_score = -100

    for user in sorted_scores:
        users_places[user] = {}
        if sorted_scores[user] == -1: #disqualified
            users_disqualified.append(user)
        else:
            if sorted_scores[user] == prev_score: #a tie
                users_places[user]["rank"] = prev_user_place #give the same place as prev player
            else: #not a tie
                users_places[user]["rank"] = current_place
                prev_user_place = current_place

            prev_score = sorted_scores[user]
            current_place = current_place + 1

    for user in users_disqualified:
        users_places[user]["rank"] = current_place #joint last place

    for user in sorted_scores:
        if sorted_scores[user] == -1:
            users_places[user]["text"] = "(Already Seen)"
        elif users_places[user]["rank"] == 1:
            users_places[user]["text"] = ":first_place:st"
        elif users_places[user]["rank"] == 2:
            users_places[user]["text"] = ":second_place:nd"
        elif users_places[user]["rank"] == 3:
            users_places[user]["text"] = ":third_place:rd"
        else:
            users_places[user]["text"] = str(users_places[user]["rank"]) + "th"

    return users_places

def get_leaderboard_embed(ctx, bot, category, page):
    unsorted_scores = {}

    if category == 'exp':
        category = " " + category
        for uid in bot.users_stats:
            if bot.users_stats[uid]['exp'] > 0: #remove people with 0 exp
                unsorted_scores[uid] = bot.users_stats[uid]['exp']
    else:
        category = "\\" + category
        for uid in bot.users_stats:
            user_achievements = bot.get_user_achievements(ctx, uid)
            if user_achievements['total'] > 0:
                unsorted_scores[uid] = user_achievements['total']

    users_places = rank_players(unsorted_scores, True)

    leaderboard_message = ''

    page_start = (page-1)*10
    page_end = page*10
    for user in islice(users_places, page_start, page_end):
        leaderboard_message = leaderboard_message + f"{users_places[user]['text']} ({unsorted_scores[user]}{category}): <@{user}>\n"

    return discord.Embed(colour = discord.Colour.yellow(), title = f"{category} Leaderboard (Page {page})", description = leaderboard_message)

def get_upload_rdsave_message():
    return f"You haven\'t uploaded your \"settings.rdsave\" file!\n\nTo find this file, first right-click Rhythm Doctor in Steam, and click the button [shown below](https://cdn.discordapp.com/attachments/1392061548549373972/1454561205157888144/image.png?ex=6951892f&is=695037af&hm=9634b8979bd8702491ef77fe4642b8aaa16acb5f37377a0b8795b336bdf9b21a&).\nThen, go to the \"User\" folder, and upload the file called \"settings.rdsave\" using `/upload_rdsave`."

def get_number_emoji(number):
    match number:
        case 0:
            return ''
        case 1:
            return '<:bronze:1399860108665557043>'
        case 2:
            return '<:silver:1399860110389542915>'
        case 3:
            return '<:gold:1399860113883402270>'
        case 4:
            return '<:distinguished:1399860116119093529>'
        case 5:
            return '<:illustrious:1399860117700087888>'
        case 6:
            return '<:stellar:1399860119092854936>'
        case 7:
            return '<:medical_grade:1399860122288783390>'