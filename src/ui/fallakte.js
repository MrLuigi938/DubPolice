/* The window: season tabs, paths, episode choice, and following a running conversion. */
"use strict";

const LOCK = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" ' +
  'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Gesperrt"><rect x="5" y="11" width="14" height="10" rx="1.5"/>' +
  '<path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

const LOCKED_TITLE = "Die Akte liegt noch im Keller";
const LOCKED_NOTE = "Noch kein Beweisstück. Diese Season kommt später dran.";

const SEASONS = [
  {
    id: 1, name: "Season 1", subtitle: "Save the World", caseNo: "101–106", locked: true,
    episodes: [["101", "Culture Shock"], ["102", "Situation Comedy"], ["103", "The Mole, the Mob and the Meatball"],
      ["104", "Abe Lincoln Must Die!"], ["105", "Reality 2.0"], ["106", "Bright Side of the Moon"]],
  },
  {
    id: 2, name: "Season 2", subtitle: "Beyond Time and Space", caseNo: "201–205", locked: false,
    episodes: [["201", "Eisstation Santa"], ["202", "Moai Better Blues"], ["203", "Nacht der tanzenden Toten"],
      ["204", "Chariots of the Dogs"], ["205", "Was geht ab, Beelzebub?"]],
  },
  {
    id: 3, name: "Season 3", subtitle: "The Devil's Playhouse", caseNo: "301–305", locked: true,
    episodes: [["301", "The Penal Zone"], ["302", "The Tomb of Sammun-Mak"], ["303", "They Stole Max's Brain!"],
      ["304", "Beyond the Alley of the Dolls"], ["305", "The City That Dares Not Sleep"]],
  },
];

const OPEN_NOTE = "Beweisstück A: Das Remaster spricht nur noch Englisch.";
const SOLVED_NOTE = "Fall gelöst: Sam und Max sprechen wieder Deutsch.";
const $ = (id) => document.getElementById(id);

const state = {
  season: 2,
  game: "",
  source: "",
  gameOk: false,
  sourceOk: false,
  installed: [],
  selected: new Set(SEASONS[1].episodes.map(([no]) => no)),
  running: false,
  mode: null,
  note: OPEN_NOTE,
  noteIsError: false,
  chosen: [],
};

function renderTabs() {
  const box = $("tabs");
  box.textContent = "";
  for (const season of SEASONS) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "tab" + (season.locked ? " locked" : "");
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", "panel");
    const selected = season.id === state.season;
    tab.setAttribute("aria-selected", selected ? "true" : "false");
    tab.tabIndex = selected ? 0 : -1;
    tab.dataset.season = season.id;
    const name = document.createElement("span");
    name.className = "tab-name";
    name.innerHTML = season.locked ? LOCK : "";
    name.append(season.name);
    const sub = document.createElement("span");
    sub.className = "tab-sub";
    sub.textContent = season.subtitle;
    tab.append(name, sub);
    tab.addEventListener("click", () => selectSeason(season.id));
    tab.addEventListener("keydown", onTabKey);
    box.append(tab);
  }
}

function onTabKey(event) {
  const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
  if (!step) return;
  event.preventDefault();
  const next = ((state.season - 1 + step + SEASONS.length) % SEASONS.length) + 1;
  selectSeason(next);
  document.querySelector(`.tab[data-season="${next}"]`).focus();
}

function selectSeason(id) {
  state.season = id;
  render();
}

function renderEpisodes(season) {
  const list = $("episodeList");
  list.textContent = "";
  for (const [no, title] of season.episodes) {
    const row = document.createElement("label");
    row.className = "episode";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = state.selected.has(no);
    box.addEventListener("change", () => {
      if (box.checked) state.selected.add(no);
      else state.selected.delete(no);
      renderButtons();
    });
    const text = document.createElement("span");
    text.textContent = `${no} ${title}`;
    row.append(box, text);
    if (state.installed.includes(no)) {
      const done = document.createElement("span");
      done.className = "done";
      done.textContent = "installiert";
      row.append(done);
    }
    list.append(row);
  }
}

function renderLocked(season) {
  $("lockedText").textContent = `Diese Akte ist noch nicht geöffnet. Für ${season.name} gibt es noch keine Umwandlung.`;
  const list = $("lockedList");
  list.textContent = "";
  for (const [no, title] of season.episodes) {
    const row = document.createElement("div");
    row.className = "row";
    row.textContent = `${no} ${title}`;
    list.append(row);
  }
}

function renderButtons() {
  $("install").disabled = !state.gameOk || !state.sourceOk || state.selected.size === 0;
  $("remove").disabled = state.installed.length === 0;
}

function pathValue(element, value, ok, emptyText) {
  element.textContent = value || emptyText;
  element.classList.toggle("missing", !ok);
  element.title = value;
}

function stampText(season) {
  if (season.locked) return ["Gesperrt", false];
  if (state.running) return ["In Arbeit", false];
  const all = season.episodes.every(([no]) => state.installed.includes(no));
  return all ? ["Gelöst", true] : ["Ungelöst", false];
}

