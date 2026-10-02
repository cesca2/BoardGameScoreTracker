import mysql.connector
from api.config import logger
from api.db import (
    DatabaseException,
    create_connection,
)


def delete_scoreboard_by_id(database_config, scoreboard_id: int) -> int:
    cursor = None
    try:
        with create_connection(database_config) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM sessions
                WHERE session_id = %s
                """,
                (scoreboard_id,),
            )
            impact = cursor.rowcount
            if impact == 1:
                connection.commit()
            return impact

    except mysql.connector.Error as err:
        logger.error(f"Error processing db operation (delete_scoreboard_by_id): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()


def fetch_scoreboard_by_id(database_config, scoreboard_id: int) -> dict:
    cursor = None
    try:
        with create_connection(database_config) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT s.session_id, s.session_date, g.title, p.nickname, sp.score, sp.is_win  
                FROM sessions s
                JOIN games g ON s.game_id = g.game_id
                JOIN sessions_players sp ON s.session_id = sp.session_id
                JOIN players p ON p.player_id = sp.player_id
                WHERE s.session_id = %s
                """,
                (scoreboard_id,),
            )
            scoreboard = None
            # convert results into our APIs format for a scoreboard object
            for id, date, title, nickname, score, is_win in cursor:
                # if not existant create new scoreboard object
                if not scoreboard:
                    scoreboard = {
                        "id": id,
                        "title": title,
                        "date": date.strftime("%a, %d %b %Y"),
                        "players": {},
                    }
                # insert player data (unique player info per row in query)
                scoreboard["players"][nickname] = {"win": bool(is_win), "score": score}

            return scoreboard

    except mysql.connector.Error as err:
        logger.error(f"Error processing db query (fetch_scoreboard_by_id): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()


def fetch_all_scoreboards(
    datbase_config, game: str | None = None, player=str | None
) -> list[dict]:
    scoreboards = []
    cursor = None

    # handle query parameters to filter results
    filter_queries = []
    filter_params = []
    if game is not None:
        filter_queries.append("g.title = %s")
        filter_params.append(game)
    if player is not None:
        filter_queries.append("p.nickname = %s")
        filter_params.append(player)

    try:
        with create_connection(datbase_config) as connection:
            cursor = connection.cursor()
            # use cte to grab list of session ids to use in main query if filtering applied
            if filter_queries:
                where_clause = " WHERE " + " AND ".join(filter_queries) + ")"
                filter_query = """
                WITH ids AS ( SELECT s.session_id 
                                FROM sessions s
                                JOIN games g ON s.game_id = g.game_id
                                JOIN sessions_players sp ON s.session_id = sp.session_id
                                JOIN players p ON p.player_id = sp.player_id
                """ + where_clause
                filter_where = "WHERE s.session_id IN (SELECT * FROM ids)"
            else:
                filter_query = ""
                filter_where = ""
            # append cte string before main select and use WHERE clause after to select filter from cte
            cursor.execute(
                filter_query + f"""
                SELECT s.session_id, s.session_date, g.title, p.nickname, sp.score, sp.is_win  
                FROM sessions s
                JOIN games g ON s.game_id = g.game_id
                JOIN sessions_players sp ON s.session_id = sp.session_id
                JOIN players p ON p.player_id = sp.player_id
                {filter_where}
                ORDER BY g.title, s.session_date
                """,
                (tuple(filter_params)),
            )
            # convert results into our APIs format for a scoreboard object
            for id, date, title, nickname, score, is_win in cursor:
                # check if a given scoreboard already exists in our list by the session id (unique per scoreboard)
                scoreboard = [s for s in scoreboards if s["id"] == id]
                # if not create new scoreboard object
                if not scoreboard:
                    scoreboard = {
                        "id": id,
                        "title": title,
                        "date": date.strftime("%a, %d %b %Y"),
                        "players": {},
                    }
                    scoreboards.append(scoreboard)
                # otherwise grab existing object -- just take first index as uniquely id'ed should only ever be one result
                else:
                    scoreboard = scoreboard[0]
                # insert player data (unique player info per row in query)
                scoreboard["players"][nickname] = {"win": bool(is_win), "score": score}

            return scoreboards

    except mysql.connector.Error as err:
        logger.error(f"Error processing db query (fetch_all_scoreboards): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()


def insert_new_scoreboard(database_config, scoreboard) -> int:
    cursor = None
    try:
        with create_connection(database_config) as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT IGNORE INTO games (title)
                VALUES (%s);
                """,
                (scoreboard["title"],),
            )
            cursor.execute(
                """
                INSERT INTO sessions (game_id, session_date)
                SELECT game_id, CURRENT_DATE()
                FROM games
                WHERE title = %s
                """,
                (scoreboard["title"],),
            )
            # scoreboard can be uniquely identified by the session id
            scoreboard_id = cursor.lastrowid
            # now know about cursor.lastrowid user-defined variable not strictly necessary here
            cursor.execute("""SELECT LAST_INSERT_ID() INTO @session_id""")

            for k, v in scoreboard["players"].items():
                cursor.execute(
                    """
                    INSERT IGNORE INTO players (nickname)
                    VALUES ( %s )
                    """,
                    (k,),
                )
                cursor.execute(
                    """
                    SELECT player_id FROM players
                    WHERE nickname = %s INTO @player_id
                    """,
                    (k,),
                )
                cursor.execute(
                    """
                    INSERT INTO sessions_players (session_id, player_id, score, is_win)
                    VALUES (@session_id, @player_id, %s, %s);
                    """,
                    (v["score"], v["win"]),
                )
            connection.commit()
            return scoreboard_id

    except mysql.connector.Error as err:
        logger.error(f"Error processing db operation (insert_new_scoredboard): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()
