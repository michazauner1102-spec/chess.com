"""Command line interface.

    python -m chess_trainer all --user sleepy_micha
    python -m chess_trainer fetch --user sleepy_micha
    python -m chess_trainer analyze --user sleepy_micha --depth 14
    python -m chess_trainer report --user sleepy_micha
    python -m chess_trainer import-pgn --user sleepy_micha datei.pgn   (falls die API nicht erreichbar ist)
"""

import argparse
import datetime as dt
import io
import json
import re
from pathlib import Path

import chess.pgn

from .analyze import analyse_all
from .fetch import fetch_games
from .plan import build_plan, rating_projection
from .profile import build_profile
from .report import render

DRAW_CODES = {"repetition": "repetition", "agreement": "agreed", "stalemate": "stalemate",
              "insufficient": "insufficient", "50": "50move", "timeout vs insufficient": "timevsinsufficient"}


def _time_class(tc):
    if not tc or "/" in tc or tc == "-":
        return "daily"
    base, _, inc = tc.partition("+")
    est = int(base) + 40 * int(inc or 0)
    return "bullet" if est < 180 else "blitz" if est < 600 else "rapid"


def pgn_to_games(text):
    """Convert a multi-game PGN (e.g. Chess.com download) into the archive JSON format."""
    games = []
    stream = io.StringIO(text)
    while True:
        start = stream.tell()
        g = chess.pgn.read_game(stream)
        if g is None:
            break
        raw = text[start:stream.tell()].strip()
        h = g.headers
        term = h.get("Termination", "").lower()
        res = h.get("Result", "*")
        if res == "1/2-1/2":
            code = next((v for k, v in DRAW_CODES.items() if k in term), "agreed")
            wr = br = code
        else:
            loss = ("checkmated" if "checkmate" in term else "timeout" if "time" in term
                    else "abandoned" if "abandon" in term else "resigned")
            wr, br = ("win", loss) if res == "1-0" else (loss, "win")
        date = h.get("EndDate", h.get("Date", "1970.01.01")).replace("?", "1")
        clock = h.get("EndTime", "00:00:00").split()[0]
        try:
            end = int(dt.datetime.strptime(f"{date} {clock}", "%Y.%m.%d %H:%M:%S").timestamp())
        except ValueError:
            end = 0
        tc = h.get("TimeControl", "")
        games.append({
            "url": h.get("Link") or f"pgn://{len(games)}-{h.get('White')}-{h.get('Black')}-{date}",
            "pgn": raw, "time_control": tc, "time_class": _time_class(tc), "end_time": end, "rules": "chess",
            "eco": h.get("ECOUrl", ""),
            "white": {"username": h.get("White", ""), "rating": _int(h.get("WhiteElo")), "result": wr},
            "black": {"username": h.get("Black", ""), "rating": _int(h.get("BlackElo")), "result": br},
        })
    return games


def _int(x):
    return int(x) if x and re.fullmatch(r"\d+", x) else None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chess_trainer", description="Chess.com Elo-Trainer")
    ap.add_argument("command", choices=["fetch", "analyze", "report", "all", "import-pgn"])
    ap.add_argument("pgn", nargs="?", help="PGN-Datei für import-pgn")
    ap.add_argument("--user", default="sleepy_micha")
    ap.add_argument("--time-class", default="rapid", choices=["rapid", "blitz", "bullet", "daily"])
    ap.add_argument("--data", default="data", help="Ordner für Rohdaten und Analyse-Cache")
    ap.add_argument("--out", default="report", help="Ordner für den Report")
    ap.add_argument("--depth", type=int, default=12, help="Stockfish-Suchtiefe (12 schnell, 16 gründlich)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--max-games", type=int, default=None, help="nur die neuesten N Partien analysieren")
    ap.add_argument("--stockfish", default=None, help="Pfad zur Stockfish-Binary")
    ap.add_argument("--start", default=None, help="Startdatum des Plans (JJJJ-MM-TT), Standard: morgen")
    ap.add_argument("--target", type=int, default=2600)
    a = ap.parse_args(argv)

    data = Path(a.data)
    games_file = data / f"games_{a.time_class}.json"

    if a.command in ("fetch", "all"):
        fetch_games(a.user, a.time_class, a.data)
    if a.command == "import-pgn":
        if not a.pgn:
            ap.error("import-pgn braucht eine PGN-Datei")
        games = [g for g in pgn_to_games(Path(a.pgn).read_text(encoding="utf-8", errors="replace"))
                 if g["time_class"] == a.time_class]
        data.mkdir(parents=True, exist_ok=True)
        games_file.write_text(json.dumps(games, ensure_ascii=False))
        print(f"{len(games)} {a.time_class}-Partien importiert nach {games_file}")
        return
    if a.command == "fetch":
        return

    if not games_file.exists():
        raise SystemExit(f"{games_file} fehlt – zuerst 'fetch' oder 'import-pgn' ausführen.")
    games = json.loads(games_file.read_text())
    analysed = analyse_all(games, a.user, a.data, depth=a.depth, stockfish=a.stockfish,
                           threads=a.threads, max_games=a.max_games)
    if a.command == "analyze":
        return

    profile = build_profile(analysed)
    start = dt.date.fromisoformat(a.start) if a.start else dt.date.today() + dt.timedelta(days=1)
    plan = build_plan(profile, start)
    proj = rating_projection(profile["current_rating"], a.target)
    path = render(profile, plan, proj, a.user, a.out)
    print(f"Report: {path.resolve()}")


if __name__ == "__main__":
    main()
