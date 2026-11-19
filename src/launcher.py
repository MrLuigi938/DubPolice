"""Entry point of DubPolice.exe: opens the window, or does the conversion when called with --engine."""
import multiprocessing
import os
import sys


def unblock():
    """Drop the download mark Windows puts on files unpacked from a downloaded ZIP.

    .NET refuses to load a marked Python.Runtime.dll, and then the window cannot open."""
    if not getattr(sys, "frozen", False):
        return
    for root, _dirs, files in os.walk(sys._MEIPASS):
        for f in files:
            try:
                os.remove(os.path.join(root, f) + ":Zone.Identifier")
            except OSError:
                pass


def main():
    multiprocessing.freeze_support()
    if "--engine" in sys.argv:
        sys.argv.remove("--engine")
        import sammax_de

        try:
            sammax_de.main()
        except SystemExit as stop:
            if isinstance(stop.code, str):
                print(stop.code, flush=True)
                sys.exit(1)
            raise
        except Exception:  # noqa: BLE001 - the window shows the log; a crash dialog would only block it
            import traceback

            traceback.print_exc()
            sys.stdout.flush()
            sys.exit(1)
    else:
        unblock()
        import gui

        gui.run()


if __name__ == "__main__":
    main()
