from config import (
    APP_CREATE_SCOREBOARD_FIELDS,
    APP_CREATE_SCOREBOARD_PLAYERS_FIELDS,
    APP_CREATE_SCOREBOARD_PLAYERS_TYPES,
    APP_CREATE_SCOREBOARD_TYPES,
)


def check_input_scoreboard(scoreboard: dict) -> tuple[bool, str]:
    for field in APP_CREATE_SCOREBOARD_FIELDS:
        if field not in scoreboard:
            return False, f"Required field is missing: '{field}'"

    for field, value in scoreboard.items():
        if field not in APP_CREATE_SCOREBOARD_FIELDS:
            return False, f"Invalid field included: '{field}'"
        elif not isinstance(value, APP_CREATE_SCOREBOARD_TYPES[field]):
            return (
                False,
                f"Type for field '{field}' should be {APP_CREATE_SCOREBOARD_TYPES[field]}, provided {type(value)}",
            )
    # get players nested dictionaries under each player name and check inputs
    players_info = scoreboard["players"].items()
    for player_name, player_dict in players_info:
        if not isinstance(player_name, str):
            return False, "'players' must have type str for name (dictionary key)"
        for field in APP_CREATE_SCOREBOARD_PLAYERS_FIELDS:
            if field not in player_dict:
                return (
                    False,
                    f"Required field '{field}' is missing for player '{player_name}'",
                )

        for player_field, value in player_dict.items():
            if player_field not in APP_CREATE_SCOREBOARD_PLAYERS_FIELDS:
                return False, f"Invalid field included: '{player_field}'"
            elif not isinstance(
                value,
                APP_CREATE_SCOREBOARD_PLAYERS_TYPES[player_field],
            ):
                return (
                    False,
                    f"Type for field '{player_field}' for player '{player_name}' should be {APP_CREATE_SCOREBOARD_PLAYERS_TYPES[player_field]}, provided {type(value)}",
                )

    return True, ""
