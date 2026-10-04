"""Download a player's finished games from the Chess.com Published-Data API.

Requests are made strictly one after another (the PubAPI only rate-limits
parallel requests) and carry a User-Agent with contact info, as the API
documentation asks.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.chess.com/pub/player/{user}"
USER_AGENT = "sleepy_micha-elo-trainer/1.0 (personal training tool)"


def _get_json(url, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    delay = 2
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise SystemExit(f"Nicht gefunden (404): {url} – stimmt der Benutzername?")
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def fetch_games(username, time_class="rapid", out_dir="data", verbose=True):
    """Fetch all games of `time_class` and store them as JSON + PGN in out_dir.

    Returns the list of game dicts (Chess.com archive format).
    """
    user = username.lower()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    profile = _get_json(API.format(user=user))
    stats = _get_json(API.format(user=user) + "/stats")
    archives = _get_json(API.format(user=user) + "/games/archives").get("archives", [])
    if verbose:
        print(f"{len(archives)} Monatsarchive gefunden für {username}")

    games = []
    for url in archives:
        month_games = _get_json(url).get("games", [])
        picked = [g for g in month_games
                  if g.get("time_class") == time_class and g.get("rules", "chess") == "chess"]
        games.extend(picked)
        if verbose:
            print(f"  {url.rsplit('/', 2)[-2]}/{url.rsplit('/', 1)[-1]}: {len(picked)} {time_class}-Partien")

    meta = {"username": username, "time_class": time_class, "profile": profile,
            "stats": stats, "fetched_at": int(time.time())}
    (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    (out / f"games_{time_class}.json").write_text(json.dumps(games, indent=1, ensure_ascii=False))
    (out / f"games_{time_class}.pgn").write_text("\n\n".join(g.get("pgn", "") for g in games))
    if verbose:
        print(f"{len(games)} {time_class}-Partien gespeichert in {out}/")
    return games
