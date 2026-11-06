/* The window: season and language tabs, paths, episode choice, and following a running conversion. */
"use strict";

const TEXT = {
  german: {
    htmlLang: "de", season: "Season", short: "DE",
    title: "Der Fall der verschwundenen Stimmen",
    caseName: "Fallakte", caseNo: "Aktenzeichen",
    gameCaption: "Tatort (Remaster-Ordner)", gameEmpty: "Bitte Remaster-Ordner wählen",
    sourceCaption: "Zeugen (alte Version)", sourceEmpty: "Bitte alte deutsche Version wählen",
    episodes: "Episoden", installed: "installiert",
    deess: "Scharfe S-Laute abmildern",
    deessHint: "Dämpft scharfe S-Laute der alten Aufnahmen. Ausgeschaltet bleiben sie wie im Original.",
    install: "Stimmen installieren", remove: "Fall zu den Akten legen", removeHint: "Stimmen entfernen", cancel: "Abbrechen",
    photo: "Beweisfoto: die Erde mit Hasenohren", progress: "Fortschritt", languageGroup: "Sprache", seasonGroup: "Season",
    stampWorking: "In Arbeit", stampSolved: "Gelöst", stampOpen: "Ungelöst",
    open: "Beweisstück A: Das Remaster spricht nur noch Englisch.",
    solved: "Fall gelöst: Sam und Max sprechen wieder.",
    done: "Fall gelöst! Sam und Max sprechen wieder Deutsch.\nBitte im Spiel die Sprache auf Deutsch stellen.",
    removed: "Akte geschlossen. Das Spiel spricht wieder Englisch.",
    cancelled: "Abgebrochen. Am Spiel wurde nichts geändert.",
    failed: "Das hat nicht geklappt:", unknown: "Unbekannter Fehler.",
    starting: "Die Ermittlungen laufen …", removing: "Die Akte wird geschlossen …",
    step: (episode, voices, done, total) => `Episode ${episode}: ${voices ? "Stimmen" : "Szenen"} ${done} von ${total}`,
  },
  french: {
    htmlLang: "fr", season: "Saison", short: "FR",
    title: "L'affaire des voix disparues",
    caseName: "Dossier", caseNo: "Référence",
    gameCaption: "Scène de crime (dossier du remaster)", gameEmpty: "Choisir le dossier du remaster",
    sourceCaption: "Témoins (ancienne version)", sourceEmpty: "Choisir l'ancienne version française",
    episodes: "Épisodes", installed: "installé",
    deess: "", deessHint: "",
    install: "Installer les voix", remove: "Classer l'affaire", removeHint: "Retirer les voix", cancel: "Annuler",
    photo: "Photo à conviction : la Terre avec des oreilles de lapin", progress: "Progression", languageGroup: "Langue", seasonGroup: "Saison",
    stampWorking: "En cours", stampSolved: "Résolu", stampOpen: "Non résolu",
    open: "Pièce à conviction A : le remaster ne parle plus qu'anglais.",
    solved: "Affaire résolue : Sam et Max ont retrouvé leur voix.",
    done: "Affaire résolue ! Sam et Max parlent à nouveau français.\nRéglez la langue du jeu sur le français.",
    removed: "Dossier classé. Le jeu reparle anglais.",
    cancelled: "Annulé. Le jeu n'a pas été modifié.",
    failed: "Ça n'a pas marché :", unknown: "Erreur inconnue.",
    starting: "L'enquête est en cours…", removing: "Classement du dossier…",
    step: (episode, voices, done, total) => `Épisode ${episode} : ${voices ? "voix" : "scènes"} ${done} sur ${total}`,
  },
};

const SEASONS = [
  {
    id: 1, subtitle: "Save the World", caseNo: "101–106", languages: ["german", "french"],
    episodes: [
      ["101", "Culture-Schock", "Choc culturel"],
      ["102", "Situation Comedy", "Situation : comédie"],
      ["103", "Der Maulwurf, die Mafia und die Millionen", "La taupe, la Mafia et le nounours"],
      ["104", "Abe Lincoln muss sterben", "Abe Lincoln doit mourir !"],
      ["105", "Realität 2.0", "Reality 2.0"],
      ["106", "Die helle Seite des Mondes", "La face éclairée de la Lune"],
    ],
  },
  {
    id: 2, subtitle: "Beyond Time and Space", caseNo: "201–205", languages: ["german", "french"],
    episodes: [
      ["201", "Eisstation Santa", "Station de glace Père Noël"],
      ["202", "Moai Better Blues", "Moai Better Blues"],
      ["203", "Nacht der tanzenden Toten", "Les démons de minuit moins le quart"],
      ["204", "Chariots of the Dogs", "Chariots of the Dogs"],
      ["205", "Was geht ab, Beelzebub?", "Quoi de neuf, Belzébulle ?"],
    ],
  },
  {
    id: 3, subtitle: "The Devil's Playhouse", caseNo: "301–305", languages: ["german"],
    episodes: [
      ["301", "Der Straf-Raum", "La Quarantaine Dimension"],
      ["302", "Das Grab des Sammun-Mak", "Le tombeau de Sammun-Mak"],
      ["303", "Sie haben Max' Hirn entführt!", "On a volé le cerveau de Max !"],
      ["304", "Jenseits der Puppengasse", "Au-delà de l'allée des pantins"],
      ["305", "Die Stadt, die nicht zu schlafen wagt", "La ville qui ne dort jamais"],
    ],
  },
];

