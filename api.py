from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from modules.support.LPProblem import LPProblem
from modules.support.handleCodes import handleCodes
from modules.support.generateCodes import *
from models import Players, WhiteList, TourType, Challonge, InhouseResults
from typing import Optional
from utils import get_guess_watched, get_guess_random, get_player_stats, get_blacklist, add_to_tourlist, get_guess_watched_28_gr
from utils import create_teams, sync_ids_from_sheet
from modules.main.eloscrape import EloScrape
from modules.main.tierMaker import TierMaker
from modules.support.getGuess import get_guess_old_usual
from modules.support.getAliases import *
import os
import json
from datetime import datetime, timezone

app = FastAPI()

origins = ["http://127.0.0.1:5000", "http://localhost:5000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/solver")
def solver(people: Players, team_size: int, tourType: TourType, whitelist: Optional[WhiteList], separateT1: bool):
    """
    Teams maker for watched, usual, random op/ed/ins, watched ins, 5s, 2+8
    """
    players = [(p.name, p.rating) for p in people.players]
    whitelist = [[team.player1, team.player2] for team in whitelist.teams]
    p_values = {p.name: p.rating for p in people.players}
    teams_number = int(len(players) / team_size)
    blacklist = get_blacklist()
    
    match tourType:
        case TourType.WATCHED:
            path = "watched_autoelo"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=1719516221, tabIDs=1903970832, type="watched")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_gr, gamemode="40", gr_based=True)
            
        case TourType.WATCHED_INS:
            path = "in_watched"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=1177294729, tabIDs=1903970832, type="watched-in")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_in_gr, gamemode="45", gr_based=True)
            
        case TourType.WATCHED_5S:
            path = "5s"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=676003100, tabIDs=1903970832, type="watched-5s")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_5s_gr, gamemode="no", gr_based=True)
            
        case TourType.RANDOM:
            path = "usual"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=0, tabIDs=1903970832, type="usual")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_usual_gr, gamemode="usual", gr_based=True)
            
        case TourType.RANDOM_15S:
            path = "usual"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=0, tabIDs=1903970832, type="usual")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_usual_gr, gamemode="quag", gr_based=True)

        case TourType.RANDOM_HOUSE:
            path = "usual_house"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=0, tabIDs=1903970832, type="usual")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_usual_gr, gamemode="usual", gr_based=True)
            
        case TourType.RANDOM_OP:
            path = "op_autoelo"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=591917504, tabIDs=1903970832, type="op")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_op_gr, gamemode=None, gr_based=True)
            
        case TourType.RANDOM_ED:
            path = "ed_autoelo"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=601464032, tabIDs=1903970832, type="ed")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_ed_gr, gamemode=None, gr_based=True)
            
        case TourType.RANDOM_INS:
            path = "in_autoelo"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=2075065970, tabIDs=1903970832, type="in")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_in_gr, gamemode=None, gr_based=True)
            
        case TourType.RANDOM_CL:
            path = "cl-usual"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=1506914251, tabIDs=1903970832, type="cl")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 8, "twog": 19, "threeg": 28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_random,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_cl_gr, gamemode=None, gr_based=True)
            
        case tourType.WATCHED_2_PLUS_8:
            path = "2+8"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=165193471, tabIDs=1903970832, type="watched-2+8")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "zerog":5, "oneg": 10, "twog": 15, "threeg": 20, "fourg":25}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched_28_gr,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_28_gr, gamemode="2+8", gr_based=True)
        
        case tourType.WATCHED_X_2009:
            path = "x-2009"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=1955111089, tabIDs=1903970832, type="watched-2009")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg":28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_2009_gr, gamemode="2009", gr_based=True)
            
        case tourType.WATCHED_ED:
            path = "ed_watched"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=484347985, tabIDs=1903970832, type="watched-ed")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg":28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_ed_gr, gamemode="ed", gr_based=True)
        
        case tourType.WATCHED_OP:
            path = "op_watched"
            teams = create_teams(path, players, team_size, whitelist, blacklist, separateT1)
            player_stats, idtable = get_player_stats(path=path, tabStats=1478248904, tabIDs=1903970832, type="watched-op")
            kwargs = {"player_stats": player_stats, "idtable": idtable, "oneg": 6, "twog": 12, "threeg": 18, "fourg":28}
            finalcodes = handleCodes(foundSolutions=teams, p_values=p_values, k=teams_number, get_guesses=get_guess_watched,
                kwargs_guesses=kwargs or None, get_codes=generate_codes_watched_op_gr, gamemode="op", gr_based=True)

    return finalcodes

