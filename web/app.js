// UI: load games (Chess.com API in the browser, or a PGN file), analyse with
// Stockfish WASM, cache per game in IndexedDB, render the report.

import { analyseGame } from "./analysis.js";
import { Engine } from "./engine.js";
import { buildPlan, ratingProjection } from "./plan.js";
import { buildProfile } from "./profile.js";
import { planCsv, renderReport } from "./render.js";

const $ = (id) => document.getElementById(id);
const API = "https://api.chess.com/pub/player/";
let cancelled = false;

// ---------- Chess.com API (fetch, JSONP fallback; strictly serial requests)
function jsonp(url) {
  return new Promise((resolve, reject) => {
    const cb = "cb_" + Math.random().toString(36).slice(2);
    const s = document.createElement("script");
    const done = () => { delete window[cb]; s.remove(); };
    window[cb] = (data) => { done(); resolve(data); };
    s.onerror = () => { done(); reject(new Error("JSONP fehlgeschlagen: " + url)); };
    s.src = url + (url.includes("?") ? "&" : "?") + "callback=" + cb;
    document.head.appendChild(s);
  });
}

async function getJSON(url) {
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const r = await fetch(url);
      if (r.status === 404) throw Object.assign(new Error("Nicht gefunden: " + url), { fatal: true });
      if (r.status === 429) { await new Promise((ok) => setTimeout(ok, 2000 * 2 ** attempt)); continue; }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch (err) {
      if (err.fatal) throw err;
      try { return await jsonp(url); } catch { /* retry */ }
      await new Promise((ok) => setTimeout(ok, 1000 * 2 ** attempt));
    }
  }
  throw new Error("Chess.com-API nicht erreichbar: " + url);
}

async function fetchGames(user, timeClass, maxGames) {
  const base = API + encodeURIComponent(user.toLowerCase());
  const { archives = [] } = await getJSON(base + "/games/archives");
  const games = [];
  for (let i = archives.length - 1; i >= 0; i--) { // newest month first
    if (cancelled) break;
    status(`Lade Archiv ${archives.length - i}/${archives.length} …`, (archives.length - i) / archives.length);
    const month = await getJSON(archives[i]);
    const picked = (month.games || []).filter((g) => g.time_class === timeClass && (g.rules || "chess") === "chess");
    games.push(...picked.reverse());
    if (maxGames && games.length >= maxGames) break;
  }
  games.sort((a, b) => (b.end_time || 0) - (a.end_time || 0));
  return maxGames ? games.slice(0, maxGames) : games;
}

// ---------- PGN import (Chess.com "Download" export)
const DRAW = { repetition: "repetition", agreement: "agreed", stalemate: "stalemate", insufficient: "insufficient", "50": "50move" };

function timeClassOf(tc) {
  if (!tc || tc.includes("/") || tc === "-") return "daily";
  const [b, inc = "0"] = tc.split("+");
  const est = parseInt(b, 10) + 40 * parseInt(inc, 10);
  return est < 180 ? "bullet" : est < 600 ? "blitz" : "rapid";
}