const $ = (id) => document.getElementById(id);

/* Paths, choices and messages belong to one season each; only one conversion runs at a time.
   A note is either a key into TEXT, so it follows the language, or text from the conversion itself. */
const cases = {};
for (const season of SEASONS) {
  cases[season.id] = {
    game: "",
    sources: {},
    gameOk: false,
    sourceOk: false,
    installed: {},
    selected: new Set(season.episodes.map(([no]) => no)),
    deess: true,
    note: { key: "open" },
    noteIsError: false,
    chosen: [],
  };
}

const state = { season: 1, language: "german", running: false, runSeason: null, mode: null };

const t = () => TEXT[state.language];
const seasonNow = () => SEASONS.find((s) => s.id === state.season);
const caseNow = () => cases[state.season];
const sourceOf = (current) => current.sources[state.language] || "";
const offered = (season) => season.languages.includes(state.language);

function renderTabs() {
  const box = $("tabs");
  box.textContent = "";
  box.setAttribute("aria-label", t().seasonGroup);
  for (const season of SEASONS) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "tab";
    tab.disabled = !offered(season);
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", "panel");
    const selected = season.id === state.season;
    tab.setAttribute("aria-selected", selected ? "true" : "false");
    tab.tabIndex = selected ? 0 : -1;
    tab.dataset.season = season.id;
    const name = document.createElement("span");
    name.className = "tab-name";
    name.textContent = `${t().season} ${season.id}`;
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
  const open = SEASONS.filter(offered).map((s) => s.id);
  const next = open[(open.indexOf(state.season) + step + open.length) % open.length];
  selectSeason(next);
  document.querySelector(`.tab[data-season="${next}"]`).focus();
}

function selectSeason(id) {
  state.season = id;
  render();
}

function renderEpisodes(season) {
  const current = caseNow();
  const list = $("episodeList");
  list.textContent = "";
  for (const [no, german, french] of season.episodes) {
    const row = document.createElement("label");
    row.className = "episode";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = current.selected.has(no);
    box.addEventListener("change", () => {
      if (box.checked) current.selected.add(no);
      else current.selected.delete(no);
      renderButtons();
    });
    const text = document.createElement("span");
    text.textContent = `${no} ${state.language === "french" ? french : german}`;
    row.append(box, text);
    if (current.installed[no]) {
      const done = document.createElement("span");
      done.className = "done";
      done.textContent = `${t().installed} (${TEXT[current.installed[no]].short})`;
      row.append(done);
    }
    list.append(row);
  }
}

function renderButtons() {
  const current = caseNow();
  $("install").disabled = state.running || !current.gameOk || !current.sourceOk || current.selected.size === 0;
  $("remove").disabled = state.running || Object.keys(current.installed).length === 0;
}

function renderLanguage() {
  document.documentElement.lang = t().htmlLang;
  $("language").setAttribute("aria-label", t().languageGroup);
  for (const tab of document.querySelectorAll(".lang-tab")) {
    tab.setAttribute("aria-checked", tab.dataset.language === state.language ? "true" : "false");
    tab.disabled = state.running;
  }
}

function renderStaticText() {
  const words = t();
  $("gameCaption").textContent = words.gameCaption;
  $("sourceCaption").textContent = words.sourceCaption;
  $("episodesLegend").textContent = words.episodes;
  $("deessText").textContent = words.deess;
  $("deessRow").title = words.deessHint;
  $("install").textContent = words.install;
  $("removeText").textContent = words.remove;
  $("removeHint").textContent = words.removeHint;
  $("cancel").textContent = words.cancel;
  $("photo").alt = words.photo;
  $("bar").setAttribute("aria-label", words.progress);
}

function pathValue(element, value, ok, emptyText) {
  element.textContent = value || emptyText;
  element.classList.toggle("missing", !ok);
  element.title = value;
}

function stampText(season) {
  if (state.running && state.runSeason === season.id) return [t().stampWorking, false];
  const all = season.episodes.every(([no]) => caseNow().installed[no]);
  return all ? [t().stampSolved, true] : [t().stampOpen, false];
}

function noteText(solved) {
  const note = caseNow().note;
  if (!note.key) return note.text;
  if (note.key !== "open") return t()[note.key];
  return solved ? t().solved : t().open;
}