@app.get("/tiermaker")
def tiermaker(tourType: TourType):
    """
    Watched 5s, Random, Watched 2+8 don't use tiermaker.
    """
    match tourType:
        case TourType.WATCHED:
            path = "watched_autoelo"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=1719516221, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A7',maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.4,minRating=0,maxRating=25,tourType="watched",gui=True)
            return True
                
        case TourType.WATCHED_INS:
            path = "in_watched"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=1177294729, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A8',maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.4,minRating=0,maxRating=25,tourType="watched-in",gui=True)
            return True
        
        case TourType.WATCHED_ED:
            path = "ed_watched"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=484347985, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A18', maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.4,minRating=0,maxRating=25,tourType="watched-ed",gui=True)
            return True
        
        case tourType.WATCHED_OP:
            path = "op_watched"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=1478248904, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A17', maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.4,minRating=0,maxRating=25,tourType="watched-op",gui=True)
            return True
  
        case TourType.RANDOM_OP:
            path = "op_autoelo"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=591917504, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A10',maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.33,minRating=0,maxRating=25,tourType="op",gui=True)
            return True

        case TourType.RANDOM_ED:
            path = "ed_autoelo"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=601464032, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A11',maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.33,minRating=0,maxRating=25,tourType="ed",gui=True)
            return True
            
        case TourType.RANDOM_INS:
            path = "in_autoelo"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=2075065970, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A12', maxFallbackWindow=6, activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.33,minRating=0,maxRating=25,tourType="in",gui=True)
            return True

        case TourType.RANDOM_CL:
            path = "cl-usual"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=1506914251, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A13',maxFallbackWindow=6,activeTours=10)
            tiermaker.make_tiers(alpha=3.75,midpoint=0.33,minRating=0,maxRating=25,tourType="cl",gui=True)
            return True
        
        # Not Dry Elo
        case TourType.WATCHED_5S:
            path = "5s"
            #only tabelostoragecell and tourlist_cell matter
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A3', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(tourlist_cell="C3") #important
            return True
        
        case TourType.WATCHED_2_PLUS_8:
            path = "2+8"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A2', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(tourlist_cell="C2")
            return True
        
        case TourType.RANDOM:
            path = "usual"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A1', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(tourlist_cell="C1")
            return True
        
        case TourType.RANDOM_15S:
            path = "usual"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A1', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(tourlist_cell="C1")
            return True

        case TourType.RANDOM_HOUSE:
            path = "usual_house"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0,
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A20', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(backlog_cell="C20")
            return True
        
        case TourType.WATCHED_X_2009:
            path = "x-2009"
            sync_ids_from_sheet(path, sheetName="NGM Stats Export v2", tabIDs=1903970832)
            tiermaker = TierMaker(directory=path, sheetName="NGM Stats Export v2", tabStats=0, 
                tabIDs=1903970832, tabEloStorage=82254993, tabEloStorageCell='A15', maxFallbackWindow=6, activeTours=10)
            tiermaker.update_elos(tourlist_cell="C15")
            return True
        
    return False


