import os
import re
import sys

import requests
from dotenv import load_dotenv
from rich import print as rich_print
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

load_dotenv()

API_HOST = os.getenv("API_HOST")
API_PORT = os.getenv("API_PORT")
APP_BASE_URL = "http://" + API_HOST + ":" + API_PORT

APP_INPUTTEXT_SUPPORTED_REGEX = r"^[a-zA-Z0-9  ,!-'#_]+$"
APP_INPUTTEXT_UNSUPPORTED_CHARS_REGEX = r"[^a-zA-Z0-9  ,!-'#_]"
APP_INPUTTEXT_CHARLIMIT = 50  # hard limit on player name in API db


console = Console()


class InvalidInputTextLength(Exception):
    pass


class InvalidInputTextCharactersException(Exception):
    pass


# validate input text from user in text prompts
def check_input_text(text: str) -> tuple[bool, str]:
    try:
        if len(text) > APP_INPUTTEXT_CHARLIMIT or len(text) == 0:
            raise InvalidInputTextLength("Length of text is invalid")
        elif not re.match(APP_INPUTTEXT_SUPPORTED_REGEX, text):
            raise InvalidInputTextCharactersException("Text characters not supported")

    except InvalidInputTextLength:
        if text:
            validation_message = f"Please adjust your entry. Text exceeds character limit (input is currently {len(text)} characters, limit is {APP_INPUTTEXT_CHARLIMIT})"
        else:
            validation_message = "Please enter text (length of input is currently 0)"
        return False, validation_message
    except InvalidInputTextCharactersException:

        validation_message = f"Please adjust characters used, unsupported characters were included: {" and ".join(set(re.findall(APP_INPUTTEXT_UNSUPPORTED_CHARS_REGEX, text)))}"

        return False, validation_message
    else:
        return True, ""


def create_record_user_input() -> dict:
    while True:
        prompt_title = Prompt.ask(
            "Please enter the [dark_orange3]game title[/dark_orange3]"
        )
        check, message = check_input_text(prompt_title)
        if check:
            break
        else:
            rich_print(f"[prompt.invalid]{message}")
            continue

    while True:
        prompt_players = Prompt.ask(
            "Please enter the [cyan]player names[/cyan] [magenta][As a comma separated list][/magenta]"
        )
        check, message = check_input_text(prompt_players)
        if check:
            break
        else:
            rich_print(f"[prompt.invalid]{message}")
            continue
    # from list of players can now break down prompts to get info relevant to each player winner/scores for dto
    players_dict = {}
    for player in [i.strip() for i in prompt_players.split(",")]:
        players_dict[player] = {"win": False, "score": 0}

    prompt_winner = Prompt.ask(
        "Who is the [cornflower_blue]winner[/cornflower_blue]?",
        choices=[i.strip() for i in prompt_players.split(",")],
    )
    players_dict[prompt_winner]["win"] = True

    for k, v in players_dict.items():
        prompt_score = IntPrompt.ask(f"Add a [green]score[/green] for [cyan]{k}[/cyan]")
        v["score"] = prompt_score

    return {"title": prompt_title, "players": players_dict}


