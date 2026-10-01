from api.queries.player_stats_queries import *
from flask import Blueprint, current_app, jsonify

bp = Blueprint("player-stats", __name__, url_prefix="/player-stats")


@bp.get("/<string:player_name>")
def get_player_stats(player_name):
    try:
        game_count = fetch_player_gamecount(current_app.config["DATABASE"], player_name)
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
        win_count = fetch_player_wincount(current_app.config["DATABASE"], player_name)
        game_highscores = fetch_player_game_highscores(
            current_app.config["DATABASE"], player_name
        )
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