@app.post("/inhouse_results")
async def inhouse_results(tourType: TourType, results: InhouseResults):
    if tourType != TourType.RANDOM_HOUSE:
        raise HTTPException(status_code=400, detail="In-house results are only supported for usual-house.")

    if not results.matches:
        raise HTTPException(status_code=400, detail="Add at least one match result.")

    for match in results.matches:
        if not (0 <= match.team1_score <= 5 and 0 <= match.team2_score <= 5):
            raise HTTPException(status_code=400, detail="Scores must be between 0 and 5.")

    path = "usual_house"
    now = datetime.now(timezone.utc)
    tour_id = now.strftime("usual_house_%Y%m%d_%H%M%S")

    def team_payload(team):
        players = [{"name": p.name.strip().lower(), "rating": float(p.rating)} for p in team]
        display_name = " ".join(f"{p['name']} ({p['rating']:.3f})" for p in players)
        return {"display_name": display_name, "players": players}

    entry = {
        "source": "inhouse",
        "tour_id": tour_id,
        "time": now.isoformat(),
        "team_size": len(results.team1),
        "teams": {
            "team1": team_payload(results.team1),
            "team2": team_payload(results.team2),
        },
        "matches": [],
    }

    for match in results.matches:
        if match.team1_score > match.team2_score:
            winner = "team1"
        elif match.team2_score > match.team1_score:
            winner = "team2"
        else:
            winner = "draw"

        entry["matches"].append({
            "round": match.round,
            "team1_score": match.team1_score,
            "team2_score": match.team2_score,
            "winner": winner,
        })

    backlog_path = os.path.join(path, "match_backlog.json")
    if os.path.exists(backlog_path):
        with open(backlog_path, encoding="utf-8") as f:
            backlog = json.load(f)
    else:
        backlog = []

    backlog.append(entry)
    with open(backlog_path, "w", encoding="utf-8") as f:
        json.dump(backlog, f, indent=4)

    eloscraper = EloScrape(directory=path, tabEloStorage=82254993, tabEloStorageCell="A20", sheetName="NGM Stats Export v2",
        mu=12, sigma=4, beta=7, tau=5, draw_probability=0.04)
    await eloscraper.eloscrape(backlog_cell="C20")
    return True

@app.post("/eloscrape")
async def eloscrape(tourType: TourType, challonge: Challonge):
    challonge_str = challonge.challonge
    match tourType:
        case TourType.WATCHED_5S:
            path = "5s"
            add_to_tourlist(tour=challonge_str, folder=path)
            eloscraper = EloScrape(directory=path, tabEloStorage=716533894, tabEloStorageCell="A3", sheetName="ngm stats", 
                mu=12, sigma=4, beta=7, tau=0.09, draw_probability=0.04)
            await eloscraper.eloscrape(tourlist_cell="C3")
            return True
        
        case TourType.WATCHED_2_PLUS_8:
            path = "2+8"
            add_to_tourlist(tour=challonge_str, folder=path)
            eloscraper = EloScrape(directory=path, tabEloStorage=82254993, tabEloStorageCell="A2", sheetName="NGM Stats Export v2", 
                mu=10, sigma=3, beta=3, tau=0.5, draw_probability=0.01)
            await eloscraper.eloscrape(tourlist_cell="C2")
            return True
        
        case TourType.RANDOM:
            path = "usual"
            add_to_tourlist(tour=challonge_str, folder=path)
            eloscraper = EloScrape(directory=path, tabEloStorage=82254993, tabEloStorageCell="A1", sheetName="NGM Stats Export v2", 
                mu=12, sigma=1.75, beta=7, tau=0.09, draw_probability=0.04)
            await eloscraper.eloscrape(tourlist_cell="C1")
            return True
        
        case TourType.RANDOM_15S:
            path = "usual"
            add_to_tourlist(tour=challonge_str, folder=path)
            eloscraper = EloScrape(directory=path, tabEloStorage=82254993, tabEloStorageCell="A1", sheetName="NGM Stats Export v2", 
                mu=12, sigma=1.75, beta=7, tau=0.09, draw_probability=0.04)
            await eloscraper.eloscrape(tourlist_cell="C1")
            return True
        
        case TourType.WATCHED_X_2009:
            path = "x-2009"
            add_to_tourlist(tour=challonge_str, folder=path)
            eloscraper = EloScrape(directory=path, tabEloStorage=82254993, tabEloStorageCell="A15", sheetName="NGM Stats Export v2", 
                mu=12, sigma=1.75, beta=7, tau=0.09, draw_probability=0.04)
            await eloscraper.eloscrape(tourlist_cell="C15")
            return True
        
    return False

#uvicorn api:app --reload
