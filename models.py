from pydantic import BaseModel
from typing import List
from enum import Enum

class Player(BaseModel):
    name: str
    rating: float

class Players(BaseModel):
    players: List[Player]

class Team(BaseModel):
    player1: str
    player2: str

class WhiteList(BaseModel):
    teams: List[Team]

class TourType(str, Enum):
    RANDOM = "random"
    RANDOM_15S = "random 15s"
    RANDOM_HOUSE = "usual-house"
    WATCHED = "watched"
    RANDOM_OP = "random op"
    RANDOM_ED = "random ed"
    RANDOM_INS = "random ins"
    RANDOM_CL = "random cl"
    WATCHED_INS = "watched ins"
    WATCHED_INS_NO_CHANTING  = "watched ins no chanting"
    WATCHED_5S = "watched 5s"
    WATCHED_2_PLUS_8 = "watched 2 8"
    WATCHED_X_2009 = "watched x-2009"
    WATCHED_ED = "watched ed"
    WATCHED_OP = "watched op"


class InhouseMatch(BaseModel):
    round: int
    team1_score: int
    team2_score: int

class InhouseResults(BaseModel):
    team1: List[Player]
    team2: List[Player]
    matches: List[InhouseMatch]

class Tour(BaseModel):
    type: TourType

class Challonge(BaseModel):
    challonge: str
