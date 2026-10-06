import mysql.connector

from api.config import logger
from api.db import (
    DatabaseException,
    create_connection,
)


def fetch_player_gamecount(database_config, player_name) -> int:
    cursor = None
    try:
        with create_connection(database_config) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS game_count FROM sessions_players sp
                JOIN  players p ON p.player_id = sp.player_id
                WHERE p.nickname=%s
                """,
                (player_name,),
            )
            # use fetchone as just expecting one result from aggregate SELECT
            return cursor.fetchone()[0]

    except mysql.connector.Error as err:
        logger.error(f"Error processing db query (fetch_player_gamecount): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()


def fetch_player_wincount(database_config, player_name) -> int:
    cursor = None
    try:
        with create_connection() as connection:

            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS game_count FROM sessions_players sp
                JOIN  players p ON p.player_id = sp.player_id
                WHERE is_win = TRUE AND p.nickname=%s
                """,
                (player_name,),
            )
            # use fetchone as just expecting one result from aggregate SELECT
            return cursor.fetchone()[0]

    except mysql.connector.Error as err:
        logger.error(f"Error processing db query (fetch_player_wincount): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()


def fetch_player_game_highscores(database_config, player_name) -> list[dict]:
    game_highscores = []
    cursor = None
    try:
        with create_connection(database_config) as connection:
            # pre-format result as dictionary
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT g.title, MAX(sp.score ) AS high_score 
                FROM sessions_players sp
                JOIN players p ON p.player_id= sp.player_id
                JOIN sessions s ON sp.session_id = s.session_id 
                JOIN games g ON s.game_id = g.game_id 
                WHERE p.nickname=%s
                GROUP BY g.title
                ORDER BY title ASC;
                """,
                (player_name,),
            )
            game_highscores = cursor.fetchall()

            return game_highscores

    except mysql.connector.Error as err:
        logger.error(f"Error processing db query (fetch_player_game_highscores): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()
