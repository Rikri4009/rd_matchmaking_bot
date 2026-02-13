import datetime
from discord import Bot
from discord import Activity
from discord import ActivityType
import rd_matchmaking_bot.utils.data as data
import rd_matchmaking_bot.utils.misc as misc


class MatchmakingBot(Bot):
    def __init__(self, *cogs: str):
        super().__init__(activity=Activity(type=ActivityType.competing, name="Do /about for an overview!"))

        self.load_cogs(*cogs)

        self.users_rdsaves = {}
        self.users_stats = {}
        self.game_data = {}
        self.level_history = {}

        self.users_achievements = {} # used to listen for changes to users' achievement levels

        self.load_data()
        self.save_data()


    def load_cogs(self, *cogs: str) -> None:
        for cog in cogs:
            self.load_extension(f"rd_matchmaking_bot.bot.cogs.{cog}")


    def load_data(self):
        path = data.get_path("resources/data")

        self.users_rdsaves = data.read_file(path, "users_rdsaves.json")
        self.users_stats = data.read_file(path, "users_stats.json")
        self.game_data = data.read_file(path, "game_data.json")
        self.level_history = data.read_file(path, "level_history.json")

        self.validate_game_data()
        self.validate_users_stats()


    def save_data(self):
        path = data.get_path("resources/data")

        data.write_json(self.users_rdsaves, path, "users_rdsaves.json")
        data.write_json(self.users_stats, path, "users_stats.json")
        data.write_json(self.game_data, path, "game_data.json")
        data.write_json(self.level_history, path, "level_history.json")

        self.create_users_stats_backup()


    def create_users_stats_backup(self):
        path = data.get_path("resources/data")
        users_stats_backups = data.read_file(path, "users_stats_backups.json")

        users_stats_clone = (self.users_stats).copy()

        now = datetime.datetime.now()

        if (len(users_stats_backups) == 0) or (datetime.datetime.fromtimestamp(users_stats_backups[len(users_stats_backups)-1]["backup_timestamp"]) + datetime.timedelta(hours=12) < now):
            users_stats_backups.append(users_stats_clone)
            users_stats_backups[len(users_stats_backups)-1]["backup_timestamp"] = now.timestamp()

        data.write_json(users_stats_backups, path, "users_stats_backups.json")


    def validate_users_stats(self):
        path = data.get_path("resources/data")

        achievement_list = data.read_file(path, "achievement_requirements.json")

        number_stats = []
        for achievement in (achievement_list["Tiered"] | achievement_list["Secret"]).values():
            number_stats.append(achievement["Assoc_Stat"])

        number_stats.append("current_ascension_difficulty")
        number_stats.append("current_tickets")
        number_stats.append("diamonds")
        number_stats.append("exp_boosters")
        number_stats.append("relic_boxes")
        number_stats.append("last_milestone")
        number_stats.append("exp")
        number_stats.append("level")

        string_stats = ["specialization", "notification_settings"]

        list_stats = ["opponents_beaten_list", "tough_plus_opponents_beaten_list", "quests"]

        for uid, user_stats in (self.users_stats).items():

            for stat in number_stats:
                if stat not in user_stats:
                    user_stats[stat] = 0

            for stat in string_stats:
                if stat not in user_stats:
                    user_stats[stat] = None

            for stat in list_stats:
                if stat not in user_stats:
                    user_stats[stat] = []
            
            while len(user_stats["quests"]) < 2:
                user_stats["quests"].append({})

            if "essences" not in user_stats:
                user_stats["essences"] = {}
                user_stats["essences"]["Apples"] = 0
                user_stats["essences"]["Ivory Dice"] = 0
                user_stats["essences"]["Chronographs"] = 0
                user_stats["essences"]["Shields"] = 0

            if "owned_relics" not in user_stats:
                user_stats["owned_relics"] = {}
                user_stats["owned_relics"]["easy_button"] = 1

            if ("choose_modifiers" not in user_stats["owned_relics"]) and (user_stats["highest_set_beaten"] >= 5):
                user_stats["owned_relics"]["choose_modifiers"] = 1

            if "equipped_relics" not in user_stats:
                user_stats["equipped_relics"] = []

            for i in range(len(user_stats["quests"])):
                if len(user_stats["quests"][i]) < 8:
                    self.refresh_quest(uid, i)

            if uid not in self.users_achievements:
                self.users_achievements[uid] = self.get_user_achievements(None, uid)


    def validate_game_data(self):
        if "lobbies" not in self.game_data:
            self.game_data["lobbies"] = {}
        if "ascension" not in self.game_data:
            self.game_data["ascension"] = {}

        endless_lobbies = self.game_data["ascension"]

        for player in endless_lobbies:
            endless_lobby = endless_lobbies[player]

            if "status" not in endless_lobby:
                endless_lobby["status"] = "Not Started"
            if "ascension_difficulty" not in endless_lobby:
                endless_lobby["ascension_difficulty"] = 0
            if "max_hp" not in endless_lobby:
                endless_lobby["max_hp"] = -1
            if "current_hp" not in endless_lobby:
                endless_lobby["current_hp"] = -1
            if "incoming_damage" not in endless_lobby:
                endless_lobby["incoming_damage"] = -1
            if "current_sp" not in endless_lobby:
                endless_lobby["current_sp"] = -1
            if "sp_times_used" not in endless_lobby:
                endless_lobby["sp_times_used"] = -1
            if "sp_spent" not in endless_lobby:
                endless_lobby["sp_spent"] = -1
            if "current_set" not in endless_lobby:
                endless_lobby["current_set"] = -1
            if "level_number" not in endless_lobby:
                endless_lobby["level_number"] = -1
            if "items" not in endless_lobby:
                endless_lobby["items"] = {}
            if "shields_used" not in endless_lobby:
                endless_lobby["shields_used"] = 0
            if "chosen_item_1" not in endless_lobby:
                endless_lobby["chosen_item_1"] = None
            if "chosen_item_2" not in endless_lobby:
                endless_lobby["chosen_item_2"] = None
            if "extra" not in endless_lobby:
                endless_lobby["extra"] = 0
            if "die_used" not in endless_lobby:
                endless_lobby["die_used"] = False
            if "chronograph_used" not in endless_lobby:
                endless_lobby["chronograph_used"] = False
            if "s_ranked_so_far" not in endless_lobby:
                endless_lobby["s_ranked_so_far"] = False
            if "essence_uses" not in endless_lobby:
                endless_lobby["essence_uses"] = 0
            if "lobby_relics" not in endless_lobby:
                endless_lobby["lobby_relics"] = []
            if "relic_damage_multipliers" not in endless_lobby:
                endless_lobby["relic_damage_multipliers"] = []
            if "set_modifiers_override" not in endless_lobby:
                endless_lobby["set_modifiers_override"] = []
            if "relic_data" not in endless_lobby:
                endless_lobby["relic_data"] = {}
            if "victory_random_reward" not in endless_lobby:
                endless_lobby["victory_random_reward"] = None

            if "set_theme" not in endless_lobby:
                endless_lobby["set_theme"] = None
            if "set_modifier" not in endless_lobby:
                endless_lobby["set_modifier"] = None
            if "roll_tags" not in endless_lobby:
                endless_lobby["roll_tags"] = []
            if "roll_facets" not in endless_lobby:
                endless_lobby["roll_facets"] = {}
            if "set_difficulties" not in endless_lobby:
                endless_lobby["set_difficulties"] = []

            if "no_levels_found_damage_multiplier" not in endless_lobby:
                endless_lobby["no_levels_found_damage_multiplier"] = 1

            current_items = endless_lobby["items"]
            if "Apples" not in current_items:
                current_items["Apples"] = 0
            if "Ivory Dice" not in current_items:
                current_items["Ivory Dice"] = 0
            if "Chronographs" not in current_items:
                current_items["Chronographs"] = 0
            if "Shields" not in current_items:
                current_items["Shields"] = 0


    def lobby_name_user_is_hosting(self, uid):
        for lobby_name in self.game_data["lobbies"]:
            if self.game_data["lobbies"][lobby_name]["host"] == uid:
                return lobby_name
        return None


    def lobby_name_user_is_playing_in(self, uid):
        for lobby_name in self.game_data["lobbies"]:
            if uid in self.game_data["lobbies"][lobby_name]["players"]:
                return lobby_name
        return None


    def get_achievement_milestones(self):
        milestones = {}
        
        def add_milestone(achievement_count, item, type, count):
            milestone = {}
            milestone["item"] = item
            milestone["type"] = type
            milestone["count"] = count
            milestones[achievement_count] = milestone

        add_milestone(10, "exp_boosters", None, 1)
        add_milestone(20, "relic_boxes", None, 1)
        add_milestone(30, "essences", "Apples", 30)
        add_milestone(40, "exp_boosters", None, 4)
        add_milestone(50, "essences", "Ivory Dice", 50)
        add_milestone(60, "relic_boxes", None, 1)
        add_milestone(70, "essences", "Chronographs", 70)
        add_milestone(80, "exp_boosters", None, 8)
        add_milestone(90, "essences", "Shields", 90)

        return milestones


    def get_item_emoji(self, item, type):
        match item:
            case "current_tickets":
                return "🎫"
            case "relic_boxes":
                return "📦"
            case "diamonds":
                return "💎"
            case "exp_boosters":
                return "🧪"
            case "essences":
                match type:
                    case "Apples":
                        return "🌿"
                    case "Ivory Dice":
                        return "🪸"
                    case "Chronographs":
                        return "🍄"
                    case "Shields":
                        return "🪻"

        return "ITEM NOT FOUND"


    def get_item_name(self, item, type):
        match item:
            case "current_tickets":
                return "🎫 Tickets"
            case "relic_boxes":
                return "📦 Relic Boxes"
            case "diamonds":
                return "💎"
            case "exp_boosters":
                return "🧪 EXP Boosters"
            case "essences":
                match type:
                    case "Apples":
                        return "🌿 Apples' Essence"
                    case "Ivory Dice":
                        return "🪸 Ivory Dice's Essence"
                    case "Chronographs":
                        return "🍄 Chronographs' Essence"
                    case "Shields":
                        return "🪻 Shields' Essence"

        return "ITEM NOT FOUND"


    def get_user_achievements(self, ctx, uid):
        if uid not in self.users_stats:
            return None

        this_user_stats = self.users_stats[uid]

        path = data.get_path("resources/data")

        achievement_list = data.read_file(path, "achievement_requirements.json")
        achievement_list['message'] = f"You have **{this_user_stats['exp']}** exp. ({self.exp_to_next_level(uid)} to next level)\n\n**Tiered Achievements:**\n"
        achievement_list['total'] = 0

        for achievement in achievement_list['Tiered']:
            ach_description = achievement_list['Tiered'][achievement]['Description']
            ach_assoc_stat = achievement_list['Tiered'][achievement]['Assoc_Stat']
            ach_requirements = achievement_list['Tiered'][achievement]['Requirements']
            ach_tier = 0

            ach_user_current_stat = this_user_stats[ach_assoc_stat]
            for tier_requirement in ach_requirements:
                if ach_user_current_stat >= tier_requirement:
                    ach_tier = ach_tier + 1

            ach_emoji = misc.get_number_emoji(ach_tier)

            ach_next_tier = ach_tier + 1
            if ach_tier == 7:
                ach_next_tier = ach_tier #no next tier to speak of

            achievement_list['Tiered'][achievement]['tier'] = ach_tier

            if ctx != None:
                achievement_list['Tiered'][achievement]['message_line'] = f'{ach_emoji} [{achievement}]({ctx.channel.jump_url} "{ach_description}"): ({ach_user_current_stat}/{ach_requirements[ach_next_tier-1]})\n'
                achievement_list['message'] = achievement_list['message'] + achievement_list['Tiered'][achievement]['message_line']

            achievement_list['total'] = achievement_list['total'] + ach_tier

        achievement_list['message'] = achievement_list['message'] + '\n**Secret Achievements:**\n'
        for achievement in achievement_list['Secret']:
            ach_description = achievement_list['Secret'][achievement]['Description']
            ach_assoc_stat = achievement_list['Secret'][achievement]['Assoc_Stat']
            ach_requirement = achievement_list['Secret'][achievement]['Requirement']

            if ach_assoc_stat in this_user_stats:
                ach_user_current_stat = this_user_stats[ach_assoc_stat]

                if ach_user_current_stat >= ach_requirement:
                    achievement_list['Secret'][achievement]['tier'] = 1

                    if ctx != None:
                        achievement_list['Secret'][achievement]['message_line'] = f':medal: [{achievement}]({ctx.channel.jump_url} "{ach_description}"): ({ach_user_current_stat}/{ach_requirement})\n'
                        achievement_list['message'] = achievement_list['message'] + achievement_list['Secret'][achievement]['message_line']

                    achievement_list['total'] = achievement_list['total'] + 1
                else:
                    achievement_list['Secret'][achievement]['tier'] = 0

        item_list = ["diamonds", "current_tickets", "exp_boosters", "relic_boxes"]
        essence_list = ["Apples", "Ivory Dice", "Chronographs", "Shields"]

        achievement_list['message'] = achievement_list['message'] + "\n**Items:**"
        for item in item_list:
            achievement_list['message'] = achievement_list['message'] + f" {this_user_stats[item]} {self.get_item_emoji(item, None)} |"
        achievement_list['message'] = achievement_list['message'][:-1]

        achievement_list['message'] = achievement_list['message'] + "\n\n**Essences:**"
        for essence_type in essence_list:
            achievement_list['message'] = achievement_list['message'] + f" {this_user_stats['essences'][essence_type]} {self.get_item_emoji('essences', essence_type)} |"
        achievement_list['message'] = achievement_list['message'][:-1]

        return achievement_list


    def get_play_history(self, uid):
        play_history = []

        for past_lobby in self.level_history:
            if uid in past_lobby['players']:
                play_history.append(past_lobby)

        return play_history


    def get_user_ratings(self, uid):
        play_history = self.get_play_history(uid)

        score_history = {}
        score_history["Easy"] = []
        score_history["Medium"] = []
        score_history["Tough"] = []
        score_history["Very Tough"] = []

        for past_lobby in reversed(play_history):
            level_misses = past_lobby['players'][uid]['miss_count']

            no_difficulty_modifiers = ('difficulty_modifiers' not in past_lobby['roll_settings']) or (len(past_lobby['roll_settings']['difficulty_modifiers']) == 0)

            if no_difficulty_modifiers and (past_lobby['roll_settings']['played_before'] == 'No') and (past_lobby['level']['peer review status'] == 'Peer Reviewed') and (level_misses >= 0):
                level_difficulty = past_lobby['level']['difficulty']

                if len(score_history[level_difficulty]) < 16:
                    score_history[level_difficulty].append(level_misses)

        user_ratings = {}

        difficulty_multiplier = {}
        difficulty_multiplier["Easy"] = 7/60
        difficulty_multiplier["Medium"] = 7/20
        difficulty_multiplier["Tough"] = 7/10
        difficulty_multiplier["Very Tough"] = 7/5

        for difficulty, difficulty_score_history in score_history.items():
            if len(difficulty_score_history) < 4:
                user_ratings[difficulty] = 0
            else:
                difficulty_score_history.sort()

                outlier_count = len(difficulty_score_history) // 4

                #print(difficulty_score_history)
                #remove outlier_count best and worst scores
                for _ in range(outlier_count):
                    difficulty_score_history.pop(0)
                    difficulty_score_history.pop()

                #print(difficulty_score_history)
                average_misses = sum(difficulty_score_history) / len(difficulty_score_history)
                #print(average_misses)
                user_ratings[difficulty] = 70 * difficulty_multiplier[difficulty] / (average_misses + 1)

        user_ratings["Total"] = ( (0.5*user_ratings["Easy"]) + user_ratings["Medium"] + user_ratings["Tough"] + (0.5*user_ratings["Very Tough"]) ) / 3

        return user_ratings


    # not currently in use
    def get_user_stat(self, uid, stat):
        if uid not in self.users_stats:
            return None

        if stat not in self.users_stats[uid]:
            return None

        return self.users_stats[uid][stat]


    # not currently fully in use
    def set_user_stat(self, uid, stat, new_value):
        stat_value = self.get_user_stat(uid, stat)

        if stat_value == None:
            print("INVALID SET_USER_STAT!")
            return

        if type(stat_value) != type(new_value):
            print("INVALID SET_USER_STAT!")
            return

        self.users_stats[uid][stat] = new_value


    def increment_user_stat(self, uid, stat, increment_by, count_for_quests):
        stat_value = self.get_user_stat(uid, stat)

        self.set_user_stat(uid, stat, stat_value + increment_by)

        if count_for_quests:
            self.refresh_eligible_quests(uid)

            user_quests = self.get_user_stat(uid, "quests")

            for i in range(len(user_quests)):
                if user_quests[i]["assoc_stat"] == stat:
                    user_quests[i]["completion"] = min(user_quests[i]["requirement"], user_quests[i]["completion"] + increment_by)


    def refresh_eligible_quests(self, uid):
        user_quests = self.get_user_stat(uid, "quests")

        est_time = datetime.timezone(-datetime.timedelta(hours=5))
        now = datetime.datetime.now(est_time)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(len(user_quests)):
            if user_quests[i]["completion_time"] != None: # if a new day has passed, refresh the quest
                completion_time = datetime.datetime.fromtimestamp(user_quests[i]["completion_time"], est_time)

                if completion_time <= midnight:
                    self.refresh_quest(uid, i)


    def refresh_quest(self, uid, i):
        user_quests = self.get_user_stat(uid, "quests")

        if i == 0:
            user_quests[i]["description"] = "Earn exp from lobbies!"
            user_quests[i]["assoc_stat"] = "exp"
            user_quests[i]["completion"] = 0
            user_quests[i]["requirement"] = 50
            user_quests[i]["completion_time"] = None
            user_quests[i]["reward_stat"] = "diamonds"
            user_quests[i]["reward_amount"] = 1
            user_quests[i]["reward_description"] = "💎"
        elif i == 1:
            user_curr_tickets = self.get_user_stat(uid, "current_tickets")

            user_quests[i]["description"] = "Earn SP as a World Tour supporter!"
            user_quests[i]["assoc_stat"] = "total_sp_earned"
            user_quests[i]["completion"] = 0
            user_quests[i]["requirement"] = 20 + (5 * user_curr_tickets)
            user_quests[i]["completion_time"] = None
            user_quests[i]["reward_stat"] = "current_tickets"
            user_quests[i]["reward_amount"] = 1
            user_quests[i]["reward_description"] = ":ticket:"


    def pop_user_achievement_changes(self, ctx, uid):
        prev_user_achievements = self.users_achievements[uid] # cached achievement list; note that ctx was passed as None
        curr_user_achievements = self.get_user_achievements(ctx, uid) # current true achievement list

        if curr_user_achievements['total'] <= prev_user_achievements['total']:
            return None
        
        new_achievements_message = "**Achievement Unlocked!**\n"

        for achievement in prev_user_achievements["Tiered"]:
            if curr_user_achievements["Tiered"][achievement]['tier'] > prev_user_achievements["Tiered"][achievement]['tier']:
                new_achievements_message = new_achievements_message + curr_user_achievements["Tiered"][achievement]['message_line']

        for achievement in prev_user_achievements["Secret"]:
            if curr_user_achievements["Secret"][achievement]['tier'] > prev_user_achievements["Secret"][achievement]['tier']:
                new_achievements_message = new_achievements_message + curr_user_achievements["Secret"][achievement]['message_line']

        self.users_achievements[uid] = curr_user_achievements

        return new_achievements_message


    def pop_user_completed_quests(self, uid):
        user_quests = self.get_user_stat(uid, "quests")

        completed_quests_message = ""

        for i in range(len(user_quests)):
            if (user_quests[i]["completion_time"] == None) and (user_quests[i]["completion"] >= user_quests[i]["requirement"]):
                self.increment_user_stat(uid, "quests_completed", 1, False)
                self.increment_user_stat(uid, user_quests[i]["reward_stat"], user_quests[i]["reward_amount"], False)

                est_time = datetime.timezone(-datetime.timedelta(hours=5))
                now = datetime.datetime.now(est_time)

                user_quests[i]["completion_time"] = now.timestamp()

                completed_quests_message = completed_quests_message + f"- **Quest {str(i+1)}**: {user_quests[i]['description']} ({user_quests[i]['completion']}/{user_quests[i]['requirement']})\n  - Reward: {user_quests[i]['reward_amount']} {user_quests[i]['reward_description']}"

        if completed_quests_message == "":
            return None
        
        completed_quests_message = "**Quest Completed!**\n" + completed_quests_message
        return completed_quests_message


    def pop_user_milestones(self, uid):
        milestones_message = ""

        achievement_count = self.users_achievements[uid]["total"]
        milestones = self.get_achievement_milestones()
        user_stats = self.users_stats[uid]
        highest_milestone = user_stats["last_milestone"]

        for milestone_requirement in milestones:
            if (user_stats["last_milestone"] < milestone_requirement) and (achievement_count >= milestone_requirement):
                highest_milestone = max(highest_milestone, milestone_requirement)

                item = milestones[milestone_requirement]["item"]
                type = milestones[milestone_requirement]["type"]
                name = self.get_item_name(item, type)
                count = milestones[milestone_requirement]["count"]

                if item == "essences":
                    user_stats["essences"][type] = user_stats["essences"][type] + count
                else:
                    user_stats[item] = user_stats[item] + count

                milestones_message = milestones_message + f"- {milestone_requirement}\⭐ You earned {count} {name}!"

                if item == "exp_boosters":
                    milestones_message = milestones_message + " (Use it in a lobby using `/use_exp_booster` to double exp gain for 5 levels.)"

                milestones_message = milestones_message + "\n"

        if milestones_message == "":
            return None

        user_stats["last_milestone"] = highest_milestone
        milestones_message = "**Milestone Achieved!**\n" + milestones_message
        return milestones_message


    def get_sets_config(self):
        path = data.get_path("resources/data")
        return data.read_file(path, "sets_config.json")


    def get_relic_information(self):
        path = data.get_path("resources/data")
        return data.read_file(path, "relic_information.json")


    def pop_user_levels(self, uid):
        user_stats = self.users_stats[uid]
        levels_message = ""
    
        while self.exp_to_next_level(uid) <= 0:
            user_stats["level"] = user_stats["level"] + 1
            user_stats["diamonds"] = user_stats["diamonds"] + 3
            levels_message = levels_message + f"\🎵 **Level Up!** \🎵\nYou are now Level {user_stats['level']}. (+3 💎)\n"

        return levels_message


    def exp_to_next_level(self, uid):
        user_stats = self.users_stats[uid]
        user_exp = user_stats["exp"]
        user_level = user_stats["level"]

        exp_sum = 0
        increment = 100
        for _ in range(user_level+1):
            exp_sum = exp_sum + increment
            if increment < 300:
                increment = increment + 25

        return exp_sum - user_exp


    async def send_notifications(self, lobby_name, type):
        users_stats = self.users_stats
        lobby = self.game_data["lobbies"][lobby_name]

        if ("channel_id" not in lobby) or ("message_id" not in lobby):
            print("SEND_NOTIFICATION CHANNEL ID NOT FOUND OR MESSAGE ID NOT FOUND")
            return

        channel_id = lobby["channel_id"]
        if channel_id != 1470904655767666698: #make sure lobby is from syncope channel in rdl
            return

        message_id = lobby["message_id"]

        for uid in users_stats:
            if (users_stats[uid]["notification_settings"] == type) and (uid != lobby["host"]) and (uid not in lobby["players"]):
                await self.send_user_dm(uid, f"A lobby is active: https://discord.com/channels/296802696243970049/1470904655767666698/{str(message_id)}!")


    async def send_user_dm(self, uid, message):
        user = await self.fetch_user(uid)
        user_dm_channel = user.dm_channel

        if user_dm_channel == None:
            user_dm_channel = await user.create_dm()

        await user_dm_channel.send(message)


    async def on_ready(self):
        print(f"{self.user.name} is alive!")