def create_record_menu():
    console.rule("[gold3]Creating new record", style="gold3")
    # take user input
    new_record = create_record_user_input()
    # create table object to display entered information back to user
    table = Table(
        title=f"\n{new_record['title']}",
        show_lines=True,
        title_style="dark_orange3",
    )
    table.add_column("Name", justify="right", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Winner?", justify="right", style="dark_magenta")
    for player, player_dict in new_record["players"].items():
        win = ":trophy:" if player_dict["win"] else ""
        table.add_row(
            player,
            str(player_dict["score"]),
            win,
        )
    console.print(table)
    # confirm entry before posting to API
    confirm = Confirm.ask("Confirm entry")
    if not confirm:
        console.rule("[red]Record creation cancelled", style="red")
    else:
        try:
            response = requests.post(APP_BASE_URL + "/scoreboards", json=new_record)
            # raise exception if not 200 status code
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            # for HTTPError server sends an error message to help client debug
            error = response.json().get("message")
            rich_print(
                f"[red]Something went wrong with your request: {error} Please try again later!"
            )
            console.rule("[red]Record creation cancelled", style="red")
        else:
            rich_print(
                f"[green]Recorded your scoreboard successfully! Your scoreboard ID is: {response.json()["data"]["id"]}"
            )
            console.rule("[green]Record creation success", style="green")


def display_stats_menu():
    # take necessary user input for endpoint -- player name
    while True:

        player_name = Prompt.ask("Please enter the [cyan]player name")
        check, message = check_input_text(player_name)
        if check:
            break
        else:
            rich_print(f"[prompt.invalid]{message}")
            continue
    try:
        response = requests.get(APP_BASE_URL + f"/player-stats/{player_name}")
        # raise exception if not 200 status code
        response.raise_for_status()

    except requests.exceptions.HTTPError:
        # for HTTPError server sends an error message to help client debug
        error = response.json().get("message")
        rich_print(
            f"[red]Something went wrong with your request. {error} Please try again later!"
        )
    else:
        # JSON decoding etc exceptions caught at run() function level
        stats = response.json()["data"]
        # display data back to user
        console.rule(f"[gold3]Displaying player stats for {player_name}", style="gold3")
        table = Table(
            title=f"\nGames played: {stats["total_games"]}\n [dark_magenta]Games won: {stats["total_wins"]}[/dark_magenta]",
            show_lines=True,
            title_style="cornflower_blue",
        )
        table.add_column("Game", justify="right", style="dark_orange3")
        table.add_column("High Score", justify="right", style="green")
        for game in stats["game_highscores"]:
            table.add_row(
                game["title"],
                str(game["high_score"]),
            )

        console.print(table)
        console.rule(style="gold3")


def display_records_menu():
    # take optional inputs for query parameters in scoreboards endpoint
    filters = {}
    confirm = Confirm.ask("Would you like to filter the results?")
    if confirm:
        while True:
            rich_print(
                Panel.fit(
                    f"[gold3]Would you like to filter the records?[/gold3]\n[cornflower_blue]Current filters {filters}",
                    border_style="red",
                    title="Filter Records Menu",
                    padding=2,
                )
            )
            selection = Prompt.ask(
                "\nEnter filter option to edit",
                choices=["player", "game"],
                default="Continue",  # this lets user just press enter to continue
                show_choices=True,
                show_default=True,
            )

            if selection == "Continue":
                break
            else:
                filters[selection] = Prompt.ask("Enter new value")
    try:
        response = requests.get(APP_BASE_URL + "/scoreboards", params=filters)
        # raise exception if not 200 status code
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        # for HTTPError server sends an error message to help client debug
        error = response.json().get("message")
        rich_print(
            f"[red]Something went wrong with your request. {error}. Please try again later!"
        )
    else:
        # display data back to user
        filter_string = ""
        if filters:
            filter_string += " for "
            if filters.get("player") is not None:
                filter_string += filters.get("player") + "'s "
            if filters.get("game") is not None:
                filter_string += filters.get("game") + " "
            filter_string += "scoreboards"
        console.rule("[gold3]Displaying all records" + filter_string, style="gold3")

        tables = []
        for game in response.json()["data"]:
            table = Table(
                title=f"\n{game['title']}\n [purple]{game['date']} \n [gold3]Scoreboard ID: {game['id']}",
                show_lines=True,
                title_style="dark_orange3",
            )
            table.add_column("Name", justify="right", style="cyan")
            table.add_column("Score", justify="right", style="green")
            table.add_column("Winner?", justify="right", style="dark_magenta")
            for player, player_dict in game["players"].items():
                win = ":trophy:" if player_dict["win"] else ""
                table.add_row(
                    player,
                    str(player_dict["score"]),
                    win,
                )
            tables.append(table)
        console.print(Columns(tables, column_first=True))
        console.rule(style="gold3")


# main function controls control application menu selections
# each menu 1-3 calls an API endpoint and displays relevant data back to the user
def run():
    # main menu
    rich_print(
        Panel.fit(
            "[gold3]What would you like to do?[/gold3]\n\n1. Record new game scoreboard :memo:\n2. Search records :mag: \n3. See player stats :bar_chart:\n4. Exit application :wave::door:",
            border_style="red",
            title=":game_die: Main Menu :game_die:",
            padding=2,
        )
    )
    main_selection = IntPrompt.ask("", choices=["1", "2", "3", "4"], show_choices=False)

    if main_selection == 4:
        sys.exit()

    elif main_selection == 1:
        rich_print("\n")
        create_record_menu()
        rich_print("\n")

    elif main_selection == 2:
        rich_print("\n")
        display_records_menu()
        rich_print("\n")

    elif main_selection == 3:
        rich_print("\n")
        display_stats_menu()
        rich_print("\n")


if __name__ == "__main__":
    console.rule("[gold3]Welcome to the Board Game Score Tracker App!", style="gold3")
    rich_print("\n")
    while True:
        try:
            run()
        # if ever network connection failure with requests during app excecution return user to main menu safely
        except requests.exceptions.ConnectionError:
            rich_print(
                "[red]Could not connect to the API to continue processing your request, check your network connection and try again later!\n"
            )
        # catch other requests module exceptions and return to main menu
        except (
            requests.exceptions.Timeout,
            requests.exceptions.JSONDecodeError,
            requests.exceptions.TooManyRedirects,
        ):
            rich_print(
                "[red]Something went wrong with your request. Please try again later!\n"
            )
