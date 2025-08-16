from discord import Bot
import rd_matchmaking_bot.utils.data as data


class MatchmakingBot(Bot):
    def __init__(self, *cogs: str):
        super().__init__()

        self.load_cogs(*cogs)

        self.users_rdsaves = {}
        self.users_stats = {}
        self.game_data = {}
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

        self.validate_game_data()
        self.validate_users_stats()


    def save_data(self):
        path = data.get_path("resources/data")

        data.write_json(self.users_rdsaves, path, "users_rdsaves.json")
        data.write_json(self.users_stats, path, "users_stats.json")
        data.write_json(self.game_data, path, "game_data.json")


    def validate_users_stats(self):
        path = data.get_path("resources/data")

        achievement_list = data.read_file(path, "achievement_requirements.json")

        number_stats = []
        for achievement in (achievement_list["Tiered"] | achievement_list["Secret"]).values():
            number_stats.append(achievement["Assoc_Stat"])

        number_stats.append("current_ascension_difficulty")

        string_stats = ["specialization"]

        list_stats = ["opponents_beaten_list", "tough_plus_opponents_beaten_list"]

        for user_stats in (self.users_stats).values():

            for stat in number_stats:
                if stat not in user_stats:
                    user_stats[stat] = 0

            for stat in string_stats:
                if stat not in user_stats:
                    user_stats[stat] = None

            for stat in list_stats:
                if stat not in user_stats:
                    user_stats[stat] = []


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


    def get_user_achievements(self, ctx, uid):
        if uid not in self.users_stats:
            return None

        this_user_stats = self.users_stats[uid]

        path = data.get_path("resources/data")

        achievement_list = data.read_file(path, "achievement_requirements.json")
        achievement_list['message'] = '**Tiered Achievements:**\n'
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

            ach_level_desc = 'Unobtained'
            ach_emoji = ''

            match ach_tier:
                case 1:
                    ach_level_desc = 'Bronze'
                    ach_emoji = '<:bronze:1399860108665557043>'
                case 2:
                    ach_level_desc = 'Silver'
                    ach_emoji = '<:silver:1399860110389542915>'
                case 3:
                    ach_level_desc = 'Gold'
                    ach_emoji = '<:gold:1399860113883402270>'
                case 4:
                    ach_level_desc = 'Distinguished'
                    ach_emoji = '<:distinguished:1399860116119093529>'
                case 5:
                    ach_level_desc = 'Illustrious'
                    ach_emoji = '<:illustrious:1399860117700087888>'
                case 6:
                    ach_level_desc = 'Stellar'
                    ach_emoji = '<:stellar:1399860119092854936>'
                case 7:
                    ach_level_desc = 'Medical-Grade'
                    ach_emoji = '<:medical_grade:1399860122288783390>'

            ach_next_tier = ach_tier + 1
            if ach_tier == 7:
                ach_next_tier = ach_tier #no next tier to speak of

            achievement_list['message'] = achievement_list['message'] + f'{ach_emoji} [{achievement}]({ctx.channel.jump_url} "{ach_description}"): ({ach_user_current_stat}/{ach_requirements[ach_next_tier-1]})\n'

            achievement_list['total'] = achievement_list['total'] + ach_tier

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

        return achievement_list


    def get_sets_config(self):
        path = data.get_path("resources/data")
        return data.read_file(path, "sets_config.json")

    async def on_ready(self):
        print(f"{self.user.name} is alive!")