#!/usr/bin/env python3

from collections import namedtuple
import json
import requests
import uuid
import datetime
import itertools

ctuncan_ns = uuid.uuid5(uuid.NAMESPACE_DNS, "chris.tuncan.uk")
table_ns = uuid.uuid5(ctuncan_ns, "bga-tables")
player_ns = uuid.uuid5(ctuncan_ns, "bga-players")
location_ns = uuid.uuid5(ctuncan_ns, "bga-location")
game_ns = uuid.uuid5(ctuncan_ns, "bga-game")

ctuncan_bga = 0 # Enter your ID here


def get_games(player, page):
    params = {
        "player": player,
        "opponent_id": 0,
        "finished": 0,
        "updateStats": 0,
    }

    if page > 0:
        params["page"] = page

    return requests.get(
        "https://boardgamearena.com/gamestats/gamestats/getGames.html", params=params
    ).json()


def duration_s(table):
    return int(table["end"]) - int(table["start"])


def start(table):
    return datetime.datetime.utcfromtimestamp(int(table["start"]))


def players(tables):
    if not isinstance(tables, list):
        tables = [tables]
    keys = ("players", "player_names", "ranks", "scores")
    Player = namedtuple("Player", ("id", "name", "rank", "score"))
    for table in tables:

        def safe_key_split(key):
            raw = table[key]
            if raw is None:
                return [None]
            return raw.split(",")

        yield from [
            Player(*data)
            for data in itertools.zip_longest(*(safe_key_split(key) for key in keys))
        ]


def play(table):
    return {
        "uuid": uuid.uuid5(table_ns, table["table_id"]),
        "ignored": table["normalend"] != "1",
        "rating": 0,
        "scoringSetting": 0,
        "playerScores": [
            {
                "winner": player.rank == "1",
                "seatOrder": 0,
                "score": player.score,
                "startPlayer": False,
                "playerRefId": int(player.id),
                "rank": player.rank or 0,
                "newPlayer": False,
            }
            for player in players(table)
        ],
        "playDate": start(table),
        "manualWinner": False,
        "locationRefId": 1,
        "rounds": 0,
        "usesTeams": False,
        "playImages": "[]",
        "durationMin": duration_s(table) // 60,
        "gameRefId": int(table["game_id"]),
    }


def location():
    return {
        "id": 1,
        "name": "Board Game Arena",
        "uuid": location_ns,
    }


def unique(seq, key=None):
    if key is None:
        key = lambda x: x
    seen = set()
    return (x for x in seq if key(x) not in seen and not seen.add(key(x)))


def players_data(players):
    unique_players = unique(players, lambda player: player.id)
    return [
        {
            "id": int(player.id),
            "isAnonymous": False,
            "name": player.name,
            "uuid": uuid.uuid5(player_ns, player.id),
        }
        for player in unique_players
    ]


def games(tables):
    unique_games = unique(tables, lambda table: table["game_id"])
    return [game(table) for table in unique_games]


def game(table):
    return {
        "id": int(table["game_id"]),
        "uuid": uuid.uuid5(game_ns, table["game_id"]),
        "noPoints": False,
        "highestWins": True,
        "cooperative": False,
        "usesTeams": False,
        "bggId": 0,
        "bggYear": 0,
        "name": table["game_name"],
    }


class BGStatsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj).upper()
        if isinstance(obj, datetime.datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def get_tables(max_pages=10):
    for i in range(max_pages):
        yield from get_games(ctuncan_bga, i)["data"]["tables"]


def get_tables_since(since):
    for table in get_tables():
        table_time = datetime.datetime.utcfromtimestamp(int(table["start"]))
        if table_time > since:
            yield table
        else:
            return


tables = list(get_tables_since(datetime.datetime(2021, 12, 8)))

bgsplay = {
    "games": games(tables),
    "plays": [play(table) for table in tables],
    "locations": [location()],
    "players": players_data(players(tables)),
    "userInfo": {"meRefId": ctuncan_bga},
}


print(json.dumps(bgsplay, cls=BGStatsEncoder))
with open("output.bgsplay", "w") as f:
    print(json.dump(bgsplay, f, cls=BGStatsEncoder))
