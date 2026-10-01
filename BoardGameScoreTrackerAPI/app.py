import uuid

from app_utils import check_input_scoreboard
from config import API_HOST, API_PORT, DB_NAME, db_config, logger
from db_utils import (
    DatabaseException,
    db_init,
    fetch_all_scoreboards,
    fetch_player_game_highscores,
    fetch_player_gamecount,
    fetch_player_wincount,
    fetch_scoreboard_by_id,
    insert_new_scoreboard,
)
from flask import Flask, jsonify, request, url_for


# use create_app function to share app setup code between this file and test_app file with testing=True
def create_app(db: dict = db_config, testing: bool = False):
    app = Flask(__name__)

    app.testing = testing
    if app.testing:
        db_config["database"] = DB_NAME + "_test_" + str(uuid.uuid4()).replace("-", "_")

    try:
        logger.info("Initialising database")
        db_init(db)
    except DatabaseException:
        logger.error("Database initialisation failed")

    # home page endpoint
    @app.route("/")
    def home():
        scoreboard_get_url = url_for("get_scoreboards")
        scoreboard_post_url = url_for("create_scoreboard")
        playerstats_get_url = url_for("get_player_stats", player_name=":player_name")

        return (
            "<h1>Welcome to the Board Game Score Tracker API</h1>"
            + "<h2>Supported Endpoints</h2>"
            + f"<p>See all scoreboards: GET {scoreboard_get_url}</p>"
            + f"<p>Record new scoreboard: POST {scoreboard_post_url}</p>"
            + f"<p>See player stats: GET {playerstats_get_url}</p>"
        )

    @app.get("/scoreboards")
    def get_scoreboards():
        search_params = {
            "game": request.args.get("game"),
            "player": request.args.get("player"),
        }
        try:

            scoreboards = fetch_all_scoreboards(db, **search_params)
            if scoreboards:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": f"Retrieved {len(scoreboards)} scoreboards for {str(search_params).replace("None", "all")}.",
                            "data": scoreboards,
                        }
                    ),
                    200,
                )
            elif scoreboards == []:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"No scoreboards currently exist in our records for {str(search_params).replace("None", "all")}",
                            "error_code": "RESOURCE_NOT_FOUND",
                        }
                    ),
                    404,
                )
        # catches e.g. when connection is None (i.e. cannot connect to MySQL server), problem with SQL queries in development etc...
        except DatabaseException as err:
            logger.error(err)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Server error: {err!s}.",
                        "error_code": "SERVER_ERROR",
                    }
                ),
                500,
            )

    @app.post("/scoreboards")
    def create_scoreboard():
        data = request.json
        # do validation on input data format
        check, message = check_input_scoreboard(data)
        if not check:
            logger.error("Check failed")
            logger.error(message)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid input data for scoreboard: {message}.",
                        "error_code": "INVALID_INPUT",
                    }
                ),
                400,
            )
        else:
            try:
                id = insert_new_scoreboard(db, data)
                new_scoreboard = fetch_scoreboard_by_id(db, id)
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": f"New scoreboard created with ID {id}.",
                            "data": new_scoreboard,
                        }
                    ),
                    201,
                )
            except DatabaseException as err:
                logger.error(err)
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Server error: {err!s}.",
                            "error_code": "SERVER_ERROR",
                        }
                    ),
                    500,
                )

    @app.get("/player-stats/<string:player_name>")
    def get_player_stats(player_name):
        try:
            game_count = fetch_player_gamecount(db, player_name)
            # if no sessions exist in records return player_name not found
            if game_count == 0:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"No stats data available for player with name {player_name.capitalize()}.",
                            "error_code": "RESOURCE_NOT_FOUND",
                        }
                    ),
                    404,
                )
            win_count = fetch_player_wincount(db, player_name)
            game_highscores = fetch_player_game_highscores(db, player_name)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Retrieved stats for {player_name.capitalize()}.",
                        "data": {
                            "total_games": game_count,
                            "total_wins": win_count,
                            "game_highscores": game_highscores,
                        },
                    }
                ),
                200,
            )
        except DatabaseException as err:
            logger.error(err)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Server error: {err!s}.",
                        "error_code": "SERVER_ERROR",
                    }
                ),
                500,
            )

    return app, db


if __name__ == "__main__":
    app, _ = create_app()
    app.run(debug=True, host=API_HOST, port=API_PORT)