function pgnToGames(text) {
  return text.split(/(?=^\[Event )/m).map((s) => s.trim()).filter(Boolean).map((raw, i) => {
    const h = {};
    for (const m of raw.matchAll(/^\[(\w+) "([^"]*)"\]/gm)) h[m[1]] = m[2];
    const term = (h.Termination || "").toLowerCase();
    let wr, br;
    if (h.Result === "1/2-1/2") {
      wr = br = Object.entries(DRAW).find(([k]) => term.includes(k))?.[1] || "agreed";
    } else {
      const loss = term.includes("checkmate") ? "checkmated" : term.includes("time") ? "timeout" : term.includes("abandon") ? "abandoned" : "resigned";
      [wr, br] = h.Result === "1-0" ? ["win", loss] : [loss, "win"];
    }
    const date = (h.EndDate || h.Date || "1970.01.01").replace(/\?/g, "1").replace(/\./g, "-");
    const end = Date.parse(`${date}T${(h.EndTime || "00:00:00").split(" ")[0]}Z`) / 1000 || 0;
    return {
      url: h.Link || `pgn://${i}-${h.White}-${h.Black}-${date}`, pgn: raw, time_control: h.TimeControl || "",
      time_class: timeClassOf(h.TimeControl), end_time: end, rules: "chess", eco: h.ECOUrl || "",
      white: { username: h.White || "", rating: parseInt(h.WhiteElo, 10) || null, result: wr },
      black: { username: h.Black || "", rating: parseInt(h.BlackElo, 10) || null, result: br },
    };
  });
}

// ---------- IndexedDB cache
function db() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("elo-trainer", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("analysis");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function cacheGet(key) {
  try {
    const d = await db();
    return await new Promise((ok) => { const r = d.transaction("analysis").objectStore("analysis").get(key); r.onsuccess = () => ok(r.result); r.onerror = () => ok(undefined); });
  } catch { return undefined; }
}
async function cachePut(key, val) {
  try {
    const d = await db();
    await new Promise((ok) => { const t = d.transaction("analysis", "readwrite"); t.objectStore("analysis").put(val, key); t.oncomplete = ok; t.onerror = ok; });
  } catch { /* cache is optional */ }
}

// ---------- UI
function status(text, frac) {
  $("status").textContent = text;
  if (frac !== undefined) $("progress").style.width = `${Math.round(100 * frac)}%`;
}

async function run(source) {
  cancelled = false;
  const user = $("user").value.trim();
  const timeClass = $("tc").value;
  const maxGames = parseInt($("max").value, 10) || null;
  const depth = parseInt($("depth").value, 10) || 10;
  try { localStorage.setItem("elo-trainer-form", JSON.stringify({ user, timeClass, maxGames, depth })); } catch { /* optional */ }
  $("run").disabled = true; $("cancel").hidden = false; $("progresswrap").hidden = false; $("report").innerHTML = "";

  let engine;
  try {
    let games;
    if (source) {
      games = pgnToGames(source).filter((g) => g.time_class === timeClass)
        .sort((a, b) => (b.end_time || 0) - (a.end_time || 0));
      if (maxGames) games = games.slice(0, maxGames);
    } else {
      status("Lade Partien von Chess.com …", 0);
      games = await fetchGames(user, timeClass, maxGames);
    }
    if (!games.length) throw new Error(`Keine ${timeClass}-Partien für „${user}“ gefunden.`);

    status("Starte Stockfish …", 0);
    engine = new Engine();
    await engine.init();
    const analysed = [];
    for (let k = 0; k < games.length && !cancelled; k++) {
      const g = games[k], key = `${depth}|${user.toLowerCase()}|${g.url}`;
      let res = await cacheGet(key);
      if (!res) {
        res = await analyseGame(engine, g, user, depth, (i, n) =>
          status(`Analysiere Partie ${k + 1}/${games.length} (Stellung ${i}/${n}) …`, (k + i / n) / games.length));
        if (res) await cachePut(key, res);
      }
      if (res) analysed.push(res);
    }
    if (!analysed.length) throw new Error(`Keine Partien von „${user}“ in den Daten gefunden – Benutzername korrekt?`);

    status(`${analysed.length} Partien analysiert – erstelle Report …`, 1);
    const profile = buildProfile(analysed);
    const tomorrow = new Date(); tomorrow.setUTCHours(12, 0, 0, 0); tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
    const plan = buildPlan(profile, tomorrow);
    const proj = ratingProjection(profile.current_rating, parseInt($("target").value, 10) || 2600);
    $("report").innerHTML = renderReport(profile, plan, proj, user);
    $("csv").onclick = () => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([planCsv(plan)], { type: "text/csv;charset=utf-8" }));
      a.download = `trainingsplan_${user}.csv`; a.click();
    };
    status(cancelled ? `Abgebrochen – Report aus ${analysed.length} Partien.` : `Fertig: ${analysed.length} Partien analysiert.`, 1);
    $("report").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    status("Fehler: " + err.message);
    console.error(err);
  } finally {
    if (engine) engine.quit();
    $("run").disabled = false; $("cancel").hidden = true;
  }
}

try {
  const saved = JSON.parse(localStorage.getItem("elo-trainer-form") || "null");
  if (saved) { $("user").value = saved.user; $("tc").value = saved.timeClass; $("max").value = saved.maxGames || ""; $("depth").value = saved.depth; }
} catch { /* optional */ }

$("form").addEventListener("submit", (ev) => { ev.preventDefault(); run(null); });
$("cancel").addEventListener("click", () => { cancelled = true; status("Breche nach der aktuellen Partie ab …"); });
$("pgn").addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (file) run(await file.text());
  ev.target.value = "";
});
