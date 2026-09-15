import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]

# global bot owner — bypasses cooldowns and admin checks in every server
OWNER_ID = 706477292737527829

# how many Modaks a caught rat is worth, as a fraction of its sell_value
CATCH_REWARD_RATIO = 0.2

CATCH_TRIGGER_WORD = "rat"
