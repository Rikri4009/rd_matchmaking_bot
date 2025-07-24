def rank_players(unsorted_scores):
    sorted_scores = {}
    for uid in sorted(unsorted_scores, key=unsorted_scores.get, reverse=True):
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
            users_places[user]["text"] = "Disqualified"
        elif users_places[user]["rank"] == 1:
            users_places[user]["text"] = ":first_place:st"
        elif users_places[user]["rank"] == 2:
            users_places[user]["text"] = ":second_place:nd"
        elif users_places[user]["rank"] == 3:
            users_places[user]["text"] = ":third_place:rd"
        else:
            users_places[user]["text"] = str(users_places[user]["rank"]) + "th"

    return users_places