function render() {
  const season = SEASONS.find((s) => s.id === state.season);
  renderTabs();
  document.body.classList.toggle("is-locked", season.locked);
  $("title").textContent = season.locked ? LOCKED_TITLE : "Der Fall der verschwundenen Stimmen";
  $("caseName").textContent = `Fallakte ${season.name}`;
  $("caseNo").textContent = `Aktenzeichen ${season.caseNo}`;
  const [stamp, solved] = stampText(season);
  $("stamp").textContent = stamp;
  $("stamp").classList.toggle("solved", solved);
  const evidence = $("evidence");
  const note = solved && state.note === OPEN_NOTE ? SOLVED_NOTE : state.note;
  evidence.textContent = season.locked ? LOCKED_NOTE : note;
  evidence.classList.toggle("error", !season.locked && state.noteIsError);
  $("openView").hidden = season.locked;
  $("lockedView").hidden = !season.locked;
  if (season.locked) {
    renderLocked(season);
    return;
  }
  pathValue($("gameValue"), state.game, state.gameOk, "Bitte Remaster-Ordner wählen");
  pathValue($("sourceValue"), state.source, state.sourceOk, "Bitte alte deutsche Version wählen");
  $("gameRow").disabled = state.running;
  $("sourceRow").disabled = state.running;
  $("episodes").disabled = state.running;
  renderEpisodes(season);
  $("actions").hidden = state.running;
  $("running").hidden = !state.running;
  renderButtons();
}

async function refreshPaths() {
  const result = await window.pywebview.api.check(state.game, state.source);
  state.gameOk = result.game_ok;
  state.sourceOk = result.source_ok;
  state.installed = result.installed;
}

async function pick(field) {
  const folder = await window.pywebview.api.pick_folder(state[field]);
  if (!folder) return;
  state[field] = folder;
  await refreshPaths();
  render();
}

function setProgress(fraction, text) {
  const percent = Math.round(Math.max(0, Math.min(1, fraction)) * 100);
  $("barFill").style.width = `${percent}%`;
  $("bar").setAttribute("aria-valuenow", percent);
  $("runText").textContent = text;
}

/* Each episode has two phases of about equal length: voices, then timing. */
function overallProgress(step, done, total) {
  const match = /^(\S+) (\d+)$/.exec(step);
  if (!match || !state.chosen.length) return 0;
  const index = Math.max(0, state.chosen.indexOf(match[2]));
  const phase = match[1] === "Stimmen" ? 0 : 0.5;
  return (index + phase + (0.5 * done) / Math.max(total, 1)) / state.chosen.length;
}

function friendlyStep(step, done, total) {
  const match = /^(\S+) (\d+)$/.exec(step);
  if (!match) return step;
  const noun = match[1] === "Stimmen" ? "Stimmen" : "Szenen";
  return `Episode ${match[2]}: ${noun} ${done} von ${total}`;
}

async function follow() {
  const update = await window.pywebview.api.poll();
  if (update.progress) {
    const { step, done, total } = update.progress;
    setProgress(overallProgress(step, done, total), friendlyStep(step, done, total));
  }
  if (update.lines.length) {
    state.note = update.lines.slice(-4).join("\n");
    state.noteIsError = false;
    if (state.season === 2) $("evidence").textContent = state.note;
  }
  if (update.finished === null) {
    setTimeout(follow, 250);
    return;
  }
  state.running = false;
  await refreshPaths();
  if (update.finished === 0) {
    state.note = state.mode === "remove"
      ? "Akte geschlossen. Das Spiel spricht wieder Englisch."
      : "Fall gelöst! Sam und Max sprechen wieder Deutsch.\nBitte im Spiel die Sprache auf Deutsch stellen.";
    state.noteIsError = false;
  } else if (update.cancelled) {
    state.note = "Abgebrochen. Am Spiel wurde nichts geändert.";
    state.noteIsError = false;
  } else {
    state.note = "Das hat nicht geklappt:\n" + (update.tail || "Unbekannter Fehler.");
    state.noteIsError = true;
  }
  render();
}

function beginRun(mode, text) {
  state.running = true;
  state.mode = mode;
  state.note = text;
  state.noteIsError = false;
  setProgress(0, text);
  render();
  follow();
}

async function install() {
  const season = SEASONS.find((s) => s.id === 2);
  state.chosen = season.episodes.map(([no]) => no).filter((no) => state.selected.has(no));
  const error = await window.pywebview.api.install(state.game, state.source, state.chosen);
  if (error) {
    state.note = error;
    state.noteIsError = true;
    render();
    return;
  }
  beginRun("install", "Die Ermittlungen laufen …");
}

async function removeDub() {
  const started = await window.pywebview.api.uninstall(state.game);
  if (started) beginRun("remove", "Die Akte wird geschlossen …");
}

window.addEventListener("pywebviewready", async () => {
  const initial = await window.pywebview.api.initial_state();
  state.game = initial.game;
  state.source = initial.source;
  await refreshPaths();
  render();
});

$("gameRow").addEventListener("click", () => pick("game"));
$("sourceRow").addEventListener("click", () => pick("source"));
$("install").addEventListener("click", install);
$("remove").addEventListener("click", removeDub);
$("cancel").addEventListener("click", () => window.pywebview.api.cancel());
render();
