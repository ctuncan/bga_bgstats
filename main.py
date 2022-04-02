#!/usr/bin/env python3

from collections import namedtuple
import json
import requests
import uuid
import datetime

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


table = get_games(ctuncan_bga, 0)["data"]["tables"][0]


def duration_s(table):
    return int(table["end"]) - int(table["start"])


def start(table):
    return datetime.datetime.utcfromtimestamp(int(table["start"]))


def players(table):
    keys = ("players", "player_names", "ranks", "scores")
    Player = namedtuple("Player", ("id", "name", "rank", "score"))
    return [Player(*data) for data in zip(*(table[key].split(",") for key in keys))]


def play(table):
    return {
        "uuid": uuid.uuid5(table_ns, table["table_id"]),
        "ignored": False,
        "rating": 0,
        "scoringSetting": 0,
        "playerScores": [
            {
                "winner": player.rank == "1",
                "seatOrder": 0,
                "score": player.score,
                "startPlayer": False,
                "playerRefId": int(player.id),
                "rank": player.rank,
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


def location(table):
    return {
        "id": 1,
        "name": "Board Game Arena",
        "uuid": location_ns,
    }


def players_data(table):
    return [
        {
            "id": int(player.id),
            "isAnonymous": False,
            "name": player.name,
            "uuid": uuid.uuid5(player_ns, player.id),
        }
        for player in players(table)
    ]


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


bgsplay = {
    "games": [game(table)],
    "plays": [play(table)],
    "locations": [location(table)],
    "players": players_data(table),
    "userInfo": {"meRefId": ctuncan_bga},
}

print(json.dumps(bgsplay, cls=BGStatsEncoder))
with open("output.bgsplay", "w") as f:
    print(json.dump(bgsplay, f, cls=BGStatsEncoder))
