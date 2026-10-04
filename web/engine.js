// Stockfish (WASM, single-threaded lite build) in a Web Worker.

export class Engine {
  constructor(url = "vendor/stockfish-19-lite-single.js") {
    this.worker = new Worker(url);
    this.listeners = [];
    this.worker.onmessage = (e) => {
      const line = typeof e.data === "string" ? e.data : String(e.data);
      for (const l of [...this.listeners]) l(line);
    };
  }

  _waitFor(pred) {
    return new Promise((resolve) => {
      const fn = (line) => {
        if (pred(line)) {
          this.listeners = this.listeners.filter((x) => x !== fn);
          resolve(line);
        }
      };
      this.listeners.push(fn);
    });
  }

  send(cmd) {
    this.worker.postMessage(cmd);
  }

  async init() {
    const ok = this._waitFor((l) => l === "uciok");
    this.send("uci");
    await ok;
    this.send("setoption name Hash value 32");
    await this.ready();
  }

  async ready() {
    const r = this._waitFor((l) => l === "readyok");
    this.send("isready");
    await r;
  }

  async newGame() {
    this.send("ucinewgame");
    await this.ready();
  }

  /** Analyse a FEN to a fixed depth. Score is from the side to move. */
  analyse(fen, depth) {
    return new Promise((resolve) => {
      let last = null;
      const fn = (line) => {
        if (line.startsWith("info") && line.includes(" pv ") && line.includes(" score ")) {
          if (/ multipv (\d+)/.test(line) && !/ multipv 1 /.test(line)) return;
          last = line;
        } else if (line.startsWith("bestmove")) {
          this.listeners = this.listeners.filter((x) => x !== fn);
          resolve(parseInfo(last, line));
        }
      };
      this.listeners.push(fn);
      this.send(`position fen ${fen}`);
      this.send(`go depth ${depth}`);
    });
  }

  quit() {
    this.send("quit");
    this.worker.terminate();
  }
}

function parseInfo(info, bestLine) {
  const res = { cp: 0, mate: null, pv: [] };
  if (info) {
    const m = info.match(/ score (cp|mate) (-?\d+)/);
    if (m) {
      if (m[1] === "cp") res.cp = parseInt(m[2], 10);
      else {
        res.mate = parseInt(m[2], 10);
        res.cp = res.mate > 0 ? 10000 - res.mate : -10000 - res.mate;
      }
    }
    const pv = info.split(" pv ")[1];
    if (pv) res.pv = pv.trim().split(/\s+/);
  }
  if (!res.pv.length && bestLine) {
    const b = bestLine.split(/\s+/)[1];
    if (b && b !== "(none)") res.pv = [b];
  }
  return res;
}
