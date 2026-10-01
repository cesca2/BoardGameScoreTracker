import mysql.connector
from config import db_config, logger


class DatabaseException(Exception):
    """Exception to raise with user-safe message to pass with 500 status code in case of database operation failure"""


def create_connection(config: dict = db_config):
    connection = None

    try:
        logger.info("Creating MySQL connection")
        connection = mysql.connector.connect(**config)

        if connection.is_connected():
            logger.info("Connection successful")
            return connection

    except mysql.connector.Error as err:
        # log MySQL error in application level to keep any sensitive info hidden
        logger.error(f"Error creating connection: {err}")
        # pass generic error message to return with 500 status code
        raise DatabaseException("Database connection failed")


def db_init(config: dict = db_config, reinit: bool = False):
    # define connection, cursor None so finally executes correctly
    connection = None
    cursor = None
    tables = {}

    tables["games"] = """
        CREATE TABLE IF NOT EXISTS games (
            game_id INT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(100) NOT NULL UNIQUE
        )
        """

    tables["players"] = """
        CREATE TABLE IF NOT EXISTS players (
            player_id INT PRIMARY KEY AUTO_INCREMENT,
            nickname VARCHAR(50) NOT NULL UNIQUE
        )
        """

    tables["sessions"] = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INT PRIMARY KEY AUTO_INCREMENT,
            session_date DATE NOT NULL,
            game_id INT NOT NULL,
            FOREIGN KEY (game_id)
            REFERENCES games (game_id) ON DELETE CASCADE
        )
        """

    tables["sessions_players"] = """
        CREATE TABLE IF NOT EXISTS sessions_players (
            session_id INT NOT NULL,
            player_id INT NOT NULL,
            score INT NOT NULL,
            is_win BOOL NOT NULL,
            PRIMARY KEY (session_id, player_id),
            FOREIGN KEY (session_id)
            REFERENCES sessions (session_id) ON DELETE CASCADE,
            FOREIGN KEY (player_id)
            REFERENCES players (player_id) ON DELETE CASCADE
        )
        """

    try:
        # need to temporarily remove db name from config for initial db creation
        database_name = config.pop("database")
        connection = create_connection(config)

        cursor = connection.cursor()

        # not user input (handled on server only setup) so f-string should be safe in this instance
        if reinit:
            cursor.execute(f"""DROP DATABASE IF EXISTS {database_name}""")
            logger.info(f"Dropped database {database_name}")

        cursor.execute(f"""CREATE DATABASE IF NOT EXISTS {database_name}""")
        logger.info(f"Database {database_name} verified")

        # alternative to running USE database_name
        connection.database = database_name

        for table_name, query in tables.items():
            cursor.execute(query)
            logger.info(f"Table {table_name} verified")

        connection.commit()

    except mysql.connector.Error as err:
        logger.error(f"Error processing database initialisation (db_init): {err}")
        raise DatabaseException("Database operation failed")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
        # make sure temporary removal of "database" from dict is undone regardless of exceptions
        config["database"] = database_name


def fetch_scoreboard_by_id(db, scoreboard_id: int) -> dict:
    cursor = None
    try:
        with create_connection(db) as connection:
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


def fetch_all_scoreboards(db, game: str | None = None, player=str | None) -> list[dict]:
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
        with create_connection(db) as connection:
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


def fetch_player_game_highscores(db, player_name) -> list[dict]:
    game_highscores = []
    cursor = None
    try:
        with create_connection(db) as connection:
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


def fetch_player_gamecount(db, player_name) -> int:
    cursor = None
    try:
        with create_connection(db) as connection:
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


def fetch_player_wincount(db, player_name) -> int:
    cursor = None
    try:
        with create_connection(db) as connection:

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


def insert_new_scoreboard(db, scoreboard) -> int:
    cursor = None
    try:
        with create_connection(db) as connection:

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
