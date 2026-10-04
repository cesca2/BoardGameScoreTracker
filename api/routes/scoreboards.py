from api.queries.scoreboard_queries import *
from api.utils import check_input_scoreboard
from flask import Blueprint, current_app, jsonify, request, url_for

bp = Blueprint("scoreboards", __name__, url_prefix="/scoreboards")


@bp.get("")
def get_scoreboards():
    search_params = {
        "game": request.args.get("game"),
        "player": request.args.get("player"),
    }
    try:

        scoreboards = fetch_all_scoreboards(
            current_app.config["DATABASE"], **search_params
        )
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


@bp.get("/<int:scoreboard_id>")
def get_scoreboard_by_id(scoreboard_id):
    try:

        scoreboard = fetch_scoreboard_by_id(
            current_app.config["DATABASE"], scoreboard_id
        )
        if scoreboard:
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Retrieved scoreboard for ID {scoreboard_id}.",
                        "data": scoreboard,
                    }
                ),
                200,
            )
        elif scoreboard is None:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"No scoreboard currently exists in our records for ID {scoreboard_id}.",
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


@bp.post("")
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
            id = insert_new_scoreboard(current_app.config["DATABASE"], data)
            new_scoreboard = fetch_scoreboard_by_id(current_app.config["DATABASE"], id)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"New scoreboard created with ID {id}.",
                        "data": new_scoreboard,
                    }
                ),
                201,
                {
                    "Location": url_for(
                        "scoreboards.get_scoreboard_by_id", scoreboard_id=id
                    )
                },
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


@bp.put("/<int:scoreboard_id>")
def update_scoreboard_by_id(scoreboard_id):
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
            scoreboard_exists = fetch_scoreboard_by_id(
                current_app.config["DATABASE"], scoreboard_id
            )

            if scoreboard_exists is not None:
                impact = update_scoreboard(
                    current_app.config["DATABASE"], data, scoreboard_id
                )
                new_scoreboard = fetch_scoreboard_by_id(
                    current_app.config["DATABASE"], scoreboard_id
                )
                if impact > 0:
                    return (
                        jsonify(
                            {
                                "status": "success",
                                "message": f"Scoreboard with ID {scoreboard_id} updated.",
                                "data": new_scoreboard,
                            }
                        ),
                        200,
                        {
                            "Location": url_for(
                                "scoreboards.get_scoreboard_by_id",
                                scoreboard_id=scoreboard_id,
                            )
                        },
                    )
                else:
                    logger.error(
                        f"Update operation for {id} triggered {impact} deletions"
                    )
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Server error occurred.",
                                "error_code": "SERVER_ERROR",
                            }
                        ),
                        500,
                    )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"No scoreboard currently exists in records with ID {scoreboard_id}.",
                            "error_code": "RESOURCE_NOT_FOUND",
                        }
                    ),
                    404,
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


@bp.delete("/<int:scoreboard_id>")
def delete_scoreboard(scoreboard_id):

    try:
        impact = delete_scoreboard_by_id(current_app.config["DATABASE"], scoreboard_id)
        if impact == 1:
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Scoreboard deleted with ID {scoreboard_id}.",
                    }
                ),
                200,
            )
        elif impact == 0:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"No scoreboard currently exists in records with ID {scoreboard_id}.",
                        "error_code": "RESOURCE_NOT_FOUND",
                    }
                ),
                404,
            )
        else:
            logger.error(
                f"Delete operation for {scoreboard_id} triggered {impact} deletions (>1)"
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Server error occurred.",
                        "error_code": "SERVER_ERROR",
                    }
                ),
                500,
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
