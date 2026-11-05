"""Simple window for the Sam & Max German dub tool."""
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if FROZEN else HERE
EPISODES = ("201", "202", "203", "204", "205")
DEFAULT_GAMES = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Sam & Max Beyond Time and Space",
    r"Z:\SteamLibrary\steamapps\common\Sam & Max Beyond Time and Space",
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sam & Max – Deutsche Synchronisation")
        self.geometry("760x540")
        self.minsize(640, 460)
        self.lines = queue.Queue()
        self.process = None

        pad = {"padx": 8, "pady": 4}
        frame = ttk.Frame(self)
        frame.pack(fill="x", **pad)
        frame.columnconfigure(1, weight=1)

        self.game = tk.StringVar(value=next((g for g in DEFAULT_GAMES if os.path.isdir(g)), ""))
        local = os.path.join(APP_DIR, "Quelldaten")
        self.source = tk.StringVar(value=local if os.path.isdir(local) else "")
        ttk.Label(frame, text="Remaster-Ordner:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.game).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(frame, text="Auswählen …", command=lambda: self.pick(self.game)).grid(row=0, column=2)
        ttk.Label(frame, text="Alte deutsche Version:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(frame, text="Auswählen …", command=lambda: self.pick(self.source)).grid(row=1, column=2)
        ttk.Label(frame, text="Installierter Ordner oder eingelegte/gemountete Disc von Season 2.").grid(row=2, column=1, sticky="w", padx=4)

        boxes = ttk.Frame(self)
        boxes.pack(fill="x", **pad)
        ttk.Label(boxes, text="Episoden:").pack(side="left")
        self.chosen = {}
        for e in EPISODES:
            self.chosen[e] = tk.BooleanVar(value=True)
            ttk.Checkbutton(boxes, text=e, variable=self.chosen[e]).pack(side="left", padx=4)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **pad)
        self.install_button = ttk.Button(buttons, text="Deutsche Stimmen installieren", command=self.install)
        self.install_button.pack(side="left")
        self.remove_button = ttk.Button(buttons, text="Wieder entfernen", command=self.uninstall)
        self.remove_button.pack(side="left", padx=8)

        self.status = tk.StringVar(value="Bereit.")
        ttk.Label(self, textvariable=self.status).pack(fill="x", **pad)
        self.bar = ttk.Progressbar(self, maximum=1.0)
        self.bar.pack(fill="x", **pad)
        self.log = tk.Text(self, height=14, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, **pad)
        self.after(100, self.pump)

    def pick(self, variable):
        folder = filedialog.askdirectory(initialdir=variable.get() or None)
        if folder:
            variable.set(os.path.normpath(folder))

    def run(self, args):
        self.install_button.state(["disabled"])
        self.remove_button.state(["disabled"])
        self.write("Starte …")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        handle, self.log_path = tempfile.mkstemp(prefix="SamMaxDE_", suffix=".log")
        os.close(handle)
        command = [sys.executable] if FROZEN else [sys.executable, os.path.join(HERE, "launcher.py")]
        self.process = subprocess.Popen([*command, "--engine", *args, "--log", self.log_path], creationflags=flags)
        threading.Thread(target=self.reader, daemon=True).start()

    def reader(self):
        """Follow the log file until the conversion process has ended."""
        newline = chr(10)
        with open(self.log_path, encoding="utf-8", errors="replace") as log:
            partial = ""
            while True:
                chunk = log.read()
                if chunk:
                    partial += chunk
                    *complete, partial = partial.split(newline)
                    for line in complete:
                        self.lines.put(line.rstrip())
                elif self.process.poll() is not None:
                    break
                else:
                    time.sleep(0.2)
        if partial.strip():
            self.lines.put(partial.rstrip())
        code = self.process.wait()
        try:
            os.remove(self.log_path)
        except OSError:
            pass
        self.lines.put(("EXIT", code))

    def pump(self):
        try:
            while True:
                item = self.lines.get_nowait()
                if isinstance(item, tuple):
                    self.finished(item[1])
                elif item.startswith("PROGRESS "):
                    step, done, total = item[9:].rsplit(" ", 2)
                    total = max(int(total), 1)
                    self.bar["value"] = int(done) / total
                    self.status.set(f"{step}: {done} von {total}")
                else:
                    self.write(item)
        except queue.Empty:
            pass
        self.after(100, self.pump)

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def finished(self, code):
        self.install_button.state(["!disabled"])
        self.remove_button.state(["!disabled"])
        self.bar["value"] = 1.0 if code == 0 else 0.0
        self.status.set("Fertig." if code == 0 else "Abgebrochen, siehe Meldungen.")
        if code == 0:
            messagebox.showinfo("Sam & Max", "Fertig.")
        else:
            messagebox.showerror("Sam & Max", "Das hat nicht geklappt. Die Meldungen stehen im Fenster.")

    def install(self):
        if not self.game.get() or not self.source.get():
            messagebox.showwarning("Sam & Max", "Bitte beide Ordner auswählen.")
            return
        episodes = [e for e in EPISODES if self.chosen[e].get()]
        if not episodes:
            messagebox.showwarning("Sam & Max", "Bitte mindestens eine Episode auswählen.")
            return
        self.run(["--game", self.game.get(), "--source", self.source.get(), "--episodes", *episodes])

    def uninstall(self):
        if not self.game.get():
            messagebox.showwarning("Sam & Max", "Bitte den Remaster-Ordner auswählen.")
            return
        if messagebox.askyesno("Sam & Max", "Deutsche Stimmen wieder entfernen?"):
            self.run(["--game", self.game.get(), "--uninstall"])


if __name__ == "__main__":
    App().mainloop()
