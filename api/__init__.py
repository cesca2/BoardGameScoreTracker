import uuid

from flask import Flask, url_for

from api.config import (
    DB_NAME,
    db_config,
    logger,
)
from api.db import (
    DatabaseException,
    db_init,
)
from api.routes import player_stats, scoreboards


def create_app(db: dict = db_config, testing: bool = False):
    app = Flask(__name__)

    app.testing = testing

    if app.testing:
        db["database"] = DB_NAME + "_test_" + str(uuid.uuid4()).replace("-", "_")
    app.config["DATABASE"] = db

    try:
        logger.info("Initialising database")
        db_init(app.config["DATABASE"])
    except DatabaseException:
        logger.error("Database initialisation failed")

    app.register_blueprint(scoreboards.bp)
    app.register_blueprint(player_stats.bp)

    # home page endpoint
    @app.route("/")
    def home():
        scoreboard_get_url = url_for("scoreboards.get_scoreboards")
        scoreboard_post_url = url_for("scoreboards.create_scoreboard")
        scoreboard_get_id_url = url_for(
            "scoreboards.get_scoreboard_by_id", scoreboard_id=1
        )
        playerstats_get_url = url_for(
            "player-stats.get_player_stats", player_name=":player_name"
        )
        scoreboards_put_url = url_for(
            "scoreboards.update_scoreboard_by_id", scoreboard_id=1
        )
        scoreboards_delete_url = url_for(
            "scoreboards.delete_scoreboard", scoreboard_id=1
        )

        return (
            "<h1>Welcome to the Board Game Score Tracker API</h1>"
            + "<h2>Supported Endpoints</h2>"
            + "<h3>Scoreboards</h3>"
            + f"<p>Retrieve scoreboards: GET {scoreboard_get_url}</p>"
            + f"<p>Retrieve scoreboard by ID: GET {scoreboard_get_id_url}</p>"
            + f"<p>Record new scoreboard: POST {scoreboard_post_url}</p>"
            + f"<p>Record new scoreboard: PUT {scoreboards_put_url}</p>"
            + f"<p>Record new scoreboard: DELETE {scoreboards_delete_url}</p>"
            + "<h3>Player statistics</h3>"
            + f"<p>See player stats: GET {playerstats_get_url}</p>"
        )

    return app
