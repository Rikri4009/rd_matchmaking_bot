from rd_matchmaking_bot.bot import MatchmakingBot
import rd_matchmaking_bot.utils.data as data


cogs = (
    "user_commands",
    "lobby_commands",
    "admin_commands"
)

if __name__ == "__main__":
    rd_bot = MatchmakingBot(*cogs)

    key_path = data.get_path("resources")
    key = open(f"{key_path}/KEY").read()

    rd_bot.run(key)