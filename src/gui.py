"""The window of the tool: a small web page (ui/) shown through WebView2, with this class as its backend."""
import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import webview

HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
GAME_FOLDER = "Sam & Max Beyond Time and Space"
MANIFEST = "SamMax_GermanDub.json"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"


def steam_libraries():
    """Every Steam library folder on this PC, from Steam's own configuration."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam = winreg.QueryValueEx(key, "SteamPath")[0]
    except OSError:
        return []
    folders = [os.path.normpath(steam)]
    try:
        with open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as f:
            for path in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                folders.append(os.path.normpath(path.replace("\\\\", "\\")))
    except OSError:
        pass
    return folders


def is_game(path):
    return bool(path) and os.path.isfile(os.path.join(path, "SamMax200.exe")) and os.path.isdir(os.path.join(path, "Archives"))


def find_game():
    for library in steam_libraries():
        candidate = os.path.join(library, "steamapps", "common", GAME_FOLDER)
        if is_game(candidate):
            return candidate
    return ""


def installed_episodes(game):
    try:
        with open(os.path.join(game, MANIFEST), encoding="utf-8") as f:
            return sorted(json.load(f).get("episodes", {}))
    except (OSError, ValueError):
        return []


class Backend:
    """Methods the page calls. Names starting with an underscore stay hidden from it."""

    def __init__(self):
        self._window = None
        self._process = None
        self._messages = queue.Queue()
        self._progress = None
        self._finished = None
        self._cancelled = False
        self._recent = []
        self._work = None

    def _set_window(self, window):
        self._window = window

    def initial_state(self):
        local = os.path.join(APP_DIR, "Quelldaten")
        return {"game": find_game(), "source": local if os.path.isdir(local) else ""}

    def check(self, game, source):
        ok = is_game(game)
        return {"game_ok": ok, "source_ok": bool(source) and os.path.isdir(source), "installed": installed_episodes(game) if ok else []}

    def pick_folder(self, current):
        start = current if current and os.path.isdir(current) else ""
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=start)
        return os.path.normpath(result[0]) if result else ""

    def install(self, game, source, episodes):
        if not episodes:
            return "Bitte mindestens eine Episode auswählen."
        return self._start(["--game", game, "--source", source, "--episodes", *episodes])

    def uninstall(self, game):
        question = "Deutsche Stimmen wieder entfernen? Das Spiel spricht danach wieder Englisch."
        if not self._window.create_confirmation_dialog("Fall zu den Akten legen", question):
            return False
        return self._start(["--game", game, "--uninstall"]) is None

    def cancel(self):
        if self._process and self._process.poll() is None:
            self._cancelled = True
            # Stops the worker processes too. Files reach the game complete or not at all.
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self._process.pid)], capture_output=True, creationflags=NO_WINDOW)

    def poll(self):
        lines = []
        while True:
            try:
                lines.append(self._messages.get_nowait())
            except queue.Empty:
                break
        finished = self._finished
        return {
            "lines": lines,
            "progress": self._progress,
            "finished": finished,
            "cancelled": self._cancelled,
            "tail": "\n".join(self._recent[-3:]) if finished else "",
        }

    def _start(self, args):
        if self._process and self._process.poll() is None:
            return "Es läuft bereits eine Umwandlung."
        self._progress = None
        self._finished = None
        self._cancelled = False
        self._recent = []
        self._work = tempfile.mkdtemp(prefix="SamMaxDE_")
        log_path = os.path.join(self._work, "log.txt")
        open(log_path, "w").close()
        command = [sys.executable] if FROZEN else [sys.executable, os.path.join(HERE, "launcher.py")]
        extra = ["--work", self._work] if "--uninstall" not in args else []
        self._process = subprocess.Popen([*command, "--engine", *args, *extra, "--log", log_path], creationflags=NO_WINDOW)
        threading.Thread(target=self._follow, args=(log_path,), daemon=True).start()
        return None

    def _follow(self, log_path):
        """Read the log until the conversion process has ended, then clean up its work folder."""
        with open(log_path, encoding="utf-8", errors="replace") as log:
            partial = ""
            while True:
                chunk = log.read()
                if chunk:
                    partial += chunk
                    *complete, partial = partial.split("\n")
                    for line in complete:
                        self._handle(line.rstrip())
                elif self._process.poll() is not None:
                    break
                else:
                    time.sleep(0.2)
        if partial.strip():
            self._handle(partial.rstrip())
        code = self._process.wait()
        shutil.rmtree(self._work, ignore_errors=True)
        self._finished = code

    def _handle(self, line):
        if line.startswith("PROGRESS "):
            step, done, total = line[9:].rsplit(" ", 2)
            self._progress = {"step": step, "done": int(done), "total": int(total)}
        elif line:
            self._recent.append(line)
            self._messages.put(line)


def run():
    backend = Backend()
    window = webview.create_window(
        "Sam & Max: Deutsche Synchronisation",
        url=os.path.join(HERE, "ui", "index.html"),
        js_api=backend,
        width=976,
        height=639,
        resizable=False,
        background_color="#05060b",
    )
    backend._set_window(window)
    try:
        webview.start(gui="edgechromium")
    except Exception as err:  # pywebview reports a missing WebView2 runtime in several ways
        ctypes.windll.user32.MessageBoxW(
            None,
            f"Das Fenster konnte nicht geöffnet werden. Vermutlich fehlt die WebView2-Runtime von Microsoft:\n"
            f"{WEBVIEW2_URL}\n\nFehler: {err}",
            "Sam & Max: Deutsche Synchronisation",
            0x10,
        )
        sys.exit(1)
    backend.cancel()


if __name__ == "__main__":
    run()
