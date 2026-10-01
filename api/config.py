import logging
import os

from dotenv import load_dotenv

load_dotenv()

DB_NAME = "scoretracker"
API_HOST = os.getenv("API_HOST")
API_PORT = os.getenv("API_PORT")

db_config = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PWD"),
    "database": DB_NAME,
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# control expected format for DTO for creating a scoreboard
# note: no id or date fields as assigned directly in db
APP_CREATE_SCOREBOARD_FIELDS = ["title", "players"]
APP_CREATE_SCOREBOARD_TYPES = {
    "title": str,
    "players": dict,
}
APP_CREATE_SCOREBOARD_PLAYERS_FIELDS = {"win", "score"}
APP_CREATE_SCOREBOARD_PLAYERS_TYPES = {"win": bool, "score": int}
