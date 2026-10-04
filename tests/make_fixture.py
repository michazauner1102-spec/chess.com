"""Create synthetic Chess.com-style rapid games (Stockfish self-play at low skill)
so the pipeline can be tested without network access. NOT real games."""
import random
import sys

import chess
import chess.engine
import chess.pgn

def make(n, path, user="sleepy_micha", seed=1):
    rnd = random.Random(seed)
    eng = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
    out = []
    for k in range(n):
        board = chess.Board()
        game = chess.pgn.Game()
        me_white = k % 2 == 0
        h = game.headers
        h["Event"] = "Live Chess"; h["Site"] = "Chess.com"; h["Date"] = h["EndDate"] = f"2026.09.{k + 1:02d}"
        h["White"], h["Black"] = (user, f"opp{k}") if me_white else (f"opp{k}", user)
        h["WhiteElo"], h["BlackElo"] = ("1100", str(1050 + 20 * k)) if me_white else (str(1050 + 20 * k), "1100")
        h["TimeControl"] = "600"; h["EndTime"] = "12:00:00"; h["Link"] = f"https://www.chess.com/game/live/{1000 + k}"
        node, clocks = game, {True: 600.0, False: 600.0}
        while not board.is_game_over() and board.ply() < 140:
            mine = board.turn == me_white
            eng.configure({"Skill Level": 2 if mine else 4})
            mv = eng.play(board, chess.engine.Limit(time=0.02)).move
            clocks[board.turn] -= rnd.uniform(1, 25)
            node = node.add_variation(mv)
            node.set_clock(max(1.0, clocks[board.turn]))
            board.push(mv)
        res = board.result(claim_draw=True)
        if res == "*":
            res = "1-0" if rnd.random() < 0.5 else "0-1"
            h["Termination"] = "won by resignation"
        elif board.is_checkmate():
            h["Termination"] = "won by checkmate"
        else:
            h["Termination"] = "Game drawn by repetition"
        h["Result"] = res
        game.headers["Result"] = res
        out.append(str(game))
    eng.quit()
    open(path, "w").write("\n\n".join(out) + "\n")

if __name__ == "__main__":
    make(int(sys.argv[1]), sys.argv[2])