function render() {
  const season = seasonNow();
  const current = caseNow();
  const busyHere = state.running && state.runSeason === season.id;
  renderTabs();
  renderLanguage();
  renderStaticText();
  $("title").textContent = t().title;
  $("caseName").textContent = `${t().caseName} ${t().season} ${season.id}`;
  $("caseNo").textContent = `${t().caseNo} ${season.caseNo}`;
  const [stamp, solved] = stampText(season);
  $("stamp").textContent = stamp;
  $("stamp").classList.toggle("solved", solved);
  const evidence = $("evidence");
  evidence.textContent = noteText(solved);
  evidence.classList.toggle("error", current.noteIsError);
  pathValue($("gameValue"), current.game, current.gameOk, t().gameEmpty);
  pathValue($("sourceValue"), sourceOf(current), current.sourceOk, t().sourceEmpty);
  $("gameRow").disabled = state.running;
  $("sourceRow").disabled = state.running;
  $("episodes").disabled = busyHere;
  renderEpisodes(season);
  $("deessRow").hidden = state.language !== "german";
  $("deess").checked = current.deess;
  $("deess").disabled = busyHere;
  $("actions").hidden = busyHere;
  $("running").hidden = !busyHere;
  renderButtons();
}

async function refreshPaths(id) {
  const current = cases[id];
  if (!window.pywebview) return;
  const result = await window.pywebview.api.check(id, current.game, sourceOf(current));
  current.gameOk = result.game_ok;
  current.sourceOk = result.source_ok;
  current.installed = result.installed;
}

async function pick(field) {
  const id = state.season;
  const current = cases[id];
  const folder = await window.pywebview.api.pick_folder(field === "game" ? current.game : sourceOf(current));
  if (!folder) return;
  if (field === "game") current.game = folder;
  else current.sources[state.language] = folder;
  await refreshPaths(id);
  render();
}

/* Each language has its own old release, so the witness folder is remembered per language. */
async function selectLanguage(language) {
  if (state.running || language === state.language) return;
  state.language = language;
  if (!offered(seasonNow())) state.season = SEASONS.find(offered).id;
  for (const season of SEASONS) {
    cases[season.id].sourceOk = false;
    await refreshPaths(season.id);
  }
  if (window.pywebview) window.pywebview.api.set_language(language);
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
  const chosen = cases[state.runSeason].chosen;
  const match = /^(\S+) (\d+)$/.exec(step);
  if (!match || !chosen.length) return 0;
  const index = Math.max(0, chosen.indexOf(match[2]));
  const phase = match[1] === "Stimmen" ? 0 : 0.5;
  return (index + phase + (0.5 * done) / Math.max(total, 1)) / chosen.length;
}

function friendlyStep(step, done, total) {
  const match = /^(\S+) (\d+)$/.exec(step);
  if (!match) return step;
  return t().step(match[2], match[1] === "Stimmen", done, total);
}

async function follow() {
  const running = cases[state.runSeason];
  const update = await window.pywebview.api.poll();
  if (update.progress) {
    const { step, done, total } = update.progress;
    setProgress(overallProgress(step, done, total), friendlyStep(step, done, total));
  }
  /* The conversion reports in German; the French window keeps its own message instead. */
  if (update.lines.length && state.language === "german") {
    running.note = { text: update.lines.slice(-4).join("\n") };
    running.noteIsError = false;
    if (state.season === state.runSeason) $("evidence").textContent = running.note.text;
  }
  if (update.finished === null) {
    setTimeout(follow, 250);
    return;
  }
  const id = state.runSeason;
  state.running = false;
  state.runSeason = null;
  await refreshPaths(id);
  if (update.finished === 0) {
    running.note = { key: state.mode === "remove" ? "removed" : "done" };
    running.noteIsError = false;
  } else if (update.cancelled) {
    running.note = { key: "cancelled" };
    running.noteIsError = false;
  } else {
    running.note = { text: `${t().failed}\n${update.tail || t().unknown}` };
    running.noteIsError = true;
  }
  render();
}

function beginRun(mode, key) {
  state.running = true;
  state.runSeason = state.season;
  state.mode = mode;
  caseNow().note = { key };
  caseNow().noteIsError = false;
  setProgress(0, t()[key]);
  render();
  follow();
}

async function install() {
  const current = caseNow();
  current.chosen = seasonNow().episodes.map(([no]) => no).filter((no) => current.selected.has(no));
  const error = await window.pywebview.api.install(current.game, sourceOf(current), current.chosen, current.deess, state.language);
  if (error) {
    current.note = { text: error };
    current.noteIsError = true;
    render();
    return;
  }
  beginRun("install", "starting");
}

async function removeDub() {
  const started = await window.pywebview.api.uninstall(caseNow().game, state.language);
  if (started) beginRun("remove", "removing");
}

window.addEventListener("pywebviewready", async () => {
  const initial = await window.pywebview.api.initial_state();
  for (const [id, values] of Object.entries(initial)) {
    cases[id].game = values.game;
    cases[id].sources = values.sources;
    await refreshPaths(Number(id));
  }
  render();
});

$("gameRow").addEventListener("click", () => pick("game"));
$("sourceRow").addEventListener("click", () => pick("source"));
$("deess").addEventListener("change", (event) => { caseNow().deess = event.target.checked; });
for (const tab of document.querySelectorAll(".lang-tab")) {
  tab.addEventListener("click", () => selectLanguage(tab.dataset.language));
}
$("install").addEventListener("click", install);
$("remove").addEventListener("click", removeDub);
$("cancel").addEventListener("click", () => window.pywebview.api.cancel());
render();
