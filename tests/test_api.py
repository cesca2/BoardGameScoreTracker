import unittest

from api import create_app
from api.config import logger
from api.db import create_connection
from api.queries.scoreboard_queries import fetch_scoreboard_by_id, insert_new_scoreboard


class ApiTestCase(unittest.TestCase):

    def setUp(self):
        # setup app
        self.app = create_app(testing=True)
        self.ctx = self.app.app_context()
        self.ctx.push()
        # setup client to run requests in tests
        self.client = self.app.test_client()
        # share mock data between methods for initialising db where necessary
        self.init_scoreboards = [
            {
                "players": {
                    "Cat": {"win": False, "score": 115},
                    "Joe": {
                        "win": True,
                        "score": 120,
                    },
                },
                "title": "Ark Nova",
            },
            {
                "players": {
                    "Cat": {"win": False, "score": 92},
                    "Joe": {
                        "win": True,
                        "score": 120,
                    },
                },
                "title": "Ark Nova",
            },
            {
                "players": {
                    "Lisa": {"score": 166, "win": True},
                    "Mike": {"score": 136, "win": False},
                    "Paul": {"score": 120, "win": False},
                },
                "title": "Emberleaf",
            },
            {
                "players": {
                    "Cat": {"score": 239, "win": True},
                    "Paul": {"score": 162, "win": False},
                },
                "title": "Forest Shuffle",
            },
            {
                "players": {
                    "Cat": {"score": 129, "win": True},
                    "Paul": {"score": 113, "win": False},
                },
                "title": "Terraforming Mars",
            },
            {
                "players": {
                    "Luke": {"score": 82, "win": True},
                    "Mike": {"score": 60, "win": False},
                },
                "title": "Wingspan",
            },
        ]

    def tearDown(self):
        # drop database after each test for clean db per test

        try:
            with create_connection(self.app.config["DATABASE"]) as connection:
                logger.info(
                    f"Dropping database {self.app.config["DATABASE"]["database"]}"
                )
                cursor = connection.cursor()
                cursor.execute(
                    f"DROP DATABASE {self.app.config["DATABASE"]["database"]}"
                )
            self.ctx.pop()
        finally:
            if cursor:
                cursor.close()

    def test_get_scoreboards(self):
        # Arrange
        # Insert mock data for this test

        for scoreboard in self.init_scoreboards:
            insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        # Act
        response = self.client.get("/scoreboards")
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], list)
        # check expected top-level keys in first object in response list are present
        self.assertIn("title", response.json["data"][0])
        self.assertIn("players", response.json["data"][0])
        self.assertIn("date", response.json["data"][0])
        self.assertIn("id", response.json["data"][0])
        # check each scoreboard from db initialisation is included in response
        self.assertEqual(len(response.json["data"]), len(self.init_scoreboards))
        for scoreboard in response.json["data"]:
            self.assertIn(
                {k: scoreboard[k] for k in ["players", "title"]}, self.init_scoreboards
            )

    def test_get_scoreboard_by_id(self):
        # Arrange
        # Insert mock data for this test
        scoreboard = self.init_scoreboards[0]
        scoreboard_id = insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        # Act
        response = self.client.get(f"/scoreboards/{scoreboard_id}")
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], dict)
        # check expected top-level keys in first object in response list are present
        self.assertIn("title", response.json["data"])
        self.assertIn("players", response.json["data"])
        self.assertIn("date", response.json["data"])
        self.assertIn("id", response.json["data"])
        # check scoreboard from dto is equivalent to that returned in response
        self.assertEqual(
            {k: response.json["data"][k] for k in ["players", "title"]},
            scoreboard,
        )

    def test_get_scoreboards_query_no_results(self):
        # Arrange
        name = "Fake"
        # Act
        response = self.client.get(
            f"/scoreboards?player={name}",
        )
        # Assert
        # check status code
        self.assertEqual(response.status_code, 404)

    def test_get_scoreboards_query_player(self):
        # Arrange
        # Insert mock data for this test

        for scoreboard in self.init_scoreboards:
            insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        name = "Cat"
        # Act
        response = self.client.get(
            f"/scoreboards?player={name}",
        )
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], list)
        # check expected top-level keys in first object in response list are present
        self.assertIn("title", response.json["data"][0])
        self.assertIn("players", response.json["data"][0])
        self.assertIn("date", response.json["data"][0])
        self.assertIn("id", response.json["data"][0])
        # check each relevant scoreboard from db initialisation is included in response
        for scoreboard in response.json["data"]:
            self.assertEqual(
                len(response.json["data"]),
                len([s for s in self.init_scoreboards if name in s["players"]]),
            )
            self.assertIn(
                {k: scoreboard[k] for k in ["players", "title"]},
                [s for s in self.init_scoreboards if name in s["players"]],
            )

    def test_get_scoreboards_query_game(self):
        # Arrange
        # Insert mock data for this test

        for scoreboard in self.init_scoreboards:
            insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        game = "Ark Nova"
        # Act
        response = self.client.get(
            f"/scoreboards?game={game}",
        )
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], list)
        # check expected top-level keys in first object in response list are present
        self.assertIn("title", response.json["data"][0])
        self.assertIn("players", response.json["data"][0])
        self.assertIn("date", response.json["data"][0])
        self.assertIn("id", response.json["data"][0])
        # check each relevant scoreboard from db initialisation is included in response
        for scoreboard in response.json["data"]:
            self.assertEqual(
                len(response.json["data"]),
                len([s for s in self.init_scoreboards if game in s["title"]]),
            )
            self.assertIn(
                {k: scoreboard[k] for k in ["players", "title"]},
                [s for s in self.init_scoreboards if game in s["title"]],
            )

    def test_get_scoreboards_query_player_and_game(self):
        # Arrange
        # Insert mock data for this test

        for scoreboard in self.init_scoreboards:
            insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        game = "Ark Nova"
        name = "Cat"
        # Act
        response = self.client.get(
            f"/scoreboards?game={game}&player={name}",
        )
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], list)
        # check expected top-level keys in first object in response list are present
        self.assertIn("title", response.json["data"][0])
        self.assertIn("players", response.json["data"][0])
        self.assertIn("date", response.json["data"][0])
        self.assertIn("id", response.json["data"][0])
        # check each relevant scoreboard from db initialisation is included in response
        for scoreboard in response.json["data"]:
            self.assertEqual(
                len(response.json["data"]),
                len(
                    [
                        s
                        for s in self.init_scoreboards
                        if game in s["title"] and name in s["players"]
                    ]
                ),
            )
            self.assertIn(
                {k: scoreboard[k] for k in ["players", "title"]},
                [
                    s
                    for s in self.init_scoreboards
                    if game in s["title"] and name in s["players"]
                ],
            )

    def test_get_player_stats(self):
        # Arrange
        # Insert mock data for this test

        for scoreboard in self.init_scoreboards:
            insert_new_scoreboard(self.app.config["DATABASE"], scoreboard)
        # Act
        response = self.client.get("/player-stats/cat")
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check list instance
        self.assertIsInstance(response.json["data"], dict)
        # check expected data are present
        self.assertIn("game_highscores", response.json["data"])
        self.assertIsInstance(response.json["data"]["game_highscores"], list)
        self.assertIn("total_games", response.json["data"])
        self.assertIsInstance(response.json["data"]["total_games"], int)
        self.assertIn("total_wins", response.json["data"])
        self.assertIsInstance(response.json["data"]["total_wins"], int)

        # do some calculation on mock data to sanity check results
        self.assertEqual(response.json["data"]["total_games"], 4)
        self.assertEqual(response.json["data"]["total_wins"], 2)
        self.assertIn(
            {"title": "Ark Nova", "high_score": 115},
            response.json["data"]["game_highscores"],
        )
        self.assertIn(
            {"high_score": 239, "title": "Forest Shuffle"},
            response.json["data"]["game_highscores"],
        )
        self.assertIn(
            {"high_score": 129, "title": "Terraforming Mars"},
            response.json["data"]["game_highscores"],
        )

    def test_get_player_stats_unknown_player(self):
        # Act
        response = self.client.get("/player-stats/fake")
        # Assert
        # check status code
        self.assertEqual(response.status_code, 404)

    def test_get_scoreboards_no_scoreboards(self):
        # Act
        response = self.client.get("/scoreboards")
        # Assert
        # check status code
        self.assertEqual(response.status_code, 404)

    def test_create_scoreboard(self):
        # Arrange
        # create test data for post request
        test_scoreboard_dto = {
            "title": "Test Game",
            "players": {
                "Player1": {"score": 100, "win": True},
                "Player2": {"score": 70, "win": False},
            },
        }
        # Act
        response = self.client.post(
            "/scoreboards",
            json=test_scoreboard_dto,
        )
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            {k: response.json["data"][k] for k in ["players", "title"]},
            test_scoreboard_dto,
        )

    def test_create_scoreboard_incorrect_dto(self):
        # Arrange
        # capture edge cases for incorrect dtos
        incorrect_dtos = []
        incorrect_dtos.append(
            ### MISSING FIELDS ###
            # missing title
            {
                "players": {
                    "Player1": {"score": 100, "win": True},
                    "Player2": {"score": 70, "win": False},
                },
            }
        )
        incorrect_dtos.append(
            # missing score for Player1
            {
                "title": "Test Game",
                "players": {
                    "Player1": {"win": True},
                    "Player2": {"score": 70, "win": False},
                },
            }
        )
        incorrect_dtos.append(
            # missing win for Player2
            {
                "title": "Test Game",
                "players": {
                    "Player1": {"win": True, "score": 100},
                    "Player2": {
                        "score": 70,
                    },
                },
            }
        )
        ### TYPE ERRORS ###
        incorrect_dtos.append(
            # title incorrect type
            {
                "title": 1,
                "players": {
                    "Player1": {"win": True, "score": 100},
                    "Player2": {"score": 70, "win": False},
                },
            }
        )
        incorrect_dtos.append(
            # score incorrect type for Player 2
            {
                "title": "Test Game",
                "players": {
                    "Player1": {"win": True, "score": 100},
                    "Player2": {"score": "70", "win": False},
                },
            }
        )
        incorrect_dtos.append(
            # win incorrect type
            {
                "title": "Test Game",
                "players": {
                    "Player1": {"win": True, "score": 100},
                    "Player2": {"score": 70, "win": 0},
                },
            }
        )
        incorrect_dtos.append(
            # incorrect type for 'players' (list not dict)
            {
                "title": "Test Game",
                "players": [
                    {"win": True, "score": 100},
                    {"score": 70, "win": False},
                ],
            }
        )

        ### ADDITIONAL FIELDS ###
        incorrect_dtos.append(
            {
                "extra_field": "extra_data",
                "title": "Test Game",
                "players": {
                    "Player1": {"score": 100, "win": True},
                    "Player2": {"score": 70, "win": False},
                },
            }
        )
        incorrect_dtos.append(
            {
                "title": "Test Game",
                "players": {
                    "Player1": {
                        "score": 100,
                        "win": True,
                        "extra_field": "extra_data",
                    },
                    "Player2": {"score": 70, "win": False},
                },
            }
        )

        for dto in incorrect_dtos:
            # Act
            response = self.client.post(
                "/scoreboards",
                json=dto,
            )
            # Assert
            with self.subTest(dto=dto):
                self.assertEqual(response.status_code, 400)
                self.assertIn(
                    "Invalid input data for scoreboard", response.json["message"]
                )

    def test_delete_scoreboard(self):
        # Arrange
        scoreboard_id = insert_new_scoreboard(
            self.app.config["DATABASE"], self.init_scoreboards[0]
        )
        # Act
        response = self.client.delete(
            f"/scoreboards/{scoreboard_id}",
        )
        # Assert
        # check status code
        self.assertEqual(response.status_code, 200)
        # check record does not exist
        self.assertIsNone(
            fetch_scoreboard_by_id(self.app.config["DATABASE"], scoreboard_id)
        )

    def test_delete_scoreboard_no_record(self):
        # Arrange - db is initially empty
        # Act
        response = self.client.delete(
            "/scoreboards/0",
        )
        # Assert
        # check record does not exist - ensures integrity of test
        self.assertIsNone(fetch_scoreboard_by_id(self.app.config["DATABASE"], 0))
        # check status code
        self.assertEqual(response.status_code, 404)
