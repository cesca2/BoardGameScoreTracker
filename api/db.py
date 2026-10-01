import mysql.connector

from api.config import db_config, logger


